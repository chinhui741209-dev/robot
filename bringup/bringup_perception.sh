#!/bin/bash
# bringup_perception.sh - Perception layer bring-up with camera

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POC_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "Bring-up: Perception Layer (with Camera)"
echo "=========================================="

source /opt/ros/humble/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS2Daemon=False
export ROS_DOMAIN_ID=42
export POC_ROOT="$POC_ROOT"
export PYTHONPATH="$PYTHONPATH:$POC_ROOT"

echo "[1/5] Checking camera device..."
if [ -e /dev/video0 ]; then
    echo "  Camera found: /dev/video0"
    ls -la /dev/video*
else
    echo "  ERROR: No camera device found"
    exit 1
fi

echo "[2/5] Checking models..."
MODEL_DIR="$POC_ROOT/models/active"
if [ -f "$MODEL_DIR/detection.onnx" ]; then
    echo "  Model found: detection.onnx"
else
    echo "  WARNING: detection.onnx not found"
fi

echo "[3/5] Checking ML frameworks..."
python3 -c "import cv2" 2>/dev/null && echo "  OpenCV: OK" || echo "  OpenCV: FAIL"
python3 -c "import onnxruntime" 2>/dev/null && echo "  ONNX Runtime: OK" || echo "  ONNX Runtime: FAIL"

echo "[4/5] Starting Camera Node..."
nohup python3 "$POC_ROOT/perception/scripts/camera_node.py" > "$POC_ROOT/logs/camera.log" 2>&1 &
CAMERA_PID=$!
echo "  Camera Node PID: $CAMERA_PID"

sleep 1

echo "[5/5] Starting Perception Node..."
nohup python3 "$POC_ROOT/perception/scripts/perception_node.py" > "$POC_ROOT/logs/perception.log" 2>&1 &
PERCEPTION_PID=$!
echo "  Perception Node PID: $PERCEPTION_PID"

sleep 1

echo "[6/6] Starting Visualization Node..."
nohup python3 "$POC_ROOT/perception/scripts/visualization_node.py" > "$POC_ROOT/logs/visualization.log" 2>&1 &
VIS_PID=$!
echo "  Visualization Node PID: $VIS_PID"

sleep 1
echo ""
echo "=========================================="
echo "Perception bring-up complete (nodes running)"
echo "=========================================="
echo ""
echo "Topics:"
echo "  /camera/image_raw          - Raw camera image"
echo "  /perception/detections     - Detection results"
echo "  /perception/visualization  - Annotated image (bbox overlay)"
echo "  /perception/latency        - Inference latency"
echo ""
echo "To view camera: ros2 run image_view image_view --ros-args -r image:=/camera/image_raw"
echo "To stop: pkill -f camera_node.py; pkill -f perception_node.py; pkill -f visualization_node.py"