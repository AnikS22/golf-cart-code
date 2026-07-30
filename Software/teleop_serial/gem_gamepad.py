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


def _axis_rest(pad, secs=0.6):
    """Snapshot each axis's resting value (call while the pad is untouched)."""
    end = now() + secs
    vals = {}
    while now() < end:
        pad.poll()
        for n, v in pad.axes.items():
            vals[n] = v
        time.sleep(0.02)
    return vals


def _busy(pad, rest):
    return (any(pad.buttons.values()) or
            any(abs(pad.axis(n) - rest.get(n, 0)) > 8000 for n in pad.axes))


def _wait_idle(pad, rest, need=0.4, timeout=15):
    """Block until nothing is pressed / no axis is deflected, sustained `need` sec."""
    stable = None
    t0 = now()
    while now() - t0 < timeout:
        pad.poll()
        if _busy(pad, rest):
            stable = None
        else:
            stable = stable or now()
            if now() - stable >= need:
                return
        time.sleep(0.02)


def _hold_button(pad, hold=0.30, timeout=25):
    """Return a button index held (alone) for `hold` seconds — rejects transients."""
    cand = since = None
    t0 = now()
    while now() - t0 < timeout:
        pad.poll()
        pressed = [n for n, v in pad.buttons.items() if v]
        if len(pressed) == 1:
            n = pressed[0]
            if cand == n and now() - since >= hold:
                return n
            if cand != n:
                cand, since = n, now()
        else:
            cand = None
        time.sleep(0.02)
    return None


def _hold_axis_or_button(pad, rest, hold=0.35, thresh=14000, timeout=25):
    """Detect a control held for `hold` sec: an axis pushed past `thresh`, OR a
    button. Returns ('axis', idx, sign) or ('button', idx, None)."""
    cand = since = None
    t0 = now()
    while now() - t0 < timeout:
        pad.poll()
        pressed = [n for n, v in pad.buttons.items() if v]
        best = None; bestdev = 0; bestval = 0
        for n, v in pad.axes.items():
            d = abs(v - rest.get(n, 0))
            if d > bestdev:
                bestdev, best, bestval = d, n, v
        key = None
        if len(pressed) == 1 and bestdev < thresh:
            key = ("button", pressed[0], None)
        elif best is not None and bestdev >= thresh:
            key = ("axis", best, 1 if bestval > rest.get(best, 0) else -1)
        if key is not None:
            if cand == key[:2] and now() - since >= hold:
                return key
            if cand != key[:2]:
                cand, since = key[:2], now()
        else:
            cand = None
        time.sleep(0.02)
    return None


def _capture_button(pad, rest, label):
    """Ask for a button, detect a sustained hold, confirm with a second press."""
    while True:
        print(f"\n  >>> {label}")
        print("      Press & HOLD the button you want (any button). Waiting...")
        _wait_idle(pad, rest)
        n = _hold_button(pad)
        if n is None:
            print("      (didn't catch a steady press — let's try again)")
            continue
        print(f"      got button {n}. Release it, then TAP the SAME button to confirm.")
        while pad.button(n):
            pad.poll(); time.sleep(0.02)
        _wait_idle(pad, rest, need=0.2)
        n2 = _hold_button(pad, hold=0.04)
        if n2 == n:
            print(f"      ✓ {label} = button {n}")
            while pad.button(n):
                pad.poll(); time.sleep(0.02)
            return n
        print(f"      that was button {n2}, not {n} — redoing {label}.")
        if n2 is not None:
            while pad.button(n2):
                pad.poll(); time.sleep(0.02)


def calibrate(path):
    print("\n══════════════ GAMEPAD CALIBRATION WIZARD ══════════════")
    inv = None
    try:
        inv = js_inventory(path)
        print(f"Controller: {inv['name']}  ({inv['num_axes']} axes, {inv['num_buttons']} buttons)")
    except OSError as e:
        print(f"(inventory ioctl unavailable: {e})")
    print("\nI'll ask for one control at a time. HOLD it firmly for ~half a second so")
    print("I read it cleanly. You pick which physical buttons you want. Ctrl-C aborts.")
    pad = Gamepad(path)
    m = {}
    if inv:
        m["inventory"] = inv
    rest = _axis_rest(pad)
    try:
        # 1) DEADMAN (button, confirmed)
        m["BTN_DEADMAN"] = _capture_button(pad, rest, "DEADMAN (hold-to-drive; RB is a good pick)")

        # 2) STEERING (axis)
        print("\n  >>> STEERING — push the LEFT THUMBSTICK fully RIGHT and HOLD it there")
        _wait_idle(pad, rest)
        r = _hold_axis_or_button(pad, rest)
        if r and r[0] == "axis":
            m["AXIS_STEER"] = r[1]; m["STEER_INVERT"] = (r[2] < 0)
            print(f"      ✓ steering = axis {r[1]}")
            _wait_idle(pad, rest)

        # 3) D-PAD (axis)
        print("\n  >>> MICRO-STEER — push the D-PAD (the + cross) RIGHT and HOLD it")
        _wait_idle(pad, rest)
        r = _hold_axis_or_button(pad, rest)
        if r and r[0] == "axis":
            m["AXIS_DPAD_X"] = r[1]; m["DPAD_INVERT"] = (r[2] < 0)
            print(f"      ✓ D-pad = axis {r[1]}")
        elif r and r[0] == "button":
            print("      (D-pad reads as buttons here — D-pad micro-steer left as default)")
        _wait_idle(pad, rest)

        # 4) BRAKE (axis analog OR button)
        print("\n  >>> BRAKE — squeeze the LEFT TRIGGER (LT) fully and HOLD it")
        _wait_idle(pad, rest)
        r = _hold_axis_or_button(pad, rest)
        if r and r[0] == "axis":
            m["BRAKE_KIND"] = "axis"; m["BRAKE_INDEX"] = r[1]
            full = pad.axis(r[1]); m["BRAKE_REST"] = rest.get(r[1], 0); m["BRAKE_FULL"] = full
            print(f"      ✓ brake = ANALOG axis {r[1]} (proportional / gradual)")
        elif r and r[0] == "button":
            m["BRAKE_KIND"] = "button"; m["BRAKE_INDEX"] = r[1]
            print(f"      ✓ brake = button {r[1]} (on/off -> software ramp: hold longer = more brake)")
        _wait_idle(pad, rest)

        # 5) E-STOP + 6) CLEAR (buttons, confirmed)
        m["BTN_ESTOP"] = _capture_button(pad, rest, "E-STOP (panic stop; BACK is a good pick)")
        m["BTN_CLEAR"] = _capture_button(pad, rest, "CLEAR (un-latch e-stop; START is a good pick)")
    except KeyboardInterrupt:
        print("\naborted — nothing saved.")
        pad.close()
        return
    finally:
        pad.close()

    tmp = MAP_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(m, f, indent=2)
    os.replace(tmp, MAP_PATH)                     # atomic write -> never a half file
    print("\n──────────── SAVED MAPPING ────────────")
    for k, v in m.items():
        if k == "inventory":
            print(f"  {k:14s} = {v['num_axes']} axes, {v['num_buttons']} buttons (full list stored)")
        else:
            print(f"  {k:14s} = {v}")
    print(f"\n✓ Saved to {MAP_PATH} — this persists; the driver auto-loads it.")

    # Auto-verify: apply the just-saved map and open the live dry-run.
    apply_map(m)
    print("\nLaunching a LIVE CHECK — press each control and confirm the DECODED")
    print("action matches. Nothing moves. Ctrl-C when you're happy.\n")
    time.sleep(1.5)
    test_mode(path)


def monitor(path):
    """Live 'digital twin' of the controller — every axis + button drawn on screen,
    updating in real time. Touch a control, watch which one lights up. No mapping
    needed; nothing actuates. This is the easiest way to read your controller."""
    inv = None
    try:
        inv = js_inventory(path)
    except OSError:
        pass
    ax_names = {a["index"]: a["name"] for a in inv["axes"]} if inv else {}
    bt_names = {b["index"]: b["name"] for b in inv["buttons"]} if inv else {}
    pad = Gamepad(path)
    name = inv["name"] if inv else path
    last = "-"
    prev_ax, prev_bt = {}, {}
    sys.stdout.write("\033[2J")   # clear once
    try:
        while True:
            pad.poll()
            # track last-changed control (helps you identify it)
            for n, v in pad.axes.items():
                if abs(v - prev_ax.get(n, 0)) > 6000:
                    last = f"AXIS {n} ({ax_names.get(n,'?')})"
                prev_ax[n] = v
            for n, v in pad.buttons.items():
                if v and not prev_bt.get(n):
                    last = f"BUTTON {n} ({bt_names.get(n,'?')})"
                prev_bt[n] = v

            lines = [f" CONTROLLER: {name}",
                     f" last touched: {last}", ""]
            for n in sorted(pad.axes):
                v = pad.axis(n)
                pos = int((v / AXIS_MAX + 1) * 10)          # 0..20
                pos = max(0, min(20, pos))
                bar = "".join("┃" if i == pos else ("·" if i == 10 else "─") for i in range(21))
                lines.append(f"  axis {n:2d} [{bar}] {v:+6d}  {ax_names.get(n,'')}")
            lines.append("")
            nbtn = inv["num_buttons"] if inv else (max(pad.buttons) + 1 if pad.buttons else 0)
            cells = []
            for n in range(nbtn):
                cells.append(f"\033[7m {n:2d} \033[0m" if pad.button(n) else f" {n:2d} ")
            lines.append("  buttons (highlighted = pressed):")
            lines.append("   " + " ".join(cells))
            lines.append("")
            lines.append(" Press each control; note its number. Ctrl-C to quit.")
            padded = [l if "\033" in l else l.ljust(78) for l in lines]
            sys.stdout.write("\033[H" + "\n".join(padded) + "\n\033[J")
            sys.stdout.flush()
            time.sleep(0.05)
    except KeyboardInterrupt:
        sys.stdout.write("\033[2J\033[H")
        print("done.")
    finally:
        pad.close()


def test_mode(path):
    """Dry run: show what each control WOULD do, per the saved map. No Teensies,
    nothing actuates — safe way to confirm the mapping is correct."""
    print("\n═══════════ DRY-RUN TEST (nothing moves) ═══════════")
    print(f"  deadman=btn{BTN_DEADMAN}  steer=axis{AXIS_STEER}(inv={STEER_INVERT})  "
          f"dpad=axis{AXIS_DPAD_X}(inv={DPAD_INVERT})")
    print(f"  brake={BRAKE_KIND} {BRAKE_INDEX}  e-stop=btn{BTN_ESTOP}  clear=btn{BTN_CLEAR}")
    print("\n  Push/press ONE control at a time. Check the DECODED action matches")
    print("  what you touched. RAW shows the live axis/button so mismatches are obvious.")
    print("  Ctrl-C to quit.\n")
    pad = Gamepad(path)
    try:
        while True:
            pad.poll()
            acts = []
            if pad.button(BTN_DEADMAN): acts.append("DEADMAN")
            if pad.button(BTN_ESTOP):   acts.append("E-STOP")
            if pad.button(BTN_CLEAR):   acts.append("CLEAR")
            s = pad.axis(AXIS_STEER) / AXIS_MAX
            if STEER_INVERT: s = -s
            if abs(s) > STEER_DEADZONE:
                acts.append(f"STEER {'RIGHT' if s > 0 else 'LEFT'} {abs(s)*100:3.0f}%")
            dx = pad.axis(AXIS_DPAD_X)
            if DPAD_INVERT: dx = -dx
            if dx != 0:
                acts.append(f"D-PAD {'RIGHT' if dx > 0 else 'LEFT'}")
            if BRAKE_KIND == "axis":
                span = float(BRAKE_FULL - BRAKE_REST) or 1.0
                b = max(0.0, min(1.0, (pad.axis(BRAKE_INDEX) - BRAKE_REST) / span))
                if b > BRAKE_DEADZONE:
                    acts.append(f"BRAKE {b*100:3.0f}%")
            elif pad.button(BRAKE_INDEX):
                acts.append("BRAKE (held)")
            raw_ax = " ".join(f"a{n}={v:+6d}" for n, v in sorted(pad.axes.items()) if abs(v) > 8000)
            raw_bt = " ".join(f"b{n}" for n, v in sorted(pad.buttons.items()) if v)
            decoded = ", ".join(acts) if acts else "-"
            print(f"  DECODED: {decoded:38s} | RAW: {raw_ax} [{raw_bt}]".ljust(118)[:118],
                  end="\r", flush=True)
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
    ap.add_argument("--test", action="store_true", help="dry run: show decoded actions, touch nothing")
    ap.add_argument("--monitor", action="store_true", help="live on-screen view of every stick/button")
    ap.add_argument("--js", help="gamepad device (default: first /dev/input/js*)")
    ap.add_argument("--steer", help="steering Teensy serial port (skip auto-detect)")
    ap.add_argument("--brake", help="brake Teensy serial port (skip auto-detect)")
    args = ap.parse_args()

    saved = load_map()
    if saved:
        apply_map(saved)

    if args.calibrate or args.test or args.monitor:
        js = args.js or (sorted(glob.glob("/dev/input/js*")) or [None])[0]
        if not js:
            sys.exit("No /dev/input/js* found. Plug in the gamepad.")
        if args.monitor:
            monitor(js)
        elif args.test:
            test_mode(js)
        else:
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
