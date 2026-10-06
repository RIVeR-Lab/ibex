---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Perception

Everything IBEX uses to sense the world: two lidars, three cameras, two point
spectrometers, and a 360° camera, across six ROS 2 packages.

This is the largest subsystem in the manual by a wide margin — six of the ten packages and
eight of the sensors. It is also the least uniform: the sensors share almost nothing in
terms of interface, power, or software stack.

## What is on the vehicle

| Sensor | Measures | Interface | Power | Status |
| --- | --- | --- | --- | --- |
| [Ouster OS1-64](hardware/ouster-os1-64.md) | 3D point cloud + IMU | Ethernet, link-local | Compute and Sensing box | In use |
| [SICK picoScan 150](hardware/sick-picoscan-150.md) | 2D lidar, swept to 3D by a motor base | Ethernet, via router | Kairos box | Driver planned |
| [IMEC SWIR HSI](hardware/imec-swir-hsi.md) | Hyperspectral, SWIR | USB | Compute and Sensing box | In use |
| [Ximea VNIR HSI](hardware/ximea-vnir-hsi.md) | Hyperspectral, VNIR | USB | USB from Volta | In use |
| [Alvium RGB](hardware/alvium-rgb-camera.md) | Colour imagery | USB | USB from Volta | In use |
| [Ibsen NIR](hardware/ibsen-nir-spectrometer.md) | Point spectrum, NIR | SPI over FT4222H | Compute and Sensing box | In use |
| [Ibsen VIS-NIR](hardware/ibsen-vis-nir-spectrometer.md) | Point spectrum, VIS-NIR | SPI over FT4222H | Compute and Sensing box | In use |
| [Insta360 X4](hardware/insta360-x4.md) | 360° imagery | USB-C | Own battery + USB from Volta | In use |

> This table is a comparison view for navigation. **The hardware pages are authoritative**
> — if one disagrees with a row here, the hardware page wins and this row should be
> corrected. Expect to update this page as each hardware page is written.

Three different power sources and four different interface types across eight devices. That
asymmetry is why [power-on.md](../../02-operations/power-on.md) checks devices in groups
rather than as one list, and why killing the Compute and Sensing box takes out some sensors
and not others — see [estop-chain.md](../../01-safety/estop-chain.md).

## Why this sensor set

Two distinct jobs, and the sensors split along that line.

**Geometry** — where the ground is and what is on it. The Ouster OS1-64 does this: dense
3D point clouds for obstacle detection, terrain geometry, and the geometric half of
traversability estimation. Its point cloud also feeds lidar odometry, so it is doing
double duty for [state estimation](../state-estimation/).

**Material** — what the ground is made of. This is the unusual part of IBEX and the reason
for the spectrometers and hyperspectral cameras. Geometry tells you a surface is flat;
spectral response tells you whether it is dry soil, mud, or standing water covered in
vegetation. That distinction is what the marsh and swamp terrain at
[Olin](../../02-operations/field-sites.md) exists to test.

The RGB and 360° cameras are context rather than measurement: human-interpretable record
of what a run looked like.

### Spectral coverage

Four instruments measure spectra. Their combined coverage is roughly 450–1700 nm.

| Instrument | Spectral range | Bands | FWHM | Spatial |
| --- | --- | --- | --- | --- |
| Ximea VNIR HSI | 662.7–932.9 nm | 24 | TODO — read from a cube | Imaging, 407 × 215 per band |
| IMEC SWIR HSI | 1119.5–1650.1 nm | 9 | TODO — read from a cube | Imaging, 211 × 168 per band |
| Ibsen VIS-NIR | 451–1101 nm | 256 | 6.7 or 11.5 nm | Single point |
| Ibsen NIR | 901–1701 nm | 127, of 256 read | 9.5 or 12.9 nm | Single point |

**The two spectrometers overlap by 200 nm**, from 901 to 1101 nm, and together span
451–1701 nm. These figures come from the instruments' own calibration coefficients as
reported at driver startup, and are slightly wider than the datasheet ranges.

Both instruments view the same Spectralon panel through separate fibres, so across that
overlap they are measuring the same light.

The combiner resolves it with a **hard cut at 950 nm** — VNIR below, NIR above — so the
overlap is measured twice and half of it discarded. That makes it a free consistency check
on the pair: compare the two raw topics across 901–1101 nm and they should agree. Nobody
has done it, and a disagreement would point at a calibration problem in one instrument.

**Imaging coverage has a 186.5 nm gap; point coverage does not.** The VNIR camera ends at
932.9 nm and the SWIR camera begins at 1119.5 nm. The spectrometers span that gap
continuously, but at a single point rather than across an image.

All four ranges above come from the instruments themselves — the cameras' band centres as
logged by `hyper_drive`, and the spectrometers' on-board calibration coefficients. They
supersede the datasheet figures in the original notes, several of which were wrong.

**The SWIR camera's 9 bands are very unevenly spaced**: five between 1119 and 1207 nm,
then four spread to 1650 nm with gaps up to 189 nm. It is not a smooth spectrum and should
not be interpolated as one.

> **The VNIR camera is uncalibrated.** No dark or light reference has been collected, so
> its output is uncorrected radiance and the reflectance pipeline cannot work for the
> shorter half of the spectrum. The SWIR camera has a documented calibration procedure;
> this one does not. See
> [ximea-vnir-hsi.md](hardware/ximea-vnir-hsi.md#calibration).

The two cameras' FWHM figures travel in every cube as a per-band array, so
`ros2 topic echo /synchronous_cubes --once --no-arr` fills both cells — see
[hyper-drive.md](software/hyper-drive.md#message-definitions).

To be filled in as each hardware page is written. The two things to watch for when it is
populated: whether the VNIR and SWIR imagers meet cleanly or leave a gap in the middle,
and whether the point spectrometers overlap the imagers usefully or duplicate them.

**The spectrometers and the imagers are paired by band, and they do different jobs.** The
imagers measure radiance reflected from the scene. The spectrometers measure the
illumination falling on it, by viewing a reference that returns all incident light. One
divided by the other is reflectance — a property of the material rather than of the
lighting — which is what spectral analysis actually wants.

So the NIR spectrometer pairs with the SWIR camera by wavelength, and the VIS-NIR
spectrometer with the VNIR camera. Stitched, the two spectrometers span roughly
500–1700 nm.

> TODO(verify): whether this correction is implemented anywhere, or is currently an
> intent. Nothing is recorded as consuming the spectral products beyond recording them.

Definitions of spectral range, spectral resolution, FWHM, and spatial resolution are in
the [glossary](../../00-onboarding/glossary.md).

## Ouster mounting geometry

The Ouster is mounted nose-down rather than level, which is a deliberate choice about
coverage and has consequences worth understanding before using the data.

The tilt comes from the `sensor_rack` → `os_mount` static transform, where only the pitch
term is non-zero:

```
0.436 rad = 24.98° ≈ 25° nose-down
```

Positive pitch about +y tips the sensor's forward axis downward under REP-103, so the
sensor looks at terrain ahead of the vehicle rather than at the horizon.

### What that buys and costs

The sensor's beam altitude angles span +21.03° to −21.33° — asymmetric, and read from this
unit's own metadata rather than the datasheet's nominal 45°. With the sensor origin at
1.71 m above ground:

| | Angle below horizontal | Ground intersection |
| --- | --- | --- |
| Top beam | 3.95° | 24.8 m |
| Nominal axis | 24.98° | 3.67 m |
| Bottom beam | 46.31° | 1.64 m |

The 64 beams are not evenly spaced across that span, so these are the extremes rather than
a description of how returns distribute between them. The full per-channel angle list is
in the sensor metadata — see
[ouster-os1-64.md](hardware/ouster-os1-64.md).

So the usable ground-scanning footprint runs from roughly 1.6 m to 25 m ahead, biased
strongly toward near terrain. Good for traversability; weak for distant obstacle detection,
and the vehicle sees essentially no sky.

The far-edge figure is sensitive: at 3.78° below horizontal the rays are near-grazing, so
range resolution translates into poor height resolution out there. Treat 25 m as the
geometric limit rather than a useful working range.

### Consequences for anyone using the data

**Points arrive in a tilted frame.** Raw z in `os_sensor` or `os_lidar` is not height above
ground. Transform into `base_link` or `odom` before any ground-plane or height reasoning —
see [tf-frames.md](../../05-reference/tf-frames.md).

**Vehicle pitch adds to mount tilt dynamically.** Nose-down on a slope steepens the
look angle and pulls the footprint closer; nose-up flattens it and pushes it out. Relevant
on the grades at Olin.

**The 1.71 m height is traced, not assumed.** It sums three links in the transform chain
— `base_link` → `front_bumper` at +0.5715 m, `front_bumper` → `sensor_rack` at +1.250 m,
and `sensor_rack` → `os_mount` at −0.11 m. Since `base_link` sits at the rear axle centre
on the ground, that total is height above the ground datum. See
[tf-frames.md](../../05-reference/tf-frames.md).

> TODO(verify): the 25° is still the **design** tilt recorded in the transform tree, and
> the claim that every other link in the chain has zero rotation is still unconfirmed.
> Check the installed tilt with an inclinometer, or by fitting the ground plane in a static
> cloud on level ground.

## Known issues spanning the subsystem

**The SICK picoScan has no driver yet, and needs more than one.** It comes up with the
Kairos box at [power-on.md](../../02-operations/power-on.md) step 3 and is checked there,
but nothing runs against it. Until a driver exists, a failed check is not a session
blocker.

It is also not a simple driver job: the scanner is 2D and sits on a **motor-controlled
base** that sweeps it to produce 3D. That needs a lidar driver, motor control with
position feedback, and a dynamic transform — the only moving sensor frame on the vehicle.
See [sick-picoscan-150.md](hardware/sick-picoscan-150.md).

**CycloneDDS breaks the Alvium.** Despite VimbaX's documentation recommending it, setting
`RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` stops the camera streaming after it initializes.
The stack uses the default FastRTPS for this reason. Any DDS change has to be tested
against this camera.

**The vendor SDK stack is fragile.** IMEC's HSI Mosaic was built for Ubuntu 18 and runs on
22.04 only via symlinks onto a newer Pleora eBUS library — see
[workstation-setup.md](../../00-onboarding/workstation-setup.md). This is the single
largest source of setup time for a new researcher, and it is load-bearing for two cameras.

**USB permissions reset on replug.** The hyperspectral cameras use a `chmod` that does not
persist; the spectrometers use a udev rule that does. The inconsistency is deliberate but
means the cameras need attention after any reboot or cable change.

## Pages

### Hardware

| Page | Covers |
| --- | --- |
| [ouster-os1-64.md](hardware/ouster-os1-64.md) | The 3D lidar, its IMU, and its addressing |
| [sick-picoscan-150.md](hardware/sick-picoscan-150.md) | The 2D lidar. Currently unused |
| [imec-swir-hsi.md](hardware/imec-swir-hsi.md) | SWIR hyperspectral camera |
| [ximea-vnir-hsi.md](hardware/ximea-vnir-hsi.md) | VNIR hyperspectral camera |
| [alvium-rgb-camera.md](hardware/alvium-rgb-camera.md) | Allied Vision RGB camera |
| [ibsen-nir-spectrometer.md](hardware/ibsen-nir-spectrometer.md) | NIR point spectrometer |
| [ibsen-vis-nir-spectrometer.md](hardware/ibsen-vis-nir-spectrometer.md) | VIS-NIR point spectrometer |
| [insta360-x4.md](hardware/insta360-x4.md) | 360° camera |

### Software

| Page | Covers |
| --- | --- |
| [ouster-ros.md](software/ouster-ros.md) | Ouster driver. Forked submodule |
| [hyper-drive.md](software/hyper-drive.md) | Hyperspectral and RGB camera driver. Also covers `hyper_drive_interfaces` |
| [spectrometer-drivers.md](software/spectrometer-drivers.md) | Ibsen spectrometer drivers. Also covers `spectrometer_interfaces` |
| [insta360-ros-driver.md](software/insta360-ros-driver.md) | Insta360 driver. Forked submodule |

`hyper_drive_interfaces` and `spectrometer_interfaces` contain message and service
definitions only. They are documented within their parent package's page rather than
separately — a page whose entire content is "defines messages for X" is not worth a click.

## Open questions

| Question | Why it matters |
| --- | --- |
| Is the installed Ouster tilt actually 25°? | Every ground-footprint number above depends on it |
| What is the sensor height above ground, from a traced TF chain? | Same |
| Is anything consuming the spectral products beyond recording them? | Determines whether this subsystem has a live downstream consumer |

Two items that were open are now scheduled rather than unresolved: spectral coverage per
instrument will be filled in from the hardware pages, and the SICK picoScan is getting a
driver.

## Related

- [04-subsystems/README.md](../README.md) — the interconnect and processing diagrams
- [state-estimation/](../state-estimation/) — consumer of the Ouster point cloud and IMU
- [power/](../power/) — which box feeds which sensor
- [tf-frames.md](../../05-reference/tf-frames.md) — the frame tree and extrinsics
- [network.md](../../05-reference/network.md) — sensor addressing
- [ros-graph.md](../../05-reference/ros-graph.md) — topics and rates
- [glossary.md](../../00-onboarding/glossary.md) — radiometry and spectral terms
- [workstation-setup.md](../../00-onboarding/workstation-setup.md) — the vendor SDK
  installation this subsystem depends on
