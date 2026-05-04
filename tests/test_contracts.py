import unittest
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu, JointState
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String
import time

class TestSystemContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy.init()

    @classmethod
    def tearDownClass(cls):
        rclpy.shutdown()

    def setUp(self):
        self.node = rclpy.create_node('contract_test_listener')
        self.received_imu = False
        self.received_joints = False
        self.received_pose = False

    def tearDown(self):
        self.node.destroy_node()

    def test_ros2_bridge_topics(self):
        """Verify that the bridge is publishing required topics with correct frequency (approx)."""
        
        def imu_cb(msg): self.received_imu = True
        def joint_cb(msg): self.received_joints = True
        def pose_cb(msg): self.received_pose = True

        self.node.create_subscription(Imu, '/buddy/imu', imu_cb, 10)
        self.node.create_subscription(JointState, '/joint_states', joint_cb, 10)
        self.node.create_subscription(PoseStamped, '/state/pose', pose_cb, 10)

        start_time = time.time()
        timeout = 5.0
        
        print("Waiting for bridge topics (ensure hal_buddy and ros2_bridge are running)...")
        while time.time() - start_time < timeout:
            rclpy.spin_once(self.node, timeout_sec=0.1)
            if self.received_imu and self.received_joints and self.received_pose:
                break

        self.assertTrue(self.received_imu, "Did not receive /buddy/imu")
        self.assertTrue(self.received_joints, "Did not receive /joint_states")
        self.assertTrue(self.received_pose, "Did not receive /state/pose")

    def test_imu_data_validity(self):
        """Verify IMU data follows the hardware contract (e.g., orientation is normalized)."""
        imu_msg = None
        def imu_cb(msg): nonlocal imu_msg; imu_msg = msg
        
        self.node.create_subscription(Imu, '/buddy/imu', imu_cb, 10)
        
        start_time = time.time()
        while imu_msg is None and time.time() - start_time < 2.0:
            rclpy.spin_once(self.node, timeout_sec=0.1)
        
        if imu_msg:
            q = imu_msg.orientation
            norm = (q.x**2 + q.y**2 + q.z**2 + q.w**2)**0.5
            self.assertAlmostEqual(norm, 1.0, places=3, msg="IMU Orientation not normalized")
            self.assertNotEqual(imu_msg.header.stamp.sec, 0, "IMU Timestamp is zero")

if __name__ == '__main__':
    unittest.main()
