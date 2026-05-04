# teleop.launch.py — full RC stack on the laptop.
#
#   joy_node                → /joy
#   joy_to_ackermann_node   → /dbw/cmd  +  /dbw/enable
#   gem_dbw_bridge_node     → CAN frames on can0
#
# Prerequisites:
#   1. Plug in CANable; `bin/setup_can_bus.sh` to bring up can0 at 500 kbps.
#   2. Plug in Logitech F710 USB receiver.
#   3. `colcon build --symlink-install`; `source install/setup.bash`.
#
# Run:
#   ros2 launch gem_teleop teleop.launch.py

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package="joy",
            executable="joy_node",
            name="joy_node",
            parameters=[{
                "deadzone": 0.05,
                "autorepeat_rate": 50.0,
            }],
            output="screen",
        ),
        Node(
            package="gem_teleop",
            executable="joy_to_ackermann_node",
            name="joy_to_ackermann",
            output="screen",
        ),
        Node(
            package="gem_dbw_bridge",
            executable="gem_dbw_bridge_node",
            name="gem_dbw_bridge",
            output="screen",
        ),
    ])
