/*
 * pedals_teensy/src/main.cpp
 * ============================================================================
 * GEM E4 self-driving conversion — Pedals MCU firmware.
 *
 * Job: throttle DAC bypass, Kartech 1A001HAJ J1939 brake actuator,
 * master state machine (DISENGAGED/ARMED/ACTIVE/FAULT), E-stop /
 * brake-pedal / wheel-touch monitoring, read-only J1939 sniffer of
 * the GEM internal CAN bus.
 *
 * Hardware: Teensy 4.1 in Pedals Aux Box on firewall above pedals.
 *   CAN1 (pins 22/23) → DBW bus            @ 500 kbps, 11-bit IDs
 *                       Transceiver: SN65HVD230 (3.3 V)
 *                       Peers: Jetson + Motion Teensy
 *   CAN2 (pins  0/ 1) → GEM J1939 bus      @ 250 kbps, 29-bit, READ-ONLY
 *                       Transceiver: ISO1042 (TX permanently grounded —
 *                       hardware-enforced sniffer; firmware NEVER TX here)
 *   CAN3 (pins 30/31) → Kartech J1939 bus  @ 250 kbps, 29-bit, bidirectional
 *                       Transceiver: SN65HVD230
 *                       Dedicated isolated bus to the Kartech 1A001HAJ
 *                       (see kartech_brake.h and reference_kartech_brake.md)
 *   I²C0 (pins 18/19) → 2× MCP4725 DACs @ 0x60 / 0x61 (throttle pair)
 *   GPIO              → DPDT relay coil drive, dash buttons, ESTOP loop sense,
 *                       brake-light optoisolator, MPR121 wheel-touch
 *
 * Safety: independent WDT 50 ms. Jetson HB lost or any local fault → FAULT.
 *
 * THIS IS PRE-FLIGHT FIRMWARE — bench-test EVERYTHING before installing on
 * the cart. The throttle DAC mirroring MUST be measured against the actual
 * pedal sweep (CART_VISIT_DAY1 §4); without that calibration the traction
 * controller will fault.
 * ============================================================================
 */

#include <Arduino.h>
#include <Wire.h>
#include <FlexCAN_T4.h>
#include <Adafruit_MCP4725.h>
#include "dbw_can_protocol.h"
#include "kartech_brake.h"

// ─── CAN ────────────────────────────────────────────────────────────────────
FlexCAN_T4<CAN1, RX_SIZE_256, TX_SIZE_16> dbw_can;      // DBW bus (Jetson+Motion)
FlexCAN_T4<CAN2, RX_SIZE_256, TX_SIZE_16> j1939_can;    // GEM internal J1939 (RX-only)
FlexCAN_T4<CAN3, RX_SIZE_256, TX_SIZE_16> kartech_can;  // Kartech 1A001HAJ brake bus

// ─── DACs ───────────────────────────────────────────────────────────────────
Adafruit_MCP4725 dac1;   // throttle channel A
Adafruit_MCP4725 dac2;   // throttle channel B (mirror)

// ─── Pin assignments ────────────────────────────────────────────────────────
constexpr uint8_t PIN_LED_STATUS    = 13;
constexpr uint8_t PIN_RELAY_COIL    = 2;   // DPDT throttle bypass (energize → DAC out)
constexpr uint8_t PIN_BTN_ARM       = 3;   // dash ARM (active LOW, internal pullup)
constexpr uint8_t PIN_BTN_ENGAGE    = 4;   // dash ENGAGE (active LOW)
constexpr uint8_t PIN_BTN_DISENG    = 5;   // dash DISENGAGE (active LOW)
constexpr uint8_t PIN_ESTOP_SENSE   = 6;   // E-stop loop sense (HIGH = loop closed/OK)
constexpr uint8_t PIN_BRAKE_PEDAL   = 7;   // optoiso from GEM brake light switch
constexpr uint8_t PIN_WHEEL_TOUCH   = 8;   // MPR121 IRQ (active LOW on touch)
// pins 9, 10, A0 freed by Kartech transition (formerly BTS7960 PWM + pot ADC).
// CAN3 (pins 30/31) is now used for the Kartech J1939 bus instead.

// ─── Throttle calibration (CART_VISIT_DAY1 §4 — TUNE BEFORE FLIGHT) ─────────
// At pedal rest: V1 ≈ 0.8 V, V2 ≈ 4.2 V (CTS-style mirrored Hall pair)
// At pedal full: V1 ≈ 4.2 V, V2 ≈ 0.8 V
// MCP4725 outputs 0..VDD (5V). The op-amp buffer presents 1 kΩ source to controller.
// Convert V → 12-bit DAC code: code = round(V/5.0 * 4095)
constexpr float DAC_VREF_V             = 5.0f;
constexpr float V_REST_V1              = 0.8f;
constexpr float V_FULL_V1              = 4.2f;
constexpr float V_REST_V2              = 4.2f;
constexpr float V_FULL_V2              = 0.8f;

static inline uint16_t volts_to_code(float v) {
    if (v < 0) v = 0;
    if (v > DAC_VREF_V) v = DAC_VREF_V;
    return uint16_t(v / DAC_VREF_V * 4095.0f + 0.5f);
}

static void set_throttle_dacs(uint16_t throttle_permil) {
    if (throttle_permil > 1000) throttle_permil = 1000;
    const float t = throttle_permil / 1000.0f;
    const float v1 = V_REST_V1 + (V_FULL_V1 - V_REST_V1) * t;
    const float v2 = V_REST_V2 + (V_FULL_V2 - V_REST_V2) * t;
    dac1.setVoltage(volts_to_code(v1), false);
    dac2.setVoltage(volts_to_code(v2), false);
}

// ─── J1939 sniffer (read-only) ──────────────────────────────────────────────
// PGN dictionary recovered from 2020 team's PGN Data.docx (see memory:
// reference_gem_e4_j1939_pgns.md). Re-verify byte positions on the actual
// 2018 cart via candump — firmware revisions may shift bit positions.
struct J1939State {
    uint16_t speed_mph_x100  = 0;   // PGN 65265 byte 4
    uint8_t  gear            = 0;   // 0=N, 1=F, 2=R, 3=Charging — PGN 61445 byte 6 decoded
    uint16_t voltage_x10     = 0;   // PGN 61444 byte 4
    uint32_t last_speed_ms   = 0;
    uint32_t last_gear_ms    = 0;
    uint32_t last_voltage_ms = 0;
};
J1939State g_j1939;

// Decode PGN from extended J1939 ID (29-bit). PGN sits in bits 8..25 of the ID.
static inline uint32_t pgn_from_can_id(uint32_t can_id_29bit) {
    const uint8_t pdu_format    = (can_id_29bit >> 16) & 0xFF;
    const uint8_t pdu_specific  = (can_id_29bit >>  8) & 0xFF;
    if (pdu_format < 240) {
        // PDU1 — destination-specific. PGN = pdu_format << 8 (specific is dest)
        return uint32_t(pdu_format) << 8;
    } else {
        // PDU2 — broadcast. PGN = pdu_format << 8 | pdu_specific
        return (uint32_t(pdu_format) << 8) | pdu_specific;
    }
}

static void on_j1939_rx(const CAN_message_t& f) {
    if (!(f.flags.extended)) return;     // J1939 is always 29-bit
    const uint32_t pgn = pgn_from_can_id(f.id);
    const uint32_t now = millis();
    switch (pgn) {
        case 65265:  // CCVS1: cruise control / vehicle speed
            // byte 4 → speed in mph (per 2020 team's notes); convert ×100 for x100 unit
            g_j1939.speed_mph_x100 = uint16_t(f.buf[3]) * 100;
            g_j1939.last_speed_ms  = now;
            break;
        case 61445:  // ETC2: gear position (byte 6)
            // 70=Forward, 78=Neutral, 67=Charging, 255=Reverse
            switch (f.buf[5]) {
                case 70:  g_j1939.gear = uint8_t(GEAR_FORWARD);  break;
                case 78:  g_j1939.gear = uint8_t(GEAR_NEUTRAL);  break;
                case 67:  g_j1939.gear = uint8_t(GEAR_CHARGING); break;
                case 255: g_j1939.gear = uint8_t(GEAR_REVERSE);  break;
                default:  break;
            }
            g_j1939.last_gear_ms = now;
            break;
        case 61444:  // EEC1: voltage in byte 4 (per 2020 notes — verify)
            g_j1939.voltage_x10 = uint16_t(f.buf[3]) * 10;
            g_j1939.last_voltage_ms = now;
            break;
        default:
            break;
    }
}

// ─── DBW state ──────────────────────────────────────────────────────────────
struct {
    uint16_t throttle_permil = 0;
    bool     enable          = false;
    uint32_t last_rx_ms      = 0;
} g_thr;

struct {
    uint16_t brake_permil    = 0;
    bool     enable          = false;
    uint32_t last_rx_ms      = 0;
} g_brk;

uint32_t       g_jetson_hb_last_ms = 0;
uint32_t       g_motion_hb_last_ms = 0;
master_state_t g_master_state      = MASTER_STATE_DISENGAGED;
uint8_t        g_fault_flags       = 0;
uint32_t       g_hb_counter        = 0;

static constexpr uint32_t JETSON_HB_TIMEOUT_MS = WATCHDOG_TIMEOUT_MS;

// ─── Bench serial overrides (BENCH ONLY — bypasses DBW + state machine) ─────
// -1 = no override, 0..1000 = forced value in permil. When active, drive_outputs()
// uses these instead of the values latched from /dbw/cmd. Cleared by 'x' command
// or by disengage(). Throttle override also forces the relay ON.
int16_t g_serial_brake_override    = -1;
int16_t g_serial_throttle_override = -1;

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

// ─── DBW bus: receive ───────────────────────────────────────────────────────
static void on_dbw_rx(const CAN_message_t& f) {
    const uint32_t now = millis();
    switch (f.id) {
        case ID_JETSON_HEARTBEAT:
            g_jetson_hb_last_ms = now;
            break;
        case ID_THROTTLE_CMD:
            if (f.len == 8) {
                throttle_cmd_t c;
                memcpy(&c, f.buf, 8);
                g_thr.throttle_permil = c.throttle_permil;
                g_thr.enable          = (c.enable != 0);
                g_thr.last_rx_ms      = now;
            }
            break;
        case ID_BRAKE_CMD:
            if (f.len == 8) {
                brake_cmd_t c;
                memcpy(&c, f.buf, 8);
                g_brk.brake_permil = c.brake_permil;
                g_brk.enable       = (c.enable != 0);
                g_brk.last_rx_ms   = now;
            }
            break;
        case ID_MCU_HB_MOTION:
            g_motion_hb_last_ms = now;
            break;
        default:
            break;
    }
}

// ─── DBW bus: TX ────────────────────────────────────────────────────────────
static void send_throttle_status(uint16_t v1_mV, uint16_t v2_mV, bool relay_on) {
    throttle_status_t s{};
    s.dac1_mV     = v1_mV;
    s.dac2_mV     = v2_mV;
    s.relay_state = relay_on ? 1 : 0;
    s.fault_flags = g_fault_flags;

    CAN_message_t f{};
    f.id  = ID_THROTTLE_STATUS;
    f.len = 8;
    memcpy(f.buf, &s, 8);
    dbw_can.write(f);
}

static void send_brake_status(uint16_t pos_mm_x10, uint16_t current_mA) {
    brake_status_t s{};
    s.actuator_pos_mm_x10  = pos_mm_x10;
    s.actuator_current_mA  = current_mA;
    s.fault_flags          = g_fault_flags;

    CAN_message_t f{};
    f.id  = ID_BRAKE_STATUS;
    f.len = 8;
    memcpy(f.buf, &s, 8);
    dbw_can.write(f);
}

static void send_estop_state(bool estop_loop_ok, bool brake_pedal_pressed,
                              bool wheel_touched, uint8_t dash_switch_bits) {
    estop_state_t s{};
    s.estop_loop            = estop_loop_ok ? 1 : 0;
    s.brake_pedal           = brake_pedal_pressed ? 1 : 0;
    s.wheel_torque_override = wheel_touched ? 1 : 0;
    s.dash_switch           = dash_switch_bits;
    s.master_state          = uint8_t(g_master_state);

    CAN_message_t f{};
    f.id  = ID_ESTOP_STATE;
    f.len = 8;
    memcpy(f.buf, &s, 8);
    dbw_can.write(f);
}

static void send_pedals_heartbeat() {
    mcu_heartbeat_t hb{};
    hb.counter = ++g_hb_counter;
    hb.state   = uint8_t(g_master_state);

    CAN_message_t f{};
    f.id  = ID_MCU_HB_PEDALS;
    f.len = 8;
    memcpy(f.buf, &hb, 8);
    dbw_can.write(f);
}

static void send_vehicle_state() {
    vehicle_state_t s{};
    s.speed_mph_x100      = g_j1939.speed_mph_x100;
    s.gear                = g_j1939.gear;
    s.traction_voltage_x10 = g_j1939.voltage_x10;
    const uint32_t now = millis();
    const bool fresh = (now - g_j1939.last_speed_ms < 500);
    s.j1939_link_state = fresh ? 1 : 2;   // 0=down 1=up 2=stale

    CAN_message_t f{};
    f.id  = ID_VEHICLE_STATE;
    f.len = 8;
    memcpy(f.buf, &s, 8);
    dbw_can.write(f);
}

// ─── State machine ──────────────────────────────────────────────────────────
struct ButtonEdge {
    uint8_t pin;
    bool last;
    bool pressed_now() {
        bool now = (digitalRead(pin) == LOW);
        bool edge = (now && !last);
        last = now;
        return edge;
    }
};
ButtonEdge btn_arm    {PIN_BTN_ARM, false};
ButtonEdge btn_engage {PIN_BTN_ENGAGE, false};
ButtonEdge btn_diseng {PIN_BTN_DISENG, false};

static void try_arm() {
    if (g_master_state != MASTER_STATE_DISENGAGED) return;
    if (g_fault_flags != 0) {
        Serial.print("[arm-blocked] fault_flags=0x");
        Serial.println(g_fault_flags, HEX);
        return;
    }
    if (digitalRead(PIN_BRAKE_PEDAL) == HIGH) {
        Serial.println("[arm-blocked] brake pedal pressed");
        return;
    }
    if (digitalRead(PIN_ESTOP_SENSE) == LOW) {
        Serial.println("[arm-blocked] E-stop loop open");
        return;
    }
    Serial.println("[state] DISENGAGED → ARMED");
    g_master_state = MASTER_STATE_ARMED;
}

static void try_engage() {
    if (g_master_state != MASTER_STATE_ARMED) return;
    const uint32_t now = millis();
    if (now - g_jetson_hb_last_ms > JETSON_HB_TIMEOUT_MS) {
        Serial.println("[engage-blocked] no Jetson HB");
        return;
    }
    if (now - g_motion_hb_last_ms > JETSON_HB_TIMEOUT_MS) {
        Serial.println("[engage-blocked] no Motion Teensy HB");
        return;
    }
    Serial.println("[state] ARMED → ACTIVE");
    g_master_state = MASTER_STATE_ACTIVE;
}

static void disengage(const char* reason) {
    if (g_master_state == MASTER_STATE_DISENGAGED) return;
    Serial.print("[state] → DISENGAGED (");
    Serial.print(reason);
    Serial.println(")");
    g_master_state = MASTER_STATE_DISENGAGED;
}

static void step_state_machine() {
    const uint32_t now = millis();

    // E-stop loop: if open, drop EVERYTHING immediately
    if (digitalRead(PIN_ESTOP_SENSE) == LOW) {
        if (!(g_fault_flags & FAULT_HW_ESTOP)) {
            set_fault(FAULT_HW_ESTOP, "hardware E-stop loop open");
        }
    }

    // Brake pedal pressed → DISENGAGE (latched until re-arm; not sticky FAULT)
    if (digitalRead(PIN_BRAKE_PEDAL) == HIGH && g_master_state == MASTER_STATE_ACTIVE) {
        disengage("brake pedal pressed");
    }

    // Wheel touch → DISENGAGE (cap-touch is NOISY; debounce in real install)
    if (digitalRead(PIN_WHEEL_TOUCH) == LOW && g_master_state == MASTER_STATE_ACTIVE) {
        disengage("wheel touched");
    }

    // Watchdogs
    if (g_master_state == MASTER_STATE_ACTIVE) {
        if (now - g_jetson_hb_last_ms > JETSON_HB_TIMEOUT_MS) {
            set_fault(FAULT_WATCHDOG, "Jetson HB lost");
        }
        if (now - g_motion_hb_last_ms > JETSON_HB_TIMEOUT_MS) {
            set_fault(FAULT_WATCHDOG, "Motion Teensy HB lost");
        }
    }

    // Button edges
    if (btn_arm.pressed_now())     try_arm();
    if (btn_engage.pressed_now())  try_engage();
    if (btn_diseng.pressed_now())  disengage("DISENGAGE button");
}

// ─── Serial command interface (bench testing) ──────────────────────────────
// Type any of (newline-terminated):
//   b NN         brake 0..100 % (e.g. "b 50")
//   t NN         throttle 0..100 % (forces relay ON, bypasses state machine)
//   pos NNNN     Kartech raw 14-bit position 0..16383
//   demand NN    Kartech raw 0..255 demand byte (2020 RPi-API equivalent)
//   clutch on    send kartech::clutch_on frame once
//   clutch off   send kartech::clutch_off frame once
//   full         send kartech::brake_full preset once
//   release      send kartech::release_to_stock preset once
//   s            print full status snapshot
//   x            clear all serial overrides
//   ?            print this help

static void print_serial_help() {
    Serial.println(F("=== Bench Serial Commands (BENCH ONLY) ==="));
    Serial.println(F("  b NN         brake 0..100 %"));
    Serial.println(F("  t NN         throttle 0..100 % (forces relay ON)"));
    Serial.println(F("  pos NNNN     Kartech raw position 0..16383"));
    Serial.println(F("  demand NN    Kartech raw demand 0..255"));
    Serial.println(F("  clutch on    clutch_on frame"));
    Serial.println(F("  clutch off   clutch_off frame"));
    Serial.println(F("  full         brake_full preset"));
    Serial.println(F("  release      release_to_stock preset"));
    Serial.println(F("  s            status snapshot"));
    Serial.println(F("  x            clear all overrides"));
    Serial.println(F("  ?            this help"));
    Serial.println(F("=========================================="));
}

static void process_serial() {
    static char buf[64];
    static uint8_t len = 0;
    while (Serial.available()) {
        const char c = (char)Serial.read();
        if (c == '\r') continue;
        if (c != '\n' && len < sizeof(buf) - 1) { buf[len++] = c; continue; }
        buf[len] = 0;
        len = 0;

        char* p = buf;
        while (*p == ' ' || *p == '\t') p++;
        if (*p == 0) continue;

        if (p[0] == '?') {
            print_serial_help();
        } else if (p[0] == 'x' || p[0] == 'X') {
            g_serial_brake_override    = -1;
            g_serial_throttle_override = -1;
            Serial.println(F("[serial] overrides cleared"));
        } else if (p[0] == 's' && (p[1] == 0 || p[1] == ' ')) {
            Serial.print(F("state=")); Serial.print(int(g_master_state));
            Serial.print(F(" fault=0x")); Serial.print(g_fault_flags, HEX);
            Serial.print(F(" thr_dbw=")); Serial.print(g_thr.throttle_permil);
            Serial.print(F(" thr_ovr=")); Serial.print(g_serial_throttle_override);
            Serial.print(F(" brk_dbw=")); Serial.print(g_brk.brake_permil);
            Serial.print(F(" brk_ovr=")); Serial.print(g_serial_brake_override);
            Serial.print(F(" relay="));   Serial.println(digitalRead(PIN_RELAY_COIL));
        } else if (p[0] == 'b' && (p[1] == ' ' || p[1] == 0)) {
            int v = atoi(p + 1);
            if (v < 0) v = 0; if (v > 100) v = 100;
            g_serial_brake_override = int16_t(v * 10);  // % → permil
            Serial.print(F("[serial] brake -> ")); Serial.print(v); Serial.println(F("%"));
        } else if (p[0] == 't' && (p[1] == ' ' || p[1] == 0)) {
            int v = atoi(p + 1);
            if (v < 0) v = 0; if (v > 100) v = 100;
            g_serial_throttle_override = int16_t(v * 10);
            Serial.print(F("[serial] throttle -> ")); Serial.print(v); Serial.println(F("% (relay forced ON)"));
        } else if (strncmp(p, "pos", 3) == 0) {
            int v = atoi(p + 3);
            if (v < 0) v = 0; if (v > 0x3FFF) v = 0x3FFF;
            kartech::send_position_14bit(kartech_can, (uint16_t)v);
            Serial.print(F("[serial] kartech pos -> ")); Serial.println(v);
        } else if (strncmp(p, "demand", 6) == 0) {
            int v = atoi(p + 6);
            if (v < 0) v = 0; if (v > 255) v = 255;
            kartech::send_demand_byte(kartech_can, (uint8_t)v);
            Serial.print(F("[serial] kartech demand -> ")); Serial.println(v);
        } else if (strncmp(p, "clutch on", 9) == 0) {
            kartech::clutch_on(kartech_can);
            Serial.println(F("[serial] kartech clutch_on"));
        } else if (strncmp(p, "clutch off", 10) == 0) {
            kartech::clutch_off(kartech_can);
            Serial.println(F("[serial] kartech clutch_off"));
        } else if (strncmp(p, "full", 4) == 0) {
            kartech::brake_full(kartech_can);
            Serial.println(F("[serial] kartech brake_full"));
        } else if (strncmp(p, "release", 7) == 0) {
            kartech::release_to_stock(kartech_can);
            Serial.println(F("[serial] kartech release_to_stock"));
        } else {
            Serial.print(F("[serial] ? unknown: ")); Serial.println(p);
            Serial.println(F("type '?' for help"));
        }
    }
}

// ─── Output stage: drive throttle relay + DACs based on state ───────────────
static void drive_outputs() {
    // Relay: energized when ACTIVE (normal) OR when serial throttle override is set
    const bool serial_throttle_active = (g_serial_throttle_override >= 0);
    const bool relay_on = serial_throttle_active ||
                          (g_master_state == MASTER_STATE_ACTIVE && g_thr.enable);
    digitalWrite(PIN_RELAY_COIL, relay_on ? HIGH : LOW);

    // Throttle: write DAC pair (will be ignored if relay is open)
    uint16_t throttle = 0;
    if (serial_throttle_active) {
        throttle = (uint16_t)g_serial_throttle_override;
        if (throttle > 250) throttle = 250;  // governor cap, even on bench
    } else if (relay_on) {
        const uint32_t now = millis();
        if (now - g_thr.last_rx_ms < WATCHDOG_TIMEOUT_MS) {
            throttle = g_thr.throttle_permil;
            // Hard cap at governed speed (firmware-enforced; defense in depth)
            // (5 mph governor: throttle_permil cap depends on traction
            //  controller's response curve. Tune on bench.)
            if (throttle > 250) throttle = 250;  // ~25% throttle ≈ 5 mph
        }
    }
    set_throttle_dacs(throttle);

    // Brake — Kartech 1A001HAJ on CAN3 (J1939, 250 kbps).
    //
    // Continuous proportional control: send_brake_permil(0..1000) maps to
    // 14-bit Kartech positions in the observed useful band
    // [POS_RELEASE_STOCK=3520 .. POS_FULL_BRAKE=3009]. Higher brake_permil =
    // lower position = more brake force. See kartech_brake.h header for the
    // protocol derivation.
    //
    // Brake is engaged ONLY when ACTIVE, brake_cmd.enable, and the watchdog
    // is fresh. Otherwise the actuator is commanded back to RELEASE so a
    // stale command can't keep the mechanical brake held down.
    static uint32_t last_kartech_ms = 0;
    const uint32_t now2 = millis();
    if (now2 - last_kartech_ms >= 20) {   // 50 Hz
        last_kartech_ms = now2;
        uint16_t demand;
        if (g_serial_brake_override >= 0) {
            demand = (uint16_t)g_serial_brake_override;       // bench override
        } else {
            const bool brake_active =
                (g_master_state == MASTER_STATE_ACTIVE) &&
                g_brk.enable &&
                (now2 - g_brk.last_rx_ms < WATCHDOG_TIMEOUT_MS);
            demand = brake_active ? g_brk.brake_permil : 0;
        }
        kartech::send_brake_permil(kartech_can, demand);
    }
}

// ─── Setup + loop ───────────────────────────────────────────────────────────
void setup() {
    pinMode(PIN_LED_STATUS,  OUTPUT);
    pinMode(PIN_RELAY_COIL,  OUTPUT);
    pinMode(PIN_BTN_ARM,     INPUT_PULLUP);
    pinMode(PIN_BTN_ENGAGE,  INPUT_PULLUP);
    pinMode(PIN_BTN_DISENG,  INPUT_PULLUP);
    pinMode(PIN_ESTOP_SENSE, INPUT_PULLUP);
    pinMode(PIN_BRAKE_PEDAL, INPUT);             // optoisolator drives this
    pinMode(PIN_WHEEL_TOUCH, INPUT_PULLUP);      // MPR121 IRQ (open-collector)

    digitalWrite(PIN_LED_STATUS, HIGH);
    digitalWrite(PIN_RELAY_COIL, LOW);           // de-energized = pedal direct

    Serial.begin(115200);
    while (!Serial && millis() < 2000) {}
    Serial.print("[pedals] FW v");
    Serial.print(PEDALS_FW_VERSION);
    Serial.println(" booting");

    // I²C + DACs
    Wire.begin();
    Wire.setClock(400000);
    if (!dac1.begin(0x60)) Serial.println("[pedals] DAC1 init FAIL");
    if (!dac2.begin(0x61)) Serial.println("[pedals] DAC2 init FAIL");
    set_throttle_dacs(0);  // 0% throttle on boot

    // DBW CAN
    dbw_can.begin();
    dbw_can.setBaudRate(DBW_BUS_BITRATE_HZ);
    dbw_can.setMaxMB(16);
    dbw_can.enableFIFO();
    dbw_can.enableFIFOInterrupt();
    dbw_can.onReceive(on_dbw_rx);

    // GEM J1939 CAN — read-only sniffer (ISO1042 also enforces TX-disable in HW)
    j1939_can.begin();
    j1939_can.setBaudRate(VEHICLE_J1939_BITRATE_HZ);
    j1939_can.setMaxMB(16);
    j1939_can.enableFIFO();
    j1939_can.enableFIFOInterrupt();
    j1939_can.onReceive(on_j1939_rx);

    // Kartech J1939 CAN — dedicated brake bus (TX commands, RX feedback later)
    kartech_can.begin();
    kartech_can.setBaudRate(VEHICLE_J1939_BITRATE_HZ);  // 250 kbps J1939
    kartech_can.setMaxMB(16);
    kartech_can.enableFIFO();
    kartech_can.enableFIFOInterrupt();
    // TODO: kartech_can.onReceive(on_kartech_rx) once feedback PGNs are sniffed.

    Serial.println("[pedals] 3 CAN buses up; relay de-energized; DACs at 0%");
    print_serial_help();
}

uint32_t last_status_ms  = 0;
uint32_t last_hb_ms      = 0;
uint32_t last_estop_ms   = 0;
uint32_t last_vstate_ms  = 0;
uint32_t last_blink_ms   = 0;
uint32_t last_console_ms = 0;

void loop() {
    dbw_can.events();
    j1939_can.events();
    kartech_can.events();
    process_serial();

    const uint32_t now = millis();

    // 50 Hz: state machine + outputs
    if (now - last_estop_ms >= 20) {
        last_estop_ms = now;
        step_state_machine();
        drive_outputs();
    }

    // 50 Hz: telemetry on DBW
    if (now - last_status_ms >= PERIOD_STATUS_MS) {
        last_status_ms = now;
        const bool relay_on = digitalRead(PIN_RELAY_COIL) == HIGH;
        // For status, report what we *commanded* (rest voltages if 0%)
        const float t = g_thr.throttle_permil / 1000.0f;
        const uint16_t v1_mV = uint16_t((V_REST_V1 + (V_FULL_V1 - V_REST_V1) * t) * 1000.0f);
        const uint16_t v2_mV = uint16_t((V_REST_V2 + (V_FULL_V2 - V_REST_V2) * t) * 1000.0f);
        send_throttle_status(v1_mV, v2_mV, relay_on);
        send_brake_status(0, 0);   // Phase 2 — placeholder

        const bool estop_ok = digitalRead(PIN_ESTOP_SENSE) == HIGH;
        const bool brake_pp = digitalRead(PIN_BRAKE_PEDAL) == HIGH;
        const bool wheel_t  = digitalRead(PIN_WHEEL_TOUCH) == LOW;
        uint8_t dash_bits = 0;
        if (digitalRead(PIN_BTN_ARM)    == LOW) dash_bits |= 1;
        if (digitalRead(PIN_BTN_ENGAGE) == LOW) dash_bits |= 2;
        if (digitalRead(PIN_BTN_DISENG) == LOW) dash_bits |= 4;
        send_estop_state(estop_ok, brake_pp, wheel_t, dash_bits);
    }

    // 20 Hz: vehicle state (J1939-decoded)
    if (now - last_vstate_ms >= PERIOD_VEHICLE_MS) {
        last_vstate_ms = now;
        send_vehicle_state();
    }

    // 50 Hz: heartbeat
    if (now - last_hb_ms >= PERIOD_HEARTBEAT_MS) {
        last_hb_ms = now;
        send_pedals_heartbeat();
    }

    // Status LED
    const uint32_t blink_period =
        (g_master_state == MASTER_STATE_FAULT)      ? 100 :
        (g_master_state == MASTER_STATE_ACTIVE)     ? 1000 :
        (g_master_state == MASTER_STATE_ARMED)      ? 250 :
                                                      500;
    if (now - last_blink_ms >= blink_period) {
        last_blink_ms = now;
        digitalWrite(PIN_LED_STATUS, !digitalRead(PIN_LED_STATUS));
    }

    // 1 Hz console dump
    if (now - last_console_ms >= 1000) {
        last_console_ms = now;
        Serial.print("[pedals] state=");
        Serial.print(int(g_master_state));
        Serial.print(" fault=0x");
        Serial.print(g_fault_flags, HEX);
        Serial.print(" thr=");
        Serial.print(g_thr.throttle_permil);
        Serial.print(" relay=");
        Serial.print(digitalRead(PIN_RELAY_COIL));
        Serial.print(" estop_ok=");
        Serial.print(digitalRead(PIN_ESTOP_SENSE) == HIGH);
        Serial.print(" v_speed=");
        Serial.print(g_j1939.speed_mph_x100 / 100.0f);
        Serial.print("mph gear=");
        Serial.println(int(g_j1939.gear));
    }
}
