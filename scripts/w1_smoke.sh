#!/bin/bash
# W1 Smoke Test - Starts all W1 components

set -e

echo "=== W1 Smoke Test ==="

source /opt/ros/humble/setup.bash

cd ~/poc/poc-orin

# Start HAL (if not running)
echo "[1/4] Starting HAL..."
if ! pgrep -f "hal_buddy_node" > /dev/null; then
    cd hal/scripts
    nohup python3 hal_buddy_node.py > /tmp/hal.log 2>&1 &
    sleep 2
fi

# Start State Estimator
echo "[2/4] Starting State Estimator..."
cd ~/poc/poc-orin/rt_control
nohup python3 state_estimator.py > /tmp/state_est.log 2>&1 &
sleep 2

# Start Policy
echo "[3/4] Starting Policy..."
cd ~/poc/poc-orin/policy
nohup python3 policy_node.py > /tmp/policy.log 2>&1 &
sleep 2

# Start Recorder
echo "[4/4] Starting Recorder..."
cd ~/poc/poc-orin/middleware
nohup python3 recorder_node.py > /tmp/recorder.log 2>&1 &
sleep 2

# Verify
echo ""
echo "=== Verification ==="
ros2 topic list
ros2 topic hz /buddy/imu --window 3 || true
ros2 topic hz /policy/action --window 3 || true

echo ""
echo "=== W1 Smoke Complete ==="
echo "Log files:"
echo "  /tmp/hal.log"
echo "  /tmp/state_est.log"
echo "  /tmp/policy.log"
echo "  /tmp/recorder.log"