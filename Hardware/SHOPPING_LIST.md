# Shopping List — GEM E4 Self-Driving Build

Grouped by tier. Buy each tier in order; each unlocks the next milestone.

Vendors: **Amazon** where the part is sold there reliably, **direct** where it's specialty (DigiKey, manufacturer, ArduSimple, Stereolabs, etc.). Don't substitute Amazon knockoffs for the safety-critical parts (E-stops, contactor, CAN transceivers) — buy genuine.

---

## Tier 1 — Firmware bench (BUY NOW, ~$300)

This tier unlocks **bench-bringup of the two Teensies + CAN bus** before they go on the cart. Nothing here is on the critical path of the cart visit; you can develop in parallel with whatever the cart inspection turns up.

| # | Item | Qty | Vendor | Search term / link | ~$ ea | $ |
|---|---|---|---|---|---|---|
| 1 | Teensy 4.1 (no headers) | 2 | Amazon | "PJRC Teensy 4.1" | 32 | 64 |
| 2 | CANable 2.0 USB-to-CAN dongle | 1 | Amazon | "CANable 2.0 candleLight" | 45 | 45 |
| 3 | TJA1051T/3 CAN transceiver breakout | 4 | Amazon | "TJA1051T/3 module" (4-pack) | 4 | 16 |
| 4 | Adafruit MCP4725 DAC breakout | 2 | Amazon | "Adafruit MCP4725 12-bit DAC" | 7 | 14 |
| 5 | MCP6002 op-amp (DIP-8, 5-pack) | 1 | Amazon | "MCP6002 op-amp DIP" | 6 | 6 |
| 6 | Omron G8HE-1A7T DPDT auto relay | 2 | Mouser / DigiKey | Mouser part `653-G8HE-1A7T-DC12` | 7 | 14 |
| 7 | TI ISO1042 isolated CAN transceiver (breakout) | 1 | DigiKey | DigiKey `296-ISO1042BDWVR-ND` + breakout PCB OR Amazon "ISO1042 breakout" | 12 | 12 |
| 8 | PC817 optoisolator (10-pack) | 1 | Amazon | "PC817 optoisolator DIP 10pcs" | 5 | 5 |
| 9 | Adafruit MPR121 cap-touch breakout | 1 | Amazon | "Adafruit MPR121 capacitive touch" | 8 | 8 |
| 10 | Logitech F710 gamepad | 1 | Amazon | "Logitech F710 wireless gamepad" | 35 | 35 |
| 11 | Belden 9841 1-pair shielded 24AWG (25 ft) | 1 | Amazon | "Belden 9841 25ft" | 28 | 28 |
| 12 | Deutsch DT04-4P connector kit + crimper | 1 | Amazon | "Deutsch DT connector kit crimp tool" | 45 | 45 |
| 13 | Half-size breadboard + jumper wires + header pins | 1 | Amazon | "breadboard jumper wire kit" | 15 | 15 |
| 14 | 120 Ω ¼ W resistor (10-pack) for CAN termination | 1 | Amazon | "120 ohm 1/4W resistor 10pcs" | 3 | 3 |
| | | | | | **Tier 1 subtotal** | **~$310** |

### What it enables
- Bench-flash both Teensy firmwares
- Verify CAN bus with `candump` / `cangen`
- Verify DAC outputs into a scope
- Verify state machine via dash-button-equivalents on bench
- Verify gamepad → ROS → CAN end-to-end **with the Jetson you already have**

---

## Tier 2 — Power, safety, enclosures (~$450)

Buy alongside Tier 1 once you confirm pack voltage (48 V vs 72 V) from the cart inspection.

### Power

| # | Item | Qty | Vendor | Search / link | ~$ |
|---|---|---|---|---|---|
| 15 | Pololu D24V50F19 (12 V→19 V, 50 W) — for Jetson barrel | 1 | Pololu direct (pololu.com #2580) | — | 30 |
| 16 | Pololu D24V50F5 (any-in → 5 V, 5 A) | 2 | Pololu direct (#2851) | — | 30 |
| 17 | Vicor DCM3623 200 W DC-DC (72 V → 12 V) ⚠ **only if pack is 72 V** | 1 | DigiKey `1102-DCM3623TD2K17E0M70-ND` | — | 85 |
| 17b | Mean Well RSDW20H-12 (24/48→12 V) ⚠ **only if pack is 48 V** | 1 | DigiKey | — | 30 |
| 18 | Battle Born BB1012 100 Ah LiFePO4 (UPS aux) | 1 | Battle Born direct | battleborn.com | 900 |
| 18b | **Cheaper alt:** Renogy 12 V 100 Ah LiFePO4 | 1 | Amazon | "Renogy 100Ah LiFePO4" | 400 |
| 19 | Blue Sea 5025 6-pos ATC fuse block | 1 | Amazon | "Blue Sea 5025 fuse block" | 20 |
| 20 | ANL fuse holder + 100 A fuse | 1 | Amazon | "ANL fuse holder 100A" | 25 |
| 21 | ANL fuse 80 A (for EPAS18) | 2 | Amazon | "ANL fuse 80A" | 15 |
| 22 | ATC fuse assortment (3–30 A) | 1 | Amazon | "ATC fuse assortment kit" | 12 |
| 23 | 4 AWG silicone wire — 10 ft red, 10 ft black | 1 set | Amazon | "4 AWG silicone wire 10ft" | 35 |
| 24 | 14 AWG marine tinned wire — red+black 25 ft each | 1 set | Amazon | "14 AWG marine wire tinned" | 20 |
| 25 | 22 AWG MIL-spec hookup wire (Tefzel, M22759) | 1 spool | Amazon / DigiKey | "M22759 22 AWG" | 25 |
| 26 | M8 ring terminals + lugs assortment | 1 set | Amazon | "battery cable lugs 4AWG 8AWG" | 15 |
| 27 | Heat-shrink tubing assortment | 1 set | Amazon | "heat shrink tubing kit" | 12 |

### Safety (MANDATORY day-one, don't skip)

| # | Item | Qty | Vendor | Search / link | ~$ |
|---|---|---|---|---|---|
| 28 | IDEC XA1E-BV4U02R mushroom E-stop NC | 2 | DigiKey | DigiKey `966-1538-ND` (or Amazon "IDEC XA1E mushroom NC") | 25 |
| 29 | TE Kilovac LEV200 200 A safety contactor (12 V coil) | 1 | DigiKey | DigiKey `LEV200A4ANG-ND` | 95 |
| 30 | 22 mm illuminated momentary buttons (ARM/ENGAGE/DISENG) | 3 | Amazon | "22mm illuminated momentary push button" | 10 |
| 31 | 22 mm LED indicators (red/green/blue) | 5 | Amazon | "22mm LED indicator 12V" | 5 |

| | | | | **Tier 2 subtotal (72 V pack + Battle Born)** | **~$1,500** |
| | | | | **Tier 2 subtotal (48 V pack + Renogy alt)** | **~$950** |

---

## Tier 3 — Sensors (~$5,200 — after firmware works)

Don't buy until Tier 1 firmware milestone passes (RC first-light). Lab inventory check (`Hardware/system_design.md` PART F) might cover some of these.

| # | Item | Qty | Vendor | Search / link | ~$ |
|---|---|---|---|---|---|
| 32 | Livox Mid-360 360° LiDAR | 1 | Livox direct | livoxtech.com | 1,400 |
| 33 | Stereolabs ZED 2i (4 mm lens, IP66) | 1 | Stereolabs direct | stereolabs.com | 500 |
| 34 | e-con Systems e-CAM130_CUOAGX corner cam (GMSL) | 4 | e-con Systems direct | e-consystems.com | 250 |
| 35 | ArduSimple simpleRTK2B with u-blox ZED-F9P | 2 | ArduSimple direct | ardusimple.com | 300 |
| 36 | u-blox ANN-MB-00 multiband GNSS antenna (magnetic) | 2 | Mouser / DigiKey | u-blox `ANN-MB-00-00` | 80 |
| 37 | VectorNav VN-100 industrial 9-DoF IMU | 1 | VectorNav direct | vectornav.com | 800 |
| 38 | Bosch BNO086 dev board (backup IMU) | 1 | Adafruit / Amazon | "Adafruit BNO086" | 25 |
| 39 | Stereolabs ZED Mini (rear cam) | 1 | Stereolabs direct | stereolabs.com | 450 |
| | | | | **Tier 3 subtotal** | **~$5,200** |

### GMSL note (might not fit your current Yahboom carrier)
The 4× e-CAM130 corner cams use GMSL2 over Fakra coax. **The Yahboom Orin NX Super you have does not have FAKRA GMSL connectors.** Either:
- Skip the GMSL cams, substitute with **Arducam IMX477 USB3 cams** (~$80 each) on a powered USB hub, or
- Add an **AGX Orin Dev Kit + Hawk GMSL carrier** (master plan calls for AGX Orin as primary anyway)

---

## Tier 4 — Enclosures + cooling (~$350)

Buy when you start physically mounting things in the cart.

| # | Item | Qty | Vendor | Search / link | ~$ |
|---|---|---|---|---|---|
| 40 | Pelican 1450 protective case | 1 | Amazon | "Pelican 1450" | 195 |
| 41 | IP54 plastic enclosure 150×100×60mm (Aux Boxes) | 3 | Amazon | "IP65 junction box 150x100x60" | 12 |
| 42 | Adroit/EBM-Papst SLE-200 Peltier cabinet AC, 12 V | 1 | eBay / TECA direct | "Adroit SLE-200 thermoelectric AC" | 200 |
| 43 | Noctua NF-A8 12 V 80 mm fan | 2 | Amazon | "Noctua NF-A8" | 18 |
| 44 | Gore PMF200 IP67 Gore-Tex vent | 2 | Mouser | Gore `PMF200322` | 5 |
| 45 | Cable glands assortment (PG7/PG9/PG11) | 1 set | Amazon | "cable gland kit IP68" | 15 |
| 46 | Misumi HFS5-2020 aluminum extrusion (1 m × 4) for sensor mast | 4 | misumi-ec.com | HFS5-2020 | 30 |
| | | | | **Tier 4 subtotal** | **~$350** |

---

## Tier 5 — Brake actuator (Phase 2, ~$250 — buy after Week 9)

Don't buy until first-light RC drive milestone passes. Safety driver brakes with foot until then.

| # | Item | Qty | Vendor | Search / link | ~$ |
|---|---|---|---|---|---|
| 47 | Progressive Automations PA-14P-4-150 linear actuator | 1 | Progressive Auto direct | progressiveautomations.com | 180 |
| 48 | Bowden cable kit (36" inner cable + housing + ends) | 1 | Amazon | "Bowden cable kit 36 inch" | 25 |
| 49 | BTS7960 (IBT-2) 43 A H-bridge motor driver | 1 | Amazon | "BTS7960 IBT-2 motor driver" | 12 |
| 50 | 12 V solenoid-actuated parking-brake mechanism (Phase 4) | 1 | TBD spec later | — | 80 |
| | | | | **Tier 5 subtotal** | **~$300** |

---

## What you DON'T need to buy

- **Jetson Orin NX** — you already have the Yahboom one. Eventually you'll want an **AGX Orin 64GB Dev Kit** ($2,000) for primary perception (Phase 2+) but defer.
- **Teensy headers** — Teensy 4.1 comes solderable.
- **CAN crimp pins** — included with the Deutsch kit.
- **DCE EPAS18 ECU** — already installed on the cart.

---

## Grand total by phase

| Phase | What | Total |
|---|---|---|
| Phase 0 firmware bench | Tier 1 | **$310** |
| Phase 0 + 1 power + safety | Tier 2 (Renogy alt) | **$950** |
| Phase 1 sensors | Tier 3 | **$5,200** |
| Phase 1 enclosures + cooling | Tier 4 | **$350** |
| Phase 2 brake | Tier 5 | **$300** |
| | **Project total** | **~$7,100** |

If FAU has any of these in lab inventory (see `Hardware/system_design.md` PART F — inventory check) the bill drops fast — IMUs, antennas, e-stops, even a spare Pelican case often live in robotics-lab closets.

---

## Recommended buy order (this week)

1. **Today:** Tier 1 (~$310). One Amazon order, plus a Mouser/DigiKey order for the safety-critical parts (Kilovac LEV200, IDEC E-stops, Vicor DC-DC).
2. **This week:** confirm pack voltage from cart inspection → finalize Tier 2 DC-DC choice → place that order.
3. **Mid-bench:** order Tier 4 enclosures + cabling so they're on hand when Tier 1 firmware is bench-validated.
4. **Phase 1 (Week 4+):** Tier 3 sensors, after RC first-light works.
5. **Phase 2 (Week 9+):** Tier 5 brake.

---

## Order tracking (fill in as you buy)

| Tier | Order date | Vendor | Order # | ETA | Received |
|---|---|---|---|---|---|
| Tier 1 | | | | | |
| Tier 2 | | | | | |
| | | | | | |
