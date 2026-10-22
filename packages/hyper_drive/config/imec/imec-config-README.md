# IMEC SWIR camera contexts

Three context directories live here. **Only one is ever loaded.**

```python
dn_context = os.path.join(package_share_dir, 'config', self.model, 'context')
```

The driver builds that path from the `camera_model` parameter and a hardcoded `'context'`.
There is no setting that selects between the three — **the folder named `context` is the
active one, and switching means renaming directories.**

## The three

| Directory | Captured | Integration | f-number | References | Status |
| --- | --- | --- | --- | --- | --- |
| **`context`** | 2026-07-08 | 60 ms | 2.8 | dark + non-uniformity | **ACTIVE** |
| `context_exp_cal` | 2026-06-25 | 60 ms | **0** | dark + non-uniformity | Superseded |
| `context_base` | — | — | **0** | **none** | Baseline / empty |

All three share the same ROI (639 × 510 at offset 1,1), the same system ID, and were
written by HSI Mosaic **2.11.10.0** — the current Windows SDK, which the manufacturer
recommends for calibration.

**That version is newer than the 1.12.0.0 the ROS stack is pinned to, and that is
correct.** Running 2.11.10.0 in the stack breaks it; contexts written by it are compatible
with the pinned runtime. A newer stamp here is the expected result of the vendor's
workflow, **not a defect** — see each context's `README.md`.

**`context_base` contains no references at all** — only a description and an optical
setup. Loading it means running with no dark subtraction and no flat-fielding. It is a
starting point for building a new context, not a usable one.

## Before switching

Renaming a directory to `context` puts it in play immediately, with no warning and no
error if it is wrong. Check three things first:

**Integration time.** Each context's dark reference is tied to one. Both populated
contexts here are 60 ms, and `ambient_light_launch.py` sets `i_integration_time: 60`. If
you change either, they must change together.

**Declared f-number.** `context` declares f/2.8; the other two declare 0. **This is an
input to band-centre computation, not just a record of the physical aperture** — the
Fabry–Pérot angle-of-incidence correction is computed from it.

Measured against the Hyper-Drive ROS 1 contexts, which also declare f/0, the difference is
**3.0 to 4.5 nm in reported band centres** and up to **1.1% in band values**. So the three
contexts here are genuinely not interchangeable, and swapping one for another shifts the
spectral axis.

**What you are actually trying to fix.** A context swap changes dark subtraction and
flat-fielding. If the symptom is geometric, spectral range, or timing, this is the wrong
lever.

## Switching procedure

```bash
cd ~/ibex_ws/src/ibex/packages/hyper_drive/config/imec
mv context context_<descriptive-name>      # never delete; rename
mv <the-one-you-want> context
cd ~/ibex_ws && colcon build --packages-select hyper_drive
source install/setup.bash
```

**The rebuild is required.** Contexts are installed into the package share directory, and
the driver reads them from there, not from `src/`.

Record the swap and the reason in the relevant context's `README.md`.

## Adding a new context

1. Capture. Two routes, and the choice should be recorded:
   - **Vendor Windows GUI** — what produced all three contexts here, and what the
     manufacturer recommends. Needs a Windows machine and a file transfer.
   - **`hsi_sensor_calibration/light_reference.py`** on Volta — self-contained and in-repo,
     writes to `/home/river/imec_light_reference/context`, and stamps the context with the
     pinned 1.12.0.0.
2. Copy it in under a descriptive name — not `context`.
3. **Write its `README.md` from the template before renaming anything.** The capture
   conditions are only in your head for about a day.
4. Rename to make it active, rebuild, and validate against a test cube.

## The Ximea now has references too

`config/ximea/context/` previously held only a description and an optical setup. It now
carries a calibration file, a dark reference at **10.049 ms**, and dark/white
non-uniformity references — the same structure as this directory's `context`.

Unlike the IMEC, the Ximea has **one** context, so there is nothing to choose between and
no renaming to get wrong.

> Note the different integration times: IMEC at 60 ms, Ximea at 10.049 ms. Each camera's
> dark reference is tied to its own, and `ambient_light_launch.py` sets both.

## See also

- `../../hyper_drive/hsi_sensor_calibration/light_reference.py` — the capture script
- `docs/manual/04-subsystems/perception/software/hyper-drive.md` — calibration, and why
  camera correction was removed from the ambient-light node
- `docs/manual/_templates/context-readme.md` — the template for these README files
