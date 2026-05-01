#!/usr/bin/env bash
# Launch ros2-gem:humble with GPU + Wayland/XWayland GUI passthrough.
# Build image first:  podman build -t ros2-gem:humble ~/ros2_ws
set -e

IMAGE="ros2-gem:humble"
CONTAINER="ros2-gem"

# Optional: pass a command to run instead of the default (RViz via container_setup.sh).
# Example:  ~/launch_ros2.sh ros2 launch gazebo_ros gazebo.launch.py
if [ $# -gt 0 ]; then
  # Unique per-invocation suffix so concurrent adhoc shells don't --replace each other.
  CONTAINER="${CONTAINER}-adhoc-$$-$(date +%s%N | tail -c7)"
  QUOTED=$(printf '%q ' "$@")
  RUN_CMD=(bash -lc "source /opt/ros/humble/setup.bash; [ -f /root/ros2_ws/install/setup.bash ] && source /root/ros2_ws/install/setup.bash; exec ${QUOTED}")
else
  RUN_CMD=(bash /root/ros2_ws/container_setup.sh)
fi

: "${WAYLAND_DISPLAY:=wayland-0}"
: "${XDG_RUNTIME_DIR:=/run/user/$(id -u)}"
: "${DISPLAY:=:0}"

WL_SOCK="${XDG_RUNTIME_DIR}/${WAYLAND_DISPLAY}"

# Qt platform: xcb (XWayland) is most reliable for RViz's Ogre3D renderer.
# To try native Wayland instead, run:  QT_PLATFORM=wayland ~/launch_ros2.sh
: "${QT_PLATFORM:=xcb}"

# XWayland auth: pass the host's X cookie file into the container.
# The cookie is bound to DISPLAY+hostname; --network host keeps hostname identical.
XAUTH_MOUNT=()
if [ -n "${XAUTHORITY:-}" ] && [ -r "${XAUTHORITY}" ]; then
  XAUTH_MOUNT=(-v "${XAUTHORITY}:/tmp/.Xauthority:ro" -e "XAUTHORITY=/tmp/.Xauthority")
fi

exec podman run --rm -it \
  --name "${CONTAINER}" \
  --replace \
  --network host \
  --ipc host \
  --device /dev/dri \
  --group-add keep-groups \
  -v "${HOME}/ros2_ws:/root/ros2_ws:Z" \
  -v "${WL_SOCK}:/tmp/${WAYLAND_DISPLAY}" \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  "${XAUTH_MOUNT[@]}" \
  -e "WAYLAND_DISPLAY=${WAYLAND_DISPLAY}" \
  -e "XDG_RUNTIME_DIR=/tmp" \
  -e "DISPLAY=${DISPLAY}" \
  -e "QT_QPA_PLATFORM=${QT_PLATFORM}" \
  "${IMAGE}" \
  "${RUN_CMD[@]}"
