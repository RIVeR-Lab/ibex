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
| [SICK picoScan 150](hardware/sick-picoscan-150.md) | 2D lidar | Ethernet, via router | Kairos box | Driver planned |
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
| Ximea VNIR HSI | TODO | TODO | TODO | Imaging |
| IMEC SWIR HSI | 1100–1700 nm **(disputed)** | 9 or 16 | TODO | Imaging, mosaic |
| Ibsen VIS-NIR | 500–1100 nm | 256 | 6.7 or 11.5 nm | Single point |
| Ibsen NIR | 950–1700 nm | 128 | 9.5 or 12.9 nm | Single point |

**The two spectrometers overlap by 150 nm**, from 950 to 1100 nm, and together span
500–1700 nm. The overlap is useful: it is a region where both instruments see the same
light, so it doubles as a consistency check on the pair.

> **The SWIR camera's range is disputed** — 1100–1700 nm or 1250–1700 nm depending on
> which variant is installed and which source is believed. If it is 1250 nm, there is a
> gap in imaging coverage between the two cameras that only the point spectrometers span.
> Resolving this is the first thing to do in this table. See
> [imec-swir-hsi.md](hardware/imec-swir-hsi.md).

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

> TODO(verify): three inputs to the numbers above are unconfirmed. The 1.71 m sensor height
> is summed as `0.5715 + 1.250 - 0.11`, but only the `-0.11` appears in the transform we
> have recorded. The claim that every other link in the chain has zero rotation is
> unverified. And the 25° is the design tilt in the TF tree — real installed tilt may
> differ, and should be checked with an inclinometer or by fitting the ground plane in a
> static cloud.

## Known issues spanning the subsystem

**The SICK picoScan has no driver yet.** It comes up with the Kairos box at
[power-on.md](../../02-operations/power-on.md) step 3 and is checked there, but nothing
runs against it. A driver is planned. Until it exists, the power-on check confirms a
sensor that nothing will use — worth knowing so nobody treats a failed check as a blocker.

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
