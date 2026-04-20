#!/bin/bash
source /opt/ros/humble/setup.bash

echo "=========================================="
echo "   W2 Demo - Jetson Orin POC"
echo "=========================================="

cd ~/poc/poc-orin/scripts

echo ""
echo "[1] W2 Architecture"
echo "-------------------------------------------"
echo "  Buddy (1000 Hz) + Omni (1000 Hz)"
echo "  State Estimator (500 Hz)"
echo "  Policy (50 Hz)"
echo "  Perception (15 Hz)"
echo ""

echo "[2] Starting W2 Components..."
echo "-------------------------------------------"
python3 w2_launch.py &
sleep 3
echo "  Started: $(date)"
echo ""

echo "[3] Topic List"
echo "-------------------------------------------"
ros2 topic list
echo ""

echo "[4] Topic Rates"
echo "-------------------------------------------"
for t in /buddy/imu /omni/imu /state/pose /policy/action /perception/camera; do
    echo -n "  $t: "
    ros2 topic hz $t --window 1 2>/dev/null | grep average || echo "checking..."
done

echo ""
echo "[5] Sample Data"
echo "-------------------------------------------"
ros2 topic echo /buddy/imu --once 2>/dev/null | head -15
echo ""

echo "[6] Recorder Status"
echo "-------------------------------------------"
ros2 topic echo /recorder/status --once 2>/dev/null
echo ""

echo "=========================================="
echo "   W2 Demo Complete"
echo "=========================================="