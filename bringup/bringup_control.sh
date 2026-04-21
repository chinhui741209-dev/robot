#!/bin/bash
# bringup_control.sh - Control layer bring-up
# Layer: State Manager + Policy + Control Bridge

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POC_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "Bring-up: Control Layer"
echo "=========================================="

source /opt/ros/humble/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS2Daemon=False
export ROS_DOMAIN_ID=42
export POC_ROOT="$POC_ROOT"
export PYTHONPATH="$PYTHONPATH:$POC_ROOT"

echo "[1/4] Starting HAL nodes..."

# Check if HAL node exists
if [ -f "$POC_ROOT/hal/scripts/hal_buddy_node.py" ]; then
    echo "  Starting HALBuddy node..."
    nohup python3 "$POC_ROOT/hal/scripts/hal_buddy_node.py" > "$POC_ROOT/logs/hal.log" 2>&1 &
    HAL_PID=$!
    echo "  HAL PID: $HAL_PID"
    sleep 1
else
    echo "  HAL: Not found"
fi

echo "[2/4] Starting State Estimator..."
if [ -f "$POC_ROOT/rt_control/state_estimator.py" ]; then
    echo "  Starting State Estimator..."
    nohup python3 "$POC_ROOT/rt_control/state_estimator.py" > "$POC_ROOT/logs/state.log" 2>&1 &
    STATE_PID=$!
    echo "  State PID: $STATE_PID"
    sleep 1
else
    echo "  State Estimator: Not found"
fi

echo "[3/4] Starting Policy Node..."
if [ -f "$POC_ROOT/policy/policy_node.py" ]; then
    echo "  Starting Policy node..."
    nohup python3 "$POC_ROOT/policy/policy_node.py" > "$POC_ROOT/logs/policy.log" 2>&1 &
    POLICY_PID=$!
    echo "  Policy PID: $POLICY_PID"
    sleep 1
else
    echo "  Policy: Not found"
fi

echo "[4/4] Checking topics..."
sleep 1
ros2 topic list 2>/dev/null | grep -E "(buddy|policy|state)" || echo "  No topics found"

echo ""
echo "=========================================="
echo "Control bring-up complete"
echo "=========================================="
echo ""
echo "Next: ./bringup_perception.sh"