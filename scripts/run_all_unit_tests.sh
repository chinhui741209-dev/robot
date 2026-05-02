#!/bin/bash
# run_all_unit_tests.sh
# 目的：一鍵執行全系統模組單元測試

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_ROOT/logs/test_results/full_suite_report.txt"

mkdir -p "$PROJECT_ROOT/logs/test_results"

echo "=== [Full System Unit Test Suite] ===" | tee "$LOG_FILE"
echo "Date: $(date)" | tee -a "$LOG_FILE"
echo "------------------------------------" | tee -a "$LOG_FILE"

# 1. 執行 C++ RT 核心單元測試
echo "[Layer 1] Testing C++ RT Core (SHM & Watchdog)..." | tee -a "$LOG_FILE"
if [ -f "$PROJECT_ROOT/rt_cpp/build/test_shm_logic" ]; then
    "$PROJECT_ROOT/rt_cpp/build/test_shm_logic" | tee -a "$LOG_FILE"
else
    echo "  >> SKIP: C++ test binary not found. Build it first." | tee -a "$LOG_FILE"
fi

# 2. 執行 Python Orchestration 測試
echo -e "\n[Layer 2] Testing Python Orchestration (Pytest)..." | tee -a "$LOG_FILE"
pytest "$PROJECT_ROOT/tests/test_orchestration.py" -v | tee -a "$LOG_FILE"

# 3. 執行 Python Inference 測試
echo -e "\n[Layer 3] Testing Inference & Perception (Pytest)..." | tee -a "$LOG_FILE"
pytest "$PROJECT_ROOT/tests/test_inference.py" -v | tee -a "$LOG_FILE"

echo -e "\n------------------------------------" | tee -a "$LOG_FILE"
echo "Test Suite Completed. Report saved to: $LOG_FILE"
