#!/usr/bin/env python3
"""
W2 Components - Run multiple ROS2 processes
"""

import subprocess
import time
import sys
import os

os.chdir("/home/nvidia/poc/poc-orin/scripts")

scripts = [
    ("W2_Buddy", "w2_launch.py"),
]

for name, script in scripts:
    print(f"Starting {name}...")
    proc = subprocess.Popen(
        ["bash", "-c", f"source /opt/ros/humble/setup.bash && python3 {script}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(2)

print("All components started")
print("Check topics with: source /opt/ros/humble/setup.bash && ros2 topic list")

while True:
    time.sleep(1)
