#!/usr/bin/env bash
# Run this ON THE HPC LOGIN NODE. It reports the facts I need to finalize the
# SLURM/Apptainer scripts: scheduler, Apptainer, GPU, internet, partitions, storage.
# Read-only; changes nothing. Paste the output back.
echo "================ GEM HPC PROBE ================"
echo "host: $(hostname)   user: $(whoami)   date: $(date)"
echo
echo "--- scheduler ---"
command -v sbatch >/dev/null && { echo "SLURM: yes ($(sbatch --version 2>/dev/null))";
  echo "partitions:"; sinfo -o '%P %a %l %D %G' 2>/dev/null | head -20; } || echo "SLURM: NO"
echo
echo "--- GPU partitions (look for gres/gpu) ---"
sinfo -o '%P %G' 2>/dev/null | grep -i gpu || echo "(no gpu gres visible from login node)"
echo
echo "--- container runtime ---"
command -v apptainer >/dev/null && echo "apptainer: $(apptainer --version)" || echo "apptainer: NO"
command -v singularity >/dev/null && echo "singularity: $(singularity --version)" || echo "singularity: NO"
echo "apptainer fakeroot? try: apptainer build --help | grep -i fakeroot"
echo
echo "--- modules (lmod/tcl) ---"
command -v module >/dev/null && { module --version 2>&1 | head -1; echo "cuda/python modules:";
  module -t avail 2>&1 | grep -iE 'cuda|python|apptainer|singularity|conda' | head -20; } || echo "module: NO"
echo
echo "--- internet from LOGIN node ---"
curl -sI --max-time 8 https://github.com 2>/dev/null | head -1 || echo "github: unreachable"
curl -sI --max-time 8 https://ghcr.io   2>/dev/null | head -1 || echo "ghcr.io: unreachable"
echo "(compute-node internet is usually different — test inside a job with the sbatch)"
echo
echo "--- storage / quotas ---"
echo "HOME: $HOME"; df -h "$HOME" 2>/dev/null | tail -1
for v in "$SCRATCH" "$WORK" /scratch /work; do [ -n "$v" ] && [ -d "$v" ] && { echo "scratch-like: $v"; df -h "$v" 2>/dev/null | tail -1; }; done
echo
echo "--- nvidia driver on login node (may differ on compute) ---"
command -v nvidia-smi >/dev/null && nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader 2>/dev/null || echo "nvidia-smi: not on login node (normal)"
echo "================ END PROBE ================"
