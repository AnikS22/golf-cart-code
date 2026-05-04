# sim_minimal.launch.py — bring up Gazebo (Ignition Fortress) in an empty
# world only. NO cart, NO sensors, NO bridge. Use this to confirm the
# container's GUI + Gazebo is working before troubleshooting URDF/SDF
# version issues.
#
# Run inside the container:
#   ros2 launch gem_sim sim_minimal.launch.py

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    return LaunchDescription([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                PathJoinSubstitution([
                    FindPackageShare("ros_gz_sim"),
                    "launch", "gz_sim.launch.py",
                ]),
            ]),
            launch_arguments={"gz_args": "empty.sdf -r -v 4"}.items(),
        ),
    ])
