# Project Primer — Everything you need to know, no fluff

Read this once. ~20 minutes. After, you'll be able to look at the cart, the repo, and the wiring diagrams and actually know what you're looking at.

---

## 1. The 30-second version

We're turning a 2018 Polaris GEM E4 (a 4-seat electric golf-cart-grade vehicle) into a self-driving cart that operates around FAU Boca campus. It will see the world with cameras + a LiDAR, decide what to do with software running on an NVIDIA Jetson computer, and physically drive itself by sending commands over a wire to the cart's steering / throttle / brake. Phase 1 has a human safety driver in the seat. Phase 4 has no human at all.

The whole project is a layer cake. Top layer is autonomy (vision, planning). Bottom layer is the mechanical/electrical interface to the cart (motors, brakes). We're building from the bottom up.

---

## 2. The cake — what each layer does

```
┌─────────────────────────────────────────────────┐
│  L4  AUTONOMY            "where do I go?"      │ ← cameras, LiDAR, planner
├─────────────────────────────────────────────────┤
│  L3  DRIVE-BY-WIRE       "send command"        │ ← ROS node on Jetson
├─────────────────────────────────────────────────┤
│  L2  MICROCONTROLLER     "translate to action" │ ← Teensy 4.1 firmware
├─────────────────────────────────────────────────┤
│  L1  ACTUATOR INTERFACE  "fool the cart"       │ ← DAC chips, relays, EPAS ECU
├─────────────────────────────────────────────────┤
│  L0  THE CART            "go forward"          │ ← motor, wheels, brakes
└─────────────────────────────────────────────────┘
```

Each layer only talks to the layer above and below it. That's deliberate — it means we can swap any one layer without rewriting the others. ML model better at perception? Swap L4 only. Phase 2 adds a brake actuator? Swap L1 only.

---

## 3. The hardware pieces, in plain English

### NVIDIA Jetson (the brain)
A small Linux computer with a strong GPU. You already have one — the **Yahboom Jetson Orin NX Super** (~$700 retail). It runs ROS 2 (a robot software framework) and our Python code. Eventually for Phase 2+ we add an **AGX Orin** (bigger, ~$2k) for heavier perception, with the Orin NX you have demoted to "safety supervisor."

### Teensy 4.1 (the muscle reflexes)
A microcontroller — basically a tiny computer that runs ONE program forever in real-time, with no operating system getting in the way. ~$30 each. We use TWO:

- **Motion Teensy** — talks to the steering motor's brain (the EPAS18 ECU). Job: "Jetson said steer +5°, here's the torque command."
- **Pedals Teensy** — talks to the throttle and brake. Job: "Jetson said 30% throttle, write the right voltage to the DAC chip."

We use Teensies (not the Jetson itself) for actuator control because microcontrollers have **deterministic timing**. A Linux box can pause for 200 ms randomly to do garbage collection — bad if you're commanding a wheel. Microcontrollers can't.

### EPAS18 Ultra ECU (the steering brain — ALREADY ON THE CART)
EPAS = Electric Power Assisted Steering. Originally for race cars / kit cars; the 2020 FAU team installed one on this cart. It has its OWN motor (called EPAS01 column) that grips the steering shaft, its OWN torque sensor that feels how hard you turn the wheel, and its OWN computer (the ECU) that decides how much to help. We just feed it commands over CAN bus and it does the steering.

**Important**: it needs a special "autonomous firmware" variant from the manufacturer (DCE Motorsport, UK) — without it, the ECU only operates as power-assist (helps a human turn the wheel), not as autonomous control. We need to confirm this firmware is loaded; that's a pending email.

### Traction controller (the cart's gas-pedal brain — ALREADY ON THE CART)
The big gold finned heatsink box in your photo. It's a **Sevcon Gen4** (or Curtis 1238). It takes the throttle pedal's voltage signal and decides how much power to send to the drive motor. We don't replace it — we **fool it** by injecting fake voltage signals instead of the pedal's real ones.

### CAN bus (the cart's nervous system)
**CAN = Controller Area Network.** It's a two-wire network designed in the 1980s for cars. Every device on the bus can broadcast short messages (max 8 bytes of data) tagged with a numeric ID. Other devices that care about that ID listen.

We have THREE CAN buses (kept physically separate so one fault doesn't crash everything):
- **DBW bus** (500 kbps) — our private bus: Jetson ↔ both Teensies. Our protocol, our message IDs.
- **EPAS bus** (500 kbps) — between the Motion Teensy and the EPAS18 ECU. DCE Motorsport's protocol.
- **Vehicle J1939 bus** (250 kbps, READ-ONLY) — the GEM's own internal CAN. We can listen but **never** transmit on it, because writing to the wrong message could brick the traction controller.

### MCP4725 DAC (the throttle voltage faker)
DAC = Digital-to-Analog Converter. It's a $5 chip that takes a digital number (0-4095) and produces a precise analog voltage. We use TWO (because the GEM throttle pedal has TWO Hall sensors that mirror each other). The Pedals Teensy says "I want 30% throttle" → DACs output the same voltages the pedal would have at 30% press → traction controller sees a "pressed pedal" → cart accelerates.

### DPDT failsafe relay (the safety switch)
DPDT = Double-Pole, Double-Throw. A relay is an electrically-controlled switch. This one chooses between TWO inputs (the real pedal OR the DACs) and routes them to ONE output (the traction controller). **Default (no power) = real pedal connected.** Powered = DACs connected. So if anything goes wrong electrically, the relay drops back to the real pedal and you have a normal cart.

### Sensors
- **LiDAR** (Livox Mid-360) — spinning laser, 360° around the cart, gives a 3D point cloud of "stuff exists at coordinates X,Y,Z." Sees walls, pedestrians, curbs.
- **Cameras** — 7 of them (front stereo, front mono, 4 corner, rear). For object detection (people, signs, lane markings).
- **GPS-RTK** (ZED-F9P × 2) — high-accuracy GPS using corrections from a base station; gets us centimeter accuracy instead of normal-GPS 5-meter accuracy. Two antennas because two antennas give us heading direction even when stopped.
- **IMU** (VectorNav VN-100) — measures acceleration and rotation. Fills in between GPS readings.

We don't have any sensors yet. They come in Phase 1 (Week 5+ of timeline). Phase 0 is just the drive-by-wire layer.

### Safety hardware
- **Mushroom E-stop buttons** (2 of them — dash + passenger). The big red ones. Pressing one breaks an electrical loop.
- **Kilovac LEV200 contactor** — a heavy-duty relay that gates ALL 12 V power to the actuators. When the E-stop loop breaks, the contactor drops, and every actuator loses power simultaneously, in milliseconds. Software cannot override this. **It's the safety net.**

---

## 4. How a command travels from your thumb to the wheel

You hold the Logitech F710 gamepad. You push the left stick to the right.

```
1. GAMEPAD                  Stick at +0.5 (half right)
       │ USB
       ▼
2. JETSON                   joy_node reads the USB device
                            → publishes /joy ROS topic
                            joy_to_ackermann_node converts:
                              stick → road-wheel angle in radians
                              trigger → speed in m/s
                            → publishes /dbw/cmd ROS topic
                            gem_dbw_bridge_node packs the ROS message
                            into CAN frames (steering cmd, throttle cmd)
       │ DBW CAN bus
       ▼
3. MOTION TEENSY            Receives 0x110 STEER_CMD (steering angle)
                            Runs a PI controller: "we want X angle,
                            we have Y angle, push by Z newton-meters"
                            Sends 0x296 to EPAS18 ECU
       │ EPAS CAN bus
       ▼
4. EPAS18 ECU               Receives torque command
                            Drives current to the EPAS01 column motor
       │ wires
       ▼
5. STEERING MOTOR           Rotates the steering shaft
       │ mechanical
       ▼
6. WHEELS                   Turn right
```

And in parallel, the throttle path:
```
JETSON → DBW CAN → PEDALS TEENSY → DAC chips → DPDT relay → traction controller → motor → cart moves
```

Each step is 20 ms or faster. Total latency from gamepad to wheel: ~100 ms (mostly mechanical inertia in the steering column).

---

## 5. How power flows

```
   GEM Traction Pack (72 V battery)
        │
        ├──► Existing GEM DC-DC ──► 12 V to lights, horn, accessories
        │
        ├──► Our new Vicor DC-DC ──► 12 V aux bus ──┬──► Jetson (via 12V→19V boost)
        │                                            ├──► Teensies (via 12V→5V buck)
        │                                            ├──► EPAS18 ECU
        │                                            └──► DAC chips, relay, sensors
        │
        └──► (Phase 2) Pololu 12V→19V ──► linear actuator for brake
```

**Orange wires = high voltage (72 V).** Never touch them. The cart's drive motor and battery are at 72 V — enough to kill you on damp skin. We always work on the 12 V side after the DC-DC step-down.

A LiFePO4 backup battery (Battle Born or Renogy 100 Ah) sits on the 12 V aux bus to:
1. Smooth out brownouts when the steering motor pulls 80 A transient
2. Keep the Jetson alive if the traction pack dips
3. Act as UPS so the Jetson doesn't yank power mid-shutdown

---

## 6. Safety architecture (this is the most important part)

There are THREE independent ways the cart stops:

### A. Hardware kill chain (the always-works path)
```
Press any mushroom E-stop OR brake pedal OR wireless E-stop
    ↓
Series-NC electrical loop breaks
    ↓
Kilovac LEV200 contactor coil de-energizes
    ↓
12 V is physically cut from: throttle relay, EPAS18, brake actuator
    ↓
Throttle relay drops to "pedal direct" (cart driveable by your foot only)
EPAS18 powers off (steering loses assist but mechanical linkage still works)
Brake actuator releases
```

Software is NEVER in this loop. Even if every line of our code is bugged, hitting the E-stop physically yanks power. Milliseconds, no microcontroller involved.

### B. Software state machine (the day-to-day path)
The Pedals Teensy runs a four-state machine:
- **DISENGAGED** — autonomy ignored, pedal direct, idle
- **ARMED** — preconditions checked, waiting for engage
- **ACTIVE** — autonomy commands actually executing
- **FAULT** — sticky error state; requires key cycle to clear

You arm + engage via dash buttons. Any of these auto-DISENGAGE: brake pedal pressed, hand on the steering wheel (cap-touch sensor), Jetson heartbeat missing for >100 ms, EPAS18 reports an error, motor draws unexpected current.

### C. Driver always wins (mechanical override)
- Steering wheel: the EPAS18 has a torque sensor; when you grip the wheel, the autonomous loop drops out within 50 ms and yields.
- Throttle: pressing the brake pedal kills the throttle relay (back to pedal-direct).
- Brake: Phase 2 actuator uses a Bowden cable that PULLS — you can always press deeper than it pulls.

---

## 7. The protocols

### CAN bus
A bus is a shared wire that multiple devices listen to. Every CAN message has:
- **ID** (11-bit, like 0x100 or 0x296) — a number that identifies what kind of message it is
- **Up to 8 bytes** of data

We defined our own protocol — see `Software/firmware/common/include/dbw_can_protocol.h`. Key IDs:
- `0x100` JETSON_HEARTBEAT — "I'm alive" beacon from Jetson, every 20 ms
- `0x110` STEER_CMD — "turn the wheel to X degrees"
- `0x120` THROTTLE_CMD — "press the throttle X%"
- `0x130` BRAKE_CMD — "press the brake X%"
- `0x140` ESTOP_STATE — "current state machine state"

### J1939
A higher-level protocol layered on CAN, used by all heavy vehicles. Messages are identified by **PGN** (Parameter Group Number) instead of raw ID. E.g.:
- PGN 65265 = vehicle speed
- PGN 61445 = transmission gear
- PGN 61444 = engine voltage

The GEM internal CAN speaks J1939. We listen to it (read-only) to know the cart's speed and gear without adding our own sensors.

### ROS 2 (Robot Operating System)
The plumbing between programs on the Jetson. Programs publish messages to named "topics" (like `/dbw/cmd`), and other programs subscribe to those topics. ROS handles serialization, discovery, networking. It's not really an OS — it's a library that runs on top of Ubuntu Linux.

A **node** is one program. A **topic** is a named message channel. A **launch file** starts multiple nodes together.

---

## 8. The cart's physical zones

We split the cart into 7 zones, connected by 3 cable channels:

| Zone | What's in it |
|---|---|
| **Roof / mast** | LiDAR, GPS antennas, front cameras, LTE antenna |
| **Windshield top** | Front stereo + Leopard front camera |
| **Dash console** | HMI tablet, ARM/ENGAGE/DISENGAGE buttons, mushroom E-stop, status LEDs |
| **Steering column area** | Motion Teensy aux box, EPAS18 ECU |
| **Pedal area (footwell)** | Pedals Teensy aux box (DACs, relay, brake actuator Phase 2) |
| **Under driver seat** | Kilovac contactor, master fuse, traction controller (existing GEM hardware) |
| **Rear cargo (trunk)** | Main Pelican compute box (Jetsons, switch, DC-DCs, LTE modem), aux LiFePO4 battery |

Cable channels:
- **Channel R** — roof → trunk along headliner and rear D-pillar (sensors)
- **Channel D** — dash → trunk along driver-side floor under trim (buttons, CAN)
- **Channel S** — column / pedals → trunk via center tunnel (CAN, power, harness taps)

---

## 9. The repository tree (where everything lives)

```
.claude/memory/      ← memory files Claude reads automatically every session
Hardware/            ← anything physical: BOMs, wiring, photos, recovered 2020 docs
  CART_VISIT_DAY1.md         what to check when you visit the cart
  WIRING_DIAGRAM.md          canonical wiring (renders nice on GitHub)
  JETSON_WIRING_DIAGRAM.md   Jetson port-by-port assignments
  SHOPPING_LIST.md           what to buy, when
  system_design.md           locked component selection
  jetson_runtime/            systemd units we put on the Jetson
  OneDrive_1_5-1-2026/       recovered 2020 team artifacts
Software/            ← all code that runs on the cart
  firmware/
    common/include/dbw_can_protocol.h   ← THE shared CAN protocol header
    motion_teensy/                       ← Motion Teensy firmware (C++)
    pedals_teensy/                       ← Pedals Teensy firmware (C++)
  autonomy_ws/src/
    gem_dbw_bridge/                      ← Python, runs on Jetson, ROS↔CAN
    gem_teleop/                          ← Python, gamepad → ROS command
Sim/                 ← off-cart simulation environment (DEV-ONLY, never on cart)
bin/                 ← helper scripts (sync, setup, install)
Masterplan.md        ← full project plan, long form
STATUS.md            ← current status + weekly timeline
PRIMER.md            ← THIS DOCUMENT
CLAUDE.md            ← auto-loaded into every Claude session
README.md            ← repo home page
```

---

## 10. The phases — where are we, where are we going

| Phase | Goal | Status | What's done | What's next |
|---|---|---|---|---|
| **0a** | Inspect cart, understand what's there | 🟡 in progress | First photos taken, front bay identified | Confirm pack voltage, locate J1939 port, photo EPAS ECU label |
| **0b** | Firmware bench bring-up | ⛔ blocked on parts | Code is written | Order Tier 1 parts (~$310) |
| **0c** | RC first-light: drive cart via gamepad, no autonomy | ⛔ ~Week 4 | All ROS code working on Jetson | Wire Teensies to cart, gamepad in hand |
| **1** | Sensors mounted, mapping run | ⛔ ~Week 5–8 | Plans written | Buy sensors after RC works |
| **2** | Autonomous waypoint following on closed lot | ⛔ ~Week 9–16 | Sim foundation exists | Build HD map of campus |
| **3** | Pedestrian-aware autonomy on campus paths | ⛔ ~Mo 6–9 | — | Autoware perception integration |
| **4** | Unmanned operation with chase observer | ⛔ ~Mo 9–12 | — | Brake actuator + redundant safety |

---

## 11. Plain-English glossary

| Term | What it really means |
|---|---|
| **ADC** | Reverse of DAC — converts an analog voltage to a digital number. Used to read sensors. |
| **AGV** / **AV** | Automated Guided Vehicle / Autonomous Vehicle. Same idea. |
| **CAN bus** | Car wiring network. Two wires + 1-8 byte messages broadcast at high speed. |
| **DAC** | Digital-to-Analog Converter. Chip that outputs a precise voltage when you tell it a number. |
| **DBW** | Drive-By-Wire. The cart is steered/throttled/braked by sending electrical commands instead of mechanical linkages. |
| **DC-DC** | A circuit that converts one DC voltage to another (e.g., 72 V from the pack → 12 V for accessories). Like a small power supply. |
| **ECU** | Electronic Control Unit. A vehicle's embedded computer for a specific function (engine ECU, steering ECU, etc.). |
| **EPAS** | Electric Power Assisted Steering. The motorized steering system. |
| **GMSL** | Gigabit Multimedia Serial Link. A camera connector technology that sends high-bandwidth video over a single coax cable, used in automotive. |
| **GPIO** | General Purpose Input/Output. Pin headers on a microcontroller or single-board computer (like the 40-pin header on the Jetson). |
| **IMU** | Inertial Measurement Unit. Combines accelerometers + gyroscopes (sometimes magnetometer) to measure motion. |
| **J1939** | A higher-level protocol on top of CAN, used by trucks, buses, golf carts, etc. |
| **LiDAR** | Light Detection and Ranging. A spinning laser that maps the 3D world around itself. |
| **LSV** | Low-Speed Vehicle. Federal classification for street-legal electric vehicles ≤25 mph. The GEM E4 is an LSV. |
| **MCU** | Microcontroller (Teensy, Arduino, ESP32, etc.). One tiny chip running one program forever. |
| **NDT** | Normal Distributions Transform. Algorithm that matches a LiDAR point cloud to a stored map to figure out where you are. |
| **NTRIP** | Networked Transport of RTCM via Internet Protocol. Way to get GPS correction data over the internet. |
| **Optoisolator** | Tiny chip that transfers a signal between two circuits using a light beam, so the two circuits don't share a ground. Used to safely tap into the GEM's brake light wire. |
| **OBD-II** | On-Board Diagnostics version 2. The standard diagnostic connector under your dashboard on consumer cars. |
| **PCB** | Printed Circuit Board. The green (or other color) flat thing with components on it. |
| **PGN** | Parameter Group Number. The J1939 way of naming what a CAN message contains. |
| **PI / PID** | Proportional-Integral / Proportional-Integral-Derivative controller. The standard control-loop algorithm — "how much should I push to get to where I want to be?" |
| **PWM** | Pulse-Width Modulation. Way of controlling motor speed or power by switching a digital signal on/off rapidly at varying duty cycle. |
| **RTK** | Real-Time Kinematic. High-precision GPS technique that gets centimeter accuracy by using corrections from a base station. |
| **ROS 2** | Robot Operating System 2. Open-source middleware framework for robot software. Lets programs talk to each other. |
| **SDF** | Simulation Description Format. XML format that describes a simulated world for Gazebo. |
| **SocketCAN** | Linux's way of talking to a CAN bus through standard network socket calls. |
| **TF tree** | Transform tree. ROS concept — relationships between coordinate frames (where is the LiDAR relative to base_link, where is base_link relative to the world, etc). |
| **URDF** | Unified Robot Description Format. XML format that describes a robot's links and joints (kinematic structure). |
| **xacro** | XML macros for URDF. Lets you parameterize URDF files. |

---

## 12. What to do next (concretely)

You don't need to know everything from this primer. You need to know:
- The 30-second version (Section 1)
- The cake layers (Section 2)
- That orange wires are dangerous (Section 5)
- How to use the glossary as a lookup when you forget what something means

Then take the next action:

1. **Buy a $25 multimeter** so you can measure things on the cart
2. **Order Tier 1 parts** (~$310, mostly Amazon) so the firmware bench can start
3. **Email DCE Motorsport** about the EPAS18 autonomous firmware
4. **Reach out to anyone at FAU with auto/EV experience** to pair with you on the first hardware work

That's it. We do one thing at a time, you ask whenever something doesn't make sense, and we work through it together.
