"""Main GUI window for ALF-ROS - ROS2 communication interface."""

from __future__ import annotations

import logging
from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStatusBar,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)

LOG_LEVEL_COLORS = {
    "INFO": "#00CC00",
    "WARN": "#FFA500",
    "ERROR": "#FF4444",
    "DEBUG": "#AAAAAA",
}


class LogPanel(QTextEdit):
    """Scrollable log panel displaying timestamped messages."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumHeight(150)
        font = QFont("Monospace", 9)
        font.setStyleHint(QFont.TypeWriter)
        self.setFont(font)
        self.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")

    def append_message(self, level: str, message: str) -> None:
        """Append a colored log message to the panel.

        Args:
            level: Log level string (INFO, WARN, ERROR, DEBUG).
            message: The message text to display.
        """
        color = LOG_LEVEL_COLORS.get(level, "#d4d4d4")
        self.append(f'<span style="color:{color}">[{level}] {message}</span>')
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


class NodePanel(QWidget):
    """Panel displaying and managing ROS2 nodes."""

    refresh_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        header.addWidget(QLabel("<b>Aktywne węzły ROS2</b>"))
        self.btn_refresh = QPushButton("🔄 Odśwież")
        self.btn_refresh.clicked.connect(self.refresh_requested.emit)
        header.addStretch()
        header.addWidget(self.btn_refresh)
        layout.addLayout(header)

        self.node_list = QListWidget()
        self.node_list.setAlternatingRowColors(True)
        layout.addWidget(self.node_list)

        info_box = QGroupBox("Szczegóły węzła")
        info_layout = QVBoxLayout(info_box)
        self.node_info_label = QLabel("Wybierz węzeł z listy")
        self.node_info_label.setWordWrap(True)
        info_layout.addWidget(self.node_info_label)
        layout.addWidget(info_box)

        self.node_list.currentItemChanged.connect(self._on_node_selected)

    def update_nodes(self, nodes: list[str]) -> None:
        """Update the node list with current ROS2 nodes.

        Args:
            nodes: List of node name strings.
        """
        self.node_list.clear()
        for node_name in sorted(nodes):
            item = QListWidgetItem(node_name)
            item.setForeground(QColor("#00AA00"))
            self.node_list.addItem(item)

    def _on_node_selected(
        self,
        current: Optional[QListWidgetItem],
        _previous: Optional[QListWidgetItem],
    ) -> None:
        if current:
            self.node_info_label.setText(f"Węzeł: <b>{current.text()}</b>")


class TopicPanel(QWidget):
    """Panel for monitoring and publishing to ROS2 topics."""

    echo_requested = pyqtSignal(str)
    publish_requested = pyqtSignal(str, str)
    refresh_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        header.addWidget(QLabel("<b>Topiki ROS2</b>"))
        self.btn_refresh = QPushButton("🔄 Odśwież")
        self.btn_refresh.clicked.connect(self.refresh_requested.emit)
        header.addStretch()
        header.addWidget(self.btn_refresh)
        layout.addLayout(header)

        self.topic_list = QListWidget()
        self.topic_list.setAlternatingRowColors(True)
        layout.addWidget(self.topic_list)

        actions_box = QGroupBox("Operacje na topiku")
        actions_layout = QVBoxLayout(actions_box)

        echo_row = QHBoxLayout()
        echo_row.addWidget(QLabel("Topik:"))
        self.echo_input = QLineEdit()
        self.echo_input.setPlaceholderText("/topic_name")
        echo_row.addWidget(self.echo_input)
        self.btn_echo = QPushButton("👂 Echo")
        self.btn_echo.clicked.connect(self._on_echo)
        echo_row.addWidget(self.btn_echo)
        actions_layout.addLayout(echo_row)

        pub_row = QHBoxLayout()
        pub_row.addWidget(QLabel("Wiadomość:"))
        self.pub_input = QLineEdit()
        self.pub_input.setPlaceholderText('{"data": "hello"}')
        pub_row.addWidget(self.pub_input)
        self.btn_publish = QPushButton("📤 Publikuj")
        self.btn_publish.clicked.connect(self._on_publish)
        pub_row.addWidget(self.btn_publish)
        actions_layout.addLayout(pub_row)

        layout.addWidget(actions_box)

        self.topic_list.currentItemChanged.connect(self._on_topic_selected)

    def update_topics(self, topics: list[tuple[str, str]]) -> None:
        """Update the topic list.

        Args:
            topics: List of (topic_name, topic_type) tuples.
        """
        self.topic_list.clear()
        for name, msg_type in sorted(topics):
            item = QListWidgetItem(f"{name}  [{msg_type}]")
            item.setData(Qt.UserRole, name)
            item.setForeground(QColor("#0088CC"))
            self.topic_list.addItem(item)

    def _on_topic_selected(
        self,
        current: Optional[QListWidgetItem],
        _previous: Optional[QListWidgetItem],
    ) -> None:
        if current:
            topic = current.data(Qt.UserRole)
            self.echo_input.setText(topic)

    def _on_echo(self) -> None:
        topic = self.echo_input.text().strip()
        if topic:
            self.echo_requested.emit(topic)

    def _on_publish(self) -> None:
        topic = self.echo_input.text().strip()
        msg = self.pub_input.text().strip()
        if topic and msg:
            self.publish_requested.emit(topic, msg)


class ActionPanel(QWidget):
    """Panel for sending and monitoring ROS2 actions."""

    send_goal_requested = pyqtSignal(str, str)
    cancel_goal_requested = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._active_server: str = ""
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Akcje ROS2</b>"))

        goal_box = QGroupBox("Wyślij cel (Goal)")
        goal_layout = QVBoxLayout(goal_box)

        action_row = QHBoxLayout()
        action_row.addWidget(QLabel("Serwer akcji:"))
        self.action_server_input = QLineEdit()
        self.action_server_input.setPlaceholderText("/move_to_goal")
        action_row.addWidget(self.action_server_input)
        goal_layout.addLayout(action_row)

        goal_row = QHBoxLayout()
        goal_row.addWidget(QLabel("Parametry celu:"))
        self.goal_input = QLineEdit()
        self.goal_input.setPlaceholderText('{"x": 1.0, "y": 0.5, "theta": 0.0}')
        goal_row.addWidget(self.goal_input)
        goal_layout.addLayout(goal_row)

        btn_row = QHBoxLayout()
        self.btn_send_goal = QPushButton("🎯 Wyślij cel")
        self.btn_send_goal.setStyleSheet(
            "QPushButton { background-color: #005580; color: white; }"
        )
        self.btn_send_goal.clicked.connect(self._on_send_goal)
        self.btn_cancel_goal = QPushButton("❌ Anuluj")
        self.btn_cancel_goal.setStyleSheet(
            "QPushButton { background-color: #880000; color: white; }"
        )
        self.btn_cancel_goal.setEnabled(False)
        self.btn_cancel_goal.clicked.connect(self._on_cancel_goal)
        btn_row.addWidget(self.btn_send_goal)
        btn_row.addWidget(self.btn_cancel_goal)
        goal_layout.addLayout(btn_row)

        layout.addWidget(goal_box)

        feedback_box = QGroupBox("Feedback akcji")
        feedback_layout = QVBoxLayout(feedback_box)
        self.feedback_text = QTextEdit()
        self.feedback_text.setReadOnly(True)
        self.feedback_text.setMaximumHeight(200)
        feedback_layout.addWidget(self.feedback_text)
        layout.addWidget(feedback_box)

        self.status_label = QLabel("Status: Bezczynny")
        layout.addWidget(self.status_label)

    def _on_send_goal(self) -> None:
        server = self.action_server_input.text().strip()
        goal = self.goal_input.text().strip()
        if server and goal:
            self._active_server = server
            self.btn_send_goal.setEnabled(False)
            self.btn_cancel_goal.setEnabled(True)
            self.status_label.setText("Status: Wysyłanie celu...")
            self.send_goal_requested.emit(server, goal)

    def _on_cancel_goal(self) -> None:
        self.cancel_goal_requested.emit(self._active_server)
        self._active_server = ""
        self.btn_send_goal.setEnabled(True)
        self.btn_cancel_goal.setEnabled(False)
        self.status_label.setText("Status: Anulowano")

    def update_feedback(self, message: str) -> None:
        """Display action feedback.

        Args:
            message: Feedback message string.
        """
        self.feedback_text.append(message)

    def update_status(self, status: str) -> None:
        """Update the action status label.

        Args:
            status: Status string to display.
        """
        self.status_label.setText(f"Status: {status}")
        if status in ("Zakończono", "Anulowano", "Błąd"):
            self.btn_send_goal.setEnabled(True)
            self.btn_cancel_goal.setEnabled(False)


class RobotStatusPanel(QWidget):
    """Panel displaying Unitree G1 EDU robot status."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._joint_labels: dict[str, QLabel] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Status robota Unitree G1 EDU</b>"))

        conn_row = QHBoxLayout()
        conn_row.addWidget(QLabel("Połączenie:"))
        self.conn_status = QLabel("● Brak połączenia")
        self.conn_status.setStyleSheet("color: red; font-weight: bold;")
        conn_row.addStretch()
        conn_row.addWidget(self.conn_status)
        layout.addLayout(conn_row)

        battery_row = QHBoxLayout()
        battery_row.addWidget(QLabel("Bateria:"))
        self.battery_label = QLabel("-- %")
        self.battery_label.setStyleSheet("font-weight: bold;")
        battery_row.addStretch()
        battery_row.addWidget(self.battery_label)
        layout.addLayout(battery_row)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Tryb:"))
        self.mode_label = QLabel("--")
        mode_row.addStretch()
        mode_row.addWidget(self.mode_label)
        layout.addLayout(mode_row)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        layout.addWidget(separator)

        layout.addWidget(QLabel("<b>Stawy (pozycje w radianach):</b>"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        joint_widget = QWidget()
        self.joint_layout = QVBoxLayout(joint_widget)
        scroll.setWidget(joint_widget)
        layout.addWidget(scroll)

        control_box = QGroupBox("Sterowanie")
        control_layout = QHBoxLayout(control_box)
        self.btn_stand = QPushButton("🧍 Stój")
        self.btn_stand.setStyleSheet(
            "QPushButton { background-color: #006600; color: white; padding: 8px; }"
        )
        self.btn_lie = QPushButton("🛌 Leż")
        self.btn_lie.setStyleSheet(
            "QPushButton { background-color: #663300; color: white; padding: 8px; }"
        )
        self.btn_home = QPushButton("🏠 Pozycja domyślna")
        self.btn_home.setStyleSheet(
            "QPushButton { background-color: #004488; color: white; padding: 8px; }"
        )
        self.btn_estop = QPushButton("🛑 STOP AWARYJNY")
        self.btn_estop.setStyleSheet(
            "QPushButton { background-color: #CC0000; color: white; "
            "font-weight: bold; padding: 8px; }"
        )
        control_layout.addWidget(self.btn_stand)
        control_layout.addWidget(self.btn_lie)
        control_layout.addWidget(self.btn_home)
        control_layout.addWidget(self.btn_estop)
        layout.addWidget(control_box)

    def update_connection(self, connected: bool) -> None:
        """Update the connection status indicator.

        Args:
            connected: True if robot is connected.
        """
        if connected:
            self.conn_status.setText("● Połączono")
            self.conn_status.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.conn_status.setText("● Brak połączenia")
            self.conn_status.setStyleSheet("color: red; font-weight: bold;")

    def update_battery(self, percentage: float) -> None:
        """Update battery level display.

        Args:
            percentage: Battery percentage (0.0 - 100.0).
        """
        self.battery_label.setText(f"{percentage:.1f} %")
        if percentage < 20.0:
            self.battery_label.setStyleSheet("color: red; font-weight: bold;")
        elif percentage < 50.0:
            self.battery_label.setStyleSheet("color: orange; font-weight: bold;")
        else:
            self.battery_label.setStyleSheet("color: green; font-weight: bold;")

    def update_mode(self, mode: str) -> None:
        """Update the robot operation mode display.

        Args:
            mode: Mode string (e.g., 'IDLE', 'WALKING', 'STANDING').
        """
        self.mode_label.setText(mode)

    def update_joints(self, joint_states: dict[str, float]) -> None:
        """Update joint position displays.

        Args:
            joint_states: Dictionary mapping joint name to position in radians.
        """
        for name, position in joint_states.items():
            if name not in self._joint_labels:
                row = QHBoxLayout()
                name_lbl = QLabel(name)
                name_lbl.setMinimumWidth(150)
                val_lbl = QLabel()
                row.addWidget(name_lbl)
                row.addStretch()
                row.addWidget(val_lbl)
                self.joint_layout.addLayout(row)
                self._joint_labels[name] = val_lbl
            self._joint_labels[name].setText(f"{position:.4f} rad")


class MainWindow(QMainWindow):
    """Main application window for ALF-ROS GUI."""

    node_refresh_requested = pyqtSignal()
    topic_refresh_requested = pyqtSignal()

    def __init__(self, ros_bridge: object = None, parent: Optional[QWidget] = None) -> None:
        """Initialize the main window.

        Args:
            ros_bridge: Optional ROS2 bridge object for communication.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._ros_bridge = ros_bridge
        self.setWindowTitle("ALF-ROS — Interfejs komunikacji ROS2")
        self.setMinimumSize(1000, 700)
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        self.tabs = QTabWidget()
        self.node_panel = NodePanel()
        self.topic_panel = TopicPanel()
        self.action_panel = ActionPanel()
        self.robot_panel = RobotStatusPanel()

        self.tabs.addTab(self.robot_panel, "🤖 Status robota")
        self.tabs.addTab(self.node_panel, "🔵 Węzły")
        self.tabs.addTab(self.topic_panel, "📡 Topiki")
        self.tabs.addTab(self.action_panel, "🎯 Akcje")

        main_layout.addWidget(self.tabs)

        log_group = QGroupBox("Dziennik zdarzeń")
        log_layout = QVBoxLayout(log_group)
        self.log_panel = LogPanel()
        log_layout.addWidget(self.log_panel)
        log_btn_row = QHBoxLayout()
        btn_clear_log = QPushButton("🗑 Wyczyść dziennik")
        btn_clear_log.clicked.connect(self.log_panel.clear)
        log_btn_row.addStretch()
        log_btn_row.addWidget(btn_clear_log)
        log_layout.addLayout(log_btn_row)
        main_layout.addWidget(log_group)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Gotowy — oczekiwanie na połączenie z ROS2...")

    def _connect_signals(self) -> None:
        self.node_panel.refresh_requested.connect(self._on_refresh_nodes)
        self.topic_panel.refresh_requested.connect(self._on_refresh_topics)
        self.topic_panel.echo_requested.connect(self._on_echo_topic)
        self.topic_panel.publish_requested.connect(self._on_publish_topic)
        self.action_panel.send_goal_requested.connect(self._on_send_action_goal)
        self.action_panel.cancel_goal_requested.connect(self._on_cancel_action_goal)
        self.robot_panel.btn_stand.clicked.connect(lambda: self._on_robot_command("stand"))
        self.robot_panel.btn_lie.clicked.connect(lambda: self._on_robot_command("lie_down"))
        self.robot_panel.btn_home.clicked.connect(
            lambda: self._on_robot_command("home_position")
        )
        self.robot_panel.btn_estop.clicked.connect(self._on_estop)

    def log(self, level: str, message: str) -> None:
        """Add a message to the log panel.

        Args:
            level: Log level string (INFO, WARN, ERROR, DEBUG).
            message: Message to display.
        """
        self.log_panel.append_message(level, message)
        logger.info("[%s] %s", level, message)

    def _on_refresh_nodes(self) -> None:
        self.log("INFO", "Odświeżanie listy węzłów...")
        if self._ros_bridge:
            nodes = self._ros_bridge.get_node_names()
            self.node_panel.update_nodes(nodes)
        self.node_refresh_requested.emit()

    def _on_refresh_topics(self) -> None:
        self.log("INFO", "Odświeżanie listy topików...")
        if self._ros_bridge:
            topics = self._ros_bridge.get_topic_names_and_types()
            self.topic_panel.update_topics(topics)
        self.topic_refresh_requested.emit()

    def _on_echo_topic(self, topic: str) -> None:
        self.log("INFO", f"Nasłuchiwanie topiku: {topic}")
        if self._ros_bridge:
            self._ros_bridge.echo_topic(topic)

    def _on_publish_topic(self, topic: str, message: str) -> None:
        self.log("INFO", f"Publikowanie na topik {topic}: {message}")
        if self._ros_bridge:
            self._ros_bridge.publish_to_topic(topic, message)

    def _on_send_action_goal(self, server: str, goal: str) -> None:
        self.log("INFO", f"Wysyłanie celu do serwera akcji {server}: {goal}")
        if self._ros_bridge:
            self._ros_bridge.send_action_goal(server, goal)

    def _on_cancel_action_goal(self, server: str) -> None:
        self.log("WARN", f"Anulowanie celu dla serwera akcji: {server}")
        if self._ros_bridge:
            self._ros_bridge.cancel_action_goal(server)

    def _on_robot_command(self, command: str) -> None:
        self.log("INFO", f"Wysyłanie komendy do robota: {command}")
        if self._ros_bridge:
            self._ros_bridge.send_robot_command(command)

    def _on_estop(self) -> None:
        reply = QMessageBox.warning(
            self,
            "Stop awaryjny",
            "Czy na pewno chcesz zatrzymać robota awaryjnie?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.log("ERROR", "STOP AWARYJNY AKTYWOWANY!")
            self.status_bar.showMessage("⚠️ STOP AWARYJNY!")
            if self._ros_bridge:
                self._ros_bridge.emergency_stop()
