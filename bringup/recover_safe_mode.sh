#!/bin/bash
# recover_safe_mode.sh - Safe mode recovery

set -e

echo "=========================================="
echo "Safe Mode Recovery"
echo "=========================================="

echo "[1/3] Stopping all ROS 2 nodes..."
pkill -f "w3_launch" 2>/dev/null || true
pkill -f "policy_node" 2>/dev/null || true
pkill -f "state_estimator" 2>/dev/null || true
pkill -f "hal_buddy" 2>/dev/null || true

echo "[2/3] Cleaning up processes..."
sleep 1
pkill -9 -f "rclpy" 2>/dev/null || true

echo "[3/3] Checking system state..."
echo "  ROS_DOMAIN_ID: ${ROS_DOMAIN_ID:-42}"
echo "  Memory: $(free -h | awk '/^Mem:/{print $3}')"

echo ""
echo "=========================================="
echo "Safe mode ready"
echo "=========================================="
echo ""
echo "To restart: ./bringup_all.sh"