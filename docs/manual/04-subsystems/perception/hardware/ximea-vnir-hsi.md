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

> **This camera is now calibrated.** `config/ximea/context/` carries a dark reference at
> 10.049 ms plus dark and white non-uniformity references, alongside the factory
> calibration file. This closes what was previously the most consequential gap on this
> page.

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

### 24 bands from a 5 × 5 mosaic — resolved

**Mosaic position 20, centred at 659.085 nm, is excluded.** It is marked `selected=false`
in the sensor calibration file and carries zero coefficients in every virtual band, because
it falls outside the camera's 656–974 nm bandpass filter.

25 physical filters, 24 usable bands.

### Nominal versus effective band centres

Two wavelength scales exist for the same bands, and they differ by 7 to 16 nm:

| | Range | What it is |
| --- | --- | --- |
| **Nominal** | 669.56 – 948.97 nm | From the sensor calibration XML, measured under collimated light |
| **Effective** | **662.74 – 932.91 nm** | What the HSI Mosaic pipeline reports on IBEX |

The difference is the **Fabry–Pérot angle-of-incidence correction**, computed from the
f/1.4 declared in `optical_setup.xml`. A faster lens means a wider cone of incoming light,
and a Fabry–Pérot filter's passband shifts to shorter wavelengths off-axis. The correction
is about ×0.983 to ×0.990, growing toward the long-wavelength end.

**The effective centres are the ones to use** — they describe the cubes the pipeline
actually produces. The nominal values are recorded here because they appear in the
calibration file and are easy to mistake for the real thing.

> This also means **the declared f-number is an input to band-centre computation**, not
> merely a record of the physical aperture. Changing it in `optical_setup.xml` changes the
> reported wavelengths.

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
| Spectral resolution (FWHM) | **6.03 – 19.42 nm**, median 8.45 — widens toward the red end |
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

**Done.** `config/ximea/context/` now contains a full reference set:

| File | Contents |
| --- | --- |
| `calibration_file/CMV2K-SSM5x5-665_975-13.7.8.4.xml` | Factory sensor calibration, modified 2022-09-26 |
| `dark_references/dark_reference_10.049000.raw` | Dark reference at **10.049 ms** |
| `non_uniformity/dark_reference.raw` | Flat-field dark |
| `non_uniformity/white_reference.raw` | Flat-field white |
| `optical_setup/optical_setup.xml` | Edmund Optics 25 mm, f/1.4 |

That supersedes the earlier state, in which this camera had no references and its cubes
were not flat-fielded.

> TODO(verify): **the dark reference is stamped 10.049 ms while the launch requests
> 10 ms.** The camera quantizes — the blank-cube metadata shows the same 10.049 figure —
> so this is the hardware's actual applied time. Confirm
> `ContextIntegrationTimeInDark(context, 10.0)` returns true against it.
> `light_reference.py` searches a range rather than testing one value, which suggests its
> author already hit this.

> TODO(verify): write a `README.md` into that directory from the template at
> `docs/manual/_templates/context-readme.md`. The IMEC contexts have one; this does not,
> and illumination and target are not recoverable from the XML.

## Known issues & fixes

### USB buffer limit

**Symptom:** dropped frames.

**Cause:** the default `usbfs_memory_mb` is too small for this camera's data rate.

**Fix:** set it to 0, meaning unlimited. Made persistent by a systemd unit — see
[workstation-setup.md](../../../00-onboarding/workstation-setup.md). **Installed.**

### Quantum efficiency is low, and worst at the long end

| | QE range | Median |
| --- | --- | --- |
| This camera | **2.45% – 17.84%** | 7.95% |
| [IMEC SWIR](imec-swir-hsi.md), for contrast | 40.39% – 52.73% | 48.40% |

**Seven of the 25 filters sit below 4% QE**, all at 854 nm and above: 854, 899, 914, 922,
932, 941, and 949 nm. That is silicon's response falling away at the red end, and it is
expected rather than a fault.

**The practical consequence:** the longest VNIR bands are the noisiest on the vehicle, by a
wide margin. Anything selecting spectral features should weight them accordingly, and the
f/1.4 lens — two stops faster than the SWIR's — is partly what compensates.

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
