---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# ibex_state

The state estimation back end. Serves [State estimation](../README.md).

A GTSAM factor graph that fuses lidar odometry, two IMUs, GPS, and vehicle dynamics into a
single 6-DoF pose with covariance, published at a fixed rate.

**It is the most architecturally involved package in the repository**, and it is custom
rather than adapted — the design rationale is recorded in full under
[Why GTSAM](#why-gtsam) and [Why not a SLAM package](#why-not-a-slam-package), because it
is the kind of reasoning that is expensive to reconstruct later.

> **One line of code currently undermines the whole backbone.** The control input driving
> the dynamics factor is hardcoded to zero. See
> [The control input is not connected](#the-control-input-is-not-connected) before
> interpreting any output from this node.

## Source

| | |
| --- | --- |
| In this repo | `packages/ibex_state` — committed directly, not a submodule |
| Build type | `ament_python` |
| Licence | Apache-2.0 |
| Maintainer | Ben Cometto |

## Fork status

Not a fork. First-party lab code.

## Description

Three layers:

| Layer | File | Role |
| --- | --- | --- |
| ROS node | `graph_frontender.py` | Thin wrapper — timer and subscriptions feed the estimator, publishers drain it |
| Estimator | `estimator/estimators.py` | `GraphReckoner` — the factor graph, the smoother, all the chain management |
| Custom factors | `estimator/factors.py` | Six factors GTSAM does not provide |
| Symbols | `estimator/symbols.py` | Fixed single-character GTSAM key prefixes |

The node is deliberately thin. `GraphReckoner`'s interface is callback-shaped —
`add_primary`, `add_lidar`, `add_gps`, `add_imu` — so the ROS layer contains no estimation
logic and the estimator has no ROS dependency.

### The architecture in one paragraph

A **primary pose chain** advances on a fixed ~6 Hz timer, linked by a bicycle-model
dynamics factor. Asynchronous measurements do not snap to that chain: each lidar and GPS
reading creates its own **transient residual node** at its own true timestamp, which is
then linked forward to the next primary node by a dynamics-propagation factor over the
exact elapsed interval. Three **latent chains** — lidar drift, the odom-to-UTM offset, and
odom's tilt relative to gravity — absorb the slowly-varying unknowns. The whole thing is
solved incrementally by an `IncrementalFixedLagSmoother` over a 5-second window.

## Capabilities

### Graph variables

From `symbols.py`, with an import-time assertion that no prefix collides:

| Prefix | Variable | Chain behaviour |
| --- | --- | --- |
| `x` | Primary pose, `Pose3` | Timer-driven backbone, ~6 Hz |
| `v` | Velocity, `Vector3` | One per primary pose |
| `r` | Angular rate (roll̇, pitcḣ), `Vector2` | Constant-velocity chain |
| `d` | Lidar drift, `Pose3` | Latent, grows per lidar reading, √dt random walk |
| `l` | Lidar residual, `Pose3` | **Transient**, one per lidar reading |
| `g` | GPS residual, `Pose3` | **Transient**, one per GPS fix |
| `o` | Odom offset, `Pose2` | Latent, grows per GPS fix |
| `w` | Gravity align (roll, pitch), `Vector2` | Latent, grows only when stationary |
| `b` | Ouster IMU bias | Random walk, √dt scaled |
| `c` | Insta360 IMU bias | Random walk, √dt scaled |

### The six custom factors

GTSAM provides priors, between-factors, and IMU preintegration. These encode what it does
not:

| Factor | Ties | Asserts |
| --- | --- | --- |
| `make_nhc_factor` | pose, velocity | Body-frame lateral and vertical velocity ≈ 0 — no sideslip, no independent bounce |
| `make_rate_tie_factor` | two poses, rate | Roll/pitch change between poses matches the estimated rate × dt |
| `make_rate_cv_factor` | two rates | Constant angular rate |
| `make_lidar_drift_factor` | pose, drift | `pose ∘ drift` explains the raw lidar reading |
| `make_gps_odom_offset_factor` | GPS residual, gravity align, odom offset | A UTM fix, after tilt correction and offset, matches the backbone |
| `make_gravity_align_factor` | pose, gravity align | A stationary accelerometer reading is explained by gravity alone |

All six compute **numerical Jacobians** by central differences with `eps=1e-6`, through
`gtsam.CustomFactor` in Python.

**The lidar drift factor is the statistically important one.** It means the lidar residual
observes `pose ∘ drift` rather than `pose` directly, so KISS-ICP's accumulated error is
absorbed by an explicit latent state instead of being double-counted as independent
measurement noise. That is what makes consuming an external odometry front end honest
rather than convenient.

## Purpose

IBEX carries a heterogeneous sensor set producing measurements at different rates, in
different frames, with different failure modes:

| Source | Rate | Frame | Observes |
| --- | --- | --- | --- |
| Drive-by-wire commands (`v`, `δ`) | Fixed timer | Body | Relative motion, via bicycle model |
| Ouster IMU | ~100 Hz | Sensor → body | Angular rate, specific force |
| Insta360 IMU | ~200 Hz | Sensor → body | Angular rate, specific force |
| KISS-ICP lidar odometry | ~10 Hz | Arbitrary odom | Full 6-DoF pose, drifting |
| GNSS | ~1–5 Hz, dropout-prone | UTM | Absolute 2D position |

The estimator must produce one consistent 6-DoF pose plus a usable covariance, at a fixed
publish rate, from all of it.

Three properties of that problem drive the entire architecture:

**Measurements are asynchronous and land between backbone ticks.** A lidar pose stamped at
*t* aligns with no primary node, so something has to reconcile timestamps rather than
snapping measurements to the nearest state.

**Several unknowns are latent and slowly varying.** KISS-ICP's accumulated drift, the
odom-to-UTM transform, and odom's tilt relative to gravity must all be *inferred* from the
same measurement stream that depends on them.

**Evidence arrives late and should correct the past.** A GPS fix after a dropout says
something about where the vehicle was *during* the dropout, not only where it is now.

## Why a factor graph rather than a filter

An EKF propagates a single mean and covariance forward, and the past is baked in. Three
consequences make it a poor fit:

**No retroactive correction.** When a delayed measurement lands, a filter can only update
the present. A smoother re-solves the window and redistributes the correction across every
pose the measurement actually informs.

**Latent calibration states are awkward.** Augmenting a filter's state with drift, offset,
and tilt works in principle — but their correlations with the trajectory are exactly what
makes them observable, and a single joint covariance handles that far less naturally than
an explicit graph where each latent has its own chain and its own process noise.

**Relinearization is one-shot.** An EKF linearizes once at the current estimate and can
never revisit that choice. Nonlinear least squares re-linearizes and iterates.

## Why GTSAM

Several libraries solve sparse nonlinear least squares. GTSAM was chosen for what it
provides *above* the solver:

**Native manifold types with analytic Jacobians.** `Pose3`, `Rot3`, `Pose2`, `NavState`,
and `imuBias::ConstantBias` are first-class, with correct `retract` / `localCoordinates`
and Jacobians that compose automatically. Rotations are never over-parameterized or
renormalized by hand. A generic solver like Ceres would mean building that layer manually.

**iSAM2 and incremental solving.** The Bayes-tree formulation re-eliminates only the
cliques a new factor touches and relinearizes fluidly rather than globally, which is what
makes a growing graph tractable at control rates.

**`IncrementalFixedLagSmoother`.** This is the specific capability the design is built
around: a smoother's retroactive correction over a 5-second window at a filter's bounded
cost, by marginalizing variables older than `lag_seconds`. No other library offers it off
the shelf.

**IMU preintegration.** `PreintegratedImuMeasurements` and `ImuFactor` compress hundreds of
raw samples into one factor between consecutive poses, with bias-corrected re-evaluation on
relinearization. Implementing that correctly is a serious undertaking on its own.

**Marginal and joint covariance as first-class output.** `get_aligned_covariance()` depends
on this directly — it pulls the *joint* covariance of the pose and the gravity-align state,
cross-terms included, and propagates both through the alignment composition rather than
treating the correction as a known constant.

**A real custom-factor API.** `NoiseModelFactorN` and `CustomFactor` are supported
extension points, not workarounds. Six custom factors is what makes the design possible at
all.

### Capabilities actually exercised

| GTSAM capability | Where |
| --- | --- |
| `NonlinearFactorGraph`, `Values`, `Symbol` | Throughout; prefixes in `symbols.py` |
| `ISAM2` + `ISAM2Params` | `relinearizeSkip=1`, via the smoother |
| `IncrementalFixedLagSmoother` (`gtsam_unstable`) | Bounded-window solving, in `_push()` |
| `Pose3`, `Pose2`, `Rot3.Ypr` | Backbone, offset chain, alignment |
| `PriorFactor{Pose3,Pose2,Vector,ConstantBias}` | Chain roots, re-bootstraps, weak rank fixes |
| `BetweenFactor{Pose3,Pose2,Vector,ConstantBias}` | Dynamics, propagation, every latent chain, bias walks |
| `PreintegratedImuMeasurements` + `ImuFactor` | Per-IMU inertial constraints |
| `PreintegrationParams.setBodyPSensor` | Per-IMU extrinsics |
| `marginalCovariance` | `get_covariance`, `get_odom_offset_covariance` |
| `Marginals.jointMarginalCovariance` | `get_aligned_covariance` cross-covariance propagation |
| `CustomFactor` | The six factors in `factors.py` |
| `Values.exists` | Detecting marginalized-out keys before re-bootstrap |

## Why not a SLAM package

LIO-SAM, GLIM, and MOLA were considered. The short answer: **this is not a SLAM system,
and those are.**

Those packages are organized around keyframes, a persistent map, place recognition, and
loop closure. This estimator has none of them — no map, no place recognition, no loop
closure. It is a dead-reckoning and sensor-fusion problem with a different shape:

**A fixed-rate backbone driven by control input.** The primary chain advances on a timer
and its dynamics factor comes from a bicycle model consuming the current `(v, δ)` command —
motion prediction from what the vehicle was *told to do*, not from what a scan matcher
observed. No SLAM package has a place for that; their backbones are keyframe-driven and
measurement-triggered.

**Vehicle-specific structural constraints.** The non-holonomic factor encodes that a
car-like platform does not move sideways. That is a strong, free prior available only
because the platform is known, and nothing in a general lidar-SLAM package expresses it.

**Timestamp-exact transient residual nodes**, rather than snapping asynchronous
measurements to the nearest keyframe.

**Three explicit latent chains**, each with process noise matched to its actual physics.

**Two heterogeneous IMUs**, with separate preintegration pipelines, bias chains, and
extrinsics. Standard packages assume one.

None of that is a modification to an existing back end. It is a different back end — and
writing it directly is the cheaper path, because the front end is the expensive part and
[KISS-ICP](kiss-icp.md) already handles it.

## Launch / invocation

```bash
ros2 launch ibex_state graph_frontender.launch.py
```

Loads `config/graph_frontender_config.yaml` from the installed share directory. The launch
file declares no arguments — all configuration is in the YAML.

**Preconditions.** The node **blocks indefinitely at startup** until it can look up two
static transforms, so these are hard requirements rather than recommendations:

- `base_link` → `os_imu`, published by the Ouster driver
- `base_link` → `insta_imu`
- The static chain from `ibex_bringup`

> That blocking is deliberate and documented in the code: frames like `os_imu` only appear
> once the Ouster's lifecycle node finishes activating, which can take over a minute. It
> retries forever rather than timing out, logging every 10 seconds.

> TODO(verify): **confirm something publishes `insta_imu`.** Nothing recorded so far does.
> The Insta360 driver's `imu_filter` publishes to `/tf`, but its frames are unknown — see
> [insta360-ros-driver.md](../../perception/software/insta360-ros-driver.md#imu_filter-publishes-to-tf).
> If `insta_imu` does not exist, this node hangs at startup forever and the only symptom is
> a log line every 10 seconds.

## Topics

### Subscribed

| Topic | Type | QoS | Source |
| --- | --- | --- | --- |
| `/kiss/odometry` | `nav_msgs/Odometry` | depth 10 | [KISS-ICP](kiss-icp.md) |
| `/ouster/imu` | `sensor_msgs/Imu` | `sensor_data` | [ouster-ros](../../perception/software/ouster-ros.md) |
| `/insta360/imu/data_raw` | `sensor_msgs/Imu` | `sensor_data` | [insta360_ros_driver](../../perception/software/insta360-ros-driver.md) |
| `/gps_values` | `shared_link_bridge/GpsValues` | depth 10 | [shared_link_bridge](../../motion/software/shared-link-bridge.md) |

> **It subscribes to the Insta360's `data_raw`, not its filtered `data`.** That bypasses
> the Madgwick filter entirely — which matters, because that filter is subscribed to a
> magnetometer nothing publishes and may never publish at all. State estimation is
> unaffected by it.
>
> It also means **the Insta360 is a state-estimation sensor, not only a context camera.**
> Its hardware page describes it as context rather than measurement, which is now only half
> true.

> TODO(verify): the Ouster publishes `/ouster/imu` as **best effort**, and this node
> subscribes with `qos_profile_sensor_data` — which is also best effort, so they match.
> Confirm the same for `/kiss/odometry`, which is subscribed with a plain depth-10 profile
> (reliable by default). If KISS-ICP publishes best effort, **this subscription will
> silently receive nothing.**

> TODO(verify): the config sets `lidar_odom_topic: "/kiss/odometry"`, but
> [running-the-system.md](../../../02-operations/running-the-system.md) launches KISS-ICP
> with no remap, so its topic is whatever upstream names it. Confirm they match.

### Published

| Topic | Type | Frame | Contents |
| --- | --- | --- | --- |
| `graph_pose` | `PoseWithCovarianceStamped` | `aligned_odom` | The fused pose estimate, gravity-corrected |
| `odom_offset` | `PoseWithCovarianceStamped` | `utm` | The odom origin's easting, northing, and yaw in UTM |

Both publish every primary tick, ~6 Hz.

`odom_offset` is SE(2) — GPS supplies no altitude or heading — so its z, roll, and pitch
covariance diagonals are set to **1e6 placeholders rather than 0**, which would
misleadingly read as perfectly known.

### No transform is broadcast

The node creates a TF **listener** and no broadcaster. So `aligned_odom` and `utm` appear
as `frame_id` strings on published poses with **no corresponding entry in the transform
tree.**

> TODO(verify): this is a real gap. Anything attempting `tf2` lookups involving
> `aligned_odom` will fail, and RViz cannot use it as a fixed frame. Either broadcast
> `odom` → `aligned_odom` and `utm` → `odom`, or document that these frames are
> message-local labels only. Also needed in
> [tf-frames.md](../../../05-reference/tf-frames.md), which currently accounts for neither.

### aligned_odom versus odom

Worth being precise, because the distinction is deliberate and easy to misread:

| Frame | |
| --- | --- |
| `odom` | KISS-ICP's own lidar-odometry frame. Starts at an arbitrary, **not gravity-aware** identity. Used internally as the backbone's frame. **Never published** |
| `aligned_odom` | `odom` rotated in place about its own origin so +z is antiparallel to gravity. Yaw is left alone — gravity cannot observe it. **This is what is published** |

The backbone chain and its prior deliberately stay in raw `odom` to match KISS-ICP's
convention. Gravity correction is a fully separate latent applied only when producing
output and when comparing GPS fixes, which keeps the backbone and the lidar drift prior
consistent with each other.

> Correcting for gravity by loosening the backbone's prior was tried and reverted: it
> fights the lidar drift prior, which assumes drift starts near identity to match that same
> KISS-ICP convention.

## Parameters

All in `config/graph_frontender_config.yaml`.

### Structure

| Parameter | Value | Effect |
| --- | --- | --- |
| `wheelbase` | 1.2 | **Placeholder — see [Known issues](#the-wheelbase-is-a-placeholder)** |
| `primary_period_s` | 0.167 | ~6 Hz backbone |
| `lag_seconds` | 5.0 | Fixed-lag smoothing window |

### Enables

`enable_lidar`, `enable_IMUs`, `enable_NHC`, `enable_rate`, `enable_gps` are all `true`;
`enable_debugging` is `false`.

> The code's default for `enable_debugging` is `True`, so running the node without the
> config file produces debug output on every graph operation.

### Noise models

In `(x, y, z, roll, pitch, yaw)` order, converted internally to GTSAM's rotation-first
tangent convention.

| Parameter | Value | Note |
| --- | --- | --- |
| `prior_noise_std` | 0.001 | Tight — the backbone's origin is definitional |
| `dyn_noise_std` | 0.005, 0.005, 1.0, 1.0, 1.0, 0.001 | **x, y, yaw tight; z, roll, pitch loose** |
| `lidar_noise_std` | 0.05, 0.05, 0.05, 0.02, 0.02, 0.02 | |
| `lidar_drift_prior_std` | 0.01 ×3, 0.005 ×3 | |
| `lidar_drift_process_noise_std` | 0.01 ×3, 0.005 ×3 | Scaled by √dt at use |
| `residual_prop_noise_std` | 0.01, 0.01, 1.0, 1.0, 1.0, 0.01 | Lidar residual → primary link |
| `gps_prop_noise_std` | 0.5 ×6 | GPS residual → primary link, much looser |
| `nhc_noise_std` | 0.001, 0.001 | Lateral and vertical body velocity |
| `rate_prior_std` | 1.0, 1.0 | |
| `rate_process_noise_std` | 0.5, 0.5 | Scaled by √dt |
| `rate_tie_noise_std` | 0.01, 0.01 | |

**The dynamics noise shape is good design.** x, y, and yaw are what a bicycle model can
predict, so they are tight; z, roll, and pitch are what it cannot, so they are loose
enough to let the IMU and lidar own them. That makes the unconnected control input worse
rather than better — see below.

### Latent chains

| Parameter | Value |
| --- | --- |
| `odom_offset_prior_std` | 50.0, 50.0, π — very loose, position initially unknown |
| `odom_offset_process_noise_std` | 1e-4 ×3 — near-constant |
| `gravity_align_prior_std` | 0.5, 0.5 |
| `gravity_align_process_noise_std` | 1e-4 ×2 |
| `gravity_align_stationary_vel_thresh` | 0.05 m/s |
| `gravity_align_stationary_rate_thresh` | 0.02 rad/s |
| `gravity_align_min_update_interval` | 2.0 s |

### GPS

| Parameter | Value |
| --- | --- |
| `gps_sigma_at_best_quality` | 1.5 m |
| `gps_sigma_at_worst_quality` | 15.0 m |

**Both are flagged in the config itself as an unvalidated placeholder.** See
[Known issues](#the-gps-noise-model-is-an-admitted-placeholder).

### IMUs

Identical values for both, which is unlikely to be right for two different devices:

| | Ouster | Insta360 |
| --- | --- | --- |
| Gyro noise | 0.01 | 0.01 |
| Accel noise | 0.05 | 0.05 |
| Integration noise | 1e-4 | 1e-4 |
| Gyro bias walk | 0.0005 | 0.0005 |
| Accel bias walk | 0.001 | 0.001 |

> TODO(verify): the Ouster's IMU is a Bosch BMI085; the Insta360's is unidentified. Their
> noise characteristics will differ, and identical parameters mean one of them is weighted
> wrongly. Both datasheets would give real figures, or an Allan variance analysis on logged
> stationary data.

## Dependencies

**Ibex packages**

- `shared_link_bridge` — for the `GpsValues` message type. **This pulls in the entire
  Kairos driver**, teleop GUI included, because the message is defined inside the driver
  package rather than in a separate interfaces package. See
  [shared-link-bridge.md](../../motion/software/shared-link-bridge.md#message-definitions)
- `ibex_bringup` — publishes the static transforms this node blocks on at startup

**ROS**

- `rclpy`, `std_msgs`, `tf2_ros`

**Python**

- `utm` — declared in `setup.py`'s `install_requires` but **not** in `package.xml`, so
  `rosdep install` will not fetch it
- `gtsam` and `gtsam_unstable` — **declared nowhere at all**
- `numpy` — **declared nowhere at all**

> TODO(verify): add `gtsam`, `gtsam_unstable`, `numpy`, and `utm` to `package.xml` so a
> fresh clone's `rosdep install` produces a working build rather than an import error at
> first launch. Three of the four are currently invisible to the dependency system.

> TODO(verify): **pin the GTSAM version.** `IncrementalFixedLagSmoother` lives in
> `gtsam_unstable`, where API stability is explicitly not guaranteed across releases. This
> package's central mechanism is therefore sitting on an unpinned unstable API.

## Known issues & fixes

### The control input is not connected

In `graph_frontender.py`:

```python
self.last_v = 0.0 # TODO: need to hook these up to steering
self.last_delta = 0.0
```

Both are set once and **never updated**. Every primary tick calls
`add_primary(t, 0.0, 0.0)`.

**The bicycle dynamics factor therefore asserts, at 6 Hz, that the vehicle has not moved —
with a 5 mm standard deviation in x and 0.001 rad in yaw.**

| Actual speed | True displacement per tick | Standard deviations from the assertion |
| --- | --- | --- |
| 0.1 m/s | 0.017 m | 3σ |
| 1.0 m/s | 0.167 m | 33σ |
| 5.0 m/s | 0.835 m | **167σ** |
| 10.0 m/s | 1.670 m | **334σ** |

And the dynamics factor is **ten times tighter than the lidar factor** — 0.005 m against
0.05 m in x — so when they disagree, the zero-motion assertion wins.

**This is the feature the architecture is built around.** The rationale for choosing a
custom back end over a SLAM package rests on having a control-driven backbone; without
`(v, δ)` that backbone is a tight stationary prior fighting every other sensor.

> TODO(verify): **connect it.** The source is already on the vehicle:
> `shared_link_bridge` publishes `/kairos_values`, which carries the vehicle state the P4S4
> reports — speed and steering angle among it. This node already depends on that package.
> See
> [shared-link-bridge.md](../../motion/software/shared-link-bridge.md).
>
> Until then, consider either loosening `dyn_noise_std` in x, y, and yaw to something that
> does not assert stationarity, or setting `enable_rate`/the dynamics factor aside so the
> lidar and IMU carry the estimate unopposed. Running as-is with tight noise and zero input
> is the one configuration that is clearly wrong.

### The wheelbase is a placeholder

```yaml
wheelbase: 1.2          # TODO: set to IBEX's actual wheelbase (m)
```

The transform tree puts the rear axle **2.4638 m behind the front bumper** on a vehicle
roughly 3 m long, so 1.2 m is implausible — likely around half the true value.

It matters because the bicycle model's yaw rate is `(v / L)·tan(δ)`, so wheelbase scales
yaw rate inversely:

| Steering angle | At L = 1.2 m | At L = 2.0 m | At L = 2.46 m |
| --- | --- | --- | --- |
| 0.1 rad | 0.418 rad/s | 0.251 rad/s | 0.204 rad/s |
| 0.3 rad | 1.289 rad/s | 0.773 rad/s | 0.629 rad/s |

**Currently harmless, because `v = 0` makes the whole term zero.** It becomes a significant
error the moment the control input is connected, so the two should be fixed together.

> TODO(verify): measure the wheelbase — front axle centre to rear axle centre — and record
> it in [specifications.md](../../../03-base-vehicle/specifications.md) as well as here.

### The GPS noise model is an admitted placeholder

Flagged in the config and again in `_gps_position_noise`'s docstring. Position sigma is
linearly interpolated between 1.5 m at quality 100 and 15 m at quality 0.

**Estimator consistency depends on covariances being approximately right.** A wrong GPS
sigma either lets GPS drag the trajectory around or makes it ignorable.

The 1.5–15 m range implies a basic GNSS receiver rather than RTK, which also answers an
open question on the [subsystem README](../README.md) — but it is an assumption in code,
not a specification.

> TODO(verify): obtain the receiver's accuracy specification from Kairos, or calibrate from
> logged stationary scatter. The latter needs only a long parked recording of
> `/gps_values`.

`_is_valid_gps_fix` carries the same caveat — it rejects quality ≤ 0, satellite count ≤ 0,
and exactly (0, 0), and its docstring notes it needs the receiver's real no-fix sentinel
convention.

### The non-holonomic constraint forbids vertical motion

`make_nhc_factor` constrains body-frame **lateral and vertical** velocity to zero, both
with a 0.001 m/s sigma.

Lateral is sound — a car-like vehicle does not slip sideways meaningfully. **Vertical is a
much stronger claim**: it says the vehicle body never moves up or down relative to its own
frame, at 1 mm/s. On the mud, marsh, and side slopes at
[Olin](../../../02-operations/field-sites.md), suspension travel of 8.7 in front and 9.3 in
rear says otherwise.

> TODO(verify): consider loosening the vertical term substantially, or dropping it. The
> factor's own docstring describes it as "no independent bounce", which is an assumption
> about a vehicle with KYB piggyback shocks and nearly a foot of travel.

### Marginalization fragility

**Already encountered, and the cause of a segfault.** A prior-only node that no other
factor ever touches crashes inside `ISAM2::marginalizeLeaves`.

**Fix, installed:** every latent chain's root node is created lazily, on first real use
rather than at construction. The lidar drift chain is created on the first lidar reading,
`odom_offset` on the first valid GPS fix, `gravity_align` on whichever of its two triggers
fires first.

> The class of bug is inherent to hand-managed graph structure. Any new chain needs the
> same lazy-initialization treatment.

### Rank deficiency on partially-constrained nodes

The ternary GPS factor constrains only the residual node's **translation**. Its rotation is
unconstrained until `add_primary` later adds the propagation factor — and ISAM2 correctly
rejects the system as indeterminate the moment `_push()` tries to solve it.

**Fix, installed:** a weak prior on the GPS residual node with enormous translation sigmas
(1e3, since the real factor owns that information) and loose-but-finite rotation sigmas
(1.0), just enough to keep the linear system full rank.

> Any new partial-observation factor will need the same treatment. The code carries a TODO
> to replace the weak prior properly once heading and velocity are available from the GPS.

### Chains age out of the lag window and re-bootstrap

Both `gravity_align` and `odom_offset` grow only on sporadic events, so **ordinary
operation can marginalize them out before anything renews them**:

| Chain | Grows on | Ages out during |
| --- | --- | --- |
| `gravity_align` | Stationary ticks, rate-limited to 2 s | Any drive longer than 5 s |
| `odom_offset` | Real GPS fixes | Any GPS outage longer than 5 s — a tunnel, dense foliage |

ISAM2 cannot re-insert a value for an already-marginalized key. Both detect this via
`Values.exists` and **re-bootstrap at a fresh index with a new loose prior** rather than
chaining onto a stale key or crashing.

Read paths guard too: `get_odom_offset()` returns `None` and `get_aligned_state()` falls
back to the uncorrected estimate when the tracked key has aged out.

> This is correct behaviour that looks like a bug. Re-bootstrapping `odom_offset` discards
> the accumulated offset estimate and starts again from a 50 m prior, so **absolute
> position accuracy degrades after every GPS outage longer than 5 seconds** until fixes
> re-converge.

### No outlier rejection

GTSAM offers robust noise models — Huber, Cauchy, Tukey among them — and none are used.
Gating and data association are entirely the caller's responsibility, and currently only
`_is_valid_gps_fix`'s crude checks exist.

> TODO(verify): a single bad GPS fix that passes the validity check enters the graph with
> full weight. Wrapping the GPS factor's noise model in `noiseModel::Robust` is a
> one-line change and the obvious first mitigation.

### Python and numerical Jacobians

All six custom factors compute Jacobians by central differences in Python, at 6 Hz, through
`CustomFactor`. Acceptable at current rates.

> If the graph or the rate grows, the fixed-lag update loop is the first thing to profile.
> Analytic Jacobians, or moving the hot factors to C++, are the escalation path.

### Smaller notes

**`make_rate_tie_factor` uses raw angle subtraction**, which would need proper wrapping
near ±90° pitch. Documented in the factor, and acceptable for a ground vehicle.

**`get_latlon()` exists and nothing calls it.** It composes the aligned pose with
`odom_offset` and inverts the UTM projection — a ready-made lat/lon output that is not
published.

**stdout is explicitly line-buffered** in `main()`, because `ros2 launch` pipes a
non-TTY and Python block-buffers it, which reorders debug output misleadingly.

## Understanding the software

### The UTM zone is locked to the first fix

`_latlon_to_utm` records the zone from the first GPS fix and **forces every later fix into
that same zone.**

Without that, a vehicle near a UTM zone boundary would see its natural zone flip as it
crossed, and easting/northing would jump by hundreds of kilometres instantly —
catastrophic for `odom_offset`'s continuity. The cost is a little extra projection
distortion near a zone edge, bounded well under GPS's own noise floor at ground-vehicle
ranges.

### Why gravity_align is rate-limited separately from its stationarity gate

A parked vehicle satisfies the stationarity check on **every** primary tick, indefinitely.
Without the 2-second rate limit the chain would grow at 6 Hz for the entire time the
vehicle sits still.

Chaining many near-zero-noise between-factors that fast and then continuously
marginalizing them is a known way to ill-condition ISAM2's incremental solve. Since
gravity_align is a true physical constant, occasional check-ins are exactly as informative
as constant ones.

Note also that its chain-link noise is a **fixed near-zero value, not √dt scaled**, for the
same reason: it is a marginalization device for a constant, not a model of a random walk.

### What this architecture buys going forward

New sensors are **additive rather than structural**. Adding a modality means writing a
factor and a callback; the backbone, the smoother, and the existing latents are untouched.

**The hyperspectral terrain work is the concrete case.** A spectral observation matched
against a georeferenced prior map is structurally the same shape as
`make_gps_odom_offset_factor` — a measurement routed through `gravity_align` and
`odom_offset` to become comparable to the backbone. It would slot in as `add_hyperspectral`
following the existing residual-node pattern, with a new `kind` tag selecting its
propagation noise.

It would also close a real gap. `odom_offset`'s yaw is seeded at zero and is effectively
**unobservable from single GPS fixes with no heading** — single-antenna GNSS structurally
cannot provide it. A spectral *patch* match constrains orientation as well as position, and
would supply the absolute heading anchor nothing else on the vehicle can.

> That connects this subsystem directly to [Perception](../../perception/README.md), and is
> the strongest argument for resolving the hyperspectral calibration gaps recorded there.

## Related pages

- [State estimation overview](../README.md) — the pipeline, the clock problem, the unused
  inputs
- [kiss-icp.md](kiss-icp.md) — the odometry front end this consumes
- [shared-link-bridge.md](../../motion/software/shared-link-bridge.md) — the GPS source,
  and where `(v, δ)` would come from
- [ouster-os1-64.md](../../perception/hardware/ouster-os1-64.md) — the primary IMU
- [insta360-x4.md](../../perception/hardware/insta360-x4.md) — the second IMU
- [tf-frames.md](../../../05-reference/tf-frames.md) — needs `aligned_odom`, `utm`, and
  `insta_imu`
- [ros-graph.md](../../../05-reference/ros-graph.md) — topics and rates
- [glossary.md](../../../00-onboarding/glossary.md) — factor graph, preintegration,
  `map` versus `odom`
- <https://gtsam.org> — GTSAM documentation
