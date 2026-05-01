# Sim

Gazebo Harmonic digital twin of the GEM E4 on FAU Boca campus.

> **What we're doing here:** see [`SIM_PURPOSE.md`](SIM_PURPOSE.md).
> **Sim ↔ real parity rules:** see [`digital_twin_consistency.md`](digital_twin_consistency.md).

## Layout (canonical)

```
Sim/
├── SIM_PURPOSE.md                          # what we do in sim, why, how, roadmap
├── digital_twin_consistency.md             # rules of the parity game
└── Cartagena_GEM_E4_workspace/             # Cartagena's container + workspace base
    ├── README.md                           # Cartagena's own README (Podman setup)
    ├── launch_ros2.sh                      # host launcher (Wayland/XWayland)
    └── ros2_ws/
        ├── Containerfile                   # ROS 2 Humble + Gazebo
        ├── Containerfile.jazzy             # ROS 2 Jazzy variant
        ├── tools/                          # OSM → Blender → SDF world builder
        │   ├── regions.json                # bbox per region (T1/T2/T3)
        │   ├── fetch_osm.py
        │   ├── tile_downloader.py
        │   ├── blosm_import.py
        │   ├── crop_mesh.py
        │   ├── merge_tiles.py
        │   └── build_world.sh
        └── src/
            ├── pure_pursuit/               # Cartagena's existing waypoint follower
            │   └── worlds/fau_breezeway.sdf
            ├── gem_sim/                    # NEW — top-level robot URDF + launch
            │   ├── package.xml
            │   ├── CMakeLists.txt
            │   ├── urdf/
            │   │   ├── cart_parameters.xacro      # canonical source of truth
            │   │   ├── gem_e4_sensors.urdf.xacro  # 7 cams + LiDAR + 2 GNSS + IMU
            │   │   └── gem_e4_robot.urdf.xacro    # top-level: chassis + sensors + plugins
            │   ├── config/
            │   │   └── ros_gz_bridge.yaml         # Gazebo ↔ ROS topic bridge
            │   └── launch/
            │       └── sim_full.launch.py         # full bringup
            └── sim_dbw_bridge/             # NEW — simulated DBW translation layer
                ├── package.xml
                ├── setup.py
                └── sim_dbw_bridge/
                    └── sim_dbw_bridge_node.py     # state machine + safety gates
                                                   #   (mirrors real Teensy firmware)
```

## Tiered world build

| Tier | Region | Bbox | Status |
|---|---|---|---|
| T1 | Existing breezeway (EE-96 → Wimberly) | 26.3714–26.3734°N × −80.1046–−80.0976°W | **DONE** — `pure_pursuit/worlds/fau_breezeway.sdf` |
| T2 | Academic core (Engineering, Library, Student Union, Owl Plaza) | 26.370–26.376°N × −80.106–−80.097°W | TODO — extend `regions.json` |
| T3 | Full FAU Boca campus (outer paths + parking lots) | 26.365–26.382°N × −80.110–−80.094°W | TODO — multi-region |

## Run the sim (Linux box with Podman)

```bash
# 1. Workspace must be at ~/ros2_ws for Cartagena's container mount
ln -s ~/<repo>/Sim/Cartagena_GEM_E4_workspace/ros2_ws ~/ros2_ws

# 2. Clone upstream deps inside the workspace
cd ~/ros2_ws/src
git clone https://github.com/UIUC-Robotics/gem_ws.git
git clone https://github.com/GEM-Illinois/gem-simulator.git

# 3. Build the container (one-time)
podman build -t ros2-gem:humble ~/ros2_ws

# 4. Launch the digital twin
~/<repo>/Sim/Cartagena_GEM_E4_workspace/launch_ros2.sh \
    ros2 launch gem_sim sim_full.launch.py world:=fau_breezeway

# 5. Inside the running sim — test the DBW state machine via joystick
ros2 run joy joy_node
# Press A to ARM, then Y to ENGAGE. /vehicle/master_state should
# transition DISENGAGED → ARMED → ACTIVE. After ENGAGE, /dbw/cmd
# messages will drive the cart in Gazebo.
```

## Sim ↔ real consistency check (run after any cross-cutting change)

```bash
# Sim launches; expected topics appear:
ros2 topic list | grep -E '(livox|zed2i|front_cam|cam_(fl|fr|rl|rr)|zed_mini|gnss|vn100|cmd_vel|vehicle)'
```

If a topic missing or extra → consistency violation. See `digital_twin_consistency.md`.
