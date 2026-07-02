#!/usr/bin/env python3
"""
Comma's supercombo model drives the GEM in MetaDrive — Mac-native, no openpilot daemons.

Each step:
  MetaDrive road frame -> exact openpilot YUV pack -> supercombo -> predicted PLAN path
  -> pure-pursuit steering -> drives the GEM -> repeat (feeding the model's recurrent
  hidden_state back in, like openpilot does).

HONEST SCOPE: this is a best-effort *preview*. It uses the real model + the real
input/output formats (copied from openpilot's compile_modeld.py and the model's own
metadata), but it SKIPS openpilot's calibration warp and MPC controller, and uses a
simple pure-pursuit law. So the model genuinely drives, but not with openpilot's exact
control quality. The faithful version is the openpilot tools/sim run (Linux/HPC).

Run:  .venv/bin/python gem_env/comma_drives.py --steps 600
Out:  out/comma_drives.mp4  + sample PNGs
"""
import sys, argparse, pickle, codecs
from pathlib import Path
import numpy as np
import cv2
import onnxruntime as ort

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gem_vehicle import register_gem_vehicle, GemE4Vehicle   # noqa: E402
from mdexit import clean_exit                                  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"; OUT.mkdir(exist_ok=True)
MODEL = ROOT / "models" / "driving_supercombo.onnx"

ap = argparse.ArgumentParser()
ap.add_argument("--steps", type=int, default=600)
ap.add_argument("--seed", type=int, default=2)
ap.add_argument("--lookahead", type=float, default=10.0, help="pure-pursuit lookahead (m)")
ap.add_argument("--throttle", type=float, default=0.35)
ap.add_argument("--steer_sign", type=float, default=-1.0, help="flip if it steers the wrong way")
args = ap.parse_args()

# ---- model + its output slices (decoded from the onnx metadata, like modeld) ----
sess = ort.InferenceSession(str(MODEL), providers=["CPUExecutionProvider"])
_m = __import__("onnx").load(str(MODEL))
SLICES = pickle.loads(codecs.decode({p.key: p.value for p in _m.metadata_props}["output_slices"].encode(), "base64"))
IN = {i.name: (i.shape, i.type) for i in sess.get_inputs()}

# recurrent + static inputs
feats = np.zeros((1, 24, 512), np.float16)          # rolling hidden_state history
desire = np.zeros((1, 25, 8), np.float16)
traffic = np.array([[1, 0]], np.float16)            # traffic convention (one-hot)
action = np.zeros((1, 2), np.float16)

MODEL_W, MODEL_H = 512, 256                          # full YUV frame -> 6ch @ 128x256


def frame_to_6ch(rgb):
    """RGB (H,W,3) -> openpilot 6-plane YUV (6,128,256). Exactly compile_modeld.frames_to_tensor."""
    i420 = cv2.cvtColor(rgb, cv2.COLOR_RGB2YUV_I420)  # (H*3/2, W) planar
    H = i420.shape[0] * 2 // 3
    W = i420.shape[1]
    Y = i420[:H]
    U = i420[H:H + H // 4].reshape(H // 2, W // 2)
    V = i420[H + H // 4:H + H // 2].reshape(H // 2, W // 2)
    return np.stack([Y[0::2, 0::2], Y[1::2, 0::2], Y[0::2, 1::2], Y[1::2, 1::2], U, V], 0)


def plan_to_steer(model_out, wheelbase, max_steer_rad):
    """Parse the PLAN mean (33x15), pure-pursuit on its position path -> normalized steer."""
    plan = model_out[0, SLICES["plan"]]                 # 990 = 2*(33*15)
    mu = plan[:495].reshape(33, 15)
    xs, ys = mu[:, 0], mu[:, 1]                          # device frame: x fwd, y left
    # nearest path point at the lookahead distance
    idx = int(np.argmin(np.abs(xs - args.lookahead)))
    x, y = float(xs[idx]), float(ys[idx])
    Ld2 = max(x * x + y * y, 1e-3)
    curv = 2.0 * y / Ld2                                 # pure-pursuit curvature
    delta = np.arctan(wheelbase * curv)                 # bicycle-model road-wheel angle
    return float(np.clip(args.steer_sign * delta / max_steer_rad, -1, 1)), y


register_gem_vehicle()
from metadrive.envs import MetaDriveEnv                  # noqa: E402
from metadrive.component.sensors.rgb_camera import RGBCamera  # noqa: E402

env = MetaDriveEnv(dict(
    use_render=False, image_observation=True, norm_pixel=False,
    sensors={"rgb": (RGBCamera, MODEL_W, MODEL_H)},
    num_scenarios=1, start_seed=args.seed, map="SCS", traffic_density=0.1,
    log_level=50, vehicle_config=dict(vehicle_model="gem_e4", image_source="rgb"),
))
WB = GemE4Vehicle.FRONT_WHEELBASE + GemE4Vehicle.REAR_WHEELBASE
MAX_STEER_RAD = np.radians(GemE4Vehicle.MAX_STEERING)

writer = None
try:
    obs, _ = env.reset()
    prev6 = None
    writer = cv2.VideoWriter(str(OUT / "comma_drives.mp4"), cv2.VideoWriter_fourcc(*"mp4v"),
                             20, (MODEL_W, MODEL_H))
    saved = 0
    print(f"Comma model driving GemE4Vehicle (WB={WB:.2f}m, maxsteer={GemE4Vehicle.MAX_STEERING}deg)")
    for i in range(args.steps):
        rgb = (obs["image"][..., -1] if obs["image"].ndim == 4 else obs["image"]).astype(np.uint8)
        cur6 = frame_to_6ch(rgb)
        if prev6 is None:
            prev6 = cur6
        img = np.concatenate([prev6, cur6], 0)[None].astype(np.uint8)   # (1,12,128,256)
        prev6 = cur6

        out = sess.run(None, {
            "img": img, "big_img": img,          # feed same frame to wide cam (preview)
            "features_buffer": feats, "desire_pulse": desire,
            "traffic_convention": traffic, "action_t": action,
        })[0]

        # feed recurrent hidden_state back in (rolling 24-deep history)
        hidden = out[0, SLICES["hidden_state"]].astype(np.float16)
        feats = np.roll(feats, -1, axis=1); feats[0, -1] = hidden

        steer, y_look = plan_to_steer(out, WB, MAX_STEER_RAD)
        obs, r, term, trunc, info = env.step([steer, args.throttle])

        # record + occasional readout
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        cv2.putText(bgr, f"steer={steer:+.2f}  y@{args.lookahead:.0f}m={y_look:+.2f}m",
                    (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        writer.write(bgr)
        if i in (0, args.steps // 3, 2 * args.steps // 3, args.steps - 1):
            cv2.imwrite(str(OUT / f"comma_drives_{saved}.png"), bgr); saved += 1
        if i % 50 == 0:
            print(f"  step {i:4d}  steer={steer:+.2f}  y_lookahead={y_look:+.2f}m")
        if term or trunc:
            obs, _ = env.reset(); prev6 = None; feats[:] = 0

    writer.release(); writer = None
    print(f"SAVED {OUT/'comma_drives.mp4'}  (+ {saved} PNGs)")
    print("COMMA_DRIVES_DONE")
finally:
    if writer is not None:
        writer.release()
    clean_exit(env, 0)
