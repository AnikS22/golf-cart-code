# Linux quickstart

The recommended dev environment for this project. ROS 2 + Gazebo Harmonic want a real Linux box.

## 5-minute clone-and-go

On a fresh Ubuntu 22.04 box (laptop, FAU lab machine, anything):

```bash
# 1. Clone
git clone https://github.com/AnikS22/golf-cart-code.git ~/golf-cart-code
cd ~/golf-cart-code

# 2. Wire up Claude Code memory (one-time, optional but recommended)
bin/setup_new_machine.sh

# 3. Install ROS 2 Humble + Gazebo Harmonic + project deps + build workspace
bin/setup_linux.sh

# 4. Launch the digital twin
bin/setup_linux.sh launch
```

Expected: Gazebo Harmonic opens with the FAU breezeway world and the GEM E4 spawned with all 9 sensors firing on the canonical ROS topics.

`bin/setup_linux.sh` is fully idempotent. Re-running skips already-installed pieces.

## What gets installed

- ROS 2 Humble Hawksbill (`ros-humble-desktop-full`, `python3-colcon-common-extensions`, `python3-rosdep`)
- Gazebo Harmonic (`gz-harmonic`) + ROS↔Gazebo bridge (`ros-humble-ros-gzharmonic`)
- ROS pkgs: `xacro`, `robot-state-publisher`, `joint-state-publisher`, `ackermann-msgs`, `joy`, `rviz2`
- `can-utils` (for the real-cart bridge later)
- `python-can` (for `gem_dbw_bridge`)
- Upstream UIUC `gem_ws` + GEM-Illinois `gem-simulator` cloned into the workspace

Total disk ≈ 6 GB. First-time install ≈ 10–15 min on decent network. First colcon build ≈ 5–10 min.

## Drive the cart in sim with a joystick

After `setup_linux.sh launch`, in another terminal:

```bash
source ~/golf-cart-code/Sim/Cartagena_GEM_E4_workspace/ros2_ws/install/setup.bash
ros2 run joy joy_node                    # USB gamepad
ros2 run gem_teleop joy_to_ackermann_node # convert /joy → /dbw/cmd
```

Then in the sim window: press dash buttons via gamepad mapping (A=ARM, Y=ENGAGE), hold RB as deadman, drive with left stick + right trigger.

## Manual install (if you don't trust the script)

```bash
# ROS 2 Humble per https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debs.html
sudo apt update && sudo apt install -y software-properties-common
sudo add-apt-repository universe
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/ros2.list
sudo apt update && sudo apt install -y ros-humble-desktop-full python3-colcon-common-extensions python3-rosdep
sudo rosdep init && rosdep update

# Gazebo Harmonic per https://gazebosim.org/docs/harmonic/install_ubuntu
sudo curl -sSL https://packages.osrfoundation.org/gazebo.gpg --output /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/gazebo-stable.list
sudo apt update && sudo apt install -y gz-harmonic ros-humble-ros-gzharmonic

# Clone repo + upstream
git clone https://github.com/AnikS22/golf-cart-code.git ~/golf-cart-code
cd ~/golf-cart-code/Sim/Cartagena_GEM_E4_workspace/ros2_ws/src
git clone --depth 1 https://github.com/UIUC-Robotics/gem_ws.git
git clone --depth 1 https://github.com/GEM-Illinois/gem-simulator.git
cd ..

# Build
source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src -y \
    --skip-keys "septentrio_gnss_driver lucid_vision_driver ouster_sensor_msgs ouster_ros"
colcon build --symlink-install \
    --packages-skip septentrio_gnss_driver lucid_vision_driver ouster_sensor_msgs ouster_ros

# Launch
source install/setup.bash
ros2 launch gem_sim sim_full.launch.py
```

## Alternative: use the Cartagena Podman container

If you prefer the original Cartagena workflow (Podman + the bundled Containerfile):

```bash
# After cloning the repo:
ln -sfn ~/golf-cart-code/Sim/Cartagena_GEM_E4_workspace/ros2_ws ~/ros2_ws
cd ~/ros2_ws/src
git clone --depth 1 https://github.com/UIUC-Robotics/gem_ws.git
git clone --depth 1 https://github.com/GEM-Illinois/gem-simulator.git
podman build -t ros2-gem:humble ~/ros2_ws
~/golf-cart-code/Sim/Cartagena_GEM_E4_workspace/launch_ros2.sh ros2 launch gem_sim sim_full.launch.py
```

This expects Wayland (CachyOS / Sway) for the GUI passthrough. Other compositors may need tweaks — see Cartagena's own README.

## What this gives you

The full digital twin running natively:

| Topic | Type | Source |
|---|---|---|
| `/livox/lidar` | PointCloud2 | Gazebo gpu_lidar (Mid-360 model) |
| `/zed2i/{left,right}/image_raw` | Image | Gazebo camera |
| `/zed2i/depth/depth_registered` | Image | Gazebo depth_camera |
| `/front_cam/image_raw` | Image | Gazebo camera |
| `/cam_{fl,fr,rl,rr}/image_raw` | Image | Gazebo camera ×4 |
| `/zed_mini/left/image_raw` | Image | Gazebo camera |
| `/gnss/fix` | NavSatFix | Gazebo gps |
| `/vn100/imu` | Imu | Gazebo imu |
| `/cmd_vel` | Twist | sim_dbw_bridge → Gazebo AckermannSteering |
| `/vehicle/master_state` | UInt8 | sim_dbw_bridge |
| `/dbw/cmd` | AckermannDriveStamped | autonomy → sim_dbw_bridge |

Same topic graph the real cart will publish. Autonomy code you write here drops onto the real cart unchanged.

## Troubleshooting

- **`apt install` fails** → check `/etc/apt/sources.list.d/ros2.list` and `gazebo-stable.list` exist and have correct `lsb_release -cs` codename (jammy on 22.04).
- **`colcon build` fails for missing dep** → run `rosdep install --from-paths src --ignore-src -y` and rebuild.
- **Gazebo black screen / no rendering** → make sure you have a working `glxinfo` (install `mesa-utils`, run `glxinfo | grep "OpenGL renderer"`); needs hardware GL or VirtualGL.
- **Joystick not detected** → `ls /dev/input/js*` should show your gamepad. May need `sudo usermod -a -G input $USER` then logout/login.
