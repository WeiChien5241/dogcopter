from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    # PX4 spawns the model as flight_robot_${px4_instance}; the suffix shifts
    # if PX4 restarts against a live Gazebo (old models are not despawned),
    # so the name is an argument. Find the live one with: gz topic -l | grep cmd_vel
    model_name = LaunchConfiguration('model_name')
    world_name = LaunchConfiguration('world_name')
    # /cmd_vel lets teleop_twist_keyboard drive directly; the M3 bringup
    # re-points this to /wheel/cmd_vel so the mode manager owns the wheels.
    wheel_cmd_topic = LaunchConfiguration('wheel_cmd_topic')

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            ['/model/', model_name, '/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist'],
            '/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry',
            ['/world/', world_name, '/model/', model_name,
             '/joint_state@sensor_msgs/msg/JointState[gz.msgs.Model'],
            ['/model/', model_name, '/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V'],
        ],
        remappings=[
            (['/model/', model_name, '/cmd_vel'], wheel_cmd_topic),
            (['/world/', world_name, '/model/', model_name, '/joint_state'], '/joint_states'),
            (['/model/', model_name, '/tf'], '/tf'),
        ],
        parameters=[{'use_sim_time': True}],
        output='screen',
    )

    return LaunchDescription([
        DeclareLaunchArgument('model_name', default_value='flight_robot_0'),
        DeclareLaunchArgument('world_name', default_value='default'),
        DeclareLaunchArgument('wheel_cmd_topic', default_value='/cmd_vel'),
        bridge,
    ])
