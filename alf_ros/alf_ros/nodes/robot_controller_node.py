"""ROS2 node providing high-level robot control for Unitree G1 EDU."""

from __future__ import annotations

import logging
import sys
from typing import Optional

try:
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String, Bool
    from geometry_msgs.msg import Twist
    from sensor_msgs.msg import JointState

    HAS_ROS = True
except ImportError:
    HAS_ROS = False
    Node = object  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)

ROBOT_MODES = {
    "idle": "IDLE",
    "stand": "STANDING",
    "lie_down": "LYING",
    "home_position": "HOME",
    "walk": "WALKING",
}

SAFE_HOME_POSITIONS: dict[str, float] = {
    "left_hip_pitch_joint": 0.0,
    "left_hip_roll_joint": 0.0,
    "left_hip_yaw_joint": 0.0,
    "left_knee_joint": 0.0,
    "left_ankle_pitch_joint": 0.0,
    "left_ankle_roll_joint": 0.0,
    "right_hip_pitch_joint": 0.0,
    "right_hip_roll_joint": 0.0,
    "right_hip_yaw_joint": 0.0,
    "right_knee_joint": 0.0,
    "right_ankle_pitch_joint": 0.0,
    "right_ankle_roll_joint": 0.0,
    "waist_yaw_joint": 0.0,
    "waist_roll_joint": 0.0,
    "waist_pitch_joint": 0.0,
    "left_shoulder_pitch_joint": 0.0,
    "left_shoulder_roll_joint": 0.0,
    "left_shoulder_yaw_joint": 0.0,
    "left_elbow_joint": 0.0,
    "right_shoulder_pitch_joint": 0.0,
    "right_shoulder_roll_joint": 0.0,
    "right_shoulder_yaw_joint": 0.0,
    "right_elbow_joint": 0.0,
}

if HAS_ROS:

    class RobotControllerNode(Node):  # type: ignore[valid-type,misc]
        """High-level robot controller node for Unitree G1 EDU.

        Subscribes to command topics and publishes joint commands, velocity
        commands, and status messages. Provides an abstraction layer over
        the low-level Unitree G1 SDK topics.
        """

        def __init__(self) -> None:
            super().__init__("alf_ros_controller")

            self.declare_parameter("robot_namespace", "")
            self.declare_parameter("publish_rate_hz", 50.0)
            self.declare_parameter("max_linear_vel", 0.5)
            self.declare_parameter("max_angular_vel", 1.0)

            ns = self.get_parameter("robot_namespace").value
            prefix = f"/{ns}" if ns else ""

            self._current_mode: str = "IDLE"
            self._estop_active: bool = False
            self._max_linear = float(self.get_parameter("max_linear_vel").value)
            self._max_angular = float(self.get_parameter("max_angular_vel").value)

            self._status_pub = self.create_publisher(
                String, f"{prefix}/alf_ros/status", 10
            )
            self._joint_cmd_pub = self.create_publisher(
                JointState, f"{prefix}/joint_commands", 10
            )
            self._cmd_vel_pub = self.create_publisher(Twist, f"{prefix}/cmd_vel", 10)

            self._command_sub = self.create_subscription(
                String, f"{prefix}/alf_ros/command", self._on_command, 10
            )
            self._estop_sub = self.create_subscription(
                Bool, f"{prefix}/alf_ros/emergency_stop", self._on_estop, 10
            )

            self._status_timer = self.create_timer(1.0, self._publish_status)

            self.get_logger().info("Robot controller node initialized")
            self._publish_status()

        def _on_command(self, msg: String) -> None:
            if self._estop_active:
                self.get_logger().warn("Command ignored — emergency stop active!")
                return

            command = msg.data.strip().lower()
            if command not in ROBOT_MODES:
                self.get_logger().warn(f"Unknown command: {command}")
                return

            self.get_logger().info(f"Received command: {command}")
            handler = {
                "stand": self._cmd_stand,
                "lie_down": self._cmd_lie_down,
                "home_position": self._cmd_home_position,
                "idle": self._cmd_idle,
                "walk": self._cmd_walk,
            }.get(command)

            if handler:
                handler()

        def _on_estop(self, msg: Bool) -> None:
            if msg.data:
                self._estop_active = True
                self._current_mode = "EMERGENCY_STOP"
                twist = Twist()
                self._cmd_vel_pub.publish(twist)
                self.get_logger().error("EMERGENCY STOP received!")
                self._publish_status()
            else:
                self._estop_active = False
                self._current_mode = "IDLE"
                self.get_logger().info("Emergency stop cleared")
                self._publish_status()

        def _cmd_stand(self) -> None:
            self._current_mode = "STANDING"
            self.get_logger().info("Executing: stand up")
            self._publish_status()

        def _cmd_lie_down(self) -> None:
            self._current_mode = "LYING"
            self.get_logger().info("Executing: lie down")
            self._publish_status()

        def _cmd_home_position(self) -> None:
            self._current_mode = "HOME"
            self.get_logger().info("Executing: move to home position")
            self._send_joint_command(SAFE_HOME_POSITIONS)
            self._publish_status()

        def _cmd_idle(self) -> None:
            self._current_mode = "IDLE"
            self.get_logger().info("Executing: idle mode")
            self._publish_status()

        def _cmd_walk(self) -> None:
            """Switch the robot to walking mode and publish the updated status."""
            self._current_mode = "WALKING"
            self.get_logger().info("Executing: walk mode")
            self._publish_status()

        def _send_joint_command(self, positions: dict[str, float]) -> None:
            msg = JointState()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.name = list(positions.keys())
            msg.position = list(positions.values())
            self._joint_cmd_pub.publish(msg)

        def _publish_status(self) -> None:
            msg = String()
            msg.data = self._current_mode
            self._status_pub.publish(msg)


def main(args: Optional[list[str]] = None) -> None:
    """Entry point for the robot controller node."""
    if not HAS_ROS:
        print("ERROR: rclpy is not installed. Cannot start ROS2 node.")
        sys.exit(1)

    rclpy.init(args=args)
    node = RobotControllerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Robot controller node shutting down")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
