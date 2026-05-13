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

## 10. The full plan — everything we're going to do, in order

Six phases, ~12–15 months end to end. Each phase has a concrete demo as its gate to the next.

### Phase 0a — Cart inspection & approvals  (Week 1, ~$25)

**Goal:** understand what's actually on the cart, get the long-pole approvals started.

| Step | What | Status |
|---|---|---|
| 1 | Photograph the cart front bay, traction controller, EPAS18 ECU label, dash, throttle pedal connector | 🟡 in progress |
| 2 | Buy a $25 multimeter, measure pack voltage (48 V or 72 V?) | ⛔ pending |
| 3 | Measure throttle pedal Hall pair voltages 0–100% (build calibration map) | ⛔ pending |
| 4 | Locate the GEM J1939 diagnostic port (usually under dash) | ⛔ pending |
| 5 | Email DCE Motorsport: is autonomous firmware loaded on the EPAS18 ECU? | ⛔ pending |
| 6 | Email FAU Risk Management about autonomous-vehicle research approval (long-pole — start NOW) | ⛔ pending |

**Demo gate:** All 6 questions answered with hard data + DCE email out + Risk Mgmt thread opened.

---

### Phase 0b — Firmware bench bring-up  (Weeks 1–3, ~$310)

**Goal:** prove the two Teensies talk to each other and to the Jetson, on the bench, with nothing on the cart yet.

| Step | What | Status |
|---|---|---|
| 1 | Order Tier 1 parts (~$310: Teensies, CANable, transceivers, DACs, relay, gamepad, wire, connectors) | ⛔ pending |
| 2 | Solder a small breadboard rig: 2 Teensies + 3 CAN transceivers + bus termination | ⛔ pending |
| 3 | Flash Motion Teensy firmware; verify heartbeats on CAN with `candump` | ⛔ pending |
| 4 | Flash Pedals Teensy firmware; verify state machine via dash-button-equivalents | ⛔ pending |
| 5 | Verify gamepad → Jetson → CAN end-to-end (you already have everything ROS-side on the Jetson) | ✅ Jetson side done |
| 6 | Verify DAC outputs into a scope: 0→100% throttle sweep produces correct mirrored voltages | ⛔ pending |

**Demo gate:** On the bench, press dash-ARM button → state goes to ARMED. Press ENGAGE → ACTIVE. Move gamepad stick → CAN frame `0x110 STEER_CMD` updates @ 50 Hz. Hit any E-stop simulation → throttle relay drops.

---

### Phase 0c — RC first-light on the cart  (Weeks 4–6, ~$450)

**Goal:** drive the cart in an empty parking lot at 3 mph with a gamepad. Safety driver in seat with foot on the brake.

| Step | What |
|---|---|
| 1 | Tier 2 procurement: DC-DCs, LiFePO4 aux battery, fuse block, mushroom E-stops, Kilovac contactor, wire/lugs (~$450) |
| 2 | Build the under-seat Safety Box: Kilovac + master fuse + E-stop loop wiring |
| 3 | Build the Steering Aux Box + Pedals Aux Box (the Teensy enclosures) |
| 4 | Mount the Pelican compute box in the trunk with Jetson |
| 5 | Run cable channels R/D/S (roof, dash, steering — but no sensors yet, just power + CAN) |
| 6 | Splice into the GEM throttle harness with the DPDT relay (you can revert at any time) |
| 7 | Wire CAN_H/CAN_L from Jetson's 40-pin to the Teensies (DBW bus) |
| 8 | Wire the EPAS bus from Motion Teensy to the EPAS18 ECU |
| 9 | Bench-test on cart with wheels off the ground first (jack stands) |
| 10 | Closed-parking-lot first drive at 3 mph max, safety driver, foot near brake |

**Demo gate:** Drive a figure-8 in an empty parking lot, gamepad-controlled, no autonomous decisions, safety driver hands hovering. Hit dash E-stop at speed → cart coasts to a stop safely. **No brake actuator yet** — safety driver brakes with their foot.

---

### Phase 1 — Sensors come online & first mapping run  (Weeks 5–12, ~$5,200)

**Goal:** install all sensors, drive the cart manually around FAU campus, record the data, build a 3D map of the breezeway loop.

| Step | What |
|---|---|
| 1 | Tier 3 procurement: Livox Mid-360 LiDAR, ZED 2i front cam, 4× corner cams (USB3 or GMSL), 2× ZED-F9P RTK, VectorNav IMU (~$5,200) |
| 2 | Fabricate sensor mast (aluminum extrusion, ~$30) on the cart roof |
| 3 | Wire LiDAR Ethernet + 12 V to trunk via Channel R |
| 4 | Mount cameras at all 7 positions, route GMSL or USB to trunk |
| 5 | Mount GPS antennas (40 cm apart for moving-baseline heading) |
| 6 | Mount the VectorNav IMU near vehicle CG inside the Pelican box |
| 7 | Calibrate sensor extrinsics with Autoware's calibration tools |
| 8 | First mapping drive of FAU breezeway loop (East Engineering → Wimberly Library) |
| 9 | Offline: run LIO-SAM or FAST-LIO2 on the rosbag → produce a 3D point cloud map |
| 10 | Hand-annotate a lanelet2 vector map on top of the point cloud (Tier IV's free Vector Map Builder tool) |

**Demo gate:** Foxglove playback of a recorded drive showing all 9 sensors firing, with the 3D point cloud + lanelet2 map overlaid. Sub-30 cm map repeatability.

---

### Phase 2 — Autonomous waypoint following  (Weeks 13–24, hardware-side ~$300)

**Goal:** the cart drives the breezeway loop autonomously, at 5 mph, safety driver still in seat hands hovering.

| Step | What |
|---|---|
| 1 | Tier 5 procurement: PA-14P linear brake actuator + Bowden cable + BTS7960 H-bridge (~$250) |
| 2 | Mount brake actuator on firewall, cable to brake pedal arm |
| 3 | Wire brake driver to Pedals Teensy; bench-tune position PID |
| 4 | Migrate Jetson autonomy stack from Nav2 (Phase 0–1) to **Autoware Universe** |
| 5 | Bring up `robot_localization` EKF + Autoware NDT scan-matcher (localization on the HD map) |
| 6 | Bring up Autoware mission_planner + pure-pursuit controller |
| 7 | Closed-loop test on T1 breezeway loop: 5 mph, safety driver supervising |
| 8 | Iterate on tuning until 10 consecutive clean laps |

**Demo gate:** 10 consecutive autonomous laps of the breezeway, lateral error <50 cm, zero unintended disengagements. Software-commanded brake works.

---

### Phase 3 — Perception + pedestrian behavior  (Months 6–9)

**Goal:** add real-world awareness — the cart sees and stops for pedestrians, navigates around static obstacles, follows traffic rules at crosswalks.

| Step | What |
|---|---|
| 1 | Fine-tune YOLO v8 on a campus-specific dataset (pedestrians, cyclists, scooters, golf carts) |
| 2 | Fine-tune SegFormer for drivable surface (pavement, sidewalk, grass, curb, crosswalk) |
| 3 | Integrate Autoware's `behavior_velocity_planner`: crosswalk module, stop-line module, run-out module |
| 4 | Expand operating domain from T1 breezeway → T2 academic core (Engineering complex, Library, Student Union) |
| 5 | Scripted pedestrian-crossing scenarios (50+ encounters); zero near-misses gate |
| 6 | Static-obstacle navigation (parked golf cart blocks the path → autonomous reroute) |

**Demo gate:** Cart drives the T2 academic core loop autonomously with 50+ scripted pedestrian encounters, zero near-misses, <1 unintended disengagement per km.

---

### Phase 4 — Toward unmanned operation  (Months 9–12+)

**Goal:** chase-observer-only unmanned operation on approved campus segments. The "tiny Waymo" demo.

| Step | What |
|---|---|
| 1 | Add the redundant fail-engage parking-brake solenoid (so loss of power = parking brake engages) |
| 2 | Add the wireless 433 MHz E-stop fob (Telecrane F24-8D), hardwired into the E-stop loop (NOT through software) |
| 3 | Mapping pass of T3 — full FAU Boca campus (850 acres) |
| 4 | Independent safety supervisor running on the Orin NX (the Yahboom you already have, demoted from "primary compute" to "safety / logger") |
| 5 | Buy AGX Orin 64 GB (~$2k) for primary perception compute, install in cart |
| 6 | Get FAU Risk Management sign-off on the operations envelope (requires the previous Risk Mgmt thread to have matured over 9+ months) |
| 7 | Chase-observer drives: a person walks/bikes alongside the cart with a wireless E-stop fob |
| 8 | Build up to >10 hours per phase incident-free before going further |

**Demo gate:** A campus loop, no human in or on the cart, observer follows on foot with a wireless E-stop. The "FAU Early Rider" demo.

---

### Running total by phase

| Phase | Cost | Cumulative | Time | Cumulative time |
|---|---|---|---|---|
| 0a inspection | $25 | $25 | Week 1 | 1 |
| 0b firmware bench | $310 | $335 | Weeks 1–3 | 3 |
| 0c RC first-light | $450 | $785 | Weeks 4–6 | 6 |
| 1 sensors + mapping | $5,200 | $5,985 | Weeks 5–12 | 12 |
| 2 autonomous waypoint | $300 | $6,285 | Weeks 13–24 | 24 |
| 3 perception + behavior | $250 (enclosures/cooling) | $6,535 | Months 6–9 | 36 weeks |
| 4 unmanned (AGX Orin) | $2,200 | $8,735 | Months 9–12+ | 48 weeks |

Lab inventory check can cut $2k+ off this — see `Hardware/system_design.md` PART F.

---

### The cross-cutting threads

Things that happen *throughout* the project, not at any single phase:

- **FAU approvals** — Risk Management, Campus Police, Insurance, Office of Research Integrity. Email thread should start in Phase 0a; the approvals mature over 9+ months for unmanned. *This is the actual long-pole, not any hardware.*
- **Sim work** — the Cartagena workspace runs on a Linux dev box (not the Jetson). Used in Phase 0–1 to dry-run code, in Phase 2+ to validate behaviors before real-cart testing.
- **Documentation + version control** — every change auto-pushes to GitHub every 10 minutes. Anyone joining the project clones the repo and `bin/setup_new_machine.sh` gives them ~95% of context.
- **Safety case** — grows over time. Phase 0 = mechanical E-stops + safety driver. Phase 2 = software disengagement paths. Phase 4 = wireless E-stop + parking-brake solenoid + redundant compute.

---

### How you'll know we're on track

After each phase demo gate, ask: "could a stranger reproduce this on a fresh Linux box?" If yes → next phase. If no → tighten docs/scripts first.

---

## 11. Skills, tools, and pitfalls — how to actually do this

Theory in the previous sections won't help if you don't have the workshop fundamentals. Here's the practical layer.

### Physical tools you'll need to acquire

| Tool | Why | ~$ | When |
|---|---|---|---|
| **Multimeter** (Klein MM325 or Fluke 101) | Measure voltage, continuity, resistance — 80% of investigation work | $25–80 | NOW |
| **Wire strippers + cutters** | Prepare wire ends cleanly | $15 | Phase 0c |
| **Deutsch DT crimper** | Crimps DT04 connector pins; **specialized** — generic crimpers won't work | $35 | Phase 0c (comes in the kit) |
| **Soldering iron** (Pinecil V2 is great) | Solder Teensy headers, DAC breakouts, etc. | $30 | Phase 0b |
| **Solder + flux** (lead-free 0.6mm + rosin flux pen) | — | $15 | Phase 0b |
| **Heat gun** + heat-shrink tubing | Insulate splices properly | $25 | Phase 0c |
| **PCB vise** or "helping hands" | Hold parts while you solder | $15 | Phase 0b |
| **Safety glasses + nitrile gloves** | Protect eyes from solder splatter; gloves when probing | $10 | NOW |
| **Insulated work gloves** (1000 V rated) | For when you're near the orange HV wires | $30 | Phase 0c |
| **Headlamp** | Working under the dash | $20 | Phase 0a |
| **Label maker** (Brother PT-D210) or just masking tape + Sharpie | Label every wire — you WILL forget | $30 | Always |
| **Logic analyzer** (Saleae Logic 8 clone) | Optional but huge for debugging CAN/SPI/I²C | $15 (clone) | When stuck |
| **Bench power supply** (cheap CSI3010, 0–30 V / 0–10 A) | Test electronics off-cart safely | $60 | Phase 0b |

Total: ~$300 for the workshop. Buy as you need.

### Software tools to install on your machine

- **Foxglove Studio** (Mac native) — already done, for URDF preview + ROS topic viewing
- **VS Code** (or your editor)
- **GitHub Desktop** (if you prefer GUI over command-line git)
- **Fusion 360 Personal** (free for academic) — for any CAD work
- **Slack / Discord** — for whatever team comms FAU uses

### Skills to develop (each is ~1–2 hours of YouTube + practice)

In approximate order of when you'll need them:

1. **Multimeter usage — DC voltage, continuity** (Phase 0a)
   → YouTube: "How to use a multimeter for beginners" (any 15-min video)
2. **Soldering through-hole components** (Phase 0b)
   → YouTube: "How to solder for absolute beginners" by EEVblog
3. **Reading basic schematic symbols** (ongoing)
   → SparkFun tutorial: "How to read schematics"
4. **Using `candump` and `cangen` on Linux** (Phase 0b)
   → Run `man candump` after `apt install can-utils`; pretty self-explanatory
5. **Crimping Deutsch DT connectors** (Phase 0c)
   → YouTube: "How to crimp Deutsch DT connectors"
6. **Reading ROS 2 launch files** (already starting)
   → Skim `Software/autonomy_ws/src/gem_teleop/launch/teleop.launch.py`; it's Python
7. **Basic Linux terminal** (ongoing)
   → If `ssh`, `scp`, `cd`, `ls`, `cat`, `grep` aren't familiar yet, install Warp terminal and practice for an hour

### Methodology — how to test things without setting them on fire

The golden rule: **build it small, test it isolated, add one thing at a time.**

1. **Breadboard first, PCB later.** Plug components into a solderless breadboard before committing to a soldered assembly. If something's wrong, you can rearrange in 30 seconds.
2. **Power from a benchtop supply, not the cart.** Start at 1 A current limit. If something draws more than expected, the bench supply will current-limit. The cart's traction battery will not — it'll deliver hundreds of amps into a short.
3. **Test each component alone before integrating.** Power up the Teensy alone. Then add the transceiver. Then add the DAC. Then the relay. Each step, verify functionality before adding the next.
4. **Use a scope (or just an LED) to verify outputs** before wiring to anything irreplaceable. DAC outputs especially — check on the scope that you actually get 0.8 V at rest before plugging into the throttle harness.
5. **Always disconnect actuators before re-flashing or testing new code.** A buggy firmware that floors throttle will be a bad surprise.
6. **Test on jack stands before driving.** When the cart's drive wheels are first commanded by software, the wheels should be off the ground. Listen for unusual noise. Listen for motor groan that means the steering is fighting itself.

### Debugging when something doesn't work — the systematic approach

Work outward from power, in. **Always.**

1. **Power.** Is the supply on? Is voltage correct at every rail? Voltage at the Teensy 5 V pin? Voltage at the DAC Vcc?
2. **Ground.** Continuity from every component's GND back to a single point? No multiple ground paths?
3. **Signal at source.** Is the Teensy actually emitting what you think? Check with `Serial.println()` or with an LED you toggle.
4. **Signal at destination.** Is it arriving cleanly? Probe with multimeter or scope at the receiving end.
5. **Protocol.** `candump can0` to see actual CAN traffic. `ros2 topic echo /...` to see ROS messages. Don't trust your code — verify the wire.
6. **Code.** Re-read your own code (your eyes glaze over after writing it; force yourself to read line by line). Add print statements.
7. **Documentation.** Re-read the datasheet of the chip you're talking to. Half the time the answer is in the datasheet you skimmed.
8. **Ask.** If 2 hours of solo debugging hasn't moved the needle, ask someone with fresh eyes. Bring the symptom + what you've tried + a hypothesis. Don't ask "why doesn't it work" — that's untriagable. Ask "I see X, I expected Y, my hypothesis is Z, how do I test that?"

### When to ask for help (specifically)

- **Anything involving the orange HV wires** → ask first, always. Not a place to learn from mistakes.
- **If the magic smoke comes out** → unplug everything immediately, ask before re-energizing.
- **If a component gets hot enough to burn your finger** → unplug, ask.
- **If the cart behaves unexpectedly** (twitches, surges, won't stop) → STOP, hit E-stop, ask before trying again.
- **If you've spent more than 2 hours debugging the same problem** → ask. Two fresh eyes save hours.

### Realistic expectations

- **A "1-hour task" usually takes 3–5 hours the first time.** Plan accordingly. Add 50% buffer.
- **Embedded debugging can eat full days.** A single mistake (reversed polarity, bad solder joint, wrong CAN ID byte) can take an afternoon to find.
- **You will burn out at least one Teensy.** Build it into the budget. Buy 3 instead of 2.
- **The first cart-side install will fail in some unexpected way.** Plan a half-day for "first power-on" not 30 minutes.
- **FAU approvals take months, not days.** Start the Risk Management thread now even though you won't drive on campus for 6 months.

### Common pitfalls (things that bite first-timers, every time)

1. **Wiring polarity reversed** — connect Teensy 5 V to GND and you fry it. Always check before powering on.
2. **CAN bus missing termination** — without 120 Ω at each end, frames look fine on a scope but get dropped at speed. Symptom: bus works for short bursts then errors flood.
3. **Ground loops** — multiple ground paths cause weird noise that's nearly impossible to debug. Single-point star ground at the aux battery negative, period.
4. **DPDT relay wired wrong** — easy to put pedal and DAC on the wrong sides. Test the relay logic with a multimeter in continuity mode before energizing.
5. **Software FAULT is sticky** — by design. Don't add ways to clear it from software. If you keep ending up in FAULT, fix the cause, not the symptom.
6. **EPAS18 in local mode silently** — if the autonomous firmware isn't loaded, msg `0x296` does nothing. The ECU won't error, it just won't steer. Confirm the firmware variant via DCE.
7. **Pedal Hall pair voltage flipped** — V1 and V2 mirror each other. Swap them and the traction controller faults on plausibility check. Document the orientation before splicing.
8. **`ros2: command not found`** — you forgot `source /opt/ros/humble/setup.bash` in this terminal. Add it to your `.bashrc` once you're tired of typing it.
9. **Building the wrong workspace** — `Sim/...` and `Software/autonomy_ws/` are different colcon workspaces. Same `colcon build` command, different `cd` first.
10. **Stale builds after edits** — symlink-install means launch files auto-pick edits, but C++ packages need a real rebuild. When in doubt, `rm -rf build/ install/ log/` and full rebuild.
11. **Auto-commit pushing half-edited files** — if you're in the middle of breaking something, the 10-minute cron will push it. Either commit/revert quickly, or temporarily disable: `launchctl unload ~/Library/LaunchAgents/com.fau.golfcart.autocommit.plist`.
12. **Sourcing forgotten in scripts** — every shell script that calls `ros2` must source ROS first. The bridge node's systemd unit does this. Your one-off scripts often don't, and silently exit.

### Document discipline — so this doesn't go dormant again

The 2020 team left almost nothing behind. The recovered Arduino code was 13 bytes of "404 NOT FOUND". Don't repeat that:

- **Every measurement you make on the cart goes into a file** (date, what you measured, value, what it means).
- **Every wiring change** gets photographed before and after.
- **Every "I tried X but Y happened" goes into the relevant doc** — your future self thanks you.
- **Auto-commit will catch most of this.** Don't fight it.

---

## 12. The underlying lessons — what this project is really teaching

These are the principles behind the architectural decisions. Internalize these and you'll make better calls than you'd get from following any checklist.

### Engineering principles

**1. Software is never in the kill path.**
The hardware E-stop loop physically yanks power before any microcontroller can react. Why? Software has bugs; relays don't. Every safety-critical system you'll ever build needs a path that survives total software failure. The Kilovac LEV200 contactor + the NC series-wired E-stop loop is that path here.

**2. Single source of truth, propagated everywhere.**
The CAN protocol is defined in *one* header file (`dbw_can_protocol.h`) and compiled into both Teensy firmwares AND the Python Jetson bridge. Vehicle parameters live in *one* xacro file (`cart_parameters.xacro`) that both the sim URDF and the real-cart URDF include. Anywhere you find the same value typed in two places is a bug waiting to happen.

**3. Fault domain separation.**
Three CAN buses, not one. Two Teensies, not one. Two Jetsons, not one. If the steering bus glitches, throttle still works. If perception crashes, the safety supervisor still stops the cart. Building monoliths in safety-critical systems is asking for them to fail spectacularly.

**4. Build small, integrate one piece at a time.**
Breadboard before PCB. Bench supply before traction battery. One Teensy on the bus before two. Add one component, prove it works, add the next. This is slower than "build it all and turn it on," but the cost of debugging an integrated system that has six bugs is more than 6× the cost of debugging six isolated bugs.

**5. Defense in depth on safety.**
The cart stops via three independent mechanisms: hardware E-stop loop, software state machine, mechanical override. We don't rely on any one of them being bug-free. The autonomous-firmware variant of the EPAS18 yields to driver torque on the wheel. The throttle DPDT relay defaults to "pedal direct" on power loss. The brake actuator uses a cable that you can always press deeper than. Belt and suspenders and parachute.

**6. Use existing parts when possible.**
We kept the 2020 team's EPAS18 Ultra steering instead of ripping it out for an ODrive + custom motor. We adopted the Cartagena sim foundation instead of starting over. We took the recovered J1939 PGN dictionary as our starting decode rather than reverse-engineering from scratch. NIH ("Not Invented Here") syndrome is expensive — when something works, use it.

**7. Cite prior art before deciding architecture.**
UIUC's gem_ws taught us that PACMod is one DBW option (we chose not to use it). GEM-Illinois's sim package gave us our Gazebo foundation. Autoware Universe is our Phase 2 target. The right question before designing is always "has someone built this before, and what did they learn?"

**8. Procurement detail matters in plans.**
"Add a CAN transceiver" is not a plan. "Mouser part `653-G8HE-1A7T-DC12`, qty 2, $14" is a plan. Vagueness in a procurement plan means you discover the wrong part after a week of build time. Be specific to the SKU level when the plan crosses into hardware.

### Project & process principles

**9. Demo gates, not date gates.**
Phases advance when the demo passes, not when the calendar says so. A "Week 9" milestone means nothing if Phase 0c hasn't actually driven the cart. Forcing the schedule produces theater, not progress.

**10. Approvals are the long pole.**
FAU Risk Management, Campus Police, insurance, IRB. Hardware can be ordered and assembled in weeks; institutional approvals take 6+ months. Start the approval thread on day one, even when you don't need it for half a year. This is the actual constraint, not the technical work.

**11. Document discipline saves projects.**
The 2020 team produced beautiful CAD, working Arduino code, and a partial PGN dictionary — and then the project died and almost nothing was version-controlled. We recovered some artifacts from OneDrive five years later, by luck. Don't repeat that. Every measurement on the cart goes into a file, every wiring change gets photographed, every "I tried X but Y happened" goes into the relevant doc. Auto-commit catches most of it for free.

**12. Ask for fresh eyes after 2 hours.**
Two hours of solo debugging is the threshold. Beyond it, productivity drops fast and a second pair of eyes saves more time than the asker thinks. Bring the symptom, what you've tried, and a hypothesis — don't ask "why doesn't it work."

**13. Sims are for behaviors, real cart is for ground truth.**
The sim is great for control-loop dev, behavior testing, scenario rehearsal, autonomy regression. The sim is bad for sensor noise characterization, mechanical response tuning, GPS-degraded behavior. Use each tool for what it does well — don't expect sim agreement to mean the real cart will work.

**14. Auto-commit is non-negotiable.**
The repo is the project. Local-only work is work that doesn't exist. The Mac launchd job that pushes every 10 minutes isn't a convenience — it's how we don't lose this project the way 2020 did.

### Specific design lessons from THIS project

**15. The Jetson is a CAN gateway and autonomy compute, NOT a sim host.**
Burned ~3 hours in this session trying to run Gazebo on the Jetson. Wrong tool. Sim runs on a dev box (Linux, off-cart). The Jetson on the cart talks to Teensies and runs autonomy. Architectural mismatch == wasted time.

**16. macOS isn't a ROS 2 + Gazebo platform.**
Apple Silicon Rosetta breaks Gazebo's shared-memory tracker. The osrf/ros multi-arch manifests don't include arm64. Native macOS ROS 2 is officially unsupported. Use a Linux box for cart-runtime work; use the Mac for editing and Foxglove preview only.

**17. Throttle DAC injection beats J1939 injection.**
The 2020 team considered injecting throttle commands directly onto the GEM's J1939 bus. They (correctly) rejected it as too risky — writing to the wrong bus address can brick the traction controller. We adopted their decision: read-only on J1939, DAC injection at the pedal harness.

**18. The orange wires are not optional reading.**
72 V DC will kill you. Always confirm the master cutoff is off, wait 5 minutes for Sevcon caps to discharge, work on the 12 V side after the DC-DC step-down. This isn't ceremony — it's the actual safety case.

**19. Vendor firmware matters as much as your firmware.**
The EPAS18 ECU is useless without DCE Motorsport's autonomous firmware variant. The standard firmware does power-steering assist only; msg `0x296` does nothing. **Confirm vendor firmware variants before you commit to the hardware.** This nearly bit the 2020 team and would bite us if we didn't email DCE early.

**20. The plan is going to change.**
You're reading version N of the master plan. By Phase 2 it'll be version N+5. That's healthy — plans should update with learnings. What's not healthy is plans that pretend to be done and ignore new information. Treat the plan as a living document; commit updates with reasons; use git history to trace the why.

### Meta-lessons

**21. Ambitious projects are doable; you just need the right pace.**
"Tiny Waymo on FAU campus" sounds insane for a small lab. It's actually achievable — IF you accept it's a 12-month project, not a 12-week one, and you do one phase at a time without skipping. The 2020 team's mistake wasn't ambition; it was trying to integrate everything before any one piece worked.

**22. Knowledge gaps are not blockers.**
You started this project without mech/electrical background. That's normal. Every researcher on every AV project had to learn the cross-discipline parts at some point. The blocker isn't what you don't know — it's not asking when you don't know.

**23. Future-you needs more notes than you think.**
The 2020 team's piduino_v3.ino was a 13-byte "404 NOT FOUND" stub. Five years later, no one knows what it was supposed to be. Write it down NOW. Future-you (or future-someone) will thank present-you.

---

## 13. Plain-English glossary

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

## 14. What to do next (concretely)

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
