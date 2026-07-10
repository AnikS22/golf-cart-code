# Status & Timeline

Last updated: 2026-05-03. Auto-pushed every 10 min via launchd; check `/tmp/golf-cart-sync.log`.

## Where we are right now

| Track | Status | Where |
|---|---|---|
| Master plan | ✅ Locked, approved | `Masterplan.md` |
| System design (BOM + procurement) | ✅ Ready to buy off | `Hardware/system_design.md` |
| Recovered 2020 artifacts | ✅ Inventoried | `Hardware/OneDrive_1_5-1-2026/` |
| Steering protocol (EPAS18 Ultra CAN) | ✅ Documented; firmware status TBD | `Software/firmware/common/include/dbw_can_protocol.h` (msg IDs 0x290/0x292/0x296) |
| Vehicle telemetry (J1939 read-only) | ✅ PGN dictionary recovered | `Hardware/OneDrive_1_5-1-2026/Arduino Code/PGN Data.docx` |
| Digital twin URDF (sensors + chassis) | ✅ Built; canonical params discipline enforced | `Sim/.../gem_sim/urdf/` |
| Sim DBW bridge (state machine + safety) | ✅ Coded; mirrors real Teensy firmware | `Sim/.../sim_dbw_bridge/` |
| Cartagena Gazebo workspace | ✅ Imported into repo | `Sim/Cartagena_GEM_E4_workspace/` |
| FAU breezeway world (T1) | ✅ Built (Cartagena) | `pure_pursuit/worlds/fau_breezeway.sdf` |
| macOS Docker dev env (sim with GUI) | 🟡 Built, not yet baked | `Sim/macos/`, `bin/sim_macos.sh` |
| Auto-commit | ✅ Running every 10 min | `bin/sync.sh`, launchd loaded |
| Cart visit checklist | ✅ Ready to print | `Hardware/CART_VISIT_DAY1.md` |
| CAD tool decision | ✅ Recommended Fusion 360 | `Hardware/CAD_RECOMMENDATION.md` |

| Track | Status |
|---|---|
| Real-cart Teensy firmware | ⛔ Not started — no Teensies bought |
| Real-cart Jetson `gem_dbw_bridge` (C++) | ⛔ Not started |
| FAU campus T2 world build | ⛔ Not started |
| FAU campus T3 world build | ⛔ Not started |
| Lanelet2 HD map | ⛔ Not started |
| Autoware Universe integration | ⛔ Not started |
| FAU Risk Mgmt approval | ⛔ Not contacted |
| DCE autonomous firmware confirmation | ✅ CONFIRMED PRESENT — bench-steered via CAN 2026-07-10 (ID 0x298 @ 250k) |

## Critical gates (block phase advancement)

| Gate | Owner | Unblocks |
|---|---|---|
| ~~DCE autonomous firmware loaded on EPAS18 ECU~~ | ✅ DONE — steered on bench 2026-07-10 | ~~All steering work~~ UNBLOCKED |
| **EPAS backdrive confirmed** | Cart visit hand-test | Manual override safety case |
| **Pack voltage confirmed (48 V vs 72 V)** | Cart visit multimeter | DC-DC procurement |
| **GEM throttle Hall pair characterized** | Cart visit multimeter sweep | DAC bypass calibration |
| **J1939 diag port located** | Cart visit | Vehicle-state sniffer |
| **FAU Risk Mgmt initial conversation** | Email/meeting | Phase 2+ on-campus driving |

## Timeline (week-by-week)

### Week 0 — 2026-05-03 → 2026-05-09 (this week)
- **2026-05-04 Mon** — Cart visit: inspection per `Hardware/CART_VISIT_DAY1.md`.
- **05-05 Tue** — Process inspection findings; email DCE Motorsport with EPAS ECU serial.
- **05-05 Tue** — Install Fusion 360 (per `Hardware/CAD_RECOMMENDATION.md`).
- **05-05 Tue** — `bin/sim_macos.sh` to build the macOS Docker sim image (~30 min one-time bake; runs in background while you do other things).
- **05-06 Wed** — Order Tier 1 parts: 2× Teensy 4.1, CANable 2.0, MCP4725 ×2, MCP6002, Omron G8HE relay, Belden 9841, Deutsch DT crimp kit, ISO1042. (~$250 — see `Hardware/system_design.md` PART I.)
- **05-07 Thu** — Email FAU Risk Management about autonomous-vehicle research precedent (long pole; start now, not in Phase 3).
- **05-07 Thu** — In sim: bring up `gem_sim sim_full.launch.py`; verify all sensor topics publish; manually drive cart with joystick. Validate `sim_dbw_bridge` state machine.
- **05-08–09 Fri/Sat** — Start drafting CAD for sensor mast + Pelican mounting plate (Fusion 360).

### Week 1 — 2026-05-10 → 2026-05-16
- Tier 1 parts arrive.
- Bench: solder up CAN bus on a breadboard. Get both Teensies talking to a laptop via CANable.
- Write `Software/firmware/motion_teensy/` PlatformIO skeleton — start with HB at 50 Hz on the DBW bus.
- Write `Software/firmware/pedals_teensy/` PlatformIO skeleton — same HB pattern.
- In sim: extend `regions.json` to T2 (academic core); build the world meshes via the Cartagena pipeline.

### Week 2 — 2026-05-17 → 2026-05-23
- Implement EPAS18 CAN bridge in Motion Teensy firmware. Bench-test with a simulated EPAS responder on a laptop (or with a real EPAS18 if you can get one off the cart for bench work).
- Implement throttle DAC + relay logic in Pedals Teensy. Bench-test with a scope.
- Implement J1939 sniffer in Pedals Teensy (port the recovered ARD1939 stack to Teensy 4.1 + FlexCAN_T4).
- In sim: write `joy_to_ackermann` node so a gamepad publishes `/dbw/cmd`; tune driving feel.

### Week 3 — 2026-05-24 → 2026-05-30
- Mount Pelican 1450 + Aux Boxes in the cart. Run cable channels per `Masterplan.md` PART A.14.
- Order Tier 2 (compute + LTE + sensors). Tier 3 procurement starts.
- In sim: integrate Nav2 with the canonical sensor topics. Closed-loop waypoint follower on T1 breezeway.

### Week 4 — 2026-05-31 → 2026-06-06
- **First-light RC drive** (Phase 0c milestone). Cart wheels off ground, joystick → laptop → CANable → Teensies → EPAS18 + DAC. **No autonomy, no sensors — just remote drive-by-wire.** This is the "RC the cart" demo you mentioned.
- See `Software/RC_FIRSTLIGHT_PLAN.md` (TODO Week 1) for the exact stack.

### Week 5–8 — June 2026
- Sensors mounted progressively (LiDAR → cameras → GNSS → IMU). After each, validate the corresponding ROS topic publishes.
- First-light closed-lot drive (Phase 1 demo): cart drives a square at 3 mph in an empty parking lot, safety driver in seat.

### Week 9–16 — Jul/Aug 2026
- Mapping drive of T1, T2 → PCD point cloud + lanelet2 vector map.
- Migrate from Nav2 to Autoware Universe.
- Phase 2 demo: 10 consecutive autonomous loops on T1, lateral err <50 cm.

### Week 17–24 — Sep/Oct 2026
- Full Autoware perception. Pedestrian dart-out testing.
- Phase 3 demo: scripted obstacles on T2 academic core.

### Week 25+ — Nov 2026 onward
- Brake actuator integration (Phase 2 hardware).
- T3 full-campus mapping.
- Unmanned readiness (Phase 4).

## What you're doing tomorrow

Print and follow `Hardware/CART_VISIT_DAY1.md`. Critical priorities (everything else is bonus):
1. Find the EPAS18 ECU; photograph the serial number.
2. Hand-test EPAS backdrive.
3. Multimeter pack voltage.
4. Multimeter throttle pedal Hall pair (slow sweep, record V1/V2).
5. Find the J1939 diagnostic port.
6. Photograph the traction controller.

Send the DCE firmware-availability email same day with the ECU serial.

## What you're doing in parallel (no cart access required)

- **Sim dev environment:** `bin/sim_macos.sh` to build the Docker image (one-time ~30 min). Then you can prototype control algorithms against the digital twin from your macOS host without touching the cart.
- **CAD:** install Fusion 360. Start sketching the sensor mast (mounts the Livox + ZED 2i + GNSS antennas above the hardtop).
- **FAU Risk Management approval pipeline:** start that email thread *now*. It's the long-pole gate for any on-campus driving in Phase 2+.

## Auto-update is on

This file (and the rest of the repo) auto-commits and pushes to GitHub every 10 minutes via macOS launchd. Trigger an immediate sync any time:

```bash
bin/sync.sh
tail -f /tmp/golf-cart-sync.log
```
