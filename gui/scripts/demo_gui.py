#!/usr/bin/env python3
"""
Demo GUI - Tech-style interface for VLA POC Demo
 Tkinter version with ROS image subscription
"""

import tkinter as tk
from tkinter import ttk
import threading
import json
import time
import numpy as np
import cv2
import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Int32
from sensor_msgs.msg import Image

try:
    from cv_bridge import CvBridge
except ImportError:
    CvBridge = None

try:
    from PIL import Image as PILImage, ImageTk
    from PIL import Image as PILImageModule
except ImportError as e:
    print(f"PIL import error: {e}")
    PILImage = None
    ImageTk = None


class DemoGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("VLA POC Demo - Tech Interface")
        self.root.geometry("1200x700")
        self.root.configure(bg="#0a0a14")

        self.current_step = -1
        self.latest_image = None
        self.bridge = CvBridge() if CvBridge else None

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
        self.last_command = ""
        self.last_parsed = ""

        self.setup_styles()
        self.create_layout()
        self.init_ros()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.update_camera_loop()

    def setup_styles(self):
        self.colors = {
            "bg": "#0a0a14",
            "panel": "#12121f",
            "accent": "#00f0ff",
            "active": "#00ff88",
            "text": "#ffffff",
            "muted": "#666688",
            "error": "#ff3366",
            "warning": "#ffaa00",
        }

        self.ros_running = False

        style = ttk.Style()
        style.theme_use("default")

        for widget in ["TFrame", "TLabelframe"]:
            style.configure(widget, background=self.colors["panel"])

        for widget in ["TLabel"]:
            style.configure(
                widget,
                background=self.colors["panel"],
                foreground=self.colors["text"],
                font=("Consolas", 10),
            )

    def create_layout(self):
        main = tk.Frame(self.root, bg=self.colors["bg"])
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        title = tk.Label(
            main,
            text="// VLA POC DEMO SYSTEM //",
            font=("Consolas", 20, "bold"),
            fg=self.colors["accent"],
            bg=self.colors["bg"],
        )
        title.pack(pady=(0, 15))

        grid = tk.Frame(main, bg=self.colors["bg"])
        grid.pack(fill=tk.BOTH, expand=True)

        grid.rowconfigure(0, weight=2)
        grid.rowconfigure(1, weight=1)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        self.camera_frame = self.create_panel(grid, 0, 0, "CAMERA FEED")
        self.command_frame = self.create_panel(grid, 0, 1, "COMMAND INPUT")
        self.step_frame = self.create_panel(grid, 1, 0, "TASK STEPS")
        self.motor_frame = self.create_panel(grid, 1, 1, "MOTOR STATUS")

        self.setup_camera_view()
        self.setup_command_view()
        self.setup_step_view()
        self.setup_motor_view()

    def create_panel(self, parent, row, col, title):
        frame = tk.LabelFrame(
            parent,
            text=f" {title} ",
            font=("Consolas", 12, "bold"),
            fg=self.colors["accent"],
            bg=self.colors["panel"],
            bd=1,
            relief=tk.SOLID,
        )
        frame.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
        return frame

    def setup_camera_view(self):
        inner = tk.Frame(self.camera_frame, bg=self.colors["panel"])
        inner.pack(fill=tk.BOTH, expand=True)

        self.camera_label = tk.Label(
            inner,
            text="NO IMAGE",
            fg=self.colors["muted"],
            bg=self.colors["panel"],
            font=("Consolas", 14),
        )
        self.camera_label.pack(fill=tk.BOTH, expand=True)

    def setup_command_view(self):
        inner = tk.Frame(self.command_frame, bg=self.colors["panel"])
        inner.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        tk.Label(
            inner,
            text="Enter command:",
            fg=self.colors["text"],
            bg=self.colors["panel"],
            font=("Consolas", 10),
        ).pack(anchor="w")

        self.command_entry = tk.Entry(
            inner,
            bg=self.colors["bg"],
            fg=self.colors["text"],
            insertbackground=self.colors["accent"],
            font=("Consolas", 14),
            relief=tk.FLAT,
        )
        self.command_entry.pack(fill=tk.X, pady=(5, 10))
        self.command_entry.bind("<Return>", self.send_command)

        tk.Button(
            inner,
            text="EXECUTE",
            command=self.send_command,
            bg=self.colors["accent"],
            fg=self.colors["bg"],
            font=("Consolas", 11, "bold"),
            relief=tk.FLAT,
        ).pack(fill=tk.X)

        tk.Label(
            inner,
            text="Parsed Result:",
            fg=self.colors["text"],
            bg=self.colors["panel"],
            font=("Consolas", 10),
        ).pack(anchor="w", pady=(15, 0))

        self.parsed_label = tk.Label(
            inner,
            text="--",
            fg=self.colors["muted"],
            bg=self.colors["panel"],
            font=("Consolas", 10),
        )
        self.parsed_label.pack(anchor="w")

    def setup_step_view(self):
        inner = tk.Frame(self.step_frame, bg=self.colors["panel"])
        inner.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scroll = tk.Scrollbar(inner)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.step_list = tk.Listbox(
            inner,
            bg=self.colors["bg"],
            fg=self.colors["text"],
            font=("Consolas", 10),
            selectbackground=self.colors["accent"],
            selectforeground=self.colors["bg"],
            relief=tk.FLAT,
            yscrollcommand=scroll.set,
        )
        self.step_list.pack(fill=tk.BOTH, expand=True)
        scroll.config(command=self.step_list.yview)

        for i, step in enumerate(self.task_steps):
            self.step_list.insert(tk.END, f"{i:02d} | {step}")

    def setup_motor_view(self):
        inner = tk.Frame(self.motor_frame, bg=self.colors["panel"])
        inner.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        for i, motor in enumerate(self.motors):
            row = i // 2
            col = i % 2

            f = tk.Frame(inner, bg=self.colors["bg"], bd=1, relief=tk.SOLID)
            f.grid(row=row, column=col, sticky="nsew", padx=3, pady=3)
            inner.grid_rowconfigure(row, weight=1)
            inner.grid_columnconfigure(col, weight=1)

            tk.Label(
                f,
                text=motor.upper(),
                fg=self.colors["muted"],
                bg=self.colors["bg"],
                font=("Consolas", 8),
            ).pack(pady=(5, 0))

            val = tk.Label(
                f,
                text="0.0°",
                fg=self.colors["accent"],
                bg=self.colors["bg"],
                font=("Consolas", 14, "bold"),
            )
            val.pack(pady=5)
            setattr(self, f"motor_{motor}_val", val)

    def init_ros(self):
        def ros_thread():
            try:
                rclpy.init()
                self.ros_node = Node("demo_gui")

                self.image_sub = self.ros_node.create_subscription(
                    Image, "/camera/image_raw", self.image_callback, 10
                )
                self.command_pub = self.ros_node.create_publisher(
                    String, "/ui/user_command", 10
                )
                self.parsed_sub = self.ros_node.create_subscription(
                    String, "/task/parsed_command", self.parsed_callback, 10
                )
                self.step_sub = self.ros_node.create_subscription(
                    Int32, "/planner/current_step", self.step_callback, 10
                )

                self.ros_running = True
                while self.ros_running and rclpy.ok():
                    rclpy.spin_once(self.ros_node, timeout_sec=0.1)
            except Exception as e:
                print(f"ROS error: {e}")
            finally:
                try:
                    self.ros_node.destroy_node()
                except:
                    pass
                try:
                    rclpy.shutdown()
                except:
                    pass

        self.ros_thread = threading.Thread(target=ros_thread, daemon=True)
        self.ros_thread.start()

    def image_callback(self, msg):
        try:
            if self.bridge:
                cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
                self.latest_image = cv_image  # already BGR
            else:
                h = int(msg.height)
                w = int(msg.width)
                data = np.frombuffer(msg.data, dtype=np.uint8)
                img = data.reshape((h, w, 3))
                self.latest_image = img  # keep BGR
        except Exception as e:
            print(
                f"Image error: {e}, height={msg.height}, width={msg.width}, data_len={len(msg.data) if hasattr(msg, 'data') else 'N/A'}"
            )

    def parsed_callback(self, msg):
        self.root.after(
            0, lambda: self.parsed_label.config(text=msg.data, fg=self.colors["active"])
        )

    def step_callback(self, msg):
        self.root.after(0, self.update_step_ui, msg.data)

    def update_camera_loop(self):
        if self.latest_image is not None:
            try:
                if PILImage and ImageTk:
                    import cv2

                    img = cv2.resize(self.latest_image, (960, 720))
                    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    photo = ImageTk.PhotoImage(PILImage.fromarray(rgb))
                    self.camera_label.configure(image=photo, text="")
                    self.camera_label.image = photo
                else:
                    self.camera_label.configure(
                        text="PIL not available", fg=self.colors["error"]
                    )
            except Exception as e:
                print(f"Camera display error: {e}")

        self.root.after(20, self.update_camera_loop)

    def send_command(self, event=None):
        cmd = self.command_entry.get()
        if not cmd:
            return

        self.last_command = cmd
        self.command_entry.delete(0, tk.END)

        parsed = self.parse_command(cmd)
        self.last_parsed = parsed

        if parsed:
            self.parsed_label.config(
                text=f"Sending: {cmd}",
                fg=self.colors["muted"],
            )
            print(f"[GUI] Publishing command: {cmd}")
            if hasattr(self, "command_pub") and self.command_pub:
                msg = String()
                msg.data = cmd
                self.command_pub.publish(msg)
            else:
                print(f"[GUI] ERROR: command_pub not initialized!")
        else:
            print(f"[GUI] Unknown command: {cmd}")
            self.parsed_label.config(text=f"Unknown: {cmd}", fg=self.colors["error"])

    def parse_command(self, cmd):
        commands = {
            "把筆放到盒子中": {
                "intent": "pick_and_place",
                "source": "pen",
                "target": "box",
            },
            "把筆放到箱子中": {
                "intent": "pick_and_place",
                "source": "pen",
                "target": "box",
            },
            "把筆放到箱子": {
                "intent": "pick_and_place",
                "source": "pen",
                "target": "box",
            },
            "把筆放進箱子": {
                "intent": "pick_and_place",
                "source": "pen",
                "target": "box",
            },
            "把筆放盒子": {
                "intent": "pick_and_place",
                "source": "pen",
                "target": "box",
            },
            "pick pen to box": {
                "intent": "pick_and_place",
                "source": "pen",
                "target": "box",
            },
            "把蘋果放到盒子中": {
                "intent": "pick_and_place",
                "source": "apple",
                "target": "box",
            },
            "把橘子放到盒子中": {
                "intent": "pick_and_place",
                "source": "orange",
                "target": "box",
            },
            "pick apple to box": {
                "intent": "pick_and_place",
                "source": "apple",
                "target": "box",
            },
        }
        return commands.get(cmd)

    def simulate_execution(self):
        def run():
            for step in range(len(self.task_steps)):
                self.current_step = step
                self.root.after(0, self.update_step_ui, step)

                motors = self.get_motors_for_step(step)
                for m in self.motors:
                    val = 45.0 if m in motors else 0.0
                    self.root.after(0, self.update_motor_ui, m, val)

                import time

                time.sleep(1.0)

            self.root.after(
                0,
                lambda: self.parsed_label.config(
                    text="TASK COMPLETED ✓", fg=self.colors["active"]
                ),
            )

        threading.Thread(target=run, daemon=True).start()

    def get_motors_for_step(self, step):
        mappings = {
            0: ["shoulder"],
            1: ["elbow"],
            2: ["shoulder", "elbow"],
            3: ["shoulder", "elbow", "wrist"],
            4: ["gripper"],
            5: ["shoulder"],
            6: ["shoulder", "elbow"],
            7: ["wrist"],
            8: ["gripper"],
            9: ["shoulder", "elbow"],
            10: [],
        }
        return mappings.get(step, [])

    def update_step_ui(self, step):
        self.step_list.selection_clear(0, tk.END)
        self.step_list.selection_set(step)
        self.step_list.see(step)

        for i in range(len(self.task_steps)):
            self.step_list.itemconfig(i, fg=self.colors["muted"])
        self.step_list.itemconfig(step, fg=self.colors["active"])

    def update_motor_ui(self, motor, value):
        widget = getattr(self, f"motor_{motor}_val", None)
        if widget:
            color = self.colors["active"] if value > 0 else self.colors["muted"]
            widget.config(text=f"{value:.1f}°", fg=color)

    def on_close(self):
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    gui = DemoGUI()
    gui.run()


if __name__ == "__main__":
    main()
