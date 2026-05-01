#!/usr/bin/env bash
# Runs inside ros2-gem:jazzy. Builds the workspace on first run, then idles.
set -e

source /opt/ros/jazzy/setup.bash
cd /root/ros2_ws

# Build in a separate dir so Humble + Jazzy can coexist in the mounted workspace.
if [ ! -d install_jazzy ]; then
  echo "==> colcon build for jazzy (first run; rerun by deleting install_jazzy/build_jazzy/log_jazzy)"
  colcon build --symlink-install \
    --build-base build_jazzy \
    --install-base install_jazzy \
    --log-base log_jazzy \
    --packages-skip \
      septentrio_gnss_driver \
      lucid_vision_driver \
      ouster_sensor_msgs \
      ouster_ros
fi

source /root/ros2_ws/install_jazzy/setup.bash
echo "==> Jazzy workspace ready. Try: ros2 launch pure_pursuit sim.launch.py"
exec bash
