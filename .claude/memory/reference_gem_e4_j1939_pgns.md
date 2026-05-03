---
name: GEM E4 internal CAN — J1939 PGN dictionary
description: Reverse-engineered J1939 PGN list for the 2018 GEM E4 internal CAN bus, recovered from the 2020 project notes (PGN Data.docx). Source 0xFF, Destination 0x475.
type: reference
originSessionId: 991af12c-3dcb-47ba-b9d1-a501769a1f69
---
The 2018 GEM E4 internal CAN bus uses **SAE J1939** (29-bit extended IDs, automotive heavy-duty protocol). NOT generic CAN. Source address 0xFF, destination 0x475 in the recovered captures.

The 2020 FAU team partially reverse-engineered the bus using an Arduino + MCP2515 + the open-source ARD1939 J1939 stack (recovered code in `OneDrive_1_5-1-2026/Arduino Code/`). They were attempting to inject accelerator commands via the vehicle bus as one of two design paths (the other being analog DAC injection at the pedal). **DAC injection is the safer choice; the J1939 bus should be READ-ONLY for our purposes — writing to it can brick the traction controller.**

## Recovered PGNs (from PGN Data.docx, 2020)

| PGN | Name (J1939 standard) | Notes from 2020 reverse engineering |
|---|---|---|
| 61444 | Electronic Engine Controller 1 (EEC1) | "4th bit is voltage most likely and 5th bit is possibly speed. Voltage pins right above pedal, able to measure." |
| 61445 | Electronic Transmission Controller 2 (ETC2) | Gear position on byte 6: **Forward = 70, Neutral = 78, Charging = 67, Reverse = 255 255 255 255 32 82 255 25** |
| 61446 | Electronic Axle Controller 1 (EAC1) | (no notes) |
| 64991 | Front Wheel Drive Status | "Always null, possible lock up status" |
| 65299 | (proprietary) | Changes with no input |
| 65265 | Cruise Control / Vehicle Speed 1 (CCVS1) | "3rd and 4th bit, **4th bit is most likely speed in mph**" |
| 65300 | (proprietary) | (recovered, no notes) |
| 65382 | (proprietary) | (recovered, no notes) |
| 15990542, 15728391, 15990543, 15990545, 15990546 | (extended/proprietary) | "Change with no input" — likely chatter |

## High-value reads for our autonomy stack
- **Vehicle speed** — PGN 65265 byte 4 (mph). Replaces aftermarket wheel encoders entirely.
- **Gear position** — PGN 61445 byte 6 (Forward / Neutral / Charging / Reverse). Required for safety supervisor.
- **Voltage** — PGN 61444 byte 4. Useful for telemetry / health.

## Recommendation for current project (2026)
- **Read-only J1939 sniffer** on the GEM internal CAN. NEVER transmit on it.
- Hook in via the GEM's diagnostic CAN port (typically located near the dash; check service manual). Use a separate, optoisolated CAN transceiver feeding into the Pedals Teensy (or a dedicated J1939 sniffer Teensy if loop loading becomes a concern).
- Republish vehicle speed, gear, voltage as ROS topics via the DBW bridge node.
- Re-verify all PGN bit positions on the 2018 cart with a CAN logger before trusting them — the 2020 work was on the same vehicle but may have been with a different firmware revision.

## Reference code (recovered)
- `/Users/mpcr/Downloads/OneDrive_1_5-1-2026/Arduino Code/ARD1939/` — open-source J1939 stack ported to Arduino + MCP2515 SPI CAN controller. Working starting point for the J1939 sniffer firmware.
- `/Users/mpcr/Downloads/OneDrive_1_5-1-2026/Arduino Code/J1939 Receiving Messages/` — example sketch decoding the GEM's PGNs.
- `OneDrive_1_5-1-2026/Arduino Code/PGN Data.docx` — the canonical PGN list above.
