#!/bin/bash
# HAL Buddy launcher script
source /opt/ros/humble/setup.bash
cd /home/nvidia/poc/poc-orin/hal/scripts
exec python3 hal_buddy_node.py "$@"