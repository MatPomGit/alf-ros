"""ROS2 node that hosts the ALF-ROS GUI application."""

from __future__ import annotations

import json
import logging
import sys
import threading
import time
from collections import deque
from typing import Any, Optional

try:
    import rclpy
    from rclpy.qos import QoSProfile
    from rclpy.node import Node
    from std_msgs.msg import String, Bool
    from sensor_msgs.msg import JointState, BatteryState
    from geometry_msgs.msg import Twist
    from rosidl_runtime_py.convert import message_to_ordereddict
    from rosidl_runtime_py.utilities import get_message
    from .qos_utils import build_qos_profile, log_network_settings, qos_profile_to_text

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
MAX_TOPIC_LOG_BUFFER_SIZE = 300
TOPIC_LOG_THROTTLE_SECONDS = 0.2
MAX_TOPIC_LOG_TEXT_LENGTH = 800
MAX_TOPIC_LOG_FLUSH_PER_TICK = 20

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

    def echo_topic(self, topic: str) -> None:
        """Start dynamic echo for a topic."""
        self._node.start_topic_echo(topic)

    def stop_echo_topic(self, topic: str) -> None:
        """Stop dynamic echo for a single topic."""
        self._node.stop_topic_echo(topic)

    def stop_all_echoes(self) -> None:
        """Stop dynamic echo for all topics."""
        self._node.stop_all_topic_echoes()

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
            self._dynamic_subscriptions: dict[str, Any] = {}
            self._topic_log_buffer: deque[tuple[str, str]] = deque(
                maxlen=MAX_TOPIC_LOG_BUFFER_SIZE
            )
            self._topic_last_log_time: dict[str, float] = {}
            self._qos_profile: Any = None

            self.declare_parameter("robot_namespace", "")
            self.declare_parameter("update_rate_hz", 10.0)
            self.declare_parameter("qos_preset", "sensor_data")
            self.declare_parameter("qos_reliability", "reliable")
            self.declare_parameter("qos_durability", "volatile")
            self.declare_parameter("qos_history", "keep_last")
            self.declare_parameter("qos_depth", 10)
            self.declare_parameter("ros_domain_id", 0)
            self.declare_parameter("localhost_only", False)
            self.declare_parameter("rmw_implementation", "")

            ns = self.get_parameter("robot_namespace").value
            prefix = f"/{ns}" if ns else ""
            qos_profile = build_qos_profile(
                preset=str(self.get_parameter("qos_preset").value),
                reliability=str(self.get_parameter("qos_reliability").value),
                durability=str(self.get_parameter("qos_durability").value),
                history=str(self.get_parameter("qos_history").value),
                depth=int(self.get_parameter("qos_depth").value),
            )
            ros_domain_id = int(self.get_parameter("ros_domain_id").value)
            localhost_only = bool(self.get_parameter("localhost_only").value)
            rmw_implementation = str(self.get_parameter("rmw_implementation").value)
            self._qos_profile = qos_profile

            self._cmd_vel_pub = self.create_publisher(
                Twist, f"{prefix}/cmd_vel", qos_profile
            )
            self._command_pub = self.create_publisher(
                String, f"{prefix}/alf_ros/command", qos_profile
            )
            self._estop_pub = self.create_publisher(
                Bool, f"{prefix}/alf_ros/emergency_stop", qos_profile
            )

            self._joint_state_sub = self.create_subscription(
                JointState, f"{prefix}/joint_states", self._on_joint_states, qos_profile
            )
            self._battery_sub = self.create_subscription(
                BatteryState,
                f"{prefix}/battery_state",
                self._on_battery,
                qos_profile,
            )
            self._status_sub = self.create_subscription(
                String, f"{prefix}/alf_ros/status", self._on_status, qos_profile
            )

            rate = float(self.get_parameter("update_rate_hz").value)
            timer_period = _compute_update_period(rate)
            self._update_timer = self.create_timer(timer_period, self._update_gui)

            self.get_logger().info(
                f"GUI node initialized with QoS: {qos_profile_to_text(qos_profile)}"
            )
            log_network_settings(
                self,
                ros_domain_id=ros_domain_id,
                localhost_only=localhost_only,
                rmw=rmw_implementation,
            )

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
            if not self._window:
                return
            for _ in range(MAX_TOPIC_LOG_FLUSH_PER_TICK):
                if not self._topic_log_buffer:
                    break
                topic, text = self._topic_log_buffer.popleft()
                self._window.log("DEBUG", f"[echo {topic}] {text}")

        def start_topic_echo(self, topic: str) -> None:
            """Create dynamic topic subscription and stream messages to GUI logs."""
            normalized_topic = topic.strip()
            if not normalized_topic:
                self.log_info("Echo topic cannot be empty.")
                return
            if normalized_topic in self._dynamic_subscriptions:
                self.log_info(f"Echo already active for: {normalized_topic}")
                return

            topic_types = dict(self.get_topic_names_and_types())
            if normalized_topic not in topic_types or not topic_types[normalized_topic]:
                self.log_info(f"Topic not found or without type: {normalized_topic}")
                return

            ros_type = topic_types[normalized_topic][0]
            try:
                msg_cls = get_message(ros_type)
            except (AttributeError, ModuleNotFoundError, ValueError) as exc:
                self.get_logger().error(
                    f"Cannot resolve message type '{ros_type}' for {normalized_topic}: {exc}"
                )
                return

            qos = QoSProfile(depth=10)
            subscription = self.create_subscription(
                msg_cls,
                normalized_topic,
                lambda msg, topic_name=normalized_topic: self._on_dynamic_topic_message(
                    topic_name, msg
                ),
                qos,
            )
            self._dynamic_subscriptions[normalized_topic] = subscription
            self.log_info(f"Echo started for {normalized_topic} [{ros_type}]")

        def stop_topic_echo(self, topic: str) -> None:
            """Stop dynamic subscription for a single topic."""
            normalized_topic = topic.strip()
            subscription = self._dynamic_subscriptions.pop(normalized_topic, None)
            if subscription is None:
                self.log_info(f"Echo was not active for: {normalized_topic}")
                return
            self.destroy_subscription(subscription)
            self._topic_last_log_time.pop(normalized_topic, None)
            self.log_info(f"Echo stopped for {normalized_topic}")

        def stop_all_topic_echoes(self) -> None:
            """Stop all dynamic subscriptions created by the GUI echo feature."""
            topics = list(self._dynamic_subscriptions.keys())
            for topic in topics:
                self.stop_topic_echo(topic)
            self.log_info("All dynamic topic echoes stopped.")

        def _on_dynamic_topic_message(self, topic: str, message: Any) -> None:
            """Buffer incoming topic messages with throttling."""
            now = time.monotonic()
            last_log_time = self._topic_last_log_time.get(topic, 0.0)
            if now - last_log_time < TOPIC_LOG_THROTTLE_SECONDS:
                return
            self._topic_last_log_time[topic] = now
            serialized = self._serialize_message_for_log(message)
            self._topic_log_buffer.append((topic, serialized))

        def _serialize_message_for_log(self, message: Any) -> str:
            """Serialize ROS message to compact human-readable text."""
            try:
                payload = message_to_ordereddict(message)
                text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
            except TypeError:
                text = str(message)
            if len(text) > MAX_TOPIC_LOG_TEXT_LENGTH:
                return f"{text[:MAX_TOPIC_LOG_TEXT_LENGTH]}… [truncated]"
            return text

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
                self._string_publishers[topic] = self.create_publisher(
                    String, topic, self._qos_profile
                )
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

        def destroy_node(self) -> bool:
            """Release dynamic subscriptions before node shutdown."""
            self.stop_all_topic_echoes()
            return super().destroy_node()


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
