#!/bin/bash
# bringup_perception.sh - Perception layer bring-up
# Layer: AI Runtime + Perception + Target Tracking

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POC_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "Bring-up: Perception Layer"
echo "=========================================="

source /opt/ros/humble/setup.bash
export POC_ROOT="$POC_ROOT"
export PYTHONPATH="$PYTHONPATH:$POC_ROOT"

echo "[1/3] Checking models..."
MODEL_DIR="$POC_ROOT/models/active"
if [ -d "$MODEL_DIR" ]; then
    MODEL_COUNT=$(find "$MODEL_DIR" -name "*.onnx" -o -name "*.trt" 2>/dev/null | wc -l)
    echo "  Models found: $MODEL_COUNT"
else
    echo "  Models directory: Not found"
fi

echo "[2/3] Checking ML frameworks..."
python3 -c "import torch" 2>/dev/null && echo "  PyTorch: OK" || echo "  PyTorch: Not installed"
python3 -c "import onnx" 2>/dev/null && echo "  ONNX: OK" || echo "  ONNX: Not installed"
python3 -c "import onnxruntime" 2>/dev/null && echo "  ONNXRuntime: OK" || echo "  ONNXRuntime: Not installed"

echo "[3/3] Perception nodes..."
if [ -d "$POC_ROOT/perception" ]; then
    echo "  Perception directory: Found"
else
    echo "  Perception: Not found"
fi

echo ""
echo "=========================================="
echo "Perception bring-up complete"
echo "=========================================="
echo ""
echo "Next: ./launch_demo.sh or ./launch_mission.sh"