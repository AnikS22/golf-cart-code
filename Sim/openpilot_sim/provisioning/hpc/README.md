# Running "Comma's model drives the GEM" on the HPC (SLURM + Apptainer)

This runs Openpilot's **real** stack (`modeld` + `plannerd` + `controlsd`) driving a
**GEM-configured MetaDrive vehicle**, headless on a GPU node, and saves an mp4 you
copy back to the Mac. No display, no internet on the compute node.

## Why the HPC (and not the Mac)
Openpilot's driving daemons are Linux-only; the Mac can't run them. The HPC is x86
Linux with a GPU — Openpilot's documented sim target. The Mac's job is dev + the
eventual fine-tune. (MetaDrive + the model already run on the Mac; see `../../gem_env/`.)

## Steps
```bash
# 0. ON THE LOGIN NODE — tell me what your cluster looks like:
bash probe_hpc.sh            # paste the output back so I can tailor partitions etc.

# 1. ON THE LOGIN NODE (internet) — build image, checkout+build openpilot, stage model:
bash stage_login.sh $SCRATCH/gem_sim

# 2. Submit the GPU job (offline):
sbatch run_gem_sim.sbatch $SCRATCH/gem_sim

# 3. Copy the video to your Mac:
scp <hpc>:$SCRATCH/gem_sim/out/gem_drive_*.mp4 ~/Desktop/
```

## What the overlay changed (vs stock openpilot tools/sim)
Applied by `../../openpilot_overlay/apply_overlay.py` (validated on Mac: patches +
compiles):
- **GEM vehicle** (`gem_e4`): wheelbase 1.83 m, max steer ±28°, 709 kg, tire 0.305 m.
- **Speed cap** `GEM_MAX_KMH` (default 24 ≈ 15 mph) replaces the stock `1000 km/h`.
- **Steering scale** `GEM_STEER_RATIO` (default 8) — tune so full model command ≈ ±28°.
- **mp4 recorder** via `GEM_SIM_VIDEO`.
- Fingerprint stays `HONDA_CIVIC_2022` (Phase 1). A true `GEM_E4` opendbc car-port is
  Phase 2.

## Honest caveats (this is the one genuinely hard, HPC-specific step)
- **First bring-up will need iteration.** Openpilot's containerized build (`scons`) is
  heavy and site-sensitive. `stage_login.sh` builds it *inside* the image for ABI match,
  but expect to debug missing deps / build flags on your cluster once.
- **Edit `run_gem_sim.sbatch`**: `--partition`, `--gres`, `--time` to match your site
  (the probe output tells us the right values).
- **Headless GL**: the image uses EGL offscreen. If the GPU node lacks EGL/GL, fall back
  to `xvfb-run` (I'll add it once the probe confirms the driver stack).
- **If the model won't engage** at low speed: the Honda port's `minEnableSpeed`/
  `minSteerSpeed` may block it — raise `GEM_MAX_KMH`, or we move to the Phase-2 car-port.
- **Compute-node internet**: not required at run time (everything staged). Only
  `stage_login.sh` needs internet, on the login node.

Run `probe_hpc.sh` first and paste the output — then I finalize partitions, the GL
backend, and any module loads for your specific cluster.
