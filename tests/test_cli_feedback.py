"""Unit tests for ALF-ROS CLI feedback utilities."""

from __future__ import annotations

import io
import sys
from unittest.mock import patch

import pytest

from alf_ros.alf_ros.cli.feedback import (
    FeedbackLevel,
    colorize,
    print_banner,
    print_feedback,
    print_joint_states,
    print_robot_status,
)


class TestColorize:
    """Tests for the colorize helper function."""

    def test_returns_plain_text_when_no_tty(self) -> None:
        with patch("alf_ros.alf_ros.cli.feedback._USE_COLOR", False):
            result = colorize("hello", "GREEN", bold=True)
        assert result == "hello"

    def test_returns_colored_text_when_tty(self) -> None:
        with patch("alf_ros.alf_ros.cli.feedback._USE_COLOR", True):
            result = colorize("hello", "GREEN")
        assert "hello" in result
        assert "\033[" in result

    def test_bold_flag_adds_bold_code(self) -> None:
        with patch("alf_ros.alf_ros.cli.feedback._USE_COLOR", True):
            result = colorize("bold text", "RED", bold=True)
        assert "\033[1m" in result

    def test_unknown_color_falls_back_gracefully(self) -> None:
        with patch("alf_ros.alf_ros.cli.feedback._USE_COLOR", True):
            result = colorize("text", "NONEXISTENT_COLOR")
        assert "text" in result


class TestPrintFeedback:
    """Tests for print_feedback function."""

    @pytest.mark.parametrize(
        "level",
        [
            FeedbackLevel.DEBUG,
            FeedbackLevel.INFO,
            FeedbackLevel.WARN,
            FeedbackLevel.ERROR,
            FeedbackLevel.CRITICAL,
        ],
    )
    def test_prints_level_tag(self, level: FeedbackLevel, capsys: pytest.CaptureFixture) -> None:
        with patch("alf_ros.alf_ros.cli.feedback._USE_COLOR", False):
            print_feedback(level, "test message")
        captured = capsys.readouterr()
        assert level.value in captured.out
        assert "test message" in captured.out

    def test_prints_optional_prefix(self, capsys: pytest.CaptureFixture) -> None:
        with patch("alf_ros.alf_ros.cli.feedback._USE_COLOR", False):
            print_feedback(FeedbackLevel.INFO, "msg", prefix="my_node")
        captured = capsys.readouterr()
        assert "my_node" in captured.out

    def test_no_prefix_when_none(self, capsys: pytest.CaptureFixture) -> None:
        with patch("alf_ros.alf_ros.cli.feedback._USE_COLOR", False):
            print_feedback(FeedbackLevel.INFO, "only message")
        captured = capsys.readouterr()
        assert "[" not in captured.out.split("]", 1)[-1].split("]")[0]


class TestPrintBanner:
    """Tests for print_banner function."""

    def test_prints_title(self, capsys: pytest.CaptureFixture) -> None:
        with patch("alf_ros.alf_ros.cli.feedback._USE_COLOR", False):
            print_banner("ALF-ROS Test")
        captured = capsys.readouterr()
        assert "ALF-ROS Test" in captured.out

    def test_prints_subtitle_when_provided(self, capsys: pytest.CaptureFixture) -> None:
        with patch("alf_ros.alf_ros.cli.feedback._USE_COLOR", False):
            print_banner("Title", subtitle="Subtitle here")
        captured = capsys.readouterr()
        assert "Subtitle here" in captured.out

    def test_no_subtitle_when_none(self, capsys: pytest.CaptureFixture) -> None:
        with patch("alf_ros.alf_ros.cli.feedback._USE_COLOR", False):
            print_banner("Title Only")
        captured = capsys.readouterr()
        assert "Title Only" in captured.out


class TestPrintJointStates:
    """Tests for print_joint_states function."""

    def test_prints_all_joints(self, capsys: pytest.CaptureFixture) -> None:
        joints = {"left_knee_joint": 0.5, "right_knee_joint": -0.3}
        with patch("alf_ros.alf_ros.cli.feedback._USE_COLOR", False):
            print_joint_states(joints)
        captured = capsys.readouterr()
        assert "left_knee_joint" in captured.out
        assert "right_knee_joint" in captured.out

    def test_positions_formatted_as_radians(self, capsys: pytest.CaptureFixture) -> None:
        joints = {"test_joint": 1.2345}
        with patch("alf_ros.alf_ros.cli.feedback._USE_COLOR", False):
            print_joint_states(joints)
        captured = capsys.readouterr()
        assert "rad" in captured.out

    def test_empty_dict_prints_no_joints(self, capsys: pytest.CaptureFixture) -> None:
        with patch("alf_ros.alf_ros.cli.feedback._USE_COLOR", False):
            print_joint_states({})
        captured = capsys.readouterr()
        assert "rad" not in captured.out


class TestPrintRobotStatus:
    """Tests for print_robot_status function."""

    def test_connected_status(self, capsys: pytest.CaptureFixture) -> None:
        with patch("alf_ros.alf_ros.cli.feedback._USE_COLOR", False):
            print_robot_status("STANDING", 80.0, connected=True)
        captured = capsys.readouterr()
        assert "POŁĄCZONY" in captured.out

    def test_disconnected_status(self, capsys: pytest.CaptureFixture) -> None:
        with patch("alf_ros.alf_ros.cli.feedback._USE_COLOR", False):
            print_robot_status("IDLE", 50.0, connected=False)
        captured = capsys.readouterr()
        assert "ROZŁĄCZONY" in captured.out

    def test_battery_percentage_displayed(self, capsys: pytest.CaptureFixture) -> None:
        with patch("alf_ros.alf_ros.cli.feedback._USE_COLOR", False):
            print_robot_status("IDLE", 42.5, connected=True)
        captured = capsys.readouterr()
        assert "42.5" in captured.out

    def test_mode_displayed(self, capsys: pytest.CaptureFixture) -> None:
        with patch("alf_ros.alf_ros.cli.feedback._USE_COLOR", False):
            print_robot_status("WALKING", 75.0, connected=True)
        captured = capsys.readouterr()
        assert "WALKING" in captured.out


class TestFeedbackLevel:
    """Tests for the FeedbackLevel enum."""

    def test_all_levels_have_string_values(self) -> None:
        for level in FeedbackLevel:
            assert isinstance(level.value, str)
            assert len(level.value) > 0

    def test_expected_levels_exist(self) -> None:
        levels = {level.value for level in FeedbackLevel}
        assert "INFO" in levels
        assert "WARN" in levels
        assert "ERROR" in levels
        assert "DEBUG" in levels
        assert "CRITICAL" in levels
