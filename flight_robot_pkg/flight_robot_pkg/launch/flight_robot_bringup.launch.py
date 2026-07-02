import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('flight_robot_pkg')

    bridge = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_share, 'launch', 'flight_robot_bridge.launch.py')),
        launch_arguments={
            'model_name': LaunchConfiguration('model_name'),
            'world_name': LaunchConfiguration('world_name'),
            # mode_manager owns the wheels: teleop publishes /cmd_vel,
            # the node forwards to /wheel/cmd_vel only in GROUND state.
            'wheel_cmd_topic': '/wheel/cmd_vel',
        }.items(),
    )

    mode_manager = Node(
        package='flight_robot_pkg',
        executable='mode_manager',
        parameters=[{'use_sim_time': True}],
        output='screen',
    )

    return LaunchDescription([
        DeclareLaunchArgument('model_name', default_value='flight_robot_0'),
        DeclareLaunchArgument('world_name', default_value='default'),
        bridge,
        mode_manager,
    ])
