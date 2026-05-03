# CAD software recommendation

You said "AutoCAD" — for the work this project actually needs (3D mechanical bracketry: sensor mounts, Pelican enclosure cutouts, EPAS18 mounting, dash console, brake actuator linkage), what you really want is a **3D solid modeler**, not AutoCAD (which is mostly 2D drafting + light 3D).

## Tier 1: what to install first

### Fusion 360 (Personal) — free for non-commercial / academic
- **What:** Cloud-backed 3D solid modeler from Autodesk. Industry standard for mechanical hobbyist + small-shop work. Integrated CAM for CNC and 3D printing.
- **Why it's the right pick:** Perfect for sensor brackets, mounting plates, enclosure cutouts. STEP/IGES import-export. Native macOS Apple Silicon. Free for non-commercial use including academic research.
- **Install:** download installer from https://www.autodesk.com/products/fusion-360/personal — sign in with your FAU email to get the academic license.
- **Learning curve:** ~2 hr to do useful work if you've never done CAD. Lots of YouTube tutorials. Hard-recommended over FreeCAD if you can swing it.

### SolidWorks (via FAU license) — if available
- **What:** What the 2020 team used (the recovered .step / SolidWorks renders in `OneDrive_1_5-1-2026/Motor/`).
- **Why:** Continuity with 2020 CAD work — bracket files open without conversion. FAU College of Engineering & Computer Science usually has SolidWorks lab licenses; ask in MPCR / your dept.
- **Install:** Windows-only (no native Mac). If you need this you'll be using a Windows lab machine or running it in a VM.

### Onshape (free for academic) — alternative if you want browser-only
- **What:** Browser-based 3D modeler. Same paradigm as SolidWorks (the founders left SolidWorks to build this).
- **Why pick this:** if you want zero-install, work-from-anywhere, easy collaboration. Public projects only on the free tier — so any FAU IP would need to be careful.

## Tier 2: free open-source if licensing is a problem

### FreeCAD — open-source, fully local
- Mature, capable, occasionally rough UX. Good for one-offs.
- `brew install --cask freecad`

## Tier 3: skip these

- **AutoCAD** — wrong tool. 2D-first, expensive subscription, no good reason to use it for this project.
- **TinkerCAD** — too primitive for real bracketry.
- **Blender** — phenomenal for art / sim meshes, weak for engineering brackets. (Already used in the Cartagena world build pipeline for OSM-imported terrain meshes; that's its right job here.)

## Recommendation for this project

**Default: Fusion 360 Personal.** Install it tonight; it'll be ready when you start designing.

If FAU has SolidWorks easily accessible AND you can read the 2020 .step files in it, use SolidWorks for any mounts that interface with the 2020 brackets (avoid re-modeling work). For new parts, Fusion is fine.

## What you'll design first

Once the cart is inspected (tomorrow), the immediate CAD queue:
1. **Pelican 1450 internal mounting plate** — laser-cut aluminum, drilled holes for AGX Orin + NX + switch + DC-DCs.
2. **Sensor mast** — extruded aluminum (Misumi HFS5-2020) frame for the LiDAR + GNSS antennas + front cams atop the hardtop.
3. **Steering column aux box bracket** — to mount Motion Teensy + ODrive driver near the EPAS18 ECU on the firewall.
4. **Pedals aux box bracket** — same idea, on the firewall above the pedal area.
5. **Throttle pedal harness tap board** — small PCB or bracket for the DAC output / failsafe relay junction.
6. **Brake actuator mount + Bowden cable bracket** — Phase 2.
