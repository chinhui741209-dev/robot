#!/usr/bin/env python3
"""
W2 Demo - Runs components for demo duration
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu, Image
from geometry_msgs.msg import Pose, Twist
from std_msgs.msg import String, Header
import math
import time
import numpy as np

class W2Demo(Node):
    def __init__(self):
        super().__init__('w2_demo')
        
        # Buddy publishers
        self.buddy_imu = self.create_publisher(Imu, '/buddy/imu', 10)
        self.buddy_motor = self.create_publisher(Twist, '/buddy/motor_state', 10)
        self.buddy_health = self.create_publisher(String, '/buddy/hal/health', 10)
        
        # Omni publishers  
        self.omni_imu = self.create_publisher(Imu, '/omni/imu', 10)
        self.omni_motor = self.create_publisher(Twist, '/omni/motor_state', 10)
        self.omni_health = self.create_publisher(String, '/omni/hal/health', 10)
        
        # State & Policy
        self.pose = self.create_publisher(Pose, '/state/pose', 100)
        self.action = self.create_publisher(Twist, '/policy/action', 10)
        
        # Perception
        self.camera = self.create_publisher(Image, '/perception/camera', 10)
        
        # Recorder
        self.recorder = self.create_publisher(String, '/recorder/status', 10)
        
        self.create_timer(0.001, self.tick)
        self.c = 0
        self.get_logger().info('W2 Demo started')
        
    def tick(self):
        self.c += 1
        t = self.get_clock().now()
        
        # 1000 Hz: Buddy + Omni
        imu = Imu()
        imu.header.stamp = t.to_msg()
        imu.header.frame_id = 'buddy'
        imu.orientation.x = math.sin(self.c * 0.001)
        imu.orientation.w = math.cos(self.c * 0.001)
        imu.linear_acceleration.z = 9.8
        self.buddy_imu.publish(imu)
        self.buddy_motor.publish(Twist())
        self.buddy_health.publish(String(data='OK'))
        
        imu2 = Imu()
        imu2.header.stamp = t.to_msg()
        imu2.header.frame_id = 'omni'
        imu2.orientation.x = math.sin(self.c * 0.0008)
        imu2.orientation.w = math.cos(self.c * 0.0008)
        imu2.linear_acceleration.z = 9.8
        self.omni_imu.publish(imu2)
        self.omni_motor.publish(Twist())
        self.omni_health.publish(String(data='OK'))
        
        # 500 Hz: State
        if self.c % 2 == 0:
            pose = Pose()
            pose.position.x = math.sin(self.c * 0.001) * 0.1
            self.pose.publish(pose)
        
        # 50 Hz: Policy
        if self.c % 20 == 0:
            act = Twist()
            act.linear.x = math.sin(time.time()) * 0.1
            self.action.publish(act)
        
        # 15 Hz: Camera
        if self.c % 67 == 0:
            img = Image()
            h = Header()
            h.stamp = t.to_msg()
            h.frame_id = 'camera'
            img.header = h
            img.height = 240
            img.width = 320
            img.encoding = 'rgb8'
            img.step = 320 * 3
            img.data = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8).tobytes()
            self.camera.publish(img)
        
        # 1 Hz: Recorder
        if self.c % 1000 == 0:
            self.recorder.publish(String(data=f'W2 Demo: {self.c // 1000}s'))

def main():
    rclpy.init()
    node = W2Demo()
    executor = rclpy.executors.MultiThreadedExecutor(num_threads=2)
    executor.add_node(node)
    
    print('W2 Demo running for 10 seconds...')
    
    # Run for 10 seconds
    for _ in range(100):
        executor.spin_once(timeout_sec=0.1)
        time.sleep(0.1)
    
    print('W2 Demo complete')
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()