# Golf Cart Code

FAU MPCR self-driving GEM E4 conversion. "Tiny Waymo" — full self-driving stack on FAU Boca Raton campus, low-speed (≤15 mph), safety-driver-in-seat → unmanned.

## Layout

| Folder | Contents |
|---|---|
| [`Hardware/`](Hardware/) | Component selection, wiring schedules, mechanical packaging, bill of materials. Vendor docs (EPAS18 user guide, J1939 PGN data) recovered from the 2020 project under `OneDrive_1_5-1-2026/`. |
| [`Software/`](Software/) | Drive-by-wire firmware (Teensy 4.1 × 2), autonomy stack (Jetson AGX Orin, ROS 2 Humble, Autoware). Canonical CAN protocol header at `Software/firmware/common/include/dbw_can_protocol.h`. |
| [`Sim/`](Sim/) | Gazebo Harmonic digital twin. Cartagena workspace as foundation. See [`Sim/SIM_PURPOSE.md`](Sim/SIM_PURPOSE.md). |
| [`Masterplan.md`](Masterplan.md) | The canonical project plan. |
| [`bin/`](bin/) | Helper scripts (auto-commit, etc.). |

## Read this first

1. [`Masterplan.md`](Masterplan.md) — project context, phased roadmap, BOM, open questions.
2. [`STATUS.md`](STATUS.md) — current status + week-by-week timeline.
3. [`Hardware/system_design.md`](Hardware/system_design.md) — locked component selection + procurement priority.
4. [`Software/dbw_translation_architecture.md`](Software/dbw_translation_architecture.md) — how a ROS ackermann command becomes wheel motion.
5. [`Sim/SIM_PURPOSE.md`](Sim/SIM_PURPOSE.md) — what the sim is for and how to run it.
6. [`Sim/digital_twin_consistency.md`](Sim/digital_twin_consistency.md) — the rules that keep sim ↔ real parity.

## Resume on a new machine

```bash
git clone https://github.com/AnikS22/golf-cart-code.git ~/Desktop/Golf\ Cart\ Code
cd ~/Desktop/Golf\ Cart\ Code
bin/setup_new_machine.sh
claude        # memory loads automatically
```

Full details + Linux + cross-platform path-encoding gotchas: [`CROSS_DEVICE_RESUME.md`](CROSS_DEVICE_RESUME.md).

## Auto-commit

The repo can auto-commit and push your local edits every 10 minutes via macOS launchd:

```bash
bin/install_autocommit.sh        # install (one-time)
tail -f /tmp/golf-cart-sync.log  # see what it's doing
bin/sync.sh                      # trigger immediately
```

Uninstall: `launchctl unload ~/Library/LaunchAgents/com.fau.golfcart.autocommit.plist && rm $_`.

## Status

Phase 0 (foundation) — design phase, no real-cart firmware running yet.

Critical gating items:
- Confirm DCE Motorsport "autonomous firmware" is loaded on the EPAS18 Ultra ECU.
- Probe GEM throttle Hall-pair voltages, locate J1939 diagnostic port, confirm pack voltage (48 V vs 72 V).
- Email FAU Risk Management about autonomous-vehicle research precedent.

See `Masterplan.md` PART G for the full open-questions list.
