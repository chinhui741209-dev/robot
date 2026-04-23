#!/bin/bash
# bringup_all.sh - Complete system bring-up
# Layers: Boot -> Core -> Control -> Perception -> App

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "Bring-up: Complete System"
echo "=========================================="

echo "[Step 1/1] Core bring-up..."
bash "$SCRIPT_DIR/bringup_core.sh"

echo ""
echo "=========================================="
echo "Core system bring-up done! (Skipping conflicting Control/Perception for Sim Demo)"
echo "=========================================="
echo ""
echo ">>> Auto-starting Demo as requested by CI/CD configuration..."
exec bash "$SCRIPT_DIR/launch_demo.sh"