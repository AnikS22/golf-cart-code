#!/bin/bash
# Bring up the cart-control stack on the Jetson.
# Equivalent to: systemctl start gem-cart-runtime, but interactive and shows logs.
set +u
source /opt/ros/humble/setup.bash
source /home/jetson/golf-cart-code/Software/autonomy_ws/install/setup.bash

# Ensure can0 is up
if ! ip link show can0 | grep -q "state UP\|<.*UP.*>"; then
    echo "Bringing up can0..."
    sudo ip link set can0 down 2>/dev/null
    sudo ip link set can0 type can bitrate 500000
    sudo ip link set can0 up
fi

echo "Launching teleop stack (Ctrl-C to stop)..."
echo "  ► joy_node            — gamepad → /joy"
echo "  ► joy_to_ackermann    — /joy → /dbw/cmd"
echo "  ► gem_dbw_bridge      — /dbw/cmd → CAN frames on can0"
echo
echo "On the cart: press dash ARM → ENGAGE."
echo "On the gamepad: hold RB (deadman), use left stick + right trigger."
echo
exec ros2 launch gem_teleop teleop.launch.py
