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
import fcntl
import glob
import json
import os
import struct
import sys
import time

MAP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gem_gamepad_map.json")

try:
    import serial  # pyserial 3.5 (present on the Jetson)
except ImportError:
    serial = None  # only needed to talk to the Teensies; --calibrate works without it

# ─── Gamepad mapping — DEFAULTS. `--calibrate` overwrites these into
#     gem_gamepad_map.json, which the driver auto-loads at startup. ─────────────
AXIS_STEER   = 0        # left stick left/right
AXIS_DPAD_X  = 4        # D-pad left/right — micro-steering
BTN_DEADMAN  = 5        # hold to enable actuation
BTN_ESTOP    = 6        # e-stop (latches off)
BTN_CLEAR    = 7        # clear e-stop latch
STEER_INVERT = False    # True if pushing the stick right turns the wheel LEFT
DPAD_INVERT  = False    # True if D-pad right nudges the wheel LEFT

# Brake input can be an analog trigger (proportional) OR a digital button
# (software-ramped so it still feels gradual). --calibrate sets which.
BRAKE_KIND   = "axis"   # "axis" | "button"
BRAKE_INDEX  = 2        # axis number (analog) or button number (digital)
BRAKE_REST   = -32767   # analog only: raw value at rest
BRAKE_FULL   = 32767    # analog only: raw value fully pressed
BRAKE_RAMP_IN_PER_S  = 0.9   # button brake: brake fraction added per sec while held
BRAKE_RAMP_OUT_PER_S = 2.5   # button brake: released per sec when let go

STEER_DEADZONE = 0.14   # stick fraction ignored around center
BRAKE_DEADZONE = 0.06   # brake fraction below which the brake is fully released
AXIS_MAX     = 32767.0

# ─── Control-loop tuning ─────────────────────────────────────────────────────
TICK_HZ            = 50           # host loop rate
STEER_RATE_MIN_HZ  = 3.0         # stick nudge rate at the edge of the deadzone
STEER_RATE_MAX_HZ  = 22.0        # stick nudge rate at full deflection
STEER_CENTER_HZ    = 5.0         # 'space' (recenter) rate when stick is centered
DPAD_STEER_HZ      = 6.0         # D-pad fine-nudge rate (one 6-bit step each)
KEEPALIVE_HZ       = 5.0         # '.' to each Teensy (well under both deadmen)

# Brake is proportional to LT: LT travel maps to an actuator target position.
# The actuator's usable stroke is ~0.05"..2.95"; we drive a safe band and let
# the host converge the firmware's target (parsed from its status line) to it.
BRAKE_MIN_IN  = 0.10   # LT just past deadzone  -> light brake
BRAKE_MAX_IN  = 2.50   # LT fully pressed       -> hard brake (within 2.95 limit)
BRAKE_HYST_IN = 0.08   # convergence hysteresis (~ one 0.1" step)


def now():
    return time.monotonic()


def _parse_after(line, token):
    """Return the float immediately after `token` in `line` (e.g. 'tgt=1.20in')."""
    i = line.find(token)
    if i < 0:
        return None
    j = i + len(token)
    k = j
    while k < len(line) and (line[k].isdigit() or line[k] in "+-."):
        k += 1
    try:
        return float(line[j:k])
    except ValueError:
        return None


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


# ─── Full controller inventory via the Linux joystick ioctls ─────────────────
# Records EVERY axis and button the pad exposes (not just the ones we use), so
# adding controls later needs no recalibration.
def _IOR(nr, size):
    return (2 << 30) | (size << 16) | (0x6A << 8) | nr  # _IOC(READ,'j',nr,size)

_ABS_NAMES = {0: "X (L-stick X)", 1: "Y (L-stick Y)", 2: "Z (L-trigger?)",
              3: "RX (R-stick X)", 4: "RY (R-stick Y)", 5: "RZ (R-trigger?)",
              6: "THROTTLE", 7: "RUDDER", 0x10: "HAT0X (D-pad X)", 0x11: "HAT0Y (D-pad Y)"}
_BTN_NAMES = {0x120: "TRIGGER", 0x130: "A/South", 0x131: "B/East", 0x133: "X/North",
              0x134: "Y/West", 0x136: "LB", 0x137: "RB", 0x138: "LT", 0x139: "RT",
              0x13A: "BACK/SELECT", 0x13B: "START", 0x13C: "MODE",
              0x13D: "L-stick click", 0x13E: "R-stick click"}


def js_inventory(path):
    """Return {name, num_axes, num_buttons, axes[], buttons[]} for the pad."""
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    try:
        b1 = bytearray(1)
        fcntl.ioctl(fd, _IOR(0x11, 1), b1); naxes = b1[0]
        fcntl.ioctl(fd, _IOR(0x12, 1), b1); nbtn = b1[0]
        nm = bytearray(128)
        try:
            fcntl.ioctl(fd, _IOR(0x13, 128), nm)
            devname = nm.split(b"\x00", 1)[0].decode("utf-8", "replace")
        except OSError:
            devname = "?"
        axmap = bytearray(64)                       # ABS_CNT
        fcntl.ioctl(fd, _IOR(0x32, 64), axmap)      # JSIOCGAXMAP
        btnbuf = bytearray(512 * 2)                 # (KEY_MAX-BTN_MISC+1) u16
        fcntl.ioctl(fd, _IOR(0x34, 512 * 2), btnbuf)  # JSIOCGBTNMAP
        btncodes = struct.unpack("<512H", bytes(btnbuf))
        axes = [{"index": i, "code": axmap[i],
                 "name": _ABS_NAMES.get(axmap[i], f"0x{axmap[i]:x}")} for i in range(naxes)]
        buttons = [{"index": i, "code": btncodes[i],
                    "name": _BTN_NAMES.get(btncodes[i], f"0x{btncodes[i]:x}")} for i in range(nbtn)]
        return {"name": devname, "num_axes": naxes, "num_buttons": nbtn,
                "axes": axes, "buttons": buttons}
    finally:
        os.close(fd)


def load_map():
    try:
        with open(MAP_PATH) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def apply_map(m):
    """Override the module-level mapping globals from a saved map dict."""
    g = globals()
    for k in ("AXIS_STEER", "AXIS_DPAD_X", "BTN_DEADMAN", "BTN_ESTOP", "BTN_CLEAR",
              "STEER_INVERT", "DPAD_INVERT", "BRAKE_KIND", "BRAKE_INDEX",
              "BRAKE_REST", "BRAKE_FULL"):
        if k in m:
            g[k] = m[k]


def _settle(pad, secs):
    end = now() + secs
    while now() < end:
        pad.poll()
        time.sleep(0.02)


def _capture_control(pad, prompt, want):
    """Guide the user to actuate ONE control; detect and return its mapping.
    want: 'button' | 'axis' (bipolar/analog) — 'axis' also accepts a button fallback.
    Returns a dict describing what was detected."""
    print(f"\n>>> {prompt}")
    print("    (waiting... do it now)")
    _settle(pad, 0.4)                         # let go of the previous control
    rest = dict(pad.axes)                      # baseline axis values
    prev_btn = dict(pad.buttons)
    peak = {}                                  # axis -> (max_abs_dev, value_at_peak)
    t0 = now()
    while now() - t0 < 12.0:
        pad.poll()
        # button edge?
        for n, v in pad.buttons.items():
            if v and not prev_btn.get(n):
                # confirm + wait for release
                print(f"    detected BUTTON {n}")
                twait = now()
                while now() - twait < 3.0 and pad.button(n):
                    pad.poll(); time.sleep(0.02)
                return {"type": "button", "index": n}
        prev_btn = dict(pad.buttons)
        # axis deviation
        for n, v in pad.axes.items():
            dev = abs(v - rest.get(n, 0))
            if dev > peak.get(n, (0, 0))[0]:
                peak[n] = (dev, v)
        if peak:
            bn, (bdev, bval) = max(peak.items(), key=lambda kv: kv[1][0])
            # full press seen AND control returned toward rest -> lock it in
            if bdev > 15000 and abs(pad.axis(bn) - rest.get(bn, 0)) < 6000:
                sign = 1 if bval > rest.get(bn, 0) else -1
                print(f"    detected AXIS {bn} (rest {rest.get(bn,0):+d}, full {bval:+d})")
                return {"type": "axis", "index": bn, "rest": rest.get(bn, 0),
                        "full": bval, "sign": sign}
        time.sleep(0.02)
    print("    (timed out — skipped; you can re-run --calibrate)")
    return None


def calibrate(path):
    print("\n══════════════ GAMEPAD CALIBRATION WIZARD ══════════════")
    # Full hardware inventory first — records ALL axes/buttons for future use.
    inv = None
    try:
        inv = js_inventory(path)
        print(f"Controller: {inv['name']}  ({inv['num_axes']} axes, {inv['num_buttons']} buttons)")
        print("  axes:    " + ", ".join(f"{a['index']}:{a['name']}" for a in inv["axes"]))
        print("  buttons: " + ", ".join(f"{b['index']}:{b['name']}" for b in inv["buttons"]))
    except OSError as e:
        print(f"(inventory ioctl unavailable: {e})")
    print("\nNow I'll assign the controls we use. Do ONLY the named one, fully,")
    print("then let go. Ctrl-C to abort.\n")
    pad = Gamepad(path)
    m = {}
    if inv:
        m["inventory"] = inv
    try:
        r = _capture_control(pad, "HOLD the button you want as DEADMAN (right bumper, RB), then release", "button")
        if r and r["type"] == "button":
            m["BTN_DEADMAN"] = r["index"]

        r = _capture_control(pad, "Push the LEFT STICK fully to the RIGHT, then let it center", "axis")
        if r and r["type"] == "axis":
            m["AXIS_STEER"] = r["index"]
            m["STEER_INVERT"] = (r["sign"] < 0)     # right should read positive

        r = _capture_control(pad, "Press the D-PAD RIGHT edge (the + cross on the left), then release", "axis")
        if r and r["type"] == "axis":
            m["AXIS_DPAD_X"] = r["index"]
            m["DPAD_INVERT"] = (r["sign"] < 0)
        elif r and r["type"] == "button":
            print("    (D-pad reads as buttons on this pad — micro-steer via D-pad disabled)")

        r = _capture_control(pad, "Squeeze the LEFT TRIGGER (LT) all the way, then release — this is BRAKE", "axis")
        if r and r["type"] == "axis":
            m["BRAKE_KIND"] = "axis"; m["BRAKE_INDEX"] = r["index"]
            m["BRAKE_REST"] = r["rest"]; m["BRAKE_FULL"] = r["full"]
            print("    LT is ANALOG -> proportional (gradual) braking. ")
        elif r and r["type"] == "button":
            m["BRAKE_KIND"] = "button"; m["BRAKE_INDEX"] = r["index"]
            print("    LT is ON/OFF -> software-ramped braking (hold longer = more brake).")

        r = _capture_control(pad, "Press the BACK button (E-STOP)", "button")
        if r and r["type"] == "button":
            m["BTN_ESTOP"] = r["index"]

        r = _capture_control(pad, "Press the START button (clear e-stop)", "button")
        if r and r["type"] == "button":
            m["BTN_CLEAR"] = r["index"]
    except KeyboardInterrupt:
        print("\naborted — nothing saved.")
        pad.close()
        return
    finally:
        pad.close()

    with open(MAP_PATH, "w") as f:
        json.dump(m, f, indent=2)
    print("\n──────────── SAVED MAPPING ────────────")
    for k, v in m.items():
        if k == "inventory":
            print(f"  {k:14s} = {v['num_axes']} axes, {v['num_buttons']} buttons (full list stored)")
        else:
            print(f"  {k:14s} = {v}")
    print(f"\nWritten to {MAP_PATH}")
    print("The driver will load this automatically. Run:  python3 gem_gamepad.py\n")


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
        """Pull any serial text; keep the latest [st] line for the dashboard.
        For the brake board also parse its reported target position (inches)."""
        try:
            data = self.ser.read(4096).decode("utf-8", "replace")
        except serial.SerialException:
            return
        for line in data.splitlines():
            if line.startswith("[st]"):
                self.status = line.strip()
                if self.kind == "brake":
                    self.tgt_in = _parse_after(line, "tgt=")

    tgt_in = None   # brake board's current firmware target (inches), from [st]

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
    ap.add_argument("--calibrate", action="store_true", help="run the guided mapping wizard and save it")
    ap.add_argument("--js", help="gamepad device (default: first /dev/input/js*)")
    ap.add_argument("--steer", help="steering Teensy serial port (skip auto-detect)")
    ap.add_argument("--brake", help="brake Teensy serial port (skip auto-detect)")
    args = ap.parse_args()

    saved = load_map()
    if saved:
        apply_map(saved)

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
    print(f"  mapping : {'gem_gamepad_map.json' if saved else 'DEFAULTS (run --calibrate!)'}")
    print(f"  steer   : {steer.port if steer else '(none — no steering)'}")
    print(f"  brake   : {brake.port if brake else '(none — no brake)'}  "
          f"[{BRAKE_KIND} brake on {'axis' if BRAKE_KIND=='axis' else 'button'} {BRAKE_INDEX}]")
    print(f"  HOLD button {BTN_DEADMAN} (deadman) to enable. "
          f"button {BTN_ESTOP}=E-STOP  button {BTN_CLEAR}=clear.")
    if not saved:
        print("  WARNING: no saved mapping — buttons/axes may be wrong. Run --calibrate first.")
    print("  WHEELS WILL MOVE. Front axle up or area clear.\n")

    pad = Gamepad(js)
    times = {}
    estop_latched = False
    prev_deadman = False
    prev_buttons = {}
    last_dash = 0.0
    brake_level = 0.0      # software-ramped brake fraction (button-brake mode)
    last_t = now()

    try:
        while True:
            loop_t0 = now()
            dt = loop_t0 - last_t
            last_t = loop_t0
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
                # ── STEERING (left stick coarse; D-pad fine) ──
                if steer:
                    raw = pad.axis(AXIS_STEER) / AXIS_MAX
                    if STEER_INVERT:
                        raw = -raw
                    mag = abs(raw)
                    dx = pad.axis(AXIS_DPAD_X)
                    if DPAD_INVERT:
                        dx = -dx
                    if mag >= STEER_DEADZONE:
                        frac = (mag - STEER_DEADZONE) / (1.0 - STEER_DEADZONE)
                        hz = STEER_RATE_MIN_HZ + frac * (STEER_RATE_MAX_HZ - STEER_RATE_MIN_HZ)
                        if rate_gate("steer_nudge", hz, times):
                            steer.send("d" if raw > 0 else "a")   # d=right a=left
                    elif dx != 0:
                        if rate_gate("dpad_steer", DPAD_STEER_HZ, times):
                            steer.send("d" if dx > 0 else "a")    # fine micro-step
                    else:
                        if rate_gate("steer_center", STEER_CENTER_HZ, times):
                            steer.send(" ")            # recenter, stay engaged
                    if rate_gate("steer_ka", KEEPALIVE_HZ, times):
                        steer.send(".")

                # ── BRAKE (analog trigger = proportional; button = software ramp) ──
                if brake:
                    if BRAKE_KIND == "axis":
                        span = float(BRAKE_FULL - BRAKE_REST) or 1.0
                        b = (pad.axis(BRAKE_INDEX) - BRAKE_REST) / span
                        b = max(0.0, min(1.0, b))
                    else:                              # digital button: hold longer = more brake
                        if pad.button(BRAKE_INDEX):
                            brake_level = min(1.0, brake_level + BRAKE_RAMP_IN_PER_S * dt)
                        else:
                            brake_level = max(0.0, brake_level - BRAKE_RAMP_OUT_PER_S * dt)
                        b = brake_level
                    if b < BRAKE_DEADZONE:
                        if rate_gate("brake_rel", 4.0, times):
                            brake.send("x")            # release, shaft free
                    else:
                        if rate_gate("brake_eng", 3.0, times):
                            brake.send("e")            # keep clutch+motor engaged
                        frac = (b - BRAKE_DEADZONE) / (1.0 - BRAKE_DEADZONE)
                        want_in = BRAKE_MIN_IN + frac * (BRAKE_MAX_IN - BRAKE_MIN_IN)
                        cur_in = brake.tgt_in
                        if cur_in is None:             # no telemetry yet -> creep toward brake
                            if rate_gate("brake_conv", 8.0, times):
                                brake.send("w")
                        elif want_in > cur_in + BRAKE_HYST_IN:
                            if rate_gate("brake_conv", 15.0, times):
                                brake.send("w")        # extend = more brake
                        elif want_in < cur_in - BRAKE_HYST_IN:
                            if rate_gate("brake_conv", 15.0, times):
                                brake.send("s")        # retract = less brake
                    if rate_gate("brake_ka", KEEPALIVE_HZ, times):
                        brake.send(".")
            else:
                brake_level = max(0.0, brake_level - BRAKE_RAMP_OUT_PER_S * dt)

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
