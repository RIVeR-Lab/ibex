---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Allied Vision Alvium RGB camera

The colour camera. Serves [Perception](../README.md).

## Overview

A 5 MP USB 3 colour camera on the hyperspectral array. Unlike the two hyperspectral
cameras it produces ordinary RGB imagery, and its role is **context rather than
measurement** — a human-interpretable record of what the scene looked like, registered
against the spectral data by virtue of sitting on the same rack.

Mounted at the **far right** of the hyperspectral array, which completes the layout:

| Position | Sensor |
| --- | --- |
| Far left | [Ximea VNIR HSI](ximea-vnir-hsi.md) |
| Centre | [IMEC SWIR HSI](imec-swir-hsi.md) |
| Far right | Alvium RGB — this camera |
| Above the array | [Insta360 X4](insta360-x4.md) |
| Alongside | Spectralon reference puck and both spectrometer fibre ends |

## Physical location on vehicle

Far right of the hyperspectral array, on the roof.

> TODO(verify): record the camera's orientation and look angle, and whether all three
> cameras on the array view the same ground. Same gap as the other two — there is no
> hyperspectral or camera frame in
> [tf-frames.md](../../../05-reference/tf-frames.md), which is what any registration
> between RGB, spectral, and lidar data will need.

## Power source / rail

**USB bus power from Volta.** Not fed by the Compute and Sensing box.

| | |
| --- | --- |
| Voltage | 5 V |
| Current | 0.4 A |
| Power | 2.0 W |

5 V at 0.4 A is USB bus power, so this camera comes up and goes down with Volta.

Worth noting the pattern across the array: this camera and the Ximea VNIR both run on USB
power from Volta at about 2 W each, while the SWIR camera takes 18 W at 6 V from the
Compute and Sensing box. Three cameras on one rack, two different supplies.

## Hardware specs

| | |
| --- | --- |
| Manufacturer | Allied Vision |
| Model | Alvium 1800 U-507C |
| Resolution | 2464 × 2056 — about 5.07 MP |
| Sensor type | CMOS, colour |
| Sensor spectral response | 300–1100 nm — see below |
| Interface | USB 3 |
| GPIO | 4 programmable pins |
| Supply | 5 V, 0.4 A, 2.0 W over USB |
| Serial number | TODO(verify) |

### The 300–1100 nm figure needs interpreting

That is the **bare silicon sensor's** response range, not the range of any colour channel.
This is a colour camera — the `C` in `U-507C` — so it carries a Bayer colour filter array,
and each of the red, green, and blue channels passes a subrange within roughly
400–700 nm.

What matters is whether an **IR-cut filter** is fitted:

| | Consequence |
| --- | --- |
| IR-cut fitted | Effective range roughly 400–700 nm. Colours are accurate. No NIR sensitivity |
| No IR-cut | Silicon's NIR response leaks into all three channels. Colours skew, but the camera has some sensitivity out to ~1000 nm |

> TODO(verify): **is an IR-cut filter fitted?** This determines whether the camera is
> purely contextual or has incidental spectral utility, and it also determines whether its
> colours can be trusted. Without the filter, foliage in particular photographs oddly
> because of strong NIR reflectance — which on a vehicle driven through vegetation is not a
> hypothetical.
>
> Note the camera's unfiltered response would overlap the
> [Ximea VNIR camera](ximea-vnir-hsi.md) across most of its range.

### Lens

> TODO(verify): entirely unrecorded. The model is a C-mount body, so a lens is fitted and
> is not integral. Needed: manufacturer, focal length, aperture, and whether it has an
> IR-cut coating — which bears on the question above. Without focal length, field of view
> and ground footprint cannot be calculated.

## Additional components

**Four programmable GPIO pins**, capable of trigger input and output.

> TODO(verify): **this is the third triggerable device on the array and none is used.** The
> SWIR and VNIR cameras each ship with a trigger cable, and this camera has four GPIO
> pins. Hardware synchronisation across all three is therefore available and unexercised,
> while nothing on IBEX currently shares a time base — the Ouster runs on its own
> oscillator, and the hyperspectral cameras' timing is unaddressed.
>
> Establish whether `hyper_drive`'s `synchronous_cameras_launch.py` synchronises in
> software or expects hardware triggering. The launch file's name suggests synchronisation
> is intended.

## Software

| Software | Role |
| --- | --- |
| `vimbax_camera` | **The actual driver.** Allied Vision's own ROS 2 package, installed from a `.deb` |
| Vimba X SDK | Allied Vision's vendor library, which the driver uses |
| [hyper-drive.md](../software/hyper-drive.md) | Does **not** drive this camera, but starts it and consumes its frames |

**This camera is not driven by `hyper_drive`.** `hyper_drive`'s launch files start
Allied Vision's `vimbax_camera` node alongside the hyperspectral cameras, and
`synchronous_cubes` subscribes to its output and attaches each frame to the paired-cube
message.

| | |
| --- | --- |
| Node | `vimbax_camera_node`, named `alvium_camera` in namespace `alvium` |
| Camera ID | `DEV_1AB22C025217` |
| Settings file | `~/allied_vision_config.xml` |
| Topic | Publishes `/alvium/image_raw`, remapped to `/camera/image_raw` |

Installation is in
[workstation-setup.md](../../../00-onboarding/workstation-setup.md).

> The source note records Vimba X version **2026-1**. That is stale — **2026-2** is the
> correct version, confirmed and applied in
> [workstation-setup.md](../../../00-onboarding/workstation-setup.md). The older number
> appeared inconsistently across the repo README and caused install failures, because the
> download, extract, and verify paths disagreed with each other.

Verify the camera independently of ROS with Allied Vision's own viewer:

```bash
/opt/VimbaX_2026-2/bin/VimbaXViewer
```

### Data structure / output format

> TODO(verify): unrecorded. Needed: the image topic name, encoding — Bayer or debayered
> RGB — and bit depth. Whether debayering happens in the driver, in the SDK, or not at all
> determines what a consumer receives. See
> [hyper-drive.md](../software/hyper-drive.md).

## Networking

Not applicable. USB 3 to Volta.

## Setup & calibration

### Software prerequisites

Vimba X SDK 2026-2, plus the GenTL path scripts and the ROS 2 driver `.deb` — see
[workstation-setup.md](../../../00-onboarding/workstation-setup.md).

### Configuration file

The setup sequence ends with generating a configuration file for this camera. It is
**`~/allied_vision_config.xml`**, passed to the driver as its `settings_file` parameter.

> TODO(verify): **this file is not in the repository.** It sits in the home directory, so
> it is not version-controlled and would be lost with the machine — and a fresh install
> cannot produce it without knowing what it contains. Move it into
> `hyper_drive/config/` and point the launch files at the installed share path. It is one
> of two pieces of live configuration outside git, the other being the FastDDS profile.

> TODO(verify): record how it is generated — almost certainly a settings export from
> VimbaXViewer — and what in it matters. Exposure, gain, pixel format, and white balance
> are the likely contents, and they determine whether this camera's imagery is usable.

### Calibration

**The driver publishes `/alvium/camera_info`** — a `sensor_msgs/CameraInfo`, with zero
subscribers. So an intrinsics channel exists; whether it carries real values is a separate
question, because an uncalibrated driver publishes zeroed `K` and `D`.

```bash
ros2 topic echo /alvium/camera_info --once
```

> TODO(verify): echo it and record whether the intrinsics are real. If they are, this
> camera is calibrated and that should be stated here. If they are zeroed, the topic is
> noise and the camera needs a calibration before it can be used for anything geometric.

**The topic is also orphaned from its image.** The launch file remaps the image from
`/alvium/image_raw` to `/camera/image_raw`, and leaves `camera_info` behind in the
`alvium` namespace. That breaks the ROS convention of the two sitting together, so
anything using `image_transport` or pairing them by namespace will not find the intrinsics.

> TODO(verify): extend the remap to carry `camera_info` alongside the image.

## Known issues & fixes

### CycloneDDS breaks this camera

**Symptom:** the camera initializes and then never starts streaming. No error.

**Cause:** setting `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` breaks VimbaX's subscriber
discovery on Ubuntu 22.04.

**Fix:** do not set it. The stack uses the default FastRTPS, which is why — see
[running-the-system.md](../../../02-operations/running-the-system.md). **Installed.**

**This constrains the whole vehicle, not just this camera.** VimbaX's own documentation
recommends CycloneDDS, so the obvious thing to try is the thing that breaks it. Any DDS
middleware change on IBEX has to be tested against this camera.

> There is also an undocumented FastDDS profile in use —
> `/home/river/fastdds_ibex_config.xml`, applied through
> `RMW_IMPLEMENTATION=rmw_fastrtps_cpp`. TODO(verify): read it and record what it
> configures. It affects every node on the vehicle and is currently unrecorded anywhere.

### Vimba X version confusion

Covered under [Software](#software). The repo README carried both 2026-1 and 2026-2 across
different steps, which made the install fail either way. Resolved to **2026-2**.

## Datasheets

[`docs/hardware/Hyperspectral 3D/Allied Vision RGB Spec Sheet.pdf`](../../../../hardware/Hyperspectral%203D/Allied%20Vision%20RGB%20Spec%20Sheet.pdf)

Product listing:
<https://www.edmundoptics.com/p/allied-vision-alvium-1800-u-507c-23-51mp-c-mount-usb-31-color-camera/42994/>

> That link is a reseller listing rather than Allied Vision's own documentation.
> TODO(verify): add Allied Vision's datasheet for the 1800 U-507C, which will also answer
> the IR-cut filter and sensor model questions.

## Reorder

The Alvium 1800 series is a current commercial product and readily available, which makes
this the easier of the three array cameras to replace.

> TODO(verify): record the supplier used, the exact model and lens as ordered, and lead
> time. Consolidate into [reorder.md](../../../99-appendix/reorder.md).

## Related pages

- [ximea-vnir-hsi.md](ximea-vnir-hsi.md) and [imec-swir-hsi.md](imec-swir-hsi.md) — the
  other two cameras on the array
- [hyper-drive.md](../software/hyper-drive.md) — the shared driver
- [Perception overview](../README.md) — the sensor set
- [workstation-setup.md](../../../00-onboarding/workstation-setup.md) — Vimba X
  installation
- [running-the-system.md](../../../02-operations/running-the-system.md) — the CycloneDDS
  constraint
- [power-on.md](../../../02-operations/power-on.md) — comes up with Volta, step 7
