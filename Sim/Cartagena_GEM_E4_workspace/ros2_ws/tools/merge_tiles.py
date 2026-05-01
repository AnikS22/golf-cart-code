"""Load a pre-merged glb (from `gltf-transform merge`) into Blender, apply the
ECEF->ENU rotation so x=east, y=north, z=up, then save as the region's .blend
ready for reanchor/crop.

Usage: bforartists --background --python merge_tiles.py -- <region>

Expects fau_world/<region>_merged.glb to already exist.
Blender is only used here to apply the coordinate transform + export the
combined mesh; the actual tile merging is handled faster by gltf-transform.
"""
import bpy
import json
import math
import sys
from pathlib import Path
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
if not args:
    raise SystemExit("usage: bforartists --background --python merge_tiles.py -- <region>")
region = args[0]

TOOLS = Path(__file__).resolve().parent
MERGED_GLB = TOOLS / 'fau_world' / f'{region}_merged.glb'
BLEND_OUT = TOOLS / 'fau_world' / f'{region}.blend'

WGS84_A = 6378137.0
WGS84_E2 = 6.69437999014e-3

def lla_to_ecef(lat_deg, lon_deg, alt_m=0.0):
    lat = math.radians(lat_deg); lon = math.radians(lon_deg)
    s, c = math.sin(lat), math.cos(lat)
    N = WGS84_A / math.sqrt(1 - WGS84_E2 * s * s)
    return Vector(((N + alt_m) * c * math.cos(lon),
                   (N + alt_m) * c * math.sin(lon),
                   (N * (1 - WGS84_E2) + alt_m) * s))

def ecef_to_enu_rotation(lat_deg, lon_deg):
    lat = math.radians(lat_deg); lon = math.radians(lon_deg)
    sl, cl = math.sin(lat), math.cos(lat)
    so, co = math.sin(lon), math.cos(lon)
    E = Vector((-so, co, 0.0))
    N = Vector((-sl * co, -sl * so, cl))
    U = Vector((cl * co, cl * so, sl))
    return Matrix((E, N, U))

# Start from an empty scene
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)

print(f"Loading {MERGED_GLB}")
bpy.ops.import_scene.gltf(filepath=str(MERGED_GLB), merge_vertices=False)

mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']
print(f"Imported {len(mesh_objs)} mesh(es)")
if not mesh_objs:
    raise SystemExit("no mesh")

# If gltf-transform produced multiple mesh objects (one per primitive group),
# join them so the rest of the pipeline sees a single object.
if len(mesh_objs) > 1:
    bpy.ops.object.select_all(action='DESELECT')
    for o in mesh_objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = mesh_objs[0]
    bpy.ops.object.join()

obj = bpy.context.view_layer.objects.active
obj.name = "Google3DTiles"

# ECEF -> local ENU at bbox center
regions = json.loads((TOOLS / 'regions.json').read_text())
bbox = regions[region]['bbox']
lat_c = (bbox['south'] + bbox['north']) / 2.0
lon_c = (bbox['west']  + bbox['east'])  / 2.0
ecef_center = lla_to_ecef(lat_c, lon_c, 0.0)
R = ecef_to_enu_rotation(lat_c, lon_c)

obj_world = obj.matrix_world.copy()
xform = (R.to_4x4() @ Matrix.Translation(-ecef_center)) @ obj_world

mesh = obj.data
for v in mesh.vertices:
    v.co = xform @ v.co
mesh.update()
obj.matrix_world = Matrix.Identity(4)

bb = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
print(f"Combined mesh: {len(mesh.vertices)} verts, {len(mesh.polygons)} faces")
print(f"  local ENU bbox: x {min(p.x for p in bb):.1f}..{max(p.x for p in bb):.1f}"
      f"  y {min(p.y for p in bb):.1f}..{max(p.y for p in bb):.1f}"
      f"  z {min(p.z for p in bb):.1f}..{max(p.z for p in bb):.1f}")

bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_OUT))
print(f"Saved {BLEND_OUT}")
