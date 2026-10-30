# Launch file for IBEX basic functionality
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription,
                            SetEnvironmentVariable)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution

from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    ld = LaunchDescription()

    #=========================# Environment #=========================#
    # Must come before every include: environment changes apply only to
    # processes started after them, and every included launch file inherits
    # this one's environment.
    #
    # Large-message publishers (Ouster point clouds ~3 MB, decoded Insta360
    # images ~12 MB) need a Fast DDS shared-memory segment larger than the
    # 512 KB default. Without it, the PUBLISHER falls back to UDP loopback and
    # best-effort topics silently lose whole messages (~60% of Ouster scans in
    # testing). What matters is the publishing process's environment, so it
    # is set here rather than relying on ~/.bashrc, which launch from a
    # script, service, or non-interactive shell does not load.

    fastdds_profile = LaunchConfiguration("fastdds_profile")
    ld.add_action(
        DeclareLaunchArgument(
            "fastdds_profile",
            default_value=PathJoinSubstitution(
                [FindPackageShare("ibex_bringup"), "config", "fastdds_large_msgs.xml"]
            ),
            description="Fast DDS XML profile applied to every node in the stack",
        )
    )
    ld.add_action(SetEnvironmentVariable("FASTRTPS_DEFAULT_PROFILES_FILE", fastdds_profile))

    #=========================# Sub Launches #=========================#

    static_tf_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("ibex_bringup"), "launch", "static_tf.launch.py"]
            )
        ),
    )
    ld.add_action(static_tf_launch)

    sensors_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("ibex_bringup"), "launch", "sensors.launch.py"]
            )
        ),
        launch_arguments=[("fastdds_profile", fastdds_profile)],
    )
    ld.add_action(sensors_launch)

    processing_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("ibex_bringup"), "launch", "processing.launch.py"]
            )
        ),
    )
    ld.add_action(processing_launch)

    control_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("ibex_bringup"), "launch", "control.launch.py"]
            )
        ),
    )
    ld.add_action(control_launch)

    return ld
