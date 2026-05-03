---
name: EPAS18 Ultra ECU — autonomous CAN interface
description: Reference for the DCE Motorsport EPAS18 Ultra ECU installed on the GEM E4 — pinout, autonomous CAN protocol (msg IDs 0x290/0x292/0x296), manual override detection, and gating constraints.
type: reference
originSessionId: 991af12c-3dcb-47ba-b9d1-a501769a1f69
---
The 2018 GEM E4 cart at FAU MPCR has a **DCE Motorsport EPAS18 Ultra ECU** driving the steering column (NOT a generic worm-gear motor as initially assumed). DCE Motorsport, Maldon, Essex, UK — www.dcemotorsport.com — sales@dcemotorsport.com — +44 (0)1621 856451.

**System: EPAS18 Ultra ECU + EPAS01 Column Assist (or OEM GM Opel Corsa / Holden Barina MKB&C column).** Internal closed-loop steering controller, integrated torque sensor, separate steering angle sensor (0–5V analog to ECU pin 3). 80 A peak, 13.8 V nominal, 1.05 kg, 175×136×42 mm.

## Connectors
- **High Power: ECU AS016-08PN ↔ Mating AS616-08SN.** A,B = +12V via 80A fuse. C,D = ground. E,F = motor +12V out. G,H = motor 0V out.
- **Signal: ECU AS014-35PN ↔ Mating AS614-35SN.** Pin 1 = switched +12V (1A); 2 = ground; 3 = steering angle 0–5V in; 14/15 = sensor 0V/+5V; 16/17/18 = RS232 Tx/Rx/0V; 19/29 = CAN Hi (linked); 20/30 = CAN Lo (linked); 23/24/25/26 = Torque A/B/0V/+5V; 27 = fault lamp out; 28 = map switch sig in.

## CAN bus
- **Standard mode: 1 Mbit/s, 11-bit IDs** (for monitoring + map switch via PC tool "EPAS Desktop Pro").
- **Autonomous mode: 500 kb/s, 11-bit IDs** (matches our DBW bus rate). Other rates available "by request" from DCE.

## Transmitted by ECU (TX, ECU → bus)
**CAN Message #1 — default ID 0x290, 100 ms period:**
- D0: Torque (bits, processed)
- D1: Motor duty (%)
- D2: Current (A)
- D3: Supply voltage (1 bit = 100 mV)
- D4: Switch position (0–15)
- D5: Box temperature (°C)
- D6: **Torque A raw (bits)** — MONITOR THIS for manual override
- D7: **Torque B raw (bits)** — MONITOR THIS for manual override

**CAN Message #2 — default ID 0x292, 100 ms period:**
- D0: Steering angle (bits)
- D1/D2: Analog channels #1/#2 (bits)
- D3: Selected map (0–5)
- D4: Error code (100=low V, 101=torque sensor not connected, 102=torque sensor fault, 103=current sensor fault, 104=motor power fault, 105=motor not connected, 106=motor stalled/shorted, 107/108=clutch — N/A on EPAS01, 109=overcurrent, 110=overtemp, 111=internal)
- D5: Digital I/O bitfield
- D6: Status flags — b0 program paused / b1 motor fwd / b2 motor rev / b3 **host mode active** / b4 fault light / b5–b7 reserved
- D7: Limit flags — b0 LH stop / b1 RH stop / b2 over-temp / b3–b6 unused / b7 **remote mode active**

## Received by ECU (RX, bus → ECU; AUTONOMOUS FIRMWARE ONLY)
**CAN Message #3 — FIXED ID 0x296, must transmit at 50–200 Hz (5 ms ideal). 200 ms timeout → ECU auto-reverts to local mode.**
- D0: Steering map. **0 = local mode (use physical torque sensor + map switch).** 1–5 = autonomous map (higher = faster motor response).
- D1: Torque A demand (signed-style, 128 = zero, range 64–192 i.e. ±64 from center).
- D2: Torque B demand. **D1 + D2 MUST equal 255** (mirror).
- D3–D7: Not used.

## Worked example (turn right slowly)
Map = 1 (or 2/3/4/5 for faster response), Torque A = 143, Torque B = 112 (sum = 255, A is +15 from center → demand right turn). Larger spread = stronger motor demand.

## Manual override (mandatory pattern)
Monitor torque A/B raw values in CAN Msg #1 D6/D7. **During remote operation these stay fairly static.** Driver grabbing the wheel causes a spike — when detected, immediately set CAN Msg #3 D0 = 0 (local mode, drop autonomous control). The EPS continues providing normal power assist to the driver.

## Configuration
PC tool: "EPAS Desktop Pro" via RS232 (pins 16/17/18). Also configurable: torque deadband (default 4 bits), torque zero (default 128 bits — must be calibrated with no driver torque applied: power on/off three times; flashing fault LED on 4th cycle = calibration), LH/RH steering stop positions (bits, from steering angle sensor), CAN msg ID #1 (default 0x290), CAN msg ID #2 (default 0x292), 5 user-programmable steering maps (16-point torque→duty curves).

## Critical constraints
1. **Autonomous firmware is sold separately by DCE** — the standard EPAS18 firmware does NOT accept CAN Msg #3. Confirm whether the cart's ECU has been flashed with the autonomous variant; if not, contact sales@dcemotorsport.com.
2. **Wrong wiring polarity DAMAGES the ECU** — the manual is explicit: "FAILURE TO CORRECTLY CONNECT VEHICLE POWER SUPPLY WILL DAMAGE THE CONTROL UNIT."
3. **Welding on the chassis with ECU connected can destroy it** — disconnect both Autosport plugs and remove the battery before any welding work near the cart.
4. **No CAN termination resistor inside the ECU** — termination must be added externally on the bus (120 Ω at each end).
5. **Steering angle sensor calibration** is a stored procedure (turn fully one way, note bits, set LH/RH stop params; LH must be lower than RH or sensor wires need swapping). Required to enable end-stop motor cutout.
