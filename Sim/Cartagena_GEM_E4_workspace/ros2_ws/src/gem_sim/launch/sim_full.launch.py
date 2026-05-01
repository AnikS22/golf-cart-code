# sim_full.launch.py — full GEM E4 digital-twin sim
#
# Brings up: Gazebo Harmonic, the cart spawned with the canonical URDF
# and full sensor stack, ros_gz_bridge with all topics matching the real
# cart, robot_state_publisher, and sim_dbw_bridge (the simulated DBW
# translation layer).
#
# Run:
#   ros2 launch gem_sim sim_full.launch.py
#   ros2 launch gem_sim sim_full.launch.py world:=fau_breezeway
#
# Topics published after launch should EXACTLY match what the real cart
# will publish. See Sim/digital_twin_consistency.md for the contract.

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, Command
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg_gem_sim = FindPackageShare("gem_sim")
    pkg_ros_gz_sim = FindPackageShare("ros_gz_sim")

    # ─── Args ───
    world_arg = DeclareLaunchArgument(
        "world",
        default_value="fau_breezeway",
        description="World name under pure_pursuit/worlds/ (without .sdf). T1=fau_breezeway, T2/T3 to be added via regions.json.",
    )
    use_sim_time_arg = DeclareLaunchArgument(
        "use_sim_time",
        default_value="true",
        description="Use Gazebo clock for ROS time. Always true in sim.",
    )

    world = LaunchConfiguration("world")
    use_sim_time = LaunchConfiguration("use_sim_time")

    # World file lives in pure_pursuit/worlds/ for now. When we extend to
    # full FAU campus we'll move worlds into gem_sim/worlds/ to keep
    # everything in one package.
    world_path = PathJoinSubstitution([
        FindPackageShare("pure_pursuit"), "worlds",
        [world, ".sdf"],
    ])

    # URDF generation via xacro
    urdf_xacro_path = PathJoinSubstitution([
        pkg_gem_sim, "urdf", "gem_e4_robot.urdf.xacro",
    ])
    robot_description = {
        "robot_description": Command(["xacro ", urdf_xacro_path]),
        "use_sim_time": use_sim_time,
    }

    # ─── Gazebo Harmonic ───
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([pkg_ros_gz_sim, "launch", "gz_sim.launch.py"]),
        ]),
        launch_arguments={"gz_args": [world_path, " -r -v 4"]}.items(),
    )

    # ─── Spawn the cart ───
    spawn = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=[
            "-name", "gem_e4",
            "-topic", "robot_description",
            "-x", "0.0", "-y", "0.0", "-z", "0.20",
        ],
        output="screen",
    )

    # ─── Robot state publisher ───
    rsp = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[robot_description],
        output="screen",
    )

    # ─── Bridge (Gazebo ↔ ROS) ───
    bridge_yaml = PathJoinSubstitution([
        pkg_gem_sim, "config", "ros_gz_bridge.yaml",
    ])
    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        parameters=[{"config_file": bridge_yaml, "use_sim_time": True}],
        output="screen",
    )

    # ─── Simulated DBW bridge (the digital-twin DBW translation layer) ───
    sim_dbw = Node(
        package="sim_dbw_bridge",
        executable="sim_dbw_bridge_node",
        name="sim_dbw_bridge",
        parameters=[{"use_sim_time": True}],
        output="screen",
    )

    return LaunchDescription([
        world_arg,
        use_sim_time_arg,
        gazebo,
        rsp,
        spawn,
        bridge,
        sim_dbw,
    ])
