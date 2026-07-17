# ROS ↔ Teensy DBW Integration Plan

**Status:** PLAN ONLY — not started. Written 2026-07-17 after bench-proving steering
(EPAS18, 0x298 @ 250k) and brake (Kar-Tech, priority-0 0xFF0000 @ 250k). Next session
executes this. Do NOT rebuild what already works (see §1).

## 0. TL;DR

The ROS graph already exists and is smoke-tested. The gap is **firmware, not ROS**:
1. Both "real" firmwares still carry the OLD, now-disproven actuator protocol (EPAS
   mirror byte; Kar-Tech wrong ID/encoding), and
2. Motion Teensy's EPAS transmit is **commented out** (steering does nothing today),
   Pedals never sets the Kar-Tech clutch/motor bits (brake wouldn't actuate).

So integration = **reconcile the protocol + port the proven bench code into the two
DBW firmwares + close the telemetry loop**, then bench→wheels-off→closed-lot test.
The `/dbw/cmd` + `/vehicle/*` interface stays fixed (sim already mirrors it).

## 1. DO NOT REBUILD — already working (reuse as-is)

- `Software/autonomy_ws/src/gem_dbw_bridge/` — ROS↔SocketCAN `can0` bridge (Python,
  python-can). Subscribes `/dbw/cmd` (AckermannDriveStamped), `/dbw/enable` (Bool);
  publishes `/vehicle/*`. TX 0x100 HB @ 50 Hz + 0x110/0x120/0x130 when cmd <100 ms old.
- `Software/autonomy_ws/src/gem_teleop/` — F710 → `/dbw/cmd`. `launch/teleop.launch.py`
  brings up joy_node + joy_to_ackermann + gem_dbw_bridge (single RC entry point).
- `Software/firmware/common/include/dbw_can_protocol.h` — the DBW message contract
  (0x100–0x160), single source of truth. Bus rates already correct (EPAS 250k).
- `pedals_teensy` — master state machine (DISENGAGED/ARMED/ACTIVE/FAULT), throttle DAC
  bypass, J1939 read-only sniffer, E-stop/brake/wheel gates: all IMPLEMENTED.

## 2. Command flow (confirmed as-is)

```
F710 → joy_node → joy_to_ackermann → /dbw/cmd
     → gem_dbw_bridge → can0 (DBW 500k):
         0x100 Jetson HB (50Hz), 0x110 steer, 0x120 throttle, 0x130 brake (20ms)
     → Motion Teensy:  0x110 → PI → EPAS 0x298 @ 250k
     → Pedals Teensy:  0x120 → throttle DAC/relay ; 0x130 → Kar-Tech 0xFF0000 @ 250k
Telemetry back: 0x111/0x112/0x121/0x131/0x140/0x150/0x151/0x160 → bridge → /vehicle/*
```
Buses: DBW 500k · EPAS 250k · Kar-Tech J1939 250k · GEM J1939 250k (READ-ONLY).

## 3. Workstream A — reconcile disproven facts (BLOCKS everything; do first)

- **A1** `dbw_can_protocol.h:243-251` — delete `epas_make_demand()` mirror-byte logic
  (`torque_b = 255 - torque_a`); replace with a builder emitting
  `{map, 128+torque, 0,0,0,0,0,0}`. Drop/zero `epas_msg3_t.torque_b` (`:236`).
  (Bench-proven: no mirror byte — see `steer_test_teensy/src/main.cpp:69-70`.)
- **A2** `common/include/kartech_brake.h` — TX ID `0x00FF0080` → **`0x00FF0000`** (SA 0,
  priority 0); byte3 encoding → `(clutch<<7)|(motor<<6)|(DPOS_HI 5 bits)`; position band
  → **`counts = inches*1000 + 500`, range 550–3450** (from `brake_test_teensy:39-45`).
- **A3** Stale prose only (no logic): `motion_teensy/main.cpp:16-18` (0x296→0x298);
  `dbw_translation_architecture.md:95` (mirror step) + brake band; brake_test/sniff
  header comments still print `0x18FF0000` though the `#define` is `0x00FF0000`.

## 4. Workstream B — make Motion Teensy actually steer (port `steer_test_teensy`)

- **B1** `motion_teensy/main.cpp:110-152` `epas_tx_isr()` — remove `if(false)` guard and
  uncomment the EPAS write; emit the **no-mirror** frame from A1.
- **B2** Port the proven bench behavior: boot-SAFE (map=0); first command engages map;
  torque slew-limiter (`SLEW_PER_TICK=0.30`); `MAX_OFFSET` clamp; deadman→center→local;
  torque-spike override→local. (All in `steer_test_teensy`.)
- **B3** Wire the outer loop: 0x110 `angle_centideg` target → PI (start Kp 0.2, Ki 0.05)
  → torque demand → frame. **Calibrate `scale_centideg_per_bit`** on bench (currently a
  `44800/200` placeholder, `:123-124`).
- **B4** Cross-sync gating (currently missing, `:296-304`): only emit non-center torque
  when Pedals master_state==ACTIVE (via 0x151 HB state byte) AND Jetson HB <100 ms.
- **B5** TX rate: bench validated **100 Hz**; header `PERIOD_EPAS_TX_MS=5` = 200 Hz.
  Keep 100 Hz (proven) or re-validate 200 Hz on the bench. Decide, don't assume.

## 5. Workstream C — make Pedals Teensy actually brake + feed back (port `brake_test_teensy`)

- **C1** Replace the brake path (`pedals_teensy` `drive_outputs` / `kartech::send_*`) with
  the `brake_test_teensy` frame + **explicit clutch/motor staging** (clutch ON ≥25 ms
  before motor ON; motor OFF before clutch OFF). **Set the clutch/motor enable bits** —
  today they're never set, so the actuator wouldn't move even with the right ID.
- **C2** permil→counts band: pick release/full counts within 550–3450. **Needs bench
  calibration once the actuator is linked to the pedal** (see brake reference memory).
  Phase-1 brake stays 0 (foot brake) — this is Phase-2 activation work.
- **C3** Port the Enhanced Position Report parser (byte0==152) → fill `BRAKE_STATUS` 0x131
  (real pos/current/err). Add `kartech_can.onReceive` (`:583` TODO).

## 6. Workstream D — close telemetry loop (ROS side)

- **D1** `gem_dbw_bridge_node.py:265` — decode 0x121 THROTTLE_STATUS, 0x131 BRAKE_STATUS,
  0x112 STEER_TORQUE_RAW; publish the corresponding `/vehicle/*`.
- **D2** Heartbeat CRC: bridge hardcodes 0 (`node.py:202`) while `jetson_heartbeat_t`
  documents CRC-16. Either implement both sides or explicitly document it's ignored.
- **D3** Doc-vs-code: bridge delegates ALL gating to the Teensies (no ROS-side
  master_state/gear gate), contra `dbw_translation_architecture.md`. Reconcile wording.

## 7. Bring-up test order (no autonomy — RC first)

1. **Bench, no cart** (Teensies + laptop + CANable): `candump`, verify all HBs, ARM→ENGAGE
   →DISENGAGE via dash buttons, E-stop open→FAULT, Jetson-HB-drop watchdog.
2. **EPAS bench** (EPAS18+column off-cart): 0x110 angle sweep → wheel moves, PI tracks;
   calibrate `scale_centideg_per_bit`.
3. **Throttle bench**: scope the two DAC channels across permil sweep.
4. **Wheels-off-ground**: full gamepad → steer + throttle end-to-end.
5. **Closed-lot 3 mph**, throttle cap permil→100 for first drive, safety driver in seat.

## 8. Open decisions for next session

- **Bridge host for first RC drive:** laptop+CANable (CART_CONTROL_PLAN) vs Jetson `can0`
  (already UP). Pick one for the first drive.
- **EPAS TX 100 vs 200 Hz** (B5).
- **Brake permil→counts band** — deferred until actuator linked to pedal + calibrated.
- **master_state gate location** — keep on Teensies (current, simpler) vs add ROS-side.

## 9. Prior art / reuse

UIUC `gem_ws`, Autoware Universe. `Sim/.../sim_dbw_bridge` already mirrors `/dbw/cmd` +
`/vehicle/*`, so teleop and (later) autonomy nodes run unchanged against sim or real —
keep that interface fixed. References: `.claude/memory/reference_epas18_ultra.md`,
`reference_kartech_brake.md`, `Software/dbw_translation_architecture.md`,
`Software/CART_CONTROL_PLAN.md`.
