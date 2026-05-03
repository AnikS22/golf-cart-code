# `.claude/` — Claude Code state synced across devices

This directory holds the project-specific Claude Code state we want to follow the project across machines.

## `memory/`

The canonical store for Claude Code's [auto memory](https://docs.claude.com/claude-code/memory) for this project. Five typed memory files plus an `MEMORY.md` index:

| File | Type | What |
|---|---|---|
| `MEMORY.md` | index | One-line pointer per memory; loads first ≤200 lines on every session |
| `project_gem_e4_self_driving.md` | project | Project context, status, recovered artifacts |
| `user_role.md` | user | Who the user is, communication style, knowledge gaps to expect |
| `feedback_planning_depth.md` | feedback | Always cite prior art; spec wires/cables/cooling at procurement detail |
| `reference_epas18_ultra.md` | reference | EPAS18 Ultra ECU CAN protocol, pinout, manual override pattern |
| `reference_gem_e4_j1939_pgns.md` | reference | GEM E4 internal CAN J1939 PGN dictionary |

On each machine, `bin/setup_new_machine.sh` creates a symlink:

```
~/.claude/projects/<encoded-cwd>/memory  →  <repo>/.claude/memory
```

So Claude Code reads/writes here, and auto-commit propagates updates to GitHub.

## What does NOT live here

- **Session transcripts** (`*.jsonl`) — large, conversation-specific, ephemeral (30-day default expiry). See `CROSS_DEVICE_RESUME.md` for how to manually sync if needed.
- **Sub-agent task outputs** — caches that grow during a session.
- **Tool results cache** — generated per-session.

These all live under `~/.claude/projects/<encoded-cwd>/` outside the symlinked `memory/` and don't follow the project.
