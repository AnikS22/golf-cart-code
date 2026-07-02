#!/usr/bin/env python3
"""
Watch the GEM drive on your Mac.

The GEM-E4-configured vehicle drives itself around a course using MetaDrive's built-in
autopilot (IDM). This is NOT Comma's model — it's here so you can SEE the GEM render
and move locally (no CARLA, no NVIDIA). Comma's model driving is the HPC step.

Two modes:
  # record a video you can open (headless, always works):
  .venv/bin/python gem_env/drive_gem.py               ->  out/gem_drive.mp4  + sample PNGs

  # LIVE WINDOW on your Mac (watch in real time):
  .venv/bin/python gem_env/drive_gem.py --window
"""
import sys
import argparse
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gem_vehicle import register_gem_vehicle          # noqa: E402
from mdexit import clean_exit                          # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "out"
OUT.mkdir(exist_ok=True)

ap = argparse.ArgumentParser()
ap.add_argument("--window", action="store_true", help="open a live on-screen window")
ap.add_argument("--steps", type=int, default=400)
ap.add_argument("--seed", type=int, default=0)
args = ap.parse_args()

register_gem_vehicle()

from metadrive.envs import MetaDriveEnv                 # noqa: E402
from metadrive.component.sensors.rgb_camera import RGBCamera  # noqa: E402
from metadrive.policy.idm_policy import IDMPolicy       # noqa: E402

W, H = 640, 360
cfg = dict(
    use_render=args.window,          # on-screen window when --window
    num_scenarios=1,
    start_seed=args.seed,
    map="SCS",                       # straight-curve-straight: shows the GEM turning
    traffic_density=0.15,            # a little traffic so it's lively
    agent_policy=IDMPolicy,          # MetaDrive drives the GEM itself
    log_level=50,
    vehicle_config=dict(vehicle_model="gem_e4"),
)
if not args.window:                  # headless -> render to an offscreen camera we record
    cfg.update(
        image_observation=True, norm_pixel=False,
        sensors={"rgb": (RGBCamera, W, H)},
    )
    cfg["vehicle_config"]["image_source"] = "rgb"

env = MetaDriveEnv(cfg)
writer = None
try:
    obs, _ = env.reset()
    v = env.agent
    print(f"Driving GemE4Vehicle  wheelbase={v.FRONT_WHEELBASE+v.REAR_WHEELBASE:.2f}m "
          f"max_steer={v.MAX_STEERING}deg  mass={v.MASS}kg")

    if args.window:
        print("Live window open — close it or Ctrl-C to stop.")
        for i in range(args.steps):
            obs, r, term, trunc, info = env.step([0, 0])   # IDM overrides the action
            env.render(mode="human")
            if term or trunc:
                obs, _ = env.reset()
        print("WINDOW_DRIVE_DONE")
    else:
        import cv2
        writer = cv2.VideoWriter(str(OUT / "gem_drive.mp4"),
                                 cv2.VideoWriter_fourcc(*"mp4v"), 20, (W, H))
        saved = 0
        for i in range(args.steps):
            obs, r, term, trunc, info = env.step([0, 0])
            img = obs["image"]
            frame = (img[..., -1] if img.ndim == 4 else img).astype(np.uint8)  # RGB
            writer.write(np.ascontiguousarray(frame[..., ::-1]))               # ->BGR
            if i in (0, args.steps // 3, 2 * args.steps // 3, args.steps - 1):
                from PIL import Image
                Image.fromarray(frame).save(OUT / f"gem_drive_{saved}.png")
                saved += 1
            if term or trunc:
                obs, _ = env.reset()
        writer.release(); writer = None
        print(f"SAVED {OUT/'gem_drive.mp4'}  (+ {saved} sample PNGs gem_drive_0..3.png)")
        print("HEADLESS_DRIVE_DONE")
finally:
    if writer is not None:
        writer.release()
    clean_exit(env, 0)
