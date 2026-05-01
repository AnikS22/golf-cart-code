# Hardware

Mechanical, electrical, wiring, and physical packaging for the GEM E4 self-driving conversion.

Master plan: `~/.claude/plans/i-need-your-help-hashed-dongarra.md` (PART A — Hardware, PART D — Build order, PART F — Inventory check).

## Folder layout (to populate)

- `wiring_schedules/` — PDFs of cable schedules from PART A.14 (Channels R, D, S, ESP)
- `cad/` — SolidWorks/STEP files for steering bracket (existing 2020 work) + new aux box brackets + pedal harness tap
- `enclosure_layouts/` — Pelican 1450 internal layout, Aux Box drawings, dash console
- `bom/` — CSV BOMs by zone (compute, sensors, DBW, safety, power, cabling, enclosures)
- `reference_docs/` — copy of EPAS18 PDFs from `OneDrive_1_5-1-2026/Motor/`, GEM service manual when obtained, GEM J1939 PGN docs

## Top action items (this week)

1. Email `sales@dcemotorsport.com` — confirm autonomous firmware status of the cart's EPAS18 Ultra ECU (send ECU serial number from the case label).
2. Probe GEM throttle pedal Hall pair with a multimeter; record V1/V2 vs travel for both channels.
3. Photograph traction controller under driver seat (Sevcon Gen4 vs Curtis 1238).
4. Hand-test EPAS backdrive (motor disconnected, can you turn the wheel?).
5. Confirm pack voltage (48 V or 72 V) at the traction battery.
6. Locate the GEM J1939 diagnostic CAN port (likely under dash near OBD area).
7. Walk the cart with a tape measure: validate Channel R / D / S cable length estimates.

## Open hardware questions (gating)

See PART G of the master plan for the full list. Top three:
- Is the DCE autonomous firmware loaded on the EPAS18 Ultra ECU? (If not, contact DCE — it's purchased separately.)
- Is the cart hardtopped? Affects sensor-mast mounting strategy.
- What's the GEM 12 V house-bus headroom?
