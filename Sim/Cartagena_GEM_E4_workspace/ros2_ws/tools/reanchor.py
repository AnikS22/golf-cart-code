"""Re-anchor a region's mesh so ground = z=0 (programmatic, not hand-tuned).

Usage: bforartists --background --python reanchor.py -- <region>

Ground detection: median Z of vertices in the 5th-20th percentile slice of all Z
values. Ignores rare sub-surface outliers without being skewed by building tops.
Applies the shift to the mesh, re-saves .blend and re-exports .glb.
"""
import bpy
import os
import statistics
import sys
from pathlib import Path

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
if not args:
    raise SystemExit("usage: bforartists --background --python reanchor.py -- <region>")
region = args[0]

TOOLS = Path(__file__).resolve().parent
BLEND = TOOLS / 'fau_world' / f'{region}.blend'
GLB = TOOLS / 'fau_world' / f'{region}.glb'

bpy.ops.wm.open_mainfile(filepath=str(BLEND))

for o in bpy.data.objects:
    if o.type == 'MESH':
        break
else:
    raise SystemExit("no mesh")

zs = sorted((o.matrix_world @ v.co).z for v in o.data.vertices)
n = len(zs)
ground_z = statistics.median(zs[int(n * 0.05):int(n * 0.20)])
print(f"n verts={n}  z range {zs[0]:.2f}..{zs[-1]:.2f}  ground_z={ground_z:.2f}")

o.location.z -= ground_z
bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT')
o.select_set(True)
bpy.context.view_layer.objects.active = o
bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

zs2 = sorted((o.matrix_world @ v.co).z for v in o.data.vertices)
print(f"post-shift ground: {statistics.median(zs2[int(n * 0.05):int(n * 0.20)]):.3f} (≈0)")
print(f"post-shift z range: {zs2[0]:.2f}..{zs2[-1]:.2f}")

bpy.ops.wm.save_mainfile()
bpy.ops.export_scene.gltf(filepath=str(GLB), export_format='GLB',
                          use_selection=False, export_apply=True)
print(f"GLB: {GLB} ({os.path.getsize(GLB)} bytes)")
