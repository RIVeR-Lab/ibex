---
camera: imec | ximea
status: active | superseded | baseline | experimental
captured: YYYY-MM-DD
captured-by:
integration-time-ms:
---

# Context: <folder name>

<!--
  Place this as README.md inside the context directory itself, so it travels
  with the context if the folder is copied or renamed.

  The XML files already record acquisition time, sensor temperature, bit depth,
  ROI, and integration time. Do not repeat those as the authority — summarize
  them here for readability and record what the XML CANNOT: where, who, under
  what light, against what target, and why.
-->

One sentence: what this context is and when it should be used.

> **Active?** State plainly whether this is the folder the driver loads. The
> driver loads `config/<model>/context` by hardcoded path, so only the directory
> literally named `context` is ever used. Everything else is inert until renamed.

## Validity

**Integration time: `__` ms.** The dark reference is tied to it — the file is named
`dark_reference_<time>.raw.xml` and the SDK checks it with
`ContextIntegrationTimeInDark()`. **Changing the camera's integration time invalidates
this context.**

| Invalidated by | |
| --- | --- |
| Integration time change | Dark reference no longer matches |
| Aperture change | Fabry–Pérot band response shifts with incidence angle |
| Lens removed, reseated, or refocused | Changes intrinsics and vignetting |
| Cover glass changed or cleaned differently | Changes transmission |
| Large temperature excursion from capture conditions | Dark current drifts |

> State explicitly what has and has not changed since capture.

## Capture conditions

Everything here is what the XML does not record.

| | |
| --- | --- |
| Date and time | |
| Location | Room, bay, or field site — be specific |
| Captured by | |
| Ambient room temperature | |
| Sensor temperature at capture | From the XML `temperature_c` field |
| Reason for capture | Routine, after a hardware change, troubleshooting, experiment |

### Illumination

| | |
| --- | --- |
| Source | Make, model, wattage |
| Warm-up before capture | Halogen output shifts for several minutes |
| Distance and geometry | Source-to-target distance, angle |
| Diffusion | Diffuser type, or none |
| Other light present | Room lights on or off, windows covered |

### White reference target

| | |
| --- | --- |
| Target | Spectralon puck, reflective board, PTFE panel |
| Nominal reflectance | e.g. 99% |
| Certificate or grade | If calibrated |
| Condition | Clean, marked, aged |
| Distance and fill | Did it fill the frame? |

### Dark reference

| | |
| --- | --- |
| Method | Lens cap, shutter, dark room |
| Residual light | Confirmed none? |
| Captured immediately before or after white? | Time gap matters for thermal drift |

## Optical configuration as set

**Record the aperture actually set**, not what the XML says. Two of the three IMEC
contexts in this repository record `f_number` as `0`, which is a placeholder rather than a
measurement.

| | |
| --- | --- |
| Lens | Manufacturer, model |
| Focal length | |
| **Aperture, as physically set** | |
| Focus distance | |
| Exit pupil distance | From optical_setup.xml |
| Sensor rejection filter | Refractive index from optical_setup.xml |

## Acquisition

| | |
| --- | --- |
| Integration time | ms |
| Frame rate | Hz |
| ROI | width × height at offset (x, y) |
| Frames averaged | **State the number.** `light_reference.py` captures a single frame; its averaging helper is defined and unused |
| Flip settings | IMEC uses `flip_horizontal: True` |

## Provenance

**Two SDK versions apply, and they are expected to differ.** Record both, and record why.

| | |
| --- | --- |
| Capture machine and OS | The vendor GUI is Windows-only; `light_reference.py` runs on Volta |
| Capture route | Vendor Windows GUI, or `hsi_sensor_calibration/light_reference.py` |
| **HSI Mosaic version that wrote this context** | From `context_description.xml` `data_source` |
| **HSI Mosaic version in the ROS stack** | Currently pinned at 1.12.0.0 |
| Why they differ | See below — state the reason rather than leaving it to be rediscovered |
| Capture path | Where it was written before being copied into the repo |
| System ID | From `context_description.xml` |

### A version difference is normal here, not a defect

The manufacturer recommends capturing with the **current Windows SDK**, which is newer than
the version the ROS stack can run. **The newer SDK breaks the stack**, which is why the
stack is pinned — but **contexts produced by the newer SDK remain compatible with the
pinned runtime.**

So a context stamped with a newer version than the runtime is the *expected* result of
following the vendor's recommended workflow. **Do not treat it as something to fix, and do
not regenerate a good context merely to make the numbers match.**

What to record instead:

- Which SDK wrote it, and on what machine
- That compatibility with the pinned runtime was confirmed, and how
- Whether the capture route was the vendor GUI or the in-repo script

> A context written *by the pinned Linux SDK* is also valid and simpler to reproduce. The
> trade is vendor-recommended tooling against a self-contained in-repo workflow. State
> which was chosen and why, since the choice is not obvious from the files.

> TODO(verify) for whoever maintains this: if the stack's SDK pin ever moves, re-confirm
> that existing contexts still load. Compatibility holding in one direction today does not
> guarantee it across a future pin change.

## Validation

How it was confirmed good, if it was.

- `[ ]` Dark frame min/max/mean recorded and sane
- `[ ]` White frame min/max/mean recorded, below the saturation value
- `[ ]` `ContextGetStatus()` output recorded
- `[ ]` `ContextIntegrationTimeInDark()` confirms the expected integration time
- `[ ]` A test cube inspected after applying this context

> Record the actual numbers, not just a tick. Saturation thresholds differ per camera —
> IMEC saturates at 7100 of 8191, the Ximea at 1023 of 1023.

## Why this context exists

What prompted it, what differs from the previous one, and when to prefer this over the
alternatives in this camera's config directory.

## Known issues

Anything suspected or observed.
