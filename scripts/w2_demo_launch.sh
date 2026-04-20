#!/bin/bash
# W2 Demo Launcher - Runs all components in background processes

source /opt/ros/humble/setup.bash
cd ~/poc/poc-orin/scripts

echo "=== Starting W2 Components ==="

# Component 1: Buddy + Omni IMU (1000 Hz combined at 1ms tick)
python3 -c "
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from geometry_msgs.msg import Twist
from std_msgs.msg import String
import math

class IMUNode(Node):
    def __init__(self):
        super().__init__('imu_node')
        self.buddy_pub = self.create_publisher(Imu, '/buddy/imu', 10)
        self.omni_pub = self.create_publisher(Imu, '/omni/imu', 10)
        self.buddy_motor = self.create_publisher(Twist, '/buddy/motor_state', 10)
        self.omni_motor = self.create_publisher(Twist, '/omni/motor_state', 10)
        self.buddy_health = self.create_publisher(String, '/buddy/hal/health', 10)
        self.omni_health = self.create_publisher(String, '/omni/hal/health', 10)
        self.timer = self.create_timer(0.001, self.tick)
        self.c = 0
    def tick(self):
        self.c += 1
        t = self.get_clock().now()
        for pub, frame in [(self.buddy_pub, 'buddy'), (self.omni_pub, 'omni')]:
            imu = Imu()
            imu.header.stamp = t.to_msg()
            imu.header.frame_id = f'{frame}_imu'
            imu.orientation.x = math.sin(self.c * 0.001)
            imu.orientation.w = math.cos(self.c * 0.001)
            imu.linear_acceleration.z = 9.8
            pub.publish(imu)
        for m in [self.buddy_motor, self.omni_motor]:
            m.publish(Twist())
        self.buddy_health.publish(String(data='OK'))
        self.omni_health.publish(String(data='OK'))

rclpy.init()
n = IMUNode()
e = rclpy.executors.SingleThreadedExecutor()
e.add_node(n)
while rclpy.ok(): e.spin_once(timeout_sec=0.1)
n.destroy_node()
rclpy.shutdown()
" &

# Component 2: State Pose + Policy (500 Hz + 50 Hz)
python3 -c "
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Pose, Twist
import math, time

class StateNode(Node):
    def __init__(self):
        super().__init__('state_node')
        self.pose_pub = self.create_publisher(Pose, '/state/pose', 10)
        self.action_pub = self.create_publisher(Twist, '/policy/action', 10)
        self.timer = self.create_timer(0.002, self.tick)
        self.c = 0
    def tick(self):
        self.c += 1
        pose = Pose()
        pose.position.x = math.sin(self.c * 0.001) * 0.1
        self.pose_pub.publish(pose)
        if self.c % 10 == 0:
            action = Twist()
            action.linear.x = math.sin(time.time()) * 0.1
            self.action_pub.publish(action)

rclpy.init()
n = StateNode()
e = rclpy.executors.SingleThreadedExecutor()
e.add_node(n)
while rclpy.ok(): e.spin_once(timeout_sec=0.1)
n.destroy_node()
rclpy.shutdown()
" &

# Component 3: Camera + Recorder (15 Hz + 1 Hz)
python3 -c "
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String, Header
import numpy as np

class CamNode(Node):
    def __init__(self):
        super().__init__('cam_node')
        self.cam_pub = self.create_publisher(Image, '/perception/camera', 10)
        self.rec_pub = self.create_publisher(String, '/recorder/status', 10)
        self.timer = self.create_timer(0.067, self.tick)
        self.c = 0
    def tick(self):
        self.c += 1
        img = Image()
        h = Header()
        h.stamp = self.get_clock().now().to_msg()
        h.frame_id = 'camera'
        img.header = h
        img.height = 240
        img.width = 320
        img.encoding = 'rgb8'
        img.step = 320 * 3
        img.data = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8).tobytes()
        self.cam_pub.publish(img)
        if self.c % 60 == 0:
            self.rec_pub.publish(String(data=f'W2: {self.c}'))

rclpy.init()
n = CamNode()
e = rclpy.executors.SingleThreadedExecutor()
e.add_node(n)
while rclpy.ok(): e.spin_once(timeout_sec=0.1)
n.destroy_node()
rclpy.shutdown()
" &

echo "=== W2 Started ==="
sleep 1

# Show topics
ros2 topic list