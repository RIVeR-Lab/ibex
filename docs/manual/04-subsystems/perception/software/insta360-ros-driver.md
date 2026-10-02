---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# insta360_ros_driver

The Insta360 X4 driver. Serves [Perception](../README.md).

## Source

| | |
| --- | --- |
| Upstream | <https://github.com/ai4ce/insta360_ros_driver> — NYU AI4CE |
| Our fork | <https://github.com/RIVeR-Lab/insta360_ros_driver> |
| In this repo | `packages/insta360_ros_driver` — git submodule |

## Fork status

A fork of AI4CE's driver, vendored as a submodule. Three changes are recorded as needed
for IBEX:

| Change | Where |
| --- | --- |
| Comment out rotations | `src/equirectangular.cpp` lines 279–280 |
| Crop size to 1380, to reduce clipping | `config/equirectangular.yaml` line 5 |
| Comment out the matching rotation, for calibration mode | `scripts/equirectangular.py` — search for `90` |

> TODO(verify): **are these applied in the fork, or are they instructions to apply by
> hand?** The source note lists them under "Modifications required," which is ambiguous.
> If they are in the fork, say so and record the commit. If they are applied by hand after
> every clone, that is a setup step missing from
> [workstation-setup.md](../../../00-onboarding/workstation-setup.md) — and one that will
> be forgotten.

> TODO(verify): are any of these upstreamable? The crop size is IBEX-specific, but the
> rotation removal sounds like it might be a general X4 difference rather than something
> about our mounting. AI4CE verified the driver on the X2 and X3, not the X4 — see
> [Known issues](#the-driver-is-not-verified-on-the-x4).

## Description

A ROS 2 driver for Insta360 cameras. It pulls the camera's dual-fisheye stream over USB,
decodes frames, optionally stitches them into an equirectangular image, and publishes the
camera's IMU with a Madgwick filter applied for orientation.

## Capabilities

- Real-time capture and publishing from the camera over USB
- Dual-fisheye image publishing, compressed and decoded
- Equirectangular stitching, configurable through `config/equirectangular.yaml`
- On-demand decoding through a separate decoder node
- IMU publishing, raw and Madgwick-filtered
- A calibration mode for tuning the equirectangular extrinsics
- Automatic udev rule creation, so the camera does not need `sudo` for USB access

## Purpose

It is the only thing that gets imagery off the X4 and into ROS 2. Without it the camera is
a standalone action camera.

## Alternative software

None evaluated.

> The source note is honest about this: no search was done, and writing our own was
> considered. Worth leaving as-is rather than inventing a comparison — but see
> [Known issues](#the-driver-is-not-verified-on-the-x4), because the X4 support question
> may eventually force the issue.

## Launch / invocation

```bash
ros2 launch insta360_ros_driver insta_bringup.launch.py equirectangular:=true
```

> TODO(verify): the launch file name is recorded two ways. The command sheet and
> [running-the-system.md](../../../02-operations/running-the-system.md) use
> `insta_bringup.launch.py`; the source note and upstream use `bringup.launch.xml`.
> Confirm which exists in the fork — if the fork renamed it, that is a fork change worth
> recording above.

Individual nodes, for debugging or calibration:

```bash
ros2 run insta360_ros_driver insta360_ros_driver     # camera driver
ros2 run insta360_ros_driver decoder                 # image decoding
ros2 run insta360_ros_driver equirectangular.py --calibrate
```

**Preconditions:**

- The camera powered on by hand at the roof, and in **Control with Android** mode — see
  [insta360-x4.md](../hardware/insta360-x4.md)
- Volta up, since the camera is USB-powered from it

## Topics

All in the `/insta360` namespace. Four nodes in a chain.

```
insta360_ros_driver ──compressed──> image_decoder ──image──> equirectangular_node
         │                                                            │
         └──imu/data_raw──> imu_filter ──imu/data──> (nothing)        └──> (nothing)
                                 │
                                 └──> /tf
```

| Topic | Type | Publisher | Subscriber | QoS |
| --- | --- | --- | --- | --- |
| `/insta360/dual_fisheye/image/compressed` | `sensor_msgs/CompressedImage` | `insta360_ros_driver` | `image_decoder` | Reliable |
| `/insta360/dual_fisheye/image` | `sensor_msgs/Image` | `image_decoder` | `equirectangular_node` | Reliable |
| `/insta360/equirectangular/image` | `sensor_msgs/Image` | `equirectangular_node` | **none** | Reliable |
| `/insta360/imu/data_raw` | `sensor_msgs/Imu` | `insta360_ros_driver` | `imu_filter` | Best effort |
| `/insta360/imu/data` | `sensor_msgs/Imu` | `imu_filter` | **none** | Reliable |
| `/insta360/imu/mag` | `sensor_msgs/MagneticField` | **none** | `imu_filter` | Best effort |
| `/tf` | `tf2_msgs/TFMessage` | `imu_filter` | — | Reliable |

### No CameraInfo

Neither image topic has an accompanying `camera_info`. Nothing advertises the camera's
intrinsics, so anything geometric downstream has no calibration to work from.

> TODO(verify): establish whether that matters for how the camera is used. If it stays
> situational-awareness imagery, it does not. If it is ever used geometrically — including
> as a registration aid against the point cloud — it does.

## Known issues & fixes

### The equirectangular output has no consumers

`/insta360/equirectangular/image` is published and subscribed by nothing.

The full chain runs anyway: decode, then stitch, for every frame of 4K at 60 fps. That is
real CPU on Volta, spent producing an image that is discarded.

> TODO(verify): is the equirectangular image being recorded to bag? A `ros2 bag record`
> would appear as a subscriber only while recording, and this capture was taken with no
> bag running. If it **is** bagged, this is fine and the chain is doing its job. If it is
> **not**, consider launching with `equirectangular:=false` for sessions that do not need
> it, and check whether the decoder is needed either — the compressed topic may be enough
> to bag.

### The Madgwick filter is subscribed to a magnetometer that does not exist

`imu_filter` subscribes to `/insta360/imu/mag`, and **nothing publishes it.**

In `imu_filter_madgwick` the magnetometer subscription is only created when `use_mag` is
true, and in that mode the filter synchronises IMU and magnetometer messages before
publishing. With no magnetometer data arriving, it may never publish at all.

A publisher being registered on `/insta360/imu/data` does not mean messages are flowing.

> TODO(verify): **check whether the filtered IMU is actually publishing.**
>
> ```bash
> ros2 topic hz /insta360/imu/data
> ```
>
> If the rate is zero, set `use_mag: false` in `config/imu_filter.yaml`. The X4 has no
> magnetometer exposed through this driver, so IMU-only is the correct mode.

### imu_filter publishes to /tf

The filter publishes a dynamic transform to `/tf` — not `/tf_static`.

`imu_filter_madgwick` publishes a transform from a fixed frame to the IMU frame when
`publish_tf` is enabled, and its default fixed frame is `odom`.

**That is the same frame KISS-ICP's odometry uses.** Two publishers writing transforms
involving `odom` will fight, and the symptom is a transform tree that jitters or flips
depending on which message arrived last.

> TODO(verify): **this is the highest-priority item on this page.** Determine what frames
> `imu_filter` is actually publishing:
>
> ```bash
> ros2 topic echo /tf --once
> ros2 run tf2_tools view_frames
> ```
>
> If it is publishing anything involving `odom` or `base_link`, set `publish_tf: false`.
> A 360° camera's IMU orientation has no business in the vehicle's transform tree, and
> [tf-frames.md](../../../05-reference/tf-frames.md) does not account for it.

### The driver is not verified on the X4

AI4CE verified this driver on the Insta360 X2 and X3. IBEX runs an X4.

It works, but it is not a supported configuration upstream, and the rotation changes in
the fork may be a symptom of that rather than an IBEX-specific adjustment.

> TODO(verify): record what does not work, if anything. An unverified camera model is the
> kind of thing that explains an odd behaviour six months later.

## Parameters

| Parameter | File | Our value | Effect |
| --- | --- | --- | --- |
| `equirectangular` | launch argument | `true` | Enables the stitching node |
| Crop size | `config/equirectangular.yaml` line 5 | `1380` | Reduces clipping in the stitched image |
| `use_mag` | `config/imu_filter.yaml` | TODO(verify) | Whether the Madgwick filter waits for magnetometer data |
| `publish_tf` | `config/imu_filter.yaml` | TODO(verify) | Whether the filter writes to `/tf` |

> TODO(verify): record the full contents of both config files. `config/equirectangular.yaml`
> and `config/imu_filter.yaml` are the two places IBEX's behaviour is set, and only one
> line of one of them is currently documented.

## Dependencies

**External**

- **Insta360 SDK** — required, and obtained by application at
  <https://www.insta360.com/sdk/home>. Navigate to Development Tools → SDK after logging
  in.
  **Credentials are in the lab password manager.** See
  [vendor-accounts.md](../../../99-appendix/vendor-accounts.md).
- `imu_filter_madgwick` — provides the orientation filter
- A udev rule for USB access, which the driver creates automatically

**Hardware that must be powered**

- The [Insta360 X4](../hardware/insta360-x4.md), powered by hand at the roof and in
  Control with Android mode
- Volta, which supplies its USB power

Additional setup notes are in an upstream issue thread:
<https://github.com/ai4ce/insta360_ros_driver/issues/10#issuecomment-3371481987>

## Understanding the software

**The pipeline is four nodes deep**, and each stage is separable. The driver produces
compressed dual-fisheye frames; the decoder turns those into raw images on demand; the
equirectangular node stitches them. Running fewer stages is a legitimate way to save CPU
if the later products are not needed.

**Calibration mode exists for the stitch.** `equirectangular.py --calibrate` lets you
adjust the extrinsic parameters between the two fisheye lenses, which is what the crop
size and rotation changes are tuning. Note that the calibration path needs the same
rotation commented out in the Python script as in the C++ node, or the two disagree.

## Related pages

- [insta360-x4.md](../hardware/insta360-x4.md) — the camera, its modes and power
- [Perception overview](../README.md) — the sensor set
- [running-the-system.md](../../../02-operations/running-the-system.md) — launching it
- [tf-frames.md](../../../05-reference/tf-frames.md) — the transform tree this may be
  writing into
- [ros-graph.md](../../../05-reference/ros-graph.md) — system-wide topic view
- [vendor-accounts.md](../../../99-appendix/vendor-accounts.md) — the Insta360 SDK account
