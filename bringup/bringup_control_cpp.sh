# #!/bin/bash
# bringup_control_cpp.sh - Control layer bring-up (C++ RT version)
# Layer: HAL (C++ SHM) → State Estimator (C++ SHM) → ROS2 Bridge (C++ SHM to ROS2) → Policy (ROS2)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POC_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$POC_ROOT/rt_cpp/build"

echo "=========================================="
echo "Bring-up: Control Layer (C++ RT Implementation)"
echo "=========================================="

source /opt/ros/humble/setup.bash || true
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS2Daemon=False
export ROS_DOMAIN_ID=42
export POC_ROOT="$POC_ROOT"
export PYTHONPATH="$PYTHONPATH:$POC_ROOT"

# Create logs directory if missing
mkdir -p "$POC_ROOT/logs"

echo "[1/4] Starting C++ HAL Buddy (SHM 1kHz)..."
if [ -f "$BUILD_DIR/hal_buddy" ]; then
    nohup "$BUILD_DIR/hal_buddy" > "$POC_ROOT/logs/hal_cpp.log" 2>&1 &
    echo "  HAL PID: $!"
    sleep 0.5
else
    echo "  ERROR: hal_buddy binary not found. Build it in robot/rt_cpp/build/"; exit 1
fi

echo "[2/4] Starting C++ State Estimator (SHM 500Hz)..."
if [ -f "$BUILD_DIR/state_estimator" ]; then
    nohup "$BUILD_DIR/state_estimator" > "$POC_ROOT/logs/state_cpp.log" 2>&1 &
    echo "  State PID: $!"
    sleep 0.5
else
    echo "  ERROR: state_estimator binary not found"; exit 1
fi

echo "[3/4] Starting C++ ROS2 Bridge (SHM to ROS2 100Hz)..."
# We expect ros2_bridge to be in the same build dir or installed via colcon
if [ -f "$BUILD_DIR/ros2_bridge" ]; then
    nohup "$BUILD_DIR/ros2_bridge" > "$POC_ROOT/logs/bridge_cpp.log" 2>&1 &
    echo "  Bridge PID: $!"
    sleep 1
else
    # Fallback to colcon install path if not in build dir
    BRIDGE_BIN="$POC_ROOT/ros2_ws/install/robot_rt_cpp/lib/robot_rt_cpp/ros2_bridge"
    if [ -f "$BRIDGE_BIN" ]; then
        nohup "$BRIDGE_BIN" > "$POC_ROOT/logs/bridge_cpp.log" 2>&1 &
        echo "  Bridge PID: $!"
        sleep 1
    else
        echo "  ERROR: ros2_bridge binary not found"; exit 1
    fi
fi

echo "[4/4] Starting Policy Node (Subscribing ROS2 /buddy/imu)..."
if [ -f "$POC_ROOT/policy/policy_node.py" ]; then
    # Note: policy_node.py might need a small modification to use ROS2 imu instead of LCM
    nohup python3 "$POC_ROOT/policy/policy_node.py" > "$POC_ROOT/logs/policy_cpp.log" 2>&1 &
    echo "  Policy PID: $!"
    sleep 0.5
else
    echo "  ERROR: policy_node.py not found"; exit 1
fi

echo "[Check] Verifying ROS 2 topics..."
sleep 1
ros2 topic list 2>/dev/null | grep -E "(buddy|policy|state)" || echo "  Warning: No ROS2 topics detected yet."

echo ""
echo "=========================================="
echo "C++ Control bring-up complete"
echo "  Architecture: C++ Standalone RT (Shared Memory) + C++ ROS2 Bridge"
echo "=========================================="
