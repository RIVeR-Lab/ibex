# Command Cheat Sheet

## Headless ↔ Headed Mode Switching
Via SSH from a remote computer → Enter Headless moded (Remove computer connection)
```bash
sudo systemctl disable --now gdm3 && sudo /etc/NX/nxserver --restart
```

Via SSH from a remote computer → Enter Headed moded (Perform with computer connection removed)
```bash
sudo systemctl enable --now gdm3
```

## System Bringup
Brings up the sensors and static transforms
```bash
ros2 launch ibex_bringup system_bringup.launch.py
```



## Individual Launches

### Launch kairos controller (Shared_Link_Bridge)
```bash
ros2 launch shared_link_bridge bringup.launch.py
```
or you can launch directly from inside ibex_bring up
```bash
ros2 launch ibex_bringup control.launch.py
```

### Launch ouster driver 

If need to check lidar IP:
```bash
avahi-browse -lrt _roger._tcp
```

Next, run (takes a moment to come up)
```bash
ros2 launch ouster_ros driver.launch.py params_file:=/home/river/ibex_ws/src/ibex/packages/ibex_bringup/config/ibex_ouster_sensor_config.yaml viz:=false
```

*no need to use this (gives metadata file at working directory)*
```bash
ros2 launch ouster_ros sensor.launch.xml sensor_hostname:=169.254.105.158 viz:=false
```

### Launch KISS-ICP (Odometry generation)
```bash
ros2 launch kiss_icp odometry.launch.py topic:=/ouster/points
```

### Launch insta360
```bash
ros2 launch insta360_ros_driver insta_bringup.launch.py equirectangular:=true
```


### Launch Hyperspectral and RGB
```bash
echo 0 | sudo tee /sys/module/usbcore/parameters/usbfs_memory_mb
```
```bash
lsusb
```
```bash
sudo chmod 777 /dev/bus/usb/XXX/XXX
```
```bash
ros2 launch hyper_drive ambient_light_launch.py
```

### View Hyperspectral and RGB
```bash
ros2 run image_view image_view --ros-args -r image:=/visualizer/imec/false_color
```
```bash
ros2 run image_view image_view --ros-args -r image:=/visualizer/ximea/false_color
```
```bash
ros2 run image_view image_view --ros-args -r image:=/visualizer/
```

### Launch and View Point Spectrometer
```bash
sudo chmod 777 /dev/bus/usb/XXX/XXX

ros2 launch spectrometer_drivers ibsen_launch.py
```

### Record ROS2 Bag with all topics and compressed data format
```bash
ros2 bag record -a -o /home/river/ibex_ws/rosbag_library/<fieldtestname-day-date-time> -s mcap
```

### Foxglove Data Visualization
```bash
foxglove-studio

ros2 launch foxglove_bridge foxglove_bridge_launch.xml port:=8765
```


