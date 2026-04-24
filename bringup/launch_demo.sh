#!/bin/bash
# launch_demo.sh - Launch demo application

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POC_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "Launch: Demo Application"
echo "=========================================="

source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=42
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export POC_ROOT="$POC_ROOT"
export PYTHONPATH="$PYTHONPATH:$POC_ROOT"

# Check if W3 launch exists (E2E demo)
if [ -f "$POC_ROOT/scripts/w3_launch.py" ]; then
    echo "Starting W3 E2E Demo..."
    echo "Press Ctrl-C to stop"
    python3 "$POC_ROOT/scripts/w3_launch.py"
else
    echo "ERROR: Demo not found"
    exit 1
fi