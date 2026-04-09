"""Integration-style tests for GUI ROS bridge with mocked rclpy stack."""

from __future__ import annotations

import importlib
import json
import sys
import types
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest


@dataclass
class _PublishRecorder:
    messages: list[Any]

    def publish(self, msg: Any) -> None:
        self.messages.append(msg)


class _FakeLogger:
    def __init__(self) -> None:
        self.info_messages: list[str] = []
        self.error_messages: list[str] = []

    def info(self, message: str) -> None:
        self.info_messages.append(message)

    def error(self, message: str) -> None:
        self.error_messages.append(message)


def _install_gui_node_stubs() -> None:
    rclpy = types.ModuleType("rclpy")
    rclpy.node = types.ModuleType("rclpy.node")
    rclpy.qos = types.ModuleType("rclpy.qos")

    class FakeNode:
        pass

    class FakeQoSProfile:
        def __init__(self, depth: int) -> None:
            self.depth = depth

    rclpy.node.Node = FakeNode
    rclpy.qos.QoSProfile = FakeQoSProfile

    std_msgs = types.ModuleType("std_msgs")
    std_msgs.msg = types.ModuleType("std_msgs.msg")
    sensor_msgs = types.ModuleType("sensor_msgs")
    sensor_msgs.msg = types.ModuleType("sensor_msgs.msg")
    geometry_msgs = types.ModuleType("geometry_msgs")
    geometry_msgs.msg = types.ModuleType("geometry_msgs.msg")

    class StringMsg:
        def __init__(self) -> None:
            self.data = ""

    class BoolMsg:
        def __init__(self) -> None:
            self.data = False

    class JointStateMsg:
        def __init__(self) -> None:
            self.name: list[str] = []
            self.position: list[float] = []

    class BatteryStateMsg:
        def __init__(self) -> None:
            self.percentage = 0.0

    class TwistMsg:
        pass

    std_msgs.msg.String = StringMsg
    std_msgs.msg.Bool = BoolMsg
    sensor_msgs.msg.JointState = JointStateMsg
    sensor_msgs.msg.BatteryState = BatteryStateMsg
    geometry_msgs.msg.Twist = TwistMsg

    rosidl = types.ModuleType("rosidl_runtime_py")
    rosidl.convert = types.ModuleType("rosidl_runtime_py.convert")
    rosidl.utilities = types.ModuleType("rosidl_runtime_py.utilities")
    rosidl.set_message = types.ModuleType("rosidl_runtime_py.set_message")

    class GenericMsg:
        def __init__(self) -> None:
            self.data: Any = None
            self.flag = False

    def get_message(name: str) -> type[Any]:
        if name == "unknown_pkg/msg/Unknown":
            raise ValueError("unknown")
        return GenericMsg

    def message_to_ordereddict(message: Any) -> dict[str, Any]:
        return {"data": getattr(message, "data", None)}

    def set_message_fields(message: Any, values: dict[str, Any]) -> None:
        for key, value in values.items():
            setattr(message, key, value)

    rosidl.utilities.get_message = get_message
    rosidl.convert.message_to_ordereddict = message_to_ordereddict
    rosidl.set_message.set_message_fields = set_message_fields

    qos_utils = types.ModuleType("alf_ros.alf_ros.nodes.qos_utils")
    qos_utils.build_qos_profile = lambda **_: object()
    qos_utils.log_network_settings = lambda *_args, **_kwargs: None
    qos_utils.qos_profile_to_text = lambda _profile: "mocked"

    pyqt5 = types.ModuleType("PyQt5")
    pyqt5_widgets = types.ModuleType("PyQt5.QtWidgets")
    pyqt5_widgets.QApplication = object

    sys.modules["rclpy"] = rclpy
    sys.modules["rclpy.node"] = rclpy.node
    sys.modules["rclpy.qos"] = rclpy.qos
    sys.modules["std_msgs"] = std_msgs
    sys.modules["std_msgs.msg"] = std_msgs.msg
    sys.modules["sensor_msgs"] = sensor_msgs
    sys.modules["sensor_msgs.msg"] = sensor_msgs.msg
    sys.modules["geometry_msgs"] = geometry_msgs
    sys.modules["geometry_msgs.msg"] = geometry_msgs.msg
    sys.modules["rosidl_runtime_py"] = rosidl
    sys.modules["rosidl_runtime_py.convert"] = rosidl.convert
    sys.modules["rosidl_runtime_py.utilities"] = rosidl.utilities
    sys.modules["rosidl_runtime_py.set_message"] = rosidl.set_message
    sys.modules["alf_ros.alf_ros.nodes.qos_utils"] = qos_utils
    sys.modules["PyQt5"] = pyqt5
    sys.modules["PyQt5.QtWidgets"] = pyqt5_widgets


@pytest.fixture
def gui_node_module() -> Any:
    _install_gui_node_stubs()
    sys.modules.pop("alf_ros.alf_ros.nodes.gui_node", None)
    module = importlib.import_module("alf_ros.alf_ros.nodes.gui_node")
    return importlib.reload(module)


def _make_gui_node_stub() -> Any:
    logger = _FakeLogger()
    created_publishers: list[tuple[Any, str, Any]] = []
    created_subscriptions: list[tuple[Any, str, Any, Any]] = []
    destroyed_subscriptions: list[Any] = []
    stub = SimpleNamespace()
    stub._dynamic_subscriptions = {}
    stub._topic_last_log_time = {}
    stub._topic_log_buffer = []
    stub._qos_profile = object()
    stub._runtime_mode = "LIVE"
    stub._publisher_cache = {}
    stub._logger = logger
    stub._topics = {
        "/chatter": ["std_msgs/msg/String"],
        "/pose": ["geometry_msgs/msg/Pose"],
    }

    def get_topic_names_and_types() -> list[tuple[str, list[str]]]:
        return list(stub._topics.items())

    def create_subscription(
        msg_cls: Any,
        topic: str,
        callback: Any,
        qos: Any,
    ) -> object:
        created_subscriptions.append((msg_cls, topic, callback, qos))
        return object()

    def destroy_subscription(subscription: Any) -> None:
        destroyed_subscriptions.append(subscription)

    def create_publisher(msg_cls: Any, topic: str, qos: Any) -> _PublishRecorder:
        created_publishers.append((msg_cls, topic, qos))
        return _PublishRecorder(messages=[])

    def set_runtime_mode(mode: str) -> None:
        normalized_mode = mode.strip().upper()
        if normalized_mode in {"LIVE", "SIMULATED"}:
            stub._runtime_mode = normalized_mode
            logger.info(f"Runtime mode switched to {normalized_mode}")
        else:
            logger.error(f"Unknown runtime mode: {mode}")

    stub.get_logger = lambda: logger
    stub.log_info = logger.info
    stub.get_topic_names_and_types = get_topic_names_and_types
    stub.create_subscription = create_subscription
    stub.destroy_subscription = destroy_subscription
    stub.create_publisher = create_publisher
    stub.set_runtime_mode = set_runtime_mode
    stub.created_publishers = created_publishers
    stub.created_subscriptions = created_subscriptions
    stub.destroyed_subscriptions = destroyed_subscriptions
    return stub


class TestBridgeAndGuiIntegration:
    """Integration tests for bridge-node interactions using mocked ROS API."""

    def test_dynamic_subscription_created_and_destroyed(self, gui_node_module: Any) -> None:
        node = _make_gui_node_stub()
        gui_node_module.GUINode.start_topic_echo(node, "/chatter")

        assert "/chatter" in node._dynamic_subscriptions
        assert len(node.created_subscriptions) == 1

        gui_node_module.GUINode.stop_topic_echo(node, "/chatter")
        assert "/chatter" not in node._dynamic_subscriptions
        assert len(node.destroyed_subscriptions) == 1

    def test_publish_generic_valid_and_invalid_json(self, gui_node_module: Any) -> None:
        node = _make_gui_node_stub()

        gui_node_module.GUINode.publish_generic(node, "/chatter", json.dumps({"data": "ok"}))
        assert len(node.created_publishers) == 1
        cache_key = ("/chatter", "std_msgs/msg/String")
        assert cache_key in node._publisher_cache
        published = node._publisher_cache[cache_key].messages
        assert len(published) == 1
        assert getattr(published[0], "data") == "ok"

        gui_node_module.GUINode.publish_generic(node, "/chatter", "{broken json")
        assert any("Invalid JSON" in msg for msg in node._logger.error_messages)

    def test_publishers_are_cached_per_topic_and_type(self, gui_node_module: Any) -> None:
        node = _make_gui_node_stub()
        gui_node_module.GUINode.publish_generic(node, "/chatter", '{"data":"one"}')
        gui_node_module.GUINode.publish_generic(node, "/chatter", '{"data":"two"}')

        assert len(node.created_publishers) == 1
        cache_key = ("/chatter", "std_msgs/msg/String")
        assert len(node._publisher_cache[cache_key].messages) == 2

    def test_switch_runtime_mode_live_simulated(self, gui_node_module: Any) -> None:
        node = _make_gui_node_stub()
        bridge = gui_node_module.ROSBridge(node)

        bridge.set_runtime_mode("SIMULATED")
        assert node._runtime_mode == "SIMULATED"

        bridge.set_runtime_mode("LIVE")
        assert node._runtime_mode == "LIVE"

    def test_topic_removed_during_echo_is_ignored(self, gui_node_module: Any) -> None:
        node = _make_gui_node_stub()
        gui_node_module.GUINode.start_topic_echo(node, "/chatter")
        gui_node_module.GUINode.stop_topic_echo(node, "/chatter")

        gui_node_module.GUINode._on_dynamic_topic_message(node, "/chatter", {"data": "stale"})
        assert node._topic_log_buffer == []

    def test_unknown_message_type_and_qos_conflict(self, gui_node_module: Any) -> None:
        node = _make_gui_node_stub()
        node._topics["/mystery"] = ["unknown_pkg/msg/Unknown"]
        gui_node_module.GUINode.start_topic_echo(node, "/mystery")
        assert any("Cannot resolve message type" in msg for msg in node._logger.error_messages)

        conflict_node = _make_gui_node_stub()
        conflict_node.create_subscription = lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("incompatible QoS")
        )
        gui_node_module.GUINode.start_topic_echo(conflict_node, "/chatter")
        assert any(
            "QoS conflict" in msg or "qos conflict" in msg.lower()
            for msg in conflict_node._logger.error_messages
        )
