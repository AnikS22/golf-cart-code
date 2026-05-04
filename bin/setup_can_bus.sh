#!/usr/bin/env bash
# setup_can_bus.sh — bring up can0 at 500 kbps for the DBW bus.
#
# CANable 2.0 enumerates as a SocketCAN device on Linux when the
# candleLight firmware is loaded (default). Plug it in, then run this.
#
# Usage:
#   bin/setup_can_bus.sh           # bring can0 up at 500000 bps
#   bin/setup_can_bus.sh down      # bring it down
#   bin/setup_can_bus.sh status    # show state
set -euo pipefail

IFACE=can0
BITRATE=500000

cmd="${1:-up}"

case "$cmd" in
    up)
        # Some hosts auto-up the iface at insertion; idempotent
        if ip -d link show "$IFACE" 2>/dev/null | grep -q "state UP"; then
            echo "$IFACE is already UP"
            ip -d link show "$IFACE" | grep -E "bitrate|state"
            exit 0
        fi
        echo "==> bringing $IFACE up at $BITRATE bps"
        sudo ip link set "$IFACE" down 2>/dev/null || true
        sudo ip link set "$IFACE" type can bitrate "$BITRATE"
        sudo ip link set "$IFACE" up
        echo "==> $IFACE state:"
        ip -d link show "$IFACE" | grep -E "bitrate|state"
        echo
        echo "Test:  candump -tz $IFACE"
        ;;
    down)
        echo "==> bringing $IFACE down"
        sudo ip link set "$IFACE" down
        ;;
    status)
        ip -d link show "$IFACE" 2>&1 || { echo "$IFACE not found"; exit 1; }
        ;;
    *)
        echo "Usage: $0 [up|down|status]"
        exit 1
        ;;
esac
