#!/bin/bash
# Watchdog script to keep GUI running and auto-restart it

echo "GUI Watchdog started..."

while true; do
    echo "Starting GUI process..."
    /usr/bin/python3 /home/nvidia/poc/poc-orin/gui/scripts/demo_gui_tk.py
    
    echo "GUI process exited or was killed."
    echo "Restarting in 3 seconds..."
    sleep 3
done