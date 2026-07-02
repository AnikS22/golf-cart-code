#!/usr/bin/env python3
"""
Apply the GEM-E4 overlay to an Openpilot checkout's tools/sim so Comma's model
drives a GEM-configured MetaDrive vehicle instead of the default sedan.

It makes FOUR targeted, idempotent edits (each asserts its anchor exists, so it
fails loudly if upstream drifts rather than silently no-op'ing):

  1. Writes tools/sim/lib/gem_vehicle.py  (GemE4Vehicle: wheelbase 1.83, ±28°,
     709 kg, tire 0.305) and registers it in MetaDrive's type maps.
  2. metadrive_bridge.py  — vehicle_config gets  vehicle_model="gem_e4".
  3. metadrive_process.py — the hard-coded highway speed override
        env.vehicle.config["max_speed_km_h"] = 1000
     becomes a GEM cap (env GEM_MAX_KMH, default 40 ≈ 25 mph); and steer_ratio
     becomes env-tunable (GEM_STEER_RATIO, default 8).
  4. metadrive_process.py — optional mp4 recorder of the road camera, enabled by
     env GEM_SIM_VIDEO=/path/out.mp4  (the whole point: capture the drive).

Phase 1 keeps FINGERPRINT=HONDA_CIVIC_2022 (control tuning stays Honda's); a true
GEM car-port in opendbc is a later step. See openpilot_overlay/README.md.

Usage:
  python apply_overlay.py [OPENPILOT_ROOT]
      OPENPILOT_ROOT defaults to ../openpilot_upstream/openpilot
Idempotent: safe to run repeatedly.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_OP = HERE.parent / "openpilot_upstream" / "openpilot"

MARK = "# [GEM-OVERLAY]"

GEM_VEHICLE_SRC = '''\
# [GEM-OVERLAY] GEM E4 vehicle for MetaDrive. Kinematics from FAU cart_parameters.md.
from metadrive.component.vehicle.vehicle_type import DefaultVehicle
import metadrive.component.vehicle.vehicle_type as _vt


class GemE4Vehicle(DefaultVehicle):
    FRONT_WHEELBASE = 0.915        # + REAR = 1.83 m wheelbase
    REAR_WHEELBASE = 0.915
    LATERAL_TIRE_TO_CENTER = 0.635 # track 1.27 / 2
    TIRE_RADIUS = 0.305
    TIRE_WIDTH = 0.22
    MASS = 709
    MAX_STEERING = 28.0            # GEM road-wheel max (deg)

    @property
    def max_speed_km_h(self):
        return 40.0                # ~25 mph stock LSV cap

    @property
    def max_speed_m_s(self):
        return 40.0 / 3.6


def register_gem_vehicle(name="gem_e4"):
    """Register in BOTH forward (name->class) and reverse (class->name) maps;
    MetaDrive's BaseVehicle.reset() needs the reverse lookup."""
    _vt.vehicle_type[name] = GemE4Vehicle
    _vt.vehicle_class_to_type[GemE4Vehicle] = name
    return name
'''


def patch(path: Path, anchor: str, new: str, label: str):
    text = path.read_text()
    if MARK in text and label in text:
        print(f"  [skip] {path.name}: {label} already applied")
        return text
    assert anchor in text, f"ANCHOR NOT FOUND in {path} for {label!r}:\n{anchor!r}"
    text = text.replace(anchor, new, 1)
    path.write_text(text)
    print(f"  [ok]   {path.name}: {label}")
    return text


def main():
    op = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_OP
    md = op / "tools" / "sim" / "bridge" / "metadrive"
    lib = op / "tools" / "sim" / "lib"
    assert md.is_dir(), f"not an openpilot checkout (missing {md})"
    print(f"Applying GEM overlay to: {op}")

    # 1. GEM vehicle module
    (lib / "gem_vehicle.py").write_text(GEM_VEHICLE_SRC)
    print("  [ok]   wrote tools/sim/lib/gem_vehicle.py")

    # 2. bridge: select the GEM vehicle
    patch(
        md / "metadrive_bridge.py",
        anchor=(
            "      vehicle_config=dict(\n"
            "        enable_reverse=False,\n"
            "        render_vehicle=False,\n"
            "        image_source=\"rgb_road\",\n"
            "      ),"
        ),
        new=(
            "      vehicle_config=dict(\n"
            "        enable_reverse=False,\n"
            "        render_vehicle=False,\n"
            "        image_source=\"rgb_road\",\n"
            "        vehicle_model=\"gem_e4\",  # [GEM-OVERLAY] vehicle_model\n"
            "      ),"
        ),
        label="vehicle_model",
    )

    # 3a. process: register the GEM vehicle right before the env is built
    patch(
        md / "metadrive_process.py",
        anchor="  env = MetaDriveEnv(config)",
        new=(
            "  from openpilot.tools.sim.lib.gem_vehicle import register_gem_vehicle  " + MARK + " register\n"
            "  register_gem_vehicle()\n"
            "  env = MetaDriveEnv(config)"
        ),
        label="register",
    )

    # 3b. process: GEM speed cap instead of 1000 km/h highway override
    patch(
        md / "metadrive_process.py",
        anchor='    env.vehicle.config["max_speed_km_h"] = 1000',
        new=(
            "    import os as _os  " + MARK + " speedcap\n"
            "    env.vehicle.config[\"max_speed_km_h\"] = float(_os.environ.get(\"GEM_MAX_KMH\", \"40\"))"
        ),
        label="speedcap",
    )

    # 3c. process: env-tunable steer ratio (GEM road-wheel scaling)
    patch(
        md / "metadrive_process.py",
        anchor="  steer_ratio = 8\n",
        new=(
            "  import os as _os2  " + MARK + " steerratio\n"
            "  steer_ratio = float(_os2.environ.get(\"GEM_STEER_RATIO\", \"8\"))\n"
        ),
        label="steerratio",
    )

    # 4. process: optional mp4 recorder of the road camera
    patch(
        md / "metadrive_process.py",
        anchor='      road_image[...] = get_cam_as_rgb("rgb_road")',
        new=(
            '      road_image[...] = get_cam_as_rgb("rgb_road")\n'
            "      _gem_record(road_image)  " + MARK + " record-call"
        ),
        label="record-call",
    )
    # 4b. the recorder helper + init, injected after env creation
    patch(
        md / "metadrive_process.py",
        anchor="  register_gem_vehicle()\n  env = MetaDriveEnv(config)",
        new=(
            "  register_gem_vehicle()\n"
            "  env = MetaDriveEnv(config)\n"
            "  " + MARK + " recorder\n"
            "  import os as _os3\n"
            "  _gem_vw = None\n"
            "  _gem_vpath = _os3.environ.get(\"GEM_SIM_VIDEO\")\n"
            "  def _gem_record(img):\n"
            "    nonlocal _gem_vw\n"
            "    if not _gem_vpath:\n"
            "      return\n"
            "    import cv2, numpy as _np\n"
            "    if _gem_vw is None:\n"
            "      h, w = img.shape[:2]\n"
            "      _gem_vw = cv2.VideoWriter(_gem_vpath, cv2.VideoWriter_fourcc(*'mp4v'), 20, (w, h))\n"
            "    _gem_vw.write(_np.ascontiguousarray(img[..., ::-1]))  # RGB->BGR"
        ),
        label="recorder",
    )

    print("\nGEM overlay applied. Run the sim per openpilot_overlay/README.md.")
    print("Env knobs: GEM_MAX_KMH, GEM_STEER_RATIO, GEM_SIM_VIDEO=/path/out.mp4")


if __name__ == "__main__":
    main()
