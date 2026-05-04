#!/bin/bash
# setup_dev.sh - Set up development environment and build workspace

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POC_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "Robot Project - Development Setup"
echo "=========================================="

# 1. Install Python dependencies
echo "[1/4] Installing Python dependencies..."
if [ -f "$POC_ROOT/requirements.txt" ]; then
    pip3 install -r "$POC_ROOT/requirements.txt"
else
    echo "Warning: requirements.txt not found"
fi

# 2. Initialize and update rosdep
echo "[2/4] Updating rosdep..."
if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
    sudo rosdep init || true
fi
rosdep update

# 3. Install ROS 2 dependencies
echo "[3/4] Installing ROS 2 dependencies..."
cd "$POC_ROOT"
rosdep install --from-paths . --ignore-src -r -y --rosdistro humble

# 4. Build workspace
echo "[4/4] Building workspace with colcon..."
colcon build --symlink-install

echo ""
echo "=========================================="
echo "Setup complete! Please source the workspace:"
echo "source install/setup.bash"
echo "=========================================="
