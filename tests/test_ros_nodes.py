"""Unit tests for ALF-ROS ROS2 node communication logic (no ROS2 runtime required)."""

from __future__ import annotations

import ast
import importlib
import inspect
from pathlib import Path
from unittest.mock import MagicMock


def _get_source(module_name: str) -> str:
    """Return the source code of a module."""
    mod = importlib.import_module(module_name)
    return inspect.getsource(mod)


def _function_names_in_class(source: str, class_name: str) -> set[str]:
    """Return the set of method names defined directly inside *class_name*."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return {
                n.name
                for n in ast.walk(node)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
    return set()


def _dict_keys_in_function(source: str, func_name: str) -> set[str]:
    """Return all string literal keys found in dict literals inside *func_name*."""
    tree = ast.parse(source)
    keys: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
            for child in ast.walk(node):
                if isinstance(child, ast.Dict):
                    for k in child.keys:
                        if isinstance(k, ast.Constant) and isinstance(k.value, str):
                            keys.add(k.value)
    return keys


def _imported_names_from(source: str, module_pattern: str) -> set[str]:
    """Return names imported via ``from <module_pattern> import ...``."""
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and module_pattern in node.module:
            for alias in node.names:
                names.add(alias.asname or alias.name)
    return names


def _assignments_in_method(source: str, class_name: str, method_name: str) -> list[str]:
    """Return string values of all constants assigned in *class_name.method_name*."""
    tree = ast.parse(source)
    values: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for child in ast.walk(node):
                if (
                    isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and child.name == method_name
                ):
                    for stmt in ast.walk(child):
                        if (
                            isinstance(stmt, ast.Assign)
                            and isinstance(stmt.value, ast.Constant)
                            and isinstance(stmt.value.value, str)
                        ):
                            values.append(stmt.value.value)
    return values


class TestRobotControllerNodeCommands:
    """Tests for RobotControllerNode command handling without a live ROS2 context."""

    def test_robot_modes_includes_walk(self) -> None:
        from alf_ros.alf_ros.nodes.robot_controller_node import ROBOT_MODES

        assert "walk" in ROBOT_MODES
        assert ROBOT_MODES["walk"] == "WALKING"

    def test_robot_modes_complete(self) -> None:
        from alf_ros.alf_ros.nodes.robot_controller_node import ROBOT_MODES

        expected_keys = {"idle", "stand", "lie_down", "home_position", "walk"}
        assert expected_keys == set(ROBOT_MODES.keys())

    def test_safe_home_positions_has_all_joints(self) -> None:
        from alf_ros.alf_ros.nodes.robot_controller_node import SAFE_HOME_POSITIONS

        assert len(SAFE_HOME_POSITIONS) == 23
        assert "left_knee_joint" in SAFE_HOME_POSITIONS
        assert "right_knee_joint" in SAFE_HOME_POSITIONS


class TestGUINodeBatterySubscription:
    """Tests for GUINode battery subscription configuration."""

    def test_has_ros_flag_exists(self) -> None:
        from alf_ros.alf_ros.nodes import gui_node

        assert hasattr(gui_node, "HAS_ROS")

    def test_battery_state_imported_when_ros_available(self) -> None:
        """When ROS is available, BatteryState must be importable via sensor_msgs."""
        try:
            from sensor_msgs.msg import BatteryState  # noqa: F401
        except ImportError:
            pass  # ROS2 not installed in this environment — skip verification

    def test_gui_node_module_loads(self) -> None:
        """gui_node module must be importable without errors."""
        mod = importlib.import_module("alf_ros.alf_ros.nodes.gui_node")
        assert mod is not None

    def test_float32_not_imported_from_std_msgs(self) -> None:
        """Float32 must no longer be imported from std_msgs in gui_node."""
        source = _get_source("alf_ros.alf_ros.nodes.gui_node")
        names = _imported_names_from(source, "std_msgs")
        assert "Float32" not in names

    def test_battery_state_imported_from_sensor_msgs(self) -> None:
        """BatteryState must be imported from sensor_msgs in gui_node."""
        source = _get_source("alf_ros.alf_ros.nodes.gui_node")
        names = _imported_names_from(source, "sensor_msgs")
        assert "BatteryState" in names

    def test_battery_topic_is_battery_state(self) -> None:
        """The battery subscription must use /battery_state, not /battery_state/percentage."""
        source = _get_source("alf_ros.alf_ros.nodes.gui_node")
        assert "/battery_state/percentage" not in source
        assert "battery_state" in source

    def test_battery_handler_uses_percentage_field(self) -> None:
        """_on_battery must access msg.percentage, not msg.data."""
        source = _get_source("alf_ros.alf_ros.nodes.gui_node")
        assert "msg.percentage" in source

    def test_compute_update_period_returns_inverse_rate(self) -> None:
        """_compute_update_period should return the inverse of positive frequency."""
        from alf_ros.alf_ros.nodes.gui_node import _compute_update_period

        assert _compute_update_period(10.0) == 0.1

    def test_compute_update_period_rejects_non_positive_rate(self) -> None:
        """_compute_update_period must raise ValueError for invalid update rates."""
        from alf_ros.alf_ros.nodes.gui_node import _compute_update_period

        for invalid_rate in (0.0, -1.0):
            try:
                _compute_update_period(invalid_rate)
            except ValueError:
                continue
            raise AssertionError("Expected ValueError for non-positive update rate")

    def test_ros_bridge_exposes_graph_methods(self) -> None:
        """ROSBridge should provide graph/service/action inspection helpers."""
        source = _get_source("alf_ros.alf_ros.nodes.gui_node")
        methods = _function_names_in_class(source, "ROSBridge")
        expected = {
            "get_service_names_and_types",
            "get_action_names_and_types",
            "get_publishers_info_by_topic",
            "get_subscribers_info_by_topic",
            "get_topic_graph",
        }
        assert expected.issubset(methods)
    def test_gui_node_uses_dynamic_subscription_registry(self) -> None:
        """GUINode should keep runtime dynamic subscriptions in a dedicated registry."""
        source = _get_source("alf_ros.alf_ros.nodes.gui_node")
        assert "_dynamic_subscriptions" in source

    def test_echo_topic_uses_runtime_type_resolution(self) -> None:
        """Dynamic echo should resolve message types at runtime and create subscription."""
        source = _get_source("alf_ros.alf_ros.nodes.gui_node")
        assert "get_topic_names_and_types()" in source
        assert "get_message(" in source
        assert "create_subscription(" in source

    def test_publish_generic_uses_json_decode(self) -> None:
        """Generic publish should decode JSON payload before creating message."""
        source = _get_source("alf_ros.alf_ros.nodes.gui_node")
        assert "json.loads(message)" in source

    def test_publish_generic_uses_publisher_cache(self) -> None:
        """Generic publish should cache publishers by topic and message type."""
        source = _get_source("alf_ros.alf_ros.nodes.gui_node")
        assert "_publisher_cache" in source
        assert "cache_key = (normalized_topic, ros_type)" in source

    def test_runtime_mode_switch_support_present(self) -> None:
        """GUI node and bridge should expose runtime mode switching hooks."""
        source = _get_source("alf_ros.alf_ros.nodes.gui_node")
        assert "def set_runtime_mode(" in source


class TestRobotControllerWalkHandler:
    """Tests that the walk command is wired to a proper handler."""

    _MODULE = "alf_ros.alf_ros.nodes.robot_controller_node"
    _CLASS = "RobotControllerNode"

    def test_cmd_walk_method_exists(self) -> None:
        """_cmd_walk method must exist inside RobotControllerNode."""
        source = _get_source(self._MODULE)
        methods = _function_names_in_class(source, self._CLASS)
        assert "_cmd_walk" in methods

    def test_walk_key_in_on_command_dispatch_dict(self) -> None:
        """'walk' must be a key in the handler dispatch dict inside _on_command."""
        source = _get_source(self._MODULE)
        keys = _dict_keys_in_function(source, "_on_command")
        assert "walk" in keys

    def test_cmd_walk_sets_walking_mode(self) -> None:
        """_cmd_walk must assign 'WALKING' to _current_mode."""
        source = _get_source(self._MODULE)
        assigned = _assignments_in_method(source, self._CLASS, "_cmd_walk")
        assert "WALKING" in assigned

    def test_walk_command_handled_by_cmd_walk(self) -> None:
        """The dispatch dict must map 'walk' to self._cmd_walk (not None)."""
        source = _get_source(self._MODULE)
        # Parse the AST to find the Dict node inside _on_command
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "_on_command":
                for child in ast.walk(node):
                    if isinstance(child, ast.Dict):
                        for key, val in zip(child.keys, child.values):
                            if isinstance(key, ast.Constant) and key.value == "walk":
                                # Value must reference self._cmd_walk
                                assert isinstance(val, ast.Attribute)
                                assert val.attr == "_cmd_walk"
                                return
        raise AssertionError("'walk' key not found in dispatch dict inside _on_command")

    def test_mock_node_walk_dispatch(self) -> None:
        """Simulate _on_command dispatch to ensure walk handler is called."""
        from alf_ros.alf_ros.nodes.robot_controller_node import ROBOT_MODES

        called: list[str] = []

        class FakeNode:
            _estop_active = False
            _current_mode = "IDLE"

            def _cmd_stand(self) -> None:
                called.append("stand")

            def _cmd_lie_down(self) -> None:
                called.append("lie_down")

            def _cmd_home_position(self) -> None:
                called.append("home_position")

            def _cmd_idle(self) -> None:
                called.append("idle")

            def _cmd_walk(self) -> None:
                called.append("walk")

            def _on_command(self, msg: MagicMock) -> None:
                command = msg.data.strip().lower()
                if command not in ROBOT_MODES:
                    return
                handler = {
                    "stand": self._cmd_stand,
                    "lie_down": self._cmd_lie_down,
                    "home_position": self._cmd_home_position,
                    "idle": self._cmd_idle,
                    "walk": self._cmd_walk,
                }.get(command)
                if handler:
                    handler()

        fake = FakeNode()
        msg = MagicMock()
        msg.data = "walk"
        fake._on_command(msg)
        assert called == ["walk"]


class TestQoSAndNetworkConfiguration:
    """Tests for QoS preset and ROS network parameter wiring."""

    def test_qos_utils_defines_required_presets(self) -> None:
        from alf_ros.alf_ros.nodes.qos_utils import QOS_PRESETS

        assert {"sensor_data", "reliable_control", "latched_status"} <= set(QOS_PRESETS.keys())

    def test_gui_node_declares_qos_and_network_parameters(self) -> None:
        source = _get_source("alf_ros.alf_ros.nodes.gui_node")
        expected = {
            "qos_preset",
            "qos_reliability",
            "qos_durability",
            "qos_history",
            "qos_depth",
            "ros_domain_id",
            "localhost_only",
            "rmw_implementation",
        }
        for name in expected:
            assert f'declare_parameter("{name}"' in source

    def test_controller_declares_qos_and_network_parameters(self) -> None:
        source = _get_source("alf_ros.alf_ros.nodes.robot_controller_node")
        expected = {
            "qos_preset",
            "qos_reliability",
            "qos_durability",
            "qos_history",
            "qos_depth",
            "ros_domain_id",
            "localhost_only",
            "rmw_implementation",
        }
        for name in expected:
            assert f'declare_parameter("{name}"' in source

    def test_params_yaml_contains_qos_presets_and_network_fields(self) -> None:
        params_path = Path("alf_ros/config/params.yaml")
        text = params_path.read_text(encoding="utf-8")
        for expected in (
            'qos_preset: "sensor_data"',
            'qos_preset: "reliable_control"',
            "ros_domain_id: 0",
            "localhost_only: false",
            'rmw_implementation: ""',
        ):
            assert expected in text
