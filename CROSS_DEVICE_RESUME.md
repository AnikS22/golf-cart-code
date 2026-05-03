# Cross-device resume

Pick this project up on any machine — laptop, FAU lab Linux box, second Mac, etc. — without losing context.

## TL;DR

```bash
git clone https://github.com/AnikS22/golf-cart-code.git ~/Desktop/Golf\ Cart\ Code
cd ~/Desktop/Golf\ Cart\ Code
bin/setup_new_machine.sh
claude
```

Memory loads automatically. You're caught up.

## What's in the repo

The entire `/Users/mpcr/Desktop/Golf Cart Code` working directory is the GitHub repo — same files, same layout. Pushed automatically every 10 minutes via macOS launchd (`com.fau.golfcart.autocommit`).

| What | Where |
|---|---|
| Master plan + status + timeline | `Masterplan.md`, `STATUS.md` |
| Hardware design + cart visit checklist + CAD recommendations | `Hardware/` |
| Software design + DBW protocol + sim_dbw_bridge node | `Software/` |
| Digital twin URDF + sim launch + macOS Docker env | `Sim/` |
| **Claude Code memory** (5 files: project, user, feedback, EPAS18 ref, J1939 ref) | `.claude/memory/` |
| Recovered 2020 artifacts (EPAS18 PDFs, J1939 PGN data, etc.) | `Hardware/OneDrive_1_5-1-2026/` |
| Helper scripts (auto-commit, sim, URDF preview, machine setup) | `bin/` |

## What does NOT travel via the repo

- **Conversation transcripts** — Claude Code session JSONLs (~9 MB each) live at `~/.claude/projects/-Users-mpcr-Desktop-Golf-Cart-Code/<session-id>.jsonl` on the machine that hosted the session. They don't sync. They're not strictly needed because the memory + repo carry 90%+ of the context.
- **Sub-agent task outputs** — `~/.claude/projects/-.../991af12c-3dcb-47ba-b9d1-a501769a1f69/tasks/*.output` (3 MB cache).
- **Docker images** (~5 GB) — rebuild via `bin/sim_macos.sh build` per machine.
- **Built ROS 2 workspace artifacts** — `build/`, `install/`, `log/` are gitignored; rebuild with `colcon build` per machine.

If you want full conversation transcripts on the new machine, manually copy them:
```bash
# from the old machine
rsync -av ~/.claude/projects/-Users-mpcr-Desktop-Golf-Cart-Code/*.jsonl new-machine:~/.claude/projects/-Users-mpcr-Desktop-Golf-Cart-Code/
```
But on the new machine the path-encoded directory must match — see "Path encoding" below.

## How the memory cross-device handoff works

Claude Code stores memory at `~/.claude/projects/<encoded-cwd>/memory/`. We've made that path a **symlink** into the repo:

```
~/.claude/projects/-Users-mpcr-Desktop-Golf-Cart-Code/memory
       └── symlink → /Users/mpcr/Desktop/Golf Cart Code/.claude/memory
```

So:
- Memory writes from Claude Code → land in the repo → auto-commit pushes to GitHub.
- Cloning the repo on a new machine → memory is already there.
- Running `bin/setup_new_machine.sh` on the new machine → recreates the symlink so Claude Code on that machine reads the same files.

End result: **memory is one canonical thing, mirrored across every device that has the repo cloned.**

## Path encoding (the gotcha)

Claude Code derives `<encoded-cwd>` from the absolute path by replacing `/` and ` ` (space) with `-`. So:

| Working dir | Encoded |
|---|---|
| `/Users/mpcr/Desktop/Golf Cart Code` (macOS) | `-Users-mpcr-Desktop-Golf-Cart-Code` |
| `/home/mpcr/Desktop/Golf Cart Code` (Linux) | `-home-mpcr-Desktop-Golf-Cart-Code` |
| `/home/mpcr/golf-cart-code` (Linux, different name) | `-home-mpcr-golf-cart-code` |

Different encodings = Claude Code treats them as different projects. **`setup_new_machine.sh` handles this automatically** — it computes the right encoding for whatever path you cloned to.

If you want to keep the same encoded directory across devices (so `claude --resume <session-id>` works for transcripts you copied over), clone to the same relative path on every machine. e.g. always `~/Desktop/Golf Cart Code`.

## Resume on a Linux dev box (FAU lab, Jetson, etc.)

```bash
# 1. Clone
mkdir -p ~/Desktop && git clone https://github.com/AnikS22/golf-cart-code.git ~/Desktop/Golf\ Cart\ Code

# 2. Set up Claude Code memory symlink (creates ~/.claude/projects/.../memory)
cd ~/Desktop/Golf\ Cart\ Code
bin/setup_new_machine.sh

# 3. (Optional) install Claude Code if not already
# See https://docs.claude.com/claude-code/install

# 4. (Optional) auto-commit on this machine via cron (Linux equivalent of launchd)
crontab -l 2>/dev/null > /tmp/crontab.bak
echo "*/10 * * * * $HOME/Desktop/Golf\\ Cart\\ Code/bin/sync.sh" >> /tmp/crontab.bak
crontab /tmp/crontab.bak

# 5. Resume working
cd ~/Desktop/Golf\ Cart\ Code
claude
```

## Resume on a second Mac

Same as Linux but the Mac install path may differ (`/Users/<user>/...`). The setup script handles it.

```bash
brew install --cask docker foxglove   # optional but useful
git clone https://github.com/AnikS22/golf-cart-code.git ~/Desktop/Golf\ Cart\ Code
cd ~/Desktop/Golf\ Cart\ Code
bin/setup_new_machine.sh
bin/install_autocommit.sh             # if you want this Mac to auto-push too
claude
```

## What Claude sees on a fresh session

When you run `claude` in the repo directory on any machine after setup:

1. `MEMORY.md` (the index) loads automatically from `.claude/memory/MEMORY.md`.
2. The 5 memory files (project, user, feedback, EPAS18 ref, J1939 ref) are loadable on demand.
3. The repo's `STATUS.md`, `Masterplan.md`, and folder READMEs provide the rest.

Effectively, a new Claude session on a new machine starts ~95% as informed as the session that's been running on the original Mac.

## Limits

- **Live conversation isn't shared.** Two devices running Claude in the same repo at the same time → two independent sessions. They both push to the repo, so memory edits eventually merge, but real-time collab isn't supported.
- **`claude --resume <session-id>` for transcripts copied between devices** requires identical encoded-cwd. Easiest fix: always clone to the same relative path.
- **Sessions auto-expire after 30 days** by default. The repo + memory are durable; transcripts are ephemeral.
