#!/bin/bash
# launch_mission.sh - Launch mission manager

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POC_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "Launch: Mission Manager"
echo "=========================================="

source /opt/ros/humble/setup.bash
export POC_ROOT="$POC_ROOT"

echo "NOTE: Mission manager not yet implemented"
echo ""
echo "Available options:"
echo "  - Demo: ./launch_demo.sh"
echo "  - Tests: ./run_e2e_test.sh"