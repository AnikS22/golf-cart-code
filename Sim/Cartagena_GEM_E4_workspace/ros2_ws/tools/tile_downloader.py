#!/usr/bin/env python3
"""Walk Google's 3D Tiles tileset and download glTF tiles for a bbox.

Uses the Map Tiles API directly (no Blosm). Reads region config from
regions.json and downloads all glb tiles whose bounding volumes intersect
the requested bbox, recursing until geometricError <= target_error_m.

Usage: python3 tile_downloader.py <region>

Output: fau_world/<region>_tiles/*.glb  + manifest.json listing them.
"""
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

API_KEY = "AIzaSyCKpmobWicRxBIqjJQUZYdbkbkis9bOVvM"
API_HOST = "https://tile.googleapis.com"
ROOT_URL = f"{API_HOST}/v1/3dtiles/root.json?key={API_KEY}"

TOOLS = Path(__file__).resolve().parent
REGIONS = json.loads((TOOLS / 'regions.json').read_text())

# -------------------- WGS84 / ECEF math --------------------
WGS84_A = 6378137.0
WGS84_E2 = 6.69437999014e-3

def lla_to_ecef(lat_deg, lon_deg, alt_m=0.0):
    lat = math.radians(lat_deg); lon = math.radians(lon_deg)
    s, c = math.sin(lat), math.cos(lat)
    N = WGS84_A / math.sqrt(1 - WGS84_E2 * s * s)
    return ((N + alt_m) * c * math.cos(lon),
            (N + alt_m) * c * math.sin(lon),
            (N * (1 - WGS84_E2) + alt_m) * s)

def bbox_to_ecef_sphere(bbox, alt_low=-20.0, alt_high=50.0):
    """Return (center_ecef, radius_m) enclosing the bbox from alt_low to alt_high."""
    corners = []
    for lat in (bbox['south'], bbox['north']):
        for lon in (bbox['west'], bbox['east']):
            for alt in (alt_low, alt_high):
                corners.append(lla_to_ecef(lat, lon, alt))
    cx = sum(p[0] for p in corners) / len(corners)
    cy = sum(p[1] for p in corners) / len(corners)
    cz = sum(p[2] for p in corners) / len(corners)
    r = max(math.sqrt((p[0]-cx)**2 + (p[1]-cy)**2 + (p[2]-cz)**2) for p in corners)
    return ((cx, cy, cz), r)

# -------------------- tile bounding-volume geometry --------------------
def tile_box_sphere(box):
    """3D Tiles box is [cx, cy, cz, xx, xy, xz, yx, yy, yz, zx, zy, zz].
    Returns (center, bounding_sphere_radius)."""
    cx, cy, cz = box[0], box[1], box[2]
    ax = (box[3], box[4], box[5])
    ay = (box[6], box[7], box[8])
    az = (box[9], box[10], box[11])
    # Farthest corner from center is center + ax + ay + az; its distance is sqrt(|ax|^2+|ay|^2+|az|^2)
    r = math.sqrt(ax[0]**2+ax[1]**2+ax[2]**2
                + ay[0]**2+ay[1]**2+ay[2]**2
                + az[0]**2+az[1]**2+az[2]**2)
    return ((cx, cy, cz), r)

def spheres_overlap(c1, r1, c2, r2):
    dx = c1[0] - c2[0]; dy = c1[1] - c2[1]; dz = c1[2] - c2[2]
    return dx*dx + dy*dy + dz*dz <= (r1 + r2) ** 2

# -------------------- HTTP helpers --------------------
def http_get_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'claude-fau-sim/1.0'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def http_get_bytes(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'claude-fau-sim/1.0'})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()

def make_full_url(rel_uri, session):
    if not rel_uri.startswith('http'):
        rel_uri = API_HOST + rel_uri
    sep = '&' if '?' in rel_uri else '?'
    url = f"{rel_uri}{sep}key={API_KEY}"
    if session and 'session=' not in url:
        url = f"{url}&session={session}"
    return url

def extract_session(uri):
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(uri).query)
    vals = qs.get('session')
    return vals[0] if vals else None

# -------------------- walker --------------------
def walk(tile, target_error, target_center, target_radius, session, out_dir, tiles, depth=0):
    box = tile.get('boundingVolume', {}).get('box')
    if box is None:
        return  # only handle box volumes for now
    tc, tr = tile_box_sphere(box)
    if not spheres_overlap(tc, tr, target_center, target_radius):
        return

    err = tile.get('geometricError', 0.0)
    content = tile.get('content', {}) or {}
    uri = content.get('uri', '')

    # If the content is a nested tileset (JSON), fetch and recurse into its root.
    if uri and (uri.endswith('.json') or '.json?' in uri):
        if not session:
            session = extract_session(uri)
        try:
            sub = http_get_json(make_full_url(uri, session))
        except Exception as e:
            print(f"  [depth {depth}] sub-tileset fetch failed: {e}")
        else:
            sub_root = sub.get('root', sub)
            walk(sub_root, target_error, target_center, target_radius, session, out_dir, tiles, depth + 1)
    elif uri.endswith('.glb') or '.glb?' in uri:
        if not session:
            session = extract_session(uri)
        # Download if this tile is at the right LOD (err <= target) OR if it has no children
        children = tile.get('children', [])
        if err <= target_error or not children:
            fname = f"tile_{len(tiles):04d}_err{int(err)}.glb"
            out = out_dir / fname
            if not out.exists():
                full = make_full_url(uri, session)
                try:
                    data = http_get_bytes(full)
                except Exception as e:
                    print(f"  [depth {depth}] glb fetch failed: {e}")
                    return
                out.write_bytes(data)
                tiles.append({'file': fname, 'err': err, 'depth': depth,
                              'center_ecef': list(tc), 'radius_m': tr,
                              'size_bytes': len(data)})
                if len(tiles) % 10 == 0:
                    print(f"  [{len(tiles)}] depth={depth} err={err:.1f} size={len(data) // 1024}kB")
                time.sleep(0.03)  # polite
        # also recurse into children if we still need more detail
        if err > target_error:
            for child in children:
                walk(child, target_error, target_center, target_radius, session, out_dir, tiles, depth + 1)
    else:
        for child in tile.get('children', []):
            walk(child, target_error, target_center, target_radius, session, out_dir, tiles, depth + 1)

# -------------------- main --------------------
def main():
    if len(sys.argv) < 2:
        raise SystemExit(f"usage: {sys.argv[0]} <region>  (available: {list(REGIONS)})")
    region = sys.argv[1]
    cfg = REGIONS[region]
    bbox = cfg['bbox']
    target_err = cfg.get('custom', {}).get('target_error_m', 2.0)
    bbox_alt_low  = cfg.get('custom', {}).get('alt_low_m', -20.0)
    bbox_alt_high = cfg.get('custom', {}).get('alt_high_m', 80.0)

    out_dir = TOOLS / 'fau_world' / f'{region}_tiles'
    out_dir.mkdir(parents=True, exist_ok=True)

    target_center, target_radius = bbox_to_ecef_sphere(bbox, bbox_alt_low, bbox_alt_high)
    print(f"[{region}] target_err={target_err}m  bbox center={target_center}  r={target_radius:.1f}m")
    print(f"Fetching root tileset...")
    root = http_get_json(ROOT_URL)

    tiles = []
    walk(root['root'], target_err, target_center, target_radius, None, out_dir, tiles)

    manifest = {
        'region': region,
        'bbox': bbox,
        'target_error_m': target_err,
        'tile_count': len(tiles),
        'total_bytes': sum(t['size_bytes'] for t in tiles),
        'tiles': tiles,
    }
    (out_dir / 'manifest.json').write_text(json.dumps(manifest, indent=1))
    print(f"Downloaded {len(tiles)} tiles ({manifest['total_bytes'] // (1024*1024)} MB) -> {out_dir}")

if __name__ == '__main__':
    main()
