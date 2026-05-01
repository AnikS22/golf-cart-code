# Cart parameters — human-readable mirror

This file mirrors `Sim/urdf/cart_parameters.xacro` for humans (procurement, mechanical, controls). **The xacro is the canonical source of truth** — when these two files disagree, the xacro wins.

When you remeasure a value on the real cart, update **both** the xacro AND this doc. The `digital_twin_consistency.md` discipline ensures sim ↔ real parity.

## Vehicle geometry (Polaris GEM e4)

| Parameter | Value | Notes |
|---|---|---|
| Length | 3.05 m | stock GEM e4 spec |
| Width | 1.40 m | stock |
| Height (with hardtop) | 2.00 m | confirm on actual cart |
| Wheelbase | 1.83 m | front axle to rear axle |
| Track width | 1.27 m | left wheel to right wheel |
| Wheel radius | 0.305 m | 24.5" tire / 2 |
| Ground clearance | 0.150 m | stock |
| Curb weight | 709 kg | stock spec, ~1563 lb |

## Vehicle dynamics

| Parameter | Value | Notes |
|---|---|---|
| Steering ratio | 16.0 | handwheel / road wheel; **VERIFY by measurement** |
| Max road-wheel angle | ±28° | stock |
| Max handwheel angle | ±448° | derived from above |
| Max vehicle speed | 11.18 m/s (25 mph) | stock GEM e4 LSV cap |
| Phase 1 governed speed | 2.24 m/s (5 mph) | firmware-enforced + ROS-param check |

## Sensor extrinsics (base_link → sensor_link)

All values in meters / radians, ROS REP-103 convention (X forward, Y left, Z up).

| Sensor | X (m) | Y (m) | Z (m) | Yaw (rad) | Notes |
|---|---|---|---|---|---|
| LiDAR (Livox Mid-360) | 0.00 | 0.00 | 2.20 | 0.00 | atop roof mast |
| ZED 2i front stereo | 0.45 | 0.00 | 1.50 | 0.00 | windshield top center |
| Leopard IMX390 front mono | 0.45 | -0.15 | 1.50 | 0.00 | windshield top, just right of ZED |
| Cam FL (corner) | 0.35 | 0.65 | 1.30 | +0.785 | front-left A-pillar, +45° |
| Cam FR (corner) | 0.35 | -0.65 | 1.30 | -0.785 | front-right A-pillar, -45° |
| Cam RL (corner) | -0.90 | 0.65 | 1.30 | +2.356 | rear-left B-pillar, +135° |
| Cam RR (corner) | -0.90 | -0.65 | 1.30 | -2.356 | rear-right B-pillar, -135° |
| ZED Mini rear | -1.30 | 0.00 | 1.40 | 3.14159 | rear cargo top, facing aft |
| GNSS antenna 1 (front) | 0.60 | 0.00 | 2.05 | — | front of roof |
| GNSS antenna 2 (rear) | -0.40 | 0.00 | 2.05 | — | rear of roof |
| GNSS baseline length | 1.00 m | (computed) | for moving-baseline heading |
| IMU (VectorNav VN-100) | 0.00 | 0.00 | 0.30 | 0.00 | trunk near vehicle CG |

## Sensor specs

| Sensor | Rate | FOV (H) | Resolution | Range / Notes |
|---|---|---|---|---|
| Livox Mid-360 | 10 Hz | 360° | 32 ch vertical (-7° to +52°) | 0.1–70 m |
| ZED 2i | 30 Hz | ~110° | 1280×720 | 0.3–20 m depth |
| Leopard IMX390 | 30 Hz | ~60° | 1920×1080 | HDR, automotive grade |
| Corner e-CAM130 (×4) | 20 Hz | ~120° | 1280×720 | wide FOV |
| ZED Mini | 30 Hz | ~100° | 1280×720 | rear |
| ZED-F9P GNSS | 10 Hz | — | — | RTK FIX target; moving-baseline heading |
| VN-100 IMU | 200 Hz | — | — | gyro stddev 1e-4 rad/s, accel 5e-3 m/s² |

## Calibration discipline

When you calibrate the real cart with Autoware's calibration tools (or equivalent):

1. Run extrinsic calibration LiDAR ↔ each camera, IMU ↔ base_link.
2. Convert calibration output to numeric XYZ + RPY values.
3. **Update `Sim/urdf/cart_parameters.xacro`** with the new numbers.
4. **Update this file** to match.
5. Rebuild both the sim package and the real-cart `gem_description` package.
6. Both sim and real-cart now use the same numbers → sim ↔ real consistency preserved.

If you find yourself updating sim numbers without updating real numbers (or vice versa), STOP — that's the consistency-violation antipattern this file exists to prevent.
