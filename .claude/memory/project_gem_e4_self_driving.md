---
name: GEM E4 self-driving cart project
description: Active multi-year project at FAU MPCR lab — converting a 2018 GEM E4 LSV into a "tiny Waymo" full self-driving golf cart. Picked back up 2026-05 after being abandoned in 2020.
type: project
originSessionId: 991af12c-3dcb-47ba-b9d1-a501769a1f69
---
**What:** Self-driving conversion of a 2018 GEM E4 (low-speed electric vehicle) on FAU campus.
**Lab:** Florida Atlantic University, MPCR (Machine Perception & Cognitive Robotics).
**Timeline:** Originally started ~2019, abandoned 2020, revived 2026-05-01 by current user.

**Architecture (decided 2026-05-01):**
- Autonomy goal: full self-driving stack ("tiny Waymo" — the user's words).
- Compute: NVIDIA Jetson (Orin family) + a real-time microcontroller for drive-by-wire.
- Operating env: FAU campus paths/sidewalks, low speed (<15 mph).
- Safety posture: Phase 1 = safety driver always in seat with mechanical override; Phase 2 = unmanned.

**Hardware status as of 2026-05-01:**
- New higher-capacity battery pack installed (does NOT fit original under-seat carriage — open mechanical issue).
- New ignition switch installed.
- Steering motor mounted on the steering shaft via custom bracket (CAD shows worm-gear DC gearmotor); **specific motor model is unknown** — old documentation/code lost.
- Accelerator pedal: CAD bracket exists for a mechanical actuator approach, but plan is now to **bypass electronically** via DAC voltage injection into the GEM's Hall-effect throttle signal.
- Brake actuator: NOT YET installed. Phase 1 relies on safety-driver foot. Phase 2 will add a linear actuator.

**Critical lost context:**
- 2020 Arduino code (`piduino_v3.ino` referenced in user's notes) is unrecoverable — the file on disk is 13 bytes containing literal "404 NOT FOUND" text, not real code.
- Steering motor part number / driver type unknown without physical inspection.

**Why:** University research project demonstrating full-stack autonomy on a real vehicle.

**How to apply:** When user mentions "the cart" / "GEM" / "self-driving" / "campus drive", load this context. Treat firmware as greenfield. Do NOT assume any 2020 code is salvageable. Always verify decisions against the safety-driver-first → unmanned-later progression. The canonical project plan lives at `/Users/mpcr/.claude/plans/i-need-your-help-hashed-dongarra.md` (created 2026-05-01).
