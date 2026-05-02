#!/bin/bash
# build_tensorrt.sh - Convert ONNX models to TensorRT Engines
# This script should be run on the target Jetson Orin.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ACTIVE_MODELS="$SCRIPT_DIR/active"
TRT_EXEC="trtexec"

# Check if trtexec exists
if ! command -v $TRT_EXEC &> /dev/null; then
    echo "Error: trtexec not found. Is JetPack installed?"
    echo "Try: export PATH=\$PATH:/usr/src/tensorrt/bin"
    exit 1
fi

echo "=========================================="
echo "TensorRT Model Conversion (Orin Optimized)"
echo "=========================================="

# 1. Detection Model (FP16)
echo "[1/2] Converting Detection Model..."
$TRT_EXEC --onnx="$ACTIVE_MODELS/detection_v2.onnx" \
          --saveEngine="$ACTIVE_MODELS/detection_v2.engine" \
          --fp16 \
          --inputIOFormats=fp16:chw \
          --outputIOFormats=fp16:chw \
          --workspace=2048

# 2. Simple Policy Model (FP16)
echo "[2/2] Converting Policy Model..."
$TRT_EXEC --onnx="$ACTIVE_MODELS/simple_policy.onnx" \
          --saveEngine="$ACTIVE_MODELS/simple_policy.engine" \
          --fp16 \
          --workspace=1024

echo ""
echo "Conversion Complete. Engines saved in robot/models/active/"
echo "=========================================="
