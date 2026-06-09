#!/usr/bin/env python3
"""
Planner Node - event-driven, closed-loop task sequencer (Phase 2).

Replaces the old open-loop "+1 every second" planner. Each step's precondition
(which object must be present) is checked against the World Model scene graph;
a step advances only when its precondition has held for a few consecutive
checks, retries on timeout, and fails after exhausting retries.

Subscribes:  /task/parsed_command  std_msgs/String (JSON intent/source/target/steps)
             /world_model/state     std_msgs/String (JSON, present_classes[])
Publishes:   /planner/current_step  std_msgs/Int32
             /planner/state         std_msgs/String  (IDLE/RUNNING/COMPLETED/FAILED)
             /planner/status        std_msgs/String  (JSON event detail)
             /planner/task_plan     std_msgs/Float32MultiArray
             /arbiter/mode          std_msgs/String  (IDLE/LOCOMOTION/MANIPULATION)
"""

import os
import sys
import json
import time
import signal

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Int32, Float32MultiArray

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from planner.step_logic import StepSequencer, RUNNING, COMPLETED, FAILED

MANIP_KEYWORDS = ("grasp", "release", "move_to", "pick", "place", "gripper")


class PlannerNode(Node):
    def __init__(self):
        super().__init__("planner")
        self.declare_parameter("tick_hz", 4.0)
        self.declare_parameter("confirm_needed", 2)
        self.declare_parameter("timeout_s", 5.0)
        self.declare_parameter("max_retries", 2)

        self.create_subscription(String, "/task/parsed_command", self.command_callback, 10)
        self.create_subscription(String, "/world_model/state", self.world_callback, 10)

        self.plan_pub = self.create_publisher(Float32MultiArray, "/planner/task_plan", 10)
        self.step_pub = self.create_publisher(Int32, "/planner/current_step", 10)
        self.state_pub = self.create_publisher(String, "/planner/state", 10)
        self.status_pub = self.create_publisher(String, "/planner/status", 10)
        self.mode_pub = self.create_publisher(String, "/arbiter/mode", 10)

        self.seq = None
        self.present_classes = []
        tick = self.get_parameter("tick_hz").value
        self.create_timer(1.0 / tick, self.tick)
        self.get_logger().info("Planner (event-driven, closed-loop) started")

    def command_callback(self, msg):
        try:
            cmd = json.loads(msg.data)
        except Exception:
            self.get_logger().error(f"bad command: {msg.data}")
            return
        steps = cmd.get("steps", [])
        self.seq = StepSequencer(
            steps, source=cmd.get("source"), target=cmd.get("target"),
            confirm_needed=self.get_parameter("confirm_needed").value,
            timeout_s=self.get_parameter("timeout_s").value,
            max_retries=self.get_parameter("max_retries").value,
        )
        self.get_logger().info(f"Task '{cmd.get('intent')}' with {len(steps)} steps; "
                               f"source={cmd.get('source')} target={cmd.get('target')}")
        plan = Float32MultiArray()
        plan.data = [float(i) for i in range(len(steps))]
        self.plan_pub.publish(plan)

    def world_callback(self, msg):
        try:
            self.present_classes = json.loads(msg.data).get("present_classes", [])
        except Exception:
            pass

    def _mode_for_step(self, step):
        if step is None:
            return "IDLE"
        s = step.lower()
        return "MANIPULATION" if any(k in s for k in MANIP_KEYWORDS) else "LOCOMOTION"

    def tick(self):
        if self.seq is None:
            self._publish_mode("IDLE")
            return
        now = time.monotonic()
        ev = self.seq.update(self.present_classes, now)

        self.step_pub.publish(Int32(data=int(max(ev["idx"], 0))))
        self.state_pub.publish(String(data=ev["state"]))
        self.status_pub.publish(String(data=json.dumps(ev)))
        self._publish_mode(self._mode_for_step(ev["step"]) if ev["state"] == RUNNING else "IDLE")

        if ev["advanced"] or ev["state"] in (COMPLETED, FAILED):
            lvl = self.get_logger().warn if ev["state"] == FAILED else self.get_logger().info
            lvl(f"[{ev['state']}] step={ev['idx']} '{ev['step']}' :: {ev['reason']}")
        if ev["state"] in (COMPLETED, FAILED):
            self.seq = None  # latch; await next command

    def _publish_mode(self, mode):
        self.mode_pub.publish(String(data=mode))


def main(args=None):
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    rclpy.init(args=args)
    node = PlannerNode()
    from rclpy.executors import MultiThreadedExecutor
    executor = MultiThreadedExecutor(num_threads=1)
    executor.add_node(node)
    try:
        executor.spin()
    except (KeyboardInterrupt, Exception) as e:
        node.get_logger().error(f"spin: {e}")
    finally:
        try:
            node.destroy_node()
        except Exception:
            pass
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
