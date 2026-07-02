#!/usr/bin/env bash
#SBATCH --job-name=gem-op-sim
#SBATCH --partition=gpu            # <-- EDIT to your GPU partition (see probe output)
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=00:30:00
#SBATCH --output=gem_op_sim_%j.log
#
# Runs Comma's model driving the GEM in MetaDrive, HEADLESS, and writes an mp4.
# Two processes inside ONE Apptainer container, talking over cereal/msgq on
# localhost. No display needed (EGL offscreen). No internet needed (staged).
#
#   sbatch run_gem_sim.sbatch /path/to/scratch/gem_sim
set -euo pipefail

PROJECT="${1:?usage: sbatch run_gem_sim.sbatch <staged_project_dir>}"
SIF="$PROJECT/gem_sim.sif"
OP="$PROJECT/openpilot"
OUT="$PROJECT/out"; mkdir -p "$OUT"
VIDEO="$OUT/gem_drive_${SLURM_JOB_ID:-local}.mp4"

# GEM tuning knobs (read by the overlay). Start gentle; adjust after first run.
export GEM_MAX_KMH="${GEM_MAX_KMH:-24}"          # ~15 mph
export GEM_STEER_RATIO="${GEM_STEER_RATIO:-8}"
export GEM_SIM_VIDEO="$VIDEO"

# Phase-1 fingerprint stays Honda Civic (control tuning); GEM is the physical car.
COMMON_ENV="--env SIMULATION=1,GEM_MAX_KMH=$GEM_MAX_KMH,GEM_STEER_RATIO=$GEM_STEER_RATIO,GEM_SIM_VIDEO=$GEM_SIM_VIDEO"

echo "[*] GPU:"; nvidia-smi --query-gpu=name,driver_version --format=csv,noheader || echo "  (no nvidia-smi)"
echo "[*] Launching openpilot stack (background)..."
apptainer exec --nv --bind "$PROJECT" $COMMON_ENV "$SIF" \
    bash -lc "cd '$OP' && ./tools/sim/launch_openpilot.sh" &
OP_PID=$!

sleep 20   # let the daemons come up

echo "[*] Launching MetaDrive bridge (records to $VIDEO)..."
apptainer exec --nv --bind "$PROJECT" $COMMON_ENV "$SIF" \
    bash -lc "cd '$OP' && python tools/sim/run_bridge.py --dual_camera" || true

echo "[*] Bridge exited; stopping openpilot stack..."
kill "$OP_PID" 2>/dev/null || true
wait "$OP_PID" 2>/dev/null || true

echo "[✓] Done. Video: $VIDEO"
echo "    Copy to your Mac:  scp <hpc>:$VIDEO ~/Desktop/"
