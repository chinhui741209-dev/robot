#!/bin/bash
# TensorRT Engine Build Script
# Requires full JetPack installation with CUDA support

set -e

MODEL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "TensorRT Engine Build"
echo "=========================================="

# Check TensorRT
if ! /usr/src/tensorrt/bin/trtexec --version >/dev/null 2>&1; then
    echo "ERROR: TensorRT not available"
    exit 1
fi

# Build simple_policy engine
echo "[1/2] Building simple_policy.trt..."
/usr/src/tensorrt/bin/trtexec \
    --onnx="$MODEL_DIR/simple_policy.onnx" \
    --saveEngine="$MODEL_DIR/simple_policy.trt" \
    --fp16 \
    --skipInference

echo "[2/2] Building detection.trt..."
/usr/src/tensorrt/bin/trtexec \
    --onnx="$MODEL_DIR/detection.onnx" \
    --saveEngine="$MODEL_DIR/detection.trt" \
    --fp16 \
    --skipInference

echo ""
echo "=========================================="
echo "TensorRT Engines Built"
echo "=========================================="
ls -la "$MODEL_DIR"/*.trt
