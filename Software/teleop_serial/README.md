# USB-serial gamepad teleop (`gem_gamepad.py`)

Drive the GEM E4 from a Logitech F710 plugged into the **Jetson**, talking to the
Teensies over **USB serial** — the "drive it now" path before the DBW CAN bus is
wired Jetson↔Teensies.

It sends the *exact* single-character commands the Mac-proven bench firmwares
already accept — **no firmware changes**:

| Teensy | Firmware | Serial commands used |
|---|---|---|
| Steering | `steer_test_teensy` (EPAS18, 0x298 @ 250k) | `a` left · `d` right · `space` center · `x` stop · `.` keepalive |
| Brake | `brake_test_teensy` (Kar-Tech, 0xFF0000 @ 250k) | `w` extend · `s` retract · `e` engage · `x` release · `.` keepalive |

## One-time Jetson setup (already done on this unit)

The F710 must be in **DirectInput mode** — slide the switch on the back to **D**
(XInput needs the `xpad` driver, which this Tegra kernel lacks). Two fixes make
it work and persist across reboot:

- `hid.ignore_special_drivers=1` added to `/boot/extlinux/extlinux.conf` — the
  built-in Logitech HID driver fails to probe the F710 (`probe failed -1`); this
  forces `hid-generic`, which works. (Backup: `extlinux.conf.bak-gamepad`.)
- `joydev` added to `/etc/modules-load.d/joystick.conf` — creates `/dev/input/js0`.

If a future controller misbehaves, the pad still enumerates on USB (`lsusb`) even
when no `js0` appears — that's the driver-binding issue above, not your wiring.

## Calibrate (guided wizard — do this once per controller)

```bash
ssh jetson@192.168.55.1
cd ~/golf-cart-code/Software/teleop_serial
python3 gem_gamepad.py --calibrate
```

It first prints the controller's **full axis/button inventory** (every control,
so adding features later needs no recalibration), then walks you through each
control we use — "push the left stick right", "squeeze LT", etc. — detecting and
saving each to `gem_gamepad_map.json`, which the driver auto-loads. It also
detects whether **LT is analog or a button** and sets braking to match.

## Drive

```bash
python3 gem_gamepad.py            # auto-detects Teensies + gamepad, loads the saved map
```

| Input | Action |
|---|---|
| **Hold the deadman** (RB by default) | Required — nothing actuates unless held |
| Left stick left/right | Steer (hold to keep turning; release to center) |
| **D-pad** left/right | **Micro-steering** — one small step per tap, for fine aim |
| **LT** | Brake. Analog trigger = proportional; button (F710 in D-mode) = ramped: hold longer → more brake |
| **BACK** | **Emergency stop** — stops everything and *latches* off |
| **START** | Clear the e-stop latch |
| Release deadman / quit / unplug | Immediate stop; wheel recenters, brake releases |

## Safety

- **Steering moves the front wheels.** Jack the front axle up or clear the area.
- **Brake is not mechanically coupled to the pedal yet** — the actuator strokes
  in the air, so it does **not** stop the cart. Demonstrates control only.
- **No throttle** — no bench-proven throttle firmware exists, so the gamepad
  can't accelerate the cart. That's the next firmware piece.
- Independent firmware deadmen back you up if this script dies: steering
  recenters + drops to local assist after 3 s of no serial; brake releases
  after 0.8 s. Releasing the deadman or pressing BACK stops things immediately.
