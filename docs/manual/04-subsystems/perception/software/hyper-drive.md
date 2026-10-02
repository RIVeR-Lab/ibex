---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# hyper_drive

The hyperspectral camera pipeline. Serves [Perception](../README.md).

Drives the IMEC SWIR and Ximea VNIR cameras through IMEC's HSI Mosaic SDK, produces
synchronised spectral cubes, and applies ambient-light correction using the point
spectrometers.

> **It does not drive the Alvium.** That camera is handled by Allied Vision's own
> `vimbax_camera` package, which `hyper_drive`'s launch files start alongside it — see
> [The Alvium is a separate driver](#the-alvium-is-a-separate-driver).

## Source

| | |
| --- | --- |
| Repository | <https://github.com/RIVeR-Lab/hyper_drive> |
| Branch | `dev/ros2` |
| In this repo | `packages/hyper_drive` — committed directly, not a submodule |
| Maintainer | Aidan Reichenberg |
| Licence | Apache-2.0 |

## Fork status

Not a fork. First-party lab code, committed into the monorepo.

The repository also exists standalone on GitHub as the Hyper-Drive research project. The
copy here is the one that runs on IBEX.

> TODO(verify): whether the standalone repository and this copy have diverged, and which is
> authoritative for future work.

## Description

Four things, in order of the data flow:

1. **Acquire** raw mosaic frames from both hyperspectral cameras over the IMEC SDK.
2. **Demosaic** them through HSI Mosaic pipelines, using per-camera context files that
   carry the dark and non-uniformity references.
3. **Publish** both cubes together as one message, with the Alvium's RGB frame attached.
4. **Correct** for ambient illumination by dividing each band by the point spectrometers'
   measurement of the light available.

## Capabilities

### Nodes

Installed executables, from `setup.py`:

| Executable | Source | Role |
| --- | --- | --- |
| `synchronous_cubes` | `synchronous_cubes.py` | **The main node.** Acquires both cameras in parallel, publishes paired cubes |
| `ambient_light_measurement` | `ambient_light_measurement.py` | Divides cubes by the spectrometer-derived illumination reference |
| `synchronous_cube_visualizer` | — | False-colour and per-band images from the raw cubes |
| `corrected_cube_visualizer` | — | The same, from the corrected cubes. Runs side by side for comparison |
| `hyper_drive_pub` | `cube_data.py` | Single-camera acquisition. Predecessor to `synchronous_cubes` |
| `cube_visualizer` | — | Single-camera visualizer |
| `combined_cube_data` | — | Warps both cubes into the Alvium frame and merges them. **Currently non-functional** — see [Known issues](#combined_cube_data-cannot-run) |
| `hsi_hist` | — | Histogram and single-band GUI feed |

Four source files are **not** registered as executables and cannot be launched:
`synchronous_cubes_single_thread.py`, `calibration.py`,
`ambient_light_measurement_cref.py`, and `ambient_light_measurement_old.py`.

> `synchronous_cubes_single_thread.py` is the pre-threading version of the main node, kept
> for comparison. `ambient_light_measurement_cref.py` is the version that still applied
> camera white and dark references — see
> [Why camera C_ref was removed](#why-camera-c_ref-was-removed).

### Launch files

| Launch file | Brings up |
| --- | --- |
| `ambient_light_launch.py` | **The full pipeline.** Spectrometers, then Alvium, then cubes, then correction, then visualizer |
| `synchronous_cameras_launch.py` | Alvium + both hyperspectral cameras + raw visualizer. No correction |
| `hyper_drive_launch.py` | IMEC only, single-camera path |
| `master_launch.py` | IMEC and Ximea in separate namespaces, plus GUI and combiner |
| `ambient_light_launch_old.py` | Superseded. **Contains a bug** — see [Known issues](#ambient_light_launch_oldpy-starts-two-cube-generators) |

## Purpose

It is the only path from the two hyperspectral cameras into ROS 2. Both cameras are driven
through IMEC's SDK rather than a vendor ROS driver, so without this package there is no
hyperspectral data at all.

## Alternative software

None. The IMEC SDK is the only way to operate these cameras, and nothing else wraps it for
ROS 2.

## Launch / invocation

**Full pipeline, including ambient-light correction:**

```bash
ros2 launch hyper_drive ambient_light_launch.py
```

**Cameras only, no correction:**

```bash
ros2 launch hyper_drive synchronous_cameras_launch.py
```

**Preconditions:**

- Compute and Sensing box powered, so the SWIR camera and both spectrometers are up
- Volta up, so the Ximea and Alvium have USB power
- The four vendor libraries installed — see
  [workstation-setup.md](../../../00-onboarding/workstation-setup.md)
- USB permissions for the cameras, and the udev rule for the spectrometers

### Start order matters, and the launch file explains why

`ambient_light_launch.py` staggers startup deliberately:

| Time | Starts |
| --- | --- |
| 0 s | Ibsen VNIR spectrometer, spectra combiner |
| +5 s | Ibsen NIR spectrometer |
| +8 s | Alvium, via `vimbax_camera` |
| +13 s | `synchronous_cubes` |
| +18 s | `ambient_light_measurement` |
| +20 s | `corrected_cube_visualizer` |

**The spectrometers lead because the correction depends on them.**
`ambient_light_measurement`'s cube callback divides by terms that only its spectra
callback populates. If cubes arrive first, those terms are still scalar zero and the
correction collapses — crashing on `max()`/`min()` of a scalar. So `/combined_spectra` has
to be flowing before cubes start.

The NIR spectrometer is delayed behind VNIR for an unrelated reason: the FT4222
enumeration race — see
[spectrometer-drivers.md](spectrometer-drivers.md).

### The Alvium is a separate driver

The launch files start Allied Vision's `vimbax_camera` node, not a `hyper_drive` node:

| | |
| --- | --- |
| Package | `vimbax_camera` — installed from a `.deb`, not in this repo |
| Camera ID | `DEV_1AB22C025217` |
| Settings file | `~/allied_vision_config.xml` |
| Topic | `/alvium/image_raw`, remapped to `/camera/image_raw` |

That settings file is the "generate a configuration file for the Alvium" step recorded on
[alvium-rgb-camera.md](../hardware/alvium-rgb-camera.md). **It lives in the home
directory, not in the repository**, so it is not version-controlled and would be lost with
the machine.

> TODO(verify): move `allied_vision_config.xml` into `hyper_drive/config/` and point the
> launch files at the installed share path. It is the only piece of camera configuration on
> the vehicle that is not in git. Same applies to the FastDDS profile at
> `~/fastdds_ibex_config.xml`.

## Topics

Captured with `ambient_light_launch.py` running. Node names are the launch-assigned ones.

| Topic | Type | Publisher | Subscriber |
| --- | --- | --- | --- |
| `/synchronous_cubes` | `MultipleDataCubes` | `cameraProcessors` | `ambient_light` |
| `/corrected_cubes` | `MultipleDataCubes` | `ambient_light` | `corrected_cube_visualizer` |
| `/combined_spectra` | `Spectra` | `spectra_combiner` | `ambient_light`, `combined_plot` |
| `/camera/image_raw` | `sensor_msgs/Image` | `alvium_camera` in `/alvium` | `cameraProcessors` |
| `/alvium/camera_info` | `sensor_msgs/CameraInfo` | `alvium_camera` | **none** |

**Everything is Reliable and Volatile**, with the history depth not reported. That matters
here more than anywhere else on the vehicle — see below.

`corrected_cubes` is declared as a relative name and the node runs with no namespace, so it
resolves to `/corrected_cubes` and the corrected visualizer connects. The code comments
warn about this; in the current launch configuration it works.

### Reliable QoS on very large messages

A single `MultipleDataCubes` carries both cubes plus the Alvium frame:

| Component | Size |
| --- | --- |
| Ximea cube, 407 × 215 × 24 float32 | 8.40 MB |
| IMEC cube, 211 × 168 × 9 float32 | 1.28 MB |
| Alvium frame, 2464 × 2056 | 5.07 MB at 8-bit, 15.20 MB at rgb8 |
| **Total per message** | **14.7 MB**, or 24.9 MB if the Alvium publishes rgb8 |

At the configured 15 Hz that is roughly **220 MB/s**, or 370 MB/s with an rgb8 frame — and
**Reliable** means a slow subscriber causes the publisher to retain and retransmit rather
than drop. At the default depth of 10 that is 147 MB of queue per endpoint.

> TODO(verify): measure the actual rate with `ros2 topic hz /synchronous_cubes` and
> compare against 15 Hz. If it is well below, the transport is the limit rather than the
> cameras, and best-effort QoS with a depth of 1 would be the appropriate change — nothing
> downstream benefits from a retransmitted stale cube.

> TODO(verify): record the Alvium's pixel format, which decides whether each message is
> 14.7 or 24.9 MB. `ros2 topic echo /camera/image_raw --once --no-arr` prints the encoding.

### The Alvium publishes intrinsics, and they are orphaned

`/alvium/camera_info` exists with **zero subscribers**, and it sits in the `alvium`
namespace while its image was remapped out to `/camera/image_raw`.

That breaks the ROS convention of `camera_info` living beside its image topic, so anything
using `image_transport` or pairing the two by namespace will not find it.

> TODO(verify): echo it. A published `CameraInfo` does not mean a calibrated camera — an
> uncalibrated driver publishes zeroed `K` and `D`. If the values are real, this is the
> Alvium's intrinsic calibration and
> [alvium-rgb-camera.md](../hardware/alvium-rgb-camera.md) should say so; if zeroed, the
> topic is noise. Either way the remap should carry it along with the image.

### Visualizer output

Per camera: `band_N` for every band, plus `band_grid` and `false_color`, under
`/visualizer_corrected/` — 24 band topics for the Ximea and 9 for the IMEC.

`synchronous_cube_visualizer` mirrors the same tree under `/visualizer/`, but
**`ambient_light_launch.py` starts only the corrected visualizer**, so the raw tree is
absent in normal operation. The two were written for side-by-side comparison and do not
run together by default.

**Most of those publishers carry no traffic.** Only band 6 is ever published — the
per-band loop is commented out — and `publish_band_grid()` is never called at all. So of
33 band topics plus 2 grids, 2 carry data and 33 are advertised and silent.

All visualizer topics had zero subscribers in the capture, which is expected: they exist
for `image_view` or Foxglove to attach to on demand. Worth knowing the visualizer is doing
the normalization and encoding work regardless of whether anyone is looking.

### Visualizer output

`/visualizer/ximea/false_color`, `/visualizer/imec/false_color`,
`/visualizer/{ximea,imec}/band_N`, `/visualizer/{ximea,imec}/band_grid`,
`/visualizer/vimba`.

The corrected visualizer mirrors all of these under `/visualizer_corrected/`, so raw and
corrected can be compared side by side.

False colour maps the first, middle, and last band to R, G, B.

> TODO(verify): the command sheet records
> `ros2 run image_view image_view --ros-args -r image:=/visualizer/` with the topic
> truncated. It is almost certainly `/visualizer/vimba`.

## Services

| Service | Type | Effect |
| --- | --- | --- |
| `adjust_param` | `hyper_drive_interfaces/srv/AdjustParam` | Sets integration time and frame rate on one camera at runtime |

Request fields are `camera_model`, `integration_time`, and `frame_rate`. The call is
rejected unless the integration time is inside the camera's range **and** shorter than one
frame period:

| Camera | Integration range |
| --- | --- |
| Ximea | 0.021 – 999.995 ms |
| IMEC | 0.010 – 90 ms |

Changing a parameter pauses the camera, drops the frame rate to 1 Hz, sets the exposure,
then restores the frame rate — a three-step sequence the SDK requires.

## Parameters

`synchronous_cubes`:

| Parameter | Default | Set in launch | Effect |
| --- | --- | --- | --- |
| `x_frame_rate` | 30 | 15 | Ximea frame rate, Hz |
| `x_integration_time` | 15 | 10 | Ximea exposure, ms |
| `i_frame_rate` | 10 | 15 | IMEC frame rate, Hz |
| `i_integration_time` | 70 | 60 | IMEC exposure, ms |
| `sleep` | 0.001 | 0.001 | Timer period, s |
| `time_wait` | 0 | 0 | Minutes between publishes. **Multiplied by 60 internally** |

> `time_wait` of 0 means publish every timer tick. Any non-zero value is interpreted as
> minutes, so `1` gives one cube per minute — a large step. Worth knowing before changing
> it.

## Non-ROS interfaces

**The IMEC HSI Mosaic SDK**, through its Python API at
`/opt/imec/hsi-mosaic/python_apis`. The node adds that to `sys.path` and
`/opt/imec/hsi-mosaic/bin` to `PATH` at import time.

Launch files set `LD_LIBRARY_PATH` across five vendor library directories plus
`GENICAM_ROOT_V3_1` and `GENICAM_ROOT_V3_4`. That environment setup is why the cameras
must be started through a launch file rather than `ros2 run`.

Both cameras are USB devices reached through the SDK — the IMEC via a Pleora frame grabber
reported as `iPORT-CL-U3-PT03-CL0UP04-128xU [28B702142385]`.

## Camera configuration, as actually set

These resolve the band-count and spectral-range disputes on both hardware pages.

### Band centres — authoritative

Copied verbatim from `synchronous_cubes`' own `bands_nm` log output into
`write_camera_lamba.py`:

| Camera | Bands | Range | Spacing |
| --- | --- | --- | --- |
| Ximea VNIR | **24** | **662.7 – 932.9 nm** | 4.7 – 16.2 nm |
| IMEC SWIR | **9** | **1119.5 – 1650.1 nm** | 17.9 – 188.7 nm |

**The IMEC is therefore the SWIR 9**, a 3 × 3 mosaic — not the SWIR 16. That settles the
variant question on [imec-swir-hsi.md](../hardware/imec-swir-hsi.md).

**The IMEC's bands are very unevenly spaced.** Five sit between 1119 and 1207 nm, then
four spread to 1650 with gaps of up to 189 nm. Anyone treating the SWIR cube as a smooth
spectrum will be misled — it is five closely spaced samples plus four isolated ones.

**Imaging coverage has a 186.5 nm gap**, from 932.9 to 1119.5 nm. Only the point
spectrometers cover it, and only at a single point.

### Regions of interest and cube dimensions

| | Sensor | ROI | Cube |
| --- | --- | --- | --- |
| Ximea | 2048 × 1088 | 2045 × 1085 at (0,0) | **407 × 215 × 24** |
| IMEC | 640 × 512 | 639 × 510 at (1,1) | **211 × 168 × 9** |

The ROI is cropped a few pixels to align with the mosaic pattern, and demosaicing divides
spatial resolution by the mosaic size. The per-band resolution is **407 × 215** for the
Ximea and **211 × 168** for the IMEC — not the sensor dimensions.

The IMEC frame is flipped horizontally in the driver to match its housing.

### Bit depth and saturation

From the context files:

| | Bit depth | Max value | Saturation value |
| --- | --- | --- | --- |
| Ximea | 10 | 1023 | 1023 |
| IMEC | 13 | 8191 | 7100 |

**The IMEC's saturation threshold is below its maximum** — 7100 of 8191, about 87%.
Values above 7100 are unreliable even though the sensor can report up to 8191. The Ximea
saturates at full scale.

That answers the saturation question on both hardware pages: check cube maxima against
7100 and 1023 respectively, not against the bit depth.

### Lenses

From the context files' `optical_setup.xml`, which resolves the lens gap on
[ximea-vnir-hsi.md](../hardware/ximea-vnir-hsi.md):

| | Manufacturer | Focal length | f-number | Exit pupil |
| --- | --- | --- | --- | --- |
| Ximea VNIR | **Edmund Optics** | **25 mm** | **f/1.4** | **31.7 mm** |
| IMEC SWIR | Navitar | 25 mm | f/2.8 | 65 mm |

Both carry a sensor rejection filter with refractive index 1.7.

> TODO(verify): the IMEC's `context_base` and `context_exp_cal` optical setups record
> `f_number` as 0, while the active `context` records 2.8. Confirm 2.8 is correct and the
> zeros are unset placeholders.

## Calibration

### The IMEC is calibrated; the Ximea is not

This is visible in the repository itself:

| | Dark reference | Non-uniformity | Optical setup |
| --- | --- | --- | --- |
| `config/imec/context/` | ✅ `dark_reference_60.000000.raw.xml` | ✅ dark + white | ✅ |
| `config/ximea/context/` | ❌ absent | ❌ absent | ✅ |

**The Ximea context directory contains no dark or white reference.** Its cubes are
therefore not flat-fielded, which confirms what
[ximea-vnir-hsi.md](../hardware/ximea-vnir-hsi.md) records — and makes it concrete rather
than anecdotal.

The IMEC's references were captured on **2026-07-08 at 60 ms integration**, at a sensor
temperature of 25.0 °C. A second set in `context_exp_cal/` dates from 2026-06-25.

> TODO(verify): capture dark and non-uniformity references for the Ximea.
> `hsi_sensor_calibration/light_reference.py` does exactly this for the IMEC and is the
> obvious starting point — it would need the device enumeration changed from
> `EM_IMEC` to `EM_XIMEA` and the ROI changed to 2045 × 1085.

> TODO(verify): the dark reference is tied to a specific integration time — the filename
> is `dark_reference_60.000000.raw.xml` and the script checks
> `ContextIntegrationTimeInDark(context, 60.0)`. The launch file runs the IMEC at 60 ms,
> which matches. **If anyone changes `i_integration_time`, the dark reference no longer
> applies.** That coupling should be recorded wherever the parameter is documented.

### The calibration script

`hsi_sensor_calibration/light_reference.py` captures references for the IMEC and writes
them into the context:

1. Re-executes itself once with `LD_LIBRARY_PATH` set, since that must be in place before
   the process starts.
2. Opens the IMEC, sets 60 ms at 15 Hz, and reports what the hardware actually applied.
3. Prompts you to cover the lens, captures one dark frame, and sets it as the dark field
   reference.
4. Prompts you to point at a uniform white surface, captures one white frame, and sets the
   non-uniformity correction.
5. Saves the context.

> Note it reads `CONTEXT_PATH = '/home/river/imec_light_reference/context'`, **not** the
> context inside the package. The result has to be copied into
> `config/imec/context/` and rebuilt.

> TODO(verify): the script captures a **single** frame for each reference, with the
> averaging helper `capture_averaged_frame()` defined but unused. Averaging 30 frames was
> evidently the intent and would reduce noise in both references. Worth deciding whether
> single-frame is deliberate.

### HSI Mosaic version mismatch in the context files

| Context | Created by |
| --- | --- |
| `config/imec/context/` | HSI Mosaic **2.11.10.0** |
| `config/ximea/context/` | HSI Mosaic **1.12.0.0** |

The installed version is 1.12.0.0, pinned deliberately — see
[imec-swir-hsi.md](../hardware/imec-swir-hsi.md). **So the IMEC context was generated by a
newer SDK than the one reading it.**

> TODO(verify): whether that matters. It evidently works, but a context written by 2.11 and
> consumed by 1.12 is the kind of mismatch that produces subtly wrong output rather than an
> error. Regenerating the IMEC context under 1.12.0.0 would remove the question.

## The ambient light correction

`ambient_light_measurement` is where the spectrometers and the cameras meet.

For each camera band, it finds the nearest spectrometer wavelength and computes an
illumination reference:

```
S_ref = (S_raw - S_dark) / (S_white - S_dark) * S_norm      S_norm = 100000
corrected_cube = raw_cube / S_ref                           per band, guarded against S_ref == 0
```

`S_raw` comes live from `/combined_spectra`; `S_dark` and `S_white` are stored references.

### Why camera C_ref was removed

An earlier version — preserved as `ambient_light_measurement_cref.py` — also applied
camera white and dark references:

```
C_ref = (C_raw - C_dark) / (C_white * CI_raw/CI_white - C_dark * CI_raw/CI_dark) * C_norm
```

That was removed because **the cubes arriving on `/synchronous_cubes` are already
flat-fielded upstream** by the vendor pipeline, using the dark and non-uniformity
references in the context files. Applying C_ref again would double-correct.

Both formulas reference IMEC's Technical Note on the Ambient Light Sensor.

> That reasoning depends on the context files actually containing references — which
> **they do for the IMEC and do not for the Ximea.** So the Ximea's cubes are not
> flat-fielded upstream, and removing C_ref left nothing in its place for that camera.
> This is the concrete consequence of the missing Ximea calibration.

### Stored reference files

In `bag_files/numpy_files/`, installed into the package share directory:

| File | Contents |
| --- | --- |
| `spec_lamba.npy` | Spectrometer wavelength grid — 305 bins, 451–1702 nm |
| `ximea_lamba.npy` | 24 Ximea band centres |
| `imec_lamba.npy` | 9 IMEC band centres |
| `point_spectra_white_ref.npy` | Spectrometer white reference |
| `point_spectra_dark_ref.npy` | Spectrometer dark reference — **present but not loaded** |

The 305-bin spectrometer grid is 184 VNIR plus 121 NIR bins, and its 451–1702 nm range
matches the calibration extremes recorded on both spectrometer hardware pages.

### Regenerating the references

Three scripts under `numpy_ambient_light_calibration_scripts/`:

| Script | Produces |
| --- | --- |
| `extract_point_spectra_references.py` | White and dark spectrometer references, averaged from bags of `/combined_spectra` |
| `extract_references.py` | Camera white and dark cubes, averaged from bags of `/synchronous_cubes`. For the removed C_ref path |
| `extract_wavelength_axes.py` | All three wavelength axes, from the same bags |
| `write_camera_lamba.py` | The two camera axes, from hardcoded values. No bag needed |

`extract_point_spectra_references.py` validates that the extracted reference aligns
element-for-element with `spec_lamba.npy` and warns loudly if it does not — because the
correction indexes the reference by position, so a length or ordering mismatch silently
misaligns every dark and white subtraction.

All four require a rebuild afterwards, so the `.npy` files reinstall into `share/`.

## Dependencies

**Ibex packages**

- `hyper_drive_interfaces` — `DataCube`, `MultipleDataCubes`, `srv/AdjustParam`. Separate
  interface package, correctly, so consumers need not build the driver
- `spectrometer_interfaces` — `Spectra`, consumed by the ambient correction

> Note the contrast with `shared_link_bridge`, which defines its messages inside the
> driver package and so forces `ibex_state` to build the whole thing. `hyper_drive` does
> this the right way round.

Two small things about the interfaces package itself:

> TODO(verify): its `package.xml` still reads `description: TODO: Package description`,
> and its maintainer is a personal Gmail address under the name "river" — unlike
> `hyper_drive`, which names Aidan Reichenberg at a Northeastern address. Worth correcting
> both so ownership is traceable. See
> [ownership.md](../../../00-onboarding/ownership.md).

> TODO(verify): `CMakeLists.txt` passes `DEPENDENCIES` twice —
> `DEPENDENCIES std_msgs DEPENDENCIES sensor_msgs` — rather than listing both after one
> keyword. `cmake_parse_arguments` behaviour with a repeated multi-value keyword is worth
> confirming; if the second occurrence replaces the first, `std_msgs` is only satisfied
> transitively because `sensor_msgs` depends on it, and the build works by accident. The
> safe form is `DEPENDENCIES std_msgs sensor_msgs` on one line.

**External ROS**

- `vimbax_camera` — the Alvium driver, started by these launch files
- `rclpy`, `ros2_numpy`, `cv_bridge`, `sensor_msgs`, `std_msgs`

**Python**

- `numpy`, `cv2`, `bs4`, `numba`, `matplotlib`

> TODO(verify): three imports are not declared in `package.xml` — `PySimpleGUI` in
> `calibration.py`, and `seaborn` and `PIL` in `hsi_hist.py`. `calibration.py` is not an
> installed executable so it will not break a build, but `hsi_hist` is.

**Vendor libraries**

IMEC HSI Mosaic 1.12.0.0, Pleora eBUS 6.5.3, Photon Focus SDK 2025.1.0, Ximea SDK
LTS 4.32.0.0 — see
[workstation-setup.md](../../../00-onboarding/workstation-setup.md).

**Hardware that must be powered**

The SWIR camera and both spectrometers from the Compute and Sensing box; the Ximea and
Alvium from Volta's USB.

### Message definitions

From `hyper_drive_interfaces`, which contains nothing but these three files.

**`DataCube.msg`**

```
std_msgs/Header header
float32[]        data
int16            width
int16            height
int16            lam
float32[]        central_wavelengths
float32[]        qe
float32[]        fwhm_nm
```

**`MultipleDataCubes.msg`**

```
DataCube[]        cubes
sensor_msgs/Image im
```

**`srv/AdjustParam.srv`**

```
float32 integration_time
int8    frame_rate
string  camera_model
---
bool    success
```

**Per-band metadata travels with every cube.** `central_wavelengths`, `fwhm_nm`, and `qe`
are per-band arrays, so band centres, spectral resolution, and quantum efficiency can all
be read straight off a live cube rather than looked up:

```bash
ros2 topic echo /synchronous_cubes --once --no-arr
```

That is the quickest way to fill the FWHM column in
[Perception](../README.md) for both cameras.

The metadata is loaded by `parse_parameters()` from `config/{model}.xml`.

> TODO(verify): `config/imec.xml` and `config/ximea.xml` do not appear in the repository
> tree, only the `config/imec/` and `config/ximea/` directories. `parse_parameters()`
> would fail without them. Confirm they exist and are committed — if they are missing, the
> band metadata in every published cube is coming from somewhere undocumented.

#### Cubes carry no frame_id

`publish_cubes()` sets `header.stamp` and never sets `header.frame_id`, so every published
cube has an empty frame reference.

**Consequence:** the hyperspectral data is not associated with any coordinate frame, so
nothing can transform it into `base_link` or relate it to the point cloud. Combined with
the absence of any camera frame in
[tf-frames.md](../../../05-reference/tf-frames.md), this is the concrete blocker on fusing
spectral data with lidar geometry.

> TODO(verify): set `header.frame_id` per camera, and add the corresponding frames to the
> transform tree. The two cameras sit at different points on the array and need separate
> frames.

#### int16 and int8 are tight in one place

`width`, `height`, and `lam` as `int16` are comfortable — the largest current value is 407.

`frame_rate` as **`int8` caps requests at 127 Hz**, and prevents fractional rates while
`integration_time` is a float. The Ximea's integration range extends down to 0.021 ms,
implying rates well above 127 are physically possible, so this is a latent limit rather
than a current one.

> TODO(verify): widen `frame_rate` to `float32` if high-rate capture is ever wanted. It is
> a breaking interface change, so cheaper now than later.

## Known issues & fixes

### Serialization of cube data is fragile

`DataCube.data` is `float32[]`, and the message setter **rejects numpy arrays** — numpy
float32 scalars are not Python floats. It has to be assigned as an `array.array`:

```python
ros_cube.data = array.array('f', np.ascontiguousarray(cube, dtype=np.float32).tobytes())
```

Consumers decode with `np.frombuffer(msg.data, dtype=np.float32)`. **Publisher and
consumer must agree**, and if a publisher assigns a list or ndarray instead, the decode
produces garbage rather than an error.

This is documented in comments in both the correction node and the corrected visualizer,
and it is the single easiest way to break this pipeline silently.

### `combined_cube_data` cannot run

Two independent reasons:

**It loads a file that does not exist.** `config/homographies/mask.npy` is loaded at
startup; the directory contains only `i2a.npy`, `x2a.npy`, and `.gitkeep`.

**Nothing publishes its inputs.** It subscribes to `/ximea/undistort_data` and
`/imec/undistort_data`, and the undistortion nodes that would produce them are commented
out in `master_launch.py`.

> TODO(verify): decide whether to restore this path or remove the node. Warping both cubes
> into the Alvium frame via the stored homographies is exactly what cross-camera
> registration needs, so it is worth reviving rather than deleting — but it does not work
> today and nothing says so.

### `ambient_light_launch_old.py` starts two cube generators

The `synchronous_cubes` `TimerAction` block is duplicated verbatim at `period=5.0`, so the
launch starts two instances of the same node against the same cameras.

**Fix:** do not use this launch file. `ambient_light_launch.py` supersedes it.

> TODO(verify): delete it, or rename it to make clear it must not be run.

### Undistortion is disabled

`undistort()` exists in both acquisition nodes with hardcoded camera matrices and
distortion coefficients for the IMEC, Ximea, and Alvium — and the calls are **commented
out** in `synchronous_cubes.publish_cubes()`.

There are also `.mat` intrinsics in `config/distortion/` that nothing loads.

> TODO(verify): whether undistortion is disabled for performance, because it was wrong, or
> by accident. Three sets of intrinsics exist in two formats and none are applied, which
> means cubes are published with lens distortion intact. That matters for any registration
> against the lidar.

### The dark spectrometer reference is hardcoded

`ambient_light_measurement` defines `S_dark_spectra` as a literal 305-element array in the
source, with the `np.load` of `point_spectra_dark_ref.npy` commented out — **while that
file exists in the repository and a script generates it.**

> TODO(verify): switch to loading the file. A reference baked into source cannot be
> regenerated without editing code, and the generator script already validates alignment
> against `spec_lamba.npy`, which the hardcoded array cannot.

### `adjust_param` has three unguarded failure paths

All three are in `adjust_param_callback`, before the `try` block that protects the actual
camera reconfiguration:

**`frame_rate` of 0 divides by zero.** The first line computes
`frame_time = 1/request.frame_rate * 1000`. A request with `frame_rate: 0` raises
`ZeroDivisionError` outside any handler.

**An unrecognised `camera_model` raises `UnboundLocalError`.** The callback assigns `cam`
inside two `if` branches for `imec` and `ximea`, with no `else`. Any other string — or a
typo — leaves `cam` unassigned and the next line fails.

**The response carries no reason.** `AdjustParam` returns only `bool success`, so a
rejected request gives the caller no explanation. The node logs why; the caller cannot see
it.

> TODO(verify): guard the division, add an `else` that returns `success: false`, and
> consider adding a `string message` field to the service response. The first two are
> small fixes that turn a node crash into a failed service call.

### `cube_data.py` has a hardcoded IMEC cube shape

The single-camera node allocates `np.empty((168, 211, 9))` — the IMEC's shape — in a node
that takes `camera_model` as a parameter. Running it with `camera_model: ximea` would fail.

Two further bugs in the same file's `adjust_param_callback`: it reads
`request.integration_range[1]`, which is not a request field, and calls
`rclpy.spin_once(Publisher, ...)` passing the class rather than the instance.

> `synchronous_cubes` is the maintained path and does not share these. Worth noting that
> `hyper_drive_pub` is effectively IMEC-only despite its parameter.

### Startup cost

Both cameras are opened, initialized, and have their HSI Mosaic pipelines built in
`__init__`. The launch file allows 5 seconds before the cube node starts and another 5
before correction, which is why bringup is slow rather than broken.

## Understanding the software

**Acquisition is threaded.** `synchronous_cubes` fans both cameras out to a two-worker
pool inside one lock, then joins before releasing it, so a concurrent `adjust_param` call
cannot reconfigure a camera mid-acquisition. The workers deliberately never take the lock
— `threading.Lock` is not reentrant and doing so would deadlock.

Whether that actually overlaps depends on whether the IMEC SDK releases the GIL while
waiting on hardware. The node logs both per-camera durations and the wall clock for the
parallel section specifically so you can tell:

```
Acquire XIMEA:0.xxx Acquire IMEC:0.xxx Parallel acquire:0.xxx (serial would be ~0.xxx)
```

If the parallel figure is close to the larger of the two, threading is helping. If it is
close to their sum, the GIL is held and the work is still serial.
`synchronous_cubes_single_thread.py` is the version to compare against.

**"Synchronous" means published together, not captured together.** Both cameras are
acquired in the same callback and share one header timestamp, but nothing hardware-triggers
them. The Alvium frame attached to each message is simply the most recent one received.

> TODO(verify): all three cameras support hardware triggering and none of it is used —
> both hyperspectral cameras ship with trigger cables and the Alvium has four GPIO pins.
> `HSI_CAMERA.Trigger()` calls appear commented out in both acquisition nodes. Establish
> what the actual temporal alignment between the three cameras is, and whether hardware
> triggering is worth wiring.

**Visualizer normalization is per-band min-max.** Both visualizers contrast-stretch each
band independently, so displayed images are not radiometrically comparable between bands or
between frames. The corrected visualizer adds NaN and infinity handling, which the raw one
lacks — corrected cubes can contain non-finite values from divisions.

## Related pages

- [imec-swir-hsi.md](../hardware/imec-swir-hsi.md) and
  [ximea-vnir-hsi.md](../hardware/ximea-vnir-hsi.md) — the two cameras
- [alvium-rgb-camera.md](../hardware/alvium-rgb-camera.md) — driven by `vimbax_camera`,
  started here
- [spectrometer-drivers.md](spectrometer-drivers.md) — the illumination reference
- [Perception overview](../README.md) — the sensor set and spectral coverage
- [workstation-setup.md](../../../00-onboarding/workstation-setup.md) — the four vendor
  libraries
- [running-the-system.md](../../../02-operations/running-the-system.md) — launching it
- [ros-graph.md](../../../05-reference/ros-graph.md) — system-wide topic view
