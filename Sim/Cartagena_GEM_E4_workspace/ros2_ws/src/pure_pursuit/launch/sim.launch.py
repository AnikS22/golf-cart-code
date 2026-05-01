"""Launches Gazebo + the GEM E4 + the pure_pursuit controller in one shot."""
import os
import subprocess

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _make_rsp(context, xacro_path, gem_desc_share):
    # Xacro to URDF, then rewrite package:// URIs to absolute file:// paths so
    # gzclient (which has no ROS path resolver) can load the STL meshes directly.
    urdf = subprocess.check_output(
        ['xacro', xacro_path], stderr=subprocess.STDOUT, text=True
    )
    urdf = urdf.replace(
        'package://gem_description/',
        'file://' + gem_desc_share + '/',
    )
    return [
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{'robot_description': urdf}],
            output='screen',
        )
    ]


def generate_launch_description():
    gazebo_ros_share = get_package_share_directory('gazebo_ros')
    gem_desc_share = get_package_share_directory('gem_description')
    xacro_path = os.path.join(gem_desc_share, 'urdf', 'e4', 'gem_e4.urdf.xacro')

    gzserver = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gazebo_ros_share, 'launch', 'gzserver.launch.py')
        ),
        launch_arguments={
            'extra_gazebo_args': '-s libgazebo_ros_paths_plugin.so',
        }.items(),
    )
    gzclient = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gazebo_ros_share, 'launch', 'gzclient.launch.py')
        ),
    )

    rsp = OpaqueFunction(
        function=_make_rsp,
        kwargs={'xacro_path': xacro_path, 'gem_desc_share': gem_desc_share},
    )

    spawn = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=[
            '-topic', 'robot_description',
            '-entity', 'gem_e4',
            '-z', '0.1',
        ],
        output='screen',
    )

    use_pp = LaunchConfiguration('use_pure_pursuit')
    pp = Node(
        package='pure_pursuit',
        executable='pure_pursuit_node',
        output='screen',
        condition=IfCondition(use_pp),
    )

    pp_share = get_package_share_directory('pure_pursuit')
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', os.path.join(pp_share, 'rviz', 'sim.rviz')],
        output='screen',
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_pure_pursuit', default_value='true',
            description='Run the pure_pursuit controller. Set to false to drive manually.',
        ),
        gzserver,
        gzclient,
        rsp,
        TimerAction(period=3.0, actions=[spawn]),
        TimerAction(period=5.0, actions=[rviz]),
        TimerAction(period=7.0, actions=[pp]),
    ])
