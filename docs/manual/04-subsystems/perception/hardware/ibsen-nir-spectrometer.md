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
| Spectrometer serial | **60044** |
| PCB serial | **reads 0** — see [Known issues](#the-pcb-serial-and-firmware-read-suspiciously-low) |
| Firmware | **2** |
| Detector type, as reported | **4** |

### As reported by the instrument

Read from the driver's startup output. Authoritative for this unit; the datasheet
describes the product line.

| | |
| --- | --- |
| Pixels per image | 256, read as pixels 0–255 |
| Full calibrated range | 364.17 – 1961.79 nm |
| **Usable range** | **901 – 1701 nm** — the driver's printed bounds |
| Mean sampling | 6.27 nm per pixel |
| ADC programmable gain | 32 |
| ADC offset | 17 |
| HW_TYPE | 0 |

**Wavelength calibration coefficients**, a 4th-order polynomial in pixel index:

```
c0  +1.9617907E+03
c1  -3.2025197E+00
c2  -1.6333527E-02
c3  +2.9469965E-05
c4  -4.9083832E-08
c5  +0.0000000E+00
```

λ(p) = c0 + c1·p + c2·p² + c3·p³ + c4·p⁴, giving 1961.79 nm at pixel 0 and 364.17 nm at
pixel 255.

> **Wavelengths run in descending order.** Pixel 0 is the longest wavelength.

### Which pixels are the useful ones

This resolves the "only the central 128 pixels are used" note precisely.

The calibration polynomial spans 364–1962 nm across all 256 pixels, but the InGaAs
detector only responds across roughly 900–1700 nm. Applying the driver's printed bounds of
901–1701 nm selects **pixels 64 through 190 — 127 pixels.**

So all 256 pixels are read off the detector, and about half carry usable signal. The
"central 128" figure is correct and refers to that window.

> TODO(verify): confirm whether the driver publishes all 256 points or only the usable
> window. If it publishes 256, consumers need to know that roughly half the array is
> outside the detector's response and carries noise rather than signal.

**The real range is slightly wider than the datasheet figure** — documentation says
950–1700 nm, the driver uses 901–1701 nm.

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

A dark reference exists, but **not in this instrument's driver.**
[`spectrometer_drivers`](../software/spectrometer-drivers.md) publishes raw counts with no
dark subtraction. The reference lives in `hyper_drive`'s ambient-light node, as a
**hardcoded 305-element array** matching the length of the combined VNIR + NIR spectrum —
so it corrects the stitched spectrum, not this instrument individually. See
[hyper-drive.md](../software/hyper-drive.md#the-dark-spectrometer-reference-is-hardcoded).

Three consequences for this unit, which has the more temperature-sensitive detector:

**It is taken once, not periodically.** A reference baked into source cannot track drift —
and this is the instrument whose uncooled InGaAs dark current moves with temperature. See
[Known issues](#uncooled-detector-in-a-shared-enclosure).

**It is tied to 250 ms integration.** Dark counts scale with integration time, so changing
this unit's `integration_time` invalidates the NIR half of that array.

**It cannot be regenerated without editing code.** A generated file,
`point_spectra_dark_ref.npy`, exists in `hyper_drive` alongside a script that produces it —
and the node's `np.load` of it is commented out.

> TODO(verify): switch the ambient node to load the file, then regenerate it. That makes
> the dark reference reproducible and lets it be retaken when integration time or ambient
> temperature changes.

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

### The PCB serial and firmware read suspiciously low

At startup this unit reports **PCB serial 0** and **firmware 2**, where the VIS-NIR unit
reports PCB serial 58944 and firmware 265. The spectrometer serial reads correctly as
60044.

**Correct node-to-unit mapping is confirmed regardless.** The reported detector type is 4
here and 0 on the VIS-NIR unit, so the two nodes are talking to different instruments and
are not crossed — which was the risk worth ruling out, given matching keys off enumeration
order rather than serial number.

> TODO(verify): whether PCB serial 0 and firmware 2 are genuine values for a DISB-400, or
> a failed read. If genuine, nothing is wrong. If a failed read, something on this board's
> info page is not being retrieved correctly, and the same mechanism supplies the
> calibration coefficients — which do read plausibly, so this is probably benign. Ask Ibsen
> what a DISB-400 should report.

### The on-board temperature reads at full scale

Startup reports a temperature of **4093** on this unit and **4095** on the VIS-NIR. For a
12-bit ADC, 4095 is the maximum possible value — all bits set.

That is the signature of a saturated or disconnected channel rather than a plausible
temperature. The two readings differ by 2 counts, so something is being sampled, but at the
very top of the range.

**Consequence:** there is no usable on-board temperature telemetry. That matters here more
than on the VIS-NIR unit, because the uncooled InGaAs detector's dark current is
temperature-dependent and the obvious way to track that drift would have been this sensor.

The driver does read register 11 **every frame** and publishes it as `Spectra.temp`, so a
per-message temperature channel exists. Two things stop it being useful:

**The values look invalid**, sitting at or beside 12-bit full scale.

**The combiner discards the field.** `/combined_spectra` — the only topic the ambient
correction consumes — carries no `temp`, because `send_combined()` assigns only
wavelengths and data. See
[spectrometer-drivers.md](../software/spectrometer-drivers.md#the-combiner-drops-temp-and-integration_time).

> TODO(verify): establish whether register 11 needs a conversion the driver is not
> applying — Ibsen's DISB manual would say. If it does, a working temperature channel plus
> carrying `temp` through the combiner would make thermal drift trackable in the data
> rather than requiring a separate experiment. Until then it has to be characterized
> empirically — see below.

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
