---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# IMEC Snapshot SWIR HSI

The short-wave infrared hyperspectral camera. Serves [Perception](../README.md).

## Overview

A snapshot mosaic hyperspectral camera covering the short-wave infrared. Unlike a
line-scan imager it captures a full spectral cube in one exposure, at up to 150 cubes per
second, so it does not depend on vehicle motion to build an image.

It is the longer-wavelength half of IBEX's hyperspectral pair. The
[Ximea VNIR camera](ximea-vnir-hsi.md) covers the shorter band, and the
[NIR point spectrometer](ibsen-nir-spectrometer.md) provides this camera's illumination
reference.

Mounted at the centre of the hyperspectral array on the roof.

## Spectral range is unresolved

**This needs settling before any spectral analysis is trusted.** Three figures are in
circulation:

| Source | Range |
| --- | --- |
| Datasheet, SWIR 9 variant | 1100–1700 nm |
| Datasheet, SWIR 16 variant | 1250–1700 nm |
| Working value, attributed to the calibration file | 1100–1700 nm |

Two questions, and the second depends on the first:

**1. Which variant is installed?** The vendor URL recorded in the source note points at
the 4 × 4 mosaic product, which would be the 16-band SWIR 16 — and that variant's
datasheet range starts at 1250 nm, not 1100 nm. A 3 × 3 mosaic would be the 9-band
version.

**2. What is the usable range?** If the camera is a SWIR 16 but the calibration file
provides coefficients from 1100 nm, then either the calibration extends beyond the
datasheet specification, or the figure is being read from the wrong file.

> TODO(verify): resolve both. Check the mosaic pattern and band count the camera actually
> reports, read the band centres out of the calibration file, and compare against the
> datasheet in
> [`docs/hardware/Hyperspectral 3D/`](../../../../hardware/Hyperspectral%203D/). Then
> record the answer here and in the spectral coverage table in
> [Perception](../README.md).
>
> This is not academic. If the real range starts at 1250 nm, there is a **150 nm gap**
> between this camera and whatever the VNIR camera's upper limit is, and the only
> instrument covering it is the NIR point spectrometer — which measures one point, not an
> image.

## Physical location on vehicle

Centre of the hyperspectral array, on the roof. The Insta360 sits above the array; the
Spectralon reference puck and both spectrometer fibre ends are alongside the cameras.

> TODO(verify): record the camera's orientation and look angle. The hyperspectral data has
> to be registered against the lidar point cloud eventually, and nothing records where
> this camera points or what ground distance it covers. There is no hyperspectral frame in
> [tf-frames.md](../../../05-reference/tf-frames.md).

## Power source / rail

Fed by the **Compute and Sensing box**. Data leaves over USB to Volta.

| | |
| --- | --- |
| Voltage | 6 V |
| Current | 3 A |
| Power | 18 W |

**This is the largest single load on the 6 V supply** — more than twenty times either
spectrometer, which draw 0.8 W each. Three devices share that rail.

> TODO(verify): confirm the 6 V rail's capacity against the total of these three loads,
> and record it on [power/](../../power/). 18 W at 6 V is 3 A through whatever converter
> feeds it.

## Hardware specs

| | |
| --- | --- |
| Manufacturer | IMEC |
| Product | Snapshot SWIR |
| Variant | TODO(verify) — SWIR 9 or SWIR 16, see above |
| Sensor resolution | 640 × 512 |
| Spectral range | 1100–1700 nm, disputed — see above |
| Bands | TODO(verify) — 9 or 16 depending on variant |
| Cube rate | Up to 150 cubes/s |
| Supply | 6 V, 3 A, 18 W |
| Serial number | TODO(verify) |

### Effective spatial resolution is much lower than 640 × 512

This is a snapshot *mosaic* camera: the spectral filters are tiled across the sensor, so
each band is sampled by only a fraction of the pixels. The 640 × 512 figure is the raw
sensor, not the resolution of any single band.

| Mosaic | Bands | Approximate per-band resolution |
| --- | --- | --- |
| 4 × 4 | 16 | 160 × 128 |
| 3 × 3 | 9 | 213 × 170 |

> TODO(verify): confirm the mosaic pattern and record the actual per-band spatial
> resolution. Anyone expecting 640 × 512 per band will be surprised by a factor of 16, and
> this figure is what matters for registering the imagery against the point cloud.

### Lens

| | |
| --- | --- |
| Manufacturer | Navitar |
| Spectral range | SWIR |
| Focal length | 25 mm |
| Aperture | f/2.8 |
| Exit pupil distance | 65 mm |
| Minimum focus distance | 0.7 m |

The 0.7 m minimum focus is comfortably inside the useful range for terrain ahead of the
vehicle — the Ouster's ground footprint starts at 1.6 m — so nothing of interest should be
closer than the camera can resolve.

> TODO(verify): calculate and record the ground footprint this lens and sensor produce at
> typical working distances. A 25 mm lens on a 640 × 512 SWIR sensor gives a specific field
> of view, and knowing the ground area covered per cube is necessary for any fusion with
> the lidar.

## Additional components

- Navitar 25 mm SWIR lens
- **Trigger cable**, included per the datasheet

> TODO(verify): is the trigger cable used? A hardware trigger would allow this camera to be
> synchronised against the other hyperspectral camera, or against an external clock — and
> synchronisation between the imagers and the rest of the vehicle is currently
> unaddressed. The Ouster runs on its own internal oscillator
> ([ouster-os1-64.md](ouster-os1-64.md)), so nothing on IBEX shares a time base. If the
> trigger is unused, record where the cable is.

## Software

| Software | Role |
| --- | --- |
| [hyper-drive.md](../software/hyper-drive.md) | The ROS 2 driver. Also covers `hyper_drive_interfaces` |
| IMEC HSI Mosaic | Vendor library, version **1.12.0.0** |
| Pleora eBUS SDK | Transport layer, version **6.5.3** |
| Photon Focus SDK | Version 2025.1.0_Linux64 |
| IMEC GUI | **Windows only.** Used to verify illumination during calibration |

Installation of all four libraries is in
[workstation-setup.md](../../../00-onboarding/workstation-setup.md). This camera is the
reason that section exists and is the single largest source of setup time for a new
researcher.

### Data structure / output format

Spectral radiance. See
[glossary.md](../../../00-onboarding/glossary.md) for what that means and how it differs
from reflectance.

## Networking

Not applicable. USB to Volta, through the Pleora transport layer.

## Setup & calibration

### Software prerequisites

Four vendor libraries at pinned versions — see
[workstation-setup.md](../../../00-onboarding/workstation-setup.md). The versions are not
advisory, see [Known issues](#the-current-imec-sdk-is-incompatible).

### Calibration

Two references are collected: a **dark reference** with the lens covered, and a **light
reference** from a reflective board under diffused halogen light.

Required:

1. Set the camera up in a dark room with no windows or other light sources.
2. Run the calibration script — see
   [hyper-drive.md](../software/hyper-drive.md).
3. Cover the lens and collect the dark reference.
4. Light the reflective board with diffused halogen light.
5. Collect the light reference.

Optional, to confirm the light reference is good before committing to it:

1. Light the reflective board with diffused halogen light.
2. Open the IMEC GUI on a Windows machine.
3. Confirm the illumination is uniform and does not saturate the sensor.
4. Unplug the camera from the Windows machine and connect it to the Linux machine
   **without changing the physical setup**.
5. Turn the lights off and proceed with the required steps above.

> The optional path requires a Windows machine, because the IMEC GUI does not run on
> Linux. That is worth knowing before planning a calibration session.

> TODO(verify): record where calibration output is stored, how often recalibration is
> needed, and whether it survives a reboot. Also record which halogen source and
> reflective board are used — a light reference is only meaningful if the source is
> reproducible.

## Known issues & fixes

### The current IMEC SDK is incompatible

**Symptom:** the hyperspectral pipeline does not work with a current IMEC SDK.

**Cause:** the latest SDK is not compatible with our pipeline.

**Fix:** use the version vendored in the `hyper_drive` or `ibex` repositories — HSI Mosaic
**1.12.0.0**, not the 2.11.10.0 that IMEC's default installer provides. **Installed.**

This answers a question left open in
[workstation-setup.md](../../../00-onboarding/workstation-setup.md), which records that
1.12.0.0 must be requested from IMEC support without saying why. The reason is pipeline
compatibility, and it is a constraint rather than a preference.

> TODO(verify): record what specifically breaks with the newer SDK, and whether anyone has
> attempted to port the pipeline forward. Being pinned to a superseded vendor library is a
> long-term liability — at some point IMEC will stop supplying 1.12.0.0.

### Built for an older Ubuntu

HSI Mosaic was built for Ubuntu 18 and runs on 22.04 only via symlinks onto a newer Pleora
library. Details in
[workstation-setup.md](../../../00-onboarding/workstation-setup.md).

## Datasheets

[`docs/hardware/Hyperspectral 3D/Snapshot SWIR HSI Hardware Manual.pdf`](../../../../hardware/Hyperspectral%203D/Snapshot%20SWIR%20HSI%20Hardware%20Manual.pdf)

Vendor specifications:
<https://www.imechyperspectral.com/en/cameras/snapshot-swir-4-x-4#specs>

> Note that the vendor URL above is for the **4 × 4** product, which is the 16-band
> variant. That is part of the evidence in the
> [variant question](#spectral-range-is-unresolved).

## Reorder

> TODO(verify): nothing recorded. Needed: IMEC's ordering and support contact — the HSI
> support portal is `hsisupport@imec.be` per
> [workstation-setup.md](../../../00-onboarding/workstation-setup.md) — the exact camera
> configuration as ordered including variant and lens, and lead time. A replacement would
> also need the same calibration file situation resolved. Consolidate into
> [reorder.md](../../../99-appendix/reorder.md).

## Related pages

- [ximea-vnir-hsi.md](ximea-vnir-hsi.md) — the companion hyperspectral camera
- [ibsen-nir-spectrometer.md](ibsen-nir-spectrometer.md) — this camera's illumination
  reference
- [hyper-drive.md](../software/hyper-drive.md) — the driver
- [Perception overview](../README.md) — the sensor set and spectral coverage
- [workstation-setup.md](../../../00-onboarding/workstation-setup.md) — the four vendor
  libraries
- [power-on.md](../../../02-operations/power-on.md) — step 7
- [glossary.md](../../../00-onboarding/glossary.md) — spectral radiance, reflectance, cube
