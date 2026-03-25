"""Main launch file for ALF-ROS — starts all nodes."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    """Generate the launch description for ALF-ROS."""
    robot_ns_arg = DeclareLaunchArgument(
        "robot_namespace",
        default_value="",
        description="Robot namespace (empty for laptop, 'g1' for Unitree G1 EDU)",
    )
    use_gui_arg = DeclareLaunchArgument(
        "use_gui",
        default_value="true",
        description="Whether to launch the GUI",
    )
    use_rviz_arg = DeclareLaunchArgument(
        "use_rviz",
        default_value="true",
        description="Whether to launch RViz2",
    )

    robot_namespace = LaunchConfiguration("robot_namespace")

    controller_node = Node(
        package="alf_ros",
        executable="robot_controller",
        name="alf_ros_controller",
        parameters=[
            {"robot_namespace": robot_namespace},
            {"publish_rate_hz": 50.0},
            {"max_linear_vel": 0.5},
            {"max_angular_vel": 1.0},
        ],
        output="screen",
        emulate_tty=True,
    )

    monitor_node = Node(
        package="alf_ros",
        executable="status_monitor",
        name="alf_ros_monitor",
        parameters=[{"robot_namespace": robot_namespace}],
        output="screen",
        emulate_tty=True,
    )

    gui_node = Node(
        package="alf_ros",
        executable="gui_node",
        name="alf_ros_gui",
        parameters=[{"robot_namespace": robot_namespace}],
        output="screen",
        emulate_tty=True,
    )

    return LaunchDescription([
        robot_ns_arg,
        use_gui_arg,
        use_rviz_arg,
        LogInfo(msg=["Uruchamianie ALF-ROS (namespace: '", robot_namespace, "')"]),
        controller_node,
        monitor_node,
        gui_node,
    ])
