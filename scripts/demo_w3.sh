#!/bin/bash
# W3 Demo Script - 8 minute demo

source /opt/ros/humble/setup.bash
cd ~/poc/poc-orin/scripts

echo "=========================================="
echo "   W3 Demo - Jetson Orin POC"
echo "=========================================="

echo ""
echo "[START] Starting W3 Launch..."
python3 w3_launch.py &
W3PID=$!
sleep 3

echo ""
echo "[ACT 1] Hardware Abstraction Layer"
echo "-------------------------------------------"
echo "  Buddy + Omni simultaneously at 1000 Hz"
ros2 topic hz /buddy/imu --window 2 &
ros2 topic hz /omni/imu --window 2 &
sleep 3
ros2 topic echo /buddy/hal/health --once 2>/dev/null

echo ""
echo "[ACT 2] State Estimator + Policy"
echo "-------------------------------------------"
echo "  500 Hz pose estimation"
ros2 topic hz /state/pose --window 2
echo "  50 Hz RL policy"
ros2 topic hz /policy/action --window 2

echo ""
echo "[ACT 3] Perception Pipeline"
echo "-------------------------------------------"
echo "  15 Hz camera + lidar"
ros2 topic hz /perception/camera --window 2

echo ""
echo "[ACT 4] Observability"
echo "-------------------------------------------"
echo "  System metrics (CPU, MEM, Temp)"
echo "  RT Jitter (avg, max, p99)"
ros2 topic echo /metrics/system --once 2>/dev/null
ros2 topic echo /metrics/rt_jitter --once 2>/dev/null

echo ""
echo "[ACT 5] Recorder"
echo "-------------------------------------------"
ros2 topic echo /recorder/status --once 2>/dev/null

echo ""
echo "[CHAOS] Fault Injection Test"
echo "-------------------------------------------"
echo "  (Simulated in W3)"

echo ""
echo "=========================================="
echo "   W3 Demo Complete"
echo "=========================================="
echo ""
echo "Running PID: $W3PID"
echo "To stop: kill $W3PID"