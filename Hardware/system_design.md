# System Design — Locked Spec

This is the locked component selection for the FAU MPCR GEM E4 self-driving build. **Buy off this list.** Anything found in FAU lab inventory replaces the corresponding line item — no architecture changes required.

Master plan: `~/.claude/plans/i-need-your-help-hashed-dongarra.md`. This doc is the procurement-ready summary.

---

## A. Compute

| Role | Pick | Mount | Interfaces | ROS topic / IP |
|---|---|---|---|---|
| Primary perception + planning | **NVIDIA Jetson AGX Orin 64GB Dev Kit** | Pelican 1450 in trunk | 12 V in (barrel), 10 GbE, USB-C ×4, M.2 NVMe slot | `192.168.10.10` |
| Safety supervisor + logging | **Jetson Orin NX 16GB** on Seeed reComputer J4012 carrier | Pelican 1450 in trunk | 12 V in, 1 GbE, USB-A | `192.168.10.11` |
| Storage A | **Samsung 990 Pro 2 TB NVMe** in AGX | — | M.2 PCIe Gen4 | — |
| Storage B | **Samsung 990 Pro 2 TB NVMe** in NX | — | M.2 PCIe Gen4 | — |
| Network | **Mikrotik CRS305-1G-4S+IN** (4× SFP+ 10 GbE + 1× GbE) | Pelican 1450 in trunk | SFP+ ×4, RJ-45 ×1 | switch |

## B. Sensors

### B.1 LiDAR
| Pick | Mount | Interface | ROS topic |
|---|---|---|---|
| **Livox Mid-360** (360° solid-state, 200 m, IP67) | Roof mast centerline, ~10 cm forward of cabin, level ±1° | Cat6 Ethernet (PoE-to-12V converter or separate 12V) | `/livox/lidar` (PointCloud2) |

### B.2 Cameras (7 total — surround perception)
| Position | Pick | Cable | Interface | ROS topic |
|---|---|---|---|---|
| Front stereo | **Stereolabs ZED 2i**, 4 mm lens, IP66 | USB-C 5 m active | USB 3.1 | `/zed2i/zed_node/{left,right}/image_rect_color`, `/zed2i/zed_node/depth/depth_registered` |
| Front auto-grade mono | **Leopard LI-IMX390-GMSL2** + Hawk dev kit | Fakra coax (white code) | GMSL2 → Hawk → CSI | `/front_cam/image_raw` |
| Front-left corner | **e-con e-CAM130_CUOAGX** (Sony IMX377, 120° FOV) | Fakra coax | GMSL2 | `/cam_fl/image_raw` |
| Front-right corner | e-CAM130_CUOAGX | Fakra coax | GMSL2 | `/cam_fr/image_raw` |
| Rear-left corner | e-CAM130_CUOAGX | Fakra coax | GMSL2 | `/cam_rl/image_raw` |
| Rear-right corner | e-CAM130_CUOAGX | Fakra coax | GMSL2 | `/cam_rr/image_raw` |
| Rear | **Stereolabs ZED Mini** | USB-C 3 m | USB 3.0 | `/zed_mini/zed_node/{left,right}/image_rect_color` |

### B.3 GNSS-RTK (dual antenna for moving-baseline heading)
| Pick | Mount | Interface | ROS topic |
|---|---|---|---|
| **2× ArduSimple simpleRTK2B + u-blox ZED-F9P** (rover + heading) | Pelican 1450 in trunk | USB to AGX Orin | `/gnss/fix` (NavSatFix), `/gnss/heading` (Imu yaw) |
| **2× u-blox ANN-MB-00** multiband antennas | Roof mast, ≥40 cm separation along longitudinal axis | SMA → bulkhead N-type → coax to trunk | — |
| Corrections | NTRIP via Florida FPRN (free, dense Boca coverage) | LTE / wifi | — |

### B.4 IMU
| Pick | Mount | Interface | ROS topic |
|---|---|---|---|
| **VectorNav VN-100** (industrial 9-DoF, internal EKF) | Trunk, near vehicle CG, mechanically isolated | RS-232 / USB | `/vn100/imu` (Imu), `/vn100/euler` |
| **Bosch BNO086** dev board (backup) | Chassis frame, redundant | I²C to Pedals Teensy → bridge | `/bno086/imu` |

### B.5 Vehicle telemetry (FREE — read-only J1939 sniff)
| Pick | Mount | Interface | ROS topic |
|---|---|---|---|
| **TI ISO1042 isolated CAN transceiver** + Pedals Teensy CAN2 | Pedals Aux Box | Tap GEM diag CAN port (location TBD) | `/vehicle_state` (custom msg: speed, gear, voltage) |

---

## C. Drive-by-Wire

### C.1 MCUs
| Pick | Lives in | Job |
|---|---|---|
| **Teensy 4.1** ×2 | "Motion Aux Box" on firewall (cabin) + "Pedals Aux Box" on firewall (above pedals) | Motion = EPAS18 CAN bridge. Pedals = throttle DAC + brake + state machine + J1939 sniffer. |
| TJA1051T/3 transceivers ×4 (one per CAN per Teensy) | Aux boxes | Standard automotive 3.3 V I/O CAN PHY |

### C.2 Steering (existing)
| Item | Status | Interface |
|---|---|---|
| **DCE Motorsport EPAS18 Ultra ECU** | Installed; bench-confirmed 2026-07-10, autonomous-firmware gate CLOSED (present & works — no purchase) | CAN 250 kbps, 11-bit IDs; msg IDs 0x290 (TX 100ms), 0x292 (TX 100ms), 0x298 (RX 5ms / 200Hz) |
| **DCE EPAS01 Column Assist** motor + integrated torque sensor + steering angle sensor | Installed | Wired to EPAS18 ECU via Autosport AS016-08 (power) + AS014-35 (signal) |

### C.3 Throttle bypass
| Item | Pick | Interface |
|---|---|---|
| DACs (mirrored pair) | 2× **MCP4725** I²C 12-bit | I²C to Pedals Teensy |
| Op-amp buffers | **MCP6002** dual rail-to-rail | — |
| Failsafe relay | **Omron G8HE-1A7T** DPDT auto, 12 V coil | Coil energized only in ACTIVE state |
| Pedal harness tap | T-junction into existing GEM Hall pair | Existing GEM connector (probably Molex MX150 — verify) |

### C.4 Brake (Phase 2 — actuator already procured from 2020 team)
| Item | Pick | Interface |
|---|---|---|
| Linear actuator | **Kartech 1A001HAJ** (J1939-controlled servo, integrated closed-loop) | 12 V power; CAN bus to Pedals Teensy CAN3 |
| Cable | Generic 36" Bowden cable kit | Pulls brake pedal arm; driver presses through |
| Driver | **Built into the actuator** — no external H-bridge needed | Kartech accepts position commands via J1939 PGN 65280 |
| CAN transceiver | SN65HVD230 (3.3 V) on Teensy CAN3 (pins 30/31) | 250 kbps, 29-bit J1939 IDs |
| Phase 4 fail-engage | 12 V solenoid-actuated parking brake | Hardwired to E-stop loop (power loss = brake on) |

---

## D. Safety hardware

| Item | Pick | Where |
|---|---|---|
| E-stop ×2 | **IDEC XA1E-BV4U02R** 22 mm mushroom NC | Dash + passenger side, NC contacts in series |
| Safety contactor | **TE Kilovac LEV200** (200 A, 12 V coil) | Under-driver-seat Safety Box |
| Wheel-touch sensor | **MPR121** cap-touch + copper foil under grip | Steering wheel rim |
| Wireless E-stop (Phase 4) | **Telecrane F24-8D** + safety-relay receiver | Receiver in trunk, antenna on roof mast |
| Status LEDs | 5× 22 mm illuminated indicators (ARMED, ACTIVE, FAULT, GPS-FIX, LINK-OK) | Dash console |

**Loop topology:** all E-stops + wireless RX safety contact in series, NC, drives Kilovac coil. Software is **never** in the drop path.

---

## E. Power

**Pack voltage TBD** (verify 48 V or 72 V before ordering DC-DC).

| Rail | Pick |
|---|---|
| Compute 12 V (200 W) | **Vicor DCM3623TD2K20T6E0xy** (36–75 V in, isolated) — for 72 V pack. **Mean Well RSDW20H-12** for 48 V. |
| Logic 12 V (15 W) | **TDK-Lambda PXC15-72WS12** (or 48 V variant) |
| UPS / surge buffer | **Battle Born BB1012** LiFePO4 12 V 100 Ah (Group 24) — separate battery box |
| 5 V rail | 2× **Pololu D24V50F5** (5 A buck) |
| Distribution | **Blue Sea 5025** 6-pos ATC fuse block + 100 A ANL master + 80 A ANL EPAS-dedicated |

---

## F. Enclosures and cooling

| Box | Pick | Contents |
|---|---|---|
| Main Compute Box | **Pelican 1450** (modified rear panel) + custom mounting plate | AGX Orin, NX, switch, DC-DCs, CANable, LTE modem, wireless E-stop RX |
| Cabin AC | **Adroit/EBM-Papst SLE-200** Peltier (12 V, 100–200 W cooling, IP54) | Mounted to Pelican lid |
| Internal fans | 2× **Noctua NF-A8 12V** | Recirculation, no external air ingress |
| Pressure equalization | **W. L. Gore PMF200** Gore-Tex vent (IP67) | Rear face of Pelican |
| Aux Battery Box | Custom aluminum or sealed plastic box, ventilated for LiFePO4 | Battle Born 100 Ah |
| Steering Aux Box | IP54 plastic enclosure ~150 × 100 × 60 mm | Motion Teensy + transceivers + 5 V buck |
| Pedals Aux Box | IP54 plastic enclosure ~150 × 100 × 60 mm | Pedals Teensy + DACs + op-amp + relay + J1939 transceiver |
| Under-Seat Safety Box | IP54 enclosure ~200 × 150 × 80 mm | Kilovac LEV200 + master fuse + E-stop loop relay |

**Heat budget (Florida summer):** ~125 W steady, 160 W peak in main compute box; Peltier AC keeps interior <40 °C with ambient 35 °C + sun load.

---

## G. Cabling (Channel R/D/S/ESP — see master plan PART A.14 for full schedule)

- **Channel R** (roof → trunk, 2.5–3 m): 12 cables in 1.5" split corrugated loom, through rear D-pillar grommet.
- **Channel D** (dash → trunk, 2–2.5 m): 5 cables along driver-side floor under sill trim.
- **Channel S** (steering/pedals → trunk, 1.5–2.5 m): 9 cables via center tunnel.
- **Channel ESP** (E-stop loop): all NC contacts in series → Kilovac coil.

**Connectors:** Deutsch DT04 series at every panel boundary. Crimp tooling required.

---

## H. ROS frame tree (TF) — names align with Cartagena URDF

```
map → odom → base_footprint → base_link
  base_link → lidar_link              (Livox Mid-360, atop roof mast)
  base_link → zed2i_camera_link       (front stereo)
  base_link → front_cam_link          (Leopard front mono)
  base_link → cam_fl_link             (front-left corner)
  base_link → cam_fr_link             (front-right corner)
  base_link → cam_rl_link             (rear-left corner)
  base_link → cam_rr_link             (rear-right corner)
  base_link → zed_mini_camera_link    (rear stereo)
  base_link → gnss_antenna1_link      (front GNSS antenna)
  base_link → gnss_antenna2_link      (rear GNSS antenna, ≥40 cm aft)
  base_link → imu_link                (VN-100)
```

Extrinsic calibration (LiDAR↔cameras, IMU↔base_link): perform once with the cart on a flat pad using Autoware's calibration tools. Save to `gem_description/config/extrinsics.yaml`.

---

## I. Procurement priority (in order)

1. **Confirm DCE autonomous firmware on EPAS18 ECU** (gating; possibly $$).
2. **Probe pack voltage** + locate J1939 diag port (no cost; required for power + sniffer design).
3. **Tier-1 buy:** Teensy 4.1 ×2, CANable 2.0, MCP4725 ×2, MCP6002, Omron G8HE relay, Deutsch DT crimp kit, Belden 9841, ISO1042. ~$250. **Lets firmware + sniffer development begin immediately.**
4. **Tier-2 buy:** AGX Orin Dev Kit + Orin NX + NVMe ×2 + switch + Cradlepoint LTE. ~$3,500. **Lets autonomy stack development begin.**
5. **Tier-3 buy:** Livox Mid-360 + ZED 2i + 4× e-CAM130 + ZED-F9P ×2 + ANN-MB-00 ×2 + VectorNav VN-100. ~$5,200. **Lets sensor integration begin.**
6. **Tier-4 buy:** ZED Mini + Leopard GMSL + Hawk dev kit. ~$1,150. **Last sensors.**
7. **Tier-5 buy:** Vicor DC-DC + LiFePO4 100 Ah + Pelican 1450 + Peltier AC + Aux Boxes + cabling. ~$1,800. **Physical packaging build.**
8. **Tier-6 (Phase 2):** Kartech 1A001HAJ already in inventory; only need Bowden cable + SN65HVD230 transceiver + parking-brake solenoid (Phase 4). ~$110.

Total: **~$12,200** (before contingency). Lab inventory hits should drop this 15–35%.

---

## J. Open hardware questions (must resolve before procurement)

1. DCE autonomous firmware status on EPAS18 ECU.
2. Pack voltage (48 V vs 72 V).
3. J1939 diag port location.
4. Hardtop fitted? (Affects roof mast strategy.)
5. Inventory check results from FAU MPCR + Geomatics (could remove huge line items).
