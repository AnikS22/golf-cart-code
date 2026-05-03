---
name: Planning depth and prior-art expectations
description: For embedded / robotics / vehicle projects, this user expects (1) prior-art research before architectural lock-in, and (2) extreme physical detail — every wire, box, connector, cable route, cooling spec.
type: feedback
originSessionId: 991af12c-3dcb-47ba-b9d1-a501769a1f69
---
When planning embedded, robotics, or vehicle-conversion projects, this user expects:

1. **Always check published prior art first.** When the user pointed me to UIUC's GEM e4 wiki (UIUC-Robotics/gem_ws), they were not asking me to add a footnote — they were correcting me for not having considered their reference architecture before locking decisions. Search GitHub, university lab repos, open-source AV projects (Autoware, comma.ai, F1Tenth) for similar builds and cite specific component choices and pitfalls before locking the BOM.

2. **Plan down to every wire, box, cable route, and connector.** Direct user quote (2026-05-01): *"You need to plan out down to every wire and box and how and where it is all going to fit if it is in the trunk how to cool it how to get the cables so that everything reaches the trunk how to connect everything leave no detail not looked over."* For physical builds, the plan must include: physical zone-by-zone packaging (roof, trunk, dash, footwell, etc.), cable run tables (every cable: source → destination, length, gauge, connector type), thermal management (heat load per box, cooling method, ambient assumptions), enclosure contents listed item-by-item, mounting hardware, fuse/connector schedule.

**Why:** This is a real vehicle build that has to be physically assembled by humans — abstraction-level plans fail when the ZED 2i USB cable turns out to be 1.5 m short of the trunk, or the trunk hits 60°C in Florida sun and the Jetson thermal-throttles mid-test. The user has been burned by abandoned/under-specified plans before (this very project went dormant 2020–2026 with no recoverable artifacts), so plans must be self-sufficient.

**How to apply:** For any embedded/robotics/vehicle plan in this project, include sections for: prior-art reference table (with build/decision comparison), physical packaging map per zone, cable routing schedule (table form), thermal management calculation (heat load, cooling method, margin), bill of materials at the connector/fastener level (not just chips and modules). Don't shorthand "wire it up" — spell out every conductor.
