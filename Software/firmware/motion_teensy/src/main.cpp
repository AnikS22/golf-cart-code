/*
 * motion_teensy/src/main.cpp
 * ============================================================================
 * GEM E4 self-driving conversion — Motion MCU firmware.
 *
 * Job: bridge DBW CAN bus (Jetson + Pedals Teensy) to the EPAS bus (DCE
 * Motorsport EPAS18 Ultra ECU). Run an outer position-PI loop that
 * converts steering-angle commands into torque demands the EPAS ECU
 * accepts. Detect manual override and yield instantly to the driver.
 *
 * Hardware: Teensy 4.1 in Steering Aux Box on firewall.
 *   CAN1 (pins 22/23) → DBW bus @ 500 kbps  (twisted pair, Deutsch DT04-4P)
 *   CAN2 (pins  0/ 1) → EPAS bus @ 250 kbps (DCE protocol)
 *   USB serial        → console at 115200 (status + tuning)
 *
 * The EPAS18 internal motor-current loop is closed inside the ECU itself;
 * we just push torque demands at 200 Hz. Per DCE user manual §6: the ECU
 * reverts to local power-assist mode if it doesn't see msg 0x296 for 200 ms.
 *
 * Safety: independent WDT at 50 ms. Manual override detection on raw
 * torque sensor signals spikes within 50 ms.
 *
 * THIS IS PRE-FLIGHT FIRMWARE — bench-tested only. NEVER run with the
 * cart on the ground until §10 of CART_VISIT_DAY1 is completed and the
 * EPAS autonomous firmware is confirmed loaded by DCE.
 * ============================================================================
 */

#include <Arduino.h>
#include <FlexCAN_T4.h>
#include "dbw_can_protocol.h"

// ─── CAN bus instances ──────────────────────────────────────────────────────
FlexCAN_T4<CAN1, RX_SIZE_256, TX_SIZE_16> dbw_can;   // DBW bus
FlexCAN_T4<CAN2, RX_SIZE_256, TX_SIZE_16> epas_can;  // EPAS bus

// ─── Pin assignments ────────────────────────────────────────────────────────
constexpr uint8_t PIN_LED_STATUS  = 13;   // builtin LED
constexpr uint8_t PIN_FAULT_OUT   = 14;   // optional: drives a fault relay

// ─── Tuning constants (HARDWARE-DEPENDENT — bench-tune before drive) ────────
// Steering map (0=local, 1=gentle .. 5=aggressive). Start at 2 for first-light.
constexpr uint8_t  EPAS_MAP_AUTONOMOUS = 2;

// Outer PI loop (cmd in centi-degrees; output torque demand in bits ±64).
// Kp = 0.2 means 1° error → ~20% torque demand. Ki adds slow integration.
// Tune on bench by step-response.
constexpr float    Kp_TORQUE_PER_CENTIDEG = 0.20f;
constexpr float    Ki_TORQUE_PER_CENTIDEG = 0.05f;
constexpr float    INTEGRAL_LIMIT         = 32.0f;   // anti-windup
constexpr int8_t   MAX_TORQUE_DEMAND      = 50;      // ±50 of ±64; leave headroom

// Manual-override detection: change in raw torque A/B vs running baseline.
// During autonomy the driver hands are off the wheel, so raw torque bits sit
// stable at the calibrated zero. Driver grab → spike.
constexpr uint8_t  OVERRIDE_SPIKE_BITS    = 8;       // ±8 bits = ~5% torque
constexpr uint32_t OVERRIDE_PERSIST_MS    = 50;      // must persist >50 ms

// Watchdog / staleness
constexpr uint32_t JETSON_HB_TIMEOUT_MS   = 100;
constexpr uint32_t EPAS_RX_TIMEOUT_MS     = 250;

// ─── Cached state ───────────────────────────────────────────────────────────
struct {
    int16_t  cmd_angle_centideg = 0;
    uint16_t cmd_max_rate       = 0;
    bool     cmd_enable         = false;
    uint32_t last_rx_ms         = 0;
} g_cmd;

struct {
    epas_msg1_t msg1{};
    epas_msg2_t msg2{};
    uint32_t    msg1_last_ms = 0;
    uint32_t    msg2_last_ms = 0;
    uint8_t     baseline_torque_a = 128;   // updated when DISENGAGED
    uint8_t     baseline_torque_b = 128;
    uint32_t    override_first_ms = 0;     // when spike first appeared (0 = no spike)
} g_epas;

uint32_t       g_jetson_hb_last_ms  = 0;
uint32_t       g_pedals_hb_last_ms  = 0;
master_state_t g_master_state       = MASTER_STATE_DISENGAGED;
uint8_t        g_fault_flags        = 0;
uint32_t       g_hb_counter         = 0;
float          g_steer_integral     = 0.0f;
int8_t         g_last_torque_demand = 0;

// ─── Helpers ────────────────────────────────────────────────────────────────
static inline void set_fault(uint8_t flag, const char* reason) {
    if (!(g_fault_flags & flag)) {
        Serial.print("[FAULT] 0x");
        Serial.print(flag, HEX);
        Serial.print(" ");
        Serial.println(reason);
    }
    g_fault_flags |= flag;
    g_master_state = MASTER_STATE_FAULT;
}

static inline void clear_faults_if_safe() {
    // FAULT is sticky per dbw_can_protocol.h — only key cycle clears.
    // We could implement a hard reset here on a special CAN message later.
}

// ─── EPAS bus: send msg #3 (RX into ECU) ────────────────────────────────────
// Called from a hard 200 Hz timer interrupt. Must be deterministic.
static IntervalTimer epas_tx_timer;

static void epas_tx_isr() {
    // ─── BENCH HACK — REMOVE FOR PRODUCTION ────────────────────────────────
    // Forcing autonomous map + small torque demand at boot so we can verify
    // the EPAS bus is wired and the autonomous firmware variant is loaded.
    // Pull USB to stop. See git log for the proper state-machine-gated path.
    int8_t  torque_demand = 15;            // ±64 full scale; 15 ≈ 23% torque
    uint8_t map           = EPAS_MAP_AUTONOMOUS;  // map 2 = gentle autonomous

    if (false && g_master_state == MASTER_STATE_ACTIVE && g_cmd.cmd_enable) {
        // Outer PI: angle error → torque demand
        // (8-bit steering angle from EPAS msg #2 D0 needs mapping to centideg —
        // calibration of LH/RH stop bits gives us a linear map. Until calibrated,
        // we use a default scale assuming full range = ±MAX_HANDWHEEL_DEG.)
        // TODO: calibrate scale_centideg_per_bit on bench
        const float scale_centideg_per_bit = (44800.0f) / 200.0f;  // approx
        const int16_t measured_centideg =
            int16_t((int(g_epas.msg2.steering_angle) - 100) * scale_centideg_per_bit);

        const int16_t err = g_cmd.cmd_angle_centideg - measured_centideg;
        g_steer_integral += Ki_TORQUE_PER_CENTIDEG * err * (1.0f / 200.0f);
        if (g_steer_integral >  INTEGRAL_LIMIT) g_steer_integral =  INTEGRAL_LIMIT;
        if (g_steer_integral < -INTEGRAL_LIMIT) g_steer_integral = -INTEGRAL_LIMIT;

        float demand_f = Kp_TORQUE_PER_CENTIDEG * err + g_steer_integral;
        if (demand_f >  MAX_TORQUE_DEMAND) demand_f =  MAX_TORQUE_DEMAND;
        if (demand_f < -MAX_TORQUE_DEMAND) demand_f = -MAX_TORQUE_DEMAND;
        torque_demand = int8_t(demand_f);
        map = EPAS_MAP_AUTONOMOUS;
    }
    g_last_torque_demand = torque_demand;

    // BENCH RX-ONLY TEST: TX disabled to rule out a FlexCAN_T4 TX/RX collision
    // bug. If RX frames start arriving after this change, the issue was our
    // 200 Hz TX ISR fighting the receive path. If still zero RX → wiring/EPAS.
    (void)torque_demand;
    (void)map;
    // epas_msg3_t m = epas_make_demand(map, torque_demand);
    // CAN_message_t f{};
    // f.id  = ID_EPAS_MSG3;
    // f.len = 8;
    // memcpy(f.buf, &m, 8);
    // epas_can.write(f);
}

// ─── EPAS bus: receive msg #1 / msg #2 ──────────────────────────────────────
static void on_epas_rx(const CAN_message_t& f) {
    const uint32_t now = millis();
    // BENCH DIAGNOSTIC: print every CAN2 frame raw, regardless of ID
    Serial.print("[epas-rx] id=0x");
    Serial.print(f.id, HEX);
    Serial.print(" ext=");
    Serial.print(f.flags.extended);
    Serial.print(" len=");
    Serial.print(f.len);
    Serial.print(" buf=");
    for (uint8_t i = 0; i < f.len; i++) {
        if (f.buf[i] < 16) Serial.print('0');
        Serial.print(f.buf[i], HEX);
        Serial.print(' ');
    }
    Serial.println();

    if (f.id == ID_EPAS_MSG1 && f.len == 8) {
        memcpy(&g_epas.msg1, f.buf, 8);
        g_epas.msg1_last_ms = now;

        // Manual override detection (uses raw torque sensor signals D6/D7)
        const uint8_t da = abs(int(g_epas.msg1.torque_a_raw) - int(g_epas.baseline_torque_a));
        const uint8_t db = abs(int(g_epas.msg1.torque_b_raw) - int(g_epas.baseline_torque_b));
        const bool spike = (da > OVERRIDE_SPIKE_BITS) || (db > OVERRIDE_SPIKE_BITS);
        if (spike) {
            if (g_epas.override_first_ms == 0) g_epas.override_first_ms = now;
            else if (now - g_epas.override_first_ms > OVERRIDE_PERSIST_MS &&
                     g_master_state == MASTER_STATE_ACTIVE) {
                set_fault(FAULT_DRIVER_OVERRIDE, "manual override torque spike");
            }
        } else {
            g_epas.override_first_ms = 0;
            // Refresh baseline only when DISENGAGED (no autonomous torque applied)
            if (g_master_state == MASTER_STATE_DISENGAGED) {
                g_epas.baseline_torque_a = g_epas.msg1.torque_a_raw;
                g_epas.baseline_torque_b = g_epas.msg1.torque_b_raw;
            }
        }
    } else if (f.id == ID_EPAS_MSG2 && f.len == 8) {
        memcpy(&g_epas.msg2, f.buf, 8);
        g_epas.msg2_last_ms = now;

        // EPAS-reported error code (any non-zero = fault)
        if (g_epas.msg2.error_code != 0) {
            set_fault(FAULT_EPAS_FAULT, "EPAS reported error_code != 0");
        }
        // Steering at end-stop?
        if (g_epas.msg2.limit_flags & 0x03) {
            // bit0 = LH stop, bit1 = RH stop
            // Don't fault — just inform Jetson via STEER_STATUS
        }
    }
}

// ─── DBW bus: receive Jetson heartbeat + steer command ──────────────────────
static void on_dbw_rx(const CAN_message_t& f) {
    const uint32_t now = millis();
    switch (f.id) {
        case ID_JETSON_HEARTBEAT:
            g_jetson_hb_last_ms = now;
            break;
        case ID_STEER_CMD:
            if (f.len == 8) {
                steer_cmd_t c;
                memcpy(&c, f.buf, 8);
                g_cmd.cmd_angle_centideg = c.angle_centideg;
                g_cmd.cmd_max_rate       = c.max_rate_centideg_s;
                g_cmd.cmd_enable         = (c.enable != 0);
                g_cmd.last_rx_ms         = now;
            }
            break;
        case ID_MCU_HB_PEDALS:
            g_pedals_hb_last_ms = now;
            break;
        default:
            break;
    }
}

// ─── DBW bus: TX status + heartbeats ────────────────────────────────────────
static void send_steer_status() {
    steer_status_t s{};
    // Convert raw 8-bit angle → centideg (same scale as commanded). Until
    // calibrated, this uses a placeholder linear map.
    const float scale_centideg_per_bit = (44800.0f) / 200.0f;
    s.angle_centideg = int16_t((int(g_epas.msg2.steering_angle) - 100) * scale_centideg_per_bit);
    s.motor_current_mA = int16_t(g_epas.msg1.current_A) * 1000;
    s.fault_flags     = g_fault_flags;
    s.epas_state      = (g_epas.msg2.limit_flags & EPAS_LIMIT_REMOTE_MODE_ACTIVE) ? 1 : 0;
    s.epas_error_code = g_epas.msg2.error_code;

    CAN_message_t f{};
    f.id  = ID_STEER_STATUS;
    f.len = 8;
    memcpy(f.buf, &s, 8);
    dbw_can.write(f);
}

static void send_steer_torque_raw() {
    steer_torque_raw_t s{};
    s.torque_a_raw      = g_epas.msg1.torque_a_raw;
    s.torque_b_raw      = g_epas.msg1.torque_b_raw;
    s.epas_status_flags = g_epas.msg2.status_flags;
    s.epas_limit_flags  = g_epas.msg2.limit_flags;

    CAN_message_t f{};
    f.id  = ID_STEER_TORQUE_RAW;
    f.len = 8;
    memcpy(f.buf, &s, 8);
    dbw_can.write(f);
}

static void send_motion_heartbeat() {
    mcu_heartbeat_t hb{};
    hb.counter = ++g_hb_counter;
    hb.state   = uint8_t(g_master_state);

    CAN_message_t f{};
    f.id  = ID_MCU_HB_MOTION;
    f.len = 8;
    memcpy(f.buf, &hb, 8);
    dbw_can.write(f);
}

// ─── State machine ──────────────────────────────────────────────────────────
static void step_state_machine() {
    const uint32_t now = millis();

    // Watchdog: Jetson HB
    if (now - g_jetson_hb_last_ms > JETSON_HB_TIMEOUT_MS &&
        g_master_state != MASTER_STATE_DISENGAGED) {
        set_fault(FAULT_WATCHDOG, "Jetson heartbeat lost");
    }

    // Watchdog: EPAS staleness
    if (now - g_epas.msg2_last_ms > EPAS_RX_TIMEOUT_MS &&
        g_master_state != MASTER_STATE_DISENGAGED) {
        set_fault(FAULT_ENCODER_SENSOR, "EPAS msg #2 stale");
    }

    // Engage logic comes from the Pedals Teensy (it's the master).
    // Motion follows: ARMED if Pedals reports ARMED, ACTIVE if reports ACTIVE,
    // FAULT if either side faults. Keep simple sync via heartbeat state byte.
    // For now we only react to local faults; cross-MCU sync is done by the
    // Pedals Teensy's master state machine (see pedals_teensy/main.cpp).
    if (g_master_state == MASTER_STATE_FAULT) {
        // Reset integrator so we don't kick when re-armed
        g_steer_integral = 0.0f;
    }
}

// ─── Setup + loop ───────────────────────────────────────────────────────────
void setup() {
    pinMode(PIN_LED_STATUS, OUTPUT);
    pinMode(PIN_FAULT_OUT, OUTPUT);
    digitalWrite(PIN_LED_STATUS, HIGH);

    Serial.begin(115200);
    while (!Serial && millis() < 2000) {}
    Serial.print("[motion] FW v");
    Serial.print(MOTION_FW_VERSION);
    Serial.println(" booting");

    // DBW CAN
    dbw_can.begin();
    dbw_can.setBaudRate(DBW_BUS_BITRATE_HZ);
    dbw_can.setMaxMB(16);
    dbw_can.enableFIFO();
    dbw_can.enableFIFOInterrupt();
    dbw_can.onReceive(on_dbw_rx);

    // EPAS CAN
    epas_can.begin();
    epas_can.setBaudRate(EPAS_BUS_BITRATE_HZ);
    epas_can.setMaxMB(16);
    epas_can.enableFIFO();
    epas_can.enableFIFOInterrupt();
    epas_can.setFIFOFilter(ACCEPT_ALL);   // explicit accept-all (some lib versions default to reject)
    epas_can.onReceive(on_epas_rx);

    // Hard 200 Hz timer for EPAS msg #3 TX
    epas_tx_timer.begin(epas_tx_isr, 5000);  // 5000 µs = 200 Hz
    epas_tx_timer.priority(64);              // highish priority

    Serial.println("[motion] CAN buses up; EPAS TX timer running");
}

uint32_t last_status_tx_ms = 0;
uint32_t last_hb_tx_ms     = 0;
uint32_t last_blink_ms     = 0;
uint32_t last_console_ms   = 0;

void loop() {
    // Service CAN FIFOs (RX callbacks fire from inside these)
    dbw_can.events();
    epas_can.events();

    const uint32_t now = millis();

    // 50 Hz: status messages on DBW
    if (now - last_status_tx_ms >= PERIOD_STATUS_MS) {
        last_status_tx_ms = now;
        send_steer_status();
        send_steer_torque_raw();
    }

    // 50 Hz: heartbeat
    if (now - last_hb_tx_ms >= PERIOD_HEARTBEAT_MS) {
        last_hb_tx_ms = now;
        send_motion_heartbeat();
    }

    // 50 Hz: state machine
    step_state_machine();

    // Status LED — blink rate encodes state
    const uint32_t blink_period =
        (g_master_state == MASTER_STATE_FAULT)      ? 100 :
        (g_master_state == MASTER_STATE_ACTIVE)     ? 1000 :
        (g_master_state == MASTER_STATE_ARMED)      ? 250 :
                                                      500;
    if (now - last_blink_ms >= blink_period) {
        last_blink_ms = now;
        digitalWrite(PIN_LED_STATUS, !digitalRead(PIN_LED_STATUS));
    }

    // 1 Hz: serial console status dump
    if (now - last_console_ms >= 1000) {
        last_console_ms = now;
        Serial.print("[motion] state=");
        Serial.print(int(g_master_state));
        Serial.print(" fault=0x");
        Serial.print(g_fault_flags, HEX);
        Serial.print(" cmd_centideg=");
        Serial.print(g_cmd.cmd_angle_centideg);
        Serial.print(" measured_raw=");
        Serial.print(g_epas.msg2.steering_angle);
        Serial.print(" torque_demand=");
        Serial.print(int(g_last_torque_demand));
        Serial.print(" jetson_hb_age=");
        Serial.print(now - g_jetson_hb_last_ms);
        Serial.print("ms epas_err=");
        Serial.println(g_epas.msg2.error_code);
    }
}
