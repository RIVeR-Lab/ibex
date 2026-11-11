---
status: draft
owner: TODO(verify)
last-verified: 2026-11-10
---

# RTAB-Map

Lidar-only SLAM. **This is IBEX's state estimation**, as of 27 October 2026 — it replaced
the GTSAM factor graph in [`ibex_state`](ibex-state.md), which is no longer launched.
Serves [State estimation](../README.md).

It runs alongside [KISS-ICP](kiss-icp.md), which stays in the stack as a second,
comparable odometry estimate.

Two nodes: `icp_odometry` produces `odom → base_link`, and `rtabmap` adds loop closure and
produces `map → odom`.

> **`-d` on the `rtabmap` node deletes `~/.ros/rtabmap.db` on every launch.** The launch
> file's own first comment says so. **No map survives a restart** — see
> [The database is wiped every launch](#the-database-is-wiped-every-launch).

## Source

| | |
| --- | --- |
| Upstream | `rtabmap_ros` — `rtabmap_odom` and `rtabmap_slam` |
| Launch file | **`ibex_state/launch/rtabmap.launch.py`** |
| Config | **`ibex_state/config/rtabmap_config.yaml`** |
| In our repo | Launch and config only; the packages are installed |
| Started by | **`system_bringup` → `processing.launch.py`** |

**The launch and config live in `ibex_state`**, which now hosts RTAB-Map rather than the
factor graph it replaced.

### It replaced graph_frontender

`processing.launch.py` carries the change explicitly:

```python
# DEPRECATED: 27 Oct 26, replaced with RTAB Map
# graph_frontender_launch = IncludeLaunchDescription(...)
```

**The GTSAM factor graph is commented out and no longer runs.** Everything
[ibex-state.md](ibex-state.md) documents — the fixed-lag smoother, the two IMU
preintegration pipelines, the GPS factor, the latent drift and gravity-align chains — is
out of the stack. It is kept for reference and is worth reviving only deliberately.

## This is the first `map` frame on the vehicle

Before RTAB-Map there was no `map` frame at all. There is now, and the tree changed shape:

```
map
 └─ odom                       ~20 Hz · rtabmap
     └─ base_link              ~10 Hz · icp_odometry
         ├─ kiss_odom          ~10 Hz · KISS-ICP, INVERTED
         └─ front_bumper       static
             └─ sensor_rack
                 ├─ os_mount → os_sensor → os_lidar, os_imu
                 └─ insta_mount → insta_sensor → insta_imu
```

### odom is unambiguous

Because `processing.launch.py` always starts RTAB-Map, **`odom` always means
`icp_odometry`'s frame and KISS-ICP is always `kiss_odom`.** There is no configuration in
which the two swap.

### KISS-ICP now publishes the inverse

**`base_link → kiss_odom`, not `kiss_odom → base_link`.**

A TF frame can have exactly one parent, and `base_link`'s parent is now `odom` from
`icp_odometry`. So KISS-ICP attaches its own odometry frame as a **child** of `base_link`
instead, broadcasting the inverse of its estimate. That is the standard way to publish a
second odometry estimate without breaking the tree, and KISS-ICP's wrapper has an option
for it.

**Nothing is lost.** tf2 traverses edges in either direction:

```bash
ros2 run tf2_ros tf2_echo kiss_odom base_link   # KISS-ICP's estimate
ros2 run tf2_ros tf2_echo odom base_link        # rtabmap's ICP odometry
```

That makes the two directly comparable while driving, which is the point of running both.

> TODO(verify): `ibex_bringup/config/kiss_icp_config.yaml` previously set
> `lidar_odom_frame: odom`. It must now be `kiss_odom`, with the inversion enabled.
> **Confirm and record both**, and update
> [kiss-icp.md](kiss-icp.md#parameters).

> `ibex_state`'s config comment — *"raw odom (matching `ibex_bringup`'s `kiss_icp`
> `lidar_odom_frame` exactly)"* — no longer holds, since that frame is now `kiss_odom`.
> Moot while the node is deprecated, but it must be fixed before reviving it.

### Expected rates

| Edge | Rate | Why |
| --- | --- | --- |
| `map → odom` | ~20 Hz | rtabmap rebroadcasts the latest correction every 50 ms, even though graph optimization runs at 1 Hz |
| `odom → base_link` | ~10 Hz | One per Ouster scan |
| `base_link → kiss_odom` | ~10 Hz | One per Ouster scan |

**The 10000 Hz entries in `view_frames` are not real rates** — that is how it displays
static transforms.

> `view_frames` cannot tell you which node owns an edge; in ROS 2 every broadcaster shows
> as `default_authority`. Use `ros2 topic info /tf --verbose` to get the actual publishers.

## Launch

```bash
ros2 launch ibex_state rtabmap.launch.py
```

Both nodes run in the `/rtabmap` namespace with `--log-level warn`, and both remap
`scan_cloud` to the lidar topic read from the config's `ibex_launch` section — topic remaps
cannot be ROS parameters, so the launch file parses them out of the YAML itself.

## Configuration

`rtabmap_config.yaml`. RTAB-Map's internal parameters use `Group/Name` keys and are read
as strings, so **they must stay quoted.**

### Shared

| Parameter | Value | |
| --- | --- | --- |
| `frame_id` | `base_link` | |
| `qos` | **2 — best effort** | Matches the Ouster's publisher |
| `wait_for_transform` | 0.2 | |
| `Icp/PointToPlane` | `true` | |
| `Icp/Iterations` | `10` | |
| `Icp/VoxelSize` | `0.5` | **ICP downsampling only, not map resolution** |
| `Icp/MaxCorrespondenceDistance` | `5.0` | Rule of thumb: 10 × voxel size |
| `Icp/MaxTranslation` | `3` | Rejects ICP jumps over 3 m |
| `Icp/Strategy` | `1` | libpointmatcher rather than PCL |
| `Icp/OutlierRatio` | `0.7` | |

**The QoS choice is correct and non-obvious.** `/ouster/points` is best effort; a reliable
subscriber would receive nothing, silently.

> **If you change `Icp/VoxelSize`, change `Icp/MaxCorrespondenceDistance` with it.** The
> config says so and the ratio matters.

### icp_odometry

| Parameter | Value | |
| --- | --- | --- |
| `odom_frame_id` | `odom` | |
| `expected_update_rate` | 15.0 | Slightly above the Ouster's 10 Hz |
| `deskewing` | **false** | Constant-velocity deskew, and there is no IMU in this path |
| `Odom/ScanKeyFrameThr` | `0.4` | New keyframe below 40% overlap |
| `OdomF2M/ScanMaxSize` | `15000` | |
| `scan_cloud_max_points` | 65536 | 1024 × 64, the Ouster's full scan |

**Deskewing is off in both odometry systems.** KISS-ICP's is disabled as a workaround for
a NaN crash; RTAB-Map's is off because there is no IMU wired into its pipeline. Different
reasons, same consequence — at 10 Hz a vehicle at 5 m/s moves half a metre per sweep, and
neither system corrects for it.

### rtabmap

| Parameter | Value | |
| --- | --- | --- |
| `map_frame_id` | `map` | |
| `subscribe_scan_cloud` | true | Lidar-only — depth and RGB are off |
| `subscribe_odom_info` | true | |
| `Reg/Strategy` | `1` | ICP registration for loop closures |
| `RGBD/LinearUpdate` | `0.05` | New graph node every 5 cm… |
| `RGBD/AngularUpdate` | `0.05` | …or 0.05 rad |
| `RGBD/CreateOccupancyGrid` | **false** | No occupancy grid produced |
| `Mem/STMSize` | `30` | Last 30 nodes excluded from loop closure |
| `Icp/CorrespondenceRatio` | `0.2` | Loop closures need ≥20% overlap |

`Grid/CellSize` is present but commented out, so no OctoMap voxel size is set.

> A graph node every 5 cm is dense. Combined with `Mem/NotLinkedNodesKept: false` it keeps
> the graph bounded, but it is worth knowing when reading memory or CPU figures.

## Known issues

### The database is wiped every launch

`-d` is passed to the `rtabmap` node, which **deletes `~/.ros/rtabmap.db` on startup.**

**Consequence:** no map, no graph, and no loop-closure history survives a restart. Mapping
is per-session only, and a crash loses everything.

That is a reasonable default while developing — every run starts clean and comparable — but
it is the opposite of what a SLAM system is for, and the flag is easy to miss.

**This matters more now that RTAB-Map is the estimator**, not an experiment running
alongside one.

> TODO(verify): decide whether this stays. If maps should persist, drop `-d` and manage
> the database deliberately. If it stays, **say so in
> [data-collection.md](../../../02-operations/data-collection.md)** so nobody expects a map
> to be there afterwards.

### Two ICP systems on every scan

Both `icp_odometry` and KISS-ICP run ICP on every **65,536-point** cloud, on the same
machine.

**Ouster frame drops have been observed during bagging.** The Ouster driver already had a
packet-drop problem traced to excess work in a single-threaded pipeline stage — fixed by
disabling unused processing outputs. Two ICP pipelines plus a bag writer is a plausible
way to reintroduce pressure from a different direction.

> TODO(verify): measure it. Compare `/ouster/points` message counts with one odometry
> system running against both, while bagging. If running both costs scans, that is a real
> trade rather than a free comparison. See
> [ouster-ros.md](../../perception/software/ouster-ros.md) and
> [bag-schema.md](../../../05-reference/bag-schema.md).

> Volta has 16 cores and an idle RTX 4070, so there is headroom — but the Ouster driver's
> bottleneck was a single thread, not total CPU.

### Reading a parked `tf2_echo`

`odom → base_link` staying within about 1 mm and a few thousandths of a degree of identity
is **normal ICP jitter on a stationary scan.**

**If the vehicle was moving and it still reads near identity, `icp_odometry` is not
tracking.** The `frame does not exist` message at startup is harmless — `tf2_echo` begins
before its buffer fills.

## Why it replaced the factor graph

RTAB-Map brings **loop closure and a `map` frame**, which the GTSAM graph never had —
`ibex_state` did dead reckoning and sensor fusion with no global correction, and KISS-ICP
keeps a bounded local map with no graph at all.

The trade is what the factor graph offered and this does not: **two IMUs, GPS, and a
vehicle motion model**, all fused with explicit covariance. RTAB-Map here is lidar-only —
no IMU, no GNSS, no dynamics. See
[ibex-state.md](ibex-state.md).

> TODO(verify): whether GPS and IMU return. RTAB-Map accepts both, and `/gps_values` and
> two IMU topics are already published. Without them there is nothing to bound drift
> between loop closures, and no absolute position at all.

**RTAB-Map is the estimator now.** KISS-ICP remains for comparison, and nothing consumes
its `/kiss/odometry` topic since `graph_frontender` was deprecated.

> TODO(verify): decide whether KISS-ICP stays. It costs a second ICP pass on every 65k
> point cloud and currently feeds nothing — see
> [Two ICP systems on every scan](#two-icp-systems-on-every-scan). Keeping it as a
> comparison is defensible; keeping it by inertia is not.

## Related pages

- [kiss-icp.md](kiss-icp.md) — the other odometry front end
- [ibex-state.md](ibex-state.md) — the factor graph, which consumes neither of RTAB-Map's
  outputs
- [tf-frames.md](../../../05-reference/tf-frames.md) — the tree, now with `map`
- [ouster-ros.md](../../perception/software/ouster-ros.md) — the shared input and its QoS
- [launch-files.md](../../../05-reference/launch-files.md) — not part of `system_bringup`
