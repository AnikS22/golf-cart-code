#!/usr/bin/env bash
# Run ON THE HPC LOGIN NODE (where there is internet). Stages everything the
# offline GPU job needs: the container image, a BUILT openpilot checkout with the
# GEM overlay applied, and the supercombo model.
#
#   bash stage_login.sh /path/to/scratch/gem_sim
#
# Idempotent-ish: re-running re-pulls/rebuilds. Heavy: openpilot's scons build
# takes a while and needs the container's toolchain (that's why we build via
# `apptainer exec` so the ABI matches the runtime image).
set -euo pipefail

PROJECT="${1:?usage: stage_login.sh <project_dir_on_scratch>}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$PROJECT"
cd "$PROJECT"

echo "== [1/5] Build the Apptainer image (needs internet) =="
if [ ! -f gem_sim.sif ]; then
  apptainer build gem_sim.sif "$HERE/gem_sim.def" \
    || apptainer build --fakeroot gem_sim.sif "$HERE/gem_sim.def"
fi

echo "== [2/5] Clone openpilot + submodules (needs internet + git-lfs) =="
if [ ! -d openpilot ]; then
  GIT_LFS_SKIP_SMUDGE=1 git clone --recurse-submodules https://github.com/commaai/openpilot.git
fi
cd openpilot

echo "== [3/5] Pull the driving model via LFS =="
git lfs pull --include "openpilot/selfdrive/modeld/models/*.onnx" || \
  git lfs pull --include "selfdrive/modeld/models/*.onnx" || true

echo "== [4/5] Apply the GEM overlay =="
# Copy the overlay next to the checkout and apply it against this openpilot root.
cp -r "$HERE/../../openpilot_overlay" "$PROJECT/openpilot_overlay"
apptainer exec "$PROJECT/gem_sim.sif" python "$PROJECT/openpilot_overlay/apply_overlay.py" "$PROJECT/openpilot"

echo "== [5/5] Build openpilot inside the container (ABI-matched) =="
apptainer exec --bind "$PROJECT" "$PROJECT/gem_sim.sif" bash -lc "cd '$PROJECT/openpilot' && scons -j\$(nproc)"

echo
echo "[✓] Staged at $PROJECT :"
echo "    gem_sim.sif           (runtime image)"
echo "    openpilot/            (built, GEM overlay applied)"
echo "Next: sbatch run_gem_sim.sbatch $PROJECT"
