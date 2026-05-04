# Jetson Wiring Diagram — what to plug into which port

For the **Yahboom Jetson Orin NX Super Developer Kit** that's in your hand right now (`hostname: yahboom`, `192.168.55.1`).

This is the cart's CAN gateway + safety supervisor. Per the master plan PART A.6, it talks to the Teensies over the **DBW CAN bus** (its kernel-level `can0` interface, 500 kbps). It does NOT talk to actuators directly — that's the Teensies' job.

---

## Port map (top + back of carrier)

```
┌────────────────────────────────────────────────────────────────────────┐
│                                                                        │
│   ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐         POWER BUTTON  ●       │
│   │ USB  │  │ USB  │  │ USB  │  │ USB  │         RESET BUTTON  ○       │
│   │  A   │  │  A   │  │  A   │  │  A   │                                │
│   │ ❶3.0 │  │ ❷3.0 │  │ ❸3.0 │  │ ❹3.0 │                                │
│   └──────┘  └──────┘  └──────┘  └──────┘                                │
│                                                                        │
│   ┌─────────────┐   ┌─────────┐   ┌─────────┐    ┌──────────────┐      │
│   │  Gigabit    │   │ HDMI ❼  │   │  USB-C  │    │  DC IN 19 V  │      │
│   │  Ethernet❺  │   │         │   │  ❻      │    │  ❽ barrel    │      │
│   │  (eno1)     │   │         │   │ (data)  │    │              │      │
│   └─────────────┘   └─────────┘   └─────────┘    └──────────────┘      │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘

                       40-pin GPIO header (top edge of board)
   ┌────────────────────────────────────────────────────────────────┐
   │ 1  3  5  7  9 11 13 15 17 19 21 23 25 27 29 31 33 35 37 39    │
   │ 2  4  6  8 10 12 14 16 18 20 22 24 26 28 30 32 34 36 38 40    │
   └────────────────────────────────────────────────────────────────┘
   ❾ CAN_H + CAN_L on this header — exact pins per Yahboom docs.
     (Connects to DBW bus: Motion Teensy + Pedals Teensy.)
```

---

## What plugs where (Phase 0 — first-light cart drive)

| # | Port | What plugs in | Why |
|---|---|---|---|
| ❶ | USB-A | **Logitech F710 USB receiver** | Gamepad → `/joy` topic via `joy_node` → `joy_to_ackermann_node` → `/dbw/cmd` |
| ❷ | USB-A | **(reserved)** Optional CANable 2.0 dongle | Only if you DON'T use the GPIO CAN. With the GPIO CAN already up at `can0`, you don't need this. |
| ❸/❹ | USB-A | spare USB peripherals | Keyboard/mouse if you HDMI-attach a monitor for direct debugging |
| ❺ | RJ-45 (eno1) | Wired Ethernet | Internet for setup/dev only. Will connect to LiDAR (Livox Mid-360) in Phase 1+. |
| ❻ | USB-C | Currently your Mac (USB networking + power) | Keep until standalone in cart, then unplug |
| ❼ | HDMI | Optional monitor | For direct GUI; otherwise SSH from Mac is enough |
| ❽ | DC barrel 19V | Cart power (post DC-DC) | Standalone power; ~25 W typical, 90 W peak |
| ❾ | 40-pin GPIO CAN_H/CAN_L | **DBW CAN bus** to Motion + Pedals Teensies | THE critical connection — this is how the Jetson talks to the cart |

**Two-pin Wi-Fi antenna connectors** (M.2 module exposed connectors on the carrier) — keep antennas attached for Wi-Fi.

---

## Phase 0 first-light wiring (the absolute minimum to drive the cart from the Jetson)

```
                                      DBW CAN bus @ 500 kbps
                                         (twisted pair)
                                                │
                         ┌──────────────────────┼──────────────────────┐
                         │                      │                      │
                         ▼                      ▼                      ▼
                  ┌────────────┐         ┌────────────┐         ┌────────────┐
   ❾ GPIO CAN ───►│   Jetson   │         │ Motion     │         │ Pedals     │
                  │ Orin NX    │         │ Teensy 4.1 │         │ Teensy 4.1 │
                  │ (Yahboom)  │         │ + xceiver  │         │ + xceiver  │
                  └─────┬──────┘         └─────┬──────┘         └─────┬──────┘
                        │                      │                      │
                        │ USB ❶                │ EPAS bus             │ I²C → DACs
                        ▼                      │ 500 kbps             │ → DPDT relay
                  ┌────────────┐               ▼                      │ → traction ctrl
                  │ Logitech   │         ┌────────────┐               │
                  │ F710       │         │ EPAS18     │               │ J1939 read
                  │ gamepad    │         │ Ultra ECU  │               ▼ via ISO1042
                  └────────────┘         │ → motor    │         ┌────────────┐
                                         │ → wheels   │         │ GEM diag   │
                                         └────────────┘         │ port       │
                                                                └────────────┘
                  ❽ DC IN 19 V  ◄─── from cart's 12 V → 19 V buck (Pololu D24V50F19)

```

**Connections to verify** (each one is a separate physical wire/connector):

| From | To | Cable | Connector |
|---|---|---|---|
| Jetson 40-pin CAN_H/L | DBW bus stub (twisted pair) | Belden 9841 or equiv | crimp + heatshrink |
| DBW bus | Motion Teensy CAN1 + transceiver | Belden 9841 | DT04-4P |
| DBW bus | Pedals Teensy CAN1 + transceiver | Belden 9841 | DT04-4P |
| Cart 12 V aux | Pololu D24V50F19 → Jetson barrel | 14 AWG | 2.1 × 5.5 mm barrel |
| Logitech F710 USB receiver | Jetson USB-A ❶ | — | USB-A |

Don't forget **120 Ω termination resistors at each end of the DBW bus** (one at the CANable/Jetson end, one at the farthest Teensy). Without them the bus is electrically reflective and frames will be dropped.

---

## Phase 1+ (sensors come online)

Add as parts arrive:

| # | Sensor | Port | Notes |
|---|---|---|---|
| | **Livox Mid-360 LiDAR** | Ethernet ❺ | Cat6, plus 12 V power tap on a separate harness |
| | **ZED 2i front stereo** | USB-C ❻ (after unplugging Mac) OR powered USB-A hub | needs USB 3.0 throughput |
| | **ZED Mini rear** | USB-A ❷/❸ via powered hub | |
| | **u-blox ZED-F9P RTK ×2** | USB-A | dual-antenna for moving baseline |
| | **VectorNav VN-100 IMU** | USB-A | RS-232 over USB |

When sensor count exceeds free USB ports, add a **powered USB 3.0 hub** to USB-A port ❷.

GMSL cameras (Leopard front + 4× e-CAM corners): the Yahboom Super carrier doesn't have FAKRA GMSL connectors. Either swap to USB3 cams or move those sensors to a future AGX Orin Dev Kit (master plan PART A.1 — primary perception compute).

---

## Boot-up sequence (when you finally plug everything together in the cart)

1. Power on the cart (12 V house bus comes alive).
2. Pololu DC-DC steps 12 V to 19 V → Jetson DC barrel ❽. Jetson boots Ubuntu (~30 s).
3. Teensies boot from cart 12 V → idle in `DISENGAGED` state (LED blinking 0.5 Hz).
4. SSH into the Jetson from a laptop, OR plug in monitor + keyboard via HDMI ❼.
5. Run the cart-control stack:
   ```bash
   cd ~/golf-cart-code/Software/autonomy_ws
   source /opt/ros/humble/setup.bash
   source install/setup.bash
   ros2 launch gem_teleop teleop.launch.py
   ```
6. Press the dash **ARM** button → state goes to `ARMED`.
7. Press the dash **ENGAGE** button → state goes to `ACTIVE`. Throttle relay energizes — pedal is now bypassed.
8. Hold **Right Bumper (RB)** on the gamepad as deadman, push left stick + right trigger to drive.

Drive at < 5 mph in an empty parking lot. Foot near the brake pedal. **No autonomous brake yet** — you stop with your foot.

---

## To make the launch start automatically on boot (optional, for unmanned ops later)

```bash
sudo tee /etc/systemd/system/gem-cart-runtime.service <<'EOF'
[Unit]
Description=GEM cart DBW runtime
After=network.target

[Service]
Type=simple
User=jetson
ExecStartPre=/bin/sh -c 'sudo ip link set can0 type can bitrate 500000; sudo ip link set can0 up'
ExecStart=/bin/bash -c 'source /opt/ros/humble/setup.bash; source /home/jetson/golf-cart-code/Software/autonomy_ws/install/setup.bash; ros2 launch gem_teleop teleop.launch.py'
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl enable gem-cart-runtime.service
sudo systemctl start gem-cart-runtime.service
```

Don't enable this until you've verified the manual launch works first.

---

## Verification checklist (run before driving)

```bash
ssh jetson@<jetson-ip>

# 1. CAN interface up
ip -br link show can0
# expect: can0  UP  <NOARP,UP,LOWER_UP,ECHO>

# 2. DBW bridge runs and opens can0
source /opt/ros/humble/setup.bash
source ~/golf-cart-code/Software/autonomy_ws/install/setup.bash
ros2 run gem_dbw_bridge gem_dbw_bridge_node &
# expect: "Opened CAN bus can0 @ 500 kbps"

# 3. With Teensies powered, see their heartbeats
candump can0
# expect: 0x150 (Motion HB) and 0x151 (Pedals HB) every 50 ms,
#         0x140 (E-stop state) every 50 ms

# 4. Gamepad detected
ls /dev/input/js*
ros2 run joy joy_node &
ros2 topic echo /joy --once

# 5. End-to-end: move stick, see CAN frames change
ros2 run gem_teleop joy_to_ackermann_node &
candump -tz can0 | grep -E '110|120|130'
# 0x110 (steer cmd), 0x120 (throttle cmd), 0x130 (brake cmd) update at 50 Hz
```

If any step fails — STOP. Don't engage the system on a moving cart. Diagnose the failed step.
