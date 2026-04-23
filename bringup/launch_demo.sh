#!/bin/bash
# launch_demo.sh - Launch demo application

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POC_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "Launch: Demo Application"
echo "=========================================="

source /opt/ros/humble/setup.bash
export POC_ROOT="$POC_ROOT"
export PYTHONPATH="$PYTHONPATH:$POC_ROOT"

# Check if W3 launch exists (E2E demo)
if [ -f "$POC_ROOT/scripts/w3_launch.py" ]; then
    if [ -f "$POC_ROOT/gui/scripts/demo_gui_tk.py" ]; then
        echo "Starting GUI..."
        # 嘗試將權限賦予目前桌面
        export DISPLAY=:0
        export XAUTHORITY=/home/nvidia/.Xauthority
        
        # 讓這條指令即便失敗也繼續執行
        /usr/bin/python3 "$POC_ROOT/gui/scripts/demo_gui_tk.py" > "$POC_ROOT/logs/gui_debug.log" 2>&1 &
        echo "GUI launch command sent. Check $POC_ROOT/logs/gui_debug.log if it fails."
    fi

    echo "Starting W3 E2E Demo..."
    echo "Press Ctrl-C to stop"
    python3 "$POC_ROOT/scripts/w3_launch.py"
else
    echo "ERROR: Demo not found"
    exit 1
fi