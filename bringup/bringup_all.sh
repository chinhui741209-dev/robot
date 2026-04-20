#!/bin/bash
# bringup_all.sh - Complete system bring-up
# Layers: Boot -> Core -> Control -> Perception -> App

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "Bring-up: Complete System"
echo "=========================================="

echo "[Step 1/3] Core bring-up..."
bash "$SCRIPT_DIR/bringup_core.sh"

echo ""
echo "[Step 2/3] Control bring-up..."
bash "$SCRIPT_DIR/bringup_control.sh"

echo ""
echo "[Step 3/3] Perception bring-up..."
bash "$SCRIPT_DIR/bringup_perception.sh"

echo ""
echo "=========================================="
echo "Complete system bring-up done!"
echo "=========================================="
echo ""
echo "To start demo: ./launch_demo.sh"
echo "To start mission: ./launch_mission.sh"