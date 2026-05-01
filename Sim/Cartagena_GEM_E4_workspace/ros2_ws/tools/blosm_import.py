"""Import Google Photorealistic 3D Tiles via Blosm. Run under:
    bforartists --background --python blosm_import.py -- <region_name>

Reads region config from regions.json, writes <region>/<name>.blend.
"""
import bpy
import json
import os
import sys
from pathlib import Path

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
if not args:
    raise SystemExit("usage: bforartists --background --python blosm_import.py -- <region>")
region_name = args[0]

TOOLS = Path(__file__).resolve().parent
cfg = json.loads((TOOLS / 'regions.json').read_text())[region_name]
region_dir = TOOLS / 'fau_world'   # shared workspace for now
region_dir.mkdir(exist_ok=True)
blend_path = region_dir / f'{region_name}.blend'

# Ensure Blosm is enabled (idempotent)
try:
    bpy.ops.preferences.addon_enable(module='blosm')
except Exception:
    pass

prefs = bpy.context.preferences.addons['blosm'].preferences
prefs.dataDir = str(region_dir / 'blosm_cache')
os.makedirs(prefs.dataDir, exist_ok=True)
bpy.ops.wm.save_userpref()

# Clear any leftover mesh objects from the default scene so we import into a
# known-empty state without touching the addon's registered scene props.
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)

bx = cfg['bbox']
bb = cfg['blosm']
scn = bpy.context.scene
p = scn.blosm
p.dataType = '3d-tiles'
p.threedTilesSource = 'google'
p.lodOf3dTiles = bb['lod']
p.geometricError = bb['geometric_error']
p.maxNumTiles = bb['max_num_tiles']
p.join3dTilesObjects = True
p.singleObject = True
p.relativeToInitialImport = True
p.minLat = bx['south']; p.maxLat = bx['north']
p.minLon = bx['west'];  p.maxLon = bx['east']

print(f"Importing {region_name} bbox={bx} lod={bb['lod']} err={bb['geometric_error']}")
bpy.ops.blosm.import_data()

mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']
tot_verts = sum(len(o.data.vertices) for o in mesh_objs)
tot_faces = sum(len(o.data.polygons) for o in mesh_objs)
print(f"Imported {len(mesh_objs)} mesh(es), {tot_verts} verts, {tot_faces} faces")

bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
print(f"Saved {blend_path}")
