---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Ibsen Pebble NIR spectrometer

The near-infrared point spectrometer. Serves [Perception](../README.md).

## Overview

A point spectrometer measuring a full spectrum at a single location rather than across an
image. It covers 950–1700 nm.

**Its job is to measure the light falling on the scene, not the scene itself.** A
hyperspectral camera records reflected radiance, which depends on both the material and
the illumination. To get from radiance to reflectance — the property of the material,
which is what you actually want — you need to know the illumination.

This spectrometer provides it. Pointed at a material that reflects all incident light back
into the fibre, it measures the ambient light available in the scene. That measurement can
then be divided out of the hyperspectral imagery covering the same band.

**It is paired by wavelength, not by position.** Its 950–1700 nm coverage overlaps the
SWIR hyperspectral camera; the [VIS-NIR unit](ibsen-vis-nir-spectrometer.md) covers the
lower band and pairs with the VNIR camera. Together the two spectrometers span roughly
500–1700 nm, stitched into a single continuous spectrum by the driver.

> TODO(verify): confirm which hyperspectral camera this unit's output is actually used to
> correct, and whether that correction is implemented anywhere yet or is currently an
> intent. See [Perception](../README.md) — nothing is recorded as consuming the spectral
> products downstream.

## Physical location on vehicle

**Mounted inside the Compute and Sensing box**, in the rear of the vehicle.

That is unusual and worth knowing: the instrument is not out in the open where you would
look for a sensor. It is protected from weather and impact, and reaching it means opening
the box.

Light reaches it through a fibre optic cable from wherever the measurement point is.

> TODO(verify): **where does the fibre terminate, and what does it look at?** This is the
> most important missing fact on the page. For the ambient-light measurement to mean
> anything, the fibre end has to be looking at either the sky or a reference panel of known
> reflectance, in a known orientation. Record the mounting point, what it views, and
> whether anything shades or occludes it.

> TODO(verify): record the fibre routing from that point into the Compute and Sensing box,
> and its bend radius constraints. Optical fibre has a minimum bend radius below which it
> loses signal or breaks, and a fibre run into a sealed box is the kind of thing that gets
> pinched when the lid closes.

## Power source / rail

Fed by the **Compute and Sensing box**, which it also lives inside.

| | |
| --- | --- |
| Voltage | 6 V |
| Current | 0.133 A |
| Power | 0.8 W |

Data leaves over USB to Volta, so the instrument has power and data on separate paths —
cutting the Compute and Sensing box removes both, but shutting down Volta removes only
the data path.

## Hardware specs

| | |
| --- | --- |
| Manufacturer | Ibsen Photonics |
| Model | Pebble NIR |
| Spectral range | 950–1700 nm |
| Spectral resolution | 9.5 nm or 12.9 nm, depending on slit width |
| Detector | Hamamatsu G13913, uncooled InGaAs, 256 pixels |
| Pixels used | Central 128 only |
| Electronics board | **DISB-400** — the NIR-specific board |
| Interface | SPI native, USB 2.0 through an FTDI FT4222H bridge |
| Optical input | SMA 905 fibre coupling |
| Required fibre core | 400 µm or 600 µm |
| Supply | 6 V, 0.133 A, 0.8 W |
| Serial number | TODO(verify) — printed at driver startup |

> TODO(verify): **which slit is fitted?** The resolution is either 9.5 nm or 12.9 nm and
> the difference is substantial for any spectral analysis. The slit is fixed at order, so
> this is answerable from the purchase record or from Ibsen.

Two constraints set at order and not changeable afterwards:

**The SMA 905 coupling is factory-fixed.** It cannot be changed to another connector type
without returning the unit.

**The fibre core must exceed the 250 µm slit height**, which is why 400 µm or 600 µm is
required. A narrower fibre underfills the slit and loses signal.

With 128 usable pixels across 750 nm, the sampling interval is about 5.9 nm per pixel —
roughly 1.6 pixels per resolution element at 9.5 nm, or 2.2 at 12.9 nm.

## Additional components

- Fibre optic cable, 400 µm or 600 µm core, SMA 905

> TODO(verify): record the fibre's actual core diameter, length, and part number. It is a
> consumable in practice — fibres get pinched, scratched at the ferrule, and broken — and
> the wrong core diameter will not work.

## Software

| Software | Role |
| --- | --- |
| [spectrometer-drivers.md](../software/spectrometer-drivers.md) | The driver. Also covers `spectrometer_interfaces` |

Both spectrometers share one driver package and one launch file, and their outputs are
stitched into a single spectrum. Topics, services, message definitions, integration time,
and the staggered startup requirement are all on the software page.

Relevant here: **the driver prints this unit's PCB serial, firmware version, detector
type, and on-board calibration coefficients at startup.** That output is the fastest
confirmation that the hardware is communicating, and it is where the serial number above
can be read.

## Networking

Not applicable. SPI to USB, directly to Volta.

The FT4222H bridge presents as USB ID `0403:601c`. It needs a udev rule and the
`libft4222` library — see
[workstation-setup.md](../../../00-onboarding/workstation-setup.md).

## Setup & calibration

### Physical installation

Inside the Compute and Sensing box, with the fibre run to the measurement point.

### Wavelength calibration

**None required.** Factory calibration coefficients are stored on the DISB-400 board and
loaded automatically when the driver starts. They are printed at launch.

This is worth understanding: the wavelength-per-pixel mapping lives on the instrument, not
in our configuration. Replacing the electronics board replaces the calibration with it.

### Radiometric calibration

> TODO(verify): the wavelength mapping is handled; the intensity scale is not addressed
> anywhere. For this instrument to serve as an illumination reference, its counts have to
> relate to a physical quantity — or at least be stable and referenced against a panel of
> known reflectance. Establish whether a radiometric calibration exists, and whether a
> dark-current reference is taken. An uncooled InGaAs detector has significant dark
> current that varies with temperature.

### Integration time

NIR default is 250 ms, set in the launch file. That is ten times the VNIR default,
reflecting the weaker signal at longer wavelengths.

Set per node — see
[spectrometer-drivers.md](../software/spectrometer-drivers.md).

## Known issues & fixes

### The two spectrometers collide if started together

Both units enumerate as FT4222 devices, and bringing them up simultaneously produces blank
descriptions and an abort. The launch file staggers them.

This is a shared problem rather than a fault of this unit. Details and the known
limitation behind it are on
[spectrometer-drivers.md](../software/spectrometer-drivers.md).

### Uncooled detector

The G13913 is uncooled, so its dark current and noise vary with temperature — and it is
mounted inside a sealed box containing the vehicle's power distribution.

> TODO(verify): whether temperature inside the Compute and Sensing box affects
> measurements over a session. A box that warms up over several hours of operation will
> change this instrument's baseline. Worth a controlled check: log spectra of a fixed
> target at the start and end of a long run.

## Datasheets

Shared spec sheet covering both Pebble spectrometers:

[`docs/hardware/Hyperspectral 3D/Pebble Near Infrared and Visible Near Infrared Spectrometer Spec Sheet.pdf`](../../../../hardware/Hyperspectral%203D/Pebble%20Near%20Infrared%20and%20Visible%20Near%20Infrared%20Spectrometer%20Spec%20Sheet.pdf)

Vendor page: <https://ibsen.com/productinfo/pebble-nir/>

## Reorder

**The electronics board is model-specific.** A replacement board must be a **DISB-400** —
the NIR variant. The VIS-NIR unit uses a different board, and they are not
interchangeable.

The SMA 905 coupling is factory-fixed at order, so a replacement unit has to be specified
with the same optical input and the same slit width to behave identically.

> TODO(verify): record Ibsen's ordering contact, the exact unit configuration as ordered
> including slit width, and lead time. Also record a source for replacement fibre.
> Consolidate into [reorder.md](../../../99-appendix/reorder.md).

## Related pages

- [ibsen-vis-nir-spectrometer.md](ibsen-vis-nir-spectrometer.md) — the companion unit
- [spectrometer-drivers.md](../software/spectrometer-drivers.md) — the shared driver
- [Perception overview](../README.md) — the sensor set and spectral coverage
- [workstation-setup.md](../../../00-onboarding/workstation-setup.md) — `libft4222` and
  the udev rule
- [power-on.md](../../../02-operations/power-on.md) — step 7
- [glossary.md](../../../00-onboarding/glossary.md) — spectral range, resolution, FWHM,
  radiance, reflectance
