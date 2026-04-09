"""ROS2 node that hosts the ALF-ROS GUI application."""

from __future__ import annotations

import logging
import sys
import threading
from typing import Any, Optional

try:
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String, Bool
    from sensor_msgs.msg import JointState, BatteryState
    from geometry_msgs.msg import Twist

    HAS_ROS = True
except ImportError:
    HAS_ROS = False
    Node = object  # type: ignore[assignment,misc]

try:
    from PyQt5.QtWidgets import QApplication

    HAS_QT = True
except ImportError:
    HAS_QT = False

logger = logging.getLogger(__name__)

JOINT_NAMES_G1 = [
    "left_hip_pitch_joint",
    "left_hip_roll_joint",
    "left_hip_yaw_joint",
    "left_knee_joint",
    "left_ankle_pitch_joint",
    "left_ankle_roll_joint",
    "right_hip_pitch_joint",
    "right_hip_roll_joint",
    "right_hip_yaw_joint",
    "right_knee_joint",
    "right_ankle_pitch_joint",
    "right_ankle_roll_joint",
    "waist_yaw_joint",
    "waist_roll_joint",
    "waist_pitch_joint",
    "left_shoulder_pitch_joint",
    "left_shoulder_roll_joint",
    "left_shoulder_yaw_joint",
    "left_elbow_joint",
    "right_shoulder_pitch_joint",
    "right_shoulder_roll_joint",
    "right_shoulder_yaw_joint",
    "right_elbow_joint",
]


def _compute_update_period(update_rate_hz: float) -> float:
    """Compute a safe GUI refresh timer period.

    Args:
        update_rate_hz: Desired GUI update rate in hertz.

    Returns:
        Timer period in seconds.

    Raises:
        ValueError: If ``update_rate_hz`` is not positive.
    """
    if update_rate_hz <= 0.0:
        raise ValueError("update_rate_hz must be > 0.0")
    return 1.0 / update_rate_hz


class ROSBridge:
    """Bridge between the Qt GUI and the ROS2 node."""

    def __init__(self, node: "GUINode") -> None:
        self._node = node

    def get_node_names(self) -> list[str]:
        """Return list of known ROS2 node names."""
        return self._node.get_node_names()

    def get_topic_names_and_types(self) -> list[tuple[str, str]]:
        """Return list of (topic_name, type) tuples."""
        raw = self._node.get_topic_names_and_types()
        return [(name, types[0] if types else "?") for name, types in raw]

    def get_service_names_and_types(self) -> list[tuple[str, str]]:
        """Return list of (service_name, type) tuples."""
        raw = self._node.get_service_names_and_types()
        return [(name, types[0] if types else "?") for name, types in raw]

    def get_action_names_and_types(self) -> list[tuple[str, str]]:
        """Return list of (action_name, type) tuples."""
        getter = getattr(self._node, "get_action_names_and_types", None)
        if getter is None:
            return []
        raw = getter()
        return [(name, types[0] if types else "?") for name, types in raw]

    def get_publishers_info_by_topic(self, topic: str) -> list[dict[str, str]]:
        """Return publishers metadata for a topic."""
        infos = self._node.get_publishers_info_by_topic(topic)
        return [self._format_endpoint_info(info) for info in infos]

    def get_subscribers_info_by_topic(self, topic: str) -> list[dict[str, str]]:
        """Return subscribers metadata for a topic."""
        infos = self._node.get_subscriptions_info_by_topic(topic)
        return [self._format_endpoint_info(info) for info in infos]

    def get_topic_graph(self) -> list[tuple[str, str, int, int]]:
        """Return graph rows: topic, type, publisher count, subscriber count."""
        topics = self.get_topic_names_and_types()
        graph_data: list[tuple[str, str, int, int]] = []
        for topic, msg_type in topics:
            publishers = self.get_publishers_info_by_topic(topic)
            subscribers = self.get_subscribers_info_by_topic(topic)
            graph_data.append((topic, msg_type, len(publishers), len(subscribers)))
        return graph_data

    @staticmethod
    def _format_endpoint_info(info: Any) -> dict[str, str]:
        """Convert ROS topic endpoint info to a serializable dictionary."""
        qos_profile = getattr(info, "qos_profile", None)
        reliability = getattr(qos_profile, "reliability", None)
        durability = getattr(qos_profile, "durability", None)
        return {
            "node_name": str(getattr(info, "node_name", "")),
            "node_namespace": str(getattr(info, "node_namespace", "")),
            "topic_type": str(getattr(info, "topic_type", "")),
            "endpoint_type": str(getattr(info, "endpoint_type", "")),
            "qos_reliability": str(reliability) if reliability is not None else "",
            "qos_durability": str(durability) if durability is not None else "",
        }

    def echo_topic(self, topic: str) -> None:
        """Subscribe to a topic and log messages."""
        self._node.log_info(f"Echo requested for: {topic}")

    def publish_to_topic(self, topic: str, message: str) -> None:
        """Publish a string message to a topic."""
        self._node.publish_string(topic, message)

    def send_action_goal(self, server: str, goal: str) -> None:
        """Send an action goal."""
        self._node.log_info(f"Action goal -> {server}: {goal}")

    def cancel_action_goal(self, server: str) -> None:
        """Cancel an active action goal."""
        self._node.log_info(f"Cancel goal -> {server}")

    def send_robot_command(self, command: str) -> None:
        """Send a high-level robot command."""
        self._node.send_robot_command(command)

    def emergency_stop(self) -> None:
        """Activate emergency stop."""
        self._node.emergency_stop()


if HAS_ROS:

    class GUINode(Node):  # type: ignore[valid-type,misc]
        """ROS2 node that manages the Qt GUI and ROS2 communication."""

        def __init__(self) -> None:
            super().__init__("alf_ros_gui")
            self._window: Any = None
            self._joint_states: dict[str, float] = {}
            self._battery_level: float = 0.0
            self._connected: bool = False

            self.declare_parameter("robot_namespace", "")
            self.declare_parameter("update_rate_hz", 10.0)

            ns = self.get_parameter("robot_namespace").value
            prefix = f"/{ns}" if ns else ""

            self._cmd_vel_pub = self.create_publisher(Twist, f"{prefix}/cmd_vel", 10)
            self._command_pub = self.create_publisher(
                String, f"{prefix}/alf_ros/command", 10
            )
            self._estop_pub = self.create_publisher(
                Bool, f"{prefix}/alf_ros/emergency_stop", 10
            )

            self._joint_state_sub = self.create_subscription(
                JointState, f"{prefix}/joint_states", self._on_joint_states, 10
            )
            self._battery_sub = self.create_subscription(
                BatteryState,
                f"{prefix}/battery_state",
                self._on_battery,
                10,
            )
            self._status_sub = self.create_subscription(
                String, f"{prefix}/alf_ros/status", self._on_status, 10
            )

            rate = float(self.get_parameter("update_rate_hz").value)
            timer_period = _compute_update_period(rate)
            self._update_timer = self.create_timer(timer_period, self._update_gui)

            self.get_logger().info("GUI node initialized")

        def _on_joint_states(self, msg: Any) -> None:
            states = {name: pos for name, pos in zip(msg.name, msg.position)}
            self._joint_states = states
            if self._window:
                self._window.robot_panel.update_joints(states)
                self._window.log("DEBUG", f"Odebrano stany stawów: {len(states)} stawów")

        def _on_battery(self, msg: Any) -> None:
            self._battery_level = msg.percentage * 100.0
            self._connected = True
            if self._window:
                self._window.robot_panel.update_battery(self._battery_level)
                self._window.robot_panel.update_connection(True)

        def _on_status(self, msg: Any) -> None:
            if self._window:
                self._window.log("INFO", f"Status robota: {msg.data}")
                self._window.robot_panel.update_mode(msg.data)
                self._window.status_bar.showMessage(f"Status: {msg.data}")

        def _update_gui(self) -> None:
            pass

        def publish_string(self, topic: str, message: str) -> None:
            """Publish a string message to a topic.

            Creates a publisher on demand and caches it for reuse.

            Args:
                topic: Topic name.
                message: String payload.
            """
            if not hasattr(self, "_string_publishers"):
                self._string_publishers: dict[str, Any] = {}
            if topic not in self._string_publishers:
                self._string_publishers[topic] = self.create_publisher(String, topic, 10)
            msg = String()
            msg.data = message
            self._string_publishers[topic].publish(msg)
            self.get_logger().info(f"Publishing to {topic}: {message}")

        def send_robot_command(self, command: str) -> None:
            """Publish a high-level robot command.

            Args:
                command: Command string (e.g., 'stand', 'lie_down', 'home_position').
            """
            msg = String()
            msg.data = command
            self._command_pub.publish(msg)
            self.get_logger().info(f"Robot command sent: {command}")
            if self._window:
                self._window.log("INFO", f"Komenda wysłana: {command}")
                self._window.status_bar.showMessage(f"Komenda: {command}")

        def emergency_stop(self) -> None:
            """Activate emergency stop by publishing True to the estop topic."""
            msg = Bool()
            msg.data = True
            self._estop_pub.publish(msg)
            self.get_logger().error("EMERGENCY STOP ACTIVATED!")

        def log_info(self, message: str) -> None:
            """Log an informational message.

            Args:
                message: The message to log.
            """
            self.get_logger().info(message)
            if self._window:
                self._window.log("INFO", message)

        def set_window(self, window: Any) -> None:
            """Associate the Qt main window with this node.

            Args:
                window: The MainWindow instance.
            """
            self._window = window


def main(args: Optional[list[str]] = None) -> None:
    """Entry point for the GUI node."""
    if not HAS_ROS:
        print("ERROR: rclpy is not installed. Cannot start ROS2 node.")
        sys.exit(1)

    rclpy.init(args=args)
    node = GUINode()

    if not HAS_QT:
        node.get_logger().error("PyQt5 is not installed. Cannot start GUI.")
        rclpy.shutdown()
        return

    app = QApplication(sys.argv)
    from ..gui.main_window import MainWindow

    bridge = ROSBridge(node)
    window = MainWindow(ros_bridge=bridge)
    node.set_window(window)
    window.show()
    window.log("INFO", "Interfejs GUI uruchomiony")

    ros_thread = threading.Thread(target=lambda: rclpy.spin(node), daemon=True)
    ros_thread.start()

    exit_code = app.exec_()
    node.destroy_node()
    rclpy.shutdown()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
