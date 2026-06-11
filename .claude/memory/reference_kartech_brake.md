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

## Interface summary

| | |
|---|---|
| Manufacturer | Kar-Tech (kar-tech.com) |
| Model | 1A001HAJ (suffix HAJ encodes stroke/voltage/connector — datasheet still TBD) |
| Protocol | SAE J1939 (29-bit extended IDs, 250 kbps) |
| Bus topology | **Dedicated isolated bus** — NOT shared with the GEM internal J1939 |
| Command PGN | **65280** (0xFF00, Manufacturer Proprietary A) |
| Source addr | 128 (preferred per ARD1939 default) |
| Dest addr | 255 (global broadcast) |
| Priority | 0 |
| Feedback PGNs | Unknown — need to sniff at the cart |

## Captured command frames (from 2020 BrakeDuino, validated working)

All payloads are 8 bytes. First two bytes are the Kartech vendor magic header `0x0F 0x4A`
(15, 74). Remaining bytes encode the command.

| Action | Bytes 0-7 (decimal) |
|---|---|
| Clutch ON (engage actuator) | `15, 74, 196, 137, 0, 0, 0, 0` |
| Clutch OFF (disengage) | `15, 74, 208, 7, 0, 0, 0, 0` |
| Extend ~3 inches | `15, 74, 91, 204, 0, 0, 0, 0` |
| Retract | `15, 74, 238, 195, 0, 0, 0, 0` |
| Retract (alt) | `15, 74, 109, 201, 0, 0, 0, 0` |
| Full brake position | `15, 74, 193, 203, 0, 0, 0, 0` |
| Brake light signal | `15, 74, 105, 204, 0, 0, 0, 0` |
| Return to stock (zero) | `15, 74, 192, 205, 0, 0, 0, 0` |

Parameterized position: bytes 2 and 3 encode `(input * 40)` as MSB/LSB, with the top
two bits of MSB forced to `11` (suggesting a 2-bit command type + 14-bit position
encoding). The 2020 implementation of this encoding is buggy (see `binaryToInt()` in
`Software/firmware/kartech_brake_reference/BrakeDuino_copy_*.ino`) and should not be
copied verbatim — verify against the actual actuator before trusting.

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

## Open questions (to close at the cart or with Kartech)

1. What does the `HAJ` suffix decode to? (stroke length, voltage, connector type)
2. What are the feedback PGNs? Need to sniff with Kvaser on the dedicated bus.
3. Is the position encoding really `input * 40 → 14-bit + top 2 bits "11"`, or is the
   2020 code wrong? Test against the actual actuator.
4. Is the actuator 12 V or 24 V? Datasheet question; affects power wiring.

## Cross-references

- [[gem-e4-self-driving]] — pedals_teensy section, brake actuator line
- [[planning-depth]] — port plan needs the per-frame validation
- [[epas18-ultra]] — sister CAN-controlled actuator (different bus, different
  protocol, but same architectural style: ECU peer on a dedicated CAN bus)
