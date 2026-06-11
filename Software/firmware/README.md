# Firmware

Two PlatformIO projects, one per Teensy 4.1, plus the canonical CAN protocol header shared with the Jetson-side bridge.

```
firmware/
├── common/
│   └── include/
│       └── dbw_can_protocol.h     # canonical C header — same payload structs
│                                  # used by both Teensy firmware AND the
│                                  # Jetson gem_dbw_bridge (C++)
├── motion_teensy/                 # PlatformIO project — Steering Aux Box
│   ├── platformio.ini
│   └── src/
│       └── main.cpp               # EPAS18 CAN bridge + outer steering PI
└── pedals_teensy/                 # PlatformIO project — Pedals Aux Box
    ├── platformio.ini
    └── src/
        └── main.cpp               # Throttle DAC, brake actuator (Phase 2),
                                   # J1939 read-only sniffer, master state
                                   # machine, E-stop / brake / wheel-touch
                                   # monitoring
```

## Build (when parts arrive)

```bash
# In each project:
cd Software/firmware/motion_teensy
pio run                            # compile
pio run -t upload                  # flash (Teensy plugged in via USB)
pio device monitor -b 115200       # serial console
```

## Bench test (no cart needed)

```bash
# Plug in CANable 2.0 to your laptop
sudo ip link set can0 up type can bitrate 500000

# In one terminal — see all DBW-bus traffic
candump -tz can0

# In another terminal — fake a Jetson heartbeat at 50 Hz so the Teensies
# don't watchdog out
cangen -I 100 -L 8 -D AABBCCDDEEFF0000 -g 50 can0

# Press the dash ARM button (or short the GPIO with a wire);
# watch state transitions on the serial console.
```

## What each Teensy does

### Motion Teensy
- **Two CAN buses**: CAN1 = DBW (Jetson + Pedals), CAN2 = EPAS (DCE Motorsport ECU). Bridges between them in firmware (no physical bridge for fault isolation).
- **TX 0x296 to EPAS at 200 Hz** with map + torque demand pair. Outer PI loop drives angle error → torque demand. Inner motor-current loop is closed inside the EPAS18 ECU itself.
- **RX 0x290 + 0x292 from EPAS at 100 Hz**, cache state, republish on DBW as 0x111 (STEER_STATUS) and 0x112 (STEER_TORQUE_RAW).
- **Manual override detection**: monitor raw torque bits in 0x290 D6/D7. Spike = driver grabbed wheel → set 0x296 D0 = 0 (local mode) within 50 ms → master state DISENGAGED.
- **Heartbeat 0x150 at 50 Hz**. Jetson HB lost (no 0x100 in 100 ms) → fault, release EPAS.

### Pedals Teensy
- **Three CAN buses**: CAN1 = DBW, CAN2 = GEM J1939 (read-only via ISO1042 isolator), CAN3 = Kartech J1939 brake bus.
- **Throttle DAC**: 2× MCP4725 over I²C, mirrored to match GEM Hall pair. DPDT failsafe relay (Omron G8HE) routes pedal-or-DAC to traction controller.
- **J1939 sniffer**: decode PGN 65265 (vehicle speed, mph), 61445 (gear: F/N/R/Charging), 61444 (voltage). Republish on DBW as 0x160 VEHICLE_STATE @ 50 Hz.
- **Master state machine**: DISENGAGED → ARMED → ACTIVE → FAULT. ARM requires no faults + brake not pressed + wheel not touched. ENGAGE requires ARMED + Jetson HB OK.
- **Safety inputs**: dash E-stop GPIO, brake-light optoisolator, wheel-touch via MPR121 cap-sense.
- **Brake actuator**: Kartech 1A001HAJ via J1939 (PGN 65280) on CAN3. Proportional position control via `kartech::send_brake_permil()` at 50 Hz. Kartech runs its own closed-loop servo internally — no PID in our firmware.
- **Heartbeat 0x151 at 50 Hz**, ESTOP_STATE 0x140 at 50 Hz.

## Watchdog and safety gates (both Teensies)

Independent hardware watchdog (`WDT_T4`) at 50 ms timeout. Pet every loop. Any of these → drop master_state to FAULT (sticky, key cycle to clear):

- Jetson heartbeat (0x100) absent for >100 ms.
- Other Teensy's heartbeat absent for >100 ms.
- Hardware E-stop loop opens.
- Brake pedal pressed (instant DISENGAGE → re-arm to recover).
- EPAS18 reports error code (msg #2 D4 ≠ 0).
- Steering wheel manually touched while ACTIVE.
