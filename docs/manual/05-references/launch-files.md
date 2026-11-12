---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Launch files

Every launch file on IBEX, what it starts, and what it takes as arguments.

**Reference page.** For the procedure see
[running-the-system.md](../02-operations/running-the-system.md); for what each node does
see the subsystem pages.

## The hierarchy

`ibex_bringup` is the top of the tree. It owns no nodes of its own except the static
transform publishers — everything else is an `IncludeLaunchDescription` into another
package.

```
ibex_bringup/system_bringup.launch.py
 ├── static_tf.launch.py          ibex_bringup   → 7 static_transform_publisher nodes
 ├── sensors.launch.py            ibex_bringup
 │    ├── insta360_ros_driver/insta_bringup.launch.py
 │    └── ouster_ros/driver.launch.py
 ├── processing.launch.py         ibex_bringup
 │    ├── kiss_icp/odometry.launch.py
 │    └── ibex_state/rtabmap.launch.py        ← replaced graph_frontender
 └── control.launch.py            ibex_bringup
      └── shared_link_bridge/bringup.launch.py
```

**That is the whole vehicle except the hyperspectral payload** — see
[What system_bringup does not start](#what-system_bringup-does-not-start).

## system_bringup.launch.py

```bash
ros2 launch ibex_bringup system_bringup.launch.py
```

**It sets the Fast DDS profile before anything else**, and that ordering is load-bearing:

```python
ld.add_action(SetEnvironmentVariable("FASTRTPS_DEFAULT_PROFILES_FILE", fastdds_profile))
```

Environment changes apply only to processes started *after* them, and every included
launch file inherits this one's environment — so the `SetEnvironmentVariable` must precede
every include.

| | |
| --- | --- |
| Argument | `fastdds_profile` |
| Default | `ibex_bringup/config/fastdds_large_msgs.xml` |
| Passed down to | `sensors.launch.py` explicitly |

**Why it is here rather than in `~/.bashrc`:** what matters is the *publishing process's*
environment, and a launch started from a script, a service, or a non-interactive shell
never loads `~/.bashrc`.

> **Without the profile, the publisher falls back to UDP loopback and best-effort topics
> silently lose whole messages — about 60% of Ouster scans in testing.** Fast DDS's default
> shared-memory segment is 512 kB; an Ouster cloud is ~3 MB and a decoded Insta360 frame
> ~12 MB. See [compute.md](compute.md).

Four sub-launches, added in order, **with no delays between them**:

| Order | Sub-launch | Brings up |
| --- | --- | --- |
| 1 | `static_tf` | The frame tree |
| 2 | `sensors` | Insta360, Ouster |
| 3 | `processing` | KISS-ICP, **RTAB-Map** |
| 4 | `control` | `shared_link_bridge` |

**Nothing is staggered**, which works because the one node that needs ordering handles it
itself: `ibex_state` blocks on `base_link → os_imu` and retries indefinitely, since the
Ouster's lifecycle node can take over a minute to activate. See
[ibex-state.md](../04-subsystems/state-estimation/software/ibex-state.md).

It declares no launch arguments of its own, so the arguments exposed by `sensors.launch.py`
cannot be set through it.

> TODO(verify): whether that is intentional. Passing `equirectangular` and `imu_filter`
> through from the top would cost two `DeclareLaunchArgument` lines and make the system
> launch configurable without editing files.

## static_tf.launch.py

Seven `static_transform_publisher` nodes. **This is the authority for the frame tree** —
see [tf-frames.md](tf-frames.md) for the resulting geometry.

Arguments are positional: `x y z yaw pitch roll parent child`.

| Node name | Parent → child | x, y, z | yaw, pitch, roll |
| --- | --- | --- | --- |
| `base_to_bumper_static_tf` | `base_link` → `front_bumper` | 2.4638, 0, 0.5715 | 0, 0, 0 |
| `ouster_static_tf` | `front_bumper` → `sensor_rack` | −1.850, 0, 1.250 | 0, 0, 0 |
| `ouster_mount_static_tf` | `sensor_rack` → `os_mount` | 0.830, 0, −0.11 | 0, **0.391698**, 0 |
| `ouster_mount_to_lidar_static_tf` | `os_mount` → `os_sensor` | 0, 0, 0 | 0, 0, 0 |
| `insta360_static_tf` | `sensor_rack` → `insta_mount` | 0.650, 0, 0.20 | 0, 0, 0 |
| `insta360_to_sensor_static_tf` | `insta_mount` → `insta_sensor` | 0, 0, 0.13 | −1.5708, 0, −1.5708 |
| `insta360_imu_static_tf` | `insta_sensor` → `insta_imu` | 0, 0, 0 | 1.347411, −0.034602, −0.223388 |

Two of these rotations were **derived empirically from stationary accelerometer readings
against a known-level vehicle**, with the working recorded in `docs/ben_notes.md`:

**The Ouster's pitch**, 0.391698 rad — 22.44°. The previous 0.436 rad (25°) left about
2.6° of residual in the nose-up direction. **This supersedes the 25° figure used elsewhere
in the manual.**

**The Insta360's IMU rotation.** The IMU die is not axis-aligned with `insta_sensor`'s
optical-frame convention — roughly a 77° yaw offset rather than simple collocation. Roll
and pitch are pinned by the gravity measurement; **yaw about the gravity axis is
fundamentally unobservable from a single accelerometer reading**, so that value is a
working estimate rather than a verified measurement.

> `ouster_mount_to_lidar_static_tf` is named misleadingly — its child is `os_sensor`, not
> `os_lidar`, and it is an identity transform. `os_sensor → os_lidar` comes from the Ouster
> driver. The naming is correct in effect and confusing to read.

### There is unreachable code in this file

**The GPS transform is dead.** A `return ld` sits above the GPS section, so everything
after it never executes:

```python
    ld.add_action(insta360_imu_tf)

    return ld                        # ← execution ends here

    #=====# GPS #=====#
    gps_mount_tf = Node(...)         # ← never created
    ld.add_action(gps_mount_tf)      # ← never runs
```

**`base_link → gps_mount` at (0.70, 0.60, 0.85) is never published.**

> **This is deferred deliberately, not overlooked.** The GPS is not in its final
> mounting position, so the recorded offset would be wrong anyway. Move the `return ld`
> to the end of the function when the GPS is mounted.

> TODO(verify): once mounted, re-measure the offset and move the `return ld`. Note that nothing
> currently *consumes* `gps_mount` either — `ibex_state` applies no lever-arm correction to
> GPS fixes, treating them as taken at the vehicle origin. The recorded offset is
> **0.70 m forward and 0.60 m lateral**, which is a systematic position bias rather than
> noise. Fixing the dead code and applying the lever arm are two separate jobs; the first
> is one line.

## sensors.launch.py

| Argument | Default | Choices | Passed to |
| --- | --- | --- | --- |
| `equirectangular` | `true` | true, false | `insta360_ros_driver` |
| `imu_filter` | `true` | true, false | `insta360_ros_driver` |

| Sub-launch | Arguments |
| --- | --- |
| `insta360_ros_driver/insta_bringup.launch.py` | `equirectangular`, `imu_filter` |
| `ouster_ros/driver.launch.py` | `params_file`, `viz:=false` |

Config: `ibex_bringup/config/ibex_ouster_sensor_config.yaml` — this is where
`min_scan_valid_columns_ratio: 0.1` lives, which prevents KISS-ICP crashing on empty scans,
and where the unused processing outputs are disabled to stop packet drops. See
[ouster-ros.md](../04-subsystems/perception/software/ouster-ros.md).

> `imu_filter` defaults to `true`, which starts a Madgwick filter subscribed to a
> magnetometer nothing publishes. Since `ibex_state` consumes `/insta360/imu/data_raw`
> rather than the filter's output, **nothing uses what that filter produces.** Setting
> `imu_filter:=false` would remove a node and change nothing downstream. See
> [insta360-ros-driver.md](../04-subsystems/perception/software/insta360-ros-driver.md).

## processing.launch.py

| Sub-launch | Arguments |
| --- | --- |
| `kiss_icp/odometry.launch.py` | `topic`, `base_frame`, `lidar_odom_frame`, `visualize`, `config_file` |
| `ibex_state/rtabmap.launch.py` | none |

**`graph_frontender` was replaced here on 27 October 2026** and is commented out in place:

```python
# DEPRECATED: 27 Oct 26, replaced with RTAB Map
```

See [ibex-state.md](../04-subsystems/state-estimation/software/ibex-state.md) and
[rtabmap.md](../04-subsystems/state-estimation/software/rtabmap.md).

**KISS-ICP's arguments are read from YAML at launch time**, not hardcoded:

```python
config_path = .../ibex_bringup/config/kiss_icp_config.yaml
kiss_icp_cfg = yaml.safe_load(f)["kiss_icp"]
```

So `ibex_bringup/config/` holds two KISS-ICP configs with different jobs:

| File | Holds |
| --- | --- |
| `kiss_icp_config.yaml` | The launch arguments — topic, frames, visualize |
| `kiss_icp_processing_config.yaml` | Passed through as `config_file` — the pipeline tuning |

> **`kiss_icp_processing_config.yaml` is where deskewing is disabled**, along with max
> range and voxel size. That file has not been read yet and is worth recording in full —
> see [kiss-icp.md](../04-subsystems/state-estimation/software/kiss-icp.md#deskewing-is-disabled).

## control.launch.py

| Sub-launch | Arguments |
| --- | --- |
| `shared_link_bridge/bringup.launch.py` | `teleop_xterm` (default `true`) |

`bringup.launch.py` starts `joy_node`, `estop_beacon`, the bridge, and `controller_teleop`.
**`teleop_xterm:=false` leaves teleop out** so it can run in its own terminal — needed for
SSH or tmux sessions, since the curses TUI requires a real terminal:

```bash
ros2 launch shared_link_bridge bringup.launch.py teleop_xterm:=false   # pane 1
ros2 run shared_link_bridge controller_teleop.py                       # pane 2
```

The file is a thin wrapper, described in its own comment as "the single seam for the
vehicle-control subsystem" where future Kairos launch files get added.

### Two safety-relevant overrides are written but commented out

```python
# launch_arguments={
#     "estop_initial_state": "ESTOP",
#     "teleop_in_xterm": "true",
# }.items(),
```

with the note: *"Uncomment each once the matching `DeclareLaunchArgument` exists in
shared_link_bridge's launch file."*

**`teleop_xterm` was added in November 2026; `estop_initial_state` was not.** So the second
override is still blocked, and the first can now be uncommented.

**`estop_initial_state: "ESTOP"` is the fix for a known defect.** `estop_beacon.py`
initializes to RUN rather than ESTOP — the author's own comment flags it — so the vehicle's
software e-stop state comes up permissive. The system-level intent to force a safe initial
state exists here and **is blocked on a single `DeclareLaunchArgument` in the submodule.**

> TODO(verify): add `estop_initial_state` to `shared_link_bridge`'s `bringup.launch.py` and
> uncomment this. It is a small change in a forked submodule we control, and it closes the
> highest-priority item on
> [estop-chain.md](../01-safety/estop-chain.md).

## What system_bringup does not start

| Not included | Launch separately |
| --- | --- |
| Hyperspectral cameras and ambient correction | `hyper_drive` |
| Point spectrometers | `spectrometer_drivers` |
| SICK picoScan | No driver exists |
| Alvium RGB camera | Started by `hyper_drive`'s launch files |

**The hyperspectral payload is a separate stack.** Running a full sensing session means two
launches, not one, and the second brings up its own copy of the spectrometer nodes.

> TODO(verify): this is worth stating prominently in
> [running-the-system.md](../02-operations/running-the-system.md). It also means the
> hyperspectral cameras have no frames in the tree that `static_tf.launch.py` builds — see
> [tf-frames.md](tf-frames.md#no-camera-has-a-frame).

## Launch files elsewhere in the repo

### hyper_drive — five

| File | Starts |
| --- | --- |
| `ambient_light_launch.py` | **The full pipeline.** Spectrometers, Alvium, cubes, ambient correction, corrected visualizer |
| `synchronous_cameras_launch.py` | Alvium + both hyperspectral cameras + raw visualizer |
| `hyper_drive_launch.py` | IMEC only, single-camera path |
| `master_launch.py` | IMEC and Ximea in namespaces, plus GUI and combiner |
| `ambient_light_launch_old.py` | **Superseded. Starts two cube generators — do not use** |

> `ambient_light_launch.py` contains the entire spectrometer stack copied from
> `ibsen_launch.py`. **Running both duplicates the combiner** — see
> [spectrometer-drivers.md](../04-subsystems/perception/software/spectrometer-drivers.md).

### spectrometer_drivers — one

`ibsen_launch.py` — both streamers, the combiner, and the live plot. NIR is delayed 5 s
behind VNIR to avoid the FT4222 enumeration race.

### ibex_state — two

| File | Starts |
| --- | --- |
| `graph_frontender.launch.py` | One node, loading `graph_frontender_config.yaml`. No launch arguments |
| `rtabmap.launch.py` | `icp_odometry` and `rtabmap` in the `/rtabmap` namespace, loading `rtabmap_config.yaml` |

**`rtabmap.launch.py` is started by `system_bringup`**, through `processing.launch.py`.

> **It passes `-d` to the `rtabmap` node, which deletes `~/.ros/rtabmap.db` on every
> launch.** No map survives a restart — see
> [rtabmap.md](../04-subsystems/state-estimation/software/rtabmap.md#the-database-is-wiped-every-launch).

It also reads topic remaps out of its own YAML's `ibex_launch` section, because remaps
cannot be ROS parameters.

### Submodule launch files

Included rather than run directly: `shared_link_bridge/bringup.launch.py`,
`insta360_ros_driver/insta_bringup.launch.py`, `ouster_ros/driver.launch.py`,
`kiss_icp/odometry.launch.py`.

> TODO(verify): `shared_link_bridge/bringup.launch.py` and
> `insta360_ros_driver/insta_bringup.launch.py` have not been read. Both are forks we
> control, and the first is blocking the e-stop fix above.

## Config files

| File | Package | Holds |
| --- | --- | --- |
| `ibex_ouster_sensor_config.yaml` | `ibex_bringup` | Ouster driver params, incl. the two workarounds |
| `kiss_icp_config.yaml` | `ibex_bringup` | KISS-ICP launch arguments |
| `kiss_icp_processing_config.yaml` | `ibex_bringup` | KISS-ICP pipeline tuning |
| `graph_frontender_config.yaml` | `ibex_state` | The entire factor-graph configuration |
| `rtabmap_config.yaml` | `ibex_state` | RTAB-Map's ICP, odometry, and SLAM parameters |
| `fastdds_large_msgs.xml` | `ibex_bringup` | **The DDS profile**, set by `system_bringup` before every include |
| `allied_vision_config.xml` | **`~/`** | Alvium camera settings — **not in the repo** |

**The DDS profile is now in the repository and applied by the launch file**, which
supersedes the earlier `~/.bashrc` export and the copy under `insta360_ros_driver`. Only
the Alvium settings remain outside version control.

> TODO(verify): confirm whether `~/fastdds_ibex_config.xml`, the
> `insta360_ros_driver/config/` copy, and the `~/.bashrc` export have all been removed.
> **Multiple profiles with one environment variable is worse than none**, because which one
> applies depends on how the process was started.

## Open items

| Item | |
| --- | --- |
| **Dead GPS transform** | One misplaced `return ld` |
| **`estop_initial_state` override** | Blocked on one line in `shared_link_bridge` |
| **`kiss_icp_processing_config.yaml` unread** | Holds the deskew setting and range tuning |
| **`ibex_ouster_sensor_config.yaml` unread** | Holds both Ouster workarounds |
| **Two configs outside the repo** | Not version-controlled |
| **Hyperspectral stack not in `system_bringup`** | Two launches needed for a full session |

## Related

- [tf-frames.md](tf-frames.md) — the geometry `static_tf.launch.py` produces
- [running-the-system.md](../02-operations/running-the-system.md) — the procedure
- [ros-graph.md](ros-graph.md) — what the resulting nodes publish
- [estop-chain.md](../01-safety/estop-chain.md) — the commented-out override
- [ibex-state.md](../04-subsystems/state-estimation/software/ibex-state.md) — why nothing
  needs staggering
