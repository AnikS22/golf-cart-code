/*
 * brake_test_teensy — bench tool for the Kar-Tech 1A001HAJ CAN actuator (brake).
 *
 * Protocol PROVEN from the Kar-Tech datasheet (1A001HAJ.doc, rev 1.30):
 *   J1939 29-bit extended IDs · 250 kbps · same CAN2 transceiver as steering
 *   (pin 0 = RX, pin 1 = TX).
 *   Command ID  0x18FF0000 (default, always enabled at power-up).
 *   Report  ID  0x18FF0001 (auto-reply, Enhanced Position Report).
 *
 *   Position command frame (8 bytes):
 *     [0]=0x0F  [1]=0x4A(auto-reply)  [2]=DPOS_LOW  [3]=CE·M·DPOS_HI  [4..7]=0
 *     counts = inches*1000 + 500   (byte3 low 5 bits = DPOS_HI)
 *     byte3 bit7 = clutch enable, bit6 = motor enable
 *     working range 550..3450 counts (0.05"..2.95") — outside is ignored.
 *
 * Drive it with brake.py (or any serial terminal @115200). Single-char cmds:
 *   w / up   extend  (+step)        s / down  retract (-step)
 *   e        engage (clutch+motor)  space     hold current position
 *   x        RELEASE -> clutch off, shaft free      .  keepalive
 *
 * SAFETY (BENCH semantics — actuator NOT yet coupled to the brake)
 *   • Boots IDLE (clutch off, shaft free). First move/engage key engages.
 *   • Clutch sequencing per datasheet: clutch ON >=20ms before motor ON;
 *     motor OFF >=20ms before clutch OFF (protects the clutch).
 *   • Deadman: no serial for DEADMAN_MS -> sequenced release to IDLE. brake.py
 *     streams a keepalive, so quitting/crashing/unplugging frees the shaft.
 *   • ponytail: bench fail-to-RELEASE is safe on the bench but WRONG on the cart
 *     — the real brake must fail-to-APPLIED. The actuator's own 1s failsafe also
 *     drops the clutch on comms loss, so the cart needs a mechanical/spring brake
 *     return. Reconcile in pedals_teensy before this drives a real brake.
 */
#include <Arduino.h>
#include <FlexCAN_T4.h>

#define BRAKE_BUS_BITRATE_HZ  250000U
// Priority 0 CONFIRMED on-bench 2026-07-17: the actuator transmits on 0xFF0001 and
// only accepts commands at 0xFF0000 — it filters priority, so 0x18FF0000 (prio 6)
// was silently ignored. Verified via a confirmation-flag echo of our exact frame.
#define ID_KT_CMD             0x00FF0000UL   // default command ID, priority 0 (extended)
#define ID_KT_REPORT          0x00FF0001UL   // default report ID,  priority 0 (extended)

static constexpr int      POS_OFFSET   = 500;    // counts added to inches*1000
static constexpr int      POS_MIN      = 550;    // 0.05" — datasheet working min
static constexpr int      POS_MAX      = 3450;   // 2.95" — datasheet working max
static constexpr int      HOME_COUNTS  = 600;    // 0.1" — datasheet-suggested home
static constexpr int      STEP         = 100;    // 0.1" per key
static constexpr uint32_t CLUTCH_LEAD_MS = 25;   // >=20ms clutch-before-motor
static constexpr uint32_t DEADMAN_MS   = 800;    // no serial -> release (< 1s HW failsafe)

// Enhanced Position Report (byte0 == 152)
typedef struct __attribute__((packed)) {
  uint8_t type, dt, shaft_lo, shaft_hi, errors, cur_lo, cur_hi, status;
} kt_report_t;

FlexCAN_T4<CAN2, RX_SIZE_256, TX_SIZE_16> brake_can;

volatile int  g_target   = HOME_COUNTS;   // desired position (counts)
volatile bool g_want_eng = false;         // operator wants clutch+motor on
volatile bool g_clutch   = false;         // actual staged clutch state
volatile bool g_motor    = false;         // actual staged motor state
uint32_t g_stage_ms  = 0;                 // last clutch/motor transition
uint32_t g_last_rx_ms = 0;                // any serial byte refreshes this

kt_report_t g_rep{};
uint32_t g_rep_last_ms = 0;   // last Enhanced Position Report (byte0=152)
uint32_t g_alive_ms   = 0;    // last ANY frame on the report ID
bool g_have_rep = false;

IntervalTimer g_tx_timer;

static inline int clampc(int v) { return v < POS_MIN ? POS_MIN : (v > POS_MAX ? POS_MAX : v); }

static void tx_isr() {
  const int counts = clampc(g_target);
  CAN_message_t f{};
  f.id = ID_KT_CMD;
  f.flags.extended = 1;
  f.len = 8;
  f.buf[0] = 0x0F;                         // position command
  f.buf[1] = 0x4A;                         // auto-reply (Enhanced Position Report)
  f.buf[2] = counts & 0xFF;                // DPOS_LOW
  f.buf[3] = (g_clutch ? 0x80 : 0) | (g_motor ? 0x40 : 0) | ((counts >> 8) & 0x1F);
  // buf[4..7] = 0
  brake_can.write(f);
}

static void on_rx(const CAN_message_t& f) {
  if (!f.flags.extended || f.id != ID_KT_REPORT) return;
  g_alive_ms = millis();
  if (f.len == 8 && f.buf[0] == 152) {   // Enhanced Position Report
    memcpy(&g_rep, f.buf, 8);
    g_rep_last_ms = g_alive_ms;
    g_have_rep = true;
  }
}

static void handle_key(int c) {
  g_last_rx_ms = millis();
  switch (c) {
    case 'w': case 'W': g_want_eng = true; g_target = clampc(g_target + STEP); break;
    case 's': case 'S': g_want_eng = true; g_target = clampc(g_target - STEP); break;
    case 'e': case 'E':                                  // engage, hold where we are
      g_want_eng = true;
      if (g_have_rep) g_target = clampc(((g_rep.shaft_hi << 8) | g_rep.shaft_lo));
      break;
    case ' ':                                            // hold current reported pos
      g_want_eng = true;
      if (g_have_rep) g_target = clampc(((g_rep.shaft_hi << 8) | g_rep.shaft_lo));
      break;
    case 'x': case 'X': g_want_eng = false; Serial.println("[RELEASE] shaft free"); break;
    case '.': case '\r': case '\n': break;               // keepalive
    default: break;
  }
}

// Staged clutch/motor transitions (non-blocking). Datasheet: clutch leads motor.
static void update_stage() {
  const uint32_t now = millis();
  if (g_want_eng) {
    if (!g_clutch)               { g_clutch = true;  g_stage_ms = now; }   // 1) clutch on
    else if (!g_motor && now - g_stage_ms >= CLUTCH_LEAD_MS) g_motor = true; // 2) motor on
  } else {
    if (g_motor)                 { g_motor = false; g_stage_ms = now; }    // 1) motor off
    else if (g_clutch && now - g_stage_ms >= CLUTCH_LEAD_MS) g_clutch = false; // 2) clutch off
  }
}

void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 2000) {}
  Serial.println("[brake] Kar-Tech actuator — 0x18FF0000 @ 250k (29-bit).");
  Serial.println("  w/up extend  s/down retract  e engage  space hold  x release");
  brake_can.begin();
  brake_can.setBaudRate(BRAKE_BUS_BITRATE_HZ);
  brake_can.setMaxMB(16);
  brake_can.enableFIFO();
  brake_can.enableFIFOInterrupt();
  brake_can.setFIFOFilter(ACCEPT_ALL);
  brake_can.onReceive(on_rx);
  g_tx_timer.begin(tx_isr, 20000);   // 50 Hz (datasheet: refresh <=100ms)
  g_last_rx_ms = millis();
}

uint32_t last_status = 0;
void loop() {
  brake_can.events();
  while (Serial.available()) handle_key(Serial.read());

  const uint32_t now = millis();
  if (g_want_eng && (now - g_last_rx_ms) > DEADMAN_MS) {
    g_want_eng = false;
    Serial.println("[deadman] no driver — releasing");
  }
  update_stage();

  if (now - last_status >= 200) {   // 5 Hz
    last_status = now;
    const bool alive = (now - g_alive_ms < 500);
    const bool live  = g_have_rep && (now - g_rep_last_ms < 500);
    const int  rc   = (g_rep.shaft_hi << 8) | g_rep.shaft_lo;
    const int  cur  = (g_rep.cur_hi << 8) | g_rep.cur_lo;
    Serial.print("[st] ");     Serial.print(g_want_eng ? "ENG " : "IDLE");
    Serial.print(g_clutch ? " C" : " -"); Serial.print(g_motor ? "M" : "-");
    Serial.print(" tgt=");     Serial.print((g_target - POS_OFFSET) / 1000.0f, 3);
    Serial.print("in | KT ");  Serial.print(alive ? (live ? "OK " : "alive") : "?? ");
    Serial.print(" pos=");     Serial.print(live ? (rc - POS_OFFSET) / 1000.0f : 0.0f, 3);
    Serial.print("in cur=");   Serial.print(cur);
    Serial.print("mA err=0x"); Serial.println(g_rep.errors, HEX);
  }
}
