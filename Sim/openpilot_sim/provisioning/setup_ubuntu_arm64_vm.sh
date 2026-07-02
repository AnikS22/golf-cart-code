#!/usr/bin/env bash
# Provision an ARM64 Ubuntu 22.04 guest running under VMware Fusion on Apple Silicon.
#
# ROLE OF THIS VM: Linux dev/build sandbox for openpilot tooling, ROS 2, and the
# pipeline client code. It is NOT a CARLA server host — see docs/PLATFORM_REALITY.md.
# (Apple Silicon Fusion guests are arm64 with no NVIDIA/CUDA; CARLA's simulator needs
#  x86-64 + a discrete GPU.)
#
# HOW TO CREATE THE VM (do this in VMware Fusion first):
#   1. Download Ubuntu 22.04 LTS *ARM64* Server/Desktop ISO
#      (https://ubuntu.com/download/server/arm  — the arm64 image, NOT amd64).
#   2. Fusion → New → Install from disc/image → select the arm64 ISO.
#   3. Give it >= 8 vCPU, 16 GB RAM, 80 GB disk (M5 Max can easily spare this).
#   4. Finish install, log in, then run this script inside the guest.
#
# Usage (inside the guest):  bash setup_ubuntu_arm64_vm.sh
set -euo pipefail

echo "[*] Confirming architecture..."
ARCH="$(uname -m)"
if [[ "$ARCH" != "aarch64" && "$ARCH" != "arm64" ]]; then
  echo "!! This script targets the arm64 Fusion guest but arch is $ARCH."
  echo "!! If you somehow have an x86-64 Linux box with an NVIDIA GPU, use"
  echo "!! provisioning/setup_carla_server_x86.sh instead — that one runs CARLA."
fi

echo "[*] Updating apt package index and base packages..."
sudo apt-get update -y
sudo apt-get upgrade -y

echo "[*] Installing build + dev toolchain..."
sudo apt-get install -y \
  build-essential git git-lfs curl wget unzip pkg-config \
  python3 python3-venv python3-pip python3-dev \
  ffmpeg libgl1 libglib2.0-0 \
  can-utils iproute2 net-tools openssh-client rsync
git lfs install

echo "[*] Creating pipeline venv (~/opc-venv)..."
python3 -m venv "$HOME/opc-venv"
# shellcheck disable=SC1091
source "$HOME/opc-venv/bin/activate"
pip install --upgrade pip wheel
# Client / tooling deps (NOT torch training — that lives on the Mac):
pip install numpy opencv-python-headless pyyaml tqdm pillow onnx onnxruntime

cat <<'EOF'

[✓] ARM64 Ubuntu dev sandbox ready.

What you have:
  - Linux build tools, python3 + ~/opc-venv, git-lfs, can-utils, rsync/ssh.
  - A place to run openpilot's Linux-only tooling and the pipeline client code
    when pointed at a REMOTE CARLA server (export CARLA_HOST=<gpu-box-ip>).

What you still need for actual CARLA data generation:
  - An x86-64 machine with an NVIDIA GPU running the CARLA server.
    Provision it with provisioning/setup_carla_server_x86.sh.

Reminder: this VM cannot run the CARLA simulator. See docs/PLATFORM_REALITY.md.
EOF
