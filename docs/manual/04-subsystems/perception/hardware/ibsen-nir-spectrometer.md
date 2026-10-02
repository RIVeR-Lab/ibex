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

**The instrument is mounted inside the Compute and Sensing box**, in the rear of the
vehicle. That is unusual and worth knowing: it is not out in the open where you would look
for a sensor. It is protected from weather and impact, and reaching it means opening the
box.

**Light reaches it by fibre from the roof.** The fibre runs from the box up to the top of
the vehicle, where its end and the reference puck are mounted together, next to the
cameras.

That co-location is deliberate and is what makes the measurement valid: the puck sits in
the same light and the same shade as the scene the cameras are imaging. An illumination
reference measured somewhere differently lit would correct the imagery toward the wrong
answer.

| Piece | Location |
| --- | --- |
| Spectrometer body and DISB-400 board | Inside the Compute and Sensing box, rear of vehicle |
| Fibre optic cable | This unit's own, routed from the box to the roof |
| Spectralon reference puck | Roof, alongside the cameras. **Shared with the VIS-NIR unit** |

Each spectrometer has its own fibre; both view the same panel. That means the two
instruments share a reference surface, so the 150 nm where their bands overlap is a real
consistency check between them — and it also makes the puck a single point of failure for
both channels at once.

The reference is a **Spectralon** puck — a near-100% diffuse reflectance panel, which is
the right material for this: its reflectance is high, flat across wavelength, and
characterized.

> TODO(verify): record its grade and nominal reflectance, and whether it carries a
> calibration certificate. Also record whether it is cleaned or replaced on any schedule —
> Spectralon degrades with dirt and UV exposure, and a soiled panel biases every
> correction made against it.

> TODO(verify): record the fibre routing and its bend radius constraints. Optical fibre has
> a minimum bend radius below which it loses signal or breaks, and a run from a sealed box
> to the roof passes through at least one point where it can be pinched.

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

### Determining which slit is fitted

The resolution is either 9.5 nm or 12.9 nm depending on slit width, and the difference
matters for any spectral analysis. The slit is fixed at order and cannot be changed.

Three ways to find out, easiest first:

**1. The purchase record.** The slit width is a configuration option specified at order,
so it is on the quote, the order confirmation, or the packing documentation. This is the
definitive answer and costs nothing.

**2. Ask Ibsen.** The driver prints the PCB serial at startup:

```bash
ros2 launch spectrometer_drivers ibsen_launch.py
```

Ibsen can look up the as-built configuration from that serial. Their contact is on the
[vendor page](https://ibsen.com/productinfo/pebble-nir/).

**3. Measure it.** Illuminate the fibre with a narrow-linewidth NIR source — a 1550 nm
telecom laser diode is ideal, since its linewidth is negligible against either candidate
resolution, so the measured peak width *is* the instrument response. Record a spectrum,
fit a Gaussian to the peak, and convert its FWHM from pixels to nanometres.

> Be aware this is marginal. With 128 usable pixels across 750 nm the sampling is about
> 5.9 nm per pixel, so 9.5 nm FWHM is ~1.6 pixels and 12.9 nm is ~2.2 pixels. Both are
> undersampled, and distinguishing them requires sub-pixel Gaussian fitting on a peak only
> two pixels wide. Use this only to corroborate the paperwork, not in place of it.

Once known, record it in the specs table above, in the FWHM column of the spectral
coverage table in [Perception](../README.md), and in
[reorder.md](../../../99-appendix/reorder.md) — a replacement unit has to be ordered with
the same slit to behave identically.

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

A **dark reference is implemented in the driver** — see
[spectrometer-drivers.md](../software/spectrometer-drivers.md). That handles detector
offset, which matters for an uncooled InGaAs detector.

> TODO(verify): record when the dark reference is taken — once at startup, periodically, or
> on request — and how. If it is taken once at startup, it will not track the temperature
> drift described under [Known issues](#uncooled-detector-in-a-shared-enclosure).

> TODO(verify): whether an absolute radiometric calibration exists, as distinct from the
> dark reference. For this instrument's intended use it may not need one: dividing scene
> radiance by the reference puck's measured return cancels the instrument's response
> provided both are measured on the same instrument. That makes the puck's known
> reflectance the thing that matters, not an absolute scale. Confirm that is the intended
> approach, and record it — it is the difference between needing a calibration campaign and
> not.

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

### Uncooled detector in a shared enclosure

The G13913 is uncooled, so its dark current and noise vary with temperature. It sits inside
the Compute and Sensing box alongside the vehicle's power distribution.

The box is actively ventilated — **two 24 V fans, one on each side**, to move heat out.
That stops heat accumulating, but fans bring the interior toward ambient rather than below
it, so the detector still tracks outside temperature across a session and between a cool
morning and a warm afternoon.

> TODO(verify): whether that affects measurements in practice. Worth a controlled check:
> log spectra of the reference puck at the start and end of a long run, under stable
> lighting, and compare. If the baseline shifts, the dark reference in the driver needs to
> be taken often enough to track it rather than once at startup.

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

Consumables worth listing: replacement fibre of the correct core diameter, and the
reference puck, which degrades with dirt and UV exposure.

> TODO(verify): record Ibsen's ordering contact, the exact unit configuration as ordered
> including slit width, and lead time. Also record a source for replacement fibre and for
> the reference puck. Consolidate into
> [reorder.md](../../../99-appendix/reorder.md).

## Related pages

- [ibsen-vis-nir-spectrometer.md](ibsen-vis-nir-spectrometer.md) — the companion unit
- [spectrometer-drivers.md](../software/spectrometer-drivers.md) — the shared driver
- [Perception overview](../README.md) — the sensor set and spectral coverage
- [workstation-setup.md](../../../00-onboarding/workstation-setup.md) — `libft4222` and
  the udev rule
- [power-on.md](../../../02-operations/power-on.md) — step 7
- [glossary.md](../../../00-onboarding/glossary.md) — spectral range, resolution, FWHM,
  radiance, reflectance
