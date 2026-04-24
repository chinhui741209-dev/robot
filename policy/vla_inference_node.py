#!/usr/bin/env python3
"""
VLA Inference Node - Embodied AI Brain
Integrates Hugging Face OpenVLA-7B for real End-to-End inference.
Falls back to Mock mode if dependencies are missing.
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Int32, Float32MultiArray
from sensor_msgs.msg import Image
import numpy as np
import cv2
import time

# Try importing AI libraries
try:
    import torch
    from PIL import Image as PILImage
    from transformers import AutoModelForVision2Seq, AutoProcessor
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

class VlaInferenceNode(Node):
    def __init__(self):
        super().__init__("vla_inference_node")
        
        # Params (Updated for OpenVLA)
        self.declare_parameter("model_path", "/home/nvidia/poc/models/openvla-7b")
        self.declare_parameter("use_real_ai", True)
        
        self.model_path = self.get_parameter("model_path").value
        self.use_real_ai = self.get_parameter("use_real_ai").value and AI_AVAILABLE
        
        # VLA Inputs
        self.cmd_sub = self.create_subscription(String, "/ui/user_command", self.cmd_callback, 10)
        self.img_sub = self.create_subscription(Image, "/camera/image_raw", self.img_callback, 10)
        
        # VLA Outputs
        self.action_pub = self.create_publisher(Float32MultiArray, "/skill/command", 10)
        self.step_pub = self.create_publisher(Int32, "/planner/current_step", 10)
        
        self.latest_image = None
        self.is_processing = False
        
        self.get_logger().info("==========================================")
        if self.use_real_ai:
            self.get_logger().info(f"🧠 INITIALIZING OpenVLA-7B MODEL from {self.model_path}...")
            self.init_ai_model()
            self.get_logger().info("✅ OpenVLA Model Loaded on GPU!")
        else:
            self.get_logger().warn("⚠️ AI libraries not found or disabled. Running in MOCK Mode.")
        self.get_logger().info("==========================================")

    def init_ai_model(self):
        try:
            # OpenVLA is massive, load in bfloat16
            self.processor = AutoProcessor.from_pretrained(self.model_path, trust_remote_code=True)
            self.model = AutoModelForVision2Seq.from_pretrained(
                self.model_path, 
                attn_implementation="flash_attention_2",  # Optimal for Orin
                torch_dtype=torch.bfloat16, 
                low_cpu_mem_usage=True, 
                trust_remote_code=True
            ).to("cuda:0")
        except Exception as e:
            self.get_logger().error(f"Failed to load OpenVLA model: {e}")
            self.use_real_ai = False

    def img_callback(self, msg):
        self.latest_image = msg

    def cmd_callback(self, msg):
        if self.is_processing:
            self.get_logger().warn("VLA is busy generating skill commands.")
            return
            
        command = msg.data
        if self.latest_image is None:
            self.get_logger().warn("No camera feed received yet.")
            return
            
        self.is_processing = True
        
        if self.use_real_ai:
            self.run_real_vla(command)
        else:
            self.run_mock_vla(command)

    def run_real_vla(self, command):
        self.get_logger().info(f"🧠 [OpenVLA] Processing Task: {command}")
        
        # 1. Decode ROS Image to PIL
        data = np.frombuffer(self.latest_image.data, dtype=np.uint8)
        try:
            bytes_per_pixel = self.latest_image.step // self.latest_image.width if self.latest_image.width > 0 else 3
            frame = data.reshape(self.latest_image.height, self.latest_image.width, bytes_per_pixel)
            if bytes_per_pixel == 3:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            else:
                rgb = frame
            pil_image = PILImage.fromarray(rgb)
        except Exception as e:
            self.get_logger().error(f"Image decode error: {e}")
            self.is_processing = False
            return

        # 2. OpenVLA Prompt Engineering
        # OpenVLA expects: "In: What action should the robot take to [instruction]?
Out:"
        prompt = f"In: What action should the robot take to {command}?\nOut:"
        
        # 3. Inference
        try:
            inputs = self.processor(prompt, pil_image).to("cuda:0", dtype=torch.bfloat16)
            
            step_msg = Int32(); step_msg.data = 0; self.step_pub.publish(step_msg)
            
            with torch.no_grad():
                # OpenVLA generates action tokens directly
                action = self.model.predict_action(**inputs, unnorm_key="bridge_orig")
            
            # Publish step indicating generation is done
            step_msg = Int32(); step_msg.data = 5; self.step_pub.publish(step_msg)
            
            # 4. Map OpenVLA action (e.g. 7-DoF) to our 4-DoF system
            # Extract relevant dimensions (x, y, z, gripper) depending on what OpenVLA predicted
            # Assuming standard OpenVLA output: [x, y, z, roll, pitch, yaw, gripper]
            actions = list(action)
            if len(actions) >= 7:
                # Mock mapping to [shoulder, elbow, wrist, gripper]
                mapped_action = [
                    float(actions[0] * 100), # Map X to Shoulder
                    float(actions[1] * 100), # Map Y to Elbow
                    float(actions[2] * 100), # Map Z to Wrist
                    float(actions[6])        # Gripper state
                ]
                
                chunk = Float32MultiArray()
                chunk.data = mapped_action
                self.action_pub.publish(chunk)
                self.get_logger().info(f"[OpenVLA Output]: {mapped_action}")
                
            step_msg = Int32(); step_msg.data = 10; self.step_pub.publish(step_msg)
            
        except Exception as e:
            self.get_logger().error(f"OpenVLA Inference Failed: {e}")
            
        self.is_processing = False

    def run_mock_vla(self, command):
        self.get_logger().info(f"🤖 [Mock OpenVLA] Processing Task: {command}")
        for step_val in [0, 2, 5, 8, 10]:
            step_msg = Int32()
            step_msg.data = step_val
            self.step_pub.publish(step_msg)
            
            chunk = Float32MultiArray()
            chunk.data = [float(step_val * 5), float(step_val * 2), 0.0, 1.0 if step_val > 5 else 0.0]
            self.action_pub.publish(chunk)
            time.sleep(1.0)
            
        self.get_logger().info("Mock execution finished.")
        self.is_processing = False

def main(args=None):
    rclpy.init(args=args)
    node = VlaInferenceNode()
    try:
        rclpy.spin(node)
    except Exception:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()
