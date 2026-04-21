#!/bin/bash
# Regenerate Python LCM bindings from .lcm schema files.
# Requires: lcm-gen (install via: sudo apt install lcm-dev)
# Output replaces robot_lcm_types.py with proper lcm-gen generated classes.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$SCRIPT_DIR/generated"
mkdir -p "$OUT"

for f in "$SCRIPT_DIR"/*.lcm; do
    [ -f "$f" ] || continue
    echo "Generating bindings for $f..."
    lcm-gen -p --ppath "$OUT" "$f"
done

echo "Done. Add $OUT to PYTHONPATH."
