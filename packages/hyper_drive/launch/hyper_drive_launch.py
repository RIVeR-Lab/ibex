from launch import LaunchDescription
from launch.actions import SetEnvironmentVariable
from launch_ros.actions import Node
import os


def generate_launch_description():
    current_ld_path = os.environ.get('LD_LIBRARY_PATH','')

    lib_paths = [
        '/opt/imec/hsi-mosaic/bin',
        '/opt/imec/hsi-mosaic/resources/installers/package/api/X64',
        '/opt/pleora/ebus_sdk/Ubuntu-22.04-x86_64/lib', # pleora ebus 7
        '/opt/pleora/ebus_sdk/Ubuntu-22.04-x86_64/lib/genicam/bin/Linux64_x64',
        # '/opt/pleora/ebus_sdk/Ubuntu-x86_64/lib', # pleora ebus 6.1.1
        # '/opt/pleora/ebus_sdk/Ubuntu-x86_64/lib/genicam/bin/Linux64_x64',
        '/opt/XIMEA/CamTool',
        '/opt/PFSDK_2025.1.0_Linux64/lib',
        current_ld_path
    ]

    ld_path = ':'.join(filter(None, lib_paths))

    return LaunchDescription([
        SetEnvironmentVariable('GENICAM_ROOT_V3_1', '/opt/pleora/ebus_sdk/Ubuntu-22.04-x86_64/lib/genicam'),
        SetEnvironmentVariable('GENICAM_ROOT_V3_4', '/opt/pleora/ebus_sdk/Ubuntu-22.04-x86_64/lib/genicam'),
        SetEnvironmentVariable('LD_LIBRARY_PATH', ld_path),

        Node(
            package='hyper_drive',
            executable='hyper_drive_pub',
            output='screen',
            emulate_tty=True,
            parameters=[{
                'camera_model': 'ximea', #imec
                'frame_rate': 15, #15
                'integration_time': 10 #60
            }]
        ),

        Node(
            package='hyper_drive',
            executable='cube_visualizer',
            output='screen',
            emulate_tty=True,
        ),
    ])