/*
 * steer_test_teensy — MANUAL DRIVE firmware for the GEM E4 EPAS18 steering.
 *
 * Locked to the config PROVEN on hardware 2026-07-10:
 *   bus 250 kbps · command ID 0x298 · frame {map, torque, 0,0,0,0,0,0}
 *   map 0=local/SAFE, 1=autonomous · torque 128=center · NO mirror byte.
 *
 * Drive it with drive.py (or any serial terminal @115200). Single-char cmds:
 *   a  steer LEFT  by one step        d  steer RIGHT by one step
 *   space  recenter (stay engaged)    x  STOP -> local power-assist
 *   .  / newline  keepalive (no change; drive.py sends this ~1/s)
 *
 * SAFETY
 *   • Boots SAFE (map=0). First a/d engages autonomous mode.
 *   • Torque slew-limited (eases in) and capped at MAX_OFFSET.
 *   • Deadman: if NO serial arrives for DEADMAN_MS the demand ramps to center
 *     and drops to local. drive.py streams a keepalive, so quitting/crashing/
 *     unplugging the driver recenters the wheel automatically.
 *   • Manual-override: a torque-sensor spike (hand on the wheel) drops to local.
 */
#include <Arduino.h>
#include <FlexCAN_T4.h>

#define EPAS_BUS_BITRATE_HZ  250000U
#define ID_EPAS_MSG1         0x290U
#define ID_EPAS_MSG2         0x292U
#define ID_EPAS_CMD          0x298U     // verified command ID (NOT manual's 0x296)

static constexpr uint8_t  DRIVE_MAP    = 1;     // 1=gentle .. 5=aggressive
static constexpr int      STEP         = 6;     // torque bits per key (clears ~4-bit deadband)
static constexpr int      MAX_OFFSET   = 30;    // cap |torque-128| (of 64)
static constexpr float    SLEW_PER_TICK= 0.30f; // 100 Hz -> 30 bits/s ease-in
static constexpr uint32_t DEADMAN_MS   = 3000;  // no serial -> recenter + local
static constexpr uint8_t  OVERRIDE_SPIKE = 12;

typedef struct __attribute__((packed)) {
  uint8_t torque_processed, motor_duty_pct, current_A, supply_voltage_x10;
  uint8_t switch_position, box_temperature_C, torque_a_raw, torque_b_raw;
} epas_msg1_t;
typedef struct __attribute__((packed)) {
  uint8_t steering_angle, analog_ch1, analog_ch2, selected_map;
  uint8_t error_code, digital_io, status_flags, limit_flags;
} epas_msg2_t;

FlexCAN_T4<CAN2, RX_SIZE_256, TX_SIZE_16> epas_can;

volatile uint8_t g_map      = 0;      // 0=SAFE
volatile int     g_target   = 128;    // torque setpoint (128 center)
volatile float   g_applied  = 128.0f; // slewed value actually sent
uint32_t g_last_rx_ms = 0;            // any serial byte refreshes this

epas_msg1_t g_msg1{};
epas_msg2_t g_msg2{};
uint32_t g_msg2_last_ms = 0;
bool g_baseline_valid = false;
uint8_t g_base_a = 128, g_base_b = 128;

IntervalTimer g_tx_timer;

static void tx_isr() {
  float tgt = (g_map == 0) ? 128.0f : (float)g_target;
  if (g_applied < tgt)      { g_applied += SLEW_PER_TICK; if (g_applied > tgt) g_applied = tgt; }
  else if (g_applied > tgt) { g_applied -= SLEW_PER_TICK; if (g_applied < tgt) g_applied = tgt; }

  CAN_message_t f{};
  f.id = ID_EPAS_CMD; f.len = 8;
  f.buf[0] = g_map;
  f.buf[1] = (uint8_t)lroundf(g_applied);
  // buf[2..7] stay 0 — no mirror byte (matches verified working frame)
  epas_can.write(f);
}

static void on_rx(const CAN_message_t& f) {
  if (f.id == ID_EPAS_MSG1 && f.len == 8) {
    memcpy(&g_msg1, f.buf, 8);
    if (!g_baseline_valid) { g_base_a = g_msg1.torque_a_raw; g_base_b = g_msg1.torque_b_raw; g_baseline_valid = true; }
    int da = abs((int)g_msg1.torque_a_raw - g_base_a), db = abs((int)g_msg1.torque_b_raw - g_base_b);
    if ((da > OVERRIDE_SPIKE || db > OVERRIDE_SPIKE) && g_map != 0) {
      g_map = 0; g_target = 128; Serial.println("[OVERRIDE] hand on wheel -> local");
    }
  } else if (f.id == ID_EPAS_MSG2 && f.len == 8) {
    memcpy(&g_msg2, f.buf, 8); g_msg2_last_ms = millis();
  }
}

static void nudge(int delta) {
  g_map = DRIVE_MAP;
  int v = g_target + delta;
  if (v > 128 + MAX_OFFSET) v = 128 + MAX_OFFSET;
  if (v < 128 - MAX_OFFSET) v = 128 - MAX_OFFSET;
  g_target = v;
}

static void handle_key(int c) {
  g_last_rx_ms = millis();
  switch (c) {
    case 'a': case 'A': nudge(-STEP); break;
    case 'd': case 'D': nudge(+STEP); break;
    case ' ':           g_target = 128; break;               // recenter, stay engaged
    case 'x': case 'X': case 's': g_map = 0; g_target = 128; Serial.println("[SAFE] stop"); break;
    case '.': case '\r': case '\n': break;                   // keepalive
    default: break;
  }
}

void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 2000) {}
  Serial.println("[drive] EPAS manual steering — 0x298 @ 250k. a=left d=right space=center x=stop");
  epas_can.begin();
  epas_can.setBaudRate(EPAS_BUS_BITRATE_HZ);
  epas_can.setMaxMB(16);
  epas_can.enableFIFO();
  epas_can.enableFIFOInterrupt();
  epas_can.setFIFOFilter(ACCEPT_ALL);
  epas_can.onReceive(on_rx);
  g_tx_timer.begin(tx_isr, 10000);   // 100 Hz
  g_last_rx_ms = millis();
}

uint32_t last_status = 0;
void loop() {
  epas_can.events();
  while (Serial.available()) handle_key(Serial.read());

  const uint32_t now = millis();
  if (g_map != 0 && (now - g_last_rx_ms) > DEADMAN_MS) {
    g_target = 128;
    if ((int)lroundf(g_applied) == 128) { g_map = 0; Serial.println("[deadman] no driver — recentered, local"); }
  }

  if (now - last_status >= 200) {   // 5 Hz
    last_status = now;
    const bool live = g_baseline_valid && (now - g_msg2_last_ms < 500);
    Serial.print("[st] "); Serial.print(g_map ? "DRIVE" : "SAFE ");
    Serial.print(" tq=");    Serial.print(g_map ? g_target : 128);
    Serial.print(" appl=");  Serial.print((int)lroundf(g_applied));
    Serial.print(" | EPAS "); Serial.print(live ? "OK" : "??");
    Serial.print(" map=");   Serial.print(g_msg2.selected_map);
    Serial.print(" remote=");Serial.print((g_msg2.limit_flags >> 7) & 1);
    Serial.print(" duty=");  Serial.print(g_msg1.motor_duty_pct);
    Serial.print(" A=");     Serial.print(g_msg1.current_A);
    Serial.print(" angle="); Serial.print(g_msg2.steering_angle);
    Serial.print(" err=");   Serial.println(g_msg2.error_code);
  }
}
