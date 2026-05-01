#!/usr/bin/env bash
# sync.sh — auto-commit and push any changes in the Golf Cart Code repo.
#
# Usage:
#   bin/sync.sh                # commit + push if there are changes; else exit 0 silently
#   bin/sync.sh "msg"          # use "msg" as the commit message
#
# Designed to be safe to run on a 10-minute cron / launchd schedule. If
# nothing changed, exits 0 with no commits and no push. If changed, makes
# one commit and one push.
#
# Logs to /tmp/golf-cart-sync.log
set -u

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="/tmp/golf-cart-sync.log"
TS() { date "+%Y-%m-%d %H:%M:%S"; }

cd "$REPO_DIR" || { echo "$(TS) FATAL: cannot cd to $REPO_DIR" | tee -a "$LOG"; exit 1; }

# Bail fast if not a git repo
if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "$(TS) skip: $REPO_DIR is not a git repository" >> "$LOG"
  exit 0
fi

# Anything to commit?
if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
  # No changes — silent exit
  exit 0
fi

MSG="${1:-auto: snapshot $(date '+%Y-%m-%d %H:%M:%S')}"

# Commit + push (collect output for log; let exit codes propagate)
{
  echo "── $(TS) auto-sync starting ──"
  git add -A
  git commit -m "$MSG" 2>&1
  git push 2>&1
  echo "── $(TS) auto-sync done ──"
} >> "$LOG" 2>&1
