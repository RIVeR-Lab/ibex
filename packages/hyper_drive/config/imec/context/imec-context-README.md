---
camera: imec
status: active
captured: 2026-07-08
captured-by: TODO(verify)
integration-time-ms: 60
---

# Context: imec/context

Dark and non-uniformity references for the IMEC SWIR 9 camera, captured 2026-07-08 at
60 ms integration.

> **This is the active context.** The driver loads `config/imec/context` by hardcoded
> path, so this folder — and only this folder — is what runs. `context_base` and
> `context_exp_cal` are inert unless renamed.

## Validity

**Integration time: 60 ms.** `dark_reference_60.000000.raw.xml` is tied to it, and
`ambient_light_launch.py` sets `i_integration_time: 60`, so they currently match.

**Changing `i_integration_time` invalidates this context.** Nothing in the launch file
warns about that coupling.

| Invalidated by | Status |
| --- | --- |
| Integration time change | ✅ Still 60 ms |
| Aperture change | TODO(verify) — see [Optical configuration](#optical-configuration-as-set) |
| Lens removed or refocused | TODO(verify) |
| Cover glass change | TODO(verify) — reported unchanged since the Hyper-Drive move |
| Temperature excursion | Captured at 25.0 °C; vehicle operating range unrecorded |

## Capture conditions

| | |
| --- | --- |
| Date and time | Dark 2026-07-08 16:03:30 UTC, white 16:04:07 UTC — 37 s apart |
| Location | TODO(verify) |
| Captured by | TODO(verify) |
| Ambient room temperature | TODO(verify) |
| Sensor temperature | **24.999 °C** dark, **25.004 °C** white |
| Reason for capture | TODO(verify) — supersedes `context_exp_cal` from 2026-06-25 |

The 5 mK difference between dark and white captures indicates a thermally stable
environment, which is a good sign. The 37-second gap is short enough that drift is not a
concern.

### Illumination

> TODO(verify): **entirely unrecorded.** Needed: source make and model, warm-up time,
> distance, geometry, diffusion, and whether room lights were on. The procedure described
> elsewhere in the manual mentions a dark room and diffused halogen, but nothing confirms
> that is what was used here.

### White reference target

> TODO(verify): unrecorded. The vehicle carries a Spectralon puck on the roof for the
> spectrometers, but whether that or a separate reflective board was used for this capture
> is not recorded. Needed: target type, nominal reflectance, and whether it filled the
> frame.

### Dark reference

> TODO(verify): method unrecorded. `light_reference.py` prompts the operator to "cover the
> lens completely", so a lens cap is likely.

## Optical configuration as set

From `optical_setup/optical_setup.xml`:

| | |
| --- | --- |
| Lens | Navitar, SWIR |
| Focal length | 25 mm |
| **Aperture** | **f/2.8** |
| Exit pupil distance | 65 mm |
| Sensor rejection filter | Refractive index 1.7 |

> This context records `f_number` as **2.8**, while `context_base` and `context_exp_cal`
> both record **0** — a placeholder. If the aperture was genuinely f/2.8 for all three,
> the other two are mislabelled; if it changed between captures, that alone makes them
> non-interchangeable. **Resolve this before using any of the other contexts.**

## Acquisition

| | |
| --- | --- |
| Integration time | 60 ms |
| Frame rate | TODO(verify) — `light_reference.py` uses 15 Hz, but that script was not used here |
| ROI | 639 × 510 at offset (1, 1) |
| **Frames averaged** | TODO(verify) — captured via the Windows GUI, whose averaging setting is unrecorded |
| Flip | `flip_horizontal: True`, `flip_vertical: False` |
| Bit depth | 13-bit, max 8191, **saturation 7100** |

## Provenance

| | |
| --- | --- |
| Capture machine and OS | **Windows** — the vendor GUI is Windows-only |
| Capture route | **IMEC's Windows SDK GUI**, as the manufacturer recommends |
| HSI Mosaic version that wrote this context | **2.11.10.0** |
| HSI Mosaic version in the ROS stack | **1.12.0.0** — pinned |
| Why they differ | Deliberate — see below |
| Capture path | TODO(verify) — written on the Windows machine, then copied here |
| System ID | `iPORT-CL-U3-PT03-CL0UP04-128xU [28B702142385]` |

### The version difference is deliberate and correct

The manufacturer recommends capturing with the current Windows SDK, which is newer than
what the ROS stack can run. **Running 2.11.10.0 in the stack breaks it**, which is why the
stack is pinned to 1.12.0.0. **The context itself is compatible across that gap.**

So this context carrying a newer version stamp than the runtime is the expected result of
following the vendor's workflow — **not a defect, and not something to fix.** Do not
regenerate a working context to make the numbers match.

> This also means `light_reference.py` did **not** produce this context. That script runs
> on Volta against the pinned 1.12.0.0 and would stamp a context accordingly. It remains a
> valid alternative route — self-contained and in-repo — but it is not what was used here.

> Worth noting: `config/ximea/context/` is stamped **1.12.0.0** and contains **no
> references**. That is consistent with the Windows calibration workflow having been run
> for the IMEC and not for the Ximea, which would explain the Ximea calibration gap
> recorded in the manual.

## Validation

> TODO(verify): no validation record exists. `light_reference.py` prints frame min, max,
> and mean and reports `ContextGetStatus()`, but none of that output was captured.
>
> - `[ ]` Dark frame min/max/mean
> - `[ ]` White frame min/max/mean — must be below 7100
> - `[ ]` `ContextGetStatus()` output
> - `[ ]` `ContextIntegrationTimeInDark(context, 60.0)` returns true
> - `[ ]` Test cube inspected

## Why this context exists

Supersedes `context_exp_cal`, captured 2026-06-25, by 13 days. Both are 60 ms at
approximately 25 °C.

> TODO(verify): what prompted the recapture, and what differs. Without that, there is no
> basis for preferring one over the other beyond recency.

## Known issues

**No illumination or target record.** The two things that most determine whether a white
reference is good are the light source and the target, and neither is recorded. This
context cannot be reproduced.

**Single-frame references.** TODO(verify) — `light_reference.py` captures one frame each,
but this context came from the Windows GUI, whose averaging behaviour is unrecorded. Check
whether the GUI averaged, and how many frames.

**Capture conditions unrecoverable.** See above — the illumination and target are the two
things that most determine whether a white reference is good, and neither is recorded.
