#!/bin/bash
# W3 E2E Launch Script
# Usage: ./e2e_launch.sh --robots buddy,omni --mode demo

ROBOTS="buddy,omni"
MODE="demo"

while [[ $# -gt 0 ]]; do
  case $1 in
    --robots) ROBOTS=$2; shift 2 ;;
    --mode) MODE=$2; shift 2 ;;
    *) shift ;;
  esac
done

echo "=========================================="
echo "   W3 E2E Launch"
echo "=========================================="
echo "Robots: $ROBOTS"
echo "Mode: $MODE"
echo ""

source /opt/ros/humble/setup.bash
cd ~/poc/poc-orin/scripts

echo "[1] Starting W3 Launch..."
python3 w3_launch.py &
W3PID=$!

sleep 2

echo "[2] Verifying topics..."
ros2 topic list

echo "[3] System status..."
echo "    PID: $W3PID"
echo ""

echo "=========================================="
echo "   E2E Running"
echo "=========================================="
echo ""
echo "To stop: kill $W3PID"