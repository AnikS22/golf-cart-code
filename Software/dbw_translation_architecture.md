# DBW Translation Architecture — ROS Commands → Real Hardware

How a ROS 2 ackermann command on the Jetson becomes a CAN message that turns the steering wheel and presses the throttle.

The translation is a **three-layer stack**:

```
┌──────────────────────────────────────────────────────────────────────────┐
│ LAYER 3: Autonomy nodes (Autoware / Nav2)                                │
│  publishes:  /control/command/ackermann_cmd  (steering_angle, speed)     │
│              /control/command/gear_cmd       (Forward/Reverse)            │
│              /control/command/turn_indicators_cmd                         │
└──────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ LAYER 2: gem_dbw_bridge ROS node (on AGX Orin)                           │
│  - subscribes to ackermann_cmd, gear_cmd                                  │
│  - splits into steering / throttle / brake setpoints                      │
│  - applies safety gates (master_state must be ACTIVE)                     │
│  - emits 0x100 JETSON_HEARTBEAT @ 50 Hz on DBW CAN                        │
│  - emits 0x110 STEER_CMD, 0x120 THROTTLE_CMD, 0x130 BRAKE_CMD @ 50 Hz     │
│  - subscribes to all *_STATUS frames, republishes as ROS topics           │
│  uses:        SocketCAN (can0) via CANable 2.0 USB                       │
└──────────────────────────────────────────────────────────────────────────┘
                                   │  500 kbps DBW CAN
                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: Teensy firmware (Motion + Pedals)                                │
│  Motion Teensy:                                                           │
│    - receives 0x110 STEER_CMD                                             │
│    - runs outer-loop angle PI: angle_error → torque demand                │
│    - sends 0x296 to EPAS bus @ 200 Hz: D0=map, D1=TorqueA, D2=TorqueB    │
│    - reads 0x290+0x292 from EPAS bus → republishes 0x111+0x112 on DBW    │
│    - monitors raw torque (0x290 D6/D7) for manual override                │
│  Pedals Teensy:                                                           │
│    - receives 0x120 THROTTLE_CMD → I²C to MCP4725 DACs (mirrored pair)   │
│    - receives 0x130 BRAKE_CMD → PWM to BTS7960 → linear actuator         │
│    - reads ESTOP loop, brake-light tap, wheel-touch sensor                │
│    - reads J1939 vehicle bus (PGN 65265, 61445, 61444) → 0x160           │
│    - runs master state machine                                            │
└──────────────────────────────────────────────────────────────────────────┘
                                   │  Hall-pair voltages, EPAS CAN, GPIO
                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ LAYER 0: Real hardware                                                    │
│  EPAS18 Ultra ECU → motor → steering column → wheels                      │
│  GEM traction controller (Sevcon/Curtis) → drive motor → wheels           │
│  Brake actuator → Bowden cable → brake pedal                              │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Latency budget (end-to-end command)

| Hop | Latency |
|---|---|
| Autoware ackermann_cmd publish → bridge subscribe | ~5 ms (DDS) |
| Bridge formats CAN frame, writes to SocketCAN | ~1 ms |
| CANable USB → DBW bus (transmit) | ~2 ms |
| Motion Teensy receives, runs PI loop | ~5 ms (1 cycle of 200 Hz) |
| Motion Teensy formats 0x296, transmits to EPAS bus | ~1 ms |
| EPAS18 ECU receives, updates motor demand | ~5 ms (1 cycle of 200 Hz internal) |
| Motor + column mechanical response | 50–200 ms (steering inertia) |
| **Total e2e steering** | **~70–220 ms (mechanically dominated)** |
| **Total e2e throttle** | **~15 ms (electronically dominated)** |

This budget is well within the >100 ms typical for ackermann-bicycle planners at 5–15 mph.

---

## Unit conversions (the actual math)

### Steering: ROS angle (rad) → EPAS torque demand (bits)

ROS publishes steering angle in **radians at the front road wheels** (ackermann convention). Convert to EPAS demand:

```
1. Compute steering wheel angle:
     wheel_rad = road_rad × steering_ratio        # GEM steering ratio ~ 16:1 (TBD measure)
2. Convert to centi-degrees (DBW protocol):
     cmd_centideg = round(wheel_rad × (18000/π))
3. Pack into 0x110 STEER_CMD as i16.

Motion Teensy receives 0x110:
4. Read measured angle from cached 0x292 D0:
     measured_centideg = (msg2.D0 - 128) × calibration_scale   # tune to match real angle
5. Compute error:
     err_centideg = cmd_centideg - measured_centideg
6. PI controller:
     torque_demand = clip( Kp * err + Ki * integral(err), -64, 64 )
7. Pack to EPAS Msg #3:
     map = 2  (start with map 2; tune up to 3-4 if response too slow)
     TorqueA = 128 + torque_demand          # (range 64-192)
     TorqueB = 255 - TorqueA                # (mirror)
8. Transmit at 200 Hz to EPAS bus.
```

The PI gains start small (Kp = 0.2 bit/centideg, Ki = 0.05) and tune by step-response on the bench. EPAS internal motor loop handles the actual current/PWM — we are commanding **torque demand**, not motor PWM directly. EPAS18 maps the torque demand through its selected steering map (1–5) into motor duty.

### Throttle: ROS speed (m/s) → DAC voltage (mV)

ROS publishes target speed (m/s). The bridge uses a **simple speed PI** to derive throttle command (because the GEM has no native ROS-acceptable throttle linearization):

```
1. Read current speed from /vehicle_state (J1939 PGN 65265, mph):
     speed_mps = mph * 0.44704
2. Compute speed error:
     err = target_mps - speed_mps
3. PI:
     throttle_permil = clip( Kp_v * err + Ki_v * integral(err), 0, 1000 )
4. Pack into 0x120 THROTTLE_CMD as u16.

Pedals Teensy receives 0x120:
5. Look up DAC pair from calibration map (built once by sweeping the real pedal):
     v1_mV = throttle_to_v1[throttle_permil]      # e.g. linear: 800 + (3400 * permil/1000)
     v2_mV = throttle_to_v2[throttle_permil]      # mirror: 4200 - (3400 * permil/1000)
6. Write to MCP4725 DACs over I²C.
7. Op-amps buffer to match Hall-pair source impedance.
8. DPDT relay (energized in ACTIVE) routes DAC outputs to traction controller.
9. Traction controller sees what it thinks is a depressed pedal → drives the motor.
```

Calibration map is generated by Pedals Teensy in a one-time bench routine: have a human slowly press the pedal 0→100% while the Teensy logs Hall V1/V2. Save as a 1024-element LUT to EEPROM.

### Brake (Phase 2): ROS brake (0–1) → actuator position (mm)

```
1. ROS publishes /control/command/brake_cmd as 0..1.
2. Bridge packs as u16 permil (0..1000) into 0x130.
3. Pedals Teensy receives, converts to actuator position:
     target_pos_mm = brake_permil/1000 * MAX_STROKE_MM    # e.g. 0..40 mm pull
4. Inner PID loop on the BTS7960 driving actuator to target_pos using pot feedback.
5. Cable pulls brake pedal lever; pedal pivots; master cylinder applies hydraulic pressure.
6. Driver can always press deeper (mechanical override).
```

---

## Safety gates (every command passes through)

A command at any layer is **silently dropped** (output zeroed) if any of these is false:

| Gate | Where checked |
|---|---|
| `master_state == ACTIVE` | Pedals Teensy state machine |
| Jetson HB seen in last 100 ms | Both Teensies (independent watchdogs) |
| HW E-stop loop is closed (Kilovac energized) | Hardware path (no software check needed) |
| Brake pedal not pressed | Pedals Teensy GPIO interrupt |
| Steering wheel not touched (cap-touch OR raw torque spike) | Motion Teensy + Pedals Teensy both monitor |
| EPAS no-fault (msg #2 D4 == 0) | Motion Teensy |
| J1939 vehicle gear == Forward (or Reverse if commanded) | Bridge node |

Multiple layers of redundant checking is **the design**, not over-engineering. The primary safety case for unmanned (Phase 4) is "no single point of software failure can cause unintended motion."

---

## Failure modes and recovery

| Failure | Detection | Response |
|---|---|---|
| Jetson process crashes | Both Teensies see HB stop → 100 ms watchdog | Throttle ramps to 0 over 50 ms; steering holds last for 200 ms then coasts; brake (Ph 2) commands 30%; master_state → FAULT |
| AGX Orin hardware wedges | Orin NX safety supervisor sees primary HB stop on local network | Safety supervisor publishes E-stop on a separate CAN ID; commands controlled stop |
| DBW CAN bus errors flood | Teensies' CAN error counters spike | Master_state → FAULT; throttle 0; steering local mode |
| EPAS18 throws fault (msg #2 D4 != 0) | Motion Teensy reads error code | Republish on DBW (0x111 D5); master_state → FAULT if E1xx is severe |
| EPAS firmware NOT autonomous variant | Motion Teensy commands 0x296 but msg #2 D7 b7 (remote mode active) stays 0 | At startup, Motion Teensy sets fault flag IMMEDIATELY → never reach ACTIVE state. Refuse to engage. |
| Throttle DAC mismatch (V1 + V2 inconsistent) | Traction controller faults; no motion | Pedals Teensy detects via no `/vehicle_state` speed change despite throttle command → fault |
| Driver grabs steering wheel | Motion Teensy detects raw torque spike | Set 0x296 D0=0 within 50 ms; master_state → DISENGAGED; latched until re-arm |
| Driver presses brake pedal | Pedals Teensy GPIO via brake-light optoisolator | Throttle = 0; master_state → DISENGAGED; latched |
| HW E-stop pressed | Loop opens, Kilovac drops | All actuator power drops physically; software learns about it via 0x140 ESTOP_STATE |

---

## Test order (firmware before vehicle)

1. **Bench** — Both Teensies, CANable, laptop running candump. Verify all CAN messages round-trip per protocol header.
2. **EPAS bench** — EPAS18 + EPAS01 column on a bench (off cart). Motion Teensy commands 0x296 with map=2, slow torque sweep. Verify msg #2 angle response.
3. **Throttle bench** — Pedals Teensy + DAC + op-amp + relay on a breadboard. Scope outputs at all throttle_permil values, compare to recorded pedal sweep.
4. **J1939 sniff** — Tap GEM diag port (key on, cart on stands), capture 10 min, decode all PGN messages, verify against dashboard.
5. **Cart wheels-off-ground** — All hardware installed. Joystick → bridge → Teensies → cart. Step inputs in steering, throttle ramps, manual override.
6. **Closed-lot 3 mph** — first-light slow drive. Safety driver hands hovering.

Don't skip the bench tests. Most embedded vehicle bring-up disasters happen because someone said "let's just try it on the cart."
