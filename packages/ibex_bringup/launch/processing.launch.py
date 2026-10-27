# Launch file for IBEX sensors
import os
import yaml

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution

from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    ld = LaunchDescription()

    #=========================# Configs #=========================#

    config_path = os.path.join(
        get_package_share_directory("ibex_bringup"), "config", "kiss_icp_config.yaml"
    )
    with open(config_path, "r") as f:
        kiss_icp_cfg = yaml.safe_load(f)["kiss_icp"]

    pipeline_config_path = os.path.join(
        get_package_share_directory("ibex_bringup"), "config", "kiss_icp_processing_config.yaml"
    )

    #=========================# Sub Launches #=========================#

    kiss_icp_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("kiss_icp"), "launch", "odometry.launch.py"]
            )
        ),
        launch_arguments={
            "topic": str(kiss_icp_cfg["topic"]),
            "base_frame": str(kiss_icp_cfg["base_frame"]),
            "lidar_odom_frame": str(kiss_icp_cfg["lidar_odom_frame"]),
            "visualize": str(kiss_icp_cfg["visualize"]),
            "config_file": pipeline_config_path,
        }.items(),
    )
    ld.add_action(kiss_icp_launch)


    # DEPRECATED: 27 Oct 26, replaced with RTAB Map
    # graph_frontender_launch = IncludeLaunchDescription(
    #     PythonLaunchDescriptionSource(
    #         PathJoinSubstitution(
    #             [FindPackageShare("ibex_state"), "launch", "graph_frontender.launch.py"]
    #         )
    #     ),
    # )
    # ld.add_action(graph_frontender_launch)

    rtabmap_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("ibex_state"), "launch", "rtabmap.launch.py"]
            )
        ),
    )
    ld.add_action(rtabmap_launch)

    return ld