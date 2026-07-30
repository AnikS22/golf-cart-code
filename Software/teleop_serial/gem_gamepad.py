#!/usr/bin/env python3
"""gem_gamepad.py — drive the GEM E4 from a USB gamepad over Teensy USB serial.

This is the USB-serial "drive it now" path (before the DBW CAN bus is wired
Jetson<->Teensies). It merges drive.py (steering) + brake.py (brake) under a
gamepad and talks to the SAME bench firmwares the Mac already proved on hardware:

  * steer_test_teensy  — EPAS18, 0x298 @ 250k.  serial: a=left d=right space=center x=stop . =keepalive
  * brake_test_teensy  — Kar-Tech 1A001HAJ.     serial: w=extend s=retract e=engage space=hold x=release . =keepalive

NO firmware changes. This host script only sends those exact single characters,
exactly like drive.py / brake.py, but sourced from a gamepad instead of the keyboard.

  python3 gem_gamepad.py                 # auto-detect Teensies + /dev/input/js0
  python3 gem_gamepad.py --calibrate     # print axis/button numbers for ANY pad
  python3 gem_gamepad.py --js /dev/input/js1 --steer /dev/ttyACM0 --brake /dev/ttyACM1

──────────────────────────── SAFETY — READ FIRST ────────────────────────────
  * STEERING MOVES THE FRONT WHEELS. Jack the front axle up or clear the area.
  * The brake actuator strokes in the air — it is NOT mechanically coupled to
    the pedal yet (CLAUDE.md), so it does NOT stop the cart. It only demonstrates
    actuator control.
  * DEADMAN: nothing actuates unless you HOLD the deadman button (default RB).
    Release it (or quit, or unplug) and both firmwares recenter/release within
    their own deadman windows (steer 3 s, brake 0.8 s) — and this script also
    sends an explicit stop the instant you let go.
  * BACK button = soft E-stop (stops everything, latches off). START re-enables.
  * There is NO throttle here — throttle is not yet bench-proven. Add it later.
"""
import argparse
import glob
import os
import struct
import sys
import time

try:
    import serial  # pyserial 3.5 (present on the Jetson)
except ImportError:
    serial = None  # only needed to talk to the Teensies; --calibrate works without it

# ─── Gamepad mapping (Logitech F710, XInput mode, Linux joydev defaults) ──────
# Run with --calibrate to discover these for a different controller/mode.
AXIS_STEER   = 0    # left stick X   (-left .. +right)
AXIS_BRAKE   = 5    # right trigger  (rest -32767 .. pressed +32767)
BTN_DEADMAN  = 5    # RB — hold to enable actuation
BTN_ESTOP    = 6    # Back — soft e-stop (latches off)
BTN_CLEAR    = 7    # Start — clear e-stop latch

STEER_INVERT = False   # set True if pushing the stick right turns the wheel LEFT
STEER_DEADZONE = 0.14  # stick fraction ignored around center
BRAKE_DEADZONE = 0.06  # trigger fraction below which brake is released
AXIS_MAX     = 32767.0

# ─── Control-loop tuning ─────────────────────────────────────────────────────
TICK_HZ            = 50           # host loop rate
STEER_RATE_MIN_HZ  = 3.0         # nudge rate at the edge of the deadzone
STEER_RATE_MAX_HZ  = 22.0        # nudge rate at full stick deflection
STEER_CENTER_HZ    = 5.0         # 'space' (recenter) rate when stick is centered
BRAKE_RATE_MIN_HZ  = 3.0
BRAKE_RATE_MAX_HZ  = 18.0
KEEPALIVE_HZ       = 5.0         # '.' to each Teensy (well under both deadmen)


def now():
    return time.monotonic()


# ─── Gamepad reader: raw Linux joystick API, no external deps ─────────────────
class Gamepad:
    """Reads /dev/input/jsN using the kernel js_event struct (8 bytes)."""
    EVENT_FMT = "IhBB"           # u32 time, s16 value, u8 type, u8 number
    EVENT_SIZE = struct.calcsize(EVENT_FMT)
    T_BUTTON, T_AXIS, T_INIT = 0x01, 0x02, 0x80

    def __init__(self, path):
        self.path = path
        self.fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        self.axes = {}
        self.buttons = {}

    def poll(self):
        """Drain pending events into self.axes / self.buttons."""
        while True:
            try:
                data = os.read(self.fd, self.EVENT_SIZE)
            except BlockingIOError:
                return
            except OSError:
                return
            if not data or len(data) < self.EVENT_SIZE:
                return
            _t, value, etype, number = struct.unpack(self.EVENT_FMT, data)
            etype &= ~self.T_INIT
            if etype == self.T_AXIS:
                self.axes[number] = value
            elif etype == self.T_BUTTON:
                self.buttons[number] = value

    def axis(self, n, default=0):
        return self.axes.get(n, default)

    def button(self, n):
        return bool(self.buttons.get(n, 0))

    def close(self):
        try:
            os.close(self.fd)
        except OSError:
            pass


def calibrate(path):
    print(f"Reading {path}. Move sticks / press buttons. Ctrl-C to quit.\n")
    pad = Gamepad(path)
    try:
        while True:
            pad.poll()
            axes = " ".join(f"a{n}={v:+6d}" for n, v in sorted(pad.axes.items()))
            btns = " ".join(f"b{n}" for n, v in sorted(pad.buttons.items()) if v)
            print(f"  {axes}   [{btns}]".ljust(110)[:110], end="\r", flush=True)
            time.sleep(0.03)
    except KeyboardInterrupt:
        print("\n")
    finally:
        pad.close()


# ─── Teensy serial wrapper + auto-classification ──────────────────────────────
class Teensy:
    def __init__(self, port, kind):
        self.port = port
        self.kind = kind            # "steer" | "brake"
        self.ser = serial.Serial(port, 115200, timeout=0)
        self.status = ""

    def send(self, ch):
        try:
            self.ser.write(ch.encode() if isinstance(ch, str) else ch)
        except serial.SerialException:
            pass

    def read_status(self):
        """Pull any serial text; keep the latest [st] line for the dashboard."""
        try:
            data = self.ser.read(4096).decode("utf-8", "replace")
        except serial.SerialException:
            return
        for line in data.splitlines():
            if line.startswith("[st]"):
                self.status = line.strip()

    def close(self):
        try:
            self.send("x")          # stop/release on the way out
            self.ser.flush()
            time.sleep(0.05)
            self.ser.close()
        except serial.SerialException:
            pass


def classify_port(port, listen_s=2.0):
    """Open a Teensy port and sniff its [st]/banner lines to tell steer vs brake."""
    try:
        s = serial.Serial(port, 115200, timeout=0)
    except serial.SerialException as e:
        print(f"  {port}: cannot open ({e})")
        return None
    kind = None
    t0 = now()
    buf = ""
    while now() - t0 < listen_s and kind is None:
        try:
            buf += s.read(4096).decode("utf-8", "replace")
        except serial.SerialException:
            break
        up = buf.upper()
        if "EPAS" in up or "STEERING" in up:
            kind = "steer"
        elif "KT " in up or "KAR-TECH" in up or "[BRAKE]" in up:
            kind = "brake"
        time.sleep(0.02)
    s.close()
    return kind


def autodetect(explicit_steer, explicit_brake, explicit_js):
    # Serial ports
    teensies = {}
    if explicit_steer:
        teensies["steer"] = Teensy(explicit_steer, "steer")
    if explicit_brake:
        teensies["brake"] = Teensy(explicit_brake, "brake")

    if not (explicit_steer and explicit_brake):
        ports = sorted(set(glob.glob("/dev/ttyACM*")) -
                       {t.port for t in teensies.values()})
        if ports:
            print(f"Sniffing {len(ports)} serial port(s) to identify firmware...")
        for p in ports:
            kind = classify_port(p)
            if kind and kind not in teensies:
                print(f"  {p}  ->  {kind}")
                teensies[kind] = Teensy(p, kind)
            elif kind:
                print(f"  {p}  ->  {kind} (duplicate, ignored)")
            else:
                print(f"  {p}  ->  unknown (no EPAS/KT status seen; skipped)")

    # Gamepad
    js = explicit_js
    if not js:
        cands = sorted(glob.glob("/dev/input/js*"))
        js = cands[0] if cands else None
    return teensies, js


# ─── Main teleop loop ─────────────────────────────────────────────────────────
def rate_gate(state_key, hz, times):
    """Return True at most `hz` times/sec for the given key."""
    t = now()
    if t - times.get(state_key, 0.0) >= 1.0 / hz:
        times[state_key] = t
        return True
    return False


def main():
    ap = argparse.ArgumentParser(description="GEM E4 gamepad teleop over Teensy USB serial")
    ap.add_argument("--calibrate", action="store_true", help="print gamepad axis/button numbers and exit")
    ap.add_argument("--js", help="gamepad device (default: first /dev/input/js*)")
    ap.add_argument("--steer", help="steering Teensy serial port (skip auto-detect)")
    ap.add_argument("--brake", help="brake Teensy serial port (skip auto-detect)")
    args = ap.parse_args()

    if args.calibrate:
        js = args.js or (sorted(glob.glob("/dev/input/js*")) or [None])[0]
        if not js:
            sys.exit("No /dev/input/js* found. Plug in the gamepad.")
        calibrate(js)
        return

    if serial is None:
        sys.exit("pyserial not found. Install it (the Jetson already has it): pip3 install pyserial")

    teensies, js = autodetect(args.steer, args.brake, args.js)

    if not teensies:
        sys.exit("No steering/brake Teensy found on /dev/ttyACM*. Plug them in "
                 "(and check they run the steer_test / brake_test firmware).")
    if not js:
        for t in teensies.values():
            t.close()
        sys.exit("No /dev/input/js* found. Plug in the gamepad. "
                 "(If it's plugged in but missing, you may need the 'input' group.)")

    steer = teensies.get("steer")
    brake = teensies.get("brake")
    print("\n─── GEM E4 gamepad teleop ───")
    print(f"  gamepad : {js}")
    print(f"  steer   : {steer.port if steer else '(none — no steering)'}")
    print(f"  brake   : {brake.port if brake else '(none — no brake)'}")
    print(f"  HOLD button {BTN_DEADMAN} (RB) to enable. BACK=e-stop  START=clear.")
    print("  WHEELS WILL MOVE. Front axle up or area clear.\n")

    pad = Gamepad(js)
    times = {}
    estop_latched = False
    prev_deadman = False
    prev_buttons = {}
    last_dash = 0.0

    try:
        while True:
            loop_t0 = now()
            pad.poll()

            # ── edge-detected buttons ──
            estop = pad.button(BTN_ESTOP)
            clear = pad.button(BTN_CLEAR)
            if estop and not prev_buttons.get(BTN_ESTOP):
                estop_latched = True
            if clear and not prev_buttons.get(BTN_CLEAR):
                estop_latched = False
            prev_buttons[BTN_ESTOP] = estop
            prev_buttons[BTN_CLEAR] = clear

            deadman = pad.button(BTN_DEADMAN) and not estop_latched
            engaged = deadman

            # ── falling edge: force stop the instant the driver lets go ──
            if prev_deadman and not deadman:
                if steer:
                    steer.send("x")
                if brake:
                    brake.send("x")
            prev_deadman = deadman

            if engaged:
                # ── STEERING ──
                if steer:
                    raw = pad.axis(AXIS_STEER) / AXIS_MAX
                    if STEER_INVERT:
                        raw = -raw
                    mag = abs(raw)
                    if mag < STEER_DEADZONE:
                        if rate_gate("steer_center", STEER_CENTER_HZ, times):
                            steer.send(" ")            # recenter, stay engaged
                    else:
                        frac = (mag - STEER_DEADZONE) / (1.0 - STEER_DEADZONE)
                        hz = STEER_RATE_MIN_HZ + frac * (STEER_RATE_MAX_HZ - STEER_RATE_MIN_HZ)
                        if rate_gate("steer_nudge", hz, times):
                            steer.send("d" if raw > 0 else "a")   # d=right a=left
                    if rate_gate("steer_ka", KEEPALIVE_HZ, times):
                        steer.send(".")

                # ── BRAKE (strokes the actuator; not coupled to pedal yet) ──
                if brake:
                    # RT rests at -1, full press = +1 -> map to 0..1
                    b = (pad.axis(AXIS_BRAKE) / AXIS_MAX + 1.0) * 0.5
                    if b < BRAKE_DEADZONE:
                        if rate_gate("brake_rel", 4.0, times):
                            brake.send("x")            # release, shaft free
                    else:
                        brake.send("e") if rate_gate("brake_eng", 2.0, times) else None
                        frac = (b - BRAKE_DEADZONE) / (1.0 - BRAKE_DEADZONE)
                        hz = BRAKE_RATE_MIN_HZ + frac * (BRAKE_RATE_MAX_HZ - BRAKE_RATE_MIN_HZ)
                        if rate_gate("brake_nudge", hz, times):
                            brake.send("w")            # extend = more brake
                    if rate_gate("brake_ka", KEEPALIVE_HZ, times):
                        brake.send(".")

            # ── telemetry + dashboard ──
            for t in teensies.values():
                t.read_status()
            if now() - last_dash >= 0.2:
                last_dash = now()
                state = "E-STOP" if estop_latched else ("DRIVE" if engaged else "idle ")
                line = f"[{state}] "
                if steer:
                    line += f"STEER {steer.status[5:70] if steer.status else '...'} | "
                if brake:
                    line += f"BRAKE {brake.status[5:60] if brake.status else '...'}"
                print("  " + line[:150].ljust(150), end="\r", flush=True)

            dt = now() - loop_t0
            if dt < 1.0 / TICK_HZ:
                time.sleep(1.0 / TICK_HZ - dt)
    except KeyboardInterrupt:
        pass
    finally:
        pad.close()
        for t in teensies.values():
            t.close()
        print("\n\nstopped — steering local, brake released.")


if __name__ == "__main__":
    main()
