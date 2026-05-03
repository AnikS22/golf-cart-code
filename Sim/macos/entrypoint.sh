#!/bin/bash
# entrypoint.sh — start virtual display, VNC, noVNC, then drop into a
# ROS-sourced shell so the user can `ros2 launch gem_sim sim_full.launch.py`.
#
# All output goes to /tmp/*.log inside the container; docker logs still works.
set -u

DISPLAY_NUM=99
export DISPLAY=":${DISPLAY_NUM}"

# 1. Virtual display
Xvfb "${DISPLAY}" -screen 0 1920x1080x24 -ac +extension GLX +render -noreset \
    > /tmp/xvfb.log 2>&1 &
sleep 1

# 2. Lightweight window manager
(fluxbox > /tmp/fluxbox.log 2>&1) &
sleep 1

# 3. VNC server
x11vnc -display "${DISPLAY}" -forever -shared -rfbport 5900 -nopw \
       -bg -o /tmp/x11vnc.log

# 4. noVNC web bridge (websockify wraps the VNC stream into the browser)
websockify --web /usr/share/novnc/ 6080 localhost:5900 \
           > /tmp/novnc.log 2>&1 &

# 5. Source ROS 2 + (if built) the workspace
source /opt/ros/humble/setup.bash
if [ -f /root/ros2_ws/install/setup.bash ]; then
    source /root/ros2_ws/install/setup.bash
fi

cat <<EOF

────────────────────────────────────────────────────────────────────
  GEM E4 Digital Twin — macOS Docker dev environment
────────────────────────────────────────────────────────────────────

  GUI:  open  http://localhost:6080/vnc.html  in your macOS browser
        (then press Connect; password is empty)

  First-time build the workspace:
      colcon build --symlink-install \\
          --packages-skip septentrio_gnss_driver lucid_vision_driver \\
                          ouster_sensor_msgs ouster_ros
      source install/setup.bash

  Launch the sim (after build):
      ros2 launch gem_sim sim_full.launch.py

  Just inspect the URDF without running Gazebo:
      ros2 run xacro xacro src/gem_sim/urdf/gem_e4_robot.urdf.xacro

  Headless test the DBW state machine:
      ros2 run sim_dbw_bridge sim_dbw_bridge_node

────────────────────────────────────────────────────────────────────
EOF

# Hand control to the requested CMD (default: bash)
exec "$@"
