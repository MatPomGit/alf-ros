"""Utilities for configurable ROS2 QoS profiles and network startup logging."""

from __future__ import annotations

from typing import Any

try:
    from rclpy.qos import (
        DurabilityPolicy,
        HistoryPolicy,
        QoSProfile,
        ReliabilityPolicy,
    )

    HAS_ROS = True
except ImportError:  # pragma: no cover - fallback for non-ROS test environments
    HAS_ROS = False
    DurabilityPolicy = HistoryPolicy = ReliabilityPolicy = Any  # type: ignore[assignment]
    QoSProfile = Any  # type: ignore[assignment]

QOS_PRESET_SENSOR_DATA = "sensor_data"
QOS_PRESET_RELIABLE_CONTROL = "reliable_control"
QOS_PRESET_LATCHED_STATUS = "latched_status"

if HAS_ROS:
    QOS_PRESETS: dict[str, QoSProfile] = {
        QOS_PRESET_SENSOR_DATA: QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=5,
        ),
        QOS_PRESET_RELIABLE_CONTROL: QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        ),
        QOS_PRESET_LATCHED_STATUS: QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        ),
    }
else:
    QOS_PRESETS: dict[str, Any] = {
        QOS_PRESET_SENSOR_DATA: object(),
        QOS_PRESET_RELIABLE_CONTROL: object(),
        QOS_PRESET_LATCHED_STATUS: object(),
    }

if HAS_ROS:
    _RELIABILITY_MAP: dict[str, ReliabilityPolicy] = {
        "best_effort": ReliabilityPolicy.BEST_EFFORT,
        "reliable": ReliabilityPolicy.RELIABLE,
    }
    _DURABILITY_MAP: dict[str, DurabilityPolicy] = {
        "volatile": DurabilityPolicy.VOLATILE,
        "transient_local": DurabilityPolicy.TRANSIENT_LOCAL,
    }
    _HISTORY_MAP: dict[str, HistoryPolicy] = {
        "keep_last": HistoryPolicy.KEEP_LAST,
        "keep_all": HistoryPolicy.KEEP_ALL,
    }
else:
    _RELIABILITY_MAP: dict[str, Any] = {}
    _DURABILITY_MAP: dict[str, Any] = {}
    _HISTORY_MAP: dict[str, Any] = {}


def build_qos_profile(
    *,
    preset: str,
    reliability: str,
    durability: str,
    history: str,
    depth: int,
) -> QoSProfile:
    """Build a ROS2 ``QoSProfile`` from preset and optional overrides.

    Args:
        preset: QoS preset name.
        reliability: Reliability policy string.
        durability: Durability policy string.
        history: History policy string.
        depth: Queue depth for keep-last history.

    Returns:
        A configured QoS profile.
    """
    if not HAS_ROS:
        raise RuntimeError("rclpy is required to build QoS profiles.")
    normalized_preset = preset.strip().lower()
    if normalized_preset in QOS_PRESETS:
        profile = QOS_PRESETS[normalized_preset]
        return QoSProfile(
            reliability=profile.reliability,
            durability=profile.durability,
            history=profile.history,
            depth=profile.depth,
        )

    normalized_reliability = reliability.strip().lower()
    normalized_durability = durability.strip().lower()
    normalized_history = history.strip().lower()

    resolved_reliability = _RELIABILITY_MAP.get(
        normalized_reliability, ReliabilityPolicy.RELIABLE
    )
    resolved_durability = _DURABILITY_MAP.get(normalized_durability, DurabilityPolicy.VOLATILE)
    resolved_history = _HISTORY_MAP.get(normalized_history, HistoryPolicy.KEEP_LAST)
    resolved_depth = max(1, depth)

    return QoSProfile(
        reliability=resolved_reliability,
        durability=resolved_durability,
        history=resolved_history,
        depth=resolved_depth,
    )


def qos_profile_to_text(profile: QoSProfile) -> str:
    """Return a compact text representation for logs."""
    return (
        f"reliability={profile.reliability.name}, "
        f"durability={profile.durability.name}, "
        f"history={profile.history.name}, "
        f"depth={profile.depth}"
    )


def log_network_settings(node: Any, *, ros_domain_id: int, localhost_only: bool, rmw: str) -> None:
    """Log effective DDS networking settings on node startup."""
    node.get_logger().info(
        "ROS network settings: "
        f"ROS_DOMAIN_ID={ros_domain_id}, "
        f"ROS_LOCALHOST_ONLY={int(localhost_only)}, "
        f"RMW_IMPLEMENTATION={rmw or '<default>'}"
    )
    if localhost_only:
        node.get_logger().warn(
            "Application networking is restricted to localhost "
            "(ROS_LOCALHOST_ONLY=1)."
        )
