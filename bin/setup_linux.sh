#!/usr/bin/env bash
# setup_linux.sh — one-shot setup of the GEM E4 sim on a fresh Linux box.
#
# Tested target: Ubuntu 22.04 LTS (Jammy) on x86_64 or arm64. Should also
# work on Pop!_OS, Linux Mint 21, and other 22.04-based distros.
#
# What it does (all idempotent):
#   1. Installs ROS 2 Humble (apt) if missing.
#   2. Installs Gazebo Harmonic + ros-gz bridge if missing.
#   3. Installs the Python + ROS package deps gem_sim / sim_dbw_bridge /
#      gem_dbw_bridge / gem_teleop need.
#   4. Clones the upstream UIUC gem_ws + GEM-Illinois gem-simulator into
#      the workspace (gitignored — per-machine, not vendored).
#   5. rosdep-resolves remaining package deps.
#   6. colcon-builds the workspace.
#
# Usage:
#   git clone https://github.com/AnikS22/golf-cart-code.git ~/golf-cart-code
#   cd ~/golf-cart-code
#   bin/setup_new_machine.sh    # one-time: Claude Code memory symlink
#   bin/setup_linux.sh          # full install + build (sudo required)
#   bin/setup_linux.sh launch   # ...and launch the sim
#
# Re-run any time. Skips steps that are already done.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE="$REPO/Sim/Cartagena_GEM_E4_workspace/ros2_ws"

if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo "==> detected: $PRETTY_NAME"
else
    echo "WARN: cannot detect distro"
fi

if [ "$EUID" -eq 0 ]; then
    echo "ERROR: do not run this script as root. It uses sudo internally."
    exit 1
fi

if ! command -v sudo >/dev/null 2>&1; then
    echo "ERROR: sudo not available. This script needs sudo for apt installs."
    exit 1
fi

if [ "${ID:-}" != "ubuntu" ] && [ "${ID_LIKE:-}" != *"ubuntu"* ]; then
    echo "WARN: tested on Ubuntu 22.04. Continuing anyway. Press Ctrl+C to abort, or wait 5s."
    sleep 5
fi

# ─── 1. ROS 2 Humble ────────────────────────────────────────────────────────
if ! command -v ros2 >/dev/null 2>&1; then
    echo "==> installing ROS 2 Humble"
    sudo apt update
    sudo apt install -y curl gnupg lsb-release software-properties-common
    sudo add-apt-repository -y universe
    sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
        -o /usr/share/keyrings/ros-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" \
        | sudo tee /etc/apt/sources.list.d/ros2.list >/dev/null
    sudo apt update
    sudo apt install -y \
        ros-humble-desktop-full \
        python3-colcon-common-extensions \
        python3-rosdep \
        python3-vcstool \
        python3-pip
    [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ] && sudo rosdep init || true
    rosdep update
else
    echo "==> ros2 already installed: $(which ros2)"
fi

# ─── 2. Gazebo Harmonic + ros-gz bridge ─────────────────────────────────────
if ! command -v gz >/dev/null 2>&1; then
    echo "==> installing Gazebo Harmonic"
    sudo curl -sSL https://packages.osrfoundation.org/gazebo.gpg \
        --output /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" \
        | sudo tee /etc/apt/sources.list.d/gazebo-stable.list >/dev/null
    sudo apt update
    sudo apt install -y gz-harmonic
fi

if ! dpkg -l ros-humble-ros-gz-sim 2>/dev/null | grep -q "^ii"; then
    echo "==> installing ros-gz bridge for Gazebo Harmonic"
    # Package name varies. Try the meta-pkg first; fall back to individual subpkgs.
    sudo apt install -y ros-humble-ros-gz 2>/dev/null \
      || sudo apt install -y \
            ros-humble-ros-gz-sim \
            ros-humble-ros-gz-bridge \
            ros-humble-ros-gz-image \
            ros-humble-ros-gz-interfaces
fi

# ─── 3. Project ROS deps ────────────────────────────────────────────────────
echo "==> installing per-package apt deps"
sudo apt install -y \
    ros-humble-xacro \
    ros-humble-robot-state-publisher \
    ros-humble-joint-state-publisher \
    ros-humble-ackermann-msgs \
    ros-humble-joy \
    ros-humble-rviz2 \
    can-utils

pip3 install --user python-can

# ─── 4. Clone upstream deps ─────────────────────────────────────────────────
mkdir -p "$WORKSPACE/src"
cd "$WORKSPACE/src"
if [ ! -d gem_ws ]; then
    echo "==> cloning UIUC-Robotics/gem_ws"
    git clone --depth 1 https://github.com/UIUC-Robotics/gem_ws.git
else
    echo "==> gem_ws already cloned"
fi
if [ ! -d gem-simulator ]; then
    echo "==> cloning GEM-Illinois/gem-simulator"
    git clone --depth 1 https://github.com/GEM-Illinois/gem-simulator.git
else
    echo "==> gem-simulator already cloned"
fi

# ─── 5. rosdep resolve any remaining package deps ────────────────────────────
cd "$WORKSPACE"
echo "==> rosdep installing per-package deps"
# Skip drivers we don't have hardware for yet
rosdep install --from-paths src --ignore-src -y \
    --skip-keys "septentrio_gnss_driver lucid_vision_driver ouster_sensor_msgs ouster_ros" \
    || echo "WARN: rosdep had non-zero exit; usually fine if all deps resolved"

# ─── 6. Build ───────────────────────────────────────────────────────────────
echo "==> colcon build (~5-10 min first time)"
# ROS 2 setup.bash references unbound vars (AMENT_TRACE_SETUP_FILES,
# COLCON_*) so we drop strict-unbound while sourcing it.
set +u
# shellcheck disable=SC1091
source /opt/ros/humble/setup.bash
set -u
colcon build --symlink-install \
    --packages-skip septentrio_gnss_driver lucid_vision_driver \
                    ouster_sensor_msgs ouster_ros

echo
echo "════════════════════════════════════════════════════════════════════"
echo "  Setup complete. To launch the digital twin:"
echo
echo "    source $WORKSPACE/install/setup.bash"
echo "    ros2 launch gem_sim sim_full.launch.py"
echo
echo "  Or just:  bin/setup_linux.sh launch"
echo "════════════════════════════════════════════════════════════════════"

# ─── 7. Launch if requested ─────────────────────────────────────────────────
if [ "${1:-}" = "launch" ]; then
    cd "$WORKSPACE"
    set +u
    # shellcheck disable=SC1091
    source install/setup.bash
    set -u
    echo "==> launching gem_sim sim_full.launch.py"
    exec ros2 launch gem_sim sim_full.launch.py
fi
