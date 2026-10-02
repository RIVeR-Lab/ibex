---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Ibsen Pebble VIS-NIR spectrometer

The visible and near-infrared point spectrometer. Serves [Perception](../README.md).

## Overview

A point spectrometer measuring a full spectrum at a single location rather than across an
image. It covers 500–1100 nm.

**Its job is to measure the light falling on the scene, not the scene itself.** It views a
Spectralon reference panel — a near-100% diffuse reflector — through a fibre, which gives
the illumination available in the scene. Dividing hyperspectral radiance by that reference
yields reflectance, a property of the material rather than of the lighting.

This is the **first half of a paired reference-channel architecture.** This unit covers the
lower band and pairs with the Ximea VNIR camera; the
[NIR unit](ibsen-nir-spectrometer.md) covers 950–1700 nm and pairs with the SWIR camera.
The driver stitches the two into one continuous spectrum spanning roughly 500–1700 nm.

**This is also the unit that starts first.** The two spectrometers cannot enumerate
simultaneously, so the launch file brings up VNIR and then delays NIR — see
[spectrometer-drivers.md](../software/spectrometer-drivers.md).

### The two bands overlap

| Instrument | Range |
| --- | --- |
| VIS-NIR, this unit | 500–1100 nm |
| NIR | 950–1700 nm |

They share **150 nm, from 950 to 1100 nm**. That is a useful property rather than a
problem — an overlap gives a region where both instruments see the same light, which is
what lets the stitch be checked and the two channels cross-referenced.

**The combiner resolves the overlap with a hard cut at 950 nm** — this unit contributes
everything below 950 nm, the NIR unit everything above. No crossfade, no averaging. See
[spectrometer-drivers.md](../software/spectrometer-drivers.md#how-the-spectra-are-combined).

So 901–950 nm is measured by both instruments and only this one is used; 950–1101 nm is
measured by both and only the NIR is used. **The overlap is therefore available as a free
consistency check** — compare the two raw topics across 901–1101 nm, and a disagreement
points at a calibration or reference problem in one of them.

## Physical location on vehicle

Same arrangement as the NIR unit.

| Piece | Location |
| --- | --- |
| Spectrometer body and DISB-105 board | Inside the Compute and Sensing box, rear of vehicle |
| Fibre optic cable | Routed from the box to the roof |
| Fibre end and Spectralon puck | Roof, alongside the cameras |

The puck sits in the same light and shade as the scene the cameras image, which is what
makes the reference valid.

**One Spectralon puck, two fibres.** Each spectrometer has its own fibre optic cable, and
both view the same panel. That is the right arrangement: a single reference surface means
the two instruments cannot disagree because of differing illumination or soiling, so the
150 nm overlap between them is a genuine consistency check on the instruments rather than
on their references.

It also means the puck is a single point of failure for both channels. A shaded, soiled, or
displaced panel invalidates the reference measurement across the whole 500–1700 nm range at
once.

## Power source / rail

Fed by the **Compute and Sensing box**, which it also lives inside. Data leaves over USB
to Volta.

| | |
| --- | --- |
| Voltage | 6 V |
| Current | 0.133 A |
| Power | 0.8 W |

Identical to the NIR unit, so the pair draws 1.6 W between them — negligible against
everything else in the box.

## Hardware specs

| | |
| --- | --- |
| Manufacturer | Ibsen Photonics |
| Model | Pebble VIS-NIR |
| Spectral range | 500–1100 nm |
| Spectral resolution | 6.7 nm (25 µm slit) or 11.5 nm (35 µm slit) |
| Detector | Hamamatsu S14739-20, CMOS, 256 spectral pixels |
| Electronics board | **DISB-105** — the VIS/VIS-NIR board |
| Interface | SPI native, USB 2.0 through an FTDI FT4222H bridge |
| Optical input | SMA 905 fibre coupling |
| Required fibre core | 400 µm or 600 µm |
| Supply | 6 V, 0.133 A, 0.8 W |
| Spectrometer serial | **58944** |
| PCB serial | **58944** |
| Firmware | **265** |
| Detector type, as reported | **0** |

### As reported by the instrument

Read from the driver's startup output. These are the authoritative values for this unit —
the datasheet describes the product line.

| | |
| --- | --- |
| Pixels per image | 256, read as pixels 0–255 |
| Calibrated range | **451.34 – 1101.42 nm** |
| Mean sampling | 2.55 nm per pixel |
| ADC programmable gain | 41 |
| ADC offset | 350 |
| HW_TYPE | 0 |

**Wavelength calibration coefficients**, a 4th-order polynomial in pixel index:

```
c0  +1.1014230E+03
c1  -1.9369562E+00
c2  -2.9704946E-03
c3  +5.6701515E-06
c4  -1.3484722E-08
c5  +0.0000000E+00
```

λ(p) = c0 + c1·p + c2·p² + c3·p³ + c4·p⁴, which gives 1101.42 nm at pixel 0 and
451.34 nm at pixel 255.

> **Wavelengths run in descending order.** Pixel 0 is the *longest* wavelength, not the
> shortest. Anyone indexing the spectrum array by position needs to know this — plotting
> it naively produces a mirrored spectrum.

**The real range is wider than the datasheet figure.** Documentation says 500–1100 nm; the
instrument's own calibration spans 451–1101 nm, and the driver prints 451 and 1101 as its
bounds. Treat 451–1101 nm as the operating range.

> TODO(verify): the note records launch parameters of `min 500.0` and `max 1100.0`, which
> do not match the 451 and 1101 the driver printed. Establish whether those parameters
> clip the output, are ignored, or have been changed. If the output is clipped to
> 500–1100 nm, usable pixels are being discarded at both ends.

Two constraints are fixed at order: the SMA 905 coupling cannot be changed, and the fibre
core must exceed the 250 µm slit height, which is why 400 µm or 600 µm is required.

### Compared with the NIR unit

Three differences worth knowing, beyond the wavelength range:

**A different detector technology.** This unit uses a silicon CMOS array; the NIR unit uses
uncooled InGaAs. Silicon has far lower dark current and is much less temperature-sensitive,
so this instrument is the better-behaved of the two inside a warm enclosure.

**All 256 pixels are spectral.** The NIR unit has 256 pixels but uses only the central 128.
This unit therefore samples at about 2.3 nm per pixel across its 600 nm range, against
5.9 nm per pixel for the NIR unit — roughly 2.5 times finer.

**A different board.** DISB-105 here, DISB-400 on the NIR unit. Not interchangeable.

### Determining which slit is fitted

The resolution is 6.7 nm with a 25 µm slit or 11.5 nm with a 35 µm slit. The slit is fixed
at order and cannot be changed.

**1. The purchase record.** The slit width is specified at order, so it is on the quote or
order confirmation. Definitive and free.

**2. Ask Ibsen.** The driver prints the PCB serial at startup; Ibsen can look up the
as-built configuration from it.

**3. Measure it.** More practical on this unit than on the NIR one, because the sampling is
finer. Illuminate the fibre with a mercury–argon pencil lamp, which produces sharp emission
lines across this range — 546.1 nm and 577.0 nm from mercury, 696.5 nm, 763.5 nm, and
811.5 nm from argon are all well inside 500–1100 nm and far narrower than either candidate
resolution. Fit a Gaussian to a line and convert its FWHM from pixels to nanometres.

> At 2.3 nm per pixel, 6.7 nm FWHM is about 2.9 pixels and 11.5 nm about 4.9 — both
> adequately sampled, so this measurement is meaningful here in a way it is not on the NIR
> unit.

Record the answer in the specs table above, in the FWHM column of the spectral coverage
table in [Perception](../README.md), and in
[reorder.md](../../../99-appendix/reorder.md).

## Additional components

- Fibre optic cable, 400 µm or 600 µm core, SMA 905 — this unit's own
- Spectralon reference panel, **shared with the NIR unit**

> TODO(verify): record the Spectralon puck's grade and nominal reflectance, and whether it
> carries a calibration certificate. Spectralon degrades with dirt and UV exposure, so also
> record whether it is cleaned or replaced on any schedule — a soiled panel biases every
> correction made against it.

## Software

| Software | Role |
| --- | --- |
| [spectrometer-drivers.md](../software/spectrometer-drivers.md) | The driver. Also covers `spectrometer_interfaces` |

This unit is the **VNIR streamer node**, launched with `wavelength_range:=vnir` and
wavelength parameters of 500.0 nm minimum and 1100.0 nm maximum. It publishes
`/ibsen_vnir/spectral_data`.

Default integration time is **25 ms** — a tenth of the NIR unit's 250 ms, reflecting the
stronger signal at these wavelengths.

> Launch-file numeric values must be written with a decimal point. `25.0` is accepted;
> `25` is rejected by ROS 2. See
> [spectrometer-drivers.md](../software/spectrometer-drivers.md).

The driver prints this unit's PCB serial, firmware version, detector type, and on-board
calibration coefficients at startup. That output is the fastest confirmation the hardware
is communicating, and where the serial number above can be read.

## Networking

Not applicable. SPI to USB, directly to Volta.

The FT4222H bridge presents as USB ID `0403:601c` — the same ID as the NIR unit's bridge,
which is the root of the enumeration problem described below. The bridge needs a udev rule
and the `libft4222` library; see
[workstation-setup.md](../../../00-onboarding/workstation-setup.md).

## Setup & calibration

### Physical installation

Inside the Compute and Sensing box, with the fibre run to the Spectralon puck on the roof.

### Wavelength calibration

**None required.** Factory calibration coefficients are stored on the DISB-105 board and
loaded automatically when the driver starts, printed at launch.

The wavelength-per-pixel mapping lives on the instrument, not in our configuration —
replacing the board replaces the calibration with it.

### Radiometric calibration

A dark reference exists, but **not in this instrument's driver.**
[`spectrometer_drivers`](../software/spectrometer-drivers.md) publishes raw counts with no
dark subtraction. The reference is a hardcoded array in `hyper_drive`'s ambient-light node,
covering the combined VNIR + NIR spectrum rather than either instrument alone — see
[hyper-drive.md](../software/hyper-drive.md#the-dark-spectrometer-reference-is-hardcoded).

This unit is the less exposed of the two: its silicon detector has low dark current and is
far more stable with temperature than the NIR unit's InGaAs, so a once-taken reference
holds up better here. Its half of that array is tied to 25 ms integration, though, so
changing `integration_time` invalidates it.

> TODO(verify): same question as on the NIR unit — whether an absolute radiometric
> calibration exists or is needed. If the intended approach is dividing scene radiance by
> the puck's measured return on the same instrument, the instrument response cancels and
> only the puck's reflectance matters.

### Integration time

25 ms by default, set per node in the launch file. This is the main field-adjustable
setting: too short and the spectrum is noisy, too long and it saturates in bright
conditions.

## Known issues & fixes

All three are shared with the NIR unit and are properties of the FT4222 bridge or the
driver rather than of this instrument. Details on
[spectrometer-drivers.md](../software/spectrometer-drivers.md).

### Enumeration race between the two spectrometers

**Symptom:** a node aborts with `INVALID NUMBER OF DETECTED DEVICES`, and device
descriptions come back blank.

**Cause:** both units present the same USB ID, and opening them simultaneously collides.

**Fix:** the launch file starts **this unit first** and delays the NIR unit by
`NIR_START_DELAY`, default 5 seconds. Increase the delay if collisions persist.
**Installed.**

### NUMBER OF DEVICES: 0

**Cause:** USB permissions. **Fix:** apply the udev rule and replug. See
[workstation-setup.md](../../../00-onboarding/workstation-setup.md).

### libft4222.so cannot be opened

**Cause:** `/usr/local/lib` is not on the dynamic loader's path. **Fix:** add it through
`ld.so.conf.d` and run `ldconfig`.

## Datasheets

Shared spec sheet covering both Pebble spectrometers:

[`docs/hardware/Hyperspectral 3D/Pebble Near Infrared and Visible Near Infrared Spectrometer Spec Sheet.pdf`](../../../../hardware/Hyperspectral%203D/Pebble%20Near%20Infrared%20and%20Visible%20Near%20Infrared%20Spectrometer%20Spec%20Sheet.pdf)

Vendor page: <https://ibsen.com/productinfo/pebble-vis-nir/>

## Reorder

**The electronics board is model-specific.** A replacement must be a **DISB-105** — the
VIS/VIS-NIR board. The NIR unit uses a DISB-400. They are not interchangeable, and the two
units otherwise look alike.

The SMA 905 coupling and the slit are fixed at order, so a replacement unit has to be
specified with the same optical input and slit width to behave identically.

Consumables: replacement fibre of the correct core diameter, and the Spectralon panel,
which degrades with dirt and UV.

> TODO(verify): record Ibsen's ordering contact, this unit's configuration as ordered
> including slit width, and lead time. Consolidate into
> [reorder.md](../../../99-appendix/reorder.md).

## Related pages

- [ibsen-nir-spectrometer.md](ibsen-nir-spectrometer.md) — the companion unit
- [spectrometer-drivers.md](../software/spectrometer-drivers.md) — the shared driver
- [Perception overview](../README.md) — the sensor set and spectral coverage
- [workstation-setup.md](../../../00-onboarding/workstation-setup.md) — `libft4222` and the
  udev rule
- [power-on.md](../../../02-operations/power-on.md) — step 7
- [glossary.md](../../../00-onboarding/glossary.md) — spectral range, resolution, FWHM,
  radiance, reflectance
