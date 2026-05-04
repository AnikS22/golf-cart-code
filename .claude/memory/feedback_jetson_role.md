---
name: Jetson role — DBW CAN gateway, NOT a sim host
description: The Jetson on the cart is the ROS↔CAN bridge to the Teensies + (Phase 1+) autonomy compute. It is NOT a sim host. Sim runs dev-side only.
type: feedback
originSessionId: 991af12c-3dcb-47ba-b9d1-a501769a1f69
---
User correction (2026-05-04, after I conflated "set up Jetson" with "run sim on Jetson"):

> "wait why would the sim work on the jetson that is not our concern I thought we were using this to control everything"

**The Jetson on the cart is FUNCTIONAL compute, not a sim host.** Per the master plan (PDF at `/Users/mpcr/Library/.../GEM_E4_Master_Plan.pdf`):

- AGX Orin = primary perception + planning (Phase 1+)
- Orin NX = safety supervisor + logging + DBW CAN bridge
- Both run `gem_dbw_bridge_node` (Python, python-can on SocketCAN can0) — translates ROS `/dbw/cmd` ↔ CAN frames at the protocol IDs from `dbw_can_protocol.h` (0x100/0x110/etc).
- Teensies handle firmware-level protocol work (EPAS18 0x296, J1939 sniff, DAC injection). Jetson does NOT.

**Sim runs OFF-CART** — on the user's Mac (Foxglove URDF preview only — Gazebo doesn't work cleanly on Apple Silicon Rosetta), or on a separate Linux dev box. The sim packages (`gem_sim`, `sim_dbw_bridge` in `Sim/Cartagena_GEM_E4_workspace/`) are dev-only.

**The cart-runtime workspace is `Software/autonomy_ws/`** — gem_dbw_bridge + gem_teleop. THIS is what gets built and deployed on the Jetson.

**How to apply:** When working on the Jetson (or any cart-mounted compute), build only `Software/autonomy_ws/`. Do NOT build `Sim/...` on the Jetson. Do NOT try to run Gazebo on the Jetson. Phase 0 first-light = `gem_dbw_bridge` + `gem_teleop` + a gamepad, talking to the Teensies via can0. The Yahboom Orin NX has a kernel-level can0 already (see `Hardware/JETSON_PLUG_LAYOUT.md`).

**Why:** I burned 2+ hours of session time trying to make Gazebo Harmonic + Fortress + Rosetta + Yahboom work. None of that was needed for Phase 0. The Jetson is a CAN gateway — keep it simple.
