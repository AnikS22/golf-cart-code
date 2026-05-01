"""Crop a region's mesh using OSM polygons — subtract-only, preserves ground.

Usage: bforartists --background --python crop_mesh.py -- <region>

Keep rule per vertex:
  z >= z_floor                  (drops subsurface artifacts)
  AND not inside any parking-lot polygon  (drops parked cars)
  AND within outlier_radius_m of any OSM building/path  (drops sky, far-buildings)

Config pulled from regions.json; OSM polygons from osm_polygons.json.
"""
import bpy
import bmesh
import json
import math
import os
import sys
from pathlib import Path

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
if not args:
    raise SystemExit("usage: bforartists --background --python crop_mesh.py -- <region>")
region = args[0]

TOOLS = Path(__file__).resolve().parent
cfg = json.loads((TOOLS / 'regions.json').read_text())[region]['crop']
BLEND = TOOLS / 'fau_world' / f'{region}.blend'
GLB = TOOLS / 'fau_world' / f'{region}.glb'
OSM = TOOLS / 'fau_world' / 'osm_polygons.json'

Z_FLOOR = cfg['z_floor']
# How far a vertex can be from *any* OSM feature before we consider it
# out-of-scene noise (sky puffs, buildings bleeding in from outside bbox).
OUTLIER_RADIUS_M = cfg.get('outlier_radius_m', 40.0)

osm = json.loads(OSM.read_text())
bbox = osm['bbox']
CLAT = (bbox['south'] + bbox['north']) / 2.0
CLON = (bbox['west']  + bbox['east'])  / 2.0
M_LAT = 111320.0
M_LON = 111320.0 * math.cos(math.radians(CLAT))

def ll(lat, lon):
    return ((lon - CLON) * M_LON, (lat - CLAT) * M_LAT)

buildings = [[ll(a, b) for a, b in p['coords']] for p in osm['buildings']]
paths     = [[ll(a, b) for a, b in p['coords']] for p in osm['paths']]
parking   = [[ll(a, b) for a, b in p['coords']] for p in osm.get('parking', [])]

GRID = 10.0
bc, pc, kc = {}, {}, {}

def _insert(table, key, xs, ys, pad):
    g0x, g0y = int((min(xs) - pad) // GRID), int((min(ys) - pad) // GRID)
    g1x, g1y = int((max(xs) + pad) // GRID) + 1, int((max(ys) + pad) // GRID) + 1
    for gx in range(g0x, g1x + 1):
        for gy in range(g0y, g1y + 1):
            table.setdefault((gx, gy), []).append(key)

for i, poly in enumerate(buildings): _insert(bc, i, [p[0] for p in poly], [p[1] for p in poly], OUTLIER_RADIUS_M)
for i, line in enumerate(paths):     _insert(pc, i, [p[0] for p in line], [p[1] for p in line], OUTLIER_RADIUS_M)
for i, poly in enumerate(parking):   _insert(kc, i, [p[0] for p in poly], [p[1] for p in poly], 0.0)

def point_in_poly(x, y, poly):
    inside = False; n = len(poly); j = n - 1
    for i in range(n):
        xi, yi = poly[i]; xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
        j = i
    return inside

def dist_seg(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    d2 = dx*dx + dy*dy
    if d2 < 1e-12: return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax)*dx + (py - ay)*dy) / d2))
    return math.hypot(px - (ax + t*dx), py - (ay + t*dy))

def cell(x, y): return (int(x // GRID), int(y // GRID))

def in_parking(x, y):
    for key in kc.get(cell(x, y), ()):
        if point_in_poly(x, y, parking[key]): return True
    return False

def near_any_osm_feature(x, y, r):
    c = cell(x, y)
    for key in bc.get(c, ()):
        poly = buildings[key]
        if point_in_poly(x, y, poly): return True
        for i in range(len(poly)):
            a, b = poly[i], poly[(i + 1) % len(poly)]
            if dist_seg(x, y, a[0], a[1], b[0], b[1]) <= r: return True
    for key in pc.get(c, ()):
        line = paths[key]
        for i in range(len(line) - 1):
            a, b = line[i], line[i + 1]
            if dist_seg(x, y, a[0], a[1], b[0], b[1]) <= r: return True
    return False

def keep(x, y, z):
    if z < Z_FLOOR:                              return False
    if in_parking(x, y):                         return False
    if not near_any_osm_feature(x, y, OUTLIER_RADIUS_M): return False
    return True

print(f"[{region}] B={len(buildings)} P={len(paths)} Parking={len(parking)}  "
      f"z_floor={Z_FLOOR} outlier_r={OUTLIER_RADIUS_M}")

bpy.ops.wm.open_mainfile(filepath=str(BLEND))
for o in bpy.data.objects:
    if o.type == 'MESH': break
else: raise SystemExit("no mesh")

before = len(o.data.vertices)
print(f"Before: {before} verts, {len(o.data.polygons)} faces")
bm = bmesh.new()
bm.from_mesh(o.data)
bm.verts.ensure_lookup_table()
to_remove = [v for v in bm.verts if not keep(v.co.x, v.co.y, v.co.z)]
print(f"Removing {len(to_remove)} ({100*len(to_remove)//before}%)")
bmesh.ops.delete(bm, geom=to_remove, context='VERTS')
bm.to_mesh(o.data)
bm.free()
o.data.update()
print(f"After: {len(o.data.vertices)} verts, {len(o.data.polygons)} faces")

bpy.ops.wm.save_mainfile()
bpy.ops.object.select_all(action='DESELECT')
o.select_set(True)
bpy.context.view_layer.objects.active = o
bpy.ops.export_scene.gltf(filepath=str(GLB), export_format='GLB',
                          use_selection=False, export_apply=True)
print(f"GLB: {GLB} ({os.path.getsize(GLB)} bytes)")
