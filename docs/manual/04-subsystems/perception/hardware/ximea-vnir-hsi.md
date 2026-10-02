---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Ximea VNIR HSI

The visible and near-infrared hyperspectral camera. Serves [Perception](../README.md).

## Overview

A snapshot mosaic hyperspectral camera built on an IMEC sensor in a Ximea body, covering
the visible and near-infrared. Like the SWIR camera it captures a full spectral cube per
exposure rather than scanning, so it does not depend on vehicle motion.

It is the shorter-wavelength half of IBEX's hyperspectral pair. The
[IMEC SWIR camera](imec-swir-hsi.md) covers the longer band, and the
[VIS-NIR point spectrometer](ibsen-vis-nir-spectrometer.md) provides this camera's
illumination reference.

Mounted at the **far left** of the hyperspectral array on the roof; the SWIR camera is at
the centre.

> **This camera has not been calibrated.** No dark or light reference has been collected —
> see [Calibration](#calibration). Until that is done its output is uncorrected radiance,
> and the reflectance pipeline cannot work for this half of the spectrum. That is the most
> consequential fact on this page.

## Spectral range — resolved

**24 bands, 662.7 – 932.9 nm.** The band centres are logged by the driver and recorded
verbatim in
`hyper_drive/hyper_drive/numpy_ambient_light_calibration_scripts/write_camera_lamba.py`:

```
662.74  678.44  691.48  702.80  718.98  730.10  743.11  757.62
770.57  779.24  794.57  805.38  817.52  831.93  842.42  853.91
867.77  878.10  887.16  901.41  909.37  919.06  928.17  932.91
```

Spacing runs 4.7 to 16.2 nm — reasonably even, unlike the SWIR camera's.

That settles four conflicting figures from the source notes. The closest was 660–960 nm;
the 460–600 nm figure in the overview was wrong, and the vendor URL's 600–1000 nm
describes the product family rather than this unit.

### 24 bands from a 5 × 5 mosaic

A 5 × 5 mosaic has 25 filter positions and the camera produces 24 bands, so one position
is unused, duplicated, or discarded.

> TODO(verify): what the twenty-fifth position is. Likely a panchromatic or out-of-band
> channel dropped by the demosaicing context.

### Imaging coverage has a gap above this camera

This camera ends at 932.9 nm and the [SWIR camera](imec-swir-hsi.md) begins at 1119.5 nm,
leaving **186.5 nm unimaged**. Only the point spectrometers cover it, at a single point.

## Physical location on vehicle

Far left of the hyperspectral array, on the roof. The array also carries the SWIR camera
at its centre, with the Insta360 mounted above it and the Spectralon reference puck and
both spectrometer fibre ends alongside.

> TODO(verify): record the camera's orientation and look angle, and the ground footprint it
> covers. Same gap as on the SWIR camera — there is no hyperspectral frame in
> [tf-frames.md](../../../05-reference/tf-frames.md), and nothing records whether the two
> imagers view the same ground.

## Power source / rail

**USB bus power from Volta.** Not fed by the Compute and Sensing box.

| | |
| --- | --- |
| Voltage | 5 V |
| Current | 0.36 A |
| Power | 1.8 W |

That 5 V at 0.36 A is USB bus power, well inside USB 3's 900 mA budget — which confirms
the camera draws from Volta rather than from a vehicle rail. It therefore comes up and
goes down with Volta, not with the Compute and Sensing box.

Worth contrasting with the SWIR camera, which takes 18 W at 6 V from the box. The two
hyperspectral cameras are on entirely different supplies despite sitting on the same rack.

## Hardware specs

| | |
| --- | --- |
| Manufacturer | Ximea |
| Model | MQ022HG-IM-SM5X5-NIR2 |
| Sensor | IMEC snapshot mosaic, 5 × 5 |
| Sensor resolution | 2048 × 1088 |
| Region of interest | 2045 × 1085, offset (0,0) |
| **Per-band resolution** | **407 × 215** |
| Bands | 24 |
| Spectral range | 662.7 – 932.9 nm |
| Bit depth | 10-bit, max value 1023 |
| **Saturation value** | **1023** — full scale |
| Configured | 15 Hz, 10 ms integration |
| Spectral resolution (FWHM) | TODO(verify) — carried per band in the published cube |
| Supply | 5 V, 0.36 A, 1.8 W over USB |
| System ID | `13.7.8.4` |
| Serial number | TODO(verify) |

Unlike the SWIR camera, this one saturates at full scale — check cube maxima against 1023.

### Effective spatial resolution is much lower than 2048 × 1088

This is a snapshot *mosaic* sensor — the 5 × 5 filter pattern is tiled across the array, so
each band is sampled by one twenty-fifth of the pixels. 2048 × 1088 is the raw sensor;
**the published cube is 407 × 215 × 24.**

Anyone expecting 2048 × 1088 per band will be out by a factor of 25, and 407 × 215 is the
figure that matters for registration against the point cloud.

### Lens

From the camera's optical setup configuration in `hyper_drive`:

| | |
| --- | --- |
| Manufacturer | Edmund Optics |
| Spectral range | VNIR |
| Focal length | 25 mm |
| Aperture | f/1.4 |
| Exit pupil distance | 31.7 mm |
| Sensor rejection filter | Refractive index 1.7 |

Same 25 mm focal length as the SWIR camera's Navitar, but a much faster aperture — f/1.4
against f/2.8, two stops more light. That is consistent with the much shorter integration
time this camera runs: 10 ms against the SWIR's 60 ms.

> TODO(verify): minimum focus distance, which is not in the configuration. The SWIR
> camera's is 0.7 m.

## Additional components

- Power and trigger cables, included per the datasheet

> TODO(verify): **the second trigger cable on the vehicle.** Both hyperspectral cameras
> ship with one, and neither is recorded as being used. Two triggerable cameras on the same
> rack is the obvious route to synchronising them with each other — and nothing on IBEX
> currently shares a time base. Establish whether either cable is installed, and whether
> `hyper_drive`'s `synchronous_cameras_launch.py` achieves synchronisation in software or
> expects hardware triggering.

## Software

| Software | Role |
| --- | --- |
| [hyper-drive.md](../software/hyper-drive.md) | The ROS 2 driver. Also covers `hyper_drive_interfaces` |
| Ximea SDK | Vendor library, **LTS v4.32.0.0** |

Installation is in
[workstation-setup.md](../../../00-onboarding/workstation-setup.md), along with the three
IMEC-side libraries the SWIR camera needs. The same `hyper_drive` launch brings up both
cameras.

Verify the camera independently of ROS with Ximea's own sample tool:

```bash
/opt/XIMEA/bin/xiSample
```

### Data structure / output format

Radiance values. See [glossary.md](../../../00-onboarding/glossary.md) for how radiance
differs from reflectance, and why the missing calibration matters.

## Networking

Not applicable. USB 3 to Volta.

## Setup & calibration

### Software prerequisites

The Ximea SDK, plus the USB buffer limit raised — the camera drops frames at the default.
See [workstation-setup.md](../../../00-onboarding/workstation-setup.md), which installs a
systemd unit so this persists:

```bash
echo 0 | sudo tee /sys/module/usbcore/parameters/usbfs_memory_mb
```

### Calibration

**Not done**, and this is visible in the repository rather than merely undocumented:

| | Dark reference | Non-uniformity | Optical setup |
| --- | --- | --- | --- |
| `hyper_drive/config/imec/context/` | ✅ | ✅ dark + white | ✅ |
| `hyper_drive/config/ximea/context/` | ❌ **absent** | ❌ **absent** | ✅ |

The Ximea's demosaicing context contains no references, so **its cubes are not
flat-fielded** — unlike the SWIR camera's, whose references were captured on 2026-07-08.

The consequence compounds. `ambient_light_measurement` once applied camera white and dark
references itself, and that code was deliberately removed on the grounds that the cubes
are already flat-fielded upstream by the vendor pipeline. **That is true for the IMEC and
false for the Ximea** — so removing it left nothing in its place for this camera. See
[hyper-drive.md](../software/hyper-drive.md#why-camera-c_ref-was-removed).

The [VIS-NIR spectrometer](ibsen-vis-nir-spectrometer.md) exists to supply this camera's
illumination reference, and that pairing cannot produce reflectance from uncorrected
radiance.

> TODO(verify): capture dark and non-uniformity references for this camera.
> `hyper_drive/hyper_drive/hsi_sensor_calibration/light_reference.py` does exactly this
> for the IMEC and is the obvious starting point — it needs the device enumeration changed
> from `EM_IMEC` to `EM_XIMEA` and the ROI changed to 2045 × 1085. The procedure is
> otherwise the same: dark room, lens covered, then a uniform white surface.

## Known issues & fixes

### USB buffer limit

**Symptom:** dropped frames.

**Cause:** the default `usbfs_memory_mb` is too small for this camera's data rate.

**Fix:** set it to 0, meaning unlimited. Made persistent by a systemd unit — see
[workstation-setup.md](../../../00-onboarding/workstation-setup.md). **Installed.**

### Uncalibrated

Covered under [Calibration](#calibration). Unresolved.

## Datasheets

[`docs/hardware/Hyperspectral 3D/Ximea Snapshot VIS Hardware Manual.pdf`](../../../../hardware/Hyperspectral%203D/Ximea%20Snapshot%20VIS%20Hardware%20Manual.pdf)

Vendor page:
<https://www.ximea.com/products/hyperspectral-imaging/xispec-hyperspectral-miniature-cameras/imec-sm-range-600-1000-usb3-hyperspectral-camera>

> Note the filed manual is for the Snapshot **VIS**, while the installed camera is an
> **NIR2** variant. Those are different products in the same family. TODO(verify): confirm
> the manual matches the camera, and obtain the correct one if not — this may be part of
> why four spectral ranges are in circulation.

## Reorder

> TODO(verify): nothing recorded. Needed: Ximea's ordering contact, the exact model as
> ordered, lens details, and lead time. Consolidate into
> [reorder.md](../../../99-appendix/reorder.md).

## Related pages

- [imec-swir-hsi.md](imec-swir-hsi.md) — the companion hyperspectral camera
- [ibsen-vis-nir-spectrometer.md](ibsen-vis-nir-spectrometer.md) — this camera's intended
  illumination reference
- [hyper-drive.md](../software/hyper-drive.md) — the driver
- [Perception overview](../README.md) — the sensor set and spectral coverage
- [workstation-setup.md](../../../00-onboarding/workstation-setup.md) — the Ximea SDK and
  the USB buffer setting
- [power-on.md](../../../02-operations/power-on.md) — comes up with Volta, step 7
- [glossary.md](../../../00-onboarding/glossary.md) — radiance, reflectance, FWHM, cube
