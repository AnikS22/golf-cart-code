# CLAUDE.md

Project-specific instructions Claude Code loads automatically every session.
Keep this file tight — it lives in every context window.

## What this project is

FAU MPCR self-driving conversion of a 2018 Polaris GEM E4 LSV. Goal: full
autonomy ("tiny Waymo") on FAU Boca campus, ≤15 mph, safety-driver-Phase 1 →
unmanned-Phase 4. Project started ~2019, abandoned 2020, revived 2026-05-01.
Master plan PDF: `~/Library/.../GEM_E4_Master_Plan.pdf`.

## Architecture (one paragraph)

Sensors (Livox Mid-360 + 7 cameras + dual ZED-F9P RTK + VN-100 IMU) feed an
**AGX Orin** for perception/planning (Phase 2+) and a **Yahboom Orin NX** for
safety + DBW CAN bridging. The two **Teensy 4.1 MCUs** ("Motion" handles the
EPAS18 steering ECU, "Pedals" handles throttle DACs + brake actuator + state
machine + J1939 sniffer) sit on a 500 kbps **DBW CAN bus** with the Jetsons.
Three CAN buses are physically isolated for fault domains: DBW (our protocol),
EPAS (DCE Motorsport internal), and the GEM's J1939 vehicle bus (READ-ONLY via
ISO1042). Software is never in the kill path — a hardware E-stop loop drops a
Kilovac LEV200 contactor that physically disconnects 12 V from every actuator
simultaneously.

## Folder map

```
.claude/memory/         5 typed memory files (project, user, feedback, refs)
                        Symlinked from ~/.claude/projects/.../memory/ on every
                        device — one canonical store, mirrored via the repo.
Hardware/               Component selection, wiring diagrams, plug layouts,
                        cart visit checklist, recovered 2020 vendor docs.
                        WIRING_DIAGRAM.md is the canonical wiring reference.
                        OneDrive_1_5-1-2026/ — recovered 2020 artifacts (EPAS18
                        manuals, J1939 PGN dictionary, ARD1939 stack).
Software/               Cart-runtime code:
  firmware/             Teensy 4.1 PlatformIO projects (Motion + Pedals)
                        Common header dbw_can_protocol.h is single source of
                        truth for the CAN protocol (compiled into both
                        firmwares AND the Python bridge).
  autonomy_ws/          ROS 2 workspace that runs on the Jetson:
                          gem_dbw_bridge — Python, /dbw/cmd ↔ SocketCAN can0
                          gem_teleop     — F710 gamepad → /dbw/cmd
Sim/                    Off-cart development sim (Cartagena workspace).
                        DEV-SIDE ONLY. Never run on the Jetson.
bin/                    Helper scripts (sync, setup, install, sim launchers).
Masterplan.md           Long-form plan; Hardware/cart_parameters.md mirrors
                        the canonical xacro values for procurement.
STATUS.md               Current status + week-by-week timeline.
```

## Critical things to remember (non-obvious)

1. **Jetson is a DBW CAN gateway, not a sim host.** Don't try to run Gazebo
   or anything from `Sim/` on the Jetson. See
   `.claude/memory/feedback_jetson_role.md`.
2. **Steering is bench-confirmed** (2026-07-10, steered the column via CAN):
   **DCE Motorsport EPAS18 Ultra**. EPAS bus = **250 kbps, 11-bit IDs**.
   Command ID **0x298**, frame {D0=map: 0=local / 1–5=auto; D1=torque:
   128=center ±64; D2..7=0}, no mirror byte, ~4-bit deadband. The
   **autonomous-firmware gate is CLOSED** (present and works — no purchase
   needed). Reference: `.claude/memory/reference_epas18_ultra.md`.
3. **GEM internal CAN is J1939** (29-bit IDs, 250 kbps), READ-ONLY for us.
   Recovered PGN dictionary: `.claude/memory/reference_gem_e4_j1939_pgns.md`.
   Speed = PGN 65265 byte 4. Gear = PGN 61445 byte 6. Voltage = PGN 61444 byte 4.
4. **Pack voltage is TBD** (48V vs 72V) — confirm before ordering DC-DCs.
5. **The 2020 piduino_v3.ino is a 13-byte "404 NOT FOUND" stub.** Discard.
   Real Arduino code is in `Hardware/OneDrive_1_5-1-2026/Arduino Code/ARD1939/`.
6. **macOS ROS 2 + Gazebo is fragile** — use a Linux box (or the Jetson) for
   cart-runtime work. macOS only has `Sim/preview/` URDF-in-Foxglove for
   visual confirmation.
7. **User wants depth, not breadth.** When planning vehicle/embedded work,
   include concrete part numbers, every wire/connector, prior art (e.g. UIUC
   gem_ws), and physical packaging. See
   `.claude/memory/feedback_planning_depth.md`.

## Build / run commands

| Where | Command | What |
|---|---|---|
| Mac (this dev box) | `bin/sync.sh` | Manual auto-commit + push |
| Mac | `bin/preview_urdf.sh` | Generate flat URDF; open in Foxglove |
| Linux box (fresh) | `bin/setup_linux.sh` | One-shot install ROS 2 + Gazebo + workspace |
| Jetson | `~/run_cart.sh` | Launch the cart-runtime stack manually |
| Jetson | `sudo systemctl start gem-cart-runtime` | Same via systemd (not auto-enabled yet) |
| Jetson firmware | `cd Software/firmware/<motion\|pedals>_teensy && pio run -t upload` | Flash Teensy |

## Cross-device resume

The repo IS the project. To pick up on any new device (laptop, FAU Linux box,
second Mac, etc.):

```bash
git clone https://github.com/AnikS22/golf-cart-code.git ~/Desktop/Golf\ Cart\ Code
cd ~/Desktop/Golf\ Cart\ Code
bin/setup_new_machine.sh    # symlinks Claude memory into the right encoded path
claude                      # memory loads automatically; new session is ~95% caught up
```

Full details: `CROSS_DEVICE_RESUME.md`.

## What's currently working

(Last verified: 2026-07-17.)

- ✅ Jetson Orin NX (Yahboom) at `192.168.55.1`: Ubuntu 22.04, ROS 2 Humble,
     `autonomy_ws` built, `can0` UP @ 500 kbps, `gem_dbw_bridge_node` opens
     can0 cleanly, all `/dbw/*` and `/vehicle/*` topics declared,
     0x100 JETSON_HEARTBEAT byte-perfect verified in loopback.
- ✅ Repo auto-commits + pushes every 10 min via macOS launchd.
- ✅ **Steering bench-confirmed (2026-07-10)**: EPAS18 Ultra steered via CAN
     (0x298 @ 250 kbps, 11-bit). Bench firmware `Software/firmware/steer_test_teensy`
     + `drive.py`, Teensy 4.1 FlexCAN_T4 CAN2 (pin0=RX, 1=TX). DCE autonomous-firmware
     gate CLOSED (present and works).
- ✅ **Brake bench-confirmed (2026-07-17)**: Kar-Tech 1A001HAJ CAN linear
     actuator strokes, position tracks command (SAE J1939, priority-0,
     cmd 0xFF0000 / report 0xFF0001). Bench firmware
     `Software/firmware/brake_test_teensy` + `brake.py` (+ `brake_sniff_teensy`).
     Remaining gap is **mechanical only** — rod not yet coupled to pedal
     (Kar-Tech linkage kit 1A0018A). Reference: `.claude/memory/reference_kartech_brake.md`.
- ⛔ FAU Risk Mgmt approval pipeline not started (long pole).

## Working norms (user prefers)

- **Cite prior art before architectural decisions.** UIUC gem_ws, GEM-Illinois
  sim, our 2020 team's recovered work. Don't rebuild what exists.
- **Plans must be actionable.** Every wire / connector / part number / cable
  length / fuse rating spelled out at procurement detail.
- **End-of-turn summary: 1–2 sentences.** What changed, what's next.
- **Don't auto-create planning/decision/analysis docs unless asked.** Memory
  files are for non-obvious context that future sessions need; they're not
  notebooks for this session's thinking.
- **The user has been burned by abandoned plans before** (this very project
  went dormant 2020–2026). Plans must be self-sufficient.
