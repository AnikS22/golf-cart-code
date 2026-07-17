# Wiring Diagram — GEM E4 Self-Driving Conversion

The canonical wiring reference. Diagrams render on GitHub. Each section is a separate concern (data, power, safety) for clarity.

---

## 1. Data flow — sensors / autonomy / DBW / actuators

```mermaid
flowchart LR
  classDef sensor   fill:#1f3a8a,stroke:#0b1f4a,color:#fff
  classDef autonomy fill:#0f766e,stroke:#0b524d,color:#fff
  classDef mcu      fill:#000,stroke:#222,color:#fff
  classDef actuator fill:#b45309,stroke:#7c3a06,color:#fff
  classDef vehicle  fill:#7c3aed,stroke:#4c1d95,color:#fff
  classDef hmi      fill:#fbbf24,stroke:#92400e,color:#000

  Lidar[Livox Mid-360 LiDAR]:::sensor
  Cams["7× Cameras<br/>ZED 2i + Leopard + 4 corner + ZED Mini"]:::sensor
  GNSS[u-blox ZED-F9P × 2<br/>+ ANN-MB-00 antennas]:::sensor
  IMU[VectorNav VN-100]:::sensor

  Jetson[Jetson AGX Orin 64GB<br/>perception + planning + DBW bridge]:::autonomy
  Safety[Jetson Orin NX 16GB<br/>safety supervisor + logger]:::autonomy
  Foxglove[Foxglove HMI tablet<br/>ARM / ENGAGE / DISENGAGE buttons + status LEDs]:::hmi
  Gamepad[Logitech F710 gamepad]:::hmi

  MotionT[Motion Teensy 4.1<br/>EPAS18 CAN bridge + steering PI]:::mcu
  PedalsT[Pedals Teensy 4.1<br/>throttle/brake/state machine + J1939 sniffer]:::mcu

  EPAS[EPAS18 Ultra ECU<br/>+ EPAS01 column motor]:::actuator
  Throttle[2× MCP4725 DAC + MCP6002 op-amp + Omron G8HE DPDT relay<br/>→ GEM Hall pair → traction controller]:::actuator
  Brake[Phase 2: Kartech 1A001HAJ J1939 actuator + Bowden cable]:::actuator

  GEMCAN[GEM internal CAN bus<br/>J1939 @ 250 kbps READ-ONLY]:::vehicle

  Lidar  -->|Ethernet| Jetson
  Cams   -->|USB-C / GMSL| Jetson
  GNSS   -->|USB| Jetson
  IMU    -->|USB / RS-232| Jetson

  Jetson <-->|DBW CAN @ 500 kbps| MotionT
  Jetson <-->|DBW CAN @ 500 kbps| PedalsT
  MotionT <-->|EPAS bus 250 kbps| EPAS
  PedalsT -->|I²C + GPIO| Throttle
  PedalsT -.->|PWM Phase 2| Brake
  PedalsT <-.->|ISO1042 read-only| GEMCAN

  Gamepad -->|USB| Jetson
  Foxglove -->|Wi-Fi / GPIO| PedalsT

  Jetson <-->|local network| Safety
```

The DBW CAN bus is **the spine**: 500 kbps, twisted pair, 120 Ω termination at each end, Deutsch DT04-4P at every node. Three buses kept physically isolated for fault containment (DBW / EPAS / vehicle J1939) — see Master Plan PART A.6.

---

## 2. CAN bus topology — three isolated buses

```mermaid
flowchart TB
  subgraph DBW["DBW BUS — 500 kbps (our internal protocol)"]
    direction LR
    JCAN[Jetson can0<br/>via 40-pin GPIO + transceiver]
    MCAN1[Motion Teensy CAN1]
    PCAN1[Pedals Teensy CAN1]
    JCAN <-->|120Ω term| MCAN1
    MCAN1 <-->|120Ω term| PCAN1
  end

  subgraph EPAS["EPAS BUS — 250 kbps (DCE Motorsport internal)"]
    direction LR
    MCAN2[Motion Teensy CAN2]
    EPASECU[EPAS18 Ultra ECU<br/>signal conn pins 19/20 or 29/30]
    MCAN2 <-->|120Ω term| EPASECU
  end

  subgraph J1939["VEHICLE J1939 BUS — 250 kbps (READ-ONLY)"]
    direction LR
    GEMCAN[GEM internal CAN<br/>diagnostic port]
    ISO[ISO1042 isolator]
    PCAN2[Pedals Teensy CAN2]
    GEMCAN -->|do NOT TX| ISO
    ISO --> PCAN2
  end

  classDef dbw  fill:#dbeafe,stroke:#1e3a8a,color:#000
  classDef epas fill:#fed7aa,stroke:#9a3412,color:#000
  classDef j1939 fill:#fecaca,stroke:#991b1b,color:#000
  class JCAN,MCAN1,PCAN1 dbw
  class MCAN2,EPASECU epas
  class GEMCAN,ISO,PCAN2 j1939
```

- **Why three buses?** Single bus = single fault domain. A glitch on the J1939 vehicle CAN can never propagate into our DBW bus, can never propagate into the EPAS bus.
- **The Motion Teensy bridges DBW ↔ EPAS in firmware** (not physically). Adds ~10 ms latency, isolates safety-critical steering from everything else.
- **NEVER transmit on the J1939 bus.** It's read-only. Writing to it can brick the GEM traction controller.

---

## 3. Power one-line diagram

```mermaid
flowchart LR
  Pack[GEM Traction Pack<br/>48 V or 72 V — confirm before ordering DC-DC]:::pack
  GemDC[GEM original DC-DC<br/>→ 12 V house bus]:::existing
  Vicor[Vicor DCM3623<br/>200 W isolated]:::dcdc
  TDK[TDK-Lambda PXC15<br/>15 W logic-only]:::dcdc
  AuxBat[Battle Born BB1012<br/>LiFePO4 12 V 100 Ah UPS]:::battery
  AuxBus["12 V aux distribution<br/>Blue Sea 5025 fuse block"]:::bus

  Lights[Existing GEM accessories<br/>lights, horn, dash]:::existing
  Pelican[Main Compute Box loads<br/>AGX Orin / Orin NX / switch / LTE / Peltier AC]:::load
  AuxBoxes[Aux Boxes<br/>Steering / Pedals / Dash]:::load
  EPASmotor["EPAS18 motor<br/>~80 A transient peak<br/>(separate run! 4 AWG, own 80 A ANL fuse)"]:::epas

  Pack --> GemDC --> Lights
  Pack --> Vicor --> AuxBus
  Pack --> TDK --> AuxBus
  AuxBus <--> AuxBat
  AuxBus --> Pelican
  AuxBus --> AuxBoxes
  Pack -.->|"separate 4 AWG run<br/>direct to aux battery −,<br/>NOT through fuse block"| EPASmotor

  classDef pack    fill:#1f2937,stroke:#000,color:#fff
  classDef existing fill:#94a3b8,stroke:#334155,color:#000
  classDef dcdc    fill:#3b82f6,stroke:#1e3a8a,color:#fff
  classDef battery fill:#22c55e,stroke:#14532d,color:#fff
  classDef bus     fill:#0ea5e9,stroke:#0c4a6e,color:#fff
  classDef load    fill:#f59e0b,stroke:#78350f,color:#fff
  classDef epas    fill:#ef4444,stroke:#7f1d1d,color:#fff
```

**Critical wiring rules:**
- **Single-point star ground** at aux battery negative.
- **EPAS18 motor power** gets its own 4 AWG run direct to aux battery, NOT shared with logic ground (steering motor draws ~80 A transient — would brown out everything else).
- **CAN cable shields** drained at one end only (Jetson end), never both.
- Cable runs: 14 AWG for 12 V distribution, 22–24 AWG MIL-spec Tefzel (M22759) for signal.

### Aux 12 V fuse block layout (Blue Sea 5025, 6 fuses + spares)

| Fuse | Rating | Rail | Load |
|---|---|---|---|
| F1 | 20 A | 12 V → Jetson | AGX Orin (90 W peak via 19 V boost) |
| F2 | 10 A | 12 V → Jetson | Orin NX (25 W) |
| F3 |  5 A | 12 V → switch | Mikrotik 10 G switch (10 W) |
| F4 |  5 A | 12 V → modem | Cradlepoint LTE (8 W) |
| F5 |  3 A | 12 V → sensors | CANable, IMU, F9P (~6 W) |
| F6 | 10 A | 12 V → Steering Aux Box | Motion Teensy + ODrive logic + relay |
| F7 |  5 A | 12 V → Pedals Aux Box | Pedals Teensy + DACs + DPDT relay coil |
| F8 | 15 A | 12 V → brake actuator (Phase 2) | Kartech 1A001HAJ J1939 actuator |
| F9 | 10 A | 12 V → cabin AC | Peltier cabinet AC |
| F10 |  5 A | 12 V → dash | Status LEDs + dash buttons |

**Separate, in-line ANL fuse for EPAS18:** 80 A, 4 AWG run from aux battery + → Kilovac contactor → EPAS18 power pins A/B. **Not in the fuse block.**

---

## 4. Safety kill-chain — hardware-only path

```mermaid
flowchart LR
  Dash[Dash mushroom<br/>IDEC NC]:::estop
  Pass[Passenger mushroom<br/>IDEC NC]:::estop
  WirelessRX[Wireless RX safety contact<br/>Telecrane F24-8D]:::estop
  Loop["E-stop loop<br/>(all NC, in series)"]:::loop
  Kilovac[Kilovac LEV200 contactor<br/>200 A, 12 V coil]:::contactor
  Drops[Drops 12 V to:<br/>throttle relay coil<br/>EPAS18 power<br/>brake actuator]:::loads

  BrakePedal[Brake pedal pressed<br/>via PC817 optoiso]:::soft
  WheelTouch[Wheel-touch sensor<br/>MPR121 + foil]:::soft
  HBLoss["Jetson HB lost > 100 ms<br/>(MCU watchdog)"]:::soft

  Dash --> Loop
  Pass --> Loop
  WirelessRX --> Loop
  Loop -->|coil power| Kilovac
  Kilovac --> Drops

  BrakePedal -.->|software-mediated| Drops
  WheelTouch -.->|software-mediated| Drops
  HBLoss     -.->|software-mediated| Drops

  classDef estop     fill:#dc2626,stroke:#7f1d1d,color:#fff
  classDef loop      fill:#fbbf24,stroke:#78350f,color:#000
  classDef contactor fill:#f97316,stroke:#7c2d12,color:#fff
  classDef loads     fill:#1f2937,stroke:#000,color:#fff
  classDef soft      fill:#a855f7,stroke:#581c87,color:#fff
```

**The whole point**: **software is never in the kill path.** Open the loop → Kilovac drops physically → 12 V disappears from every actuator simultaneously, before any MCU can react.

The **soft** disengage paths (brake-pedal-pressed, wheel-touch, watchdog) are software-mediated and stop autonomy via the state machine, but if anything in software fails, the hardware loop is still there.

---

## 5. Per-zone cabling (the actual wires)

Cart is divided into **7 zones** connected by **3 cable channels**:

```mermaid
flowchart TB
  subgraph Roof["ROOF MAST + RACK"]
    direction LR
    R1[LiDAR]
    R2[7 cameras]
    R3[2× GNSS antennas]
    R4[LTE antenna]
  end

  subgraph WS["WINDSHIELD-TOP"]
    WSlot[ZED 2i + Leopard front cams]
  end

  subgraph Dash["DASH CONSOLE"]
    Dlot["HMI tablet<br/>ARM / ENGAGE / DISENGAGE buttons<br/>Status LEDs"]
  end

  subgraph Steer["STEERING COLUMN"]
    Slot["EPAS18 ECU<br/>Motion Teensy"]
  end

  subgraph Pedal["PEDAL AREA"]
    Plot["Pedals Aux Box<br/>(DAC + relay + brake actuator CAN Phase 2)"]
  end

  subgraph Seat["UNDER-DRIVER-SEAT"]
    Stlot["Kilovac LEV200<br/>E-stop loop<br/>master fuse"]
  end

  subgraph Trunk["REAR CARGO / TRUNK"]
    Tlot["Main Compute Box (Pelican 1450)<br/>Aux LiFePO4 100 Ah"]
  end

  Roof  -.->|"Channel R<br/>(headliner → rear D-pillar)"| Trunk
  WS    -.->|Channel R| Trunk
  Dash  -.->|"Channel D<br/>(driver-side floor under trim)"| Trunk
  Steer -.->|"Channel S<br/>(center tunnel)"| Trunk
  Pedal -.->|Channel S| Trunk
  Seat  -.->|Channel S| Trunk

  classDef zone fill:#0f766e,stroke:#0b524d,color:#fff
  class Roof,WS,Dash,Steer,Pedal,Seat,Trunk zone
```

| Channel | Path | Length | Cables |
|---|---|---|---|
| **R** | roof front-center → rear D-pillar → trunk | ~3 m | LiDAR Cat6+12V, ZED 2i USB-C, Leopard GMSL, 2× GNSS coax, LTE coax, wireless E-stop coax, GPS aux |
| **D** | dash → driver-side floor under sill trim → trunk | ~2.5 m | DBW CAN, dash button bundle, HMI tablet Cat6 |
| **S** | steering column / pedal area → center tunnel → under-seat → trunk | ~2 m | DBW CAN (Steering side), DBW CAN (Pedals side), EPAS power 4 AWG, J1939 tap, throttle harness tap, brake actuator (Phase 2) |

Use 1.5" split-corrugated loom on each channel; secure every 30 cm with adhesive zip-tie mounts; pass through grommeted holes only.

---

## 6. Jetson port assignments (right now, on the Yahboom Orin NX Super)

(Detailed port-by-port + boot sequence: `Hardware/JETSON_WIRING_DIAGRAM.md`. Quick map below.)

```
                         JETSON ORIN NX SUPER (Yahboom carrier)
       ┌─────────────────────────────────────────────────────────────────┐
       │                                                                 │
       │  ❶ USB-A 3.0 ◄── Logitech F710 receiver (gamepad → /joy)        │
       │  ❷ USB-A 3.0 ◄── (sensor / hub later)                           │
       │  ❸ USB-A 3.0 ◄── (sensor)                                       │
       │  ❹ USB-A 3.0 ◄── (sensor)                                       │
       │  ❺ Ethernet (eno1) ◄── LiDAR (Phase 1+) / dev internet          │
       │  ❻ USB-C ◄── currently Mac (USB-net + power); ZED 2i later      │
       │  ❼ HDMI ◄── optional monitor for direct GUI                     │
       │  ❽ DC barrel 19 V ◄── from cart 12 V via Pololu D24V50F19 buck  │
       │                                                                 │
       │  ❾ 40-pin GPIO header (top edge):                               │
       │      CAN_H ──► DBW bus → Motion + Pedals Teensies               │
       │      CAN_L ──► (twisted pair, 120 Ω term both ends)             │
       │                                                                 │
       └─────────────────────────────────────────────────────────────────┘
```

---

## 7. First-light minimum wiring (Phase 0c — RC drive at 3 mph)

The absolute minimum to drive the cart from the Jetson with a gamepad:

```mermaid
flowchart LR
  Game[Logitech F710<br/>USB receiver]:::hmi
  Jet[Jetson Orin NX<br/>gem_dbw_bridge<br/>+ gem_teleop]:::cpu
  MotT[Motion Teensy 4.1<br/>+ TJA1051T/3 transceiver]:::mcu
  PedT[Pedals Teensy 4.1<br/>+ TJA1051T/3 transceiver<br/>+ MCP4725 DAC × 2<br/>+ MCP6002 op-amp<br/>+ Omron G8HE relay]:::mcu
  EPAS[EPAS18 Ultra ECU<br/>+ EPAS01 column → wheels]:::actuator
  HallTap["GEM throttle Hall pair tap<br/>(splice in DPDT relay)"]:::actuator
  Pwr[Cart 12 V → Pololu D24V50F19<br/>→ Jetson DC barrel]:::pwr

  Game -->|USB-A ❶| Jet
  Jet -->|"40-pin CAN_H/L ❾<br/>500 kbps, 120 Ω term"| MotT
  Jet -->|same DBW bus| PedT
  MotT -->|EPAS bus<br/>250 kbps| EPAS
  PedT -->|2× analog Hall voltages<br/>via DPDT relay| HallTap
  Pwr  --> Jet

  classDef hmi fill:#fbbf24,stroke:#92400e,color:#000
  classDef cpu fill:#0f766e,stroke:#0b524d,color:#fff
  classDef mcu fill:#000,stroke:#222,color:#fff
  classDef actuator fill:#b45309,stroke:#7c3a06,color:#fff
  classDef pwr fill:#22c55e,stroke:#14532d,color:#fff
```

That's six physical things to wire up. No sensors, no perception, no autonomy stack — just **gamepad → Jetson → CAN → Teensies → cart actuators**. Brake = your foot until Phase 2.

---

## See also

- `JETSON_WIRING_DIAGRAM.md` — port-by-port for the Yahboom carrier specifically
- `JETSON_PLUG_LAYOUT.md` — earlier deeper layout notes
- `system_design.md` — locked component selection + procurement priority
- `cart_parameters.md` — vehicle geometry + sensor extrinsics
- `CART_VISIT_DAY1.md` — checklist for the cart inspection
- Master plan PDF — for the canonical system architecture overview
