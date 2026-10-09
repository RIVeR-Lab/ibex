---
status: draft
owner: TODO(verify)
last-verified: 2026-10-08
---

# ROS graph

Every topic on IBEX with its type, publisher, subscriber, and QoS.

**Reference page.** Captured live with `system_bringup`, `hyper_drive`'s ambient-light
pipeline, and `spectrometer_drivers` all running.

## TODO(verify): rates are not yet measured

The rate column is empty throughout this page. Filling it takes two passes, because
**some topics cannot give a meaningful reading with the vehicle parked indoors.**

### Pass 1 — bench, any time

These publish on their own timers or on sensor data and do not care where the vehicle is:

```bash
for t in /ouster/points /ouster/imu /insta360/imu/data_raw /kiss/odometry \
         /graph_pose /odom_offset /synchronous_cubes /corrected_cubes \
         /combined_spectra /ibsen_vnir/spectral_data /ibsen_nir/spectral_data \
         /camera/image_raw; do
  printf '=== %s\n' "$t"
  timeout 10 ros2 topic hz "$t" 2>&1 | tail -2
done
```

### Pass 2 — outdoors, engine running, vehicle moving

**Requires a field session.** Three topics are meaningless otherwise:

| Topic | Why it needs the field |
| --- | --- |
| `/gps_values` | Needs sky view for a fix. Indoors the driver may publish sentinel values or nothing |
| `/vehicle_control` | `controller_teleop` publishes on gamepad input, so it needs an operator on the sticks with the VIM armed |
| `/kairos_values` | The P4S4's telemetry rate may differ between idle and actively reporting |

```bash
for t in /gps_values /kairos_values /vehicle_control; do
  printf '=== %s\n' "$t"
  timeout 20 ros2 topic hz "$t" 2>&1 | tail -2
done
```

Run this during a session that is happening anyway rather than scheduling one for it. Use
a 20-second window — these are slower and more irregular than the sensor topics.

**Follow [power-on.md](../02-operations/power-on.md) and the pre-run checklist.** Arming
the VIM makes the actuators live, so this needs a spotter regardless of the fact that
nobody is driving autonomously.

> While out, also capture `/kiss/odometry` moving. Its *rate* will match the parked
> figure, but confirming the pose actually advances is the definitive test that lidar
> odometry works — see
> [kiss-icp.md](../04-subsystems/state-estimation/software/kiss-icp.md#diagnostics).

## Three things this capture found

### Two nodes are running twice

| Node | Instances | Effect |
| --- | --- | --- |
| `graph_frontender` | **2** | Two independent factor graphs publishing to `/graph_pose` and `/odom_offset` |
| `spectra_combiner` | **2** | Duplicate spectra on `/combined_spectra` at twice the intended rate |

Both show one node name with **two distinct DDS GIDs**, and both affected topics report
`Publisher count: 2`.

Neither errors. Consumers simply receive interleaved messages from two sources, and for
`graph_frontender` those are two *independent estimators* that will diverge.

> TODO(verify): find what started each twice. The likely cause is running a sub-launch
> alongside `system_bringup`, which already includes it — `processing.launch.py` includes
> `graph_frontender.launch.py`, and `ambient_light_launch.py` contains the whole
> spectrometer stack. See
> [launch-files.md](launch-files.md).

### kiss_icp_node is in sim-time mode with no clock

`/clock` has **0 publishers and 2 subscribers** — `kiss_icp_node` and its internal
transform listener. `use_sim_time` is confirmed **true** on that node, and upstream's
`odometry.launch.py` defaults it that way for bag playback.

**Checked: `/kiss/odometry` carries a real wall-clock stamp**, so KISS-ICP stamps from the
input cloud rather than from its own clock. The lidar timestamps reaching the factor graph
are correct.

The node's own `now()` is still pinned at zero, which is a latent trap for anything added
to it later. Fix by setting `use_sim_time: false` in
`kiss_icp_processing_config.yaml`. See
[kiss-icp.md](../04-subsystems/state-estimation/software/kiss-icp.md#use_sim_time-is-true-with-no-clock-source).

### The dead GPS transform is confirmed on the live system

`/tf_static` has **8 publishers**: seven from `ibex_bringup` plus the Ouster driver.
`gps_mount_static_tf` is absent, confirming the unreachable code in
`static_tf.launch.py` — see
[launch-files.md](launch-files.md#there-is-unreachable-code-in-this-file).

## Topics

QoS is Reliable/Volatile unless noted. **BE** = Best Effort, **TL** = Transient Local.

### Perception — Ouster

| Topic | Type | Publisher | Subscriber | QoS |
| --- | --- | --- | --- | --- |
| `/ouster/points` | `sensor_msgs/PointCloud2` | `os_driver` | `kiss_icp_node` | **BE** |
| `/ouster/imu` | `sensor_msgs/Imu` | `os_driver` | `graph_frontender` ×2 | **BE** |
| `/ouster/metadata` | `std_msgs/String` | `os_driver` | — | **TL** |
| `/ouster/telemetry` | `ouster_sensor_msgs/Telemetry` | `os_driver` | — | **BE** |
| `/ouster/os_driver/transition_event` | `lifecycle_msgs/TransitionEvent` | `os_driver` | `launch_ros` | |

`/ouster/metadata` is **Transient Local**, so a late subscriber still receives it — this is
how beam angles are obtained without restarting the driver.

### Perception — Insta360

| Topic | Type | Publisher | Subscriber | QoS |
| --- | --- | --- | --- | --- |
| `/insta360/dual_fisheye/image/compressed` | `sensor_msgs/CompressedImage` | `insta360_ros_driver` | `image_decoder` | |
| `/insta360/dual_fisheye/image` | `sensor_msgs/Image` | `image_decoder` | `equirectangular_node` | |
| `/insta360/equirectangular/image` | `sensor_msgs/Image` | `equirectangular_node` | — | |
| `/insta360/imu/data_raw` | `sensor_msgs/Imu` | `insta360_ros_driver` | `imu_filter`, `graph_frontender` ×2 | **BE** |
| `/insta360/imu/data` | `sensor_msgs/Imu` | `imu_filter` | **none** | |
| `/insta360/imu/mag` | `sensor_msgs/MagneticField` | **none** | `imu_filter` | **BE** |

**The Madgwick filter is confirmed inert.** It subscribes to a magnetometer with no
publisher, and its output has no subscriber. `graph_frontender` takes `data_raw` and does
its own preintegration. Setting `imu_filter:=false` would remove it with no downstream
effect.

**`imu_filter` also publishes to `/tf`** — one of only two dynamic transform publishers on
the vehicle. Its frames are unrecorded.

### Perception — hyperspectral

| Topic | Type | Publisher | Subscriber | QoS |
| --- | --- | --- | --- | --- |
| `/camera/image_raw` | `sensor_msgs/Image` | `alvium_camera` | `cameraProcessors` | |
| `/alvium/camera_info` | `sensor_msgs/CameraInfo` | `alvium_camera` | **none** | |
| `/synchronous_cubes` | `hyper_drive_interfaces/MultipleDataCubes` | `cameraProcessors` | `ambient_light` | |
| `/corrected_cubes` | `hyper_drive_interfaces/MultipleDataCubes` | `ambient_light` | `corrected_cube_visualizer` | |

`/synchronous_cubes` is **Reliable** and carries ~14.7 MB per message — see
[hyper-drive.md](../04-subsystems/perception/software/hyper-drive.md#reliable-qos-on-very-large-messages).

### Perception — spectrometers

| Topic | Type | Publisher | Subscriber | QoS |
| --- | --- | --- | --- | --- |
| `/ibsen_vnir/spectral_data` | `spectrometer_interfaces/Spectra` | `ibsen_vnir` | `spectra_combiner` ×2 | |
| `/ibsen_nir/spectral_data` | `spectrometer_interfaces/Spectra` | `ibsen_nir` | `spectra_combiner` ×2 | |
| `/combined_spectra` | `spectrometer_interfaces/Spectra` | `spectra_combiner` **×2** | `ambient_light`, `combined_plot` | |

### State estimation

| Topic | Type | Publisher | Subscriber | QoS |
| --- | --- | --- | --- | --- |
| `/kiss/odometry` | `nav_msgs/Odometry` | `kiss_icp_node` | `graph_frontender` ×2 | |
| `/graph_pose` | `geometry_msgs/PoseWithCovarianceStamped` | `graph_frontender` **×2** | **none** | |
| `/odom_offset` | `geometry_msgs/PoseWithCovarianceStamped` | `graph_frontender` **×2** | **none** | |

**`/kiss/odometry` is Reliable on both ends** — the configured topic name matches and the
QoS is compatible. That link works.

**Nothing consumes the fused pose.** Both `/graph_pose` and `/odom_offset` have zero
subscribers, which answers an open question on
[the state estimation README](../04-subsystems/state-estimation/README.md): the subsystem
currently has no downstream user.

### Motion

| Topic | Type | Publisher | Subscriber | QoS |
| --- | --- | --- | --- | --- |
| `/joy` | `sensor_msgs/Joy` | `joy_node` | `controller_teleop` | |
| `/joy/set_feedback` | `sensor_msgs/JoyFeedback` | **none** | `joy_node` | |
| `/vehicle_control` | `shared_link_bridge/VehicleControl` | `controller_teleop` | `shared_link_bridge_node` | rate: **field only** |
| `/kairos_values` | `shared_link_bridge/KairosValues` | `shared_link_bridge_node` | `controller_teleop` | rate: **field only** |
| `/gps_values` | `shared_link_bridge/GpsValues` | `shared_link_bridge_node` | `graph_frontender` ×2 | rate: **field only** |
| `/outbound_msgs` | `std_msgs/String` | `shared_link_bridge_node` | **none** | |

The command chain is clean: `joy_node → /joy → controller_teleop → /vehicle_control →
shared_link_bridge_node → P4S4`.

**`/kairos_values` goes only to the teleop display.** It carries the vehicle telemetry that
`graph_frontender`'s bicycle model needs and never reaches it — see
[ibex-state.md](../04-subsystems/state-estimation/software/ibex-state.md#the-control-input-is-not-connected).

### Transforms

| Topic | Publishers | Subscribers | QoS |
| --- | --- | --- | --- |
| `/tf` | `kiss_icp_node`, `imu_filter` | `graph_frontender` ×2, kiss_icp's listener | |
| `/tf_static` | 8 — seven `static_transform_publisher` + `os_driver` | same | **TL** |

See [tf-frames.md](tf-frames.md).

### Visualization

| Topic | Publisher | Subscribers |
| --- | --- | --- |
| `/visualizer/{ximea,imec}/false_color` | `sync_cube_visualizer` | none |
| `/visualizer_corrected/{ximea,imec}/false_color` | `corrected_cube_visualizer` | none |
| `/visualizer_corrected/{ximea,imec}/band_N` | `corrected_cube_visualizer` | none |
| `/visualizer_corrected/{ximea,imec}/band_grid` | `corrected_cube_visualizer` | none |
| `/output` | `image_view_node` ×2 | none |

24 Ximea band topics and 9 IMEC. **Only band 6 carries data** — the per-band loop is
commented out and `publish_band_grid()` is never called, so 33 of 35 are advertised and
silent.

## Nodes

| Node | Namespace | Package |
| --- | --- | --- |
| `os_driver` | `/ouster` | `ouster_ros` |
| `insta360_ros_driver`, `image_decoder`, `equirectangular_node`, `imu_filter` | `/insta360` | `insta360_ros_driver` |
| `kiss_icp_node` | `/` | `kiss_icp` |
| `graph_frontender` **×2** | `/` | `ibex_state` |
| `shared_link_bridge_node`, `controller_teleop`, `joy_node` | `/` | `shared_link_bridge` |
| `alvium_camera` | `/alvium` | `vimbax_camera` |
| `cameraProcessors`, `ambient_light`, `corrected_cube_visualizer` | `/` | `hyper_drive` |
| `ibsen_vnir`, `ibsen_nir` | own | `spectrometer_drivers` |
| `spectra_combiner` **×2**, `combined_plot` | `/` | `spectrometer_drivers` |
| 7 × `*_static_tf` | `/` | `tf2_ros` |

## Topics with no subscriber

Advertised and unread. Not all are faults — several are diagnostic outlets.

| Topic | Assessment |
| --- | --- |
| `/graph_pose`, `/odom_offset` | **The system's main output.** No consumer exists |
| `/alvium/camera_info` | Orphaned from its image by the remap — see [alvium-rgb-camera.md](../04-subsystems/perception/hardware/alvium-rgb-camera.md) |
| `/insta360/imu/data` | The inert Madgwick filter's output |
| `/insta360/equirectangular/image` | Produced on request; useful for review |
| `/ouster/metadata` | Transient Local, read on demand |
| `/ouster/telemetry` | Diagnostic |
| `/outbound_msgs` | Diagnostic |
| 33 visualizer band topics | Advertised but never published to |

## Topics with no publisher

| Topic | Why |
| --- | --- |
| `/clock` | **Misconfiguration** — see above |
| `/insta360/imu/mag` | No magnetometer on the vehicle |
| `/joy/set_feedback` | Nothing drives gamepad rumble |

## QoS compatibility

Best Effort publishers require Best Effort subscribers; a Reliable subscriber receives
**nothing** from a Best Effort publisher, silently.

| Best Effort topic | Subscriber | Match |
| --- | --- | --- |
| `/ouster/points` | `kiss_icp_node` | ✅ |
| `/ouster/imu` | `graph_frontender` | ✅ `qos_profile_sensor_data` |
| `/insta360/imu/data_raw` | `graph_frontender`, `imu_filter` | ✅ |

**All compatible as configured.** The Ouster's Best Effort comes from
`use_system_default_qos: false` in `ibex_ouster_sensor_config.yaml`, whose own comment
flags that bag recording wants the opposite — relevant for
[bag-schema.md](bag-schema.md).

## Open items

| Item | |
| --- | --- |
| **Rates unmeasured — bench pass** | 12 topics, any time |
| **Rates unmeasured — field pass** | `/gps_values`, `/kairos_values`, `/vehicle_control`. Needs outdoors, engine running, operator on the sticks |
| **`graph_frontender` running twice** | Two estimators on one topic |
| **`spectra_combiner` running twice** | Duplicate spectra into the correction |
| **`kiss_icp_node` sim-time with no clock** | Low priority — stamps verified correct, but `now()` is pinned at zero |
| **Nothing consumes `/graph_pose`** | The subsystem's output is unread |
| **`imu_filter`'s `/tf` frames unrecorded** | Second dynamic TF publisher |

## Related

- [tf-frames.md](tf-frames.md) — the transform tree
- [launch-files.md](launch-files.md) — what starts each node
- [network.md](network.md) — the transport beneath
- [bag-schema.md](bag-schema.md) — what to record
