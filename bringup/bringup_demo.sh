#!/bin/bash
# bringup_demo.sh - Demo bring-up for VLA POC
# Starts: camera, perception, task_parser, planner, robot_bridge, gui

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POC_ROOT="$(dirname "$SCRIPT_DIR")"

source /opt/ros/humble/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS2Daemon=False
export ROS_DOMAIN_ID=42
export POC_ROOT="$POC_ROOT"
export PYTHONPATH="$PYTHONPATH:$POC_ROOT"

echo "=========================================="
echo "Bring-up: VLA POC Demo"
echo "=========================================="

echo "[1/6] Starting Camera Node..."
if [ -f "$POC_ROOT/perception/scripts/camera_node.py" ]; then
    nohup python3 "$POC_ROOT/perception/scripts/camera_node.py" > "$POC_ROOT/logs/camera.log" 2>&1 &
    CAMERA_PID=$!
    echo "  Camera PID: $CAMERA_PID"
    sleep 1
else
    echo "  Camera: Not found"
fi

echo "[2/6] Starting Perception Node..."
if [ -f "$POC_ROOT/perception/scripts/perception_node.py" ]; then
    nohup python3 "$POC_ROOT/perception/scripts/perception_node.py" > "$POC_ROOT/logs/perception.log" 2>&1 &
    PERCEPTION_PID=$!
    echo "  Perception PID: $PERCEPTION_PID"
    sleep 1
else
    echo "  Perception: Not found"
fi

echo "[2.5/6] Starting Visualization Node..."
if [ -f "$POC_ROOT/perception/scripts/visualization_node.py" ]; then
    nohup python3 "$POC_ROOT/perception/scripts/visualization_node.py" > "$POC_ROOT/logs/visualization.log" 2>&1 &
    VIS_PID=$!
    echo "  Visualization PID: $VIS_PID"
    sleep 1
else
    echo "  Visualization: Not found (skipping)"
fi

echo "[4/6] Starting Task Parser..."
if [ -f "$POC_ROOT/task_parser/scripts/task_parser_node.py" ]; then
    nohup python3 "$POC_ROOT/task_parser/scripts/task_parser_node.py" > "$POC_ROOT/logs/task_parser.log" 2>&1 &
    PARSER_PID=$!
    echo "  Parser PID: $PARSER_PID"
    sleep 1
else
    echo "  Task Parser: Not found"
fi

echo "[5/6] Starting Planner..."
if [ -f "$POC_ROOT/planner/scripts/planner_node.py" ]; then
    nohup python3 "$POC_ROOT/planner/scripts/planner_node.py" > "$POC_ROOT/logs/planner.log" 2>&1 &
    PLANNER_PID=$!
    echo "  Planner PID: $PLANNER_PID"
    sleep 1
else
    echo "  Planner: Not found"
fi

echo "[6/6] Starting Robot Bridge..."
if [ -f "$POC_ROOT/robot_bridge/scripts/robot_bridge_node.py" ]; then
    nohup python3 "$POC_ROOT/robot_bridge/scripts/robot_bridge_node.py" > "$POC_ROOT/logs/robot_bridge.log" 2>&1 &
    BRIDGE_PID=$!
    echo "  Bridge PID: $BRIDGE_PID"
    sleep 1
else
    echo "  Robot Bridge: Not found"
fi

echo "[7/8] Starting Policy Node (Brain)..."
if [ -f "$POC_ROOT/policy/policy_node.py" ]; then
    nohup python3 "$POC_ROOT/policy/policy_node.py" --ros-args -p sim:=True > "$POC_ROOT/logs/policy.log" 2>&1 &
    POLICY_PID=$!
    echo "  Policy PID: $POLICY_PID"
    sleep 1
else
    echo "  Policy: Not found"
fi

echo "[8/8] Starting GUI (Digital Twin)..."
if [ -f "$POC_ROOT/gui/scripts/demo_gui_tk.py" ]; then
    # Note: GUI requires X server / DISPLAY
    python3 "$POC_ROOT/gui/scripts/demo_gui_tk.py"
else
    echo "  GUI: demo_gui_tk.py not found"
fi

echo ""
echo "=========================================="
echo "Demo bring-up complete!"
echo "=========================================="
echo ""
echo "Running processes:"
ps aux | grep -E "camera_node|perception_node|task_parser|planner|robot_bridge|demo_gui" | grep python | grep -v grep | awk '{print "  "$11" PID:"$2}'
echo ""
echo "GUI should be visible on screen"
echo "To stop: pkill -f demo_gui; pkill -f camera_node; pkill -f perception_node; pkill -f task_parser; pkill -f planner; pkill -f robot_bridge"
