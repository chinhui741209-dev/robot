#!/usr/bin/env python3
"""
Demo GUI - Tech-style interface for VLA POC Demo
 Uses tkinter (available) with custom styling for tech look
"""

import os
# Force set DISPLAY for systemd/background services
if "DISPLAY" not in os.environ:
    os.environ["DISPLAY"] = ":0"

import tkinter as tk
from tkinter import ttk
import cv2
import numpy as np
from PIL import Image as PILImage, ImageTk
import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Int32, Float32MultiArray
from sensor_msgs.msg import Image
import threading


class DemoGUI:
    def __init__(self):
        self.root = tk.Tk()
        version = "Unknown"
        version_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "VERSION.txt")
        try:
            with open(version_path, "r") as f:
                version = f.read().strip()
        except Exception:
            pass
        self.root.title(f"VLA POC Demo - [{version}]")
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
        self.current_command = "Waiting..."
        self.current_step_display = "Waiting..."
        self.motor_display = {m: "0.0" for m in self.motors}

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
        self._photo_ref = None  # prevent GC

        # Command display
        inner_cmd = tk.Frame(self.command_frame, bg=self.colors["panel"])
        inner_cmd.pack(fill=tk.BOTH, expand=True)

        self.command_entry = tk.Entry(
            inner_cmd,
            bg=self.colors["bg"],
            fg=self.colors["text"],
            insertbackground=self.colors["accent"],
            font=("JetBrains Mono", 12),
            relief=tk.FLAT,
        )
        self.command_entry.pack(fill=tk.X, padx=5, pady=5)
        self.command_entry.bind("<Return>", self.send_command)

        tk.Button(
            inner_cmd,
            text="EXECUTE",
            command=self.send_command,
            bg=self.colors["accent"],
            fg=self.colors["bg"],
            font=("JetBrains Mono", 10, "bold"),
            relief=tk.FLAT,
        ).pack(fill=tk.X, padx=5, pady=5)

        self.command_label = tk.Label(
            inner_cmd,
            text="Waiting...",
            fg=self.colors["muted"],
            font=("JetBrains Mono", 12),
            bg=self.colors["panel"],
        )
        self.command_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Task steps display
        self.step_label = tk.Label(
            self.step_frame,
            text="Waiting...",
            fg=self.colors["muted"],
            font=("JetBrains Mono", 10),
            bg=self.colors["panel"],
        )
        self.step_label.pack(fill=tk.BOTH, expand=True)

        # Motor status display
        self.motor_canvas = tk.Canvas(
            self.motor_frame,
            bg=self.colors["panel"],
            highlightthickness=0,
        )
        self.motor_canvas.pack(fill=tk.BOTH, expand=True)
        self.motor_labels = {}
        for i, m in enumerate(self.motors):
            label = tk.Label(
                self.motor_canvas,
                text=f"{m}: 0.0",
                fg=self.colors["text"],
                font=("JetBrains Mono", 10),
                bg=self.colors["panel"],
            )
            label.pack(anchor="w", pady=2)
            self.motor_labels[m] = label

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
        self.node = Node("demo_gui")

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
        self.motor_sub = self.node.create_subscription(
            Float32MultiArray, "/joint_states", self.motor_callback, 10
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
            data = np.frombuffer(msg.data, dtype=np.uint8)
            expected_size = msg.height * msg.width * 3
            
            if len(data) == expected_size:
                frame = data.reshape(msg.height, msg.width, 3)
                if msg.encoding in ["bgr8", "bgr"]:
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                else:
                    rgb = frame
            else:
                print(f"[GUI] Image size mismatch! Expected {expected_size}, got {len(data)}. Encoding: {msg.encoding}, Step: {msg.step}")
                bytes_per_pixel = msg.step // msg.width if msg.width > 0 else 3
                if len(data) == msg.height * msg.step:
                    frame = data.reshape(msg.height, msg.width, bytes_per_pixel)
                    if bytes_per_pixel == 1:
                        rgb = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
                    elif bytes_per_pixel == 3:
                        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    elif bytes_per_pixel == 4:
                        rgb = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)
                    else:
                        rgb = np.zeros((msg.height, msg.width, 3), dtype=np.uint8)
                else:
                    return

            h, w = rgb.shape[:2]
            max_w, max_h = 480, 270
            scale = min(max_w / w, max_h / h)
            new_w, new_h = int(w * scale), int(h * scale)
            rgb = cv2.resize(rgb, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

            photo = ImageTk.PhotoImage(PILImage.fromarray(rgb))

            def _update(p=photo):
                self._photo_ref = p
                self.camera_label.configure(image=p, text="")

            self.root.after(0, _update)
        except Exception as e:
            print(f"[GUI] image_callback error: {e}")

    def parsed_callback(self, msg):
        def _update():
            self.current_command = msg.data
            self.command_label.configure(text=msg.data, fg=self.colors["text"])

        self.root.after(0, _update)

    def step_callback(self, msg):
        step_idx = msg.data
        if 0 <= step_idx < len(self.task_steps):
            step_name = self.task_steps[step_idx]
        else:
            step_name = "Unknown"

        def _update():
            self.current_step_display = step_name
            self.step_label.configure(text=step_name, fg=self.colors["active"])

        self.root.after(0, _update)

    def motor_callback(self, msg):
        try:
            data = list(msg.data)
            if len(data) >= 4:
                for i, m in enumerate(self.motors):
                    self.motor_values[m] = data[i]
        except Exception as e:
            print(f"[GUI] motor_callback error: {e}")

        def _update():
            for m, label in self.motor_labels.items():
                label.configure(text=f"{m}: {self.motor_values[m]:.2f}")

        self.root.after(0, _update)

    def send_command(self, event=None):
        cmd = self.command_entry.get().strip()
        if not cmd:
            return
        
        self.command_entry.delete(0, tk.END)
        self.command_label.configure(text=f"Sent: {cmd}")
        
        if hasattr(self, "command_pub") and self.command_pub:
            msg = String()
            msg.data = cmd
            self.command_pub.publish(msg)

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
