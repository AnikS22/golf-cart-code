# USB-serial gamepad teleop (`gem_gamepad.py`)

Drive the GEM E4 from a Logitech gamepad plugged into the **Jetson**, talking to
the two Teensies over **USB serial** — the "drive it now" path before the DBW CAN
bus is wired Jetson↔Teensies.

It sends the *exact* single-character commands the Mac-proven bench firmwares
already accept — **no firmware changes**:

| Teensy | Firmware | Serial commands used |
|---|---|---|
| Steering | `steer_test_teensy` (EPAS18, 0x298 @ 250k) | `a` left · `d` right · `space` center · `x` stop · `.` keepalive |
| Brake | `brake_test_teensy` (Kar-Tech, 0xFF0000 @ 250k) | `w` extend · `s` retract · `e` engage · `x` release · `.` keepalive |

It's `drive.py` + `brake.py` merged and fed from the gamepad instead of the keyboard.

## Wiring

- Both Teensies → Jetson USB (they enumerate as `/dev/ttyACM0`, `/dev/ttyACM1`).
- Logitech F710 receiver → Jetson USB (enumerates as `/dev/input/js0`).
- The script **auto-detects** which ttyACM is steering vs brake by sniffing each
  board's status line (`EPAS` = steering, `KT` = brake).

## Run (on the Jetson)

```bash
cd ~/golf-cart-code/Software/teleop_serial
python3 gem_gamepad.py            # auto-detect Teensies + gamepad
```

First time only, so the user can read the joystick:
```bash
sudo usermod -aG input $USER && echo "log out/in (or reboot) to apply"
```

Different controller or F710 mode switch changed the mapping? Discover it:
```bash
python3 gem_gamepad.py --calibrate   # move sticks / press buttons; note the numbers
```
then edit the `AXIS_*` / `BTN_*` constants at the top of `gem_gamepad.py`.

## Controls (F710, XInput mode — the little switch on the back = **X**)

| Input | Action |
|---|---|
| **Hold RB** (deadman) | **Required** — nothing actuates unless held |
| Left stick X | Steer (hold to keep turning; release to center) |
| Right trigger (RT) | Brake actuator stroke (extend = more brake) |
| **BACK** | **Emergency stop** — stops everything and *latches* off |
| **START** | Clear the e-stop latch (re-enable) |
| Release RB / quit / unplug | Immediate stop; wheel recenters, brake releases |

## Safety

- **Steering moves the front wheels.** Jack the front axle up or clear the area
  for first tests.
- **Brake is not mechanically coupled to the pedal yet** — the actuator strokes
  in the air, so it does **not** stop the cart. This only demonstrates control.
- **No throttle** — there is no bench-proven throttle firmware, so the gamepad
  can't make the cart accelerate. Add that firmware next.
- Two independent deadmen back you up if this script dies: steering recenters +
  drops to local power-assist after 3 s of no serial; the brake releases after
  0.8 s. Releasing RB or the BACK button stops things immediately.
