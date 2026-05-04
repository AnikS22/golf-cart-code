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
import subprocess
import tempfile
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
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
    headless_arg = DeclareLaunchArgument(
        "headless",
        default_value="false",
        description="Run Gazebo server-only (no GUI). Use true on a headless box like the Jetson over SSH.",
    )

    world = LaunchConfiguration("world")
    use_sim_time = LaunchConfiguration("use_sim_time")
    headless = LaunchConfiguration("headless")

    # World file lives in pure_pursuit/worlds/ for now. When we extend to
    # full FAU campus we'll move worlds into gem_sim/worlds/ to keep
    # everything in one package.
    # Note: PathJoinSubstitution can't handle a nested list, so we flatten
    # the world+.sdf concat via a small helper.
    def _world_path(context):
        world_name = LaunchConfiguration("world").perform(context)
        return os.path.join(
            get_package_share_directory("pure_pursuit"),
            "worlds",
            f"{world_name}.sdf",
        )

    # URDF generation via xacro
    urdf_xacro_path = PathJoinSubstitution([
        pkg_gem_sim, "urdf", "gem_e4_robot.urdf.xacro",
    ])
    # Wrap the xacro Command in ParameterValue(value_type=str) so launch
    # treats it as a string, not as YAML. Without this, ROS 2 launch
    # tries to YAML-parse the URDF and errors out with "Unable to parse
    # the value of parameter robot_description as yaml".
    robot_description = {
        "robot_description": ParameterValue(
            Command(["xacro ", urdf_xacro_path]),
            value_type=str,
        ),
        "use_sim_time": use_sim_time,
    }

    # ─── Gazebo Harmonic ───
    # Defer gazebo include to an OpaqueFunction so we can compute the world
    # path at launch time (after `world` arg has been parsed).
    def _make_gazebo(context, *args, **kwargs):
        wp = _world_path(context)
        is_headless = LaunchConfiguration("headless").perform(context).lower() == "true"
        # -s = server-only (no GUI). Required on headless Jetson over SSH.
        gz_flags = "-r -s -v 4" if is_headless else "-r -v 4"
        return [IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(
                    get_package_share_directory("ros_gz_sim"),
                    "launch", "gz_sim.launch.py",
                )
            ),
            launch_arguments={"gz_args": f"{wp} {gz_flags}"}.items(),
        )]
    gazebo = OpaqueFunction(function=_make_gazebo)

    # ─── Render URDF to a temp file (Humble RSP doesn't publish
    #     /robot_description as a topic by default, so we don't rely on
    #     the topic-based spawn flow — render once, pass the file path
    #     directly to ros_gz_sim create via -file). ───
    def _render_urdf(context, *args, **kwargs):
        xacro_path = os.path.join(
            get_package_share_directory("gem_sim"),
            "urdf", "gem_e4_robot.urdf.xacro",
        )
        urdf_path = os.path.join(tempfile.gettempdir(), "gem_e4_robot.urdf")
        urdf_xml = subprocess.check_output(
            ["xacro", xacro_path], text=True)
        with open(urdf_path, "w") as f:
            f.write(urdf_xml)
        spawn_node = Node(
            package="ros_gz_sim",
            executable="create",
            arguments=[
                "-name", "gem_e4",
                "-file", urdf_path,
                "-x", "0.0", "-y", "0.0", "-z", "0.20",
            ],
            output="screen",
        )
        return [spawn_node]

    spawn = OpaqueFunction(function=_render_urdf)

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
        headless_arg,
        gazebo,
        rsp,
        spawn,
        bridge,
        sim_dbw,
    ])
