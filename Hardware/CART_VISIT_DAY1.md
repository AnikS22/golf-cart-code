# Cart Visit — Day 1 Checklist (2026-05-04)

**Bring:** multimeter, phone (camera + ruler app), tape measure (≥10 ft), notepad, this checklist printed.

**You will NOT be testing autonomy / firmware / RC** — none of the firmware is written and no Teensies are bought yet. Tomorrow is **information gathering** to unblock procurement and unblock writing the firmware. Everything below is a question whose answer changes what you order or how you write the code.

---

## CRITICAL — must be done (gates everything else)

### 1. EPAS18 Ultra ECU — find it, photograph the label
- [ ] Locate the EPAS18 ECU box (DCE Motorsport, black aluminum, ~175×136×42 mm, 2 round Autosport plugs on one face). Probably mounted in the cabin / firewall near the steering column.
- [ ] **Photograph the case label/serial number** — this is what we email to DCE.
- [ ] Note any visible firmware version sticker or LED status.

### 2. EPAS — hand-test backdrive
- [ ] **With the cart powered OFF**, try to turn the steering wheel by hand.
  - **Smooth?** Backdriveable → manual override is possible → keep the EPAS18.
  - **Stuck or super stiff?** Worm gear is non-backdriveable → driver can't override autonomy → we have to add a clutch OR replace the motor (big project change).
- [ ] Note approximate handwheel rotation lock-to-lock (in turns or degrees).

### 3. Pack voltage
- [ ] Multimeter on traction battery terminals: **measure DC voltage**. Should be 48 V or 72 V (probably 72 V on a 2018 e4 LSV trim).
- [ ] Note the pack chemistry if labeled (lead-acid vs LiFePO4) — affects DC-DC sizing and charging.

### 4. Throttle pedal — probe Hall pair
- [ ] Locate the throttle pedal connector (where the pedal plugs into the harness).
- [ ] **Key on, foot OFF the pedal**: measure DC voltage on each pin to ground. Identify the two Hall outputs (typical: ~0.8 V and ~4.2 V at rest).
- [ ] **Slowly press pedal 0 → 100% in ~5 seconds**: verbally call out V1 and V2 voltages at 0%, 25%, 50%, 75%, 100%. Have a phone audio-record this.
- [ ] Note the connector body shape (Molex MX150 / TE / Deutsch?) — needed to source mating connectors.

### 5. J1939 diagnostic CAN port
- [ ] Locate the GEM service-port connector (likely under the dash near the OBD-II area, or under the seat).
- [ ] **Photograph it** with pin numbers visible if molded.
- [ ] Note any labeling ("DIAG", "CAN", "OBD").

### 6. Traction controller
- [ ] Lift the driver's seat. Locate the traction controller (large finned aluminum heatsink + connectors).
- [ ] **Photograph the label** — we need to know if it's **Sevcon Gen4** or **Curtis 1238** (different throttle plausibility behavior).

---

## IMPORTANT — do these if time allows

### 7. Brake pedal area
- [ ] Photograph the brake pedal lever and its mechanical environment (firewall, master cylinder).
- [ ] Identify the brake light switch wiring (probably 2 wires near the pedal arm).
- [ ] **Multimeter** on the brake light switch: pedal up vs pedal pressed — is it switched-12V or switched-ground?

### 8. 12 V house bus headroom
- [ ] Locate the existing GEM 12 V house battery (smaller battery, probably under hood / under seat).
- [ ] Find the existing DC-DC (steps traction pack down to 12 V). Photograph its label/rating.
- [ ] Estimate available headroom: total rated wattage minus what's already drawn (lights, horn, fans, accessory).

### 9. Roof / hardtop / mast options
- [ ] Hardtop fitted? Photograph from front, side, rear.
- [ ] Existing roof rack or rails? Mounting surface flat enough for sensor mast?
- [ ] If no hardtop: where could a sensor mast attach to the frame?

### 10. Cable run measurements
Use tape measure to estimate (note as **approximate**, ±20 cm OK):
- [ ] **Channel R** (roof front-center → rear cargo / trunk): _____ cm
- [ ] **Channel D** (dash center → trunk): _____ cm
- [ ] **Channel S** (steering column → trunk via center tunnel or under seat): _____ cm
- [ ] **Channel S** (pedal area → trunk): _____ cm
- [ ] **Trunk cargo area dimensions** (W × D × H): _____ × _____ × _____ cm

### 11. Existing wiring chase + grommets
- [ ] Note any existing grommeted holes / cable channels usable for our routing.
- [ ] Photograph any obvious place a Pelican 1450 (16.4" × 13" × 6.8") could mount in the trunk.

### 12. Steering bracket from 2020
- [ ] Photograph the steering bracket the 2020 team built (matches CAD in `Hardware/OneDrive_1_5-1-2026/`).
- [ ] Is it still installed? Loose? Painted? Rusty?

### 13. Pedal bracket from 2020
- [ ] Photograph the accelerator pedal bracket (CAD `OneDrive/Vinyl Grafx/...` and Master Plan image #1).
- [ ] Is it installed? Removable? **We are NOT using a mechanical pedal pusher** (electronic bypass instead) — confirm the bracket can be removed if it's in the way.

---

## NICE TO HAVE

### 14. Battery situation
- [ ] User noted "new batteries don't fit original carriage". Photograph current battery layout.
- [ ] Measure available volume in the original carriage; measure the new batteries.

### 15. Full vehicle photos
- [ ] 4× cardinal view photos (front, rear, left, right) for the URDF / CAD reference.
- [ ] Interior: dash close-up showing real estate for ARM/ENGAGE/DISENGAGE buttons + tablet mount.

### 16. VIN
- [ ] Photograph the VIN plate. Useful for ordering Polaris service parts.

---

## END-OF-VISIT EMAIL TO DCE

Once you have item 1's serial number, send this email same-day. Without the autonomous firmware, the entire steering plan is blocked.

> Subject: EPAS18 Ultra ECU — autonomous firmware availability
>
> Hi DCE Motorsport,
>
> I'm reviving an autonomous-vehicle research project at Florida Atlantic
> University. We have an EPAS18 Ultra ECU installed on a Polaris GEM e4
> (serial number: __________). Per User Guide §6 (Autonomous EPAS Operation),
> autonomous control via CAN Msg #3 (ID 0x296) requires a firmware variant
> purchased separately.
>
> Could you tell me:
>   1. Is the autonomous firmware variant available for purchase today?
>   2. Pricing and lead time?
>   3. Can you confirm whether our specific ECU (serial above) was previously
>      flashed with the autonomous variant by the original 2020 team?
>   4. What's the recommended configuration (steering map values, torque
>      deadband, torque zero) for an LSV golf-cart application?
>
> Many thanks,
> [your name], FAU MPCR Lab

---

## WHAT YOU WILL NOT DO TOMORROW

- Test driving via RC. (No firmware exists. RC first-light is ~Week 4–6, after Teensy firmware is written and installed.)
- Power up sensors. (No sensors bought yet.)
- Run the sim on the cart. (Sim runs on a Linux dev box; not on the cart compute since no Jetson is mounted yet.)

---

## AFTER THE VISIT

1. Open `/Users/mpcr/Desktop/Golf Cart Code/Hardware/cart_inspection_2026-05-04.md` (you'll create this from the data gathered) and write up findings.
2. Email DCE re: firmware (item 17 above).
3. Order Tier 1 procurement: Teensy 4.1 ×2, CANable 2.0, MCP4725 ×2, MCP6002, Omron G8HE, Belden 9841, Deutsch DT crimp kit. (~$250.) See `Hardware/system_design.md` PART I.
4. Process the photos → if any open hardware questions are now answered, update `Masterplan.md` PART G accordingly.
