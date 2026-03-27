"""ROS2 node that monitors and logs system status to CLI."""

from __future__ import annotations

import logging
import sys

try:
    import rclpy
    from rclpy.node import Node
    from sensor_msgs.msg import BatteryState, JointState
    from std_msgs.msg import Bool, String

    HAS_ROS = True
except ImportError:
    HAS_ROS = False
    Node = object  # type: ignore[assignment,misc]

from alf_ros.cli.feedback import colorize, print_banner, print_joint_states

logger = logging.getLogger(__name__)

if HAS_ROS:

    class StatusMonitorNode(Node):  # type: ignore[valid-type,misc]
        """Node that prints robot status feedback to the CLI.

        Subscribes to status topics and prints formatted, color-coded
        messages to stdout for terminal-based feedback.
        """

        def __init__(self) -> None:
            super().__init__("alf_ros_monitor")

            self.declare_parameter("robot_namespace", "")

            ns = self.get_parameter("robot_namespace").value
            prefix = f"/{ns}" if ns else ""

            self._status_sub = self.create_subscription(
                String, f"{prefix}/alf_ros/status", self._on_status, 10
            )
            self._estop_sub = self.create_subscription(
                Bool, f"{prefix}/alf_ros/emergency_stop", self._on_estop, 10
            )
            self._joint_sub = self.create_subscription(
                JointState, f"{prefix}/joint_states", self._on_joint_states, 10
            )
            self._battery_sub = self.create_subscription(
                BatteryState, f"{prefix}/battery_state", self._on_battery, 10
            )

            print_banner("ALF-ROS Status Monitor", "Unitree G1 EDU")
            print(colorize("Monitor uruchomiony. Oczekiwanie na dane...", "GREEN"), flush=True)
            self.get_logger().info("Status monitor node initialized")

        def _on_status(self, msg: String) -> None:
            mode = msg.data
            color = "GREEN" if mode != "EMERGENCY_STOP" else "RED"
            print(colorize(f"[STATUS] Tryb robota: {mode}", color, bold=True), flush=True)

        def _on_estop(self, msg: Bool) -> None:
            if msg.data:
                print(colorize("[!!!] STOP AWARYJNY AKTYWOWANY!", "RED", bold=True), flush=True)
            else:
                print(colorize("[OK] Stop awaryjny wyłączony", "GREEN"), flush=True)

        def _on_joint_states(self, msg: JointState) -> None:
            joint_states = dict(zip(msg.name, msg.position, strict=False))
            print_joint_states(joint_states)

        def _on_battery(self, msg: BatteryState) -> None:
            pct = msg.percentage * 100.0
            bat_color = "RED" if pct < 20.0 else ("YELLOW" if pct < 50.0 else "GREEN")
            print(colorize(f"[BATERIA] {pct:.1f}%", bat_color, bold=True), flush=True)


def main(args: list[str] | None = None) -> None:
    """Entry point for the status monitor node."""
    if not HAS_ROS:
        print("ERROR: rclpy is not installed. Cannot start ROS2 node.")
        sys.exit(1)

    rclpy.init(args=args)
    node = StatusMonitorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        print(f"\n{colorize('Monitor zatrzymany.', 'YELLOW')}")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
