#!/usr/bin/env python3
"""
VLA Inference Node - Embodied AI Brain Replacement
Represents a UnifoLM-VLA (Qwen2.5-VL-7B) model that directly takes Text + Image -> Actions
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Int32, Float32MultiArray
from sensor_msgs.msg import Image
import time

class VlaInferenceNode(Node):
    def __init__(self):
        super().__init__("vla_inference_node")
        
        # VLA Inputs: Language & Vision
        self.cmd_sub = self.create_subscription(String, "/ui/user_command", self.cmd_callback, 10)
        self.img_sub = self.create_subscription(Image, "/camera/image_raw", self.img_callback, 10)
        
        # VLA Outputs: Action Chunks & GUI Status
        self.action_pub = self.create_publisher(Float32MultiArray, "/policy/action_chunk", 10)
        self.step_pub = self.create_publisher(Int32, "/planner/current_step", 10)
        
        self.latest_image = None
        self.is_processing = False
        
        self.get_logger().info("==========================================")
        self.get_logger().info("🚀 UnifoLM-VLA Node Initialized!")
        self.get_logger().info("Awaiting Multimodal Inputs (Camera + Text)...")
        self.get_logger().info("==========================================")

    def img_callback(self, msg):
        self.latest_image = msg

    def cmd_callback(self, msg):
        if self.is_processing:
            self.get_logger().warn("VLA is currently busy executing an action sequence.")
            return
            
        command = msg.data
        self.get_logger().info(f"[VLA Inference] Received Instruction: '{command}'")
        
        if self.latest_image is None:
            self.get_logger().warn("[VLA Inference] No camera feed! Vision-Language model requires image.")
            return
            
        self.is_processing = True
        self.run_vla_inference(command)

    def run_vla_inference(self, command):
        self.get_logger().info("[VLA Inference] Passing Text + Image through Qwen2.5-VL-7B Backbone...")
        
        # Mock VLA processing steps
        vla_states = [
            (0, "Vision Encoding (ViT)"),
            (2, "Cross-Attention / Instruction Grounding"),
            (5, "Action Chunk Prediction (MLP Head)"),
            (8, "Executing Spatial Trajectory"),
            (10, "Task Complete")
        ]
        
        for step_val, state_desc in vla_states:
            self.get_logger().info(f"[VLA Inference] State: {state_desc}")
            
            # Publish step index for GUI compatibility
            step_msg = Int32()
            step_msg.data = step_val
            self.step_pub.publish(step_msg)
            
            # Publish Action Chunk
            chunk = Float32MultiArray()
            chunk.data = [
                float(step_val * 5),  # Shoulder
                float(step_val * 2),  # Elbow
                0.0,                  # Wrist
                1.0 if step_val > 5 else 0.0  # Gripper
            ]
            self.action_pub.publish(chunk)
            
            # Simulate inference latency (Autoregressive generation)
            time.sleep(1.5)
            
        self.get_logger().info("[VLA Inference] Action chunk execution finished.")
        self.is_processing = False

def main(args=None):
    rclpy.init(args=args)
    node = VlaInferenceNode()
    try:
        rclpy.spin(node)
    except Exception as e:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()
