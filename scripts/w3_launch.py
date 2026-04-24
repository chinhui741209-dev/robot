#!/usr/bin/env python3
"""
W3 Launch - End-to-End Integration Demo
Includes: Buddy + Omni + State + Policy + Percep + Chaos + Demo Scripts
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu, Image
from geometry_msgs.msg import Pose, Twist
from std_msgs.msg import String, Header, Float32MultiArray
import math
import time
import numpy as np
import random


class W3Node(Node):
    def __init__(self):
        super().__init__("w3_launch")

        # =====================
        # BUDDY Subsystem (1000 Hz)
        # =====================
        self.buddy_imu_pub = self.create_publisher(Imu, "/imu/data", 10)
        self.buddy_motor_pub = self.create_publisher(Twist, "/buddy/motor_state", 10)
        self.buddy_health_pub = self.create_publisher(String, "/buddy/hal/health", 10)

        # =====================
        # OMNI Subsystem (1000 Hz)
        # =====================
        self.omni_imu_pub = self.create_publisher(Imu, "/omni/imu", 10)
        self.omni_motor_pub = self.create_publisher(Twist, "/omni/motor_state", 10)
        self.omni_health_pub = self.create_publisher(String, "/omni/hal/health", 10)

        # =====================
        # STATE Estimator (500 Hz)
        # =====================
        self.pose_pub = self.create_publisher(Pose, "/state/pose", 100)
        self.tf_pub = self.create_publisher(Twist, "/tf", 10)

        # =====================
        # PERCEPTION (15 Hz)
        # =====================
        self.camera_pub = self.create_publisher(Image, "/camera/image_raw", 10)
        self.lidar_pub = self.create_publisher(
            Float32MultiArray, "/perception/lidar", 10
        )

        # =====================
        # METRICS & OBSERVABILITY (1 Hz)
        # =====================
        self.metrics_pub = self.create_publisher(
            Float32MultiArray, "/metrics/system", 10
        )
        self.jitter_pub = self.create_publisher(
            Float32MultiArray, "/metrics/rt_jitter", 10
        )

        # =====================
        # RECORDER & STATUS (1 Hz)
        # =====================
        self.recorder_pub = self.create_publisher(String, "/recorder/status", 10)

        # =====================
        # CHAOS INJECTION State
        # =====================
        self.chaos_mode = "none"  # none, imu_drop, cpu_spike
        self.chaos_counter = 0

        # =====================
        # DEMO State
        # =====================
        self.demo_mode = "idle"
        self.demo_act = 0

        # Main timer: 1ms = 1000 Hz base
        self.timer = self.create_timer(0.001, self.tick)

        self.counter = 0
        self.start_time = time.time()

        self.get_logger().info("W3 Launch started - E2E Demo System")

    def tick(self):
        try:
            self.counter += 1
            self.chaos_counter += 1
            t = self.get_clock().now()

            # =====================
            # Chaos Injection
            # =====================
            inject_error = False
            if self.chaos_mode == "imu_drop" and self.chaos_counter % 10 == 0:
                inject_error = True
            elif self.chaos_mode == "cpu_spike" and self.chaos_counter % 5 == 0:
                inject_error = True

            # =====================
            # BUDDY (1000 Hz)
            # =====================
            if not inject_error:
                imu = Imu()
                imu.header.stamp = t.to_msg()
                imu.header.frame_id = "imu_link"

                imu.orientation.x = math.sin(self.counter * 0.001)
                imu.orientation.y = math.cos(self.counter * 0.001)
                imu.orientation.z = math.sin(self.counter * 0.0005)
                imu.orientation.w = math.cos(self.counter * 0.0005)

                imu.angular_velocity.x = math.sin(self.counter * 0.01) * 0.1
                imu.angular_velocity.y = math.cos(self.counter * 0.01) * 0.1
                imu.angular_velocity.z = math.sin(self.counter * 0.005) * 0.05

                imu.linear_acceleration.x = 0.0
                imu.linear_acceleration.y = 0.0
                imu.linear_acceleration.z = 9.8

                self.buddy_imu_pub.publish(imu)

            self.buddy_motor_pub.publish(Twist())
            health = String()
            health.data = "OK" if self.chaos_mode == "none" else "DEGRADED"
            self.buddy_health_pub.publish(health)

            # =====================
            # OMNI (1000 Hz)
            # =====================
            if not inject_error:
                imu2 = Imu()
                imu2.header.stamp = t.to_msg()
                imu2.header.frame_id = "omni_imu"

                imu2.orientation.x = math.sin(self.counter * 0.0008)
                imu2.orientation.y = math.cos(self.counter * 0.0008)
                imu2.orientation.z = math.sin(self.counter * 0.0004)
                imu2.orientation.w = math.cos(self.counter * 0.0004)

                imu2.angular_velocity.x = math.sin(self.counter * 0.008) * 0.08
                imu2.angular_velocity.y = math.cos(self.counter * 0.008) * 0.08
                imu2.angular_velocity.z = math.sin(self.counter * 0.004) * 0.04

                imu2.linear_acceleration.z = 9.8

                self.omni_imu_pub.publish(imu2)

            self.omni_motor_pub.publish(Twist())
            self.omni_health_pub.publish(
                String(data="OK" if self.chaos_mode == "none" else "DEGRADED")
            )

            # =====================
            # STATE Estimator (500 Hz = every 2 tick)
            # =====================
            if self.counter % 2 == 0:
                pose = Pose()
                pose.position.x = math.sin(self.counter * 0.001) * 0.1
                pose.position.y = math.cos(self.counter * 0.001) * 0.1
                pose.position.z = math.sin(self.counter * 0.0005) * 0.05

                pose.orientation.x = math.sin(self.counter * 0.001)
                pose.orientation.y = math.cos(self.counter * 0.001)
                pose.orientation.z = math.sin(self.counter * 0.0005)
                pose.orientation.w = math.cos(self.counter * 0.0005)

                self.pose_pub.publish(pose)

                # TF
                tf = Twist()
                tf.linear.x = math.sin(self.counter * 0.001) * 0.1
                tf.angular.z = math.cos(self.counter * 0.001) * 0.01
                self.tf_pub.publish(tf)

            # =====================
            # PERCEPTION (15 Hz = every 67 tick)
            # =====================
            if self.counter % 67 == 0:

                # Lidar (simulated point cloud)
                lidar = Float32MultiArray()
                lidar.data = [random.uniform(-5, 5) for _ in range(10)]
                self.lidar_pub.publish(lidar)

            # =====================
            # METRICS (1 Hz = every 1000 tick)
            # =====================
            if self.counter % 1000 == 0:
                elapsed = time.time() - self.start_time

                # System metrics
                m = Float32MultiArray()
                m.data = [
                    random.uniform(20, 40),  # CPU %
                    random.uniform(30, 50),  # MEM %
                    random.uniform(40, 55),  # Temp C
                    random.uniform(0.5, 1.5),  # GPU %
                    random.uniform(950, 1050),  # Buddy Hz
                    random.uniform(950, 1050),  # Omni Hz
                ]
                self.metrics_pub.publish(m)

                # RT Jitter (simulated)
                j = Float32MultiArray()
                j.data = [
                    random.uniform(10, 50),  # avg us
                    random.uniform(50, 150),  # max us
                    random.uniform(100, 200),  # p99 us
                ]
                self.jitter_pub.publish(j)

                # Recorder status
                s = String()
                s.data = f"SYS:{elapsed:.0f}s Buddy:{self.counter // 1000} Omni:{self.counter // 1000} Pose:{self.counter // 2} Act:{self.counter // 20} Cam:{self.counter // 67} Chaos:{self.chaos_mode}"
                self.recorder_pub.publish(s)

        except Exception as e:
            self.get_logger().error(f"Tick error: {e}")


def main(args=None):
    try:
        rclpy.init(args=args)
        node = W3Node()
        
        # Add backend logic nodes for end-to-end demo
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        from policy.vla_inference_node import VlaInferenceNode
        from skill.scripts.skill_node import SkillNode
        from world_model.scripts.world_model_node import WorldModelNode
        from robot_bridge.scripts.robot_bridge_node import RobotBridgeNode
        
        vla_node = VlaInferenceNode()
        world_model = WorldModelNode()
        skill_node = SkillNode()
        robot_bridge = RobotBridgeNode()
        
        executor = rclpy.executors.MultiThreadedExecutor(num_threads=5)
        executor.add_node(node)
        executor.add_node(vla_node)
        executor.add_node(world_model)
        executor.add_node(skill_node)
        executor.add_node(robot_bridge)

        print("=" * 50)
        print("W3 Launch - E2E Demo System")
        print("=" * 50)
        print("Running... Press Ctrl-C to stop")

        try:
            executor.spin()
        except KeyboardInterrupt:
            pass

    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            node.destroy_node()
            vla_node.destroy_node()
            world_model.destroy_node()
            skill_node.destroy_node()
            robot_bridge.destroy_node()
        except:
            pass
        try:
            rclpy.shutdown()
        except:
            pass


if __name__ == "__main__":
    main()
