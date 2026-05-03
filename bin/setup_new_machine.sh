#!/usr/bin/env bash
# setup_new_machine.sh — one-shot setup for resuming this project on a
# new machine (laptop, FAU lab Linux box, second Mac, anywhere).
#
# What it does:
#   1. Detects the absolute path of this clone of the repo.
#   2. Symlinks ~/.claude/projects/<encoded-path>/memory → repo/.claude/memory
#      so Claude Code on this machine sees the canonical memory files
#      and any new memory writes flow back to the repo (auto-commit picks
#      them up).
#   3. (Optional) installs the launchd / cron auto-commit so this device
#      keeps the repo in sync. macOS only by default.
#   4. Reports what's not yet installed (Foxglove, Docker Desktop,
#      Fusion 360, Homebrew, gh CLI) so you know what to grab next.
#
# Idempotent — safe to run multiple times.
#
# Usage:
#   git clone https://github.com/AnikS22/golf-cart-code.git ~/Desktop/Golf\ Cart\ Code
#   cd ~/Desktop/Golf\ Cart\ Code
#   bin/setup_new_machine.sh
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "==> repo at: $REPO"

# Compute Claude Code's encoded-path key.
# Claude Code derives this from the absolute working-directory path by
# replacing every `/` and space with `-`. Example:
#   /Users/mpcr/Desktop/Golf Cart Code → -Users-mpcr-Desktop-Golf-Cart-Code
ENCODED=$(echo "$REPO" | sed -e 's|[/ ]|-|g')
PROJECT_DIR="$HOME/.claude/projects/$ENCODED"
MEMORY_LINK="$PROJECT_DIR/memory"

echo "==> Claude Code will look for memory at: $MEMORY_LINK"
mkdir -p "$PROJECT_DIR"

# If something is already there, back it up unless it's already the
# right symlink.
if [ -L "$MEMORY_LINK" ]; then
    target="$(readlink "$MEMORY_LINK")"
    if [ "$target" = "$REPO/.claude/memory" ]; then
        echo "==> memory symlink already correct"
    else
        echo "==> updating wrong symlink (was → $target)"
        rm "$MEMORY_LINK"
        ln -s "$REPO/.claude/memory" "$MEMORY_LINK"
    fi
elif [ -e "$MEMORY_LINK" ]; then
    BAK="$MEMORY_LINK.bak.$(date +%Y%m%d-%H%M%S)"
    echo "==> backing up existing $MEMORY_LINK → $BAK"
    mv "$MEMORY_LINK" "$BAK"
    ln -s "$REPO/.claude/memory" "$MEMORY_LINK"
else
    ln -s "$REPO/.claude/memory" "$MEMORY_LINK"
fi
echo "==> memory linked. Files now visible to Claude Code:"
ls -1 "$MEMORY_LINK"

# ─── Tooling check (informational, no installs) ─────────────────────
echo
echo "── tooling check ──"
check() {
    local name="$1" cmd="$2" install_hint="$3"
    if eval "$cmd" >/dev/null 2>&1; then
        echo "  ✓ $name"
    else
        echo "  ✗ $name — $install_hint"
    fi
}

UNAME=$(uname -s)

check "git"             "command -v git"               "core requirement"
check "gh CLI"          "command -v gh"                "macOS: brew install gh; Linux: see cli.github.com"
if [ "$UNAME" = "Darwin" ]; then
    check "Homebrew"       "command -v brew"              "https://brew.sh"
    check "Docker Desktop" "[ -d /Applications/Docker.app ]" "https://docker.com/products/docker-desktop"
    check "Foxglove Studio (URDF preview)" "[ -d '/Applications/Foxglove Studio.app' ] || [ -d /Applications/Foxglove.app ]" "brew install --cask foxglove"
elif [ "$UNAME" = "Linux" ]; then
    check "Podman or Docker" "command -v podman || command -v docker" "the Cartagena sim uses Podman; either works"
    check "Foxglove Studio" "command -v foxglove-studio || [ -d /opt/foxglove ]" "see foxglove.dev/download"
fi

# ─── Auto-commit (macOS only for now) ───────────────────────────────
echo
if [ "$UNAME" = "Darwin" ]; then
    if launchctl list 2>/dev/null | grep -q com.fau.golfcart.autocommit; then
        echo "── auto-commit launchd already installed ✓"
    else
        echo "── auto-commit (every 10 min) is NOT installed."
        echo "   Install with:  bin/install_autocommit.sh"
    fi
else
    echo "── auto-commit launchd is macOS-only. On Linux, drop this in cron:"
    echo "   */10 * * * * $REPO/bin/sync.sh"
fi

# ─── Repo state sanity check ────────────────────────────────────────
echo
echo "── repo state ──"
( cd "$REPO" && git log --oneline -3 )
( cd "$REPO" && git status --short ) | head -5

cat <<EOF

────────────────────────────────────────────────────────────────────
  Setup complete.

  Resume Claude Code in this directory:
      cd "$REPO"
      claude --resume        # pick from prior sessions in this dir
      # or just:
      claude                 # fresh session — memory loads automatically

  Memory is canonical at: $REPO/.claude/memory/  (auto-pushes to GitHub)
  Symlinked into Claude Code at: $MEMORY_LINK

  Next steps (project-specific):
    1. Read STATUS.md for current status + timeline
    2. Read Masterplan.md for full architecture
    3. macOS sim env:  bin/sim_macos.sh
    4. URDF preview:   bin/preview_urdf.sh, then drag into Foxglove
────────────────────────────────────────────────────────────────────
EOF
