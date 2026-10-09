---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# kiss-icp

The lidar odometry front end. Serves [State estimation](../README.md).

Registers successive Ouster point clouds against a local map to estimate vehicle motion,
and publishes the dynamic `odom` → `base_link` transform — **the only thing on IBEX that
tracks the vehicle moving through the world.**

## Source

| | |
| --- | --- |
| Upstream | <https://github.com/PRBonn/kiss-icp> — `main` branch |
| In this repo | `packages/kiss-icp` — git submodule |
| Licence | MIT |
| Authors | Photogrammetry and Robotics Lab, University of Bonn |

The submodule directory is `kiss-icp` with a hyphen; the ROS package inside it is
`kiss_icp` with an underscore.

## Fork status

**Not a fork.** The submodule points directly at `PRBonn/kiss-icp`, unlike the three
RIVeR-Lab forks elsewhere in `packages/`.

That is deliberate and worth preserving: nothing IBEX-specific lives inside this
submodule. All integration — the topic, the frames, the launch arguments — is supplied
from outside, and the Ouster-side workaround it depends on lives in `ibex_bringup`'s driver
config. So the pin can be advanced from upstream without merge work.

## Description

Scan-to-map ICP. Each new point cloud is aligned to a voxelized local map; the
transformation required to make them match is the motion estimate.

The name is *Keep It Small and Simple*, and the design philosophy is the point: it uses
classic point-to-point ICP with no normals, derives its correspondence threshold from the
estimated motion rather than from a tuned parameter, and runs on a single CPU with no GPU
and essentially no configuration.

## Capabilities

- **Lidar-only odometry** — no IMU, GPS, or wheel encoders required
- **Point-to-point ICP** against a voxelized local map, no point-to-plane, no normals
- **Adaptive correspondence threshold**, computed from estimated motion rather than tuned
- **Constant-velocity motion model**, used as the ICP initial guess and for deskewing
- **Motion compensation (deskewing)** for point distortion during a sweep — **currently
  disabled on IBEX**, see [Known issues](#deskewing-is-disabled)
- **Adaptive voxel-grid downsampling** for speed
- **Bounded local map** — spatially cropped around the current pose rather than a growing
  global map
- **Sensor-agnostic** across lidar types and mounting positions
- **Publishes odometry and TF**, online from a topic or offline from a bag

## Purpose

IBEX has **no wheel encoders** and only a consumer-grade IMU, so lidar odometry is the
primary source of motion estimation. Everything else either drifts faster or only bounds
the drift.

Its output becomes relative-pose factors in the GTSAM factor graph in
[`ibex_state`](ibex-state.md), where it is fused with IMU preintegration and GPS into a
single optimized, drift-corrected pose with covariance.

## Alternative software

Three were considered:

| Alternative | |
| --- | --- |
| LIO-SAM | Tightly coupled lidar-inertial |
| FAST-LIO / FAST-LIO2 | Tightly coupled, filter-based |
| DLIO — Direct LiDAR-Inertial Odometry | Tightly coupled |

**KISS-ICP was chosen because it is loosely coupled.** It is a black box producing
frame-to-frame transforms, which drop straight into GTSAM as relative-pose factors
alongside GPS and IMU. The alternatives all fuse inertial data internally, which would
have meant either duplicating that fusion in the graph or giving up the graph's ability to
weight the sources itself.

The trade is that KISS-ICP cannot use the IMU to help its own registration, so it is
weaker in geometrically degenerate environments than a tightly coupled method would be.

## Launch / invocation

Standalone, for debugging:

```bash
ros2 launch kiss_icp odometry.launch.py topic:=/ouster/points
```

In the IBEX stack it is included from a launch file rather than run directly:

```python
kiss_icp_launch = IncludeLaunchDescription(
    PythonLaunchDescriptionSource(
        PathJoinSubstitution([FindPackageShare("kiss_icp"), "launch", "odometry.launch.py"])
    ),
    launch_arguments={
        "topic": "/ouster/points",
        "base_frame": "base_link",
        "lidar_odom_frame": "odom",
        "visualize": "False",
    }.items(),
)
```

> TODO(verify): that snippet is recorded as coming from a `processing.launch.py`, which is
> not in any file listing gathered so far. Establish which package holds it —
> `ibex_bringup` or `ibex_state` — and record it in
> [launch-files.md](../../../05-reference/launch-files.md).

**Preconditions:**

- The Ouster driver running and publishing `/ouster/points`
- A connected TF path from `base_link` to `os_lidar` — see [Frames](#frames)
- The driver's `min_scan_valid_columns_ratio` set above zero, or this node will crash —
  see [Known issues](#nan-crashes-on-empty-scans)

## Parameters

**The parameter names are version-specific.** Check what your build actually exposes
before assuming:

```bash
ros2 param list /kiss_icp_node
```

Launch arguments, from `ibex_bringup/config/kiss_icp_config.yaml`:

| Parameter | Value |
| --- | --- |
| `topic` | `/ouster/points` |
| `base_frame` | `base_link` |
| `lidar_odom_frame` | `odom` |
| `visualize` | `false` |

Pipeline parameters, from `ibex_bringup/config/kiss_icp_processing_config.yaml`:

| Group | Parameter | Value |
| --- | --- | --- |
| `data` | `deskew` | **`false`** — see [Known issues](#deskewing-is-disabled) |
| `data` | `max_range` | 100.0 m |
| `data` | `min_range` | **0.0 m** — no self-return filtering |
| `mapping` | `voxel_size` | 1.0 m |
| `mapping` | `max_points_per_voxel` | 20 |
| `adaptive_threshold` | `initial_threshold` | 2.0 |
| `adaptive_threshold` | `min_motion_th` | 0.1 |
| `registration` | `max_num_iterations` | 500 |
| `registration` | `convergence_criterion` | 0.0001 |
| `registration` | `max_num_threads` | 0 — all available |

**`max_range` is 100 m here against the Ouster driver's 1000 m**, so the driver passes
everything through and KISS-ICP does the cropping.

**`min_range: 0.0` means nothing excludes returns from the vehicle's own structure**, and
the driver sets no `mask_path` either. The geometry suggests the rack sits outside the
beam fan — the whole field of view is below horizontal and the hood falls below the bottom
beam — but that is inference.

> TODO(verify): look at a cloud within 2 m of the sensor and confirm no self-returns. In
> scan-to-map ICP a stationary self-return is a strong anchor pulling the estimate toward
> "not moving", so this is worth ten seconds in RViz.

> **There is no `odom_frame` parameter in this version.** It is `lidar_odom_frame`.
> `ros2 param get /kiss_icp_node odom_frame` returns "Parameter not set", which reads like
> a misconfiguration and is not one.

> TODO(verify): record the installed KISS-ICP version or submodule commit alongside these
> names, so the next person can tell whether a mismatch is a version difference or a
> mistake.

## Topics

| Topic | Type | Direction |
| --- | --- | --- |
| `/ouster/points` | `sensor_msgs/PointCloud2` | sub |
| Odometry output | `nav_msgs/Odometry` | pub |
| `/tf` | `tf2_msgs/TFMessage` | pub — `odom` → `base_link` |

> TODO(verify): record the exact odometry topic name and its QoS. The Ouster publishes
> `/ouster/points` as **best effort**, so this node's subscription must match or it will
> silently receive nothing — see
> [ouster-ros.md](../../perception/software/ouster-ros.md#best-effort-is-not-a-mistake-but-it-has-a-consequence).

## Frames

This is where getting KISS-ICP working actually happens, and the failure modes are
non-obvious.

### Static versus dynamic

| | Describes | Published by |
| --- | --- | --- |
| **Static** | Rigid sensor mounting offsets: `base_link` → `front_bumper` → `sensor_rack` → `os_mount` → `os_sensor` | `ibex_bringup` |
| **Static** | `os_sensor` → `os_lidar` and `os_sensor` → `os_imu` | **The Ouster driver itself** |
| **Dynamic** | `odom` → `base_link` | **KISS-ICP** |

**Only the dynamic edge localizes the vehicle.** The static tree describes where the
sensors are bolted; it never says where the vehicle is.

> **The key insight from debugging this:** a mis-rooted or disconnected static tree does
> not *force* the cloud to stay still in RViz. A frozen cloud is an **absence** — with no
> dynamic `odom` → `base_link` edge there is no world frame to accumulate scans in, so
> nothing moves.

### The frame-name trap

Ouster point clouds are stamped `frame_id = os_lidar`:

```bash
ros2 topic echo /ouster/points --field header.frame_id --once   # -> os_lidar
```

KISS-ICP needs a TF path from `base_link` to `os_lidar`. **Do not satisfy that by renaming
the static leaf to `os_lidar`.** The Ouster driver already publishes
`os_sensor` → `os_lidar`; publishing `os_mount` → `os_lidar` as well **splits the tree
into two disconnected trees**, with the error *"not part of the same tree"*.

**Correct:** the static leaf ends at `os_mount` → `os_sensor`, and the driver's
`os_sensor` → `os_lidar` connects the rest. `os_lidar` becomes reachable from `base_link`
automatically.

### Why base_link sits at the rear axle, on the ground

Per REP-105, and for two concrete reasons:

**The rear axle is the kinematic centre of an Ackermann vehicle.** Its centre traces the
true path through a turn with no sideslip. A frame at the front bumper would swing through
an arc during turns and corrupt the odometry.

**On the ground gives a clean z = 0 datum**, so terrain and obstacle heights are positive
and the frame aligns with gravity-referenced `odom` and `map`.

`base_link` is virtual — nothing physical sits there.

The full tree, the measured extrinsics and their derivation live in
[tf-frames.md](../../../05-reference/tf-frames.md).

## Diagnostics

In order. Each step rules out the one before it.

```bash
# 1. What frame are the clouds stamped with?
ros2 topic echo /ouster/points --field header.frame_id --once    # -> os_lidar

# 2. Is the cloud streaming at all?
ros2 topic hz /ouster/points                                      # ~10-20 Hz

# 3. Is the TF tree connected?  (writes frames.pdf)
ros2 run tf2_tools view_frames

# 4. Does base_link reach the lidar frame?
ros2 run tf2_ros tf2_echo base_link os_lidar                      # must resolve

# 5. The definitive test: is odom->base_link updating as the vehicle drives?
ros2 run tf2_ros tf2_echo odom base_link                          # translation grows

# 6. Confirm the parameters
ros2 node list | grep -i kiss
ros2 param get /kiss_icp_node lidar_odom_frame
ros2 param get /kiss_icp_node base_frame
ros2 param get /kiss_icp_node publish_odom_tf
```

### Reading step 5

| Observation | Meaning |
| --- | --- |
| Startup warning *"frame odom does not exist"* | **Timing only.** tf2 is waiting for the first transform. Ignore it if data follows |
| Parked, translation jitters ~3 cm | Normal registration noise. Working correctly |
| Driving, translation grows to metres and traces the path | Working correctly |
| Driving, translation stays ~3 cm | **Real tracking failure.** Check the input topic, the range parameters, or whether the environment is too featureless |

### In RViz

**Set Fixed Frame to `odom`.** This is the critical setting, and getting it wrong produces
the same symptom as a broken transform.

| Display | Expected |
| --- | --- |
| `PointCloud2` on `/ouster/points`, Decay Time a few seconds | A trail of accumulated geometry building a map as the vehicle drives — not pinned to the start |
| `Odometry` on the KISS-ICP topic | A growing chain of arrows tracing the trajectory. Raise `Keep` for a longer trail. Parked gives one jittering arrow |
| `TF` | Frames translating through the odom world |

**Cross-check:** the odometry arrow trail and the accumulated cloud should describe the
same path. If they disagree, something is wrong with the extrinsics rather than with the
odometry.

**Failure signature:** the cloud frozen in the starting area, not following the vehicle,
staying put when driving away and back. That was the original bug — no dynamic `odom`
edge, or the wrong fixed frame.

## Known issues & fixes

### use_sim_time is true with no clock source

`ros2 param get /kiss_icp_node use_sim_time` returns **True**, and **nothing publishes
`/clock`**. The node and its internal transform listener are the only `/clock` subscribers
on the vehicle, and there are zero publishers.

**Cause:** upstream's `odometry.launch.py` defaults `use_sim_time` to true, because
KISS-ICP is commonly run against recorded bags. That default is wrong for live sensors.

**Checked, and the impact is limited.** The published odometry carries a real wall-clock
stamp:

```bash
ros2 topic echo /kiss/odometry --field header.stamp --once
# sec: 1791505416   -> a real time, not zero
```

So **KISS-ICP stamps from the input cloud rather than from its own clock.** The Ouster's
`TIME_FROM_ROS_TIME` stamp passes through intact, and the lidar residual timestamps
reaching the factor graph are correct. The graph output is not corrupted.

**What is still wrong:**

| | |
| --- | --- |
| The node's `now()` is pinned at zero | Anything added later that stamps from the clock will silently produce zeros |
| Its tf2 buffer runs on a clock that never advances | Time-based transform lookups may behave oddly; `Time()` "latest available" lookups are unaffected |
| It is inconsistent with every other node | No other node on the vehicle is in sim-time mode |

> TODO(verify): confirm the TF broadcast is also stamped from the cloud rather than from
> `now()`. `ros2 run tf2_ros tf2_echo odom base_link` resolving normally is sufficient
> evidence.

**Fix:** add `use_sim_time: false` under `kiss_icp_node: ros__parameters:` in
`kiss_icp_processing_config.yaml`, which is already the node's parameter source. `/clock`
should then disappear from `ros2 topic list` entirely.

**Priority: low but worth doing.** It is a latent trap rather than an active fault — the
kind of thing that costs an afternoon when someone later adds a timer to this node and
cannot work out why it never fires.

### NaN crashes on empty scans

**Symptom:** KISS-ICP crashes, apparently at random, on live lidar data.

**Cause, traced in gdb:** a NaN inside the motion calculation during deskewing. The source
was **empty lidar scans** — scans in which no points carried valid data. With no motion to
compute, a time delta of zero led to a division producing NaN.

**Two fixes, both installed:**

1. **Driver-side, the real fix.** The Ouster driver is told to skip scans with too few
   valid points, by setting `min_scan_valid_columns_ratio` to 0.1 instead of the upstream
   default of 0.0. See
   [ouster-ros.md](../../perception/software/ouster-ros.md#parameters).
2. **Node-side, as a backstop.** Deskewing disabled — see below.

> This explains why that Ouster parameter matters, which was previously recorded only as
> "prevents errors in KISS-ICP calculations."

### Deskewing is disabled

Deskewing corrects for the distortion caused by the sensor moving during a single sweep.
It is **off** on IBEX, as the backstop fix for the NaN crash above.

**Consequence:** points within one scan are treated as simultaneous when they were not.
At 10 Hz, a full rotation takes 100 ms, so a vehicle at 5 m/s moves half a metre during
one sweep. That distortion is now uncorrected.

> TODO(verify): **re-enable deskewing and confirm the driver-side fix alone is
> sufficient.** The original note flags this as a possible accuracy problem, and it is the
> more likely of the two fixes to matter at speed. The driver-side skip addresses the root
> cause; deskewing was disabled before that was understood.
>
> Expect the error to grow with vehicle speed, so a comparison is best done driving rather
> than parked.

### Upstream requires CMake 3.24

**Symptom:** the build fails on KISS-ICP's `CMakeLists.txt`, which requires CMake 3.24 or
newer.

**Cause:** Ubuntu 22.04 ships CMake 3.22.1.

**Fix:** install a newer CMake. The two versions coexist.

> TODO(verify): record which CMake version is installed and how it was obtained, in
> [workstation-setup.md](../../../00-onboarding/workstation-setup.md). This is a
> prerequisite that will stop a fresh clone from building and is currently documented
> nowhere in the setup procedure. "The versions can live side by side now, but this might
> be a problem in the future" is the original note's own caveat.

### Build and launch notes

**Use `colcon build --symlink-install`.** Launch files, YAML, and Python nodes then become
live-editable with no rebuild between changes. Without it, `ros2 launch` reads from
`install/` rather than `src/`, so edits to launch files have no effect until a rebuild —
which is a confusing failure mode.

`source install/setup.bash` is still needed in each new terminal.

**Each `static_transform_publisher` needs a unique `name=`.** Duplicate node names cause
undefined behaviour, and the static tree uses several.

## Dependencies

**Ibex packages**

- `ibex_bringup` — publishes the static transform chain this node needs, and holds the
  Ouster driver config carrying the `min_scan_valid_columns_ratio` workaround

**Consumed by**

- [`ibex_state`](ibex-state.md) — takes the relative pose estimates as graph factors

**External**

- Upstream KISS-ICP build dependencies
- **CMake 3.24 or newer**, which Ubuntu 22.04 does not ship

**Hardware that must be powered**

- The Ouster OS1-64, from the Compute and Sensing box

## Understanding the software

**It is deliberately a black box.** That is why it was chosen — a frame-to-frame transform
with no internal fusion is exactly what a factor graph wants as an input. Resist adding
IMU or GPS awareness to it; that belongs in
[`ibex_state`](ibex-state.md).

**The local map is bounded, not global.** It crops spatially around the current pose, so
memory and compute stay flat over a long run and there is no loop closure. Loop closure, if
ever wanted, is the back end's job.

**Adaptive thresholding is why it needs no tuning.** The ICP correspondence threshold is
derived from the estimated motion each iteration rather than configured, which is the main
reason this runs out of the box on a new platform.

**The constant-velocity model does double duty** — as the ICP initial guess and as the
basis for deskewing. That coupling is why disabling deskewing does not disable the motion
model.

## Related pages

- [State estimation overview](../README.md) — the pipeline and the clock problem
- [ibex-state.md](ibex-state.md) — the factor graph consuming this node's output
- [ouster-ros.md](../../perception/software/ouster-ros.md) — the driver, its QoS, and the
  `min_scan_valid_columns_ratio` workaround
- [ouster-os1-64.md](../../perception/hardware/ouster-os1-64.md) — the sensor
- [tf-frames.md](../../../05-reference/tf-frames.md) — the full frame tree and extrinsics
- [launch-files.md](../../../05-reference/launch-files.md) — where this is included from
- [workstation-setup.md](../../../00-onboarding/workstation-setup.md) — the CMake
  requirement
