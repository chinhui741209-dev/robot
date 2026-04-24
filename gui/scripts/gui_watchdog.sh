#!/bin/bash
# Watchdog script to keep GUI running and auto-restart it

echo "GUI Watchdog started..."

while true; do
    echo "Starting GUI process..."
    
    # Load ROS 2 environment
    source /opt/ros/humble/setup.bash
    export ROS_DOMAIN_ID=42
    export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
    export PYTHONPATH=$PYTHONPATH:/home/nvidia/poc/poc-orin
    
    /usr/bin/python3 /home/nvidia/poc/poc-orin/gui/scripts/demo_gui_tk.py
    
    echo "GUI process exited or was killed."
    echo "Restarting in 3 seconds..."
    sleep 3
done