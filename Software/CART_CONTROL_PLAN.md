# Cart control plan (no autonomy, no perception)

End-to-end manual ROS-based control of the GEM E4. **No SLAM, no cameras, no LiDAR, no path planning.** Just: gamepad → laptop → CAN → Teensies → cart. Phase 0c of the master plan ("RC first-light" — Week 4 of the timeline).

If you can finish this, you have a remote-controlled drive-by-wire golf cart that drives anywhere a person can drive it from a gamepad. Everything autonomous gets built on top of this same pipe later.

---

## What you're building

```
   Logitech F710 gamepad (USB)
            │
            ▼
   ┌─────────────────────────────────────┐
   │     LAPTOP                          │
   │     Ubuntu 22.04 + ROS 2 Humble    │
   │                                     │
   │   joy_node ──/joy──>                │
   │   joy_to_ackermann ──/dbw/cmd──>    │
   │   gem_dbw_bridge ──CAN frames──>    │
   └────────────────┬────────────────────┘
                    │ USB
            ┌───────▼────────┐
            │  CANable 2.0   │
            └───────┬────────┘
                    │ DBW CAN @ 500 kbps (twisted pair)
        ┌───────────┴───────────┐
        │                       │
   ┌────▼──────────┐    ┌───────▼──────────┐
   │ Motion Teensy │    │  Pedals Teensy   │
   │   firmware    │    │     firmware     │
   └────┬──────────┘    └─┬───────┬────┬───┘
        │ EPAS bus         │ I²C   │GPIO│ J1939 read
        ▼                  ▼       ▼    ▼
   EPAS18 ECU        2× MCP4725  Relay  GEM CAN
        │            DAC pair    DPDT   diag port
        ▼                │          │
   Steering motor       op-amps    pedal harness tap
        │                 │          │
        ▼                 ▼          ▼
   STEERING WHEELS  →  TRACTION CONTROLLER  (driver brake = foot)
```

Brake actuator (Bowden cable / linear actuator) is **NOT** in this Phase 1 plan — driver brakes with their foot. Phase 2 adds it.

---

## 1. Hardware

### 1.1 What you need (Phase 1 control only)

| # | Item | Pick | Approx $ | Where it lives |
|---|---|---|---|---|
| 1 | MCU (×2) | Teensy 4.1 | $30 ea | Steering Aux Box, Pedals Aux Box |
| 2 | CAN transceiver (×3) | TJA1051T/3 breakout | $4 ea | one per Teensy CAN port we use |
| 3 | USB↔CAN dongle | CANable 2.0 (candleLight firmware) | $45 | laptop |
| 4 | DAC (×2) | Adafruit MCP4725 breakout | $5 ea | Pedals Aux Box |
| 5 | Op-amp (×2 chips) | MCP6002 dual rail-to-rail | $1 ea | Pedals Aux Box |
| 6 | Failsafe relay | Omron G8HE-1A7T DPDT auto, 12 V coil | $7 | Pedals Aux Box |
| 7 | Isolated J1939 transceiver | TI ISO1042 breakout | $10 | Pedals Aux Box |
| 8 | E-stop button (×2) | IDEC XA1E-BV4U02R 22 mm NC | $20 ea | dash + passenger |
| 9 | Safety contactor | TE Kilovac LEV200 (200 A, 12 V coil) | $90 | Under-Seat Safety Box |
| 10 | Master fuse | 80 A ANL inline | $8 | next to Kilovac |
| 11 | 5 V buck (×2) | Pololu D24V50F5 (5 A) | $15 ea | one per Aux Box |
| 12 | Dash buttons (×3) | momentary 22 mm illuminated (ARM/ENGAGE/DISENGAGE) | $8 ea | dash console |
| 13 | Gamepad | Logitech F710 wireless USB | $30 | with operator |
| 14 | Laptop | any ≥4-core Ubuntu 22.04 box, USB-A or USB-C | $500–$2000 | sits in passenger seat |
| 15 | Wire / Deutsch DT04 / heatshrink / loom | misc | $200 | wiring channels |

**Total: ~$700.** Substantially less than the full sensor build.

### 1.2 Steering Aux Box (firewall, in cabin near EPAS18 ECU)

```
  ┌─────────────── Steering Aux Box (IP54, 150×100×60 mm) ────────────────┐
  │                                                                        │
  │  Teensy 4.1                                                            │
  │   ├─ pin 22 (CAN1 TX) ────┐                                            │
  │   ├─ pin 23 (CAN1 RX) ────┼─→ TJA1051T/3 #1 ─→ DBW CAN bus (DT04-4P)   │
  │   ├─ pin 0  (CAN2 RX) ────┐                                            │
  │   ├─ pin 1  (CAN2 TX) ────┼─→ TJA1051T/3 #2 ─→ EPAS bus (DT04-4P) ─→  │
  │   │                                              EPAS18 ECU pins 19/20│
  │   ├─ pin 13 (LED)                                                      │
  │   ├─ pin 14 (FAULT_OUT, optional)                                      │
  │   └─ +5V / GND from Pololu D24V50F5 buck                              │
  │                                                                        │
  │  Pololu D24V50F5: 12V in (from Safety Box) → 5V out → Teensy + xcvrs  │
  │                                                                        │
  └────────────────────────────────────────────────────────────────────────┘
```

External connections:
- **DBW CAN connector**: DT04-4P. Pinout: 1=CAN-H, 2=CAN-L, 3=GND, 4=12V (passes through, not consumed here)
- **EPAS bus connector**: DT04-4P to the EPAS18's signal connector (Autosport AS614-35SN pins 19/20 or 29/30; both pairs are linked internally in the ECU)
- **Power**: 12V from Safety Box (post-Kilovac). 0.5 A peak.

### 1.3 Pedals Aux Box (firewall above pedals)

```
  ┌──────────────── Pedals Aux Box (IP54, 150×100×60 mm) ────────────────┐
  │                                                                       │
  │  Teensy 4.1                                                           │
  │   ├─ pin 22/23 ──→ TJA1051T/3 #3 ──→ DBW CAN bus                     │
  │   ├─ pin  0/ 1 ──→ ISO1042 ──→ GEM J1939 diag port (READ ONLY)       │
  │   ├─ pin 18 (SDA) ──┐                                                 │
  │   ├─ pin 19 (SCL) ──┼─→ MCP4725 #1 (addr 0x60) ─→ MCP6002 buf #1 ─→  │
  │   │                  │                                  V1 to relay   │
  │   │                  └─→ MCP4725 #2 (addr 0x61) ─→ MCP6002 buf #2 ─→  │
  │   │                                                       V2 to relay │
  │   ├─ pin 2  (RELAY_COIL) ──→ MOSFET ──→ G8HE coil                     │
  │   ├─ pin 3  (BTN_ARM)     ←── dash ARM button                         │
  │   ├─ pin 4  (BTN_ENGAGE)  ←── dash ENGAGE button                      │
  │   ├─ pin 5  (BTN_DISENG)  ←── dash DISENGAGE button                   │
  │   ├─ pin 6  (ESTOP_SENSE) ←── E-stop loop sense (HIGH=closed)         │
  │   ├─ pin 7  (BRAKE_PEDAL) ←── PC817 optoiso ←── GEM brake light wire  │
  │   ├─ pin 8  (WHEEL_TOUCH) ←── MPR121 IRQ (if cap-touch installed)     │
  │   ├─ pin 9  (BRAKE_PWM_R) ──→ unused Phase 1 (Phase 2: BTS7960 RPWM)  │
  │   ├─ pin 10 (BRAKE_PWM_L) ──→ unused Phase 1                          │
  │   ├─ pin 13 (LED status)                                              │
  │   └─ +5V / GND from Pololu D24V50F5                                   │
  │                                                                       │
  │  G8HE DPDT relay (energized = autonomy):                              │
  │   COM-A ─── pedal Hall #1 ──┐ NC ─── traction controller V1 (default) │
  │                              ┘ NO ─── DAC1 buf out                    │
  │   COM-B ─── pedal Hall #2 ──┐ NC ─── traction controller V2 (default) │
  │                              ┘ NO ─── DAC2 buf out                    │
  │                                                                       │
  └───────────────────────────────────────────────────────────────────────┘
```

External connections:
- **DBW CAN connector**: DT04-4P
- **J1939 tap**: 2-cond shielded into GEM diag port (CAN-H + CAN-L only; GND via chassis)
- **Pedal harness**: cut into existing GEM throttle connector. T-junction:
  - Pedal Hall #1 → relay COM-A
  - Pedal Hall #2 → relay COM-B
  - Traction controller V1 in → relay NC-A (resting) / NO-A (DAC active)
  - Traction controller V2 in → relay NC-B / NO-B
  - +5 V / GND pass-through (pedal still gets power so even pedal sweeps the original sensors)
- **Brake light tap**: 2-conductor from GEM brake light switch through PC817 optoisolator
- **Power**: 12 V from Safety Box. Relay coil draws 30 mA peak.

### 1.4 Under-Seat Safety Box

```
  ┌───────────────── Safety Box (IP54, 200×150×80 mm) ────────────────┐
  │                                                                    │
  │  Aux 12 V battery (+) ─── 80 A ANL fuse ─── Kilovac LEV200 (input)│
  │                                                                    │
  │  Kilovac coil (+):  E-STOP LOOP (2× mushroom NC in series)         │
  │                     + Wireless RX safety contact (Phase 4) ──┐     │
  │  Kilovac coil (−):  GND                                       │     │
  │                                                                │     │
  │  Kilovac output (+): ──→ 12 V to Steering Aux Box              │     │
  │                       ─→ 12 V to Pedals Aux Box                │     │
  │                       ─→ 12 V to relay coils + brake actuator  │     │
  │                                                                      │
  │  E-stop loop (open = drop everything):                              │
  │    +12V → Dash mushroom (NC) → Passenger mushroom (NC) → coil(+)   │
  │                                                                    │
  └────────────────────────────────────────────────────────────────────┘
```

**Software is NEVER in the kill path.** Open the loop → Kilovac drops → all DBW power dies physically.

### 1.5 Dash Console (in cabin)

3 buttons + 1 mushroom + status LEDs:

```
  ┌────────── Dash Console ──────────┐
  │                                  │
  │  [ ARM ]  [ ENGAGE ]  [ DISENG ] │  ← momentary, illuminated, 22 mm
  │                                  │
  │  ●ARMED ●ACTIVE ●FAULT ●LINK     │  ← status LEDs from Pedals Teensy GPIO
  │                                  │
  │  ┌──────────────┐                │
  │  │ MUSHROOM     │ ← NC, in       │
  │  │ E-STOP       │   E-stop loop  │
  │  └──────────────┘                │
  └──────────────────────────────────┘
```

All button leads route to Pedals Aux Box via Channel D (driver-side floor under trim). 16-conductor 22 AWG MIL-spec bundle, DT04-12P at the box.

### 1.6 Cable runs (skinny version of `Masterplan.md` PART A.14)

| Channel | From → To | Length | What's in it |
|---|---|---|---|
| **D** | Dash → Pedals Aux Box / under-seat Safety Box | 2 m | Buttons, LEDs, E-stop loop |
| **S₁** | Pedals Aux Box → Pedal harness tap | 0.3 m | DAC outputs, brake light optoiso |
| **S₂** | Pedals Aux Box → GEM J1939 diag port | 0.5 m | Shielded twisted pair, tap only |
| **S₃** | Pedals Aux Box → Steering Aux Box | ~1.5 m | DBW CAN bus continuation |
| **S₄** | Steering Aux Box → EPAS18 ECU | 0.3 m | EPAS CAN; passes through ECU's signal connector |
| **PWR** | Safety Box → Steering + Pedals Aux Boxes | ~2 m | 12 V + GND, 14 AWG |
| **(LAPTOP)** | Laptop CANable → DBW CAN bus | 1 m | USB on one end, DBW DT04-4P pigtail on the other |

---

## 2. Software

### 2.1 What runs where

| Compute | OS | Job |
|---|---|---|
| **Laptop** (carried in cart) | Ubuntu 22.04 | ROS 2 Humble + nodes (joy, joy_to_ackermann, gem_dbw_bridge) |
| **Motion Teensy** (Aux Box) | Bare-metal Arduino-Teensy | EPAS18 CAN bridge + steering PI |
| **Pedals Teensy** (Aux Box) | Bare-metal Arduino-Teensy | Throttle DAC, state machine, J1939 sniffer |

The laptop is the brain. Without it the cart is a normal manual cart (relay de-energized = pedal direct).

### 2.2 Code map — what lives where

| Path | Role | Status |
|---|---|---|
| `Software/firmware/common/include/dbw_can_protocol.h` | Canonical CAN protocol C header. Compiled into both Teensy firmwares AND mirrored as Python constants in the bridge. **Source of truth.** | ✅ Done |
| `Software/firmware/motion_teensy/src/main.cpp` | Motion Teensy firmware. EPAS bridge + steering PI. Compiles with PlatformIO. | ✅ Done |
| `Software/firmware/pedals_teensy/src/main.cpp` | Pedals Teensy firmware. Throttle DAC, state machine, J1939 sniffer, all GPIO monitoring. | ✅ Done |
| `Software/autonomy_ws/src/gem_dbw_bridge/` | ROS 2 Python package. The bridge running on the laptop. Subscribes to `/dbw/cmd`; publishes CAN frames on `can0`. | ✅ Done (this commit) |
| `Software/autonomy_ws/src/gem_teleop/` | ROS 2 Python package. F710 gamepad → AckermannDriveStamped on `/dbw/cmd`. State machine button mapping. Deadman trigger. | ✅ Done (this commit) |
| `bin/setup_can_bus.sh` | Brings up `can0` at 500 kbps via SocketCAN. | ✅ Done (this commit) |

### 2.3 ROS topic map

| Topic | Type | Direction | Description |
|---|---|---|---|
| `/joy` | sensor_msgs/Joy | gamepad → joy_to_ackermann | Buttons + axes from F710 |
| `/dbw/cmd` | ackermann_msgs/AckermannDriveStamped | joy_to_ackermann → gem_dbw_bridge | Speed (m/s) + steering angle (rad at road wheel) |
| `/dbw/enable` | std_msgs/Bool | (any) → gem_dbw_bridge | Software arm gate |
| `/vehicle/master_state` | std_msgs/UInt8 | gem_dbw_bridge → world | DISENGAGED=0/ARMED=1/ACTIVE=2/FAULT=3 (echoed from CAN) |
| `/vehicle/speed_mps` | std_msgs/Float32 | gem_dbw_bridge → world | From J1939 PGN 65265 |
| `/vehicle/gear` | std_msgs/UInt8 | gem_dbw_bridge → world | Forward/Neutral/Reverse/Charging |
| `/vehicle/voltage_v` | std_msgs/Float32 | gem_dbw_bridge → world | Pack voltage from J1939 |
| `/vehicle/fault_flags` | std_msgs/UInt8 | gem_dbw_bridge → world | Bitfield matching `dbw_can_protocol.h` |

### 2.4 Boot sequence

On the cart:
1. Turn ignition key on → Kilovac coil energizes (E-stop loop closed) → 12V to Aux Boxes → Teensies boot, idle in DISENGAGED.

On the laptop:
1. Plug CANable into USB. Plug F710 dongle into USB.
2. `cd ~/Desktop/Golf\ Cart\ Code/Software/autonomy_ws`
3. `bin/setup_can_bus.sh` — brings up `can0` at 500 kbps.
4. `colcon build --symlink-install` (first time only).
5. `source install/setup.bash`
6. `ros2 launch gem_teleop teleop.launch.py`
   - Starts: `joy_node`, `joy_to_ackermann_node`, `gem_dbw_bridge_node`.
   - Console shows: `gem_dbw_bridge: opened can0 at 500000 bps; publishing JETSON_HEARTBEAT @ 50 Hz`.

In the cart cabin:
1. Watch dash LEDs. ARMED LED off, ACTIVE LED off, FAULT LED off, LINK LED on.
2. Press **dash ARM button**. ARMED LED comes on. (Pedals Teensy verifies: brake pedal not pressed, no faults, Jetson HB seen.)
3. Press **dash ENGAGE button**. ACTIVE LED comes on. Throttle relay energizes — pedal is now bypassed.
4. **Hold the gamepad's Right Bumper as deadman**. Without it, joy_to_ackermann publishes zeros.
5. Left stick X → steering. Right Trigger → throttle. (Brake = your foot.)
6. To stop: release Right Bumper, press DISENGAGE (or B button on gamepad), or press the dash mushroom E-stop.

### 2.5 Test order — never skip

1. **Bench** with both Teensies + CANable + dummy 12 V supply. Verify:
   - `candump can0` shows JETSON_HEARTBEAT @ 50 Hz, MCU_HB_MOTION + MCU_HB_PEDALS @ 50 Hz, ESTOP_STATE @ 50 Hz.
   - Press dash ARM button → state goes 0 → 1 in MCU_HB_PEDALS.
   - Press ENGAGE → state goes 1 → 2.
   - Open the E-stop loop (disconnect a wire) → state goes to 3 (FAULT).
2. **Throttle bench** — DAC outputs into a scope. Sweep `THROTTLE_CMD` 0 → 1000 via a custom CAN script; verify both DAC voltages mirror the calibrated pedal map.
3. **EPAS bench** (if you can detach the column for bench work — usually not feasible) — alternative is just to validate timing/voltage on a scope at the EPAS connector.
4. **Cart wheels-off-ground**:
   - Front jack stands so wheels can spin. Cart NOT moving.
   - Turn key on, run laptop stack.
   - Press ARM, ENGAGE.
   - Tiny throttle (right trigger 5%) → wheels turn slowly. **Listen for unusual noise.**
   - Steer left/right via gamepad → road wheels turn ±a few degrees. **Stop immediately if motor groans or stops responding.**
   - Press DISENGAGE.
5. **Closed lot, 3 mph cap, safety driver in seat, foot near brake pedal:**
   - Empty parking lot. Hard speed cap in `pedals_teensy/main.cpp:438` is 250 permil ≈ 5 mph; for first drive, comment it down to 100 permil ≈ 2 mph.
   - Drive a square. Drive a figure-8. Hit dash E-stop at speed → cart should coast (no software brake yet).

---

## 3. What you'll buy first (Tier 1, ~$250)

This subset is the minimum for bench bring-up before going to the cart:

- 2× Teensy 4.1 ($60)
- CANable 2.0 ($45)
- 3× TJA1051T/3 breakout ($12)
- 2× MCP4725 ($10)
- MCP6002 ($1)
- Omron G8HE-1A7T ($7)
- ISO1042 breakout ($10)
- Pololu D24V50F5 (×2) ($30)
- Belden 9841 wire (10 m) ($20)
- Deutsch DT04-4P kit (10 connectors) ($35)

Order this Wednesday after your cart visit.

---

## 4. After RC drive works: what's next

| Phase | Adds |
|---|---|
| 1c (current plan) | Manual gamepad → ROS → Teensies → cart. **Steer + throttle. No brake. ≤5 mph.** |
| 1d | Replace gamepad with a tablet UI (Foxglove/RViz). Same `/dbw/cmd` interface. |
| 1e | Add cameras + LiDAR + GNSS. Teleop with vision feedback. |
| 2 | **Brake actuator** (PA-14P). Closed-loop autonomous stops. ~Week 9. |
| 2b | Autoware Universe for path following. Same `/dbw/cmd` interface — no re-wire. |
| 3 | Perception / pedestrian behaviors. |
| 4 | Unmanned readiness (parking-brake solenoid, wireless E-stop). |

The architecture in this doc is the **floor** for everything autonomous later. Get this rock-solid first.
