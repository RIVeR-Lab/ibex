---
status: draft
owner: TODO(verify)
last-verified: 2026-10-29
---

# insta360_ros_driver

The Insta360 X4 driver, H.264 decoder, and equirectangular projector. Serves
[Perception](../README.md), and its IMU serves
[State estimation](../../state-estimation/README.md).

> **This page was substantially rewritten on 2026-10-29** after a three-day investigation
> into a laggy, corrupted image feed. Thirteen issues were found and most were fixed. If
> you are working from older notes, assume they are wrong — particularly about frame IDs,
> IMU timestamps, and video resolution.

## Source

| | |
| --- | --- |
| Upstream | RIVeR-Lab fork |
| In this repo | `packages/insta360_ros_driver` — **git submodule** |
| Namespace | `/insta360`, set by `config/namespace.yaml` |

## Fork status

A fork we control, which matters here — several of the fixes below are in the submodule
and need to stay there rather than being patched from outside.

## The pipeline

```
Insta360 X4 (USB 3)
   │
   ├─► insta360_ros_driver ──► dual_fisheye/image/compressed   H.264, ~8.5 Mbps
   │          │
   │          └──────────────► imu/data_raw                    500 Hz
   │                                │
   │                                └─► imu_filter (Madgwick) ─► imu/data
   │
   └─► dual_fisheye/image/compressed ─► image_decoder (NVDEC) ─► dual_fisheye/image
                                                                      │
                                                                      └─► equirectangular_node ─► equirectangular/image
```

Four nodes: the driver, the decoder, the Madgwick filter, and the equirectangular
projector.

## Measured stream properties

These are measured, not requested. **The camera ignores the `RES_1920_960P30` asked for in
`main.cpp`.**

| Property | Value |
| --- | --- |
| Video resolution | **2880 × 1440** dual fisheye — 1440 × 1440 per lens |
| Frame rate | 30 fps |
| Compressed bitrate | ~8.5 Mbps — mean message 35 kB, keyframes ~480 kB |
| Keyframe interval | 1.00 s, with SPS/PPS repeated on every keyframe |
| Decoded frame | 2880 × 1440 × 3 ≈ **12.4 MB** in `bgr8` |
| IMU rate | **~500 Hz**, 2.0 ms spacing |
| IMU timestamp unit | Milliseconds, camera clock |
| IMU delivery | **Batches of ~50 samples every ~100 ms** |

**Trust the resolution the node logs, not the resolution the driver requests.** A debugging
session was lost to assuming 1920 × 960 and deriving an equirectangular crop size from it.

Because SPS/PPS repeat on every keyframe, a decoder can join the stream mid-flight.

## Topics

| Topic | Type | Publisher | QoS |
| --- | --- | --- | --- |
| `dual_fisheye/image/compressed` | `sensor_msgs/CompressedImage` | driver | |
| `imu/data_raw` | `sensor_msgs/Imu` | driver | **RELIABLE, depth 200** |
| `dual_fisheye/image` | `sensor_msgs/Image` | decoder | |
| `equirectangular/image` | `sensor_msgs/Image` | equirectangular node | |
| `imu/data` | `sensor_msgs/Imu` | `imu_filter` | |

All relative, resolving under `/insta360`.

> **The IMU publisher is RELIABLE with depth 200**, chosen so a whole ~50-sample batch
> fits. That is compatible with both reliable and best-effort subscribers. Any subscriber
> wanting every sample needs **at least depth 200** of its own.

> **The equirectangular output is now `bgr8`**, previously `rgb8`. RViz handles either;
> check any other consumer that assumes RGB.

## Frames

| Parameter | Default | Applies to |
| --- | --- | --- |
| `frame_id` | `insta_sensor` | Driver, decoder, equirectangular node |
| `imu_frame_id` | `insta_imu` | Driver |

**The string `camera_frame` no longer appears anywhere in the code.** It previously
stamped every image with a frame that existed nowhere in the TF tree.

See [tf-frames.md](../../../05-reference/tf-frames.md) for where `insta_sensor` and
`insta_imu` sit.

## Parameters

| Node | Parameter | Value | Notes |
| --- | --- | --- | --- |
| driver | `frame_id`, `imu_frame_id` | `insta_sensor`, `insta_imu` | |
| decoder | `frame_id` | `insta_sensor` | |
| decoder | `subscription_depth` | | |
| equirectangular | `crop_size` | **1395** | Must match the lens circle in a 1440 × 1440 half |
| equirectangular | `rotation_deg`, `translation` | | **Tuned by eye** |
| equirectangular | `gpu` | — | **Unused.** The node is CPU-only and logs a warning |
| `imu_filter` | `publish_tf` | **false** | See below |
| `imu_filter` | `use_mag` | false | |

### YAML keys need a namespace wildcard

Parameter files were **silently ignored** because their top-level keys were bare node
names. ROS 2 matches those against the node's *full* name, so `imu_filter:` means
`/imu_filter` and never matches `/insta360/imu_filter`.

```yaml
/**/imu_filter:          # correct
  ros__parameters:
    use_mag: false
```

Both `imu_filter.yaml` and `equirectangular.yaml` were affected, and both nodes ran
entirely on defaults. Verify with `ros2 param get /insta360/imu_filter use_mag`.

**Config files load from the installed `share/` directory**, so edits take effect only
after a rebuild — unless the workspace is built with `--symlink-install`.

## IMU timestamps

**This is the most consequential change on the page**, and it is what makes the Insta360's
IMU usable for [state estimation](../../state-estimation/software/ibex-state.md).

**Previously** the SDK delivered samples in batches and the driver stamped every sample in
a batch with `now()`. A whole batch shared one timestamp, so consumers computing `dt` from
header stamps saw zero for most samples and then one large jump.

**Now** each sample carries its own camera-clock timestamp, mapped into ROS time:

```
ros_ns = camera_ts × ns_per_tick + offset_ns
```

The SDK does not document the tick unit, so **the driver measures it over the first
second** — camera-clock elapsed against ROS-clock elapsed, rounded to the nearest of
s / ms / µs / ns — and drops samples during that second. It logs the result:

```
IMU clock synced: camera timestamps are in milliseconds (measured 1005.7 ticks/s)
```

After that the offset tracks the smallest observed arrival-minus-camera time, so **stamps
can never be in the future**, and follows slow upward drift with a 1e-4 gain. Samples with
non-increasing timestamps are skipped with a throttled warning, and the clock is
re-measured if the camera clock jumps backwards by more than a second.

**Measured result:** ~500 Hz, mean spacing 2.0 ms, zero non-increasing stamps,
stamp-to-arrival lag 8–124 ms — expected with ~100 ms batching. Occasional gaps up to
18 ms have been seen.

> **`ros2 topic hz` cannot measure this.** It reports *arrival* times, not header stamps,
> and its small queue drops most of each burst. On this topic it reported **~52 Hz against
> a real 500 Hz.** Use `check_imu_timestamps.py` instead — see
> [Diagnostics](#diagnostics).

## Known issues & fixes

### The Madgwick filter still drops most samples — open

| | Rate | Gaps |
| --- | --- | --- |
| `imu/data_raw` | ~500 Hz | none |
| `imu/data` | **~66 Hz** | **up to 104 ms** |

**Cause:** each ~50-sample burst overflows the filter's short subscription queue. The
installed `imu_filter_madgwick` exposes QoS overrides only for its *publishers*, not for
its `imu/data_raw` subscription, so the depth cannot be raised through parameters.

**Consequence:** the filter's orientation is degraded during fast motion, since it
integrates across ~100 ms gaps. It looks fine when the camera is still, which is how this
went unnoticed.

**It does not affect state estimation.** `ibex_state` subscribes to `imu/data_raw` and does
its own preintegration in GTSAM — the normal arrangement for a factor-graph pipeline.

> TODO(verify): decide what the filter is for. Options are to keep it for visualization
> only, fork `imu_tools` and raise the subscription depth, or pace IMU publishing in the
> driver — the last adding ~100 ms of latency. **If nothing needs filtered orientation,
> `imu_filter:=false` removes a node and changes nothing downstream.**

### Video frames are not on the camera clock — open

IMU samples carry camera-clock stamps; **video frames are stamped with `now()` at publish
time.** The two are offset by different, varying latencies.

**This blocks any camera-IMU fusion**, and it must be fixed before calibrating extrinsics —
calibrating over misaligned timestamps folds the time offset into the extrinsic and hides
it.

> TODO(verify): the fix has a known shape. Determine whether `OnVideoData`'s `int64_t
> timestamp` shares the gyro clock, move the clock-mapping logic into a class used by both
> streams, and carry the stamp through `decoder.cpp` rather than restamping in the
> publisher thread. Validate by tapping the camera — the IMU spike and the first frame
> showing motion should line up within a frame.

### Fast DDS shared-memory limit on decoded images — fixed

**Symptom:** 5–6 decoder queue drops per second with RViz subscribed, ~20/s with RViz and
the equirectangular node both subscribed. Best-effort depth-1 subscriptions did not help.

**Cause:** Fast DDS's shared-memory transport defaults to a **512 kB segment**. A 12.4 MB
decoded image does not fit, so every frame fell back to UDP over loopback and was
fragmented — **once per subscriber.** Best effort only removes acknowledgements; it does
not reduce the copy and send cost.

**Fix:** `config/fastdds_large_msgs.xml` defines a **64 MB** shared-memory segment plus UDP
for off-machine traffic, loaded through `FASTRTPS_DEFAULT_PROFILES_FILE`.

**Result:** zero drops in both configurations; decoder CPU fell to ~48% with no thread
near 100%.

> **Every process must see that variable**, including RViz and CLI tools launched from
> other terminals. It is set in the launch file for nodes it starts, and in `~/.bashrc` for
> everything else. **An autostart service that does not load `~/.bashrc` will reintroduce
> the drops.**

### RViz "queue is full" means a missing TF frame — fixed

**Lesson worth keeping:** `Message Filter ... discarding message because the queue is full`
in RViz almost always means a **missing or disconnected TF frame**, not bandwidth. RViz
holds each message until it can transform its `frame_id` into the Fixed Frame; with a frame
that never resolves, the queue simply fills.

The same message had appeared earlier with the Ouster.

### Decoder kept old frames instead of new — fixed

The publish queue discarded the *newest* frame when full, keeping up to 10 older ones, so
viewers saw frames up to ~330 ms stale. **It now drops the oldest and keeps the newest,
with depth reduced from 10 to 2.** A live camera should skip ahead, not work through a
backlog.

### Equirectangular node at 527% CPU — fixed

| Change | Effect |
| --- | --- |
| One combined remap map, built once at startup | Halves per-frame work — the old version remapped each lens full-size then discarded half |
| `INTER_LINEAR` instead of `INTER_CUBIC` | Much cheaper per pixel |
| Fixed-point maps, `CV_16SC2` | Faster remap |
| `toCvShare` in `bgr8` | No per-frame copy or colour conversion |
| Best-effort depth-1 subscription | Never stalls the decoder's publisher |

**527% → 89% CPU; load average 6.95 → 1.47.** The projection maths is unchanged.

### Parameter callback never worked — fixed

Two bugs at once. The `add_on_set_parameters_callback` handle was a local variable, so the
callback unregistered as soon as the constructor returned — `ros2 param set` was accepted
and did nothing. And the callback read values with `get_parameter()`, but set-parameter
callbacks run **before** new values are stored, so it would have read the old ones anyway.

Now the handle is a class member and the callback reads from its `parameters` argument,
validating and rejecting bad values with a reason.

### Madgwick would have broken the TF tree — fixed

`publish_tf: true` makes the filter publish `imu_stabilized → insta_imu`. But `insta_imu`
already has a parent from the static transforms, **and a TF frame can only have one
parent.** Set to `false`; `view_frames` confirms a single parent.

### bringup_launch.xml should be removed — open

It uses no namespace and absolute topics, so it disagrees with `insta_bringup_launch.py`.
**Launching both would start two drivers competing for the camera.**

## Diagnostics

Two scripts in `scripts/`, both worth knowing about.

```bash
python3 check_h264_stream_integrity.py --topic /insta360/dual_fisheye/image/compressed --duration 30
python3 check_imu_timestamps.py --topic /insta360/imu/data_raw --duration 10
```

**`check_h264_stream_integrity.py`** records the compressed topic without decoding and runs
`ffmpeg` over it. **CLEAN** means the stream arriving over ROS is intact, so any corruption
is in the decoder or later. It skips messages until the first SPS, because frames before
the first keyframe cannot be decoded and would otherwise read as damage — that false
positive cost a round of investigation.

**`check_imu_timestamps.py`** checks header stamps, which `ros2 topic hz` cannot.

### Decoder diagnostics

One line per second:

```
rx 30 msg/s | decoded 30 fps | queue drops 0 | send errors 0 | max callback 15.0 ms
```

| Reading | Meaning |
| --- | --- |
| `rx` < 30, or `max callback` > 33 ms | Decoder too slow; compressed frames overwritten before decode → **corruption** |
| `rx` ≈ 30, `decoded` ≈ 30, drops > 0 | Decode fine; publishing is the bottleneck → frame-rate loss only |
| `decoded` below `rx` | Packets arrive but fail to decode; check FFmpeg warnings |

A few `non-existing PPS 0 referenced` lines at startup are normal.

### Reading htop

CPU% is per core — 100% is one full core, and Volta has 22. **A single thread near 100% is
a bottleneck**, because one thread cannot exceed one core. That pattern is what identified
the publisher-thread bottleneck behind the shared-memory issue.

## Running a single node by hand

The nodes use relative topic names, so a bare `ros2 run` puts them in the root namespace
and they publish on the wrong topics:

```bash
ros2 run insta360_ros_driver decoder --ros-args -r __ns:=/insta360 -r __node:=image_decoder
```

**Launch arguments such as `equirectangular:=true` work only with `ros2 launch`.** Given to
`ros2 run` they parse as old-style remap rules, warn, and do nothing.

## Host configuration

Outside the repository, and required.

**`/etc/sysctl.d/60-ros2-dds.conf`**, applied with `sudo sysctl --system`:

```
net.core.rmem_max=2147483647
net.core.rmem_default=33554432
net.ipv4.ipfrag_time=3
net.ipv4.ipfrag_high_thresh=134217728
```

`rmem_default` was deliberately kept moderate, since it applies to every socket on the
system.

**`~/.bashrc`:**

```bash
export FASTRTPS_DEFAULT_PROFILES_FILE=$HOME/ibex_ws/config/fastdds_large_msgs.xml
```

> TODO(verify): point this at the installed copy under
> `install/insta360_ros_driver/share/insta360_ros_driver/config/`, or a stable copy, so
> terminals and the launch file use the same profile. See
> [compute.md](../../../05-reference/compute.md).

## Recording

For calibration and estimator work:

```bash
ros2 bag record -s mcap \
  /insta360/dual_fisheye/image/compressed \
  /insta360/imu/data_raw \
  /tf_static
```

**Do not record the decoded or equirectangular images.** Decoded frames are ~12.4 MB each —
about **370 MB/s at 30 fps** — against ~8.5 Mbps for the compressed stream, which can be
decoded again on playback. See [bag-schema.md](../../../05-reference/bag-schema.md).

## Open items

| Item | |
| --- | --- |
| **Video stamps use `now()`** | Blocks camera-IMU fusion and extrinsic calibration |
| **Madgwick drops samples** | Decide what the filter is for |
| **IMU noise unknown** | Covariances are zero. Needs an Allan variance run |
| **`insta_imu` yaw is an estimate** | Unobservable from gravity; needs Kalibr |
| **Camera intrinsics** | None. Equirectangular parameters tuned by eye |
| **Remove `bringup_launch.xml`** | Two drivers would compete for the camera |
| **`gpu` parameter unused** | A CUDA remap would offload the remaining load |

## Related pages

- [insta360-x4.md](../hardware/insta360-x4.md) — the camera
- [ibex-state.md](../../state-estimation/software/ibex-state.md) — consumes `imu/data_raw`
- [tf-frames.md](../../../05-reference/tf-frames.md) — `insta_sensor`, `insta_imu`, and the
  unverified yaw
- [compute.md](../../../05-reference/compute.md) — the DDS profile and host sysctl
- [bag-schema.md](../../../05-reference/bag-schema.md) — what to record
- [launch-files.md](../../../05-reference/launch-files.md) — `insta_bringup_launch.py`
