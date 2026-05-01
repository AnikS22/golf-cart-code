ROS2 + Gazebo simulation of the Polaris GEM E4 autonomous golf cart, set up to run in a Podman container on CachyOS (Wayland).
- `launch_ros2.sh` - host script to run the Podman container
- `ros2_ws/Containerfile`, `Containerfile.jazzy` - container build recipes (Humble and Jazzy variants)
- `ros2_ws/container_setup.sh`, `container_setup_jazzy.sh` - in-container setup
- `ros2_ws/.gem.urdf`, `.gem.sdf` - generated robot model files
- `ros2_ws/tools/` - world building scripts (OSM tile downloader, blosm import, mesh crop/merge)
- `ros2_ws/src/pure_pursuit/` - custom pure pursuit controller ROS2 package
Skipped to save size:
- `ros2_ws/src/gem_ws/` and `ros2_ws/src/gem-simulator/` (upstream clones, see URLs below)
- `ros2_ws/build/`, `install/`, `log/` (regenerable)
- `ros2_ws/tools/fau_world/` (Blender world meshes, ~344 MB, ask if needed separately)
1. Install Podman.
2. Make a workspace and clone the upstream repos:
   ```
   mkdir -p ~/ros2_ws/src
   cd ~/ros2_ws/src
   git clone https://github.com/UIUC-Robotics/gem_ws.git
   git clone https://github.com/GEM-Illinois/gem-simulator.git
   ```
3. Drop the contents of this bundle into `~/ros2_ws/` (and `~/launch_ros2.sh`).
4. Run `~/launch_ros2.sh` to start the container.
5. Inside the container, run `bash /root/ros2_ws/container_setup.sh` once.
6. Source the workspace and `ros2 launch pure_pursuit pure_pursuit.launch.py` (or the Jazzy variant).
- Wayland passthrough requires `QT_QPA_PLATFORM=wayland` and the wayland socket bind, both set by `launch_ros2.sh`.
- The Jazzy variant exists because some upstream packages had Humble issues; both are included.
