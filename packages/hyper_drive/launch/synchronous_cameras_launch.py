from launch import LaunchDescription
from launch.actions import SetEnvironmentVariable, TimerAction
from launch_ros.actions import Node
import os


def generate_launch_description():
    current_ld_path = os.environ.get('LD_LIBRARY_PATH','')

    lib_paths = [
        '/opt/imec/hsi-mosaic/bin',
        '/opt/imec/hsi-mosaic/resources/installers/package/api/X64',
        '/opt/pleora/ebus_sdk/Ubuntu-22.04-x86_64/lib', # pleora ebus 6.5.3
        '/opt/pleora/ebus_sdk/Ubuntu-22.04-x86_64/lib/genicam/bin/Linux64_x64',
        # '/opt/pleora/ebus_sdk/Ubuntu-x86_64/lib', # pleora ebus 6.1.1
        # '/opt/pleora/ebus_sdk/Ubuntu-x86_64/lib/genicam/bin/Linux64_x64',
        '/opt/XIMEA/CamTool',
        '/opt/PFSDK_2025.1.0_Linux64/lib',
        current_ld_path
    ]

    ld_path = ':'.join(filter(None, lib_paths))
    config_path = os.path.expanduser('~/allied_vision_config.xml')

    return LaunchDescription([
        SetEnvironmentVariable('GENICAM_ROOT_V3_1', '/opt/pleora/ebus_sdk/Ubuntu-22.04-x86_64/lib/genicam'),
        SetEnvironmentVariable('GENICAM_ROOT_V3_4', '/opt/pleora/ebus_sdk/Ubuntu-22.04-x86_64/lib/genicam'),
        #SetEnvironmentVariable('RMW_IMPLEMENTATION', 'rmw_cyclonedds_cpp'),
        #SetEnvironmentVariable('CYCLONEDDS_URI', 'file:///home/river/cyclonedds.xml'),
        SetEnvironmentVariable('LD_LIBRARY_PATH', ld_path),

        # RGB Camera Node
        Node(
            package='vimbax_camera',
            executable='vimbax_camera_node',
            name='alvium_camera',
            namespace='alvium',
            output='screen',
            emulate_tty=True,
            parameters=[{
                'camera_id': 'DEV_1AB22C025217',  # your camera GUID
                'settings_file': config_path,
                'use_ros_time': True,
            }],
            remappings=[
                ('/alvium/image_raw', '/camera/image_raw')  # remap to topic synchronous_cubes expects
            ]
        ),

        # Synchronous cube generator for both IMEC and XIMEA cameras
        TimerAction(
            period=5.0,
            actions=[
                Node(
                    package='hyper_drive',
                    executable='synchronous_cubes',
                    name='cameraProcessors',
                    output='screen',
                    emulate_tty=True,
                    parameters=[{
                        'sleep': 0.001, # 0.001
                        'x_frame_rate': 17, #15
                        'x_integration_time': 10,
                        'i_frame_rate': 15,
                        'i_integration_time': 60, #60
                        'time_wait': 0,
                    }]
                ),
            ]
        ),

        # Cube visualizer
        TimerAction(
            period=10.0,
            actions=[
                Node(
                    package='hyper_drive',
                    executable='synchronous_cube_visualizer',
                    output='screen',
                    emulate_tty=True,
                ),
            ]
        ),
    ])