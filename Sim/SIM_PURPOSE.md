# What We're Doing in the Sim

## Short answer
We are building a **digital twin** of the GEM E4 cart on FAU Boca campus. Every line of autonomy code we write — perception, localization, planning, control, safety supervisor — runs against the sim **first**. When we trust it in sim, we deploy the same code to the real cart with no changes. The sim is the unit-test environment for autonomy and the integration-test environment for the full stack.

## Why bother with a sim
The real cart is dangerous (it can hurt people), expensive (sensor + compute risk), slow to test against (drive somewhere, set up scenarios), and weather-dependent. Bugs found in sim cost minutes; bugs found on the real cart at FAU campus cost broken sensors, scared pedestrians, and program-ending PR incidents. Industry rule of thumb: **>95% of autonomy iteration cycles happen in sim**.

Sim cannot replace real-world testing — sensor noise, weather, pedestrian unpredictability, motor inertia, GPS dropout under tree canopy: those are all real-only. But sim catches the obvious bugs that would otherwise eat real-cart test sessions.

## What the sim contains
1. **Cart model** — a URDF-described GEM E4 with the same wheelbase, mass, sensor mount poses, and Ackermann steering kinematics as the real cart. Source of truth: `cart_parameters.xacro`.
2. **Sensor stack** — 7 cameras (ZED 2i front stereo, Leopard front mono, 4× corner GMSL, ZED Mini rear), Livox Mid-360 LiDAR, dual-antenna GNSS, VectorNav IMU. Same FOV / rate / range / topic names as the real hardware.
3. **DBW translation layer** — `sim_dbw_bridge_node.py` runs the same state machine (DISENGAGED/ARMED/ACTIVE/FAULT) and same safety gates as the real Teensy firmware will. Autonomy commands go to `/dbw/cmd`; sim transparently emits `/cmd_vel` to Gazebo. On the real cart, the same `/dbw/cmd` becomes a CAN frame to a Teensy.
4. **World** — an SDF mesh of FAU Boca campus. Tiered:
   - **T1** (already built in Cartagena): East Engineering EE-96 → Wimberly Library breezeway.
   - **T2** (TODO): full academic core (Engineering complex, library, student union, breezeway, Owl Plaza).
   - **T3** (TODO): full ~850-acre Boca campus including parking lots and outer paths.
   World meshes are generated from real OpenStreetMap data via the Cartagena `tools/` pipeline (OSM → Blender via blosm → mesh crop/merge → SDF).

## What we *do* in the sim, day to day
- **Phase 0** — joystick teleop dry-run, sim_dbw_bridge state-machine validation, autonomy code skeleton against real ROS topics.
- **Phase 1** — sensor TF-tree validation, perception models trained on sim-augmented data, ROS bag pipeline tested with sim sensors.
- **Phase 2** — closed-loop waypoint following at 5 mph in T1 breezeway. Validate the lanelet2 map. Same map and same code will run on the real cart.
- **Phase 3** — inject simulated pedestrians (Gazebo actor entities) and scripted obstacles. Tune Autoware `behavior_velocity_planner` modules (crosswalk, run_out, occlusion_spot) against pedestrian dart-out scenarios.
- **Phase 4** — practice unmanned scenarios that are too risky to test live: GPS dropout under tree cover, telemetry link loss, mid-drive Jetson watchdog, simulated EPAS faults. Verify the safety supervisor commands a controlled stop in every case.

## What we will *not* do in the sim
- **Real-world perception training data.** Sim noise is Gaussian; real LiDAR/camera noise has structure (sun glint, motion blur, multipath). Models trained only on sim degrade on real data. Use sim for synthetic augmentation, not primary training.
- **EPAS18 mechanical response tuning.** Sim Gazebo plugin steers instantaneously; the real EPS column has 50–200 ms inertia. Tune the steering PI gains on the real cart.
- **GPS-degraded behavior characterization.** Sim GPS is always perfect. Real RTK transitions FLOAT/FIX/NO-FIX with tree cover. Test on real cart only.

## How sim ↔ real parity is enforced
- **One source of truth** for vehicle geometry, sensor poses, sensor specs: `Sim/Cartagena_GEM_E4_workspace/ros2_ws/src/gem_sim/urdf/cart_parameters.xacro`. Both sim URDF and real-cart URDF include this file.
- **One source of truth** for the DBW protocol: `Software/firmware/common/include/dbw_can_protocol.h`. Compiled into both Teensy firmware AND the sim_dbw_bridge node imports the same constants.
- **Identical ROS topic names + message types** in sim and real. The autonomy stack subscribes to the exact same topic graph in both environments.
- **Identical state machine** in sim_dbw_bridge and Teensy firmware. Same enum names, same transitions, same safety gates.
- See `Sim/digital_twin_consistency.md` for the full discipline.

## How to run the sim (Linux box; macOS host can't run Gazebo Harmonic natively)
1. Clone the workspace: `git clone https://github.com/AnikS22/golf-cart-code.git ~/golf-cart-code`
2. Symlink the Cartagena ROS workspace to the location its container expects:
   `ln -s ~/golf-cart-code/Sim/Cartagena_GEM_E4_workspace/ros2_ws ~/ros2_ws`
3. Clone upstream dependencies into `~/ros2_ws/src/`:
   ```
   git clone https://github.com/UIUC-Robotics/gem_ws.git
   git clone https://github.com/GEM-Illinois/gem-simulator.git
   ```
4. Build the Podman container: `podman build -t ros2-gem:humble ~/ros2_ws`
5. Launch: `~/golf-cart-code/Sim/Cartagena_GEM_E4_workspace/launch_ros2.sh ros2 launch gem_sim sim_full.launch.py`
6. After Gazebo comes up: connect a Logitech F710 joystick (`ros2 run joy joy_node`), press A to ARM, Y to ENGAGE, then the autonomy nodes can drive.

## Roadmap inside the sim
- **Sprint 1**: bring up the existing T1 breezeway world; validate sim_dbw_bridge state machine via joystick.
- **Sprint 2**: extend `regions.json` to T2 (academic core); rebuild world meshes; verify the cart drives on the new world.
- **Sprint 3**: hook Autoware Universe perception + planning to the canonical sensor topics; close the loop on T1.
- **Sprint 4**: T3 full campus mesh; multi-route waypoint following.
- **Sprint 5**: scripted pedestrian / obstacle injection; tune behavior_velocity_planner.
- **Sprint 6**: simulated failure modes (GPS dropout, watchdog timeout, EPAS fault); validate safety supervisor.
