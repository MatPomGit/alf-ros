"""ROS2 node that monitors and logs system status to CLI."""

from __future__ import annotations

import logging
import sys
from typing import Optional

try:
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String, Bool
    from sensor_msgs.msg import JointState, BatteryState

    HAS_ROS = True
except ImportError:
    HAS_ROS = False
    Node = object  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)

BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
RESET = "\033[0m"

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

            print(f"{BOLD}{CYAN}=== ALF-ROS Status Monitor ==={RESET}")
            print(f"{GREEN}Monitor uruchomiony. Oczekiwanie na dane...{RESET}\n")
            self.get_logger().info("Status monitor node initialized")

        def _on_status(self, msg: String) -> None:
            mode = msg.data
            color = GREEN if mode != "EMERGENCY_STOP" else RED
            print(f"{color}[STATUS] Tryb robota: {BOLD}{mode}{RESET}")

        def _on_estop(self, msg: Bool) -> None:
            if msg.data:
                print(f"{RED}{BOLD}[!!!] STOP AWARYJNY AKTYWOWANY!{RESET}")
            else:
                print(f"{GREEN}[OK] Stop awaryjny wyłączony{RESET}")

        def _on_joint_states(self, msg: JointState) -> None:
            lines = [f"{CYAN}[STAWY]{RESET}"]
            for name, pos in zip(msg.name, msg.position):
                lines.append(f"  {name}: {pos:.4f} rad")
            print("\n".join(lines))

        def _on_battery(self, msg: BatteryState) -> None:
            pct = msg.percentage * 100.0
            color = RED if pct < 20.0 else (YELLOW if pct < 50.0 else GREEN)
            print(f"{color}[BATERIA] {pct:.1f}%{RESET}")


def main(args: Optional[list[str]] = None) -> None:
    """Entry point for the status monitor node."""
    if not HAS_ROS:
        print("ERROR: rclpy is not installed. Cannot start ROS2 node.")
        sys.exit(1)

    rclpy.init(args=args)
    node = StatusMonitorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Monitor zatrzymany.{RESET}")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
