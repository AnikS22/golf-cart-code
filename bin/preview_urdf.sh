#!/usr/bin/env bash
# preview_urdf.sh — flatten the digital-twin URDF on macOS for offline viewing.
#
# Generates Sim/preview/gem_e4_preview.urdf which Foxglove Studio
# (https://foxglove.dev — free, native macOS) can load:
#
#   1. Open Foxglove Studio
#   2. + → Open local file → choose Sim/preview/gem_e4_preview.urdf
#   3. Add a "3D" panel; in panel settings, point Robot description to that file
#
# You'll see the GEM e4 chassis as a white box with all 9 sensors (LiDAR,
# 6 cameras, 2 GNSS antennas, IMU) at their canonical mount poses.
#
# To regenerate after editing cart_parameters.xacro, just run this again.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
URDF_DIR="$REPO/Sim/Cartagena_GEM_E4_workspace/ros2_ws/src/gem_sim/urdf"
PREVIEW_DIR="$REPO/Sim/preview"
VENV="/tmp/xacro_venv"

mkdir -p "$PREVIEW_DIR"

# Install xacro into a throwaway venv if not already present
if [ ! -x "$VENV/bin/xacro" ]; then
  echo "==> installing xacro into $VENV"
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --quiet xacro
fi

# xacro resolves $(find pkg) by searching its CWD and a few standard paths.
# We use a fake package name "xacro_search_path" pointing at the urdf dir
# via a symlink, so $(find xacro_search_path) resolves to our urdf folder.
# Cleaner: just run xacro from the urdf dir.
INPUT="$PREVIEW_DIR/gem_e4_preview.urdf.xacro"
OUTPUT="$PREVIEW_DIR/gem_e4_preview.urdf"

# Set up a search path symlink so $(find xacro_search_path) resolves to
# our urdf source dir (where cart_parameters.xacro and gem_e4_sensors live)
TMPLINK="/tmp/xacro_search_path_link"
rm -rf "$TMPLINK"
ln -s "$URDF_DIR" "$TMPLINK"

# Run xacro with a custom search path so $(find ...) finds our xacros
# We'll provide the include files via PYTHONPATH-style search
export ROS_PACKAGE_PATH="${TMPLINK%/*}"

# Hack: copy the include files into the preview dir so $(find ...) just
# finds them via a faux package next to the input file
cp "$URDF_DIR/cart_parameters.xacro"     "$PREVIEW_DIR/cart_parameters.xacro"
cp "$URDF_DIR/gem_e4_sensors.urdf.xacro" "$PREVIEW_DIR/gem_e4_sensors.urdf.xacro"

# Substitute the $(find xacro_search_path) macro with the literal path
sed -E "s|\\\$\\(find xacro_search_path\\)|$PREVIEW_DIR|g" \
    "$INPUT" > "$PREVIEW_DIR/.gem_e4_preview_resolved.urdf.xacro"

"$VENV/bin/xacro" "$PREVIEW_DIR/.gem_e4_preview_resolved.urdf.xacro" -o "$OUTPUT"
rm -f "$PREVIEW_DIR/.gem_e4_preview_resolved.urdf.xacro"

# Validate well-formed XML
if command -v xmllint >/dev/null 2>&1; then
  xmllint --noout "$OUTPUT" && echo "✓ XML valid"
fi

echo
echo "Generated $OUTPUT"
echo
echo "View with Foxglove Studio:"
echo "  1. open -a 'Foxglove Studio' $OUTPUT  (or drag-drop into Foxglove)"
echo "  2. Add a 3D panel; set Robot description → URDF file"
