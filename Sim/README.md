# Sim

Gazebo-based simulation of the GEM E4 on FAU Boca campus. Built on the existing **Cartagena workspace** at `~/Downloads/Cartagena_GEM_E4_workspace/`.

Master plan: `~/.claude/plans/i-need-your-help-hashed-dongarra.md` (PART C — Simulation).

## Foundation (already built — don't redo)

- Podman + ROS 2 Humble container (`Containerfile`) AND Jazzy variant (`Containerfile.jazzy`)
- `launch_ros2.sh` — host launcher with Wayland/XWayland passthrough
- `gem_e4.urdf.xacro` — chassis URDF from GEM-Illinois sim
- `pure_pursuit` ROS 2 package — sim launchers for Gazebo Classic AND Harmonic
- World-build pipeline: `fetch_osm.py` → `tile_downloader.py` → `blosm_import.py` → `crop_mesh.py` → `merge_tiles.py` → `reanchor.py` → `build_world.sh`
- `regions.json` with the FAU breezeway region (East Engineering EE-96 → Wimberly Library)
- `fau_breezeway.sdf` — built world for T1

## Tiered world build (extend Cartagena to full Boca campus)

| Tier | Region | Bbox | Status |
|---|---|---|---|
| T1 | Existing breezeway (EE-96 → Wimberly) | 26.3714–26.3734°N × −80.1046–−80.0976°W | DONE in Cartagena |
| T2 | Academic core (Engineering, Library, Student Union, Owl Plaza) | 26.370–26.376°N × −80.106–−80.097°W | TODO — add to regions.json |
| T3 | Full FAU Boca campus (outer paths + parking lots) | 26.365–26.382°N × −80.110–−80.094°W | TODO — multi-region build |

## Top action items

1. Copy the Cartagena workspace contents into `Sim/` (preserve the upstream skip list — don't re-vendor `gem_ws/` and `gem-simulator/`; clone fresh per Cartagena README).
2. Build the Podman container; bring up RViz with the breezeway world.
3. Run `pure_pursuit_node` against the breezeway world; verify lateral tracking.
4. Migrate primary launcher to Gazebo Harmonic (Classic is EOL).
5. Add T2 region to `regions.json` and run `build_world.sh fau_t2`.
6. **Critical:** the **same** lanelet2 map will live in `maps/fau_boca/` and be loaded by both sim and the on-cart Autoware. Build it once.

## Sim use per phase

- P0: dry-run pure-pursuit + DBW bridge before touching real cart.
- P1: validate sensor TF tree + rosbag pipeline; synth-data augment perception.
- P2: closed-loop waypoint following at 5 mph in sim before real-cart attempt.
- P3: inject simulated pedestrians; tune `behavior_velocity_planner`.
- P4: practice unmanned scenarios — stuck cart, GPS outage, telemetry dropout.
