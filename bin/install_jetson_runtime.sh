#!/usr/bin/env bash
# install_jetson_runtime.sh — install the cart-runtime artifacts on the
# Jetson: systemd units (can0-up + gem-cart-runtime) and ~/run_cart.sh.
#
# Idempotent. Run once (or after edits to the .service files).
#
# Usage:
#   On the Jetson, after `bin/setup_linux.sh`:
#     bin/install_jetson_runtime.sh
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$REPO/Hardware/jetson_runtime"

if [ "$(id -un)" != "jetson" ]; then
    echo "WARN: expected to run as user 'jetson'. Current: $(id -un)"
    echo "Continue anyway? (Ctrl-C to abort, Enter to proceed)"
    read -r _
fi

echo "=== install can0-up.service ==="
sudo cp "$SRC/can0-up.service" /etc/systemd/system/can0-up.service
sudo chmod 0644 /etc/systemd/system/can0-up.service

echo "=== install gem-cart-runtime.service ==="
sudo cp "$SRC/gem-cart-runtime.service" /etc/systemd/system/gem-cart-runtime.service
sudo chmod 0644 /etc/systemd/system/gem-cart-runtime.service

echo "=== install ~/run_cart.sh ==="
cp "$SRC/run_cart.sh" "$HOME/run_cart.sh"
chmod +x "$HOME/run_cart.sh"

echo "=== reload systemd, enable can0-up.service ==="
sudo systemctl daemon-reload
sudo systemctl enable can0-up.service

# Don't auto-enable gem-cart-runtime — let the user start it manually first
# until they trust it.

echo
echo "Installed:"
echo "  /etc/systemd/system/can0-up.service        (enabled — auto at boot)"
echo "  /etc/systemd/system/gem-cart-runtime.service (NOT auto-enabled)"
echo "  $HOME/run_cart.sh                           (executable shortcut)"
echo
echo "Manual launch:                ~/run_cart.sh"
echo "Manual systemd start:         sudo systemctl start gem-cart-runtime"
echo "Auto-start at boot (when you trust it):"
echo "                              sudo systemctl enable gem-cart-runtime"
echo "View live logs:               journalctl -u gem-cart-runtime -f"
