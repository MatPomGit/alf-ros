"""Unit tests for ALF-ROS GUI panel classes (no running Qt/ROS2 required)."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Minimal Qt stubs so tests run without a display or PyQt5 installed
# ---------------------------------------------------------------------------

_QT_AVAILABLE = False
try:
    from PyQt5.QtWidgets import QApplication

    if not QApplication.instance():
        _app = QApplication(sys.argv)
    _QT_AVAILABLE = True
except (ImportError, RuntimeError):
    pass


def _make_qt_stubs() -> None:
    """Inject minimal stubs for PyQt5 symbols used by main_window."""
    qt_stub = MagicMock()
    qt_core = MagicMock()
    qt_gui = MagicMock()
    qt_widgets = MagicMock()

    for mod_name, stub in [
        ("PyQt5", qt_stub),
        ("PyQt5.QtCore", qt_core),
        ("PyQt5.QtGui", qt_gui),
        ("PyQt5.QtWidgets", qt_widgets),
    ]:
        if mod_name not in sys.modules:
            sys.modules[mod_name] = stub


if not _QT_AVAILABLE:
    _make_qt_stubs()


# ---------------------------------------------------------------------------
# Tests that work with real PyQt5 (skipped if unavailable)
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.skipif(
    not _QT_AVAILABLE,
    reason="PyQt5 not installed or no display available",
)


@pytest.fixture(scope="module")
def qt_app():
    """Ensure a QApplication exists for all tests in this module."""
    from PyQt5.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    return app


@pytest.fixture
def log_panel(qt_app):
    """Create a fresh LogPanel instance."""
    from alf_ros.alf_ros.gui.main_window import LogPanel

    return LogPanel()


@pytest.fixture
def node_panel(qt_app):
    """Create a fresh NodePanel instance."""
    from alf_ros.alf_ros.gui.main_window import NodePanel

    return NodePanel()


@pytest.fixture
def topic_panel(qt_app):
    """Create a fresh TopicPanel instance."""
    from alf_ros.alf_ros.gui.main_window import TopicPanel

    return TopicPanel()


@pytest.fixture
def action_panel(qt_app):
    """Create a fresh ActionPanel instance."""
    from alf_ros.alf_ros.gui.main_window import ActionPanel

    return ActionPanel()


@pytest.fixture
def robot_panel(qt_app):
    """Create a fresh RobotStatusPanel instance."""
    from alf_ros.alf_ros.gui.main_window import RobotStatusPanel

    return RobotStatusPanel()


@pytest.fixture
def graph_panel(qt_app):
    """Create a fresh GraphPanel instance."""
    from alf_ros.alf_ros.gui.main_window import GraphPanel

    return GraphPanel()


@pytest.fixture
def main_window(qt_app):
    """Create a MainWindow without a ROS bridge."""
    from alf_ros.alf_ros.gui.main_window import MainWindow

    return MainWindow(ros_bridge=None)


# ---------------------------------------------------------------------------
# LogPanel tests
# ---------------------------------------------------------------------------


class TestLogPanel:
    """Tests for the LogPanel widget."""

    def test_initial_state_is_empty(self, log_panel) -> None:
        assert log_panel.toPlainText() == ""

    def test_append_message_adds_text(self, log_panel) -> None:
        log_panel.append_message("INFO", "test log message")
        assert "test log message" in log_panel.toHtml()

    def test_append_message_includes_level_tag(self, log_panel) -> None:
        log_panel.append_message("WARN", "warning text")
        assert "WARN" in log_panel.toHtml()

    @pytest.mark.parametrize("level", ["INFO", "WARN", "ERROR", "DEBUG"])
    def test_all_levels_accepted(self, log_panel, level: str) -> None:
        log_panel.append_message(level, f"message for {level}")
        assert f"message for {level}" in log_panel.toHtml()

    def test_clear_removes_content(self, log_panel) -> None:
        log_panel.append_message("INFO", "some content")
        log_panel.clear()
        assert log_panel.toPlainText() == ""


# ---------------------------------------------------------------------------
# NodePanel tests
# ---------------------------------------------------------------------------


class TestNodePanel:
    """Tests for the NodePanel widget."""

    def test_initial_list_is_empty(self, node_panel) -> None:
        assert node_panel.node_list.count() == 0

    def test_update_nodes_populates_list(self, node_panel) -> None:
        node_panel.update_nodes(["/node_a", "/node_b", "/node_c"])
        assert node_panel.node_list.count() == 3

    def test_update_nodes_sorts_alphabetically(self, node_panel) -> None:
        node_panel.update_nodes(["/z_node", "/a_node", "/m_node"])
        assert node_panel.node_list.item(0).text() == "/a_node"
        assert node_panel.node_list.item(2).text() == "/z_node"

    def test_update_nodes_clears_previous(self, node_panel) -> None:
        node_panel.update_nodes(["/first"])
        node_panel.update_nodes(["/second", "/third"])
        assert node_panel.node_list.count() == 2

    def test_refresh_signal_emitted(self, node_panel) -> None:
        received: list[None] = []
        node_panel.refresh_requested.connect(lambda: received.append(None))
        node_panel.btn_refresh.click()
        assert len(received) == 1


# ---------------------------------------------------------------------------
# TopicPanel tests
# ---------------------------------------------------------------------------


class TestTopicPanel:
    """Tests for the TopicPanel widget."""

    def test_initial_topic_list_empty(self, topic_panel) -> None:
        assert topic_panel.topic_list.count() == 0

    def test_update_topics_populates_list(self, topic_panel) -> None:
        topics = [("/cmd_vel", "geometry_msgs/Twist"), ("/joint_states", "sensor_msgs/JointState")]
        topic_panel.update_topics(topics)
        assert topic_panel.topic_list.count() == 2

    def test_update_topics_sorts_alphabetically(self, topic_panel) -> None:
        topics = [("/z_topic", "std_msgs/String"), ("/a_topic", "std_msgs/String")]
        topic_panel.update_topics(topics)
        first_item_text = topic_panel.topic_list.item(0).text()
        assert "/a_topic" in first_item_text

    def test_echo_signal_emitted_with_topic_name(self, topic_panel) -> None:
        received: list[str] = []
        topic_panel.echo_requested.connect(received.append)
        topic_panel.echo_input.setText("/test_topic")
        topic_panel.btn_echo.click()
        assert received == ["/test_topic"]

    def test_echo_not_emitted_for_empty_input(self, topic_panel) -> None:
        received: list[str] = []
        topic_panel.echo_requested.connect(received.append)
        topic_panel.echo_input.clear()
        topic_panel.btn_echo.click()
        assert received == []

    def test_publish_signal_emitted(self, topic_panel) -> None:
        received: list[tuple[str, str]] = []
        topic_panel.publish_requested.connect(lambda t, m: received.append((t, m)))
        topic_panel.echo_input.setText("/my_topic")
        topic_panel.pub_input.setText('{"data": 42}')
        topic_panel.btn_publish.click()
        assert received == [("/my_topic", '{"data": 42}')]


# ---------------------------------------------------------------------------
# ActionPanel tests
# ---------------------------------------------------------------------------


class TestActionPanel:
    """Tests for the ActionPanel widget."""

    def test_cancel_button_initially_disabled(self, action_panel) -> None:
        assert not action_panel.btn_cancel_goal.isEnabled()

    def test_send_goal_enables_cancel(self, action_panel) -> None:
        action_panel.action_server_input.setText("/move_to_goal")
        action_panel.goal_input.setText('{"x": 1.0}')
        action_panel.btn_send_goal.click()
        assert action_panel.btn_cancel_goal.isEnabled()

    def test_send_goal_signal_emitted(self, action_panel) -> None:
        received: list[tuple[str, str]] = []
        action_panel.send_goal_requested.connect(lambda s, g: received.append((s, g)))
        action_panel.action_server_input.setText("/navigate")
        action_panel.goal_input.setText('{"x": 2.0}')
        action_panel.btn_send_goal.click()
        assert received == [("/navigate", '{"x": 2.0}')]

    def test_cancel_signal_emitted(self, action_panel) -> None:
        received: list[str] = []
        action_panel.cancel_goal_requested.connect(received.append)
        action_panel.action_server_input.setText("/navigate")
        action_panel.goal_input.setText('{"x": 1.0}')
        action_panel.btn_send_goal.click()
        action_panel.btn_cancel_goal.click()
        assert "/navigate" in received

    def test_update_feedback_appends_text(self, action_panel) -> None:
        action_panel.update_feedback("Progress: 50%")
        assert "Progress: 50%" in action_panel.feedback_text.toPlainText()

    def test_update_status_terminal_states_re_enable_send(self, action_panel) -> None:
        action_panel.action_server_input.setText("/s")
        action_panel.goal_input.setText("{}")
        action_panel.btn_send_goal.click()
        assert not action_panel.btn_send_goal.isEnabled()
        action_panel.update_status("Zakończono")
        assert action_panel.btn_send_goal.isEnabled()


# ---------------------------------------------------------------------------
# RobotStatusPanel tests
# ---------------------------------------------------------------------------


class TestRobotStatusPanel:
    """Tests for the RobotStatusPanel widget."""

    def test_initial_connection_shows_disconnected(self, robot_panel) -> None:
        assert "Brak połączenia" in robot_panel.conn_status.text()

    def test_update_connection_true(self, robot_panel) -> None:
        robot_panel.update_connection(True)
        assert "Połączono" in robot_panel.conn_status.text()

    def test_update_connection_false(self, robot_panel) -> None:
        robot_panel.update_connection(True)
        robot_panel.update_connection(False)
        assert "Brak połączenia" in robot_panel.conn_status.text()

    def test_update_battery_displays_percentage(self, robot_panel) -> None:
        robot_panel.update_battery(75.5)
        assert "75.5" in robot_panel.battery_label.text()

    @pytest.mark.parametrize(
        "pct,expected_style_fragment",
        [
            (10.0, "red"),
            (30.0, "orange"),
            (80.0, "green"),
        ],
    )
    def test_battery_color_by_level(
        self, robot_panel, pct: float, expected_style_fragment: str
    ) -> None:
        robot_panel.update_battery(pct)
        assert expected_style_fragment in robot_panel.battery_label.styleSheet()

    def test_update_mode_changes_label(self, robot_panel) -> None:
        robot_panel.update_mode("WALKING")
        assert robot_panel.mode_label.text() == "WALKING"

    def test_update_joints_creates_labels(self, robot_panel) -> None:
        joints = {"left_knee_joint": 0.5, "right_knee_joint": -0.3}
        robot_panel.update_joints(joints)
        assert "left_knee_joint" in robot_panel._joint_labels
        assert "right_knee_joint" in robot_panel._joint_labels

    def test_update_joints_updates_existing_labels(self, robot_panel) -> None:
        robot_panel.update_joints({"left_knee_joint": 0.0})
        robot_panel.update_joints({"left_knee_joint": 1.2345})
        label = robot_panel._joint_labels["left_knee_joint"]
        assert "1.2345" in label.text()


# ---------------------------------------------------------------------------
# GraphPanel tests
# ---------------------------------------------------------------------------


class TestGraphPanel:
    """Tests for the GraphPanel widget."""

    def test_initial_graph_list_empty(self, graph_panel) -> None:
        assert graph_panel.graph_list.count() == 0

    def test_update_graph_populates_rows(self, graph_panel) -> None:
        graph_panel.update_graph([("/cmd_vel", "geometry_msgs/msg/Twist", 1, 2)])
        assert graph_panel.graph_list.count() == 1

    def test_namespace_filter_limits_rows(self, graph_panel) -> None:
        graph_panel.update_graph(
            [
                ("/robot/cmd_vel", "geometry_msgs/msg/Twist", 1, 1),
                ("/diagnostics", "std_msgs/msg/String", 1, 0),
            ]
        )
        graph_panel.namespace_filter.setText("/robot")
        assert graph_panel.graph_list.count() == 1

    def test_message_type_filter_limits_rows(self, graph_panel) -> None:
        graph_panel.update_graph(
            [
                ("/robot/cmd_vel", "geometry_msgs/msg/Twist", 1, 1),
                ("/diagnostics", "std_msgs/msg/String", 1, 0),
            ]
        )
        graph_panel.message_type_filter.setText("std_msgs")
        assert graph_panel.graph_list.count() == 1

    def test_pause_toggle_emits_signal(self, graph_panel) -> None:
        states: list[bool] = []
        graph_panel.refresh_paused_changed.connect(states.append)
        graph_panel.btn_pause.click()
        graph_panel.btn_pause.click()
        assert states == [True, False]


# ---------------------------------------------------------------------------
# MainWindow integration tests
# ---------------------------------------------------------------------------


class TestMainWindow:
    """Smoke tests for the MainWindow."""

    def test_window_title_contains_alf_ros(self, main_window) -> None:
        assert "ALF-ROS" in main_window.windowTitle()

    def test_four_tabs_present(self, main_window) -> None:
        assert main_window.tabs.count() == 5

    def test_log_method_adds_to_panel(self, main_window) -> None:
        main_window.log("INFO", "integration test message")
        assert "integration test message" in main_window.log_panel.toHtml()

    def test_status_bar_initial_message(self, main_window) -> None:
        assert main_window.status_bar.currentMessage() != ""

    def test_robot_panel_accessible(self, main_window) -> None:
        assert main_window.robot_panel is not None

    def test_node_panel_accessible(self, main_window) -> None:
        assert main_window.node_panel is not None
