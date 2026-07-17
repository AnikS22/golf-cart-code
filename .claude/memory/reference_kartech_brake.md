---
name: kartech-brake
description: Kartech 1A001HAJ linear actuator is the brake actuator (NOT BTS7960 + PA-14P as earlier docs said). J1939 CAN-controlled. Has captured 2020 BrakeDuino code as protocol reference.
metadata:
  type: reference
---

# Kartech 1A001HAJ Brake Actuator

The brake actuator on this cart is a **Kartech 1A001HAJ** — a CAN-bus linear actuator
that speaks **SAE J1939** on its own dedicated bus. It is **NOT** the BTS7960 + PA-14P
combo that earlier versions of CLAUDE.md, system_design.md, CART_CONTROL_PLAN.md, and
pedals_teensy/src/main.cpp described. Those docs need updating; this part was already
purchased and the H-bridge plan is dead.

This part choice came from the 2020 MPCR team. The current student kept it. It also
matches AutonomouStuff's commercial GEM autonomy kits (they use Kartech for brake on
the same Polaris GEM platform — significant prior art).

## Interface summary (OFFICIAL DATASHEET, 1A001HAJ.doc rev 1.30, obtained 2026-07-17)

| | |
|---|---|
| Manufacturer | Kar-Tech (kar-tech.com) |
| Model | 1A001HAJ — **3" linear CAN actuator**, 10–30 VDC, 5.8 A max, **negative-ground only** |
| Stroke / range | ~3" mechanical; software working range **0.05"–2.95" (550–3450 counts)** |
| Protocol | SAE J1939, 29-bit extended IDs, **250 kbps default** (configurable 250/500k) |
| Bus topology | **Dedicated isolated bus** — NOT shared with the GEM internal J1939 |
| **Default Command ID** | **`0x18FF0000`** (extended). Always re-enabled at power-up (DISDEF clears on boot). |
| **Default Report ID** | **`0x18FF0001`** (extended) — but reassignable & saved in NVM (see BENCH FINDING) |
| Connector | Deutsch **DT04-4P**: pin1 PWR(10–30V), pin2 GND, pin3 CAN-H, pin4 CAN-L |
| Failsafe | No command within **1 s** → drops clutch+motor (idle). Refresh ≤100 ms. |

## Position command — FULLY DECODED (datasheet page 6)

8-byte frame to `0x18FF0000` (extended):
`[0]=0x0F  [1]=0x0A/0x4A  [2]=DPOS_LOW  [3]=CE·M·DPOS_HI  [4..7]=0`
- byte0 `0x0F` = position command type
- byte1: bit7=Confirm, bit6=AutoReply, bits0-5=DataType=**0x0A**. So `0x0A`=no reply, `0x4A`=auto-reply (→ Enhanced Position Report).
- **counts = inches×1000 + 500** (offset 500 = 0"). byte2 = counts low 8 bits; byte3 low **5** bits = counts high bits.
- byte3 **bit7 = clutch enable, bit6 = motor enable**.
- Clutch sequencing (clutch life): clutch ON ≥20 ms *before* motor ON; motor OFF ≥20 ms *before* clutch OFF.
- Commands ≤500 or outside 550–3450 are silently ignored.

This DECODES the old "magic" 2020 frames: e.g. `15,74,196,137` = clutch-on/motor-off @ 2.0" (0x9C4=2500→2000c→2.0"); `15,74,196,201` = clutch+motor @ 2.0". The `binaryToInt()` in the 2020 BrakeDuino is buggy — ignore it, use the formula above.

## Feedback — Enhanced Position Report (byte0 = 152), arrives on the Report ID
`[0]=152 [1]=0 [2]=shaft_lo [3]=shaft_hi [4]=errors [5]=cur_lo [6]=cur_hi [7]=status`
- shaft position: counts = (hi<<8)|lo, **inches = (counts−500)/1000**.
- errors byte4 bits: 0 motor overload · 1 clutch overload · 2 motor open · 3 clutch open · **4 position-reach (stalled/obstructed)** · 5/6 sensor HW warn (→ Auto Zero Cal).
- motor current bytes5-6 in mA.
- Other reports: Position(128), MotorCur/Temp(129), SWrev(239), DeviceID(168), Zeroing(238). Poll any via Report-Poll `0xF1` (info request, **no motion**).

## BENCH FINDING 2026-07-17 — TX works, RX silent (KT ??)
First bench attempt with `brake_test_teensy` (CAN2 @ 250k, same transceiver as steering):
commanding position made the actuator **physically respond — audible banging** (= the
position-reach-error retry: motor pulsed full-on trying to reach an unreachable target),
proving **TX is received**. But the Teensy got **zero reports back** (status showed `KT ??`,
pos/cur/err all default zeros) even with auto-reply (byte1=0x4A) set. So **RX is silent**.
Steering RX worked on this exact transceiver, so the hardware RX path is fine → most likely
the **2020 team reassigned the actuator's User-Defined Report ID** (saved in NVM, survives
power cycles), so reports arrive on a non-default ID we weren't listening for. Next step:
`brake_sniff_teensy` — a safe poll-and-listen firmware (sends only harmless `0xF1` Report
Polls, never a motion command) that prints every CAN ID on the bus to reveal the real
report ID. If it STILL sees nothing while polling, RX is genuinely not getting through
(CAN-H/L swap / termination / actuator power). Banging with tiny targets may also mean the
internal position sensor needs Auto Zero Calibration (shaft uncoupled, cmd `0x7E`).

## Files in the repo

- `Software/firmware/kartech_brake_reference/` — the entire 2020 Arduino source tree
  (ARD1939 stack, mcp_can, the BrakeDuino .ino). **Reference only.** Do not try to
  flash it to anything — it targets Arduino Mega2560 + Seeed MCP2515 CAN shield, not
  Teensy 4.1. We're porting the protocol bits, not the code.

## Port plan (to Teensy 4.1 + FlexCAN_T4)

Throw away: ARD1939.h/.cpp, mcp_can.cpp/.h, mcp_can_dfs.h, can.cpp, can_ext.h, j1939.cpp.
Those are all MCP2515 SPI driver code, irrelevant to Teensy native CAN.

Keep + port: the captured frames above + the PGN/source-addr/priority conventions.

Target firmware structure:

```
Software/firmware/common/include/kartech_brake.h    // public API
Software/firmware/pedals_teensy/src/main.cpp        // calls kartech.brake_full() etc.
```

Public API (sketch):
```cpp
class KartechBrake {
public:
  void begin(FlexCAN_T4<CAN3, RX_SIZE_256, TX_SIZE_64>* can);
  void clutch_on();
  void clutch_off();
  void brake_full();
  void release();          // stock position
  void set_position(uint8_t demand_0_255);  // parameterized, once verified
  bool is_at_target() const;                 // requires feedback PGN sniffing
};
```

Pedals Teensy CAN bus map:
- CAN1 (500 kbps, 11-bit): DBW protocol — Jetson + Motion Teensy peer
- CAN2 (250 kbps, 29-bit J1939): Kartech actuator — dedicated isolated bus, we TX commands
- CAN3 (250 kbps, 29-bit J1939): GEM internal vehicle bus — READ-ONLY sniffer, NEVER TX

## Open questions — mostly CLOSED by the datasheet 2026-07-17
1. ~~`HAJ` suffix~~ → 3" stroke, 10–30 VDC, 5.8 A, negative-ground. **CLOSED.**
2. ~~Feedback PGNs~~ → reports (Enhanced Position 152, etc.) on the Report ID, default
   `0x18FF0001`. **CLOSED in spec** — but this unit's actual report ID is TBD (see BENCH
   FINDING: RX silent, report ID likely reassigned in NVM by the 2020 team). Sniff to confirm.
3. ~~Position encoding~~ → `counts = inches×1000 + 500`, clutch=byte3 bit7, motor=bit6, DPOS_HI
   = byte3 low 5 bits. The 2020 `binaryToInt()` was buggy; use the formula. **CLOSED.**
4. ~~12 V or 24 V?~~ → 10–30 VDC range (12 V fine). **CLOSED.**

STILL OPEN: (a) actuator's real (possibly reassigned) report ID — sniff with `brake_sniff_teensy`;
(b) does it need Auto Zero Calibration before it will servo cleanly?

## Cross-references

- [[gem-e4-self-driving]] — pedals_teensy section, brake actuator line
- [[planning-depth]] — port plan needs the per-frame validation
- [[epas18-ultra]] — sister CAN-controlled actuator (different bus, different
  protocol, but same architectural style: ECU peer on a dedicated CAN bus)
