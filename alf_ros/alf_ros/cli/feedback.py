"""CLI feedback utilities for ALF-ROS.

Provides colorized terminal output helpers used across ALF-ROS nodes
and standalone CLI scripts for interacting with the robot.
"""

from __future__ import annotations

import sys
from enum import Enum
from typing import Optional

ANSI_COLORS = {
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "BLUE": "\033[94m",
    "CYAN": "\033[96m",
    "WHITE": "\033[97m",
}

_USE_COLOR = sys.stdout.isatty()


class FeedbackLevel(Enum):
    """Severity level for CLI feedback messages."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


_LEVEL_STYLES: dict[FeedbackLevel, tuple[str, str]] = {
    FeedbackLevel.DEBUG: ("BLUE", ""),
    FeedbackLevel.INFO: ("GREEN", ""),
    FeedbackLevel.WARN: ("YELLOW", "BOLD"),
    FeedbackLevel.ERROR: ("RED", "BOLD"),
    FeedbackLevel.CRITICAL: ("RED", "BOLD"),
}


def colorize(text: str, color: str, bold: bool = False) -> str:
    """Wrap text in ANSI color codes if color output is available.

    Args:
        text: The text to colorize.
        color: Color name key from ANSI_COLORS.
        bold: Whether to apply bold formatting.

    Returns:
        Colorized string, or original string if not a TTY.
    """
    if not _USE_COLOR:
        return text
    prefix = ANSI_COLORS.get("BOLD", "") if bold else ""
    color_code = ANSI_COLORS.get(color, "")
    reset = ANSI_COLORS["RESET"]
    return f"{prefix}{color_code}{text}{reset}"


def print_feedback(
    level: FeedbackLevel, message: str, prefix: Optional[str] = None
) -> None:
    """Print a formatted feedback message to stdout.

    Args:
        level: Severity level of the message.
        message: The message text to display.
        prefix: Optional prefix string (e.g., node name).
    """
    color, style = _LEVEL_STYLES[level]
    bold = style == "BOLD"
    tag = colorize(f"[{level.value}]", color, bold)
    node_prefix = f"[{prefix}] " if prefix else ""
    print(f"{tag} {node_prefix}{message}", flush=True)


def print_banner(title: str, subtitle: Optional[str] = None) -> None:
    """Print a startup banner to stdout.

    Args:
        title: Main title text.
        subtitle: Optional subtitle line.
    """
    width = 60
    line = colorize("=" * width, "CYAN", bold=True)
    print(line)
    print(colorize(f"  {title}".center(width), "WHITE", bold=True))
    if subtitle:
        print(colorize(f"  {subtitle}".center(width), "CYAN"))
    print(line)
    print()


def print_joint_states(joint_states: dict[str, float]) -> None:
    """Print joint positions in a formatted table.

    Args:
        joint_states: Dictionary mapping joint name to position in radians.
    """
    print(colorize("─── Stany stawów ───────────────────────────────────", "CYAN"))
    for name, pos in joint_states.items():
        value_str = colorize(f"{pos:+.4f} rad", "WHITE")
        print(f"  {name:<35} {value_str}")
    print(colorize("─" * 52, "CYAN"))


def print_robot_status(mode: str, battery: float, connected: bool) -> None:
    """Print a robot status summary to stdout.

    Args:
        mode: Current robot mode string.
        battery: Battery percentage (0.0 - 100.0).
        connected: Whether the robot is connected.
    """
    conn_str = (
        colorize("POŁĄCZONY", "GREEN", bold=True)
        if connected
        else colorize("ROZŁĄCZONY", "RED", bold=True)
    )
    bat_color = "RED" if battery < 20.0 else ("YELLOW" if battery < 50.0 else "GREEN")
    bat_str = colorize(f"{battery:.1f}%", bat_color, bold=True)
    mode_str = colorize(mode, "CYAN", bold=True)

    print(colorize("─── Status robota ──────────────────────────────────", "CYAN"))
    print(f"  Połączenie : {conn_str}")
    print(f"  Tryb       : {mode_str}")
    print(f"  Bateria    : {bat_str}")
    print(colorize("─" * 52, "CYAN"))
