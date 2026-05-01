#!/usr/bin/env bash
# Runs inside the container: build workspace on first run, then launch RViz.
set -e

source /opt/ros/humble/setup.bash
cd /root/ros2_ws

if [ ! -d install ]; then
  echo "==> colcon build (first run; rerun by deleting ~/ros2_ws/{build,install,log})"
  colcon build --symlink-install \
    --packages-skip \
      septentrio_gnss_driver \
      lucid_vision_driver \
      ouster_sensor_msgs \
      ouster_ros
fi

source /root/ros2_ws/install/setup.bash
exec ros2 launch gem_description rviz_display.launch.py
