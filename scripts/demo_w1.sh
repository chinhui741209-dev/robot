#!/bin/bash
# W1 Demo - 展示 W1 成果

source /opt/ros/humble/setup.bash

echo "=========================================="
echo "   W1 Demo - Jetson Orin POC"
echo "=========================================="
echo ""

echo "[1] Topic List"
echo "-------------------------------------------"
ros2 topic list
echo ""

echo "[2] IMU Rate (1000 Hz target)"
echo "-------------------------------------------"
ros2 topic hz /buddy/imu --window 3 | head -5
echo ""

echo "[3] State Pose Rate (500 Hz target)"
echo "-------------------------------------------"
ros2 topic hz /state/pose --window 3 | head -5
echo ""

echo "[4] Policy Action Rate (50 Hz target)"
echo "-------------------------------------------"
ros2 topic hz /policy/action --window 3 | head -5
echo ""

echo "[5] Sample IMU Data"
echo "-------------------------------------------"
ros2 topic echo /buddy/imu --once
echo ""

echo "[6] Sample Policy Action"
echo "-------------------------------------------"
ros2 topic echo /policy/action --once
echo ""

echo "[7] Recorder Status"
echo "-------------------------------------------"
ros2 topic echo /recorder/status --once
echo ""

echo "=========================================="
echo "   Demo Complete"
echo "=========================================="