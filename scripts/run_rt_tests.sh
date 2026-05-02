#!/bin/bash
# run_rt_integration_test.sh
# 目的：測試 C++ RT 核心的穩定性與 Watchdog 故障處理能力

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$SCRIPT_DIR/../rt_cpp/build"
LOG_DIR="$SCRIPT_DIR/../logs/test_results"
mkdir -p "$LOG_DIR"

cd "$SCRIPT_DIR/.." # Go to project root

echo "=== [RT Integration Test Start] ==="

# 1. 啟動 HAL Buddy
echo "[Step 1] Starting hal_buddy..."
"./rt_cpp/build/hal_buddy" > "./logs/test_results/hal.log" 2>&1 &
HAL_PID=$!
sleep 1

# 2. 啟動 State Estimator
echo "[Step 2] Starting state_estimator..."
"$BIN_DIR/state_estimator" > "$LOG_DIR/est.log" 2>&1 &
EST_PID=$!
sleep 3

# 3. 故障注入：強制關閉 HAL
echo "[Step 3] Fault Injection: Killing hal_buddy..."
kill -9 $HAL_PID
sleep 1

# 4. 驗證 Watchdog 觸發
echo "[Step 4] Checking Watchdog status in est.log..."
if grep -q "WATCHDOG TRIGGERED" "$LOG_DIR/est.log"; then
    echo ">> SUCCESS: Watchdog detected HAL failure."
else
    echo ">> FAILURE: Watchdog did NOT trigger!"
    exit 1
fi

# 5. 清理
kill $EST_PID 2>/dev/null || true
echo "=== [RT Integration Test Complete] ==="
