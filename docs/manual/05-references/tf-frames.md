---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# TF frames

Every coordinate frame on IBEX, who publishes it, and the measured extrinsics between
them.

**Reference page.** For why `base_link` sits where it does, see
[kiss-icp.md](../04-subsystems/state-estimation/software/kiss-icp.md#frames); for what
breaks when the tree is wrong, see the same page's diagnostics.

> **The hyperspectral cameras have no frames**, and `aligned_odom` and `utm` are published
> as labels with no transform. See [Missing frames](#missing-frames).

## The tree

```
odom                                     ← KISS-ICP's world frame
 └── base_link                           ← rear axle centre, on the ground  [DYNAMIC]
      └── front_bumper
           └── sensor_rack
                ├── os_mount             ← the 22.44° tilt is applied here
                │    └── os_sensor       (identity)
                │         ├── os_lidar   ← point clouds are stamped with this
                │         └── os_imu
                └── insta_mount
                     └── insta_sensor    ← optical-frame convention
                          └── insta_imu  ← ~77° yaw offset, empirically derived
```

Everything below `base_link` is static. The single dynamic edge is `odom → base_link`.

**Only the dynamic edge localizes the vehicle.** The static tree describes where sensors
are bolted and never says where the vehicle is. A frozen point cloud in RViz is usually
this edge missing, not a bad extrinsic.

## Who publishes what

All static edges come from `ibex_bringup/launch/static_tf.launch.py` except the two the
Ouster driver supplies.

| Edge | Publisher | Type |
| --- | --- | --- |
| `odom → base_link` | **KISS-ICP** | Dynamic, `/tf` |
| `base_link → front_bumper` | `ibex_bringup` | Static |
| `front_bumper → sensor_rack` | `ibex_bringup` | Static |
| `sensor_rack → os_mount` | `ibex_bringup` | Static |
| `os_mount → os_sensor` | `ibex_bringup` | Static, identity |
| `os_sensor → os_lidar` | **The Ouster driver** | Static, `/tf_static` |
| `os_sensor → os_imu` | **The Ouster driver** | Static, `/tf_static` |
| `sensor_rack → insta_mount` | `ibex_bringup` | Static |
| `insta_mount → insta_sensor` | `ibex_bringup` | Static |
| `insta_sensor → insta_imu` | `ibex_bringup` | Static |

**The chain from `ibex_bringup` ends at `os_mount → os_sensor`**, an identity transform.
The driver supplies `os_sensor → os_lidar` and `os_sensor → os_imu` from there. See
[The frame-name trap](#the-frame-name-trap) for why that boundary matters.

Values below are read from the launch file. See
[launch-files.md](launch-files.md#static_tflaunchpy).

## Static transforms

Arguments in the launch file are positional: `x y z yaw pitch roll parent child`.

| Edge | x (m) | y (m) | z (m) | yaw | pitch | roll |
| --- | --- | --- | --- | --- | --- | --- |
| `base_link → front_bumper` | 2.4638 | 0 | 0.5715 | 0 | 0 | 0 |
| `front_bumper → sensor_rack` | **−1.850** | 0 | 1.250 | 0 | 0 | 0 |
| `sensor_rack → os_mount` | 0.830 | 0 | −0.11 | 0 | **0.391698** | 0 |
| `os_mount → os_sensor` | 0 | 0 | 0 | 0 | 0 | 0 |
| `sensor_rack → insta_mount` | 0.650 | 0 | 0.20 | 0 | 0 | 0 |
| `insta_mount → insta_sensor` | 0 | 0 | 0.13 | −1.5708 | 0 | −1.5708 |
| `insta_sensor → insta_imu` | 0 | 0 | 0 | **1.347411** | −0.034602 | −0.223388 |

### The Ouster tilt is 22.44°, not 25°

`0.391698 rad = 22.44°`, **derived empirically** from a stationary `os_imu` accelerometer
reading against a known-level vehicle. The working is in `docs/ben_notes.md`.

The previous value of 0.436 rad (25°) was a design assumption and left about **2.6° of
residual in the nose-up direction**.

> This supersedes every "25°" reference elsewhere in the manual, and it **changes the
> ground coverage figures materially** — see below.

### The Insta360 IMU yaw is a working estimate

`insta_sensor → insta_imu` carries a yaw of 1.347411 rad — **about 77°**. The IMU die is
not axis-aligned with `insta_sensor`'s optical-frame convention; it is genuinely rotated,
not merely collocated.

Roll and pitch are pinned by the gravity measurement that derived them. **Yaw about the
gravity axis is fundamentally unobservable from a single accelerometer reading**, so that
77° is a best working estimate rather than a verified physical measurement.

> TODO(verify): this matters for `ibex_state`, which uses this transform as the Insta360
> IMU's `body_P_sensor` for preintegration. A yaw error about gravity mixes the horizontal
> acceleration axes and the roll/pitch rate axes. Verifying it needs a motion that excites
> yaw — a slow, deliberate turn on level ground with both IMUs logged, compared against
> each other.

## Resulting sensor positions

Relative to `base_link` — rear axle centre, on the ground.

| Sensor | Forward (m) | Height (m) |
| --- | --- | --- |
| Front bumper | +2.4638 | 0.5715 |
| Sensor rack origin | +0.6138 | 1.8215 |
| **Ouster OS1-64** | **+1.4438** | **1.7115** |
| **Insta360 X4** | **+1.2638** | **2.1515** |

The Insta360 at 2.1515 m is the tallest point on the vehicle, which matches its hardware
page.

### Ouster ground coverage, recomputed

At 1.7115 m and 22.44°, with beam altitudes of +21.03° to −21.33°:

| Beam | Below horizontal | Ground range at 25° (superseded) | **At 22.44°** |
| --- | --- | --- | --- |
| Top, +21.03° | 1.41° | 24.7 m | **69.4 m** |
| Centre, 0° | 22.44° | 3.7 m | **4.1 m** |
| Bottom, −21.33° | 43.77° | 1.6 m | **1.8 m** |

**The far field changed by a factor of nearly three.** A 2.5° tilt error barely moves the
near beams and dominates the far ones, because ground range goes as `h/tan(θ)` and the top
beam is only 1.41° below horizontal.

> At 1.41° the top beam is grazing. Small changes in vehicle pitch — a slope, a load shift,
> suspension travel — move its ground intersection by tens of metres, or lift it off the
> ground entirely. Treat the 69 m figure as a level-ground ideal rather than a working
> number.

> TODO(verify): recompute the full beam-by-beam coverage table on
> [ouster-os1-64.md](../04-subsystems/perception/hardware/ouster-os1-64.md), which is still
> computed at 25°.

## base_link

**Rear axle centre, on the ground.** Per REP-105, and for two concrete reasons:

**The rear axle is the kinematic centre of an Ackermann vehicle.** Its centre traces the
true path through a turn with no sideslip. A frame at the front bumper would swing through
an arc during turns and corrupt the odometry.

**Ground level gives a clean z = 0 datum**, so terrain and obstacle heights are positive
and the frame aligns with gravity-referenced `odom` and `map`.

`base_link` is virtual — nothing physical sits there.

### Derivation

All four source measurements are clean imperial values:

| Measurement | Imperial | Metric |
| --- | --- | --- |
| Front bumper to leading edge of rear wheel | 84 in | 2.1336 m |
| Rear wheel radius | 13 in | 0.3302 m |
| **Rear axle behind front bumper** | **97 in** | **2.4638 m** |
| Front bumper height above ground | 22.5 in | 0.5715 m |
| Vehicle length, as measured | 118 in | 2.9972 m |

So `base_link → front_bumper` is `(+2.4638, 0, +0.5715)` with no rotation — the bumper is
2.4638 m forward of the axle and 0.5715 m off the ground.

### The vehicle length is recorded two ways

| Source | Length |
| --- | --- |
| This derivation, measured | **118 in / 2.9972 m** |
| [specifications.md](../03-base-vehicle/specifications.md), from the Yamaha spec | 122 in / 3.0988 m |

Four inches is beyond measurement slop. The two are probably measuring different things —
with and without a bumper guard or receiver hitch is the usual explanation.

| | Implied rear overhang |
| --- | --- |
| At 118 in | 21 in / 0.5334 m |
| At 122 in | 25 in / 0.6350 m |

> TODO(verify): resolve which is which. **The measured value is the one the extrinsics were
> derived from**, so if the 122 in figure is the correct bumper-to-bumper length, the
> transforms are still right and only the specification table needs a note.

### These measurements do not give the wheelbase

Only the **rear** axle was located. The front axle position was never measured, so the
wheelbase cannot be derived from anything on this page.

**That matters** because `ibex_state` configures `wheelbase: 1.2` with a TODO against it,
and the bicycle model's yaw rate scales as `1/L`. See
[ibex-state.md](../04-subsystems/state-estimation/software/ibex-state.md#the-wheelbase-is-a-placeholder).

> TODO(verify): measure front axle centre to rear axle centre and record it in
> [specifications.md](../03-base-vehicle/specifications.md). It is one tape measurement and
> it closes an open item in state estimation.

## Dynamic transforms

| Edge | Publisher | Rate | Notes |
| --- | --- | --- | --- |
| `odom → base_link` | KISS-ICP | Lidar rate, ~10 Hz | The only edge that moves |

KISS-ICP's relevant parameters, which are version-specific:

| Purpose | Parameter | Value |
| --- | --- | --- |
| Parent frame | `lidar_odom_frame` | `odom` |
| Child frame | `base_frame` | `base_link` |
| Broadcast the TF | `publish_odom_tf` | `True` |

> There is no `odom_frame` parameter in this version. Querying it returns "Parameter not
> set", which reads like a misconfiguration and is not one.

## Frames published as labels only

**These appear as `frame_id` strings on messages and have no entry in the transform tree.**

| Frame | Appears on | Published by |
| --- | --- | --- |
| `aligned_odom` | `/graph_pose` | `ibex_state` |
| `utm` | `/odom_offset` | `ibex_state` |

`ibex_state` creates a TF **listener** and no broadcaster.

**Consequence:** `tf2` lookups involving either frame fail, and RViz cannot use
`aligned_odom` as a fixed frame — despite it being the frame the fused pose estimate is
expressed in.

### What they mean

| Frame | |
| --- | --- |
| `odom` | KISS-ICP's lidar-odometry frame. Starts at an arbitrary, **not gravity-aware** identity. Used as `ibex_state`'s internal backbone frame and never published by it |
| `aligned_odom` | `odom` rotated in place about its own origin so +z is antiparallel to gravity. Yaw unchanged — gravity cannot observe it |
| `utm` | Universal Transverse Mercator. `odom_offset` gives the odom origin's easting, northing, and yaw within it. **SE(2) only** — GPS supplies no altitude or heading |

> TODO(verify): either broadcast `odom → aligned_odom` and `utm → odom`, or state
> explicitly that these are message-local labels. The first is a few lines and makes the
> estimator's output usable by standard tooling.

## Missing frames

### No camera has a frame

| Sensor | Frame |
| --- | --- |
| Ximea VNIR HSI | none |
| IMEC SWIR HSI | none |
| Alvium RGB | none |
| Insta360 X4 | `insta_sensor` ✅ |

The Insta360 has a full chain — `sensor_rack → insta_mount → insta_sensor → insta_imu`.
**The three hyperspectral-array cameras have nothing.**

`hyper_drive` publishes cubes with **`header.frame_id` unset entirely** — see
[hyper-drive.md](../04-subsystems/perception/software/hyper-drive.md#cubes-carry-no-frame_id).

**This is the concrete blocker on fusing spectral data with lidar geometry.** Three cameras
sit on one rack and nothing relates any of them to `base_link` or to each other.

> TODO(verify): measure each camera's position and orientation on the sensor rack and add
> `sensor_rack → <camera>` transforms. The two hyperspectral cameras need separate frames —
> they sit at opposite ends of the array.

### The GPS frame is dead code

`base_link → gps_mount` at (0.70, 0.60, 0.85) **is never published.** A misplaced
`return ld` in `static_tf.launch.py` sits above the GPS section, making it unreachable.

Nothing currently consumes it either — `ibex_state` applies no lever-arm correction and
treats GPS fixes as taken at the vehicle origin. So the 0.70 m forward and **0.60 m
lateral** offset is an unapplied systematic position bias.

> TODO(verify): two separate jobs. Moving the `return ld` is one line; applying the lever
> arm in `ibex_state`'s `add_gps` is real work. See
> [launch-files.md](launch-files.md#there-is-unreachable-code-in-this-file).

### The SICK will need a dynamic frame

The [SICK picoScan](../04-subsystems/perception/hardware/sick-picoscan-150.md) is a 2D
scanner on a motor-driven base. Its frame **moves**, so it cannot be a static transform —
it needs continuous publication to `/tf` as the base sweeps.

**It would be the only moving sensor frame on the vehicle.** Nothing exists for it yet
because the sensor has no driver.

### There is no map frame

`map` does not exist. `ibex_state` produces a globally-referenced estimate through
`odom_offset` in `utm` rather than through a `map` frame, and nothing does loop closure or
localization against a prior map.

> Worth stating explicitly so nobody looks for it. The standard
> `map → odom → base_link` convention is only half present.

## The frame-name trap

Ouster point clouds are stamped `frame_id = os_lidar`:

```bash
ros2 topic echo /ouster/points --field header.frame_id --once   # -> os_lidar
```

KISS-ICP needs a TF path from `base_link` to `os_lidar`.

**Do not satisfy that by renaming the static leaf to `os_lidar`.** The driver already
publishes `os_sensor → os_lidar`; adding `os_mount → os_lidar` **splits the tree into two
disconnected trees**, producing *"not part of the same tree"*.

**Correct:** the static chain ends at `os_mount → os_sensor` and the driver connects the
rest, which makes `os_lidar` reachable from `base_link` automatically.

## Verifying the tree

```bash
# Render the whole tree to frames.pdf
ros2 run tf2_tools view_frames

# Does base_link reach the lidar?
ros2 run tf2_ros tf2_echo base_link os_lidar

# The definitive test: is the vehicle moving in odom?
ros2 run tf2_ros tf2_echo odom base_link
```

Reading the last one:

| Observation | Meaning |
| --- | --- |
| Startup warning *"frame odom does not exist"* | Timing only. tf2 waiting for the first transform. Ignore if data follows |
| Parked, translation jitters ~3 cm | Normal registration noise. Working |
| Driving, translation grows to metres | Working |
| Driving, translation stays ~3 cm | **Tracking failure.** Check the input topic and the environment |

**In RViz set Fixed Frame to `odom`.** Getting this wrong produces the same symptom as a
broken transform — a cloud pinned to the start position.

**Each `static_transform_publisher` needs a unique `name=`.** Duplicate node names cause
undefined behaviour, and the static chain uses several.

## Open items

| Item | Blocks |
| --- | --- |
| **Camera frames** — three array cameras, no frames | All spectral-to-geometry fusion |
| **`gps_mount` is dead code**, and the lever arm is unapplied | A ~0.6 m lateral GPS bias |
| **`aligned_odom` / `utm` have no transform** | Any tf2 use of the fused estimate |
| **Insta360 IMU yaw** is an unverified estimate | `ibex_state`'s second preintegration pipeline |
| **Wheelbase** never measured | `ibex_state`'s bicycle model |
| **Ouster coverage table** still computed at 25° | Stated sensor range |
| **Vehicle length** recorded two ways | Unexplained 4 in discrepancy |
| **SICK dynamic frame** | Its future driver |

Resolved by reading `static_tf.launch.py`: the Ouster tilt is measured not assumed,
`front_bumper → sensor_rack` is confirmed, and `insta_imu` does have a publisher.

## Related

- [kiss-icp.md](../04-subsystems/state-estimation/software/kiss-icp.md) — publishes the
  dynamic edge, and the diagnostics for when it is missing
- [ibex-state.md](../04-subsystems/state-estimation/software/ibex-state.md) — consumes the
  tree, publishes the orphaned labels
- [ouster-os1-64.md](../04-subsystems/perception/hardware/ouster-os1-64.md) — the tilt and
  the coverage figures that depend on it
- [launch-files.md](launch-files.md) — where the static publishers are started
- [specifications.md](../03-base-vehicle/specifications.md) — vehicle dimensions
- [glossary.md](../00-onboarding/glossary.md) — `map` versus `odom`, REP-105
