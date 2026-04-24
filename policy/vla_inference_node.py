#!/usr/bin/env python3
"""
VLA Inference Node - Embodied AI Brain
Integrates Hugging Face Qwen2.5-VL / UnifoLM-VLA for real End-to-End inference.
Falls back to Mock mode if dependencies are missing.
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Int32, Float32MultiArray
from sensor_msgs.msg import Image
import numpy as np
import cv2
import time
import re

# Try importing AI libraries
try:
    import torch
    from PIL import Image as PILImage
    from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
    from qwen_vl_utils import process_vision_info
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

class VlaInferenceNode(Node):
    def __init__(self):
        super().__init__("vla_inference_node")
        
        # Params
        self.declare_parameter("model_path", "/home/nvidia/poc/models/unifolm-vla")
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
            self.get_logger().info(f"🧠 INITIALIZING REAL VLA MODEL from {self.model_path}...")
            self.init_ai_model()
            self.get_logger().info("✅ VLA Model Loaded on GPU!")
        else:
            self.get_logger().warn("⚠️ AI libraries not found or disabled. Running in MOCK Mode.")
        self.get_logger().info("==========================================")

    def init_ai_model(self):
        try:
            # Load Model in bfloat16 to fit in Orin RAM
            self.model = Qwen2VLForConditionalGeneration.from_pretrained(
                self.model_path, 
                torch_dtype=torch.bfloat16, 
                device_map="auto"
            )
            self.processor = AutoProcessor.from_pretrained(self.model_path)
        except Exception as e:
            self.get_logger().error(f"Failed to load VLA model: {e}")
            self.use_real_ai = False

    def img_callback(self, msg):
        self.latest_image = msg

    def cmd_callback(self, msg):
        if self.is_processing:
            self.get_logger().warn("VLA is busy generating action chunks.")
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
        self.get_logger().info(f"🧠 [Real VLA] Processing Task: {command}")
        
        # 1. Decode ROS Image to PIL
        data = np.frombuffer(self.latest_image.data, dtype=np.uint8)
        try:
            bytes_per_pixel = self.latest_image.step // self.latest_image.width
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

        # 2. Construct Multimodal Prompt
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": pil_image},
                    {"type": "text", "text": f"Task: {command}. Predict the next motor actions."}
                ]
            }
        ]
        
        # 3. Inference
        try:
            text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            image_inputs, video_inputs = process_vision_info(messages)
            
            inputs = self.processor(
                text=[text], 
                images=image_inputs, 
                videos=video_inputs, 
                padding=True, 
                return_tensors="pt"
            ).to("cuda")
            
            # Publish step 0: Generating
            step_msg = Int32(); step_msg.data = 0; self.step_pub.publish(step_msg)
            
            with torch.no_grad():
                generated_ids = self.model.generate(**inputs, max_new_tokens=128)
            
            generated_ids_trimmed = [
                out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]
            output_text = self.processor.batch_decode(
                generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
            )[0]
            
            self.get_logger().info(f"[VLA Output]: {output_text}")
            
            # 4. Parse Action Chunk (assuming output like: [15.2, 3.4, 0.0, 1.0])
            actions = self.extract_actions(output_text)
            if actions:
                step_msg = Int32(); step_msg.data = 5; self.step_pub.publish(step_msg)
                chunk = Float32MultiArray()
                chunk.data = actions
                self.action_pub.publish(chunk)
                
            step_msg = Int32(); step_msg.data = 10; self.step_pub.publish(step_msg)
            
        except Exception as e:
            self.get_logger().error(f"VLA Inference Failed: {e}")
            
        self.is_processing = False

    def extract_actions(self, text):
        # Extract comma separated floats from brackets
        match = re.search(r"\[([\d.,\-\s]+)\]", text)
        if match:
            try:
                return [float(x.strip()) for x in match.group(1).split(",")]
            except ValueError:
                pass
        return [0.0, 0.0, 0.0, 0.0]

    def run_mock_vla(self, command):
        self.get_logger().info(f"🤖 [Mock VLA] Processing Task: {command}")
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
