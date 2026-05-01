#!/usr/bin/env bash
# One-shot build of a region's Gazebo-ready photoreal mesh.
#
# Usage:  tools/build_world.sh <region>   [--skip-download]
#
# Pipeline (reads tools/regions.json):
#   1. OSM polygons via Overpass               -> fau_world/osm_polygons.json
#   2. Download Google 3D Tiles by bbox        -> fau_world/<region>_tiles/*.glb
#   3. gltf-transform merge all tiles          -> fau_world/<region>_merged.glb
#   4. Blender: ECEF->ENU transform            -> fau_world/<region>.blend
#   5. Programmatic reanchor to ground z=0     -> updates .blend + .glb
#   6. OSM polygon crop                        -> final .glb
#
# --skip-download reuses the existing tiles dir (fast iteration on crop).
set -euo pipefail

REGION="${1:-}"
[ -z "$REGION" ] && { echo "usage: $0 <region> [--skip-download]"; exit 1; }
shift
SKIP_DOWNLOAD=0
[ "${1:-}" = "--skip-download" ] && SKIP_DOWNLOAD=1

TOOLS="$(cd "$(dirname "$0")" && pwd)"
BFORA="$HOME/.local/bin/bforartists"
GLTF_XFORM="$HOME/.npm-global/bin/gltf-transform"
TILE_DIR="$TOOLS/fau_world/${REGION}_tiles"
MERGED_GLB="$TOOLS/fau_world/${REGION}_merged.glb"

echo "=== [1/6] OSM polygons ==="
python3 "$TOOLS/fetch_osm.py" "$REGION"

if [ "$SKIP_DOWNLOAD" -eq 0 ]; then
  echo "=== [2/6] Download Google 3D Tiles ==="
  python3 "$TOOLS/tile_downloader.py" "$REGION" | tail -5
else
  echo "=== [2/6] Download SKIPPED ==="
fi

echo "=== [3/6] gltf-transform merge $(ls "$TILE_DIR"/*.glb | wc -l) tiles ==="
"$GLTF_XFORM" merge "$TILE_DIR"/*.glb "$MERGED_GLB" --merge-scenes 2>&1 | tail -2

echo "=== [4/6] ECEF->ENU transform (Blender) ==="
"$BFORA" --background --python "$TOOLS/merge_tiles.py" -- "$REGION" \
  2>&1 | grep -E "Imported|Combined|local ENU|Saved" || true

echo "=== [5/6] Reanchor ground to z=0 ==="
"$BFORA" --background --python "$TOOLS/reanchor.py" -- "$REGION" \
  2>&1 | grep -E "n verts|post-shift|GLB|Error" || true

echo "=== [6/6] Crop to OSM polygons ==="
"$BFORA" --background --python "$TOOLS/crop_mesh.py" -- "$REGION" \
  2>&1 | grep -E "\[$REGION\]|Before|Removing|After|GLB|Error" || true

FINAL_GLB="$TOOLS/fau_world/${REGION}.glb"
echo "=== Done ==="
echo "Final glb: $FINAL_GLB ($(du -h "$FINAL_GLB" | cut -f1))"
