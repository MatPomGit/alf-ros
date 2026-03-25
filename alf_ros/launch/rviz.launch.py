"""Launch file for RViz2 visualization of ALF-ROS."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    """Generate launch description for RViz2."""
    pkg_share = get_package_share_directory("alf_ros")
    rviz_config = os.path.join(pkg_share, "rviz", "alf_ros.rviz")

    rviz_config_arg = DeclareLaunchArgument(
        "rviz_config",
        default_value=rviz_config,
        description="Path to RViz2 configuration file",
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        arguments=["-d", LaunchConfiguration("rviz_config")],
        output="screen",
    )

    return LaunchDescription([
        rviz_config_arg,
        rviz_node,
    ])
