#!/usr/bin/env python3
"""Drive the GEM E4 steering by keyboard.

Talks to the manual-drive firmware on the Motion Teensy (0x298 @ 250k).

    python3 drive.py            # auto-finds the Teensy
    python3 drive.py /dev/cu.usbmodemXXXX

Keys:  ← / a = left    → / d = right    space = center    q = quit (stops)

Holds your steering position while running; sends a keepalive so if this script
quits or the USB drops, the firmware recenters the wheel within ~3 s. Front
wheels off the ground or path clear before you steer.
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
    print("  a / ← left   d / → right   space center   q quit\r")

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    tty.setcbreak(fd)                       # single keys, no Enter
    last_keepalive = 0.0
    status = ""
    try:
        while True:
            # forward keystrokes
            r, _, _ = select.select([fd], [], [], 0.02)
            if r:
                ch = sys.stdin.read(1)
                if ch == "\x1b":            # arrow keys: ESC [ C/D
                    seq = sys.stdin.read(2) if select.select([fd], [], [], 0.01)[0] else ""
                    if seq == "[C": ser.write(b"d")
                    elif seq == "[D": ser.write(b"a")
                elif ch in ("q", "\x03"):   # q or Ctrl-C
                    break
                elif ch in ("a", "d", " "):
                    ser.write(ch.encode())
                elif ch == "x":
                    ser.write(b"x")

            # keepalive ~1 Hz so the firmware deadman doesn't recenter mid-drive
            now = time.time()
            if now - last_keepalive > 1.0:
                ser.write(b".")
                last_keepalive = now

            # show the latest status line in place
            data = ser.read(4096).decode("utf-8", "replace")
            for line in data.splitlines():
                if line.startswith("[st]"):
                    status = line
                elif line.strip():
                    print(line + "\r")      # OVERRIDE/SAFE/deadman notices
            if status:
                print("  " + status[:110].ljust(110) + "\r", end="", flush=True)
    finally:
        ser.write(b"x")                     # stop -> local on exit
        ser.flush()
        time.sleep(0.1)
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        ser.close()
        print("\r\nstopped (local mode).")

if __name__ == "__main__":
    main()
