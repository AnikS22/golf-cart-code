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

## Run the sim (Linux, recommended)

The full digital-twin sim runs on Ubuntu 22.04. **5-minute clone-and-go**:

```bash
git clone https://github.com/AnikS22/golf-cart-code.git ~/golf-cart-code
cd ~/golf-cart-code
bin/setup_linux.sh           # ROS 2 Humble + Gazebo Harmonic + project deps + build
bin/setup_linux.sh launch    # opens Gazebo with the FAU breezeway + cart + 9 sensors
```

Full guide: [`LINUX_QUICKSTART.md`](LINUX_QUICKSTART.md).

> macOS host caveat: ROS 2 + Gazebo are fragile on macOS (Apple Silicon Rosetta breaks Gazebo's shared-memory tracking; ROS 2 macOS support is unofficial). For visual-only confirmation on Mac, use `bin/preview_urdf.sh` then drag the URDF into Foxglove.app. For real dev, use Linux.

## Read this first

1. [`Masterplan.md`](Masterplan.md) — project context, phased roadmap, BOM, open questions.
2. [`STATUS.md`](STATUS.md) — current status + week-by-week timeline.
3. [`LINUX_QUICKSTART.md`](LINUX_QUICKSTART.md) — clone-and-go setup of the sim.
4. [`Hardware/system_design.md`](Hardware/system_design.md) — locked component selection + procurement priority.
5. [`Software/CART_CONTROL_PLAN.md`](Software/CART_CONTROL_PLAN.md) — manual ROS-based control plan, no autonomy.
6. [`Software/dbw_translation_architecture.md`](Software/dbw_translation_architecture.md) — how a ROS ackermann command becomes wheel motion.
7. [`Sim/SIM_PURPOSE.md`](Sim/SIM_PURPOSE.md) — what the sim is for.
8. [`Sim/digital_twin_consistency.md`](Sim/digital_twin_consistency.md) — sim↔real parity rules.

## Resume on a new machine

Pick this project up on any laptop, FAU lab Linux box, second Mac, etc. — without losing context.

### Quick start

```bash
git clone https://github.com/AnikS22/golf-cart-code.git ~/Desktop/Golf\ Cart\ Code
cd ~/Desktop/Golf\ Cart\ Code
bin/setup_new_machine.sh
claude        # memory loads automatically
```

That's it. The new Claude session is ~95% as informed as the original.

### How it works

Claude Code stores memory at `~/.claude/projects/<encoded-cwd>/memory/`. We've made that path a **symlink** into the repo on every device:

```
~/.claude/projects/-Users-mpcr-Desktop-Golf-Cart-Code/memory
       └── symlink → <repo>/.claude/memory
```

So memory writes from Claude → land in the repo → auto-commit pushes to GitHub → other devices `git pull` → those devices see the same memory. **One canonical store, mirrored across every device that has the repo cloned.**

`bin/setup_new_machine.sh` is idempotent: detects the right encoded path, creates the symlink (backing up any existing memory), and reports what tooling is missing (Docker Desktop, Foxglove, Homebrew, gh CLI).

### Path encoding (the gotcha)

Claude Code derives `<encoded-cwd>` from the absolute path by replacing `/` and ` ` (space) with `-`:

| Working dir | Encoded |
|---|---|
| `/Users/mpcr/Desktop/Golf Cart Code` (macOS) | `-Users-mpcr-Desktop-Golf-Cart-Code` |
| `/home/mpcr/Desktop/Golf Cart Code` (Linux) | `-home-mpcr-Desktop-Golf-Cart-Code` |

Different encodings = Claude treats them as different projects. The setup script handles this automatically. If you want `claude --resume <session-id>` to work for transcripts copied between devices, **clone to the same relative path on every machine** (e.g. always `~/Desktop/Golf Cart Code`).

### Linux dev box (FAU lab, Jetson, etc.)

```bash
mkdir -p ~/Desktop && git clone https://github.com/AnikS22/golf-cart-code.git ~/Desktop/Golf\ Cart\ Code
cd ~/Desktop/Golf\ Cart\ Code
bin/setup_new_machine.sh

# Optional: cron-based auto-commit (Linux equivalent of the macOS launchd job)
( crontab -l 2>/dev/null; echo "*/10 * * * * $HOME/Desktop/Golf\\ Cart\\ Code/bin/sync.sh" ) | crontab -

claude
```

### Second Mac

```bash
brew install --cask docker foxglove   # optional but useful
git clone https://github.com/AnikS22/golf-cart-code.git ~/Desktop/Golf\ Cart\ Code
cd ~/Desktop/Golf\ Cart\ Code
bin/setup_new_machine.sh
bin/install_autocommit.sh             # if you want this Mac to auto-push too
claude
```

### What does and doesn't travel with the repo

| | Travels via repo | Lives only on the host machine |
|---|---|---|
| Memory files (project, user, feedback, EPAS18 ref, J1939 ref) | ✓ | |
| All project code, docs, plans, recovered 2020 artifacts | ✓ | |
| Auto-commit launchd plist (template) | ✓ (run `install_autocommit.sh` to activate per-machine) | |
| Conversation transcripts (`*.jsonl`, ~9 MB each) | | ✓ (manual `rsync` if you want them) |
| Sub-agent task output caches | | ✓ |
| Docker images (~5 GB) | | ✓ (rebuild with `bin/sim_macos.sh build`) |
| ROS 2 `build/install/log/` artifacts | | ✓ (rebuild with `colcon build`) |

### Limitations

- Two devices running Claude in the same repo at the same time → two independent sessions. They both push to the repo, so memory edits eventually merge, but there's no real-time collab.
- Sessions auto-expire after 30 days by default. The repo + memory are durable; transcripts are ephemeral.
- `claude.ai/code` (web) and the CLI maintain separate session histories — they don't sync with each other.

For full details: [`CROSS_DEVICE_RESUME.md`](CROSS_DEVICE_RESUME.md).

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
