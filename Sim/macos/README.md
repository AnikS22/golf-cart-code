# macOS Sim — Docker + noVNC

The full ROS 2 Humble + Gazebo Harmonic + gem_sim digital twin, running inside a Linux container on macOS, with the GUI exposed in your browser via noVNC. No XQuartz, no Linux VM, no native ROS install.

This is the **dev environment for control algorithms** — write code on the host (any editor), run + visualize in the container.

## One-time setup

1. **Install Docker Desktop** (if not already): https://docs.docker.com/desktop/install/mac-install/ — make sure it's running before continuing.
2. **(Recommended) Bump Docker Desktop resources**: Settings → Resources → ≥ 8 GB RAM, ≥ 4 CPUs, ≥ 60 GB disk.
3. **Build + run** (first time builds the image, ~30 min one-shot):
   ```bash
   bin/sim_macos.sh
   ```
4. **Open the GUI in your browser**:
   ```
   http://localhost:6080/vnc.html
   ```
   Click *Connect* (no password). You'll land on a fluxbox desktop inside the Linux container.

## Build the workspace (first run only, inside the container shell)

```bash
cd /root/ros2_ws
colcon build --symlink-install \
    --packages-skip septentrio_gnss_driver lucid_vision_driver \
                    ouster_sensor_msgs ouster_ros
source install/setup.bash
```

This compiles `gem_sim` and `sim_dbw_bridge`. Skips the upstream sensor drivers we don't have hardware for yet.

## Launch the digital twin

In the container shell (inside the GUI's terminal, or via the host shell that ran `bin/sim_macos.sh`):

```bash
ros2 launch gem_sim sim_full.launch.py
```

You should see Gazebo Harmonic open in the browser GUI with the GEM E4 spawned in the FAU breezeway world. All sensor topics will be publishing on the canonical names (`/livox/lidar`, `/zed2i/...`, `/vn100/imu`, etc.). The `sim_dbw_bridge` node will be running in DISENGAGED state.

## Drive the cart in sim with a joystick

Plug in a Logitech F710 (or any gamepad with USB on macOS). Then **inside the container**:

```bash
ros2 run joy joy_node &
# Press A     → ARMED
# Press Y     → ACTIVE  (publishes /cmd_vel from /dbw/cmd; cart will move)
# Press B     → DISENGAGED
# Press Back  → FAULT (E-stop)
# Press Start → clear FAULT (sim only)
```

Then send a command:

```bash
ros2 topic pub --rate 20 /dbw/cmd ackermann_msgs/msg/AckermannDriveStamped \
    "{drive: {steering_angle: 0.1, speed: 1.0}}"
```

The cart drives forward at 1 m/s with a slight right turn. If you're not in ACTIVE state, sim_dbw_bridge will reject it (zero output to Gazebo).

## Develop control algorithms

- Edit code on the macOS host (VS Code / etc. — the workspace is bind-mounted into the container at `/root/ros2_ws`).
- Rebuild inside the container: `colcon build --symlink-install --packages-select <pkg>`.
- Test inside the container.
- Visualize via the browser noVNC tab.

The `sim_dbw_bridge_node.py` is the reference implementation of the state machine + safety gates. Your control algos publish to `/dbw/cmd`; the bridge gates them; Gazebo executes. Same interface as the real cart.

## Performance expectations on Apple Silicon

- Software OpenGL only (no GPU passthrough on Docker for Mac). Gazebo runs at ~5–10 FPS for a moderately complex world. **Fine for control-loop dev**; not great for perception-heavy testing.
- For perception model training / heavy LiDAR + camera workloads, use a Linux box with a real GPU. The same workspace runs there unchanged.

## Helpful commands

| Command | What |
|---|---|
| `bin/sim_macos.sh` | Build (first time) + run; drops you into container shell |
| `bin/sim_macos.sh build` | Rebuild image only (after editing Containerfile) |
| `bin/sim_macos.sh shell` | Open another shell inside the running container |
| `bin/sim_macos.sh stop` | Stop and remove the container |
| `docker logs ros2-gem-macos` | See what's happening inside |
| `tail -f /tmp/x11vnc.log` (in container) | VNC server logs |

## Troubleshooting

- **"localhost:6080 refused to connect"** → wait 5–10 s for the container to fully start, then refresh the browser tab.
- **Gazebo crashes immediately** → likely Mesa software GL OOM. Bump Docker Desktop RAM ≥ 8 GB.
- **Black screen in noVNC** → fluxbox didn't start; `docker exec ros2-gem-macos pkill -f Xvfb` then re-run.
- **"command not found: ros2"** in the container → forgot to `source /opt/ros/humble/setup.bash` (entrypoint does it for you, but new shells don't auto-source).
