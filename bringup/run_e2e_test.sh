#!/bin/bash
# run_e2e_test.sh - End-to-End tests

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POC_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "E2E Tests"
echo "=========================================="

source /opt/ros/humble/setup.bash
export POC_ROOT="$POC_ROOT"

# Run smoke test first
echo "[1/2] Running smoke tests..."
bash "$SCRIPT_DIR/run_smoke_test.sh" || exit 1

echo ""
echo "[2/2] Running E2E flow test..."

# Test bring-up flow
echo "Testing bring-up flow..."
bash "$SCRIPT_DIR/bringup_core.sh" > /dev/null 2>&1

echo ""
echo "=========================================="
echo "E2E Tests Complete"
echo "=========================================="