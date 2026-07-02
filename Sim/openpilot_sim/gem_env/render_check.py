#!/usr/bin/env python3
"""
Headless render check on Apple Silicon: spin up MetaDrive with a GEM-E4-configured
vehicle, drive a few steps, and save a frame. Proves the Mac can run the sim with
zero CARLA / zero NVIDIA.

Run:  .venv/bin/python gem_env/render_check.py
Out:  out/gem_frame.png  + printed vehicle physical params
"""
import os
import numpy as np
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "out"
OUT.mkdir(exist_ok=True)

# GEM E4 targets from Hardware/cart_parameters.md
GEM = dict(wheelbase=1.83, length=3.05, width=1.40, max_roadwheel_deg=28.0)

from metadrive.envs import MetaDriveEnv
from metadrive.component.sensors.rgb_camera import RGBCamera

# RGB camera roughly at the comma-3 road-cam framing; small res keeps it fast.
W, H = 512, 256

cfg = dict(
    use_render=False,               # headless
    image_observation=True,
    norm_pixel=False,               # give us uint8 frames
    sensors={"rgb": (RGBCamera, W, H)},
    interface_panel=[],
    num_scenarios=1,
    start_seed=0,
    traffic_density=0.10,
    map="S",                        # one straight block — easy to eyeball
    log_level=50,
    vehicle_config=dict(
        image_source="rgb",         # match our sensor name above
        # GEM E4 geometry via the keys MetaDrive actually exposes.
        length=GEM["length"],       # 3.05 m
        width=GEM["width"],         # 1.40 m
        height=2.00,
        mass=709,                   # curb weight kg
    ),
)

env = MetaDriveEnv(cfg)
try:
    obs, _ = env.reset()
    v = env.agent  # the ego vehicle
    # Introspect the ACTUAL physical params MetaDrive gave the vehicle so we know
    # the real API for the GEM tune (don't assume).
    params = {}
    for attr in ("WHEELBASE", "LENGTH", "WIDTH", "HEIGHT", "MASS", "max_steering"):
        params[attr] = getattr(v, attr, None)
    print("=== MetaDrive ego actual params ===")
    for k, val in params.items():
        print(f"  {k}: {val}")
    print(f"=== GEM E4 targets === {GEM}")

    # Drive forward a bit (throttle, no steer) to get a moving frame.
    frame = None
    for i in range(30):
        obs, r, term, trunc, info = env.step([0.0, 0.6])
        if term or trunc:
            obs, _ = env.reset()
    img = obs["image"]                       # (H, W, 3, stack)
    frame = img[..., -1] if img.ndim == 4 else img
    frame = frame.astype(np.uint8)

    # BGR->RGB (MetaDrive RGBCamera returns BGR) and save.
    from PIL import Image
    Image.fromarray(frame[..., ::-1]).save(OUT / "gem_frame.png")
    print(f"\nSAVED {OUT / 'gem_frame.png'}  shape={frame.shape} dtype={frame.dtype}")
    print("HEADLESS_RENDER_MAC=SUCCESS")
finally:
    try:
        env.close()
    except Exception:
        pass
    # Panda3D/Bullet segfaults in its atexit C++ destructor on macOS (a Bullet
    # callback grabs the GIL while the interpreter is tearing down). Our work is
    # done and flushed here, so skip Python finalizers and exit cleanly.
    import sys
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
