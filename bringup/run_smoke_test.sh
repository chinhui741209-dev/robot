#!/bin/bash
# run_smoke_test.sh - Smoke tests

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POC_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "Smoke Tests"
echo "=========================================="

source /opt/ros/humble/setup.bash
export POC_ROOT="$POC_ROOT"

PASSED=0
FAILED=0

test_ros2() {
    echo -n "Testing ROS 2... "
    if ros2 pkg list > /dev/null 2>&1; then
        echo "PASS"
        PASSED=$((PASSED+1))
    else
        echo "FAIL"
        FAILED=$((FAILED+1))
    fi
}

test_python() {
    echo -n "Testing Python... "
    if python3 --version > /dev/null 2>&1; then
        echo "PASS"
        PASSED=$((PASSED+1))
    else
        echo "FAIL"
        FAILED=$((FAILED+1))
    fi
}

test_hal() {
    echo -n "Testing HAL module... "
    if [ -d "$POC_ROOT/hal" ]; then
        echo "PASS"
        PASSED=$((PASSED+1))
    else
        echo "FAIL"
        FAILED=$((FAILED+1))
    fi
}

test_policy() {
    echo -n "Testing Policy module... "
    if [ -f "$POC_ROOT/policy/policy_node.py" ]; then
        echo "PASS"
        PASSED=$((PASSED+1))
    else
        echo "FAIL"
        FAILED=$((FAILED+1))
    fi
}

# Run tests
test_python
test_ros2
test_hal
test_policy

echo ""
echo "=========================================="
echo "Results: $PASSED passed, $FAILED failed"
echo "=========================================="

if [ $FAILED -gt 0 ]; then
    exit 1
fi