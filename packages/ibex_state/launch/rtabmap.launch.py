# Launch file for IBEX lidar-only RTAB-Map SLAM
#
# WARNING: '-d' on the rtabmap node deletes ~/.ros/rtabmap.db on every launch.
import os
import yaml

from launch import LaunchDescription

from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    ld = LaunchDescription()

    #=========================# Config #=========================#

    rtabmap_config = os.path.join(get_package_share_directory("ibex_state"), "config", "rtabmap_config.yaml")

    # Topic remaps aren't ROS parameters, so read them from the launch section of the yaml
    with open(rtabmap_config) as f:
        launch_cfg = yaml.safe_load(f)["ibex_launch"]["ros__parameters"]
    lidar_topic = launch_cfg["lidar_topic"]

    #=========================# Nodes #=========================#

    icp_odometry_node = Node(
        package="rtabmap_odom",
        executable="icp_odometry",
        name="icp_odometry",
        namespace="rtabmap",
        output="screen",
        emulate_tty=True,
        parameters=[
            rtabmap_config,
        ],
        remappings=[
            ("scan_cloud", lidar_topic),
        ],
        arguments=["--ros-args", "--log-level", "warn"],
    )
    ld.add_action(icp_odometry_node)

    rtabmap_node = Node(
        package="rtabmap_slam",
        executable="rtabmap",
        name="rtabmap",
        namespace="rtabmap",
        output="screen",
        emulate_tty=True,
        parameters=[
            rtabmap_config,
        ],
        remappings=[
            ("scan_cloud", lidar_topic),
        ],
        arguments=["-d", "--ros-args", "--log-level", "warn"],
    )
    ld.add_action(rtabmap_node)

    return ld