# Software

Drive-by-wire firmware (Teensy 4.1) + autonomy stack (Jetson AGX Orin, ROS 2 Humble, Autoware).

Master plan: `~/.claude/plans/i-need-your-help-hashed-dongarra.md` (PART B — Software).

## Folder layout (to populate)

```
Software/
├── firmware/
│   ├── motion_teensy/          # PlatformIO project — EPAS18 CAN bridge
│   ├── pedals_teensy/          # PlatformIO project — throttle DAC, brake, J1939, state
│   └── common/include/
│       ├── dbw_can_protocol.h  # IDs, payload layouts (shared with Jetson bridge)
│       ├── state_machine.h     # DISENGAGED/ARMED/ACTIVE/FAULT
│       └── j1939_pgns.h        # PGN dictionary (recovered from 2020 PGN Data.docx)
├── autonomy_ws/                # ROS 2 Humble colcon workspace (Jetson)
│   └── src/
│       ├── gem_bringup/        # top-level launches
│       ├── gem_description/    # URDF — start from Cartagena gem_e4.urdf.xacro
│       ├── gem_dbw_bridge/     # SocketCAN ↔ ROS 2
│       ├── gem_safety/         # safety supervisor (runs on Orin NX, separate)
│       ├── gem_perception/     # YOLO + SegFormer + LiDAR pipelines
│       ├── gem_localization/   # robot_localization + ndt_scan_matcher config
│       └── gem_autoware_config/ # vehicle_info, sensor_kit, lanelet2 paths
└── tools/                       # CAN sniffer scripts, calibration, dataset utilities
```

## Reference code to mine

- `/Users/mpcr/Downloads/OneDrive_1_5-1-2026/Arduino Code/ARD1939/` — open-source J1939 stack (port to Teensy 4.1 + FlexCAN_T4 for the J1939 sniffer).
- `/Users/mpcr/Downloads/OneDrive_1_5-1-2026/Arduino Code/J1939 Receiving Messages/` — example sketch decoding GEM PGNs.
- `/Users/mpcr/Downloads/Cartagena_GEM_E4_workspace/ros2_ws/src/pure_pursuit/` — pure-pursuit follower (already authored by user). Use as Phase 0–1 controller; migrate to Autoware Phase 2+.
- UIUC reference: `https://github.com/UIUC-Robotics/gem_ws` — sensor driver patterns + launch file structure.

## DBW CAN protocol (canonical — see PART B.4 of plan)

500 kbps, 11-bit IDs, little-endian. Critical IDs: 0x100 Jetson HB · 0x110 STEER_CMD · 0x111 STEER_STATUS · 0x112 STEER_TORQUE_RAW · 0x120 THROTTLE_CMD · 0x121 THROTTLE_STATUS · 0x130 BRAKE_CMD · 0x131 BRAKE_STATUS · 0x140 ESTOP_STATE · 0x150 MCU_HB_MOTION · 0x151 MCU_HB_PEDALS · 0x160 VEHICLE_STATE (J1939 decoded).

EPAS bus IDs (DCE protocol): 0x290 (TX from EPAS, 100 ms — torque/duty/current/V/temp/raw torque), 0x292 (TX from EPAS, 100 ms — angle/map/error/status/limits), 0x298 (RX into EPAS, 5 ms / 200 Hz — map + torque demand).

## Top action items

1. Stand up a PlatformIO env for Teensy 4.1; "blink" both Teensies on a bench.
2. Wire CANable 2.0 to a dev laptop; verify SocketCAN ↔ Teensy CAN with FlexCAN_T4.
3. Port ARD1939 to Teensy 4.1 + FlexCAN_T4 (J1939 sniffer firmware).
4. Stand up ROS 2 Humble + Isaac ROS containers on a Jetson dev board (or x86 dev workstation in interim).
