---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# State estimation

Where IBEX thinks it is. Two packages, no hardware of its own — it consumes sensors
belonging to [Perception](../perception/) and [Motion](../motion/).

| Package | Type | Role |
| --- | --- | --- |
| [`kiss-icp`](software/kiss-icp.md) | Submodule, tracks upstream | Lidar odometry front end |
| [`ibex_state`](software/ibex-state.md) | In-repo | GTSAM factor graph back end |

## The pipeline

```
Ouster OS1-64 ──point cloud──> kiss-icp ──relative pose──┐
              │                                           │
              └──IMU (BMI085)─────────────────────────────┤
                                                          ├──> ibex_state ──> vehicle pose
GPS (on the P4S4) ──SharedLink UDP──> shared_link_bridge ─┤     GTSAM
                                      /gps_values         │   factor graph
                                                          │
ibex_bringup ──static transforms──────────────────────────┘
```

Three measurement sources, each arriving by a completely different route:

| Input | Source | Path |
| --- | --- | --- |
| Relative pose | Ouster point cloud | `ouster-ros` → `kiss-icp` → `/kiss/odometry` |
| Inertial, 1 | Ouster's built-in BMI085 | `ouster-ros` → `/ouster/imu` |
| Inertial, 2 | **Insta360 X4's IMU** | `insta360_ros_driver` → `/insta360/imu/data_raw` |
| Global position | GPS on the Kairos P4S4 | SharedLink UDP → `shared_link_bridge` → `/gps_values` |
| Vehicle dynamics | Drive-by-wire `(v, δ)` | **Not connected — hardcoded to zero** |

**Two IMUs, not one.** `ibex_state` runs separate GTSAM preintegration pipelines for the
Ouster's and the Insta360's, each with its own bias chain and extrinsics. A consumer action
camera is therefore contributing inertial constraints to the vehicle pose.

## Why a loosely coupled architecture

The lidar front end and the graph back end are separate processes with a topic between
them, rather than one tightly integrated estimator.

**The front end** turns consecutive scans into relative pose estimates. It does not know
about GPS, IMU, or any global frame — just how the vehicle moved between two clouds.

**The back end** takes those relative poses as constraints in a factor graph, adds IMU
preintegration and GPS as global constraints, and optimizes the whole trajectory.

The benefit is that either half can be replaced without touching the other, and
`kiss-icp` can be tracked from upstream rather than forked. The cost is an extra
serialization hop and a dependency on timestamps lining up — see below.

**Each source contributes something the others cannot.** Lidar odometry is locally
accurate and drifts without bound. GPS is globally correct and locally noisy. The IMU
fills the gaps between scans and helps through the moments when lidar geometry is
degenerate. That complementarity is the reason for fusing them rather than picking one.

> The Ouster's IMU matters particularly for **yaw at standstill**, where a stationary
> consumer-grade IMU gives little heading observability and lidar odometry has no motion to
> work from.

## The clock problem

**This is the most significant open issue in the subsystem.** A factor graph is an
optimization over time-stamped measurements, and IBEX currently has **three independent
time sources** with nothing synchronising them:

| Source | Clock |
| --- | --- |
| Ouster point cloud and IMU | The sensor's own oscillator — `timestamp_mode: TIME_FROM_INTERNAL_OSC` |
| GPS | The P4S4's, arriving over UDP with no timestamp preserved |
| Everything else | Volta's system clock |

The Ouster supports `TIME_FROM_PTP_1588` and `TIME_FROM_SYNC_PULSE_IN`, and its
`multipurpose_io_mode` is currently `OFF`, so the sync-pulse input is unused. See
[ouster-os1-64.md](../perception/hardware/ouster-os1-64.md).

> TODO(verify): establish how much the clocks actually diverge, and whether it is
> affecting the estimate. Drift between the lidar and the IMU is the dangerous case,
> because IMU preintegration between two lidar poses assumes the interval is known — an
> error there appears as a bias in the optimized trajectory rather than as an obvious
> fault.
>
> There is also a ready-made fix available: the GPS on the P4S4 could drive the Ouster's
> sync-pulse input, which would put the lidar on GPS time. That is worth considering before
> building anything around the current arrangement.

## What is not being used

**Vehicle telemetry from the P4S4 — and this is now the subsystem's most urgent gap.**
`shared_link_bridge` publishes `/kairos_values`, carrying speed and steering angle among
other vehicle state. None of it reaches the factor graph.

That is not merely a missed opportunity. The backbone of `ibex_state` is a bicycle-model
dynamics factor that consumes `(v, δ)` — and both are **hardcoded to zero**, with a 5 mm
standard deviation. So the graph is told at 6 Hz that the vehicle is stationary, tightly,
while it drives. At 5 m/s that assertion is 167 standard deviations from the truth, and it
is weighted ten times more heavily than the lidar.

**The control-driven backbone is the single feature that justified writing a custom back
end instead of adopting a SLAM package**, and it is currently inert. See
[ibex-state.md](software/ibex-state.md#the-control-input-is-not-connected).

**The SICK lidar**, once it has a driver. A second geometry source swept to 3D would give
an independent odometry input and a direct cross-check on the Ouster — see
[sick-picoscan-150.md](../perception/hardware/sick-picoscan-150.md).

## Known issues spanning the subsystem

**`ibex_state` depends on the whole of `shared_link_bridge`.** It consumes `/gps_values`,
whose type `shared_link_bridge/msg/GpsValues` is defined inside the driver package rather
than in a separate interfaces package. So building state estimation drags in the Kairos
driver, its teleop GUI, and everything else. See
[shared-link-bridge.md](../motion/software/shared-link-bridge.md#message-definitions).

**The Ouster's driver config must set `min_scan_valid_columns_ratio` above zero.** At the
upstream default of 0.0 the driver passes through scans with no valid columns and KISS-ICP
errors on them. IBEX sets 0.1. See
[ouster-ros.md](../perception/software/ouster-ros.md).

**GPS quality is unrecorded.** The P4S4's GPS has a documented failure history — a broken
internal cable that required returning the unit. Nothing records what kind of fix it
provides.

> TODO(verify): establish whether it is a basic GNSS receiver or something better. The
> difference between metre-level and centimetre-level accuracy changes how GPS should be
> weighted in the graph, and whether it should constrain position at all or only bound
> drift. Shepherd displays GPS status and satellite count, which is one way to inspect it.

## Pages

| Page | Covers |
| --- | --- |
| [kiss-icp.md](software/kiss-icp.md) | The lidar odometry front end. Upstream submodule, not a fork |
| [ibex-state.md](software/ibex-state.md) | The factor graph, its estimator code, and configuration |

No hardware pages. The sensors this subsystem depends on are documented where they live:

- [ouster-os1-64.md](../perception/hardware/ouster-os1-64.md) — point cloud and IMU
- [kairos-p4s4.md](../motion/hardware/kairos-p4s4.md) — carries the GPS

## Open questions

| Question | Why it matters |
| --- | --- |
| **Connecting `(v, δ)` from `/kairos_values`** | The backbone asserts stationarity at 6 Hz until this is done. Highest priority in the subsystem |
| **IBEX's actual wheelbase** | Configured at 1.2 m with a TODO; the transform tree implies roughly double. Scales yaw rate directly once `(v, δ)` is connected |
| What accuracy does the P4S4's GPS deliver? | The noise model assumes 1.5–15 m as an admitted placeholder. Needs the receiver spec or a parked-scatter calibration |
| How far apart do the three clocks drift? | Determines whether the fused estimate is trustworthy |
| Does anything publish the `insta_imu` frame? | `ibex_state` blocks at startup forever without it |
| Is anything consuming `graph_pose`? | Determines whether this subsystem currently has a downstream user |
| Is the Ouster's installed tilt the design tilt? | Every extrinsic in the chain depends on it — see [Perception](../perception/README.md) |

**Two frames are published as labels with no transform.** `ibex_state` stamps its output
`aligned_odom` and its offset `utm`, and broadcasts no TF for either — so `tf2` lookups
against them fail and RViz cannot use them as a fixed frame. See
[tf-frames.md](../../05-reference/tf-frames.md).

## Related

- [04-subsystems/README.md](../README.md) — the interconnect and processing diagrams
- [perception/](../perception/) — the Ouster, and the SICK when it arrives
- [motion/](../motion/) — the P4S4 carrying the GPS, and `shared_link_bridge`
- [tf-frames.md](../../05-reference/tf-frames.md) — `map`, `odom`, `base_link`, and the
  sensor chain
- [ros-graph.md](../../05-reference/ros-graph.md) — topics and rates
- [glossary.md](../../00-onboarding/glossary.md) — ICP, factor graph, preintegration,
  `map` versus `odom`
