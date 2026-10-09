---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Bag schema

What to record, what it costs, and what a bag must contain to be usable later.

**Reference page.** For the procedure and naming see
[data-collection.md](../02-operations/data-collection.md); for the topics themselves see
[ros-graph.md](ros-graph.md).

> **Rates below are estimates**, not measurements — the `ros2 topic hz` pass has not been
> run. See [ros-graph.md](ros-graph.md#todoverify-rates-are-not-yet-measured). Sizes are
> computed from message definitions and are solid.

## You cannot record everything

| Topic | Message size | Est. rate | Throughput |
| --- | --- | --- | --- |
| `/synchronous_cubes` | **14.74 MB** | ~15 Hz | **~221 MB/s** |
| `/corrected_cubes` | **9.68 MB** | ~15 Hz | **~145 MB/s** |
| `/ouster/points` | **3.15 MB** | 10 Hz | **~31 MB/s** |
| `/insta360/equirectangular/image` | large | — | TODO(verify) |
| `/camera/image_raw` | 5.07 MB | TODO(verify) | — |
| `/ouster/imu` | ~60 B | ~100 Hz | negligible |
| `/insta360/imu/data_raw` | ~60 B | ~200 Hz | negligible |
| `/combined_spectra` | ~2.5 kB | ~20 Hz | negligible |
| `/gps_values`, `/kairos_values`, `/vehicle_control` | small | low | negligible |

**Recording the full graph is roughly 400 MB/s — about 1.4 TB per hour.** Against a
five-hour engine-off endurance, that is not a storage problem so much as an
impossibility.

| Profile | Rate | One hour |
| --- | --- | --- |
| Everything | ~400 MB/s | **~1.4 TB** |
| Lidar, IMUs, GPS, spectra — no imagery | ~32 MB/s | **~113 GB** |
| Non-imagery only | <0.1 MB/s | **~0.3 GB** |

**The decision that matters is cubes or no cubes.** Everything else is rounding error by
comparison.

> TODO(verify): record Volta's available storage and where bags are written. Nothing in the
> manual says, and at these rates it is the binding constraint on session length.

## Always record these

Four topics cost nothing and **without them a bag may be unusable**:

| Topic | Why | QoS |
| --- | --- | --- |
| `/tf_static` | The entire sensor geometry. Without it nothing can be placed in `base_link` | **Transient Local** |
| `/ouster/metadata` | Beam angles and the sensor's configuration. Without it the point cloud cannot be fully interpreted | **Transient Local** |
| `/tf` | The `odom → base_link` trajectory | |
| `/rosout` | Node logs. Invaluable when something turns out to have been wrong | |

**Both Transient Local topics publish once, at startup.** If recording begins after the
drivers have started, a bag may capture nothing on them.

> TODO(verify): confirm `ros2 bag record` picks up Transient Local topics started before
> it. rosbag2 subscribes with a matching durability, so a late subscriber *should* receive
> the latched message — but this is worth testing once rather than discovering in analysis.
> Test: start the stack, wait a minute, record for ten seconds, then
> `ros2 bag info` and check both topics have a non-zero message count.

## Recording profiles

### Navigation — the default

For state estimation, odometry work, and anything not about spectra.

```bash
ros2 bag record \
  /ouster/points /ouster/imu /ouster/metadata \
  /insta360/imu/data_raw \
  /kiss/odometry /graph_pose /odom_offset \
  /gps_values /kairos_values /vehicle_control \
  /tf /tf_static /rosout
```

**~32 MB/s, ~113 GB/h.** Dominated entirely by the point cloud.

### Spectral collection

Add the spectra and **one** cube topic.

```bash
ros2 bag record \
  /ouster/points /ouster/imu /ouster/metadata \
  /insta360/imu/data_raw \
  /kiss/odometry /graph_pose \
  /gps_values /kairos_values \
  /combined_spectra /ibsen_vnir/spectral_data /ibsen_nir/spectral_data \
  /corrected_cubes \
  /tf /tf_static /rosout
```

**~177 MB/s, ~640 GB/h.**

**Record `/corrected_cubes` or `/synchronous_cubes`, not both.** They carry the same
imagery; the first has ambient correction applied and no Alvium frame, the second is raw
with the frame attached. Recording both costs 366 MB/s for one dataset.

> TODO(verify): decide which is canonical. Arguments both ways — `/synchronous_cubes` is
> reproducible since correction can be re-run offline and it preserves the RGB frame;
> `/corrected_cubes` is 5 MB smaller per message and is what analysis actually consumes.
> The ambient correction depends on a hardcoded dark reference that may change, which
> argues for recording raw.

### Calibration bags

The ambient-light calibration scripts expect specific bags with specific contents.

| Bag | Topic | Captured with |
| --- | --- | --- |
| `white_bag` | `/synchronous_cubes` | Cameras imaging a white target |
| `dark_bag` | `/synchronous_cubes` | Lens capped |
| `point_white_bag` | `/combined_spectra` | Spectrometers on a white target |
| `point_dark_bag` | `/combined_spectra` | Fibre capped |

```bash
ros2 bag record /synchronous_cubes -o white_bag
ros2 bag record /combined_spectra -o point_white_bag
```

**These must use `/synchronous_cubes`**, not `/corrected_cubes` — the scripts extract
pre-correction references, and feeding them corrected data would be circular.

Convention places them in `~/ibex_ws/rosbag_library/`. See
[hyper-drive.md](../04-subsystems/perception/software/hyper-drive.md#regenerating-the-references).

A few seconds is enough — the scripts average every frame in the bag.

## The Best Effort trap

**`/ouster/points` and `/ouster/imu` are Best Effort**, set by
`use_system_default_qos: false` in `ibex_ouster_sensor_config.yaml`. That file's own
comment flags the consequence and points at rosbag2 issue 125.

**Best Effort means the publisher does not retransmit.** A recorder that falls behind — and
at 31 MB/s it can — loses messages silently, with no gap marker in the bag.

| | |
| --- | --- |
| Symptom | A bag with fewer point clouds than the duration implies |
| Detection | `ros2 bag info` message count against elapsed time × 10 Hz |
| Mitigation | `use_system_default_qos: true`, which makes it Reliable — at the cost of backpressure on the live system |

> TODO(verify): decide the policy. Flipping that parameter for recording sessions is a
> deliberate trade: Reliable guarantees a complete bag but lets a slow recorder stall the
> driver, which is worse during live operation. Recording to an SSD rather than to the
> system disk may remove the need to choose.

**Always check the message count** after a recording that matters:

```bash
ros2 bag info <bag>
```

## Storage format

rosbag2 supports `sqlite3` and `mcap`. The calibration scripts auto-detect from
`metadata.yaml` and accept either.

**mcap is the better choice here.** It handles large messages and high throughput
substantially better than sqlite3, which is what this vehicle produces.

```bash
ros2 bag record -s mcap ...
```

> TODO(verify): record which format is in use, and standardize. Mixed formats work with
> the calibration scripts but complicate everything else.

## What a bag should be accompanied by

[data-collection.md](../02-operations/data-collection.md) owns the naming convention —
`<site>-<subject>-<YYYY-MM-DD>` — and the `metadata.yaml` sidecar.

Things worth capturing there that a bag cannot record itself:

| | Why |
| --- | --- |
| Which launch files were running | Determines what is in the bag and what configuration produced it |
| Integration times for both cameras and both spectrometers | The dark references are tied to them |
| Weather and illumination | Spectral data is meaningless without it |
| Whether the vehicle was driven or stationary | Changes how odometry should be interpreted |
| Pack state of charge at start | The only record of it — see [system-battery.md](../04-subsystems/power/system-battery.md) |

## Known gaps

**No timestamps on spectra.** `Spectra` carries a header and neither the streamers nor the
combiner populate it, so recorded spectra cannot be aligned to anything in post. See
[spectrometer-drivers.md](../04-subsystems/perception/software/spectrometer-drivers.md#the-header-exists-and-is-never-set).

**No frame on cubes.** `header.frame_id` is unset on every `DataCube`, so recorded
hyperspectral data cannot be related to the point cloud even with `/tf_static` present.
See
[hyper-drive.md](../04-subsystems/perception/software/hyper-drive.md#cubes-carry-no-frame_id).

**Those two gaps limit what any bag recorded today can support.** Fixing them costs a few
lines each and would make every future bag substantially more useful — worth doing before
a large collection campaign rather than after.

## Open items

| Item | |
| --- | --- |
| **Rates unmeasured** | Every throughput figure here is an estimate |
| **Volta's storage capacity and bag location** | The binding constraint on session length |
| **`/synchronous_cubes` vs `/corrected_cubes`** | Which is canonical for archival |
| **Best Effort recording policy** | Complete bags versus live-system backpressure |
| **Transient Local capture** | Needs one test to confirm |
| **Storage format** | sqlite3 or mcap, standardize |
| **No spectra timestamps, no cube frames** | Limits what bags can support |

## Related

- [data-collection.md](../02-operations/data-collection.md) — procedure, naming,
  `metadata.yaml`
- [ros-graph.md](ros-graph.md) — topics, types, QoS
- [tf-frames.md](tf-frames.md) — what `/tf_static` carries
- [hyper-drive.md](../04-subsystems/perception/software/hyper-drive.md) — cube sizes, and
  the calibration scripts that read bags
- [ouster-ros.md](../04-subsystems/perception/software/ouster-ros.md) — the QoS setting
