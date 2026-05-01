"""Fetch OSM building + path + parking polygons for a region.

Usage: python3 fetch_osm.py <region>

Reads regions.json, writes <region>/osm_polygons.json.
"""
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
cfg_all = json.loads((TOOLS / 'regions.json').read_text())

if len(sys.argv) < 2:
    raise SystemExit(f"usage: {sys.argv[0]} <region>  (available: {list(cfg_all)})")
region = sys.argv[1]
cfg = cfg_all[region]

bbox = cfg['bbox']
hw_rx = cfg['overpass']['highways']

query = f"""[out:json][timeout:25];
(
  way["building"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
  way["highway"~"{hw_rx}"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
  way["amenity"="parking"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
  way["amenity"="university"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
  way["landuse"="education"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
  relation["amenity"="university"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
);
out body;
>;
out skel qt;
"""

print(f"Querying Overpass for region {region}...")
req = urllib.request.Request(
    'https://overpass-api.de/api/interpreter',
    data=urllib.parse.urlencode({'data': query}).encode(),
    headers={'User-Agent': 'claude-fau-sim/1.0 (mpcrlab@gmail.com)'},
)

for attempt in range(3):
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = json.load(resp)
        break
    except Exception as e:
        print(f"attempt {attempt + 1} failed: {e}")
        if attempt == 2:
            raise
        import time; time.sleep(5)

nodes = {el['id']: (el['lat'], el['lon']) for el in raw['elements'] if el['type'] == 'node'}
ways = [el for el in raw['elements'] if el['type'] == 'way']

buildings, paths, parking, campus = [], [], [], []
for w in ways:
    coords = [nodes[nid] for nid in w['nodes'] if nid in nodes]
    if len(coords) < 2:
        continue
    tags = w.get('tags', {})
    if 'building' in tags:
        if coords[0] != coords[-1]: coords.append(coords[0])
        buildings.append({'name': tags.get('name', ''), 'coords': coords})
    elif 'highway' in tags:
        paths.append({'type': tags['highway'], 'coords': coords})
    elif tags.get('amenity') == 'parking':
        if coords[0] != coords[-1]: coords.append(coords[0])
        parking.append({'coords': coords})
    elif tags.get('amenity') == 'university' or tags.get('landuse') == 'education':
        if coords[0] != coords[-1]: coords.append(coords[0])
        campus.append({'name': tags.get('name', ''), 'coords': coords})

out = TOOLS / 'fau_world' / 'osm_polygons.json'
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps({
    'region': region,
    'bbox': bbox,
    'buildings': buildings,
    'paths': paths,
    'parking': parking,
    'campus': campus,
}, indent=1))
print(f"Saved {len(buildings)} buildings, {len(paths)} paths, "
      f"{len(parking)} parking, {len(campus)} campus -> {out}")
