 GEM E4 Self-Driving Conversion — Master Plan           

 Context

 This plan revives a 2018 GEM E4 self-driving conversion at FAU MPCR. The project was started ~2019, abandoned in 2020, and picked back up on 2026-05-01. Substantial 2020-era artifacts have now been recovered from Downloads/OneDrive_1_5-1-2026/ — the original Arduino code (J1939 stack), the steering motor
 documentation (it's an EPAS18 Ultra, not "unknown"), partial J1939 PGN dictionary, team rosters, and 2020 design plans. A partial Gazebo simulation is already in place at Downloads/Cartagena_GEM_E4_workspace/ — Podman + ROS 2 Humble/Jazzy, custom pure-pursuit follower, and a built FAU breezeway world (East
 Engineering → Wimberly Library).

 Goal: "Tiny Waymo" — full self-driving stack on the entirety of FAU Boca Raton campus (~850 acres). Operating speed ≤15 mph. Phase 1 = safety driver in seat. Phase 4 = unmanned.

 Working directory (user has organized into 3 folders):
 /Users/mpcr/Desktop/Golf Cart Code/
 ├── Hardware/   # mechanical, electrical, wiring, packaging — fill from PART A & PART D
 ├── Software/   # firmware (Teensy) + autonomy (Jetson, ROS 2) — fill from PART B
 └── Sim/        # leverage Cartagena_GEM_E4_workspace as base — fill from PART C

 ---
 Recovered artifacts inventory (what to use, what to discard)

 ┌─────────────────────────────────────────────────┬───────────────────────────────────────────────────────────────────────────────────────────────┬────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                     Source                      │                                            Status                                             │                                                                            Use                                                                             │
 ├─────────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ OneDrive/Motor/EPAS18_* (5 PDFs + diagram)      │ Gold — full ECU docs                                                                          │ Steering interface = EPAS18 Ultra CAN protocol, msg IDs 0x290/0x292/0x296. See PART B.2.                                                                   │
 ├─────────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ OneDrive/Arduino Code/ARD1939/                  │ Working J1939 stack for Arduino + MCP2515                                                     │ Starting point for J1939 read-only sniffer firmware                                                                                                        │
 ├─────────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ OneDrive/Arduino Code/J1939 Receiving Messages/ │ Example sketch decoding GEM PGNs                                                              │ Reference; rewrite for Teensy 4.1 + FlexCAN_T4                                                                                                             │
 ├─────────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ OneDrive/Arduino Code/PGN Data.docx             │ Partial GEM J1939 PGN dictionary                                                              │ Vehicle speed (PGN 65265 byte 4), gear (PGN 61445 byte 6), voltage (PGN 61444 byte 4) — read-only                                                          │
 ├─────────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ OneDrive/Design Docs/*.xlsx                     │ 2020 team's draft plans (Steering, Brakes, Accelerator, Control System, Resource Assignments) │ Historical context; team approach to throttle was DAC/digital-pot OR J1939 injection — DAC route adopted (J1939 injection considered too risky to vehicle) │
 ├─────────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ OneDrive/ML/                                    │ 2020 team's ROS + TensorRT notes                                                              │ Skim for context; design decisions superseded                                                                                                              │
 ├─────────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ OneDrive/Email Messages/                        │ STMicro AUTODEVKIT webinar emails                                                             │ Discard — superseded by Jetson choice                                                                                                                      │
 ├─────────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ Cartagena_GEM_E4_workspace/                     │ Active partial sim by current user (mpcrlab@gmail.com / "ari")                                │ Use as Sim foundation. See PART C.                                                                                                                         │
 ├─────────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ Downloads/piduino_v3.ino                        │ 13-byte "404 NOT FOUND" stub                                                                  │ Discard                                                                                                                                                    │
 └─────────────────────────────────────────────────┴───────────────────────────────────────────────────────────────────────────────────────────────┴────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

 ---
 Prior art reference

 ┌────────────────────────────────────────────────────┬────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┬────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                     Reference                      │                                                   What they did                                                    │                                                           What we copy / change                                                            │
 ├────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ UIUC-Robotics gem_ws                               │ Polaris GEM e4 self-driving research platform. ROS 2 Humble. PACMod turnkey DBW (AutonomouStuff/Hexagon). Sensors: │ Software stack: copy (ROS 2 Humble, modular launches, network-Ethernet sensor topology). DBW: do NOT copy PACMod — we already have an      │
 │ (github.com/UIUC-Robotics/gem_ws)                  │  Ouster OS1-128 + Livox HAP, 4× Lucid Triton corner cams, OAK-D LR front stereo, Septentrio AsteRx SBi3 Pro+       │ EPAS18 + we'll do throttle bypass ourselves; PACMod is $15–25k turnkey but unnecessary given existing hardware. Sensor selection: lean on  │
 │                                                    │ GNSS+IMU, Smartmicro 4D radar.                                                                                     │ UIUC for camera placement and the 4× corner cam pattern.                                                                                   │
 ├────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ GEM-Illinois gem-simulator                         │ Gazebo simulation of the same vehicle                                                                              │ Already imported in Cartagena workspace; use as-is                                                                                         │
 │ (github.com/GEM-Illinois/gem-simulator)            │                                                                                                                    │                                                                                                                                            │
 ├────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ 2020 FAU MPCR team (this project)                  │ Built CAD for steering bracket + pedal bracket; reverse-engineered GEM J1939 partially; selected EPAS18 Ultra;     │ Steering motor: keep their EPAS18 Ultra choice. PGN dictionary: extend their work. Throttle CAD bracket: discard (electronic bypass is the │
 │                                                    │ never integrated.                                                                                                  │  right call).                                                                                                                              │
 ├────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ Cartagena workspace (this project, current)        │ Podman + ROS 2 Humble/Jazzy; FAU breezeway world built; pure-pursuit follower written                              │ Sim foundation. Extend world to full campus. Adopt as the "Sim/" folder content.                                                           │
 ├────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ Autoware Universe                                  │ Production-grade open-source AV stack, lanelet2-based                                                              │ Phase 2+ migration target. Phase 0–1 lives on Nav2 for faster bring-up.                                                                    │
 │ (github.com/autowarefoundation/autoware)           │                                                                                                                    │                                                                                                                                            │
 └────────────────────────────────────────────────────┴────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┴────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

 ---
 Locked-in architecture (revised after artifact recovery)

 ┌────────────────────────┬──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │       Subsystem        │                                                                                                                                            Choice                                                                                                                                            │
 ├────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ Steering               │ KEEP existing EPAS18 Ultra ECU + EPAS01 column. Driven by CAN Msg #3 @ 200 Hz from Motion Teensy. Manual override = monitor torque-sensor raw bits in Msg #1 → set map=0. GATING REQUIREMENT: confirm autonomous firmware variant is loaded (must be purchased separately from DCE           │
 │                        │ Motorsport).                                                                                                                                                                                                                                                                                 │
 ├────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ Throttle               │ Electronic bypass — 2× MCP4725 DAC + MCP6002 op-amp + DPDT relay injecting Hall-pair voltages into traction controller. Pedal stays present and operable when relay de-energized.                                                                                                            │
 ├────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ Vehicle telemetry      │ Read-only J1939 sniffer on the GEM internal CAN. Pull vehicle speed (PGN 65265), gear (PGN 61445), voltage (PGN 61444). Replaces aftermarket wheel encoders entirely. NEVER transmit on the vehicle bus.                                                                                     │
 ├────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ Brake                  │ None Phase 1 (safety driver). Phase 2: Kartech 1A001HAJ J1939 actuator (PGN 65280) + Bowden cable (driver presses through). Phase 4: redundant fail-engage parking-brake solenoid for unmanned.                                                                                                │
 ├────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ DBW MCUs               │ 2× Teensy 4.1. Motion Teensy = EPAS18 CAN bridge + safety state echo. Pedals Teensy = throttle DAC + brake actuator + state machine + E-stop monitor + J1939 sniffer (3rd CAN controller — Teensy 4.1 has 3).                                                                                │
 ├────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ DBW CAN bus            │ 500 kbps (matches EPAS18 autonomous mode), isolated from vehicle J1939 bus, twisted pair, 120 Ω term both ends, Deutsch DT04-4P, TJA1051T/3 transceivers, CANable 2.0 to Jetson                                                                                                              │
 ├────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ Compute                │ Jetson AGX Orin 64GB Dev Kit (primary perception+planning); Jetson Orin NX 16GB (safety/logging hot-spare)                                                                                                                                                                                   │
 ├────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ OS / framework         │ JetPack 6.1 → Ubuntu 22.04 → ROS 2 Humble; Isaac ROS containers for perception                                                                                                                                                                                                               │
 ├────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ Autonomy stack         │ Phase 0–1: Nav2. Phase 2+: migrate to Autoware Universe with lanelet2 HD map of FAU Boca campus.                                                                                                                                                                                             │
 ├────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ Sensors                │ Livox Mid-360 LiDAR; ZED 2i front stereo; Leopard IMX390 GMSL front mono; 4× e-CAM130 GMSL corner cams; ZED Mini rear; ArduSimple ZED-F9P RTK + ANN-MB-00 antennas (dual for moving-baseline heading); VectorNav VN-100 IMU.                                                                 │
 ├────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ HD Map                 │ LIO-SAM/FAST-LIO2 PCD + Tier IV Vector Map Builder lanelet2. Tiered build (see PART E).                                                                                                                                                                                                      │
 ├────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ Sim                    │ Cartagena workspace (Podman + ROS 2 Humble + Gazebo Classic / Harmonic). Extend Blender/OSM world from breezeway to full Boca campus.                                                                                                                                                        │
 ├────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ Operating Design       │ Entirety of FAU Boca Raton campus. Tiered rollout: T1 breezeway loop → T2 academic core → T3 full campus including parking.                                                                                                                                                                  │
 │ Domain                 │                                                                                                                                                                                                                                                                                              │
 └────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

 ---
 PART A — HARDWARE (zone-by-zone, every component)

 A0. Cart zone map (where everything lives)

                       ROOF MAST + RACK (sensors, GNSS antennas, LTE)
                               |
                               | (cables down rear D-pillar)
                               v
    ─────────────────────────────────────────────────────────────
   |                                                             |
   |  WINDSHIELD-TOP    DASH CONSOLE                             |
   |  (front cams)      (HMI tablet, ARM/ENGAGE/ESTOP buttons)   |
   |                                                             |
   |  STEERING COLUMN ←── EPAS18 Ultra ECU mounted on            |
   |                       firewall (in-cabin, away from heat)   |
   |                                                             |
   |  PEDAL AREA ←── Pedals Aux Box on firewall above pedals     |
   |                  (DACs, relay, brake actuator Phase 2)      |
   |                                                             |
   |  UNDER-DRIVER-SEAT ←── Safety Box (Kilovac LEV200,          |
   |                          E-stop loop relay, master fuse)     |
   |                          + GEM traction controller (existing)|
   |                                                             |
   |  REAR CARGO / TRUNK ←── MAIN COMPUTE BOX                    |
   |                          (Jetson AGX, Jetson NX, switch,    |
   |                          DC-DCs, network gear, Pelican 1450)|
   |                          + AUX BATTERY BOX (LiFePO4 100Ah)  |
   |                                                             |
    ─────────────────────────────────────────────────────────────

 Zones connect via three cable channels: Channel R (roof → trunk along headliner → rear D-pillar), Channel D (dash → trunk along driver-side floor under trim), Channel S (steering column / pedal → under-seat → trunk via center tunnel).

 A1. Onboard compute (in MAIN COMPUTE BOX)

 ┌────────────┬───────────────────────────────────────────────┬───────────────────────────────────────────────┬─────────────────────┬──────┐
 │    Item    │                     Pick                      │               Acceptable equiv                │        Power        │ Heat │
 ├────────────┼───────────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────────┼──────┤
 │ Primary    │ NVIDIA Jetson AGX Orin 64GB Dev Kit           │ Orin NX 16GB on ConnectTech Boson (downgrade) │ 60 W typ, 90 W peak │ 60 W │
 ├────────────┼───────────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────────┼──────┤
 │ Safety/log │ Jetson Orin NX 16GB on Seeed reComputer J4012 │ Pi 5 8GB (no CUDA → can't degrade-perceive)   │ 25 W                │ 25 W │
 ├────────────┼───────────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────────┼──────┤
 │ Storage A  │ Samsung 990 Pro 2 TB NVMe (in AGX)            │ WD SN850X 2 TB                                │ —                   │ —    │
 ├────────────┼───────────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────────┼──────┤
 │ Storage B  │ Samsung 990 Pro 2 TB NVMe (in NX)             │ WD SN850X 2 TB                                │ —                   │ —    │
 ├────────────┼───────────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────────┼──────┤
 │ Net switch │ Mikrotik CRS305-1G-4S+IN (4× SFP+ 10 GbE)     │ Mokerlink 10 G 5-port industrial              │ 10 W                │ 10 W │
 └────────────┴───────────────────────────────────────────────┴───────────────────────────────────────────────┴─────────────────────┴──────┘

 Ask FAU inventory: Jetson AGX Orin Dev Kits, Orin NX modules + carriers, NVMe ≥ 1 TB, 10 GbE switches.

 A2. Cameras (7 total — surround perception)

 ┌──────────────┬────────────────────────────────────────┬───────────────────────┬──────────────────┬────────────────────────────────┐
 │     Pos      │                  Pick                  │         Mount         │  Cable to trunk  │             Notes              │
 ├──────────────┼────────────────────────────────────────┼───────────────────────┼──────────────────┼────────────────────────────────┤
 │ Front stereo │ Stereolabs ZED 2i 4mm IP66             │ Windshield top center │ USB-C 5 m active │ Depth + ML redundancy          │
 ├──────────────┼────────────────────────────────────────┼───────────────────────┼──────────────────┼────────────────────────────────┤
 │ Front mono   │ Leopard LI-IMX390-GMSL2 + Hawk dev kit │ Windshield top center │ Fakra coax 5 m   │ Auto-grade HDR sensor for YOLO │
 ├──────────────┼────────────────────────────────────────┼───────────────────────┼──────────────────┼────────────────────────────────┤
 │ FL corner    │ e-CAM130_CUOAGX (GMSL)                 │ Front-left A-pillar   │ Fakra coax 4 m   │ 120° FOV                       │
 ├──────────────┼────────────────────────────────────────┼───────────────────────┼──────────────────┼────────────────────────────────┤
 │ FR corner    │ e-CAM130_CUOAGX                        │ Front-right A-pillar  │ Fakra coax 4 m   │ 120° FOV                       │
 ├──────────────┼────────────────────────────────────────┼───────────────────────┼──────────────────┼────────────────────────────────┤
 │ RL corner    │ e-CAM130_CUOAGX                        │ Rear-left B-pillar    │ Fakra coax 3 m   │ 120° FOV                       │
 ├──────────────┼────────────────────────────────────────┼───────────────────────┼──────────────────┼────────────────────────────────┤
 │ RR corner    │ e-CAM130_CUOAGX                        │ Rear-right B-pillar   │ Fakra coax 3 m   │ 120° FOV                       │
 ├──────────────┼────────────────────────────────────────┼───────────────────────┼──────────────────┼────────────────────────────────┤
 │ Rear         │ ZED Mini                               │ Rear cargo top        │ USB-C 3 m        │ Backing + Phase 4              │
 └──────────────┴────────────────────────────────────────┴───────────────────────┴──────────────────┴────────────────────────────────┘

 Calibration discipline: rigid M5 mounts, Sorbothane-isolated. Calibrate once, then never move them. UIUC lab learned this the hard way — extrinsic drift dominates mid-project pain.

 Ask FAU inventory: ZED 2i / ZED X / ZED Mini, RealSense D455, OAK-D Pro W, Leopard / FRAMOS GMSL kits + Hawk/Quartz carriers (rare and gold), Lucid Triton PoE cams.

 A3. LiDAR

 Pick: Livox Mid-360. ~$1,400. 360° × 59°, 200 m range, IP67, native ROS 2 driver livox_ros_driver2. Roof mast centerline, slightly forward of cab, level ±1°. Cat6 IP67 + 12V power down to trunk.

 Acceptable equiv: Ouster OS1-32/64 (~$5–10k, gold if FAU already has one), Velodyne VLP-16 (legacy, often free from retired projects), Hesai XT-32, Robosense Helios.

 Skip: RPLIDAR (2D only — useless as primary).

 Ask FAU inventory: ANY 3D LiDAR. Even a dusty Velodyne Puck saves $1,400.

 A4. GPS-RTK + IMU

 ┌─────────────────────┬──────────────────────────────────────────────────────────────────────────┬──────────────────────────────────────────────────────┐
 │        Item         │                                   Pick                                   │                        Mount                         │
 ├─────────────────────┼──────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
 │ GNSS receiver       │ ArduSimple simpleRTK2B w/ u-blox ZED-F9P × 2 for moving-baseline heading │ Trunk                                                │
 ├─────────────────────┼──────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
 │ Antennas            │ 2× u-blox ANN-MB-00 multiband, magnetic                                  │ Roof mast, ≥40 cm separation along longitudinal axis │
 ├─────────────────────┼──────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
 │ Corrections         │ NTRIP via Florida FPRN (free, dense Boca coverage)                       │ Software config — primary                            │
 ├─────────────────────┼──────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
 │ Lab base (optional) │ SparkFun RTK Facet L-Band on lab roof                                    │ Backup to NTRIP                                      │
 ├─────────────────────┼──────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
 │ IMU primary         │ VectorNav VN-100                                                         │ Trunk, near vehicle CG                               │
 ├─────────────────────┼──────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
 │ IMU secondary       │ Bosch BNO086 dev board                                                   │ Chassis frame, redundant                             │
 └─────────────────────┴──────────────────────────────────────────────────────────────────────────┴──────────────────────────────────────────────────────┘

 Why dual ZED-F9P with moving-baseline: the cart sits still a lot. Single-antenna RTK can't derive heading without motion → bad initial state every cold start. Dual gives you heading from carrier-phase difference even at rest.

 Ask FAU inventory: ZED-F9P/F9R/F9H modules, multiband GNSS antennas, VectorNav/Xsens/Microstrain IMUs. Email FAU Geomatics — they may already operate a campus base station with NTRIP credentials.

 A5. Drive-by-wire MCUs (2× Teensy 4.1)

 Both Teensy 4.1 (~$30 ea). 600 MHz Cortex-M7. 3 hardware CAN controllers (this matters — see below).

 ┌───────────────┬───────────────────────────────────────────────────────┬─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┬─────────┬────────────────────────────────────────┬───────────────────────────────┐
 │      MCU      │                       Lives in                        │                                                         Job                                                         │  CAN1   │                  CAN2                  │             CAN3              │
 ├───────────────┼───────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────┼────────────────────────────────────────┼───────────────────────────────┤
 │ Motion Teensy │ Steering Aux Box (firewall, in cabin near EPAS18 ECU) │ EPAS18 bridge: TX msg 0x296 @ 200 Hz, RX msg 0x290+0x292 @ 100 Hz, manual-override detection, fault echo to DBW bus │ DBW bus │ EPAS bus (separate or shared — see A6) │ unused                        │
 ├───────────────┼───────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────┼────────────────────────────────────────┼───────────────────────────────┤
 │ Pedals Teensy │ Pedals Aux Box (firewall above pedals)                │ Throttle DAC, brake actuator, state machine, E-stop monitor, brake-light tap, J1939 read-only sniffer               │ DBW bus │ J1939 vehicle bus (READ ONLY)          │ unused or 2nd J1939 if needed │
 └───────────────┴───────────────────────────────────────────────────────┴─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┴─────────┴────────────────────────────────────────┴───────────────────────────────┘

 Why 2 MCUs not 1: failure-domain separation. A steering bug cannot accidentally floor the throttle. They cross-monitor heartbeats; if either silently dies the other forces SAFE state.

 Ask FAU inventory: Teensy 4.1 boards (any qty), MCP2515 SPI CAN modules (legacy 2020 hardware acceptable as J1939 sniffer fallback).

 A6. CAN bus topology (3 buses, kept separate)

    ┌────────────────────────── DBW BUS (500 kbps, our bus) ────────────────────────┐
    │                                                                                │
    │  Motion Teensy CAN1 ─── Pedals Teensy CAN1 ─── CANable 2.0 ─── Jetson AGX Orin │
    │                                                                                │
    │  120Ω at one end (CANable), 120Ω at other end (Pedals Teensy board)            │
    └────────────────────────────────────────────────────────────────────────────────┘

    ┌────────────────────────── EPAS BUS (500 kbps, DCE-internal) ─────────────────┐
    │                                                                               │
    │  EPAS18 Ultra ECU (signal connector pins 19/20, 29/30) ─── Motion Teensy CAN2│
    │                                                                               │
    │  120Ω at each end. Optionally: bridge to DBW bus via Motion firmware proxy   │
    │  rather than physical bridge — cleaner failure isolation.                     │
    └───────────────────────────────────────────────────────────────────────────────┘

    ┌────────────────────── VEHICLE J1939 BUS (250 kbps, READ ONLY) ───────────────┐
    │                                                                               │
    │  GEM E4 internal CAN ─── isolated tap via TI ISO1042 ─── Pedals Teensy CAN2  │
    │                                                                               │
    │  NEVER TRANSMIT. ISO1042 isolation prevents accidentally pulling the bus low.│
    └───────────────────────────────────────────────────────────────────────────────┘

 Topology recommendation: separate EPAS bus from DBW bus to avoid mixing safety-critical steering CAN with the J1939 sniffer and Pedals telemetry. Motion Teensy proxies state between them. Adds ~10ms latency but isolates faults.

 CANable 2.0 (~$45) is the Jetson↔CAN dongle. SocketCAN on Linux. Acceptable equiv: PCAN-USB, Kvaser Leaf v2, Waveshare CAN HAT.

 A7. Steering subsystem (revised — keep existing EPAS18)

 No motor replacement. Keep:
 - EPAS01 Column Assist motor (already mounted on column)
 - Built-in torque sensor (5-pin Deutsch IMC26-2005S to ECU)
 - Steering angle sensor (0–5V to ECU pin 3)
 - EPAS18 Ultra ECU (Autosport AS016-08 power + AS014-35 signal)

 Action items before firmware work:
 1. Confirm DCE autonomous firmware is loaded onto the ECU. Standard EPAS18 firmware does NOT accept CAN Msg #3. If unknown, contact sales@dcemotorsport.com and reference the ECU's serial number printed on its case.
 2. Verify steering angle sensor calibration (LH stop bits < RH stop bits; see User Guide §10).
 3. Verify torque-zero calibration (power-cycle 3× procedure with no driver torque applied).
 4. Verify wiring matches DCE diagram (OneDrive/Motor/EPAS18_Wiring_Diagram_-_USA.pdf).

 Steering control protocol (in firmware):
 - TX from Motion Teensy: ID 0x296 @ 200 Hz, D0=map (1–5 autonomous, 0=local), D1=Torque A, D2=Torque B, where D1+D2=255. Map=2 or 3 is a reasonable starting choice; tune up.
 - RX into Motion Teensy: 0x290 (torque/duty/current/V/temp at 100 Hz), 0x292 (steering angle / map / status / limits at 100 Hz).
 - Manual override: when raw torque A/B (Msg #1 D6/D7) deviates from steady-state for >50 ms → set Msg #3 D0=0 (local mode) → EPS smoothly returns to power-assist behavior. Latch DISENGAGED in the master state machine.

 A8. Throttle subsystem (electronic bypass)

 ┌────────────────────┬─────────────────────────────────────────────────────────────────────────────────────┬────────────────────────────┬───────────────────────────────────────────────────────────────────────┐
 │        Item        │                                        Pick                                         │             In             │                                 Cable                                 │
 ├────────────────────┼─────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────┼───────────────────────────────────────────────────────────────────────┤
 │ DACs (×2 mirrored) │ MCP4725 I²C breakout                                                                │ Pedals Aux Box             │ I²C 30 cm to Pedals Teensy                                            │
 ├────────────────────┼─────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────┼───────────────────────────────────────────────────────────────────────┤
 │ Op-amp buffer      │ MCP6002 dual rail-to-rail                                                           │ Pedals Aux Box             │ —                                                                     │
 ├────────────────────┼─────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────┼───────────────────────────────────────────────────────────────────────┤
 │ Failsafe relay     │ Omron G8HE-1A7T DPDT auto                                                           │ Pedals Aux Box             │ Coil energized only when state=ACTIVE & Jetson HB OK                  │
 ├────────────────────┼─────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────┼───────────────────────────────────────────────────────────────────────┤
 │ Pedal harness tap  │ Cut into existing GEM pedal harness; T-junction with DAC outputs through DPDT relay │ Behind dash, in pedal area │ OEM mating connector (probably Molex MX150 — measure pins to confirm) │
 └────────────────────┴─────────────────────────────────────────────────────────────────────────────────────┴────────────────────────────┴───────────────────────────────────────────────────────────────────────┘

 Verify the GEM E4 throttle pinout before cutting: probe with multimeter, slow pedal sweep, record V1/V2 vs. travel both channels. Build the DAC output map from this measurement.

 Coil power chain (autonomy-armed): Key on AND dash ARM button latched AND Pedals state machine ACTIVE AND Jetson HB present AND brake pedal NOT pressed. Any link breaks → coil drops → pedal direct.

 A9. Brake actuator (Phase 2 only — keep design ready but don't buy yet)

 ┌─────────────────────┬───────────────────────────────────────────────────────────────────────────────┬──────────────────────────────────────────────────────────────────────────────┐
 │        Item         │                                     Pick                                      │                                    Notes                                     │
 ├─────────────────────┼───────────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────┤
 │ Linear actuator     │ Kartech 1A001HAJ (J1939 servo, 12 V, internal closed-loop). Already in lab inventory from 2020. │ Captured command frames in Software/firmware/kartech_brake_reference/        │
 ├─────────────────────┼───────────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────┤
 │ Mounting            │ Firewall bracket → Bowden cable to brake pedal arm clamp                      │ Driver always presses deeper = mechanical override                           │
 ├─────────────────────┼───────────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────┤
 │ Driver              │ Built into the Kartech actuator (no external H-bridge required)               │ Pedals Teensy CAN3 → SN65HVD230 → Kartech CAN connector. PGN 65280, 250 kbps │
 ├─────────────────────┼───────────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────┤
 │ Phase 4 fail-engage │ Solenoid-actuated parking brake tied directly to E-stop loop                  │ Power loss → brake engages mechanically (inverse of service brake fail-safe) │
 └─────────────────────┴───────────────────────────────────────────────────────────────────────────────┴──────────────────────────────────────────────────────────────────────────────┘

 A10. Safety hardware (day-one mandatory)

 ┌───────────────────────────┬─────────────────────────────────────────────────────────────────┬─────────────────────────────────────────────────────────┬──────────────────────────────────────────────────────────────────────────────────────┐
 │           Item            │                              Pick                               │                          Where                          │                                        Notes                                         │
 ├───────────────────────────┼─────────────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────┤
 │ E-stop button × 2         │ IDEC XA1E-BV4U02R 22mm mushroom NC                              │ Dash + passenger side                                   │ Series-wired, NC contacts                                                            │
 ├───────────────────────────┼─────────────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────┤
 │ Safety contactor          │ TE/Tyco Kilovac LEV200 (200A, 12V coil)                         │ Under-Driver-Seat Safety Box                            │ Hardware-only path; gates 12V to throttle relay coil + EPAS18 power + brake actuator │
 ├───────────────────────────┼─────────────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────┤
 │ Brake light tap           │ PC817 optoisolator                                              │ Pedals Aux Box                                          │ GEM brake light switch → optoiso → Pedals Teensy GPIO                                │
 ├───────────────────────────┼─────────────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────┤
 │ Wheel-touch sensor        │ MPR121 cap-touch + copper foil under grip wrap                  │ Steering wheel                                          │ Disengage on any touch                                                               │
 ├───────────────────────────┼─────────────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────┤
 │ Wireless E-stop (Phase 4) │ Telecrane F24-8D + safety-relay receiver                        │ Receiver hardwired into E-stop loop, NOT through Jetson │ Range ≥100 m line-of-sight                                                           │
 ├───────────────────────────┼─────────────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────┤
 │ Status LEDs               │ 5× 22mm LED indicators (ARMED, ACTIVE, FAULT, GPS-FIX, LINK-OK) │ Dash                                                    │ Driven by Pedals Teensy DIO                                                          │
 └───────────────────────────┴─────────────────────────────────────────────────────────────────┴─────────────────────────────────────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────┘

 Software not in drop path — every E-stop pulls power before any MCU can react.

 A11. Power architecture

 Pack voltage: TBD — confirm 48V vs 72V before ordering DC-DC. Most 2018 E4 LSV trim is 72V.

 ┌────────────────────────┬────────────────────────┬─────────────────────────────────────────────────────────────────────────────────────────────────────────────┬─────────────────────────────────────────────────────┐
 │          Rail          │         Source         │                                                    Pick                                                     │                        Power                        │
 ├────────────────────────┼────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────┤
 │ Traction pack 48/72 V  │ Existing GEM batteries │ —                                                                                                           │ —                                                   │
 ├────────────────────────┼────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────┤
 │ 12 V aux (compute)     │ Pack → DC-DC           │ Vicor DCM3623TD2K20T6E0xy (200 W, 36–75V in → 12V out, isolated) — for 72V; or Mean Well RSDW20H-12 for 48V │ 200 W                                               │
 ├────────────────────────┼────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────┤
 │ 12 V aux (logic)       │ Pack → DC-DC           │ TDK-Lambda PXC15-72WS12 (15 W, logic-only)                                                                  │ 15 W                                                │
 ├────────────────────────┼────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────┤
 │ 12 V aux battery (UPS) │ Independent            │ Battle Born BB1012 LiFePO4 12V 100Ah (Group 24 size, 11.4 kg)                                               │ UPS + ride-through + steering motor inrush absorber │
 ├────────────────────────┼────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────┤
 │ 5 V logic              │ 12V aux → buck         │ 2× Pololu D24V50F5 (5 A)                                                                                    │ Teensies, DACs, encoders, relays                    │
 ├────────────────────────┼────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────┤
 │ 3.3 V                  │ Onboard Teensy reg     │ —                                                                                                           │ <250 mA per Teensy                                  │
 └────────────────────────┴────────────────────────┴─────────────────────────────────────────────────────────────────────────────────────────────────────────────┴─────────────────────────────────────────────────────┘

 Aux battery placement: Group 24 LiFePO4 is 26 cm × 17 cm × 22 cm. Will not fit in main Pelican 1450 alongside Jetsons. Mount in separate dedicated battery box in trunk floor or rear cargo (slide-out tray for service).

 Grounding (critical): single-point star ground at aux-battery negative. EPAS18 motor power gets its own heavy ground (4 AWG) directly to aux battery, NOT shared with logic ground. CAN shields drained at one end only (Jetson end).

 EMI: Würth 742 711 32 ferrite chokes on EPAS18 motor leads. Shielded twisted pair for SPI/sensor lines. Route DBW CAN ≥30 cm from EPAS motor cables. Cat6 with foil shielding (FTP) on LiDAR + camera Ethernet.

 A12. MAIN COMPUTE BOX (Pelican 1450) — bill of contents

 Pelican 1450 modified. Internal usable space: ~16" × 13" × 6.8".

 ┌────────────────────── Pelican 1450 (top view) ──────────────────────┐
 │                                                                      │
 │  ┌──────────────┐      ┌──────────────┐                              │
 │  │ Jetson AGX   │      │ Jetson NX 16 │                              │
 │  │ Orin 64GB    │      │ on Boson     │   ← finned heatsink plates   │
 │  │ Dev Kit      │      │ carrier      │     bonded to enclosure top  │
 │  │ NVMe 2TB     │      │ NVMe 2TB     │                              │
 │  └──────────────┘      └──────────────┘                              │
 │                                                                      │
 │  ┌──────────────────┐  ┌──────────────────────────┐                  │
 │  │ Mikrotik CRS305  │  │ Vicor DCM3623 + Pololu   │                  │
 │  │ 4× SFP+ 10 GbE   │  │ D24V50F5 ×2              │                  │
 │  └──────────────────┘  └──────────────────────────┘                  │
 │                                                                      │
 │  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐                  │
 │  │ CANable  │ │ Cradle-  │ │ 433 MHz E-stop RX    │                  │
 │  │ 2.0      │ │ point    │ │ + Telecrane safety   │                  │
 │  │          │ │ IBR200   │ │ relay                │                  │
 │  └──────────┘ └──────────┘ └──────────────────────┘                  │
 │                                                                      │
 │  Bus bars:  [+12V aux]  [GND]   |   Fuse block: Blue Sea 5025 6-pos  │
 │                                                                      │
 │  Active cooling:  2× 80mm 12V fans (Noctua NF-A8) → cold plate       │
 │                   external + Gore-Tex IP67 vent (W. L. Gore PMF200)   │
 │                                                                      │
 │  Panel-mount connectors (all on rear face):                          │
 │    - 6× RJ-45 IP67 (LiDAR + 4 corner cams + spare)                   │
 │    - 4× Fakra coax (front GMSL + 4 corner GMSL via internal hub)     │
 │    - 2× USB-A IP67 (ZED 2i, ZED Mini)                                │
 │    - 1× DB9 (RS-232 to VN-100 IMU)                                   │
 │    - 1× SMA × 2 (GNSS antenna feeds — to ZED-F9P)                    │
 │    - 1× DT04-12P (DBW CAN + 12V to dash console + steering box)      │
 │    - 1× DT04-4P (12V aux power feed in from aux battery)             │
 │    - 1× SMA (LTE antenna)                                            │
 │                                                                      │
 └──────────────────────────────────────────────────────────────────────┘

 A13. Thermal management (Florida — non-negotiable)

 Heat load in MAIN COMPUTE BOX:
 - AGX Orin: 60 W typ
 - Orin NX: 25 W typ
 - Network switch: 10 W
 - DC-DC losses: ~20 W
 - Misc (modem, CANable, RX): 10 W
 - Total: ~125 W steady, peaks to 160 W

 Florida ambient: 35 °C summer, plus solar load on a metal trunk → interior could hit 50 °C unmitigated. AGX Orin throttles >85 °C junction → unacceptable in middle of a closed-loop run.

 Cooling solution: dedicated 12 V Peltier-based "cabinet AC" mounted to Pelican lid.
 - Pick: Adroit/EBM-Papst SLE-200 (~$200, 100–200 W cooling, 12 V, IP54).
 - Acceptable equiv: TECA AHP-301HC (~$700, beefier).
 - Recirculate internal air across cold plate; exhaust hot side externally through louvered grille on rear of Pelican.
 - Internal recirculation fans (2× Noctua NF-A8) ensure no internal hot spot at the AGX.
 - Gore-Tex vent (W. L. Gore PMF200, IP67) equalizes pressure without admitting moisture.

 Sensors: all picks above are IP66/IP67. UV-resistant Tefzel cable jackets.

 A14. Cable routing schedule (every cable, every length)

 Channel R — Roof to Trunk (2.5–3 m, headliner → rear D-pillar)

 ┌─────┬──────────────────────────────┬────────────────────────────┬────────────────────────────┬────────────────────────────┐
 │ ID  │            Cable             │            Spec            │           Length           │         Connectors         │
 ├─────┼──────────────────────────────┼────────────────────────────┼────────────────────────────┼────────────────────────────┤
 │ R01 │ LiDAR Ethernet + 12V (combo) │ Cat6 IP67 + 18 AWG twin    │ 3.0 m                      │ RJ-45 IP67 / DT04-2P       │
 ├─────┼──────────────────────────────┼────────────────────────────┼────────────────────────────┼────────────────────────────┤
 │ R02 │ ZED 2i USB                   │ USB-C 5 m active extension │ 3.0 m                      │ USB-C IP67 panel mount     │
 ├─────┼──────────────────────────────┼────────────────────────────┼────────────────────────────┼────────────────────────────┤
 │ R03 │ Leopard front GMSL           │ Fakra coax (white code)    │ 3.0 m                      │ Fakra at both ends         │
 ├─────┼──────────────────────────────┼────────────────────────────┼────────────────────────────┼────────────────────────────┤
 │ R04 │ FL corner GMSL               │ Fakra coax                 │ 3.5 m (via A-pillar route) │ Fakra                      │
 ├─────┼──────────────────────────────┼────────────────────────────┼────────────────────────────┼────────────────────────────┤
 │ R05 │ FR corner GMSL               │ Fakra coax                 │ 3.5 m                      │ Fakra                      │
 ├─────┼──────────────────────────────┼────────────────────────────┼────────────────────────────┼────────────────────────────┤
 │ R06 │ RL corner GMSL               │ Fakra coax                 │ 2.5 m                      │ Fakra                      │
 ├─────┼──────────────────────────────┼────────────────────────────┼────────────────────────────┼────────────────────────────┤
 │ R07 │ RR corner GMSL               │ Fakra coax                 │ 2.5 m                      │ Fakra                      │
 ├─────┼──────────────────────────────┼────────────────────────────┼────────────────────────────┼────────────────────────────┤
 │ R08 │ GNSS ant 1                   │ RG-58 SMA-N                │ 3.0 m                      │ SMA male / N-type bulkhead │
 ├─────┼──────────────────────────────┼────────────────────────────┼────────────────────────────┼────────────────────────────┤
 │ R09 │ GNSS ant 2                   │ RG-58 SMA-N                │ 3.0 m (≥40 cm separation)  │ SMA male / N-type bulkhead │
 ├─────┼──────────────────────────────┼────────────────────────────┼────────────────────────────┼────────────────────────────┤
 │ R10 │ LTE antenna                  │ LMR-200                    │ 2.5 m                      │ SMA                        │
 ├─────┼──────────────────────────────┼────────────────────────────┼────────────────────────────┼────────────────────────────┤
 │ R11 │ Wireless E-stop RX antenna   │ RG-58                      │ 2.0 m                      │ SMA                        │
 ├─────┼──────────────────────────────┼────────────────────────────┼────────────────────────────┼────────────────────────────┤
 │ R12 │ Roof-bundle ground           │ 10 AWG                     │ 2.5 m                      │ Ring terminal              │
 └─────┴──────────────────────────────┴────────────────────────────┴────────────────────────────┴────────────────────────────┘

 Bundle: all 12 cables in 1.5"-diameter split corrugated loom (T-Solar or Hollar Hose), routed through grommeted holes in rear D-pillar, secured every 30 cm with adhesive zip-tie mounts.

 Channel D — Dash to Trunk (2.0–2.5 m, driver-side floor under trim)

 ┌─────┬─────────────────────────────────────────────┬──────────────────────────────┬────────┬────────────┐
 │ ID  │                    Cable                    │             Spec             │ Length │ Connectors │
 ├─────┼─────────────────────────────────────────────┼──────────────────────────────┼────────┼────────────┤
 │ D01 │ HMI tablet Ethernet                         │ Cat6 patch                   │ 2.5 m  │ RJ-45      │
 ├─────┼─────────────────────────────────────────────┼──────────────────────────────┼────────┼────────────┤
 │ D02 │ DBW CAN to Pedals (and onward)              │ Belden 9841 twisted pair     │ 2.0 m  │ DT04-4P    │
 ├─────┼─────────────────────────────────────────────┼──────────────────────────────┼────────┼────────────┤
 │ D03 │ Dash button bundle (ARM/ENGAGE/E-stop/LEDs) │ 16 conductor 22 AWG MIL-spec │ 2.0 m  │ DT04-12P   │
 ├─────┼─────────────────────────────────────────────┼──────────────────────────────┼────────┼────────────┤
 │ D04 │ 12V aux to dash                             │ 14 AWG                       │ 2.0 m  │ DT04-2P    │
 ├─────┼─────────────────────────────────────────────┼──────────────────────────────┼────────┼────────────┤
 │ D05 │ Status LED return                           │ (within D03)                 │ —      │ —          │
 └─────┴─────────────────────────────────────────────┴──────────────────────────────┴────────┴────────────┘

 Routing: through driver-side kick panel grommet, along inner sill under door trim, behind rear seat, into Pelican rear panel.

 Channel S — Steering / Pedal area to Trunk (1.5–2.5 m, center tunnel)

 ┌─────┬────────────────────────────────────────────┬──────────────────────────────────────┬─────────────────────────────────────────────┬──────────────────────────────────────────┐
 │ ID  │                   Cable                    │                 Spec                 │                   Length                    │                Connectors                │
 ├─────┼────────────────────────────────────────────┼──────────────────────────────────────┼─────────────────────────────────────────────┼──────────────────────────────────────────┤
 │ S01 │ Motion Teensy DBW CAN to bus               │ Belden 9841                          │ 2.0 m                                       │ DT04-4P                                  │
 ├─────┼────────────────────────────────────────────┼──────────────────────────────────────┼─────────────────────────────────────────────┼──────────────────────────────────────────┤
 │ S02 │ EPAS18 power feed (heavy)                  │ 4 AWG                                │ 1.5 m to under-seat fuse, then 0.5 m to ECU │ M8 ring terminals + Autosport AS616-08SN │
 ├─────┼────────────────────────────────────────────┼──────────────────────────────────────┼─────────────────────────────────────────────┼──────────────────────────────────────────┤
 │ S03 │ EPAS18 signal harness                      │ OEM DCE harness or custom AS614-35SN │ 1.5 m to torque/angle sensors               │ Autosport                                │
 ├─────┼────────────────────────────────────────────┼──────────────────────────────────────┼─────────────────────────────────────────────┼──────────────────────────────────────────┤
 │ S04 │ Pedals Teensy DBW CAN to bus               │ Belden 9841                          │ 1.5 m                                       │ DT04-4P                                  │
 ├─────┼────────────────────────────────────────────┼──────────────────────────────────────┼─────────────────────────────────────────────┼──────────────────────────────────────────┤
 │ S05 │ Pedal Hall pair tap (×2 channels)          │ 4-cond shielded                      │ 0.3 m within Pedals Aux Box                 │ Spliced into OEM pedal connector         │
 ├─────┼────────────────────────────────────────────┼──────────────────────────────────────┼─────────────────────────────────────────────┼──────────────────────────────────────────┤
 │ S06 │ DAC outputs to relay → traction controller │ (within Pedals Box)                  │ —                                           │ —                                        │
 ├─────┼────────────────────────────────────────────┼──────────────────────────────────────┼─────────────────────────────────────────────┼──────────────────────────────────────────┤
 │ S07 │ Brake light switch tap (Phase 1)           │ 2-cond                               │ 0.5 m to GEM brake light                    │ Optoiso input                            │
 ├─────┼────────────────────────────────────────────┼──────────────────────────────────────┼─────────────────────────────────────────────┼──────────────────────────────────────────┤
 │ S08 │ J1939 vehicle CAN tap                      │ Belden 9841                          │ 1.0 m to GEM diag port (location TBD)       │ Isolated CAN transceiver                 │
 ├─────┼────────────────────────────────────────────┼──────────────────────────────────────┼─────────────────────────────────────────────┼──────────────────────────────────────────┤
 │ S09 │ Brake actuator power + CAN (Phase 2)       │ 2-cond power + Belden 9841 CAN pair  │ 1.5 m to Kartech actuator                   │ DT04-4P (power) + CAN connector          │
 └─────┴────────────────────────────────────────────┴──────────────────────────────────────┴─────────────────────────────────────────────┴──────────────────────────────────────────┘

 Channel ESP — E-stop loop (under-seat → dash → passenger → wireless RX)

 ┌─────┬────────────────────────────┬─────────────┬─────────────────────┬─────────────────┐
 │ ID  │           Cable            │    Spec     │       Length        │   Connectors    │
 ├─────┼────────────────────────────┼─────────────┼─────────────────────┼─────────────────┤
 │ E01 │ Dash mushroom NC           │ 18 AWG twin │ 1.5 m               │ DT04-2P         │
 ├─────┼────────────────────────────┼─────────────┼─────────────────────┼─────────────────┤
 │ E02 │ Passenger mushroom NC      │ 18 AWG twin │ 1.5 m               │ DT04-2P         │
 ├─────┼────────────────────────────┼─────────────┼─────────────────────┼─────────────────┤
 │ E03 │ Wireless RX safety contact │ 18 AWG twin │ 0.5 m (RX in trunk) │ Internal wiring │
 ├─────┼────────────────────────────┼─────────────┼─────────────────────┼─────────────────┤
 │ E04 │ Loop to Kilovac coil       │ 12 AWG      │ 0.3 m               │ Ring terminal   │
 └─────┴────────────────────────────┴─────────────┴─────────────────────┴─────────────────┘

 Loop topology: all E-stops + wireless RX safety contact in series, NC, total loop drives Kilovac coil. Open loop = drop everything.

 A15. Power distribution

    72V Traction Pack (existing GEM)
         │
         ├── GEM original DC-DC → 12V aux (existing house bus, ~30 A capacity)
         │         │
         │         └── original 12V GEM accessories (lights, horn, etc.)
         │
         └── Vicor DCM3623 200W (new) ──┐
                                        │
                                        ▼
    ┌───────────── Aux 12V Distribution Bus (in Pelican) ──────────────┐
    │                                                                   │
    │  Battle Born 100Ah LiFePO4 (UPS / surge buffer) ─── 100A ANL ─────┤
    │                                                                   │
    │  Blue Sea 5025 fuse block (6 ATC fuses):                          │
    │   F1  20A  → AGX Orin (12V → 19V boost via Jetson dev kit jack)   │
    │   F2  10A  → Orin NX                                              │
    │   F3  5A   → Network switch                                       │
    │   F4  5A   → Cradlepoint LTE                                      │
    │   F5  3A   → CANable + sensors (VN-100, ZED-F9P, IMU)             │
    │   F6  10A  → Steering Aux Box (Motion Teensy + EPAS power chain)  │
    │   F7  5A   → Pedals Aux Box (Pedals Teensy + DACs + relay)        │
    │   F8  15A  → Brake Actuator (Phase 2)                             │
    │   F9  10A  → Cabin AC (Peltier cooler)                            │
    │   F10 5A   → Dash Console + LEDs                                  │
    │                                                                   │
    └───────────────────────────────────────────────────────────────────┘

    EPAS18 Ultra power: separate 80A ANL fuse, separate 4 AWG run from
    aux battery → Kilovac LEV200 → ECU. Independent of fuse block above
    to absorb ~80A transient steering current without browning out logic.

 A16. Bill of Materials — Hardware (rough)

 ┌──────────────────────────────────────────────────────────────────────────────┬──────────┐
 │                                    Group                                     │ Subtotal │
 ├──────────────────────────────────────────────────────────────────────────────┼──────────┤
 │ Compute (AGX Orin + Orin NX + 2× NVMe + switch)                              │ $3,300   │
 ├──────────────────────────────────────────────────────────────────────────────┼──────────┤
 │ Cameras (ZED 2i + Leopard GMSL + 4× e-CAM130 + ZED Mini)                     │ $2,950   │
 ├──────────────────────────────────────────────────────────────────────────────┼──────────┤
 │ LiDAR (Livox Mid-360)                                                        │ $1,400   │
 ├──────────────────────────────────────────────────────────────────────────────┼──────────┤
 │ GNSS+IMU (2× ZED-F9P + 2× ANN-MB-00 + VN-100 + BNO086 backup)                │ $1,425   │
 ├──────────────────────────────────────────────────────────────────────────────┼──────────┤
 │ DBW MCUs + CAN gear (2× Teensy + transceivers + CANable + Deutsch kit)       │ $200     │
 ├──────────────────────────────────────────────────────────────────────────────┼──────────┤
 │ Throttle bypass parts (DACs + op-amps + relay + harness)                     │ $80      │
 ├──────────────────────────────────────────────────────────────────────────────┼──────────┤
 │ Brake (Phase 2; Bowden cable + SN65HVD230 — Kartech already on hand)         │ $30      │
 ├──────────────────────────────────────────────────────────────────────────────┼──────────┤
 │ Safety (2× E-stops + Kilovac + MPR121 + wireless E-stop kit)                 │ $400     │
 ├──────────────────────────────────────────────────────────────────────────────┼──────────┤
 │ Power (Vicor DC-DC + LiFePO4 100Ah + bucks + fuse block + ANL)               │ $750     │
 ├──────────────────────────────────────────────────────────────────────────────┼──────────┤
 │ Enclosures (Pelican 1450 + battery box + Aux boxes ×3 + Peltier AC + fans)   │ $700     │
 ├──────────────────────────────────────────────────────────────────────────────┼──────────┤
 │ Cabling (Cat6 IP67 + Fakras + USB ext + Belden + MIL-spec wire + Deutsch DT) │ $700     │
 ├──────────────────────────────────────────────────────────────────────────────┼──────────┤
 │ LTE modem + network gear + dash tablet                                       │ $850     │
 ├──────────────────────────────────────────────────────────────────────────────┼──────────┤
 │ Subtotal                                                                     │ ~$13,000 │
 ├──────────────────────────────────────────────────────────────────────────────┼──────────┤
 │ Contingency 15%                                                              │ ~$2,000  │
 ├──────────────────────────────────────────────────────────────────────────────┼──────────┤
 │ Grand Total                                                                  │ ~$15,000 │
 └──────────────────────────────────────────────────────────────────────────────┴──────────┘

 Cuts available: drop secondary Jetson NX (-$700), drop Leopard GMSL (-$600), drop lab RTK base (already $0 if using NTRIP), drop Cradlepoint LTE (-$250) → ~$13,500. Lab inventory hits could remove another $2–4k.

 ---
 PART B — SOFTWARE

 B1. Repository / workspace layout

 /Users/mpcr/Desktop/Golf Cart Code/
 ├── Hardware/
 │   ├── wiring_schedules/          # PDFs of cable schedules from PART A.14
 │   ├── cad/                        # Solidworks/Step files for brackets & mounts
 │   ├── enclosure_layouts/          # Pelican 1450 internal layout, Aux Box drawings
 │   ├── bom/                        # CSV BOMs by zone
 │   ├── reference_docs/             # Copy of EPAS18 PDFs, GEM service manual when obtained
 │   └── README.md                   # Pointer to this plan
 ├── Software/
 │   ├── firmware/
 │   │   ├── motion_teensy/          # PlatformIO project (EPAS18 CAN bridge)
 │   │   ├── pedals_teensy/          # PlatformIO project (throttle, brake, J1939, state)
 │   │   └── common/include/         # dbw_can_protocol.h, state_machine.h, j1939_pgns.h
 │   ├── autonomy_ws/                # ROS 2 Humble colcon workspace on Jetson
 │   │   └── src/
 │   │       ├── gem_bringup/        # top-level launches
 │   │       ├── gem_description/    # URDF (start from Cartagena's gem_e4.urdf.xacro)
 │   │       ├── gem_dbw_bridge/     # SocketCAN ↔ ROS2 bridge
 │   │       ├── gem_safety/         # safety supervisor on Orin NX
 │   │       ├── gem_perception/     # YOLO + SegFormer + LiDAR pipelines
 │   │       ├── gem_localization/   # robot_localization + ndt_scan_matcher config
 │   │       └── gem_autoware_config/# vehicle_info, sensor_kit, lanelet2 paths
 │   └── tools/                      # CAN sniffer scripts, calibration tools, dataset tools
 └── Sim/
     └── (see PART C — Cartagena workspace)

 B2. Firmware — Motion Teensy (steering)

 Toolchain: PlatformIO + Arduino-Teensy core. Libraries: FlexCAN_T4, WDT_T4.

 Main loop responsibilities:
 - 200 Hz: TX EPAS Msg #3 (ID 0x296) on EPAS bus with current map+torque demand.
 - 100 Hz: RX EPAS Msg #1 (0x290) and Msg #2 (0x292) → cache state.
 - Compute torque demand from steering angle command:
   - Goal: drive measured steering angle (from Msg #2 D0) toward commanded angle.
   - Outer loop on Motion Teensy: PI controller (angle error → torque demand).
   - Inner loop is closed inside the EPAS18 ECU itself (we don't tune motor PID).
 - Manual override detection: Msg #1 D6/D7 raw torque deviates from baseline by >threshold for >50 ms → set Msg #3 D0=0 → publish DRIVER_OVERRIDE fault on DBW bus → master state → DISENGAGED.
 - Watchdog: WDT_T4 at 50 ms; pet every loop. Jetson HB (DBW bus 0x100) lost >100 ms → set Msg #3 D0=0.
 - Heartbeat TX on DBW bus (0x150 @ 50ms).

 B3. Firmware — Pedals Teensy

 Three CAN domains:
 - CAN1 = DBW bus
 - CAN2 = J1939 vehicle bus (read-only via ISO1042 isolated transceiver)
 - CAN3 = unused or spare

 Main loop responsibilities:
 - 200 Hz: write throttle DAC pair (when state=ACTIVE & enable cmd=true & E-stop OK & brake not pressed).
 - 50 Hz: brake — kartech::send_brake_permil() on CAN3 (J1939 PGN 65280, 250 kbps). Continuous proportional position in band [POS_RELEASE_STOCK=3520 .. POS_FULL_BRAKE=3009].
 - 50 Hz: J1939 sniff, decode PGN 65265 (speed), 61445 (gear), 61444 (voltage) → publish on DBW bus as 0x160 VEHICLE_STATE.
 - 50 Hz: state machine evaluation — gates throttle/brake enable.
 - E-stop / brake pedal / wheel-touch monitoring on GPIO interrupts.
 - Heartbeat TX on DBW bus (0x151 @ 50ms).

 B4. Firmware — DBW CAN protocol (extended for new findings)

 500 kbps, 11-bit IDs, little-endian multi-byte fields.

 ┌───────┬───────────────────────────────┬─────────────────┬─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┬────────┐
 │  ID   │             Name              │    Direction    │                                                    Payload (8 B)                                                    │ Period │
 ├───────┼───────────────────────────────┼─────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼────────┤
 │ 0x100 │ JETSON_HEARTBEAT              │ Jetson → MCUs   │ u32 counter, u8 state, u8 reserved, u16 crc                                                                         │ 50 ms  │
 ├───────┼───────────────────────────────┼─────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼────────┤
 │ 0x110 │ STEER_CMD                     │ Jetson → Motion │ i16 angle_centideg, u16 max_rate_centideg_s, u8 enable, 3B reserved                                                 │ 20 ms  │
 ├───────┼───────────────────────────────┼─────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼────────┤
 │ 0x111 │ STEER_STATUS                  │ Motion → bus    │ i16 angle_centideg, i16 motor_current_mA, u8 fault_flags, u8 epas_state, u16 epas_error_code                        │ 20 ms  │
 ├───────┼───────────────────────────────┼─────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼────────┤
 │ 0x112 │ STEER_TORQUE_RAW              │ Motion → bus    │ u8 torque_a_raw, u8 torque_b_raw, u8 epas_status_flags, u8 epas_limit_flags, 4B reserved                            │ 20 ms  │
 ├───────┼───────────────────────────────┼─────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼────────┤
 │ 0x120 │ THROTTLE_CMD                  │ Jetson → Pedals │ u16 throttle_permil, u8 enable, 5B reserved                                                                         │ 20 ms  │
 ├───────┼───────────────────────────────┼─────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼────────┤
 │ 0x121 │ THROTTLE_STATUS               │ Pedals → bus    │ u16 dac1_mV, u16 dac2_mV, u8 relay_state, u8 fault_flags, 2B reserved                                               │ 20 ms  │
 ├───────┼───────────────────────────────┼─────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼────────┤
 │ 0x130 │ BRAKE_CMD                     │ Jetson → Pedals │ u16 brake_permil, u8 enable, 5B reserved                                                                            │ 20 ms  │
 ├───────┼───────────────────────────────┼─────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼────────┤
 │ 0x131 │ BRAKE_STATUS                  │ Pedals → bus    │ u16 actuator_pos_mm_x10, u16 actuator_current_mA, u8 fault_flags, 3B reserved                                       │ 20 ms  │
 ├───────┼───────────────────────────────┼─────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼────────┤
 │ 0x140 │ ESTOP_STATE                   │ Pedals → bus    │ u8 estop_loop, u8 brake_pedal, u8 wheel_torque_override, u8 dash_switch, u8 master_state, 3B reserved               │ 50 ms  │
 ├───────┼───────────────────────────────┼─────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼────────┤
 │ 0x150 │ MCU_HB_MOTION                 │ Motion → bus    │ u32 counter, u8 state, 3B reserved                                                                                  │ 50 ms  │
 ├───────┼───────────────────────────────┼─────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼────────┤
 │ 0x151 │ MCU_HB_PEDALS                 │ Pedals → bus    │ u32 counter, u8 state, 3B reserved                                                                                  │ 50 ms  │
 ├───────┼───────────────────────────────┼─────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼────────┤
 │ 0x160 │ VEHICLE_STATE (J1939 decoded) │ Pedals → bus    │ u16 speed_mph_x100, u8 gear (0=N, 1=F, 2=R, 3=Charging), u16 traction_voltage_x10, u8 j1939_link_state, 2B reserved │ 50 ms  │
 └───────┴───────────────────────────────┴─────────────────┴─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┴────────┘

 master_state: 0=DISENGAGED, 1=ARMED, 2=ACTIVE, 3=FAULT.
 fault_flags: bit0 overcurrent, bit1 encoder/sensor, bit2 plausibility, bit3 watchdog, bit4 range_limit, bit5 driver_override, bit6 hw_estop, bit7 epas_fault.

 B5. Firmware — state machine

   Power on
       │
       ▼
   ┌────────────┐    momentary ARM button + all preconditions OK
   │ DISENGAGED ├──────────────────────────────────────────┐
   └────┬───────┘                                          │
        │                                                  ▼
        │ any fault                              ┌──────────────┐
        │                                        │    ARMED     │
        │                                        └──┬───────────┘
        │                                           │ momentary ENGAGE button
        │                                           ▼
        │                                    ┌──────────────┐
        │              brake/wheel/estop ────┤   ACTIVE     │
        │              or HB lost            └──┬───────────┘
        │                                        │ any fault
        │                                        ▼
        │                                  ┌──────────────┐
        └────── key cycle ──────────────── │    FAULT     │ (sticky)
                                           └──────────────┘

 ARM preconditions: Jetson HB present, Motion+Pedals HB present, no EPAS error, brake pedal not pressed, wheel not touched, all subsystem fault_flags clear, key in ignition.
 ENGAGE preconditions: ARMED state + momentary ENGAGE button.

 B6. Autonomy stack (Jetson side)

 B6.1 OS / framework

 - JetPack 6.1 → Ubuntu 22.04 → ROS 2 Humble.
 - dustynv/jetson-containers for dev base. NVIDIA Isaac ROS containers for perception (NITROS zero-copy, isaac_ros_yolov8, isaac_ros_visual_slam, isaac_ros_image_pipeline). Freeze runtime image per phase.

 B6.2 Bridge node (gem_dbw_bridge)

 - Subscribes to /cmd_steering, /cmd_throttle, /cmd_brake (ackermann_msgs / std_msgs).
 - Publishes to /vehicle_state (custom msg: speed, gear, voltage, steering_angle, throttle, brake, master_state, fault flags).
 - Pumps Jetson HB at 50 Hz to DBW bus.
 - Translates STEER_CMD from radians to centi-degrees per the protocol.

 B6.3 Perception

 - 2D detection: YOLOv8m TensorRT FP16 via isaac_ros_yolov8.
 - Drivable surface: SegFormer-B0 TensorRT — pavement / sidewalk / grass / curb / crosswalk.
 - Stereo depth: ZED SDK neural depth on ZED 2i (cross-validate against LiDAR).
 - 3D detection: Autoware lidar_centerpoint on Livox Mid-360, 100 ms accumulation window.
 - Fusion: Autoware roi_cluster_fusion (LiDAR clusters projected into images, gated by YOLO).
 - Tracking: Autoware multi_object_tracker IMM with CV+CTRV models.
 - Free-space: Autoware probabilistic_occupancy_grid_map from LiDAR + depth.

 B6.4 Localization

 - Outer: robot_localization ekf_node fusing GPS-RTK (navsat_transform) + VN-100 IMU + J1939 vehicle speed (from VEHICLE_STATE topic). UTM frame.
 - Inner: Autoware ndt_scan_matcher against pre-built FAU campus PCD map. Sub-20 cm under tree cover.
 - Tertiary: Autoware yabloc (camera-based map matching).
 - GPS-denied fallback: NDT + IMU + speed dead-reckoning with watchdog.

 B6.5 Mapping

 - Drive in mapping mode → bag → LIO-SAM/FAST-LIO2 offline → PCD tiles.
 - Tier IV Vector Map Builder (web tool, free) → lanelet2 OSM file with drivable lanelets, crosswalks, stop signs, speed limits.

 B6.6 Planning + control

 - Phase 0–1: Nav2 with pure-pursuit follower (reuse Cartagena's pure_pursuit_node.py, adapted for real cart).
 - Phase 2+: migrate to Autoware Universe.
   - mission_planner (lanelet2 routing).
   - behavior_velocity_planner: crosswalk, stop_line, intersection, occlusion_spot, run_out modules.
   - obstacle_avoidance_planner + obstacle_stop_planner.
   - Lateral: pure pursuit Phase 2 → MPC lateral Phase 3.
   - Longitudinal: PID. Speed governor enforced both in firmware AND ROS param (defense in depth).

 B6.7 Safety supervisor (on Orin NX, separate from primary Jetson)

 - Independent ROS node, separate compute board, only shares the DBW CAN.
 - Watches all critical topics; cross-checks speed governor; on any anomaly issues controlled stop via DBW.
 - Cannot be restarted by primary Jetson. Independent watchdog.

 B6.8 HMI

 - Foxglove Studio on dash tablet over local wifi to AGX Orin.
 - Layout: state, speed cmd vs actual, planned path, detections w/ confidence, GPS fix type, Jetson temps, link health, last disengagement reason, EPAS error code (decoded from VEHICLE_STATE-adjacent topic), J1939 link health.
 - Software DISENGAGE button (latched) → safety supervisor → controlled stop.

 B6.9 Data pipeline

 - rosbag2 MCAP zstd to NVMe on every drive — free training data.
 - Nightly rsync to lab NAS over campus wifi when parked. ~200 GB/day.
 - Labeling: CVAT (self-host) for 2D, Xtreme1/SUSTechPOINTS for 3D.
 - Active learning: every safety-driver disengagement auto-exports 30 s before/after into "hard cases" bucket; weekly review.

 ---
 PART C — SIMULATION (build on Cartagena workspace)

 C1. Adopt Cartagena workspace verbatim as the base

 Copy Downloads/Cartagena_GEM_E4_workspace/ content into Golf Cart Code/Sim/. Already in place:
 - Podman + ROS 2 Humble container (Containerfile) AND Jazzy variant (Containerfile.jazzy).
 - launch_ros2.sh host launcher with Wayland/XWayland passthrough.
 - gem_e4.urdf.xacro from GEM-Illinois sim (already configured for the e4 chassis).
 - pure_pursuit ROS 2 package with sim launch (Gazebo Classic) and sim_harmonic launch (Gazebo Harmonic).
 - World-build pipeline: fetch_osm.py → tile_downloader.py → blosm_import.py → crop_mesh.py → merge_tiles.py → reanchor.py → build_world.sh.
 - regions.json with fau_breezeway region (East Engineering EE-96 → Wimberly Library, 26.3714–26.3734°N × −80.1046–−80.0976°W).
 - fau_breezeway.sdf world already built.

 C2. Extend world to full FAU Boca campus

 Tier the world build (don't try to do it all in one bite):

 ┌──────┬─────────────────────────────────────────────────────────────────────────────────────────────────┬─────────────────────────────────────────┬─────────────┬────────────────────┐
 │ Tier │                                             Region                                              │                  Bbox                   │ Approx area │   Mapping effort   │
 ├──────┼─────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────┼─────────────┼────────────────────┤
 │ T1   │ Existing Cartagena breezeway (EE-96 → Wimberly)                                                 │ 26.3714–26.3734°N × −80.1046–−80.0976°W │ ~0.04 km²   │ already done       │
 ├──────┼─────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────┼─────────────┼────────────────────┤
 │ T2   │ Academic core (EE complex, Engineering East/West, Library, Student Union, Breezeway, Owl Plaza) │ 26.370–26.376°N × −80.106–−80.097°W     │ ~0.6 km²    │ 1–2 mapping drives │
 ├──────┼─────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────┼─────────────┼────────────────────┤
 │ T3   │ Outer campus + parking lots (north to south & east edge)                                        │ 26.365–26.382°N × −80.110–−80.094°W     │ ~3.5 km²    │ 4–6 mapping drives │
 └──────┴─────────────────────────────────────────────────────────────────────────────────────────────────┴─────────────────────────────────────────┴─────────────┴────────────────────┘

 To extend: add a new entry to regions.json, run build_world.sh fau_full (or per tier). The OSM/Blender pipeline handles the rest. The lod5 setting + 512 max tiles is fine for T2; T3 may need to bump max_tiles or split into sub-regions.

 C3. Sim ↔ real parity (the highest-leverage move)

 Use the SAME lanelet2 map in sim and on the real cart. Build it once from a real LIO-SAM/FAST-LIO2 mapping pass + Tier IV Vector Map Builder, store at maps/fau_boca/lanelet2_map.osm. Both Cartagena sim and on-cart Autoware load this same file. What works in sim transfers directly.

 C4. Sim use cases per phase

 ┌───────┬──────────────────────────────────────────────────────────────────────────────────────────────────┐
 │ Phase │                                             Sim role                                             │
 ├───────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ P0    │ Pure-pursuit + DBW bridge dry-run before touching real cart.                                     │
 ├───────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ P1    │ Validate sensor TF tree & rosbag pipeline; train perception nets on synthetic data augmentation. │
 ├───────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ P2    │ Closed-loop waypoint following at 5 mph in sim before real-cart attempt.                         │
 ├───────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ P3    │ Inject simulated pedestrians on FAU breezeway world; tune behavior_velocity_planner.             │
 ├───────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ P4    │ Practice unmanned scenarios: stuck cart, GPS outage under tree cover, telecomm dropout.          │
 └───────┴──────────────────────────────────────────────────────────────────────────────────────────────────┘

 C5. Migration to Gazebo Harmonic (recommended)

 Cartagena ships both Classic and Harmonic Containerfiles. Gazebo Classic is EOL; prefer Harmonic for sustainability. The sim_harmonic.launch.py is the migration path.

 ---
 PART D — PHYSICAL BUILD ORDER (firmware + hardware milestones aligned)

 ┌───────┬─────────┬───────────────────────────────────────────────────────────────────────────────────────────────┬───────────────────────────────────────────────────┬─────────────────────────────────────────────────────────────────────────┬──────────────────────────────────────────────────────────────────────┐
 │ Phase │ Window  │                                      Hardware milestones                                      │                Firmware milestones                │                           Autonomy milestones                           │                              Demo gate                               │
 ├───────┼─────────┼───────────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────┤
 │ 0a    │ Wk 1–2  │ Audit cart: photograph traction controller, hand-test EPAS backdrive, verify pack voltage,    │ —                                                 │ —                                                                       │ Inventory complete; DCE firmware status known.                       │
 │       │         │ locate J1939 diag port. Contact DCE to confirm autonomous firmware.                           │                                                   │                                                                         │                                                                      │
 ├───────┼─────────┼───────────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────┤
 │ 0b    │ Wk 2–4  │ Build Pelican 1450 internals (compute box). Build 3 Aux Boxes. Run Channel R/D/S cables. Wire │ M1 comms backbone (both Teensies + CANable +      │ P0a Jetson + ROS 2 Humble bring-up.                                     │ Bench: kill loop drops Kilovac audibly; HB watchdog trips on Jetson  │
 │       │         │  E-stop loop.                                                                                 │ Jetson HB at 20 Hz).                              │                                                                         │ unplug.                                                              │
 ├───────┼─────────┼───────────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────┤
 │ 0c    │ Wk 4–6  │ Mount EPAS18 ECU; verify wiring vs DCE diagram; calibrate steering angle sensor + torque      │ M2 EPAS18 CAN bridge (TX 0x296, RX 0x290+0x292).  │ P0b joystick teleop via DBW bridge.                                     │ Cart wheels-off-ground: joystick steers wheel within ±0.5° of        │
 │       │         │ zero.                                                                                         │ M3 throttle DAC bench-tested.                     │                                                                         │ command; throttle ramp seen at the controller.                       │
 ├───────┼─────────┼───────────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────┤
 │ 0d    │ Wk 6–8  │ Wire J1939 sniffer tap (read-only ISO1042) to GEM diag port.                                  │ M4 J1939 sniff + VEHICLE_STATE @ 50 Hz.           │ P0c sensors all online + TF tree calibrated (LiDAR↔cams).               │ Foxglove shows live PGN-decoded speed/gear/voltage; perception @ ≥10 │
 │       │         │                                                                                               │                                                   │                                                                         │  Hz on bag.                                                          │
 ├───────┼─────────┼───────────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────┤
 │ 1     │ Mo 2–4  │ Closed-lot first-light at 3 mph, safety driver.                                               │ —                                                 │ P1 Mapping drive of T1 (breezeway) → LIO-SAM PCD + lanelet2. Perception │ 30 min joystick drive on lot, zero anomalies. T1 PCD repeatable <30  │
 │       │         │                                                                                               │                                                   │  fine-tuned on FAU dataset.                                             │ cm.                                                                  │
 ├───────┼─────────┼───────────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────┤
 │ 2     │ Mo 4–6  │ —                                                                                             │ —                                                 │ P2 EKF + NDT + Autoware mission_planner + pure-pursuit on T1 breezeway  │ 10 consecutive autonomous loops on T1, lateral err <50 cm, zero      │
 │       │         │                                                                                               │                                                   │ loop. Speed gov 5 mph.                                                  │ unintended disengagements.                                           │
 ├───────┼─────────┼───────────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────┤
 │ 3     │ Mo 6–9  │ —                                                                                             │ —                                                 │ P3 Full Autoware perception + behavior_velocity_planner. Expand to T2   │ 50+ scripted pedestrian encounters on T2 with zero near-miss. <1     │
 │       │         │                                                                                               │                                                   │ academic core. Mapping drives for T2.                                   │ disengage/km.                                                        │
 ├───────┼─────────┼───────────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────┤
 │ 4     │ Mo      │ M5 brake actuator + Bowden integration. M6 closed-loop emergency stop. M7 wireless E-stop.    │ M5–M7 firmware.                                   │ P4 Mapping drives for T3 (full Boca). Unmanned readiness.               │ T3 PCD complete. Unmanned point-A→B chase-observer demo. FAU Risk    │
 │       │ 9–12+   │ Phase 2 fail-engage parking brake.                                                            │                                                   │                                                                         │ Mgmt sign-off.                                                       │
 └───────┴─────────┴───────────────────────────────────────────────────────────────────────────────────────────────┴───────────────────────────────────────────────────┴─────────────────────────────────────────────────────────────────────────┴──────────────────────────────────────────────────────────────────────┘

 ---
 PART E — VERIFICATION

 Bench / unit:
 - DBW CAN protocol round-trip with cangen/cansniffer on a laptop CANable.
 - EPAS18 CAN bridge bench: power on EPAS standalone (no cart), Motion Teensy commands map=2 + slow torque sweep, scope torque commands and observe Msg #2 steering angle response.
 - Throttle DAC mirror: scope 0–100% sweep, error <50 mV vs recorded pedal map both channels.
 - J1939 sniffer: capture 10 min of GEM bus on lab bench (cart on stands, key on), decode all PGNs in PGN dictionary, verify speed/gear/voltage match dashboard.
 - E-stop: physically interrupt loop, Kilovac drops, all DBW enables drop within one HB period.

 Cart-jacked-up:
 - Throttle ramp 0→25%→0, observe wheel speed.
 - Steering sweep, EPAS Msg #2 steering angle matches command within 0.5°.
 - Manual override: while autonomy commands a setpoint, grab wheel — Motion Teensy must transition Msg #3 D0 to 0 within 50 ms (watch on logic analyzer).

 Closed-lot road test:
 - Square + figure-8 at 3 mph on T1 breezeway (or empty lot), joystick deadman.
 - E-stop at speed: cart coasts to safe stop, no DBW activity.
 - Watchdog test: kill Jetson at 3 mph, throttle ramps to 0 within 150 ms, EPAS reverts to local power-assist.

 Phase-gate criteria (pass before next phase):
 - P0→P1: 100% bench/jacked + 30 min joystick on closed lot, zero anomalies.
 - P1→P2: T1 PCD <30 cm repeatability, perception ≥10 Hz on bag playback.
 - P2→P3: 10 consecutive autonomous T1 loops, lateral err <50 cm.
 - P3→P4: 50+ ped encounters zero near-miss across T2.
 - P4→Unmanned: >10 hr per phase incident-free, FAU Risk Mgmt sign-off, wireless E-stop demonstrated, fail-engage parking brake proven, T3 mapping complete.

 ---
 PART F — INVENTORY CHECK FOR FAU MPCR LAB

 Before purchasing, ask the lab / neighboring labs / FAU surplus / Geomatics dept for any of these:

 Compute (huge value):
 - Jetson AGX Orin Dev Kit (32 or 64 GB)

 Cart-jacked-up:
 - Throttle ramp 0→25%→0, observe wheel speed.
 - Steering sweep, EPAS Msg #2 steering angle matches command within 0.5°.
 - Manual override: while autonomy commands a setpoint, grab wheel — Motion Teensy must transition Msg #3 D0 to 0 within 50 ms (watch on logic analyzer).

 Closed-lot road test:
 - Square + figure-8 at 3 mph on T1 breezeway (or empty lot), joystick deadman.
 - E-stop at speed: cart coasts to safe stop, no DBW activity.
 - Watchdog test: kill Jetson at 3 mph, throttle ramps to 0 within 150 ms, EPAS reverts to local power-assist.

 Phase-gate criteria (pass before next phase):
 - P0→P1: 100% bench/jacked + 30 min joystick on closed lot, zero anomalies.
 - P1→P2: T1 PCD <30 cm repeatability, perception ≥10 Hz on bag playback.
 - P2→P3: 10 consecutive autonomous T1 loops, lateral err <50 cm.
 - P3→P4: 50+ ped encounters zero near-miss across T2.
 - P4→Unmanned: >10 hr per phase incident-free, FAU Risk Mgmt sign-off, wireless E-stop demonstrated, fail-engage parking brake proven, T3 mapping complete.

 ---
 PART F — INVENTORY CHECK FOR FAU MPCR LAB

 Before purchasing, ask the lab / neighboring labs / FAU surplus / Geomatics dept for any of these:

 Compute (huge value):
 - Jetson AGX Orin Dev Kit (32 or 64 GB)
 - Jetson Orin NX 16GB module + carrier
 - Spare DRAM-cached NVMe SSDs ≥1 TB (not QLC)

 Sensors (huge value):
 - Any 3D LiDAR — Livox / Ouster / Velodyne / Hesai / Robosense (even retired Velodyne Puck)
 - Stereo cameras — ZED 2i / ZED X / ZED Mini / RealSense D455 / OAK-D Pro
 - GMSL camera kits + Hawk/Quartz GMSL carriers (rare, very valuable)
 - u-blox ZED-F9P / ZED-F9R / Septentrio AsteRx / Trimble GNSS receivers
 - Multiband GNSS antennas
 - VectorNav / Xsens / Microstrain / Lord IMUs

 DBW / firmware:
 - Teensy 4.1 (any qty)
 - CANable 2.0 / PCAN-USB / Kvaser Leaf
 - Deutsch DT crimp tooling
 - DCE EPAS Desktop Pro PC software — for EPAS calibration. May already be on a 2020 lab laptop.

 Safety / power:
 - Mushroom E-stops (any IEC 60947-5-1 NC)
 - Kilovac LEV200 / Gigavac / Albright contactors
 - LiFePO4 12V batteries ≥50 Ah
 - Mean Well / TDK-Lambda / Vicor isolated DC-DCs rated for the GEM pack voltage

 Documentation / access:
 - GEM E4 service manual / wiring diagram (Polaris dealer or FAU Facilities)
 - DCE EPAS18 Ultra autonomous firmware status — is it installed on the cart's ECU?
 - FAU Geomatics campus RTCM base station NTRIP credentials
 - FAU Risk Management contact + autonomous-vehicle precedent paperwork

 ---
 PART G — OPEN QUESTIONS (CRITICAL — gate Phase 0 work)

 1. DCE autonomous firmware on the EPAS18 ECU? Standard firmware does not respond to CAN Msg #3. If unknown, photograph the ECU's serial number (printed on case) and email sales@dcemotorsport.com. Without autonomous firmware, the steering plan stalls.
 2. GEM pack voltage — 48 V or 72 V? Determines DC-DC selection.
 3. GEM J1939 diag port location — where on the cart? (Probably under dash near OBD-II area.) Need this to wire the sniffer tap.
 4. Existing 3 working folders (Hardware/Software/Sim) — will be populated according to PART B.1.
 5. Is the cart hardtopped? Affects sensor mounting. If soft top, need to add a mast.
 6. Insurance / FAU Risk Mgmt status? Long pole. Start now, not in Phase 3.
 7. Wet-weather Phase 1? Drives enclosure IP rating priority.
 8. Power budget on existing GEM 12V house bus — does it have 200+ W of headroom for our compute, or does the new DC-DC need to come straight off the traction pack?
 9. 2020 team Excel design docs — should I extract the full BOMs from them and merge with PART A.16? (Currently only summarized.)

 ---
 Quick action list (ordered, what to do this week)

 1. Email DCE Motorsport (sales@dcemotorsport.com) about autonomous firmware status of your EPAS18 Ultra ECU. Send the ECU serial number.
 2. Probe the GEM throttle pedal Hall pair with a multimeter; record V1/V2 vs travel for both channels.
 3. Photograph the GEM traction controller under the seat (Sevcon Gen4 or Curtis 1238 — drives plausibility tuning).
 4. Hand-test EPAS backdrive (motor disconnected, can you turn the wheel?). Should be yes given the EPAS01 column has a clutch path; verify.
 5. Confirm pack voltage with a multimeter at the traction battery.
 6. Email FAU Geomatics about NTRIP campus base station availability.
 7. Email FAU Risk Mgmt about autonomous-vehicle research precedent.
 8. Take inventory of every item in PART F at MPCR lab and adjacent labs.
 9. In parallel: copy the Cartagena workspace into Sim/; bring up Gazebo Harmonic + pure_pursuit on a dev workstation; verify the FAU breezeway world loads.
 10. Sketch real-world cable runs on the actual cart with a tape measure to validate Channel R/D/S length estimates in PART A.14.
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌

 Claude has written up a plan and is ready to execute. Would you like to proceed?

 ❯ 1. Yes, and bypass permissions
   2. Yes, manually approve edits
   3. No, refine with Ultraplan on Claude Code on the web
   4. Tell Claude what to change
      shift+tab to approve with this feedback

 ctrl-g to edit in Vim · ~/.claude/plans/i-need-your-help-hashed-dongarra.md

- Throttle DAC mirror: scope 0–100% sweep, error <50 mV vs recorded pedal map both channels.
- J1939 sniffer: capture 10 min of GEM bus on lab bench (cart on stands, key on), decode all PGNs in PGN dictionary, verify speed/gear/voltage match dashboard.
- E-stop: physically interrupt loop, Kilovac drops, all DBW enables drop within one HB period.

**Cart-jacked-up:**
- Throttle ramp 0→25%→0, observe wheel speed.
- Steering sweep, EPAS Msg #2 steering angle matches command within 0.5°.
- Manual override: while autonomy commands a setpoint, grab wheel — Motion Teensy must transition Msg #3 D0 to 0 within 50 ms (watch on logic analyzer).

**Closed-lot road test:**
- Square + figure-8 at 3 mph on T1 breezeway (or empty lot), joystick deadman.
- E-stop at speed: cart coasts to safe stop, no DBW activity.
- Watchdog test: kill Jetson at 3 mph, throttle ramps to 0 within 150 ms, EPAS reverts to local power-assist.

**Phase-gate criteria** (pass before next phase):
- P0→P1: 100% bench/jacked + 30 min joystick on closed lot, zero anomalies.
- P1→P2: T1 PCD <30 cm repeatability, perception ≥10 Hz on bag playback.
- P2→P3: 10 consecutive autonomous T1 loops, lateral err <50 cm.
- P3→P4: 50+ ped encounters zero near-miss across T2.
- P4→Unmanned: >10 hr per phase incident-free, FAU Risk Mgmt sign-off, wireless E-stop demonstrated, fail-engage parking brake proven, T3 mapping complete.

---

# PART F — INVENTORY CHECK FOR FAU MPCR LAB

Before purchasing, ask the lab / neighboring labs / FAU surplus / Geomatics dept for any of these:

**Compute (huge value):**
- [ ] Jetson AGX Orin Dev Kit (32 or 64 GB)
- [ ] Jetson Orin NX 16GB module + carrier
- [ ] Spare DRAM-cached NVMe SSDs ≥1 TB (not QLC)

**Sensors (huge value):**
- [ ] Any 3D LiDAR — Livox / Ouster / Velodyne / Hesai / Robosense (even retired Velodyne Puck)
- [ ] Stereo cameras — ZED 2i / ZED X / ZED Mini / RealSense D455 / OAK-D Pro
- [ ] GMSL camera kits + Hawk/Quartz GMSL carriers (rare, very valuable)
- [ ] u-blox ZED-F9P / ZED-F9R / Septentrio AsteRx / Trimble GNSS receivers
- [ ] Multiband GNSS antennas
- [ ] VectorNav / Xsens / Microstrain / Lord IMUs

**DBW / firmware:**
- [ ] Teensy 4.1 (any qty)
- [ ] CANable 2.0 / PCAN-USB / Kvaser Leaf
- [ ] Deutsch DT crimp tooling
- [ ] **DCE EPAS Desktop Pro PC software** — for EPAS calibration. May already be on a 2020 lab laptop.

**Safety / power:**
- [ ] Mushroom E-stops (any IEC 60947-5-1 NC)
- [ ] Kilovac LEV200 / Gigavac / Albright contactors
- [ ] LiFePO4 12V batteries ≥50 Ah
- [ ] Mean Well / TDK-Lambda / Vicor isolated DC-DCs rated for the GEM pack voltage

**Documentation / access:**
- [ ] **GEM E4 service manual / wiring diagram** (Polaris dealer or FAU Facilities)
- [ ] **DCE EPAS18 Ultra autonomous firmware status** — is it installed on the cart's ECU?
- [ ] FAU Geomatics campus RTCM base station NTRIP credentials
- [ ] FAU Risk Management contact + autonomous-vehicle precedent paperwork

---

# PART G — OPEN QUESTIONS (CRITICAL — gate Phase 0 work)

1. **DCE autonomous firmware on the EPAS18 ECU?** Standard firmware does not respond to CAN Msg #3. If unknown, photograph the ECU's serial number (printed on case) and email `sales@dcemotorsport.com`. Without autonomous firmware, the steering plan stalls.
2. **GEM pack voltage** — 48 V or 72 V? Determines DC-DC selection.
3. **GEM J1939 diag port location** — where on the cart? (Probably under dash near OBD-II area.) Need this to wire the sniffer tap.
4. **Existing 3 working folders (Hardware/Software/Sim)** — will be populated according to PART B.1.
5. **Is the cart hardtopped?** Affects sensor mounting. If soft top, need to add a mast.
6. **Insurance / FAU Risk Mgmt status?** Long pole. Start now, not in Phase 3.
7. **Wet-weather Phase 1?** Drives enclosure IP rating priority.
8. **Power budget on existing GEM 12V house bus** — does it have 200+ W of headroom for our compute, or does the new DC-DC need to come straight off the traction pack?
9. **2020 team Excel design docs** — should I extract the full BOMs from them and merge with PART A.16? (Currently only summarized.)

---

# Quick action list (ordered, what to do this week)

1. Email DCE Motorsport (`sales@dcemotorsport.com`) about autonomous firmware status of your EPAS18 Ultra ECU. Send the ECU serial number.
2. Probe the GEM throttle pedal Hall pair with a multimeter; record V1/V2 vs travel for both channels.
3. Photograph the GEM traction controller under the seat (Sevcon Gen4 or Curtis 1238 — drives plausibility tuning).
4. Hand-test EPAS backdrive (motor disconnected, can you turn the wheel?). Should be yes given the EPAS01 column has a clutch path; verify.
5. Confirm pack voltage with a multimeter at the traction battery.
6. Email FAU Geomatics about NTRIP campus base station availability.
7. Email FAU Risk Mgmt about autonomous-vehicle research precedent.
8. Take inventory of every item in PART F at MPCR lab and adjacent labs.
9. In parallel: copy the Cartagena workspace into `Sim/`; bring up Gazebo Harmonic + pure_pursuit on a dev workstation; verify the FAU breezeway world loads.
10. Sketch real-world cable runs on the actual cart with a tape measure to validate Channel R/D/S length estimates in PART A.14.

