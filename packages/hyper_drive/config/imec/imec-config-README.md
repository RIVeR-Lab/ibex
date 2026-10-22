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
written by HSI Mosaic 2.11.10.0.

**`context_base` contains no references at all** — only a description and an optical
setup. Loading it means running with no dark subtraction and no flat-fielding. It is a
starting point for building a new context, not a usable one.

## Before switching

Renaming a directory to `context` puts it in play immediately, with no warning and no
error if it is wrong. Check three things first:

**Integration time.** Each context's dark reference is tied to one. Both populated
contexts here are 60 ms, and `ambient_light_launch.py` sets `i_integration_time: 60`. If
you change either, they must change together.

**Aperture.** `context` records f/2.8; the other two record 0. Either the other two are
mislabelled or the aperture genuinely differed — and if it differed, they are not
interchangeable at all, because Fabry–Pérot band response depends on the angle of incoming
light.

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

1. Capture with `hyper_drive/hyper_drive/hsi_sensor_calibration/light_reference.py`, which
   writes to `/home/river/imec_light_reference/context`.
2. Copy it in under a descriptive name — not `context`.
3. **Write its `README.md` from the template before renaming anything.** The capture
   conditions are only in your head for about a day.
4. Rename to make it active, rebuild, and validate against a test cube.

## The Ximea has no references at all

`config/ximea/context/` contains a description and an optical setup and **no dark or
non-uniformity references**. The Ximea VNIR camera is therefore not flat-fielded, which
has consequences well beyond this directory — see the manual's Perception pages.

`light_reference.py` is IMEC-specific but is the obvious starting point: it needs
`EM_IMEC` changed to `EM_XIMEA` and the ROI changed to 2045 × 1085.

## See also

- `../../hyper_drive/hsi_sensor_calibration/light_reference.py` — the capture script
- `docs/manual/04-subsystems/perception/software/hyper-drive.md` — calibration, and why
  camera correction was removed from the ambient-light node
- `docs/manual/_templates/context-readme.md` — the template for these README files
