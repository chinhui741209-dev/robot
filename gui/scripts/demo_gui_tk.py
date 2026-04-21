#!/usr/bin/env python3
"""
Demo GUI - Tech-style interface for VLA POC Demo
 Uses tkinter (available) with custom styling for tech look
"""

import tkinter as tk
from tkinter import ttk
import cv2
import numpy as np
from PIL import Image as PILImage, ImageTk
import rclpy
from std_msgs.msg import String, Int32, Float32MultiArray
from sensor_msgs.msg import Image
import threading


class DemoGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("VLA POC Demo - Tech Interface")
        self.root.geometry("1280x720")
        self.root.configure(bg="#0a0a14")

        self.running = True
        self.current_step = -1
        self.task_steps = [
            "Locate source",
            "Locate target",
            "Move to pre-grasp",
            "Move to grasp",
            "Close gripper",
            "Lift object",
            "Move to target",
            "Position over target",
            "Open gripper",
            "Retreat",
            "Complete",
        ]
        self.motors = ["shoulder", "elbow", "wrist", "gripper"]
        self.motor_values = {m: 0.0 for m in self.motors}

        self.setup_styles()
        self.create_layout()
        self.init_ros()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_styles(self):
        self.colors = {
            "bg": "#0a0a14",
            "panel": "#12121f",
            "accent": "#00f0ff",
            "active": "#00ff88",
            "text": "#ffffff",
            "muted": "#666688",
            "error": "#ff3366",
        }

        style = ttk.Style()
        style.theme_use("default")

        style.configure("Panel.TFrame", background=self.colors["panel"])
        style.configure(
            "Title.TLabel",
            background=self.colors["panel"],
            foreground=self.colors["accent"],
            font=("JetBrains Mono", 14, "bold"),
        )
        style.configure(
            "Tech.TLabel",
            background=self.colors["panel"],
            foreground=self.colors["text"],
            font=("JetBrains Mono", 10),
        )
        style.configure(
            "Step.TLabel",
            background=self.colors["panel"],
            foreground=self.colors["muted"],
            font=("JetBrains Mono", 9),
        )
        style.configure(
            "Active.TLabel",
            background=self.colors["panel"],
            foreground=self.colors["active"],
            font=("JetBrains Mono", 9, "bold"),
        )

    def create_layout(self):
        main = tk.Frame(self.root, bg=self.colors["bg"])
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        title = tk.Label(
            main,
            text="// VLA POC DEMO SYSTEM",
            font=("JetBrains Mono", 18, "bold"),
            fg=self.colors["accent"],
            bg=self.colors["bg"],
        )
        title.pack(pady=(0, 10))

        grid = tk.Frame(main, bg=self.colors["bg"])
        grid.pack(fill=tk.BOTH, expand=True)

        grid.rowconfigure(0, weight=1)
        grid.rowconfigure(1, weight=1)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        self.camera_frame = self.create_panel(grid, 0, 0, "CAMERA FEED")
        self.command_frame = self.create_panel(grid, 0, 1, "COMMAND")
        self.step_frame = self.create_panel(grid, 1, 0, "TASK STEPS")
        self.motor_frame = self.create_panel(grid, 1, 1, "MOTOR STATUS")

        # Camera display label inside the camera panel
        self.camera_label = tk.Label(
            self.camera_frame,
            bg=self.colors["panel"],
            text="Waiting for camera...",
            fg=self.colors["muted"],
            font=("JetBrains Mono", 10),
        )
        self.camera_label.pack(fill=tk.BOTH, expand=True)
        self._photo_ref = None   # prevent GC

    def create_panel(self, parent, row, col, title):
        frame = tk.LabelFrame(
            parent,
            text=title,
            font=("JetBrains Mono", 11, "bold"),
            fg=self.colors["accent"],
            bg=self.colors["panel"],
            padx=10,
            pady=10,
        )
        frame.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
        frame.configure(bg=self.colors["panel"])
        return frame

    def init_ros(self):
        threading.Thread(target=self.ros_spinner, daemon=True).start()

    def ros_spinner(self):
        rclpy.init()
        self.node = rclpy.node.Node("demo_gui")

        self.image_sub = self.node.create_subscription(
            Image, "/camera/image_raw", self.image_callback, 10
        )
        self.command_pub = self.node.create_publisher(String, "/ui/user_command", 10)

        self.parsed_sub = self.node.create_subscription(
            String, "/task/parsed_command", self.parsed_callback, 10
        )
        self.step_sub = self.node.create_subscription(
            Int32, "/planner/current_step", self.step_callback, 10
        )
        self.motor_sub = self.node.create_publisher(
            Float32MultiArray, "/robot/motor_status", 10
        )

        while self.running and rclpy.ok():
            rclpy.spin_once(self.node, timeout_sec=0.1)

        try:
            self.node.destroy_node()
        except:
            pass
        try:
            rclpy.shutdown()
        except:
            pass

    def image_callback(self, msg):
        try:
            frame = np.frombuffer(msg.data, dtype=np.uint8).reshape(
                msg.height, msg.width, 3
            )
            # camera publishes bgr8 → convert to RGB for PIL
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # resize to fit panel (~480×270 keeps aspect ratio)
            h, w = rgb.shape[:2]
            max_w, max_h = 480, 270
            scale = min(max_w / w, max_h / h)
            new_w, new_h = int(w * scale), int(h * scale)
            rgb = cv2.resize(rgb, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

            photo = ImageTk.PhotoImage(PILImage.fromarray(rgb))

            # update must happen on the main Tkinter thread
            def _update(p=photo):
                self._photo_ref = p
                self.camera_label.configure(image=p, text="")

            self.root.after(0, _update)
        except Exception as e:
            pass

    def parsed_callback(self, msg):
        pass

    def step_callback(self, msg):
        pass

    def run(self):
        self.root.mainloop()

    def on_close(self):
        self.running = False
        self.root.destroy()


def main():
    gui = DemoGUI()
    gui.run()


if __name__ == "__main__":
    main()
