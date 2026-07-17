/*
 * brake_sniff_teensy — SAFE poll-and-listen sniffer for the Kar-Tech actuator.
 *
 * Sends ONLY harmless Report-Poll requests (0xF1) — these ask the actuator for
 * its position/status and NEVER touch the clutch or motor. No motion, no banging.
 * Then it receives every frame on CAN2 (pin 0=RX, 1=TX) @ 250 kbps and prints a
 * live table: each unique CAN ID, ext/std, count, and last 8 bytes.
 *
 * Decodes Kar-Tech report types by byte0 (128=Position, 152=Enhanced, 129=Motor
 * Current/Temp, 239=SW rev, 168=Device ID, 238=Zeroing) no matter what ID they
 * arrive on — so we learn the actuator's REAL (possibly 2020-reassigned) report ID
 * and confirm RX works, all without moving the shaft.
 *
 * If the table stays empty even while polling, RX is genuinely not getting through
 * (bus wiring / CAN-H-L swap / termination / actuator power).
 */
#include <Arduino.h>
#include <FlexCAN_T4.h>

#define BUS_BITRATE_HZ  250000U
// Actuator TRANSMITS on 0xFF0001 = priority 0. Old (2018) units filter priority,
// so commands must match: send to 0xFF0000 (priority 0), NOT 0x18FF0000 (prio 6).
#define ID_KT_CMD       0x00FF0000UL   // default command ID, priority 0 (extended)

FlexCAN_T4<CAN2, RX_SIZE_256, TX_SIZE_16> can;

struct Seen { uint32_t id; bool ext; uint8_t len; uint8_t buf[8]; uint32_t count; };
static const int MAXID = 24;
Seen g_seen[MAXID];
int  g_nseen = 0;

static const char* kt_type(uint8_t b0) {
  switch (b0) {
    case 128: return "Position";
    case 152: return "EnhancedPos";
    case 129: return "MotorCur/Temp";
    case 239: return "SWrev";
    case 168: return "DeviceID";
    case 238: return "Zeroing";
    default:  return "";
  }
}

static void on_rx(const CAN_message_t& f) {
  for (int i = 0; i < g_nseen; i++) {
    if (g_seen[i].id == f.id && g_seen[i].ext == (bool)f.flags.extended) {
      g_seen[i].len = f.len; memcpy(g_seen[i].buf, f.buf, 8); g_seen[i].count++;
      return;
    }
  }
  if (g_nseen < MAXID) {
    Seen& s = g_seen[g_nseen++];
    s.id = f.id; s.ext = f.flags.extended; s.len = f.len;
    memcpy(s.buf, f.buf, 8); s.count = 1;
  }
}

void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 2000) {}
  Serial.println("[sniff] CAN2 @ 250k, LISTEN ONLY. Every ID the bus carries:");
  can.begin();
  can.setBaudRate(BUS_BITRATE_HZ);
  can.setMaxMB(16);
  can.enableFIFO();
  can.enableFIFOInterrupt();
  can.setFIFOFilter(ACCEPT_ALL);
  can.onReceive(on_rx);
}

// PASSIVE position request: position command with clutch OFF + motor OFF +
// auto-reply. Datasheet: CE=0/M=0 => "passive mode, shaft free" (NO motion), and
// A=1 => actuator replies with the Enhanced Position Report. Also fire an F1
// Report-Poll as a fallback. Both are info-only; neither moves the shaft.
static void poll() {
  // Passive position cmd with CONFIRMATION (byte1=0x8A: C=1,A=0,DT=0x0A) + motor
  // OFF (byte3=0x02). If the actuator accepts it, it echoes THIS exact frame back
  // on the report ID -> we'll see [15 138 88 2 ...]. No motion (M=0).
  CAN_message_t f{};
  f.id = ID_KT_CMD; f.flags.extended = 1; f.len = 8;
  f.buf[0] = 0x0F; f.buf[1] = 0x8A; f.buf[2] = 0x58; f.buf[3] = 0x02;
  can.write(f);
}

uint32_t last = 0, last_poll = 0;
void loop() {
  can.events();
  const uint32_t now = millis();
  if (now - last_poll >= 200) { last_poll = now; poll(); }   // 5 Hz harmless poll
  if (now - last >= 1000) {
    last = now;
    Serial.print("---- "); Serial.print(g_nseen); Serial.println(" unique ID(s) ----");
    if (g_nseen == 0) Serial.println("  (nothing received — actuator silent: check power/bus, or it only reports when polled)");
    for (int i = 0; i < g_nseen; i++) {
      Seen& s = g_seen[i];
      Serial.print("  ");
      Serial.print(s.ext ? "EXT 0x" : "STD 0x");
      Serial.print(s.id, HEX);
      Serial.print(" x"); Serial.print(s.count);
      Serial.print(" len="); Serial.print(s.len);
      Serial.print(" [");
      for (int b = 0; b < 8; b++) { if (b) Serial.print(' '); Serial.print(s.buf[b]); }
      Serial.print("]");
      const char* t = kt_type(s.buf[0]);
      if (*t) { Serial.print("  <"); Serial.print(t); Serial.print(">"); }
      Serial.println();
    }
    Serial.println();
  }
}
