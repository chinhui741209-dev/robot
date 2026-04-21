#!/bin/bash
# bringup_core.sh - Core system bring-up
# Layer: Boot + Core Runtime

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POC_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "Bring-up: Core System"
echo "=========================================="

# Check ROS 2 environment
if [ ! -f /opt/ros/humble/setup.bash ]; then
    echo "ERROR: ROS 2 Humble not found"
    exit 1
fi

source /opt/ros/humble/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS2Daemon=False
export ROS_DOMAIN_ID=42

echo "[1/5] Checking system..."
uname -a
echo "  CPU: $(nproc) cores"
echo "  Memory: $(free -h | awk '/^Mem:/{print $2}')"

echo "[2/5] Checking ROS 2..."
ros2 pkg list > /dev/null 2>&1 && echo "  ROS 2: OK" || { echo "  ROS 2: FAIL"; exit 1; }

echo "[3/5] Checking workspace..."
export POC_ROOT="$POC_ROOT"
export PYTHONPATH="$PYTHONPATH:$POC_ROOT"
echo "  POC_ROOT: $POC_ROOT"

echo "[4/5] Creating log directory..."
LOG_DIR="$POC_ROOT/logs"
mkdir -p "$LOG_DIR"
echo "  Log directory: $LOG_DIR"

echo "[5/5] Checking HAL modules..."
if [ -d "$POC_ROOT/hal" ]; then
    echo "  HAL: Found"
else
    echo "  HAL: Not found"
fi

echo ""
echo "=========================================="
echo "Core bring-up complete"
echo "=========================================="
echo ""
echo "Next: ./bringup_control.sh"