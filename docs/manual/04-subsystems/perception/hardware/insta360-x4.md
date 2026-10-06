---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Insta360 X4

The 360° camera. Serves [Perception](../README.md).

## Overview

A consumer 360° camera with two fisheye lenses, capturing 8K spherical video. Its imagery
provides situational awareness rather than measurement — but **its IMU is a measurement
sensor**, and that is easy to miss.

Three things make it worth having:

**It sees everything at once.** A single 360° stream replaces several fixed cameras for
the purpose of understanding what a run looked like.

**It is the only sensor that sees behind the vehicle.** Every other camera and both lidars
face forward or scan a forward-biased cone. Nothing else on IBEX covers the rear.

**Its IMU is one of two feeding state estimation.** `ibex_state` runs a separate GTSAM
preintegration pipeline, with its own bias chain and its own extrinsics, against
`/insta360/imu/data_raw` alongside the Ouster's IMU. So a consumer action camera is
contributing inertial constraints to the vehicle's pose estimate — see
[ibex-state.md](../../state-estimation/software/ibex-state.md).

That has a consequence worth stating plainly: **powering this camera off, or letting its
battery die mid-run, removes an input from state estimation**, not just a video feed.

It is mounted above the hyperspectral array, at the highest point on the roof — which
gives it the clearest view and also makes it the most exposed component on the vehicle.

## Physical location on vehicle

Roof, above the hyperspectral array. The tallest point on IBEX.

**It is powered on by hand, at the camera.** The power button is on the side of the
camera body, so starting it means physically reaching the top of the vehicle — it cannot
be done from the cab or from Volta. That is a step in
[power-on.md](../../../02-operations/power-on.md) and it is the only sensor on IBEX
requiring physical access to bring up.

> TODO(verify): record the mount — what it attaches to and how. As the highest point on
> the vehicle it sets the as-built height that matters for garage clearance and transport,
> which is still unrecorded in
> [specifications.md](../../../03-base-vehicle/specifications.md).

> TODO(verify): the lens guards and lens cap are listed among the accessories. Record
> whether guards are fitted in the field. At the highest point on a vehicle driven through
> marsh vegetation, an unguarded fisheye lens is the most likely thing to get scratched.

## Power source / rail

**Dual-powered.** Internal battery, plus USB-C from Volta.

| | |
| --- | --- |
| Battery | 2290 mAh |
| External | USB-C from Volta |

Because it is USB-connected to Volta rather than to a vehicle rail, it comes up and goes
down with Volta — not with the Compute and Sensing box directly. It is also the one sensor
that keeps running briefly if everything else loses power, since it has its own battery.

The camera's own power button is on the side of the body, and is used in
[power-on.md](../../../02-operations/power-on.md) step 8 and
[power-off.md](../../../02-operations/power-off.md) step 5.

USB-C from Volta both **powers and charges** the camera. The battery is therefore a
buffer rather than a consumable — it keeps the camera alive briefly if Volta goes down,
and tops back up when Volta returns. No between-session charging routine is needed.

The spare battery is a contingency for a failed cell or an extended session off-vehicle,
not part of normal operation.

## Hardware specs

| | |
| --- | --- |
| Manufacturer | Insta360 |
| Model | X4 |
| Storage | microSD, **V30 or higher required** |
| Battery | 2290 mAh |
| Serial number | TODO(verify) |

### Video modes

**360°**

| Resolution | Frame rates |
| --- | --- |
| 8K — 7680 × 3840 | 30 / 25 / 24 fps |
| 5.7K+ — 5760 × 2880 | 30 / 25 / 24 fps |
| 5.7K — 5760 × 2880 | 60 / 50 / 30 / 25 / 24 fps |
| 4K — 3840 × 1920 | 100 / 60 / 50 / 30 / 25 / 24 fps |

**Single-lens**

| Resolution | Frame rates |
| --- | --- |
| 4K — 3840 × 2160 | 60 / 50 / 30 / 25 / 24 fps |
| 2.7K — 2720 × 1536 | 60 / 50 / 30 / 25 / 24 fps |
| 1080p — 1920 × 1080 | 60 / 50 / 30 / 25 / 24 fps |

**Me mode**

| Resolution | Frame rates |
| --- | --- |
| 4K — 3840 × 2160 | 30 / 25 / 24 fps |
| 2.7K — 2720 × 1536 | 120 / 100 / 60 / 50 fps |
| 1080p — 1920 × 1080 | 120 / 100 / 60 / 50 fps |

### Photo

| Resolution | |
| --- | --- |
| ~72 MP | 11904 × 5952 |
| ~18 MP | 5888 × 2944 |

**Configured mode: 360°, 4K at 60 fps — 3840 × 1920.**

This is why the driver is launched with `equirectangular:=true` — the dual fisheye streams
are stitched into a single equirectangular image. See
[insta360-ros-driver.md](../software/insta360-ros-driver.md).

## Additional components

Supplied accessories: carry case, fast battery charger, selfie stick, spare battery,
thermo grip cover, lens guard, lens cap.

> TODO(verify): record which of these are kept with the vehicle versus in the lab, and
> whether the spare battery is charged. The black container manifest in
> [transport.md](../../../02-operations/transport.md) does not currently mention the camera
> or its accessories.

## Software

| Software | Role |
| --- | --- |
| [insta360-ros-driver.md](../software/insta360-ros-driver.md) | The ROS 2 driver. Forked submodule |
| Insta360 SDK | Required by the driver. Obtained by application — see the software page |
| Insta360 phone app | Vendor app. Required to start onboard SD recording, to configure the camera, and to export proprietary formats |

### Data structure / output format

**On IBEX, imagery reaches ROS over USB and nothing is recorded to the SD card.** Onboard
recording is not automatic — it has to be started deliberately through the Insta360 phone
app. The card is present because the camera wants one, not because it is being written to
in normal operation.

That means [data-collection.md](../../../02-operations/data-collection.md) is complete as
written: everything from this camera lands in a bag, and there is no second offload path
to worry about.

| Path | Format | Used on IBEX |
| --- | --- | --- |
| Over USB, through the ROS driver | ROS 2 image topics | **Yes** |
| Onboard to microSD — 360° | INSV | No. Requires the phone app |
| Onboard to microSD — single-lens | MP4 | No |
| Onboard photo | INSP, DNG | No |

The camera also produces IMU data.

INSV and INSP are proprietary and need the phone app or Insta360 Studio to export — which
is a reason to prefer the ROS path even if onboard recording is ever used.

> If onboard recording is ever started for a particular session, say so in that
> collection's `metadata.yaml`, because the footage will exist in a place nothing else
> looks.

## Networking

Not applicable. USB-C to Volta.

The camera presents itself over USB in **Control with Android** mode — the driver
communicates with it as though it were an Android host.

**The mode is decided at boot and does not persist as a setting.** Each time the camera
powers on it checks whether a USB connection is present, and enters Control with Android
if it is. Because the USB cable stays plugged in between sessions, it normally enters that
mode on its own.

**Verify it at every boot.** The mode is a consequence of what the camera saw at power-on,
not a configuration it remembers, so anything that disturbed the cable means it may come
up in the wrong mode. See
[power-on.md](../../../02-operations/power-on.md) step 8 and
[Known issues](#no-video-and-the-camera-is-in-the-wrong-usb-mode).

## Setup & calibration

### Physical installation

Roof mount above the hyperspectral array. See
[Physical location](#physical-location-on-vehicle).

### Calibration

None recorded.

> TODO(verify): a dual-fisheye camera has a stitching calibration, and its pose relative
> to `base_link` is an extrinsic like any other sensor. Establish whether either is set.
> The driver's `equirectangular:=true` argument implies stitching happens somewhere — see
> [insta360-ros-driver.md](../software/insta360-ros-driver.md). There is no Insta360 frame
> recorded in [tf-frames.md](../../../05-reference/tf-frames.md).

### SD card

Use a **V30 or higher** microSD card. V30 is the video speed class guaranteeing a sustained
30 MB/s minimum write rate, which is what 4K and above requires to avoid dropped frames
and corrupted footage.

The camera warns about this at power-on if it detects a slower card.

This only matters if onboard recording is used, which it is not in normal operation — but
the warning appears regardless, so a card below V30 produces an alarming message about a
feature nobody is using.

## Known issues & fixes

### No video, and the camera is in the wrong USB mode

**Symptom:** the camera is powered and connected but no imagery reaches ROS.

**Cause:** the camera is not in **Control with Android** mode. It decides that at
power-on, based on whether a USB connection is present — so a cable that was loose,
unplugged, or seated badly at the moment the camera booted leaves it in the wrong mode for
the whole session.

**Fix:** check the cabling, then power-cycle the camera so it re-evaluates at boot.
Changing the cable without restarting the camera does not change the mode.

**Verify the mode at every boot** rather than assuming it. It is not a remembered setting.

### Slow SD card warning at power-on

**Symptom:** a warning appears on the camera at power-on about a slow SD card affecting
performance.

**Cause:** a card below V30.

**Fix:** use a V30 or faster card. See [SD card](#sd-card).

## Datasheets

The X4 user manual is in this repository, filed under the hyperspectral design folder:

[`docs/hardware/Hyperspectral 3D/2.0 Design/Insta360 X4 Camera User Manual.pdf`](../../../../hardware/Hyperspectral%203D/2.0%20Design/Insta360%20X4%20Camera%20User%20Manual.pdf)

> TODO(verify): that location is not where anyone would look for a camera manual. Consider
> moving it to a camera or Insta360 folder under `docs/hardware/`, and update this link.

## Reorder

> TODO(verify): nothing recorded. The X4 is a consumer product and readily available, which
> makes it the easiest sensor on the vehicle to replace — worth noting explicitly, since it
> is also the most exposed. Record the current retail source, and whether a spare body
> exists. Consumables worth listing: microSD cards (V30+), spare batteries, lens guards.
> Consolidate into [reorder.md](../../../99-appendix/reorder.md).

## Related pages

- [Perception overview](../README.md) — the sensor set
- [insta360-ros-driver.md](../software/insta360-ros-driver.md) — the driver and the SDK
- [power-on.md](../../../02-operations/power-on.md) — step 8
- [power-off.md](../../../02-operations/power-off.md) — step 5
- [data-collection.md](../../../02-operations/data-collection.md) — recording and offload
- [vendor-accounts.md](../../../99-appendix/vendor-accounts.md) — the Insta360 SDK account.
  **Credentials live in the lab password manager, never in this repository**
