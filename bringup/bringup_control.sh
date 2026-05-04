#!/bin/bash
# bringup_control.sh - Control layer bring-up
# Layer: HAL (LCM 1kHz) → State Estimator (LCM 500Hz) → Bridge → Policy → Recorder

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POC_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "WARNING: This Python/LCM control path is LEGACY."
echo "Please use ./bringup_control_cpp.sh for the primary RT path."
echo "=========================================="
echo "Bring-up: Control Layer (Legacy Python/LCM Implementation)"

source /opt/ros/humble/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS2Daemon=False
export ROS_DOMAIN_ID=42
export POC_ROOT="$POC_ROOT"
export PYTHONPATH="$PYTHONPATH:$POC_ROOT"

echo "[1/5] Starting HAL Buddy (LCM 1kHz)..."
if [ -f "$POC_ROOT/hal/scripts/hal_buddy_node.py" ]; then
    nohup python3 "$POC_ROOT/hal/scripts/hal_buddy_node.py" > "$POC_ROOT/logs/hal.log" 2>&1 &
    echo "  HAL PID: $!"
    sleep 0.5
else
    echo "  ERROR: hal_buddy_node.py not found"; exit 1
fi

echo "[2/5] Starting State Estimator (LCM 500Hz)..."
if [ -f "$POC_ROOT/rt_control/state_estimator.py" ]; then
    nohup python3 "$POC_ROOT/rt_control/state_estimator.py" > "$POC_ROOT/logs/state.log" 2>&1 &
    echo "  State PID: $!"
    sleep 0.5
else
    echo "  ERROR: state_estimator.py not found"; exit 1
fi

echo "[3/5] Starting LCM→ROS2 Bridge..."
if [ -f "$POC_ROOT/middleware/lcm_ros2_bridge.py" ]; then
    nohup python3 "$POC_ROOT/middleware/lcm_ros2_bridge.py" > "$POC_ROOT/logs/bridge.log" 2>&1 &
    echo "  Bridge PID: $!"
    sleep 1   # wait for bridge to publish before policy/recorder subscribe
else
    echo "  ERROR: lcm_ros2_bridge.py not found"; exit 1
fi

echo "[4/5] Starting Policy Node (LCM IMU / ROS2 action)..."
if [ -f "$POC_ROOT/policy/policy_node.py" ]; then
    nohup python3 "$POC_ROOT/policy/policy_node.py" > "$POC_ROOT/logs/policy.log" 2>&1 &
    echo "  Policy PID: $!"
    sleep 0.5
else
    echo "  ERROR: policy_node.py not found"; exit 1
fi

echo "[5/5] Checking ROS 2 topics (via bridge)..."
sleep 1
ros2 topic list 2>/dev/null | grep -E "(buddy|policy|state)" || echo "  No bridged topics yet — check logs/bridge.log"

echo ""
echo "=========================================="
echo "Control bring-up complete"
echo "  LCM channels : BUDDY_IMU(1kHz) STATE_POSE(500Hz)"
echo "  ROS2 topics  : /buddy/imu /state/pose /policy/action (via bridge)"
echo "=========================================="
echo ""
echo "Next: ./bringup_perception.sh"