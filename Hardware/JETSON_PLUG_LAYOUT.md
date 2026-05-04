# Jetson — where to plug everything in

Yahboom Jetson Orin NX Super dev kit on `192.168.55.1` (over USB-C to your Mac, currently). Below: every cable you'll plug in for the cart project, in priority order, with which port to use.

## What's confirmed on the board (from probing it)

```
eno1            Ethernet (RJ45, gigabit)        — currently DOWN, no cable
wlP1p1s0        Wi-Fi 802.11 a/b/g/n/ac         — built-in M.2 module
can0            CAN bus (kernel-level)          — needs external transceiver to be useful
9× I²C buses    /dev/i2c-{0-11}                  — exposed on 40-pin GPIO header
HDMI/DP         Display output                   — for direct GUI use (optional)
USB-A × 4       USB 3.0 Type-A                   — peripherals
USB-C × 1       USB 3.0 Type-C (data + power)    — currently your link to my Mac; switch to barrel-jack power once standalone
40-pin header   GPIO + I²C + SPI + UART          — for sensors, custom hardware
```

## Phase 0 — first-light cart drive (gamepad teleop, no autonomy)

You only need 4 things plugged in:

| # | Device | Plug into | Notes |
|---|---|---|---|
| 1 | **Logitech F710 USB receiver** | any **USB-A** port | drives `/joy` topic via `joy_node` |
| 2 | **CANable 2.0 USB→CAN dongle** | any **USB-A** port | the bridge to the Teensies on the cart's DBW CAN bus. You'll see it as `can0` in SocketCAN once driver loads. |
| 3 | **DC power** | **DC barrel jack** | when standalone in the cart. ~19V 4A. Until then, USB-C from the Mac gives power+data. |
| 4 | **Internet (during dev only)** | **`eno1` Ethernet** OR **Wi-Fi** | needed for apt/colcon; not needed once installed. Ethernet is more reliable. |

Optional but useful:
| # | Device | Plug into | Notes |
|---|---|---|---|
| 5 | HDMI monitor | **HDMI** port | direct GUI; saves you from SSH'ing every time |
| 6 | USB keyboard + mouse | spare USB-A ports | only if using HDMI; otherwise SSH |

## Phase 1 — sensors come online (Week 5+)

Add as the parts arrive:

| Sensor | Plug into | Why this port |
|---|---|---|
| **Livox Mid-360 LiDAR** | `eno1` Ethernet (via PoE injector or 12V tap) | streams 70+ MB/s of point-cloud data; needs Gigabit |
| **ZED 2i front stereo** | **USB-C** | needs USB 3 bandwidth for 1080p stereo |
| **ZED Mini rear** | **USB-A** USB 3 | smaller bandwidth |
| **Leopard IMX390 GMSL front** | needs a **GMSL deserializer carrier** (Hawk dev kit) — likely doesn't fit Yahboom carrier cleanly. May need to bridge through an Orin NX with GMSL camera support carrier (ConnectTech Boson, etc.) |
| **e-CAM130 corner cams ×4** | same GMSL carrier issue | OR substitute USB3 cams; one per powered USB hub |
| **u-blox ZED-F9P RTK** | any **USB-A** | 9600 baud, low bandwidth |
| **VectorNav VN-100 IMU** | **USB-A** | 200 Hz IMU stream is fine on USB |

GMSL note: the Yahboom Super carrier doesn't have FAKRA GMSL connectors. If we keep Leopard + e-CAM corners, we'll either swap the carrier (ConnectTech Boson + the same Orin NX module) or substitute USB3 cams in those positions. Decide before Tier-3 buy.

## Phase 2+ — autonomy stack scales out

When the autonomy load grows past what one Orin NX can handle, the master plan adds an **AGX Orin 64GB** as the perception/planning workhorse and reuses this Orin NX as the safety supervisor + logger. Plug them together via Gigabit Ethernet (need a small switch), keep `can0` to one of them only, share clocks via PTP if possible.

## CAN (key insight from probing)

Your Yahboom carrier has a **kernel-level `can0` interface already enabled.** Two implications:

1. **You may not need CANable 2.0.** If the Yahboom exposes CAN-H/CAN-L on the 40-pin header (most do — verify pinout in Yahboom docs), you can wire directly to the DBW CAN bus through a tiny CAN transceiver (MCP2562 or SN65HVD230, ~$5). Saves $45 and one USB port.
2. To enable: `sudo ip link set can0 up type can bitrate 500000` (matches our DBW protocol). Test with `candump can0`.

If using CANable 2.0 anyway: it'll show as `can1` (or rename it) once plugged into USB.

## Power notes

- **Until the cart is wired**: keep USB-C from your Mac — that's powering the Jetson now. (~15 W is enough for idle.)
- **In the cart**: 19 V 4 A through the DC barrel jack, fed from a step-down (e.g., Pololu D24V50F19 from the 12 V aux rail). Don't try to USB-C-power off the cart's 12 V — the Jetson's USB-C wants USB-PD.
- **Peak load**: full sensor + perception load can pull 25 W. Size the DC-DC for 30 W headroom.

## Display options

- **No display**: SSH from your Mac (current setup) is fine for development. RViz/Gazebo render to virtual display, you connect via Foxglove WebSocket or X11 forwarding.
- **HDMI monitor in the cart**: easier for live debugging during test drives. Plug into HDMI on the carrier.
- **Tablet HMI** (master plan Phase 2): connect the Jetson and a 10" Android tablet to the same Wi-Fi; tablet runs Foxglove Studio pointing at the Jetson's IP.

## Verification — once everything's plugged in

```bash
ssh jetson@<jetson-ip>
ls /dev/input/js*               # should show js0 if F710 dongle plugged in
ls /dev/ttyACM* /dev/ttyUSB*    # should show CANable as ttyACM0 (or similar)
ip link show can0               # should show CAN device, possibly DOWN until configured
sudo ip link set can0 up type can bitrate 500000
candump can0                    # should see DBW CAN traffic once Teensies are powered
```
