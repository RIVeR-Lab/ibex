---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# spectrometer_drivers

The Ibsen point spectrometer driver. Serves [Perception](../README.md).

Drives both spectrometers over SPI through their FTDI bridges, stitches their output into
one continuous spectrum, and plots it live. The Ibsen protocol is implemented here
directly, so no Ibsen SDK is needed — only FTDI's `libft4222`.

## Source

| | |
| --- | --- |
| Repository | <https://github.com/RIVeR-Lab/spectrometer_drivers> |
| In this repo | `packages/spectrometer_drivers` — committed directly, not a submodule |
| Interfaces | `packages/spectrometer_interfaces` — must be built first |
| Build type | `ament_cmake`, with a C++ driver and two Python nodes |
| Original authors | Gary Lvov and Nathaniel Hanson, from Ibsen's Linux example |

## Fork status

Not a fork. Lab code, ported from ROS 1.

> TODO(verify): `package.xml` has `maintainer email="you@example.com"` and
> `license TODO` — both unfilled template values. The licence in particular should be set;
> the sibling packages are Apache-2.0.

## Description

Two spectrometers, one driver binary run twice. Each instance claims one FT4222 bridge,
reads the Ibsen DISB board's registers over SPI, triggers exposures, and publishes raw
counts with a wavelength axis derived from the board's own calibration coefficients.

A Python node then stitches the two spectra into one, and a third plots it.

## Capabilities

### Nodes

| Executable | Language | Node name in launch | Role |
| --- | --- | --- | --- |
| `spectral_data_streamer` | C++ | `ibsen_vnir`, `ibsen_nir` | The driver. Run once per spectrometer |
| `combine_ibsen.py` | Python | `spectra_combiner` | Stitches both spectra into `/combined_spectra` |
| `spectral_plot.py` | Python | `combined_plot` | Live matplotlib plot |

Internal node names differ from the launch names — the driver declares itself
`ibsen_driver` and the combiner `spectrum_combiner`. The launch file overrides both.

### What it does not do

The source note lists services `StartCollect`, `EndCollect`, `RequestOnce`, and `Light`.
**None of those are implemented.** The driver serves exactly one service,
`set_integration_time`.

All four **do** exist as `.srv` definitions in `spectrometer_interfaces` — they are built
and available to call, and nothing answers them. See [Services](#services).

**There is no dark-reference subtraction in this driver.** It publishes raw counts. The
dark reference lives in `hyper_drive`'s ambient-light node — see
[Where the dark reference actually lives](#where-the-dark-reference-actually-lives).

## Purpose

It is the only way to get data off these spectrometers. The Ibsen SPI protocol is
implemented here, so there is no vendor SDK dependency — which is unusual among IBEX's
sensors and worth preserving.

## Alternative software

None. Custom driver for a specific board.

## Launch / invocation

```bash
ros2 launch spectrometer_drivers ibsen_launch.py
```

Starts VNIR immediately, the combiner immediately, and NIR after a 5-second delay.

**Preconditions:**

- Compute and Sensing box powered, so both spectrometers have their 6 V
- `libft4222` installed and findable — see
  [workstation-setup.md](../../../00-onboarding/workstation-setup.md)
- **USB permissions.** Either the udev rule, or a one-off `chmod` on both device nodes.
  Without it the driver reports `NUMBER OF DEVICES: 0` and aborts

A single streamer can be run standalone for debugging one spectrometer.

## Topics

| Topic | Type | Publisher | Subscriber |
| --- | --- | --- | --- |
| `/ibsen_vnir/spectral_data` | `Spectra` | `ibsen_vnir` | `spectra_combiner` |
| `/ibsen_nir/spectral_data` | `Spectra` | `ibsen_nir` | `spectra_combiner` |
| `/combined_spectra` | `Spectra` | `spectra_combiner` | `combined_plot`, and `ambient_light` when the full pipeline runs |

All Reliable and Volatile. Spectra are small — 305 float32 pairs, a few kilobytes — so
Reliable costs nothing here, unlike the camera cubes.

The streamers publish on a relative `spectral_data` inside their own namespace, which is
how one binary serves two instruments without remapping.

Each streamer publishes on a relative topic inside its own namespace, which is how one
binary serves two instruments without remapping.

### Message contents

**`Spectra.msg`**, from `spectrometer_interfaces`:

| Field | Type | Populated by the driver? |
| --- | --- | --- |
| `header` | `std_msgs/Header` | ❌ **never set** |
| `data` | `float32[]` | ✅ |
| `wavelengths` | `float32[]` | ✅ |
| `integration_time` | `float32` | ✅ |
| `lamp_power` | `int32` | ❌ |
| `humidity` | `int32` | ❌ |
| `temp` | `int32` | ✅ |
| `fiber` | `int32` | ❌ |

**Half the message is unused.** `lamp_power`, `humidity`, and `fiber` anticipate a
calibration lamp, a humidity sensor, and a selectable fibre input — none of which exist on
IBEX. The interface package's own description says it covers "Ibsen, Hamamatsu, etc.", so
the schema was designed for a wider family of instruments than the two fitted here.

**Published points per instrument:**

| | Points | Wavelength span |
| --- | --- | --- |
| VNIR | **256** — every pixel | 451 – 1101 nm |
| NIR | **128** — a hardcoded window | 902 – 1702 nm |
| Combined | **305** | 451 – 1702 nm |

Both arrays are reversed before publishing, so **wavelengths ascend** in the published
message even though pixel 0 is the longest wavelength.

### The header exists and is never set

`Spectra` carries a `std_msgs/Header`. **Neither the streamers nor the combiner populate
it**, so every spectrum goes out with a zero timestamp and an empty frame.

**Consequence:** there is no way to tell when a spectrum was captured, and no way to check
that a spectrum and a camera cube are contemporaneous. `hyper_drive`'s ambient correction
pairs the most recent spectrum with the most recent cube with no temporal test at all —
and given the NIR half of the combined spectrum updates at ~2 Hz, that pairing can be
several hundred milliseconds stale without anything noticing.

> TODO(verify): stamp the header at acquisition in the streamer, and carry the earlier of
> the two stamps through the combiner. The field is already there, so this is a few lines.
> Same class of gap as the missing `frame_id` on cubes — see
> [hyper-drive.md](hyper-drive.md#cubes-carry-no-frame_id).

### The combiner drops temp and integration_time

`send_combined()` constructs a fresh `Spectra` and assigns **only** `wavelengths` and
`data`. The `temp` and `integration_time` values that both streamers do populate are lost.

**Consequence:** `/combined_spectra` is the only topic `hyper_drive`'s ambient correction
subscribes to, so the one consumer that might care about detector temperature cannot see
it. That matters for the uncooled NIR instrument — see
[ibsen-nir-spectrometer.md](../hardware/ibsen-nir-spectrometer.md).

> TODO(verify): carry `temp` and `integration_time` through, or expose them as separate
> fields for each half. Two instruments stitched into one message means one scalar field
> can only represent one of them, which is presumably why they were dropped rather than
> an oversight.

## Services

**One service is served. Five are defined.**

| Service | Type | Served? |
| --- | --- | --- |
| `set_integration_time` | `Integration` — `float32 data` → `bool response` | ✅ by each streamer |
| — | `StartCollect` — `string request` → `bool response` | ❌ defined, nothing serves it |
| — | `EndCollect` — `string request` → `SpectraArray response` | ❌ |
| — | `RequestOnce` — `string request` → `Spectra response` | ❌ |
| — | `Light` — `int32 data` → `bool response` | ❌ |

`set_integration_time` is relative, so `/ibsen_vnir/set_integration_time` and
`/ibsen_nir/set_integration_time`. The handler sets `response = true` first and only flips
it on an exception, so a silent hardware failure still reports success.

The other four are ROS 1 leftovers. Together they describe a **batch collection
workflow** — start a collection, request single spectra, end it and receive the whole set
as a `SpectraArray` — that was never ported. `SpectraArray` exists only as `EndCollect`'s
response type and is therefore entirely unused.

`Light` takes an `int32`, implying a dimmable lamp. Nothing on IBEX has one, which closes
that question: the service is a definition without an implementation or hardware.

> TODO(verify): decide whether the batch workflow is wanted. If it is, `RequestOnce` and
> `StartCollect`/`EndCollect` are the natural interface for a deliberate calibration
> capture rather than streaming continuously. If it is not, remove the four definitions and
> `SpectraArray` — unimplemented services in a built interface package read as available
> functionality.

> TODO(verify): service calls are only serviced between acquisitions, because the driver
> runs `spin_some()` inside its own `while` loop rather than using an executor. At the
> NIR's 250 ms integration time that is up to half a second of latency.

## Parameters

| Parameter | Default | VNIR in launch | NIR in launch | Effect |
| --- | --- | --- | --- | --- |
| `integration_time` | 10.0 | 25.0 | 250.0 | Exposure, ms |
| `wavelength_range` | `""` | `vnir` | `nir` | **Selects which spectrometer this instance claims** |
| `min_wavelength` | 0.0 | 500.0 | 900.0 | **No effect — see below** |
| `max_wavelength` | 0.0 | 1100.0 | 1700.0 | **No effect — see below** |

### min_wavelength and max_wavelength are dead parameters

They are declared, read into member variables, and **never used anywhere else in the
driver.** Setting them changes nothing.

This resolves an open question from both spectrometer hardware pages: the launch file's
500–1100 nm for the VNIR does **not** clip its output. The VNIR publishes all 256 pixels
across its full calibrated 451–1101 nm range, which is exactly what the driver printed at
startup.

The NIR's range is set by hardcoded values in the code instead, not by these parameters.

> TODO(verify): either wire these parameters up or remove them. A parameter that looks
> like it controls the output range and does not is worse than no parameter — the launch
> file currently documents a behaviour that does not exist.

Launch-file numeric values must be written with a decimal point. `25.0` is accepted; `25`
is rejected, because the parameter is declared as a float and ROS 2 will not coerce an
integer override.

## Non-ROS interfaces

**SPI over FTDI FT4222H**, two interfaces per spectrometer.

| | |
| --- | --- |
| USB ID | `0403:601c` |
| Interfaces used | `FT4222 A` → CS1 (bulk data), `FT4222 B` → CS0 (registers) |
| SPI clock | 60 MHz system clock, divided by 4 |
| Latency timer | 20 |
| USB transfer sizes | 4096 out, 65536 in |

Each FT4222 chip exposes four interfaces, A through D. The driver collects only those
described as `FT4222 A` or `FT4222 B`, so two chips yield four usable handles.

### DISB register map, as used

| Register | Read | Register | Read |
| --- | --- | --- | --- |
| 1 | PCB serial | 12 | Number of pixels ready |
| 2 | Hardware type | 13, 14 | Trigger delay, LSB and MSB |
| 3 | Firmware version | 15 | ADC programmable gain |
| 4 | Detector type | 16 | ADC offset |
| 5 | Pixels per image | 22 | Spectrometer serial |
| 6 | Calibration character count | 23 | First pixel |
| 7 | Calibration coefficients | 24 | Last pixel |
| 11 | Temperature | | |

Written: register 8 for sensor control — `0x10` resets the image buffer, `0x01` triggers
an exposure — and registers 9 and 10 for integration time, LSB and MSB.

**Integration time is in 200 ns increments:** the driver computes
`requestTime_ms × 1e6 / 200`, so 25 ms becomes 125,000 increments and 250 ms becomes
1,250,000.

### Temperature is published, at full scale

The driver reads register 11 every frame and publishes it as `msg.temp`. The startup values
are 4095 for the VNIR and 4093 for the NIR — at or adjacent to the 12-bit maximum.

So the field exists and is per-frame, which would make thermal drift easy to track if the
values were meaningful. They do not appear to be. See
[ibsen-nir-spectrometer.md](../hardware/ibsen-nir-spectrometer.md).

> TODO(verify): whether register 11 needs a conversion the driver is not applying. Ibsen's
> DISB manual would say. A working temperature channel would be genuinely useful for the
> uncooled NIR detector.

## How the two instruments are told apart

This is the most fragile part of the driver and it explains the startup behaviour.

`TestDevices()` opens each pair of handles in turn, reads its calibration coefficients,
generates the wavelength axis, and classifies by its extremes:

```cpp
if (minVal < 460 && maxVal < 1105) currentDevice = "vnir";
else                               currentDevice = "nir";
```

The installed units land as:

| | min | max | Classified |
| --- | --- | --- | --- |
| VNIR | 451 | 1101 | `vnir` ✅ |
| NIR | 902 | 1702 | `nir` ✅ |

**It works, with 9 nm of margin.** The VNIR's minimum is 451 against a threshold of 460.

> TODO(verify): a replacement VNIR whose calibration began above 460 nm would be
> classified as `nir`, and both nodes would then fight over the same instrument. Classify
> by detector type from register 4 instead — it reads 0 for the VNIR and 4 for the NIR,
> which is unambiguous and already being read.

**The printed numbers after the wavelength dump are these min and max values.** The
mysterious trailing `451` / `1101` and `901` / `1701` in the startup log are
`TestDevices()` printing its classification inputs, not an error.

### Why the staggered start is needed

`NUMBER OF DEVICES` counts handles whose description reads `FT4222 A` or `FT4222 B`. A
handle already claimed by another process returns a **blank description**, so it is not
counted.

That is why the earlier startup logs read as they do:

| | Devices seen | Why |
| --- | --- | --- |
| VNIR, starting first | 4 | Both chips free |
| NIR, starting 5 s later | 2 | The VNIR holds two; its entries come back blank |

If both start simultaneously, each tries to open devices the other is probing, the opens
fail, the descriptions come back blank, and `devices.size() % 2 != 0` aborts the node with
`INVALID NUMBER OF DETECTED DEVICES`.

So the 5-second `NIR_START_DELAY` is not a timing nicety — the second node depends on the
first having already claimed its handles.

## How the spectra are combined

`combine_ibsen` subscribes to both streamers and publishes at a fixed rate.

**The overlap is resolved by a hard cut at 950 nm:**

```python
mask = np.array(self.ibsen_vnir.wavelengths) < 950    # VNIR below 950
mask = np.array(self.ibsen_nir.wavelengths) > 950     # NIR above 950
```

| Contribution | Points |
| --- | --- |
| VNIR, below 950 nm | 184 |
| NIR, above 950 nm | 121 |
| **Combined** | **305** |

That 305 matches the length of the hardcoded dark reference in `hyper_drive`'s ambient
node exactly, so the two are consistent.

**This resolves the overlap question** raised on both spectrometer hardware pages: no
crossfade, no averaging, a hard cut. The 200 nm where both instruments see the same light,
901–1101 nm, is **measured twice and half discarded** — which means it remains available
as a cross-check even though the combined product does not use it.

> Values exactly equal to 950 nm are dropped by both masks, since the comparisons are
> strict. Harmless in practice because no band centre lands exactly there.

### The combined rate hides a 10:1 staleness

The combiner republishes at 20 Hz regardless of its inputs. The streamers each sleep for
their integration time after publishing, so their period is roughly twice that:

| | Integration | Approximate rate |
| --- | --- | --- |
| VNIR | 25 ms | ~20 Hz |
| NIR | 250 ms | ~2 Hz |
| Combined | — | 20 Hz |

**So roughly nine of every ten combined spectra carry NIR data that has already been
published.** The combiner holds the last message from each side and re-stitches on a
timer.

That is not wrong — but anything consuming `/combined_spectra` and treating consecutive
messages as independent samples will overcount the NIR half tenfold. It matters most for
the ambient correction, which runs against every cube.

> TODO(verify): whether the correction should be throttled to the NIR rate, or whether the
> illumination reference changes slowly enough that stale NIR data is acceptable. Ambient
> light outdoors can change faster than 2 Hz when clouds move.

## Known issues & fixes

### The NIR data and its wavelength axis are offset by one pixel — unresolved

Two separate pieces of code select the NIR's usable window, and they disagree:

| | Selection | Pixels kept | Count |
| --- | --- | --- | --- |
| Wavelength axis, in `GenerateWavelengths` | `λ >= 900 && λ <= 1702` | **63 – 190** | 128 |
| Data, in `run()` | `pixels.begin()+62` to `+190` | **62 – 189** | 128 |

Both are 128 elements, so nothing errors and the arrays line up by length. But after both
are reversed, **`data[k]` is pixel 189−k while `wavelengths[k]` is the wavelength of pixel
190−k.** Every NIR data point is labelled with its neighbour's wavelength.

**Consequence:** a systematic wavelength error across the whole NIR spectrum, of one pixel
— about 6 to 7 nm at this instrument's 6.3 nm sampling. That is comparable to its own
spectral resolution of 9.5 or 12.9 nm, so it is roughly a half-resolution-element shift,
in a consistent direction.

**Fix:** change the data slice to `pixels.begin()+63` through `+191` so it matches the
wavelength filter. The wavelength filter is the one derived from calibration; the 62 and
190 in the slice are magic numbers.

> TODO(verify): confirm the direction of the error before correcting, and check whether
> anything downstream has been tuned against the current offset. The reference spectra in
> `hyper_drive/bag_files/numpy_files/` were extracted from live data, so they carry the
> same offset — fixing the driver without regenerating them would introduce a mismatch.

### Do not run `ibsen_launch.py` and `ambient_light_launch.py` together

**`ambient_light_launch.py` already contains this package's entire spectrometer stack** —
both streamers and the combiner, copied from `ibsen_launch.py` with the same parameters.
Launching both therefore starts everything twice.

A capture taken with both running showed **two publishers on `/combined_spectra`, both
named `spectra_combiner`**, with different GIDs — two live instances of the combiner.
`combined_plot` was also present, and only `ibsen_launch.py` starts that.

**Consequence:** the ambient-light correction in `hyper_drive` receives duplicate spectra
at roughly twice the intended rate, with the same content arriving twice. It does not
error, because each callback simply overwrites the stored spectrum — so the symptom is
invisible.

The streamers cannot both run, since the second pair would fail to claim the FT4222
handles. So the likely state is one working set of streamers feeding two combiners.

**Use one launch file.** For the full pipeline, `ambient_light_launch.py`. For
spectrometers alone — debugging, or a calibration capture — `ibsen_launch.py`.

> TODO(verify): the duplication is a copy-paste between launch files. Better would be for
> `ambient_light_launch.py` to include `ibsen_launch.py` rather than restate it, so the
> parameters cannot drift apart and the overlap is structurally impossible. Worth checking
> they have not already diverged: both currently set VNIR to 25 ms and NIR to 250 ms, but
> nothing enforces that.

### `NUMBER OF DEVICES: 0`

**Cause:** USB permissions. The FT4222 handles enumerate but their descriptors cannot be
read, so none match `FT4222 A`/`B`.

**Fix:** the udev rule. See
[workstation-setup.md](../../../00-onboarding/workstation-setup.md).

> This has recurred in practice — the rule was found missing and a manual `chmod` on both
> device nodes was needed. Worth confirming the rule is installed and persists.

### The enumeration race

Covered under [Why the staggered start is needed](#why-the-staggered-start-is-needed).
Mitigated by `NIR_START_DELAY`, default 5 s. Increase it if collisions persist.

**Known limitation:** node-to-instrument matching depends on enumeration order and the
A/B descriptions rather than on serial number. It is inherently order-sensitive.

### Calibration coefficient strings are not null-terminated

`CombinedCalibrationChars[14]` is filled with exactly 14 characters and then passed to
both `printf("%s")` and `strtod()` without a terminator.

It works because each coefficient is exactly 14 characters of valid number text and
`strtod` stops at the first character it cannot parse — but both calls read past the
buffer.

> TODO(verify): make it `char[15]` with an explicit `'\0'`. Low risk, trivial fix.

### Python nodes do not shut down cleanly

`spectral_plot.py` holds the main thread in matplotlib and spins ROS on a background
thread. On `Ctrl-C` it has needed `SIGKILL` — fifteen seconds after `SIGINT` — and
`combine_ibsen.py` calls `rclpy.shutdown()` on an already-shutdown context and exits
with `RCLError`.

**Consequence for operations:** `ros2 node list` can still show `/combined_plot` and
`/spectra_combiner` after both processes are dead, because a `SIGKILL`ed process never
sends its DDS departure notice. The "confirm `ros2 node list` is empty" check in
[power-off.md](../../../02-operations/power-off.md) is therefore not reliable for this
stack.

> TODO(verify): guard the double shutdown in `combine_ibsen.py`, and handle
> `ExternalShutdownException` in the plot node's spin thread.

### Times New Roman is not installed

`spectral_plot.py` sets `font.family` to Times New Roman, which prints two `findfont`
warnings and falls back to DejaVu Sans. Cosmetic.

### Where the dark reference actually lives

**Not in this driver.** The streamers publish raw counts with no dark subtraction.

The dark reference is in `hyper_drive`'s `ambient_light_measurement.py`, as a **hardcoded
305-element array** — matching the combined spectrum length exactly. A generated file,
`point_spectra_dark_ref.npy`, exists in that package and is **not loaded**; the `np.load`
call is commented out. See
[hyper-drive.md](hyper-drive.md#the-dark-spectrometer-reference-is-hardcoded).

So the dark reference applies to the **combined** spectrum, not to either instrument
individually, and it cannot be regenerated without editing source.

> TODO(verify): this also means the dark reference was taken at particular integration
> times — 25 ms VNIR and 250 ms NIR. Dark counts scale with integration time, so changing
> either integration time invalidates the corresponding half of the dark array. Record
> that coupling, as with the IMEC's 60 ms dark reference.

## Understanding the software

**One binary, two instances, selected by parameter.** `wavelength_range` is the only thing
distinguishing them, and it drives both the device classification and the NIR's
pixel-window special case.

**The acquisition loop is synchronous and self-paced.** Each iteration resets the buffer,
triggers an exposure, polls register 12 until the framebuffer is full or one second
elapses, reads the pixels over SPI, stitches byte pairs into 16-bit counts, reverses,
publishes, then sleeps for the integration time. A timeout logs
`Timeout error when capturing spectrum` and continues with whatever is in the buffer.

**The wavelength axis is computed once at startup** from the DISB board's calibration
coefficients, as a 4th-order polynomial in pixel index, and republished unchanged with
every message. It is not recomputed, so a board swap requires a restart.

**`GenerateWavelengths` is convoluted.** It allocates a 128-element vector of zeros, then
appends matching wavelengths after them with `back_inserter`, then removes all zeros. It
works, but any genuine wavelength of exactly 0 would be removed — not a practical risk.

**The wall of run-together numbers in the startup log** is `printf("%f", i)` over every
wavelength with no separator. Harmless, but it is what makes the log hard to read.

## Dependencies

**Ibex packages**

- `spectrometer_interfaces` — two messages and five services. **Build first.** A proper
  separate interface package, so consumers like `hyper_drive` need not build this driver

> TODO(verify): both this package and `spectrometer_interfaces` carry
> `maintainer email="you@example.com"` and `license TODO` in their `package.xml`. The
> licence matters — the sibling packages are Apache-2.0, and a package built and
> distributed with `TODO` as its licence is a real problem for a lab that publishes. See
> [ownership.md](../../../00-onboarding/ownership.md).

**ROS**

- `rclcpp`, `rclpy`, `std_msgs`

**Python**

- `numpy`, `matplotlib`

**External, not ROS**

- **`libft4222`** — FTDI's library, with D2XX built in on Linux. CMake searches
  `/usr/local/include` and `/usr/local/lib` and **fails the build with a clear message** if
  it is absent. A standalone `libftd2xx` is looked for and treated as optional, because on
  Linux the `FT_*` symbols live inside `libft4222`
- `Threads` and `${CMAKE_DL_LIBS}`, linked explicitly to avoid undefined references

**Hardware that must be powered**

Both spectrometers, from the Compute and Sensing box.

**Build order**

```bash
cd ~/ibex_ws
colcon build --packages-select spectrometer_interfaces
source install/setup.bash
colcon build --packages-select spectrometer_drivers
source install/setup.bash
```

## Related pages

- [ibsen-nir-spectrometer.md](../hardware/ibsen-nir-spectrometer.md) and
  [ibsen-vis-nir-spectrometer.md](../hardware/ibsen-vis-nir-spectrometer.md) — the two
  instruments
- [hyper-drive.md](hyper-drive.md) — consumes `/combined_spectra` for ambient correction
- [Perception overview](../README.md) — the sensor set and spectral coverage
- [workstation-setup.md](../../../00-onboarding/workstation-setup.md) — `libft4222` and
  the udev rule
- [running-the-system.md](../../../02-operations/running-the-system.md) — launching it
- [ros-graph.md](../../../05-reference/ros-graph.md) — system-wide topic view
