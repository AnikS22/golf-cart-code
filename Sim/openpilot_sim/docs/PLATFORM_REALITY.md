# Platform reality — where each piece actually runs

Read this before setting up any machine. It exists so we don't burn a day setting
up a VM that physically cannot run the simulator.

## The one hard constraint

**CARLA's simulator is x86-64 + requires a discrete GPU (Vulkan/DX, ideally NVIDIA).**
There is **no ARM64 build of the CARLA simulator** and there never has been.

Your dev machine is an **Apple Silicon M5 Max (arm64)** with an Apple integrated GPU
and **no NVIDIA**. That has two consequences people usually miss:

1. **A VMware Fusion / Parallels VM on this Mac is ARM64-only.** VMware Fusion on
   Apple Silicon uses Apple's Hypervisor framework — it runs *arm64* Linux guests
   natively and **cannot run x86-64 guests at all** (no x86 emulation). So a Linux
   VM here is Ubuntu-arm64, which has no CARLA build.
2. **No GPU passthrough.** Even the arm64 guest gets only a paravirtual GPU (limited
   OpenGL), never CUDA/NVIDIA. CARLA/Unreal would fall back to software rendering at
   seconds-per-frame — useless for data generation.

UTM/QEMU *can* emulate x86-64 on the Mac, but with no GPU and TCG emulation CARLA
runs at a small fraction of 1 FPS. Also not viable.

**Conclusion: the CARLA server cannot run on this Mac, VM or not.** It needs a real
x86-64 + NVIDIA box (cloud or a lab workstation).

## Who does what (the correct split)

| Component | Runs on | Why |
|---|---|---|
| **Model fine-tuning** (PyTorch) | **This Mac, natively (MPS)** | 128 GB unified RAM + M5 Max GPU is genuinely great for training. This is where the Mac shines. |
| **Mac-local mock sim** (`mock/`) | **This Mac, natively** | Lets us test the bridge + training loop today with zero CARLA. |
| **CARLA server** (Unreal simulator) | **x86-64 + NVIDIA host** (cloud or FAU workstation) | GPU-bound, x86-only. |
| **CARLA client + data recorder** | **same x86 host** (co-located, low latency) | Official CARLA PythonAPI wheels are x86-64 only; keep client next to server. |
| **Recorded datasets** | **synced Mac ⟷ GPU host** (rsync/scp) | Record on GPU host, train on Mac. |
| **Linux dev sandbox** (VMware Fusion arm64 Ubuntu) | **This Mac** | Optional: openpilot repo tooling, ROS, compiling — NOT a CARLA host. |

## What the VMware Fusion VM is (and isn't) good for

Setting up the arm64 Ubuntu VM (`provisioning/setup_ubuntu_arm64_vm.sh`) is still
worthwhile — it's a clean Linux environment for openpilot's tooling, ROS, and code
that assumes Linux. But be clear-eyed:

- ✅ Linux dev/build environment, openpilot Python tooling, ROS 2, git/LFS.
- ✅ Can act as a networked CARLA *client* **only** if we build the CARLA PythonAPI
  from source for arm64 (non-trivial) — usually not worth it; run the client on the
  GPU host instead.
- ❌ **Cannot** run the CARLA simulator.
- ❌ **Cannot** give you CUDA/NVIDIA.

## The pragmatic path (what we're building)

1. **Now, on the Mac:** pull the real Openpilot model, build the full pipeline code
   (blueprint, bridge, data tools, training loop) + a Mac-local mock so the loop is
   runnable/testable today.
2. **When a GPU host is available:** point the same code at the CARLA server
   (`CARLA_HOST=<ip>`), generate photoreal data, sync to Mac, fine-tune.

The code is written host-agnostic so swapping in the GPU box is a config change, not
a rewrite.
