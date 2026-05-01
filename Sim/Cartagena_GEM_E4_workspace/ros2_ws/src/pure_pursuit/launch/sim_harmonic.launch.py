"""Launch the GEM E4 + Pure Pursuit + FAU Breezeway in Gazebo Harmonic."""
import os
import subprocess

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _make_rsp(context, xacro_path):
    # Xacro with gz_version:=harmonic so the URDF pulls in Harmonic plugin blocks.
    urdf = subprocess.check_output(
        ['xacro', xacro_path, 'gz_version:=harmonic'],
        stderr=subprocess.STDOUT, text=True,
    )
    # Same package:// -> file:// rewrite as Classic so gz-sim can resolve meshes.
    gem_desc_share = get_package_share_directory('gem_description')
    urdf = urdf.replace(
        'package://gem_description/',
        'file://' + gem_desc_share + '/',
    )
    return [
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{'robot_description': urdf, 'use_sim_time': True}],
            output='screen',
        )
    ]


def generate_launch_description():
    pp_share = get_package_share_directory('pure_pursuit')
    gem_desc_share = get_package_share_directory('gem_description')
    xacro_path = os.path.join(gem_desc_share, 'urdf', 'e4', 'gem_e4.urdf.xacro')
    world_path = os.path.join(pp_share, 'worlds', 'fau_breezeway.sdf')
    bridge_yaml = os.path.join(pp_share, 'config', 'bridge.yaml')

    ros_gz_sim_share = get_package_share_directory('ros_gz_sim')
    gz_sim_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_sim_share, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': f'-r -v 3 {world_path}'}.items(),
    )

    rsp = OpaqueFunction(function=_make_rsp, kwargs={'xacro_path': xacro_path})

    spawn = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-topic', '/robot_description',
            '-name', 'gem_e4',
            '-z', '0.4',
        ],
        output='screen',
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[{'config_file': bridge_yaml, 'use_sim_time': True}],
        output='screen',
    )

    use_pp = LaunchConfiguration('use_pure_pursuit')
    pp = Node(
        package='pure_pursuit',
        executable='pure_pursuit_node',
        parameters=[{'use_sim_time': True}],
        output='screen',
        condition=IfCondition(use_pp),
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', os.path.join(pp_share, 'rviz', 'sim.rviz')],
        parameters=[{'use_sim_time': True}],
        output='screen',
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_pure_pursuit', default_value='true'),
        gz_sim_launch,
        rsp,
        bridge,
        TimerAction(period=3.0, actions=[spawn]),
        TimerAction(period=5.0, actions=[rviz]),
        TimerAction(period=7.0, actions=[pp]),
    ])
