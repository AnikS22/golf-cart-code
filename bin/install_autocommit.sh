#!/usr/bin/env bash
# install_autocommit.sh — installs the launchd job that auto-commits + pushes
# every 10 minutes.
#
# Run once:
#   bin/install_autocommit.sh
#
# To uninstall:
#   launchctl unload ~/Library/LaunchAgents/com.fau.golfcart.autocommit.plist
#   rm ~/Library/LaunchAgents/com.fau.golfcart.autocommit.plist
#
# To check it's working:
#   launchctl list | grep golfcart
#   tail -f /tmp/golf-cart-sync.log
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLIST_SRC="$REPO_DIR/bin/com.fau.golfcart.autocommit.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.fau.golfcart.autocommit.plist"

if [ ! -f "$PLIST_SRC" ]; then
  echo "FATAL: missing $PLIST_SRC"
  exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents"

# Unload existing if present (idempotent)
if launchctl list | grep -q com.fau.golfcart.autocommit; then
  launchctl unload "$PLIST_DST" 2>/dev/null || true
fi

cp "$PLIST_SRC" "$PLIST_DST"
launchctl load "$PLIST_DST"

echo "Installed launchd job com.fau.golfcart.autocommit"
echo "  Plist: $PLIST_DST"
echo "  Will run every 10 min while you're logged in"
echo "  Log: /tmp/golf-cart-sync.log"
echo
echo "To trigger immediately:  bin/sync.sh"
echo "To uninstall:            launchctl unload $PLIST_DST && rm $PLIST_DST"
