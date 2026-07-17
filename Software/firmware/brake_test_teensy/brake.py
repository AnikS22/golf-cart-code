#!/usr/bin/env python3
"""Drive the GEM E4 Kar-Tech brake actuator by keyboard.

Talks to brake_test_teensy on the Motion Teensy (0x18FF0000 @ 250k, J1939).

    python3 brake.py            # auto-finds the Teensy
    python3 brake.py /dev/cu.usbmodemXXXX

Keys:  w / ↑ extend   s / ↓ retract   e engage   space hold   x release   q quit

Sends a keepalive so if this script quits or USB drops, the firmware releases the
clutch (shaft free) within ~0.8 s. BENCH tool: the actuator should be uncoupled
or the brake linkage clear before you move it.
"""
import sys, time, glob, termios, tty, select
import serial  # pyserial (already installed)

def find_port():
    if len(sys.argv) > 1:
        return sys.argv[1]
    ports = glob.glob("/dev/cu.usbmodem*") + glob.glob("/dev/ttyACM*")
    if not ports:
        sys.exit("No Teensy found. Plug it in, or pass the port explicitly.")
    return ports[0]

def main():
    port = find_port()
    ser = serial.Serial(port, 115200, timeout=0)
    print(f"connected {port}\r")
    print("  w/↑ extend   s/↓ retract   e engage   space hold   x release   q quit\r")

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    tty.setcbreak(fd)                       # single keys, no Enter
    last_keepalive = 0.0
    status = ""
    try:
        while True:
            r, _, _ = select.select([fd], [], [], 0.02)
            if r:
                ch = sys.stdin.read(1)
                if ch == "\x1b":            # arrow keys: ESC [ A/B
                    seq = sys.stdin.read(2) if select.select([fd], [], [], 0.01)[0] else ""
                    if seq == "[A": ser.write(b"w")     # up = extend
                    elif seq == "[B": ser.write(b"s")   # down = retract
                elif ch in ("q", "\x03"):   # q or Ctrl-C
                    break
                elif ch in ("w", "s", "e", "x", " "):
                    ser.write(ch.encode())

            now = time.time()
            if now - last_keepalive > 0.3:  # keepalive well under the 0.8s deadman
                ser.write(b".")
                last_keepalive = now

            data = ser.read(4096).decode("utf-8", "replace")
            for line in data.splitlines():
                if line.startswith("[st]"):
                    status = line
                elif line.strip():
                    print(line + "\r")      # RELEASE/deadman notices
            if status:
                print("  " + status[:110].ljust(110) + "\r", end="", flush=True)
    finally:
        ser.write(b"x")                     # release on exit
        ser.flush()
        time.sleep(0.1)
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        ser.close()
        print("\r\nreleased (shaft free).")

if __name__ == "__main__":
    main()
