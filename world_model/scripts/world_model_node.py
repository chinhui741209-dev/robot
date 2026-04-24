#!/usr/bin/env python3
"""
World Model Node (D5 Layer) - State Fusion & Memory
Maintains a consistent snapshot of the environment and robot state.
Alinged with ICD v0.1.
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Float32MultiArray
from vision_msgs.msg import Detection2DArray
import json
import time

class WorldModelNode(Node):
    def __init__(self):
        super().__init__("world_model_node")
        
        # ICD Inputs
        self.obj_sub = self.create_subscription(
            Detection2DArray, "/perception/objects", self.object_callback, 10
        )
        self.joint_sub = self.create_subscription(
            Float32MultiArray, "/joint_states", self.joint_callback, 10
        )
        
        # ICD Outputs
        self.state_pub = self.create_publisher(String, "/world_model/state", 10)
        
        # Internal Memory
        self.scene_memory = {
            "last_update": 0.0,
            "objects": [],
            "robot_joints": [0.0, 0.0, 0.0, 0.0],
            "status": "initializing"
        }
        
        # Timer for broadcasting state (10 Hz)
        self.timer = self.create_timer(0.1, self.broadcast_state)
        
        self.get_logger().info("🌍 World Model (D5) Initialized - Maintaining Scene Graph")

    def object_callback(self, msg):
        current_objects = []
        for det in msg.detections:
            # Simplify detection for World Model memory
            obj_id = det.results[0].hypothesis.class_id
            score = det.results[0].hypothesis.score
            x = det.bbox.center.position.x
            y = det.bbox.center.position.y
            
            current_objects.append({
                "class": obj_id,
                "confidence": round(score, 2),
                "pos": {"x": round(x, 1), "y": round(y, 1)},
                "last_seen": time.time()
            })
        
        # Basic Persistence Logic: If multiple objects seen, update memory
        # In a real system, we would perform tracking/matching here
        self.scene_memory["objects"] = current_objects
        self.scene_memory["last_update"] = time.time()

    def joint_callback(self, msg):
        self.scene_memory["robot_joints"] = [round(x, 2) for x in msg.data]

    def broadcast_state(self):
        # Update overall status
        if time.time() - self.scene_memory["last_update"] > 2.0:
            self.scene_memory["status"] = "stale"
        else:
            self.scene_memory["status"] = "active"
            
        # Publish snapshot as JSON
        msg = String()
        msg.data = json.dumps(self.scene_memory)
        self.state_pub.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = WorldModelNode()
    try:
        rclpy.spin(node)
    except Exception:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()
