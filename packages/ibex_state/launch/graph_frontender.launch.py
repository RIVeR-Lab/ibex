# Launch file for IBEX state estimation

# ================================================ #
#
# NOTE: This file is deprecated CAO 27 OCT 2026
#       and was replaced with RTAB Map
#
# ================================================ #



from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution

from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    ld = LaunchDescription()

    #=========================# Launch Args #=========================#



    #=========================# Config #=========================#

    graph_frontender_config = PathJoinSubstitution([FindPackageShare("ibex_state"), "config", "graph_frontender_config.yaml"])



    #=========================# Nodes #=========================#

    graph_frontender_node = Node(
        package="ibex_state",
        executable="graph_frontender",
        name="graph_frontender",
        output="screen",
        emulate_tty="true",
        parameters=[
            graph_frontender_config,
        ],
    )
    ld.add_action(graph_frontender_node)


    return ld