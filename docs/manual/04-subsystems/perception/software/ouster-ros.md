---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# ouster-ros

The Ouster OS1-64 driver. Serves [Perception](../README.md).

## Source

| | |
| --- | --- |
| Upstream | <https://github.com/ouster-lidar/ouster-ros> — `ros2` branch |
| Our fork | <https://github.com/RIVeR-Lab/ouster-ros> |
| In this repo | `packages/ouster-ros` — git submodule |

## Fork status

A fork of the vendor's official driver, vendored as a submodule.

> TODO(verify): **what is actually changed in the fork?** The sensor configuration lives
> outside the submodule, in `packages/ibex_bringup/config/ibex_ouster_sensor_config.yaml`,
> which is the correct place for it. If that is the only IBEX-specific content, the fork
> may carry no changes at all — in which case the submodule could track upstream directly
> the way `kiss-icp` does, and lose a maintenance burden.
>
> Check with a diff against the upstream `ros2` branch. If there are changes, record what
> they are and whether they are upstreamable.

## Description

The official ROS 2 driver for Ouster lidars. It connects to the sensor, decodes lidar and
IMU frames off the wire, and publishes them as ROS 2 messages.

## Capabilities

- Point cloud output from the OS1-64
- IMU output from the sensor's built-in BMI085
- Decodes lidar frames and publishes the corresponding ROS messages
- Exposes sensor configuration through a parameter file

## Purpose

It is the vendor's own driver, which means the wire format, the metadata handling, and the
firmware compatibility are maintained by the people who make the sensor.

Its output is the input to everything IBEX does with lidar: the point cloud feeds
[`kiss-icp`](../../state-estimation/software/kiss-icp.md) for odometry, and both the cloud
and the IMU reach the factor graph in
[`ibex_state`](../../state-estimation/software/ibex-state.md).

## Alternative software

| Alternative | Why not |
| --- | --- |
| `ros2_ouster_drivers` | Community driver. The vendor's own is better maintained against firmware changes |
| Ouster SDK (Python / C++) | Not ROS-native. Would mean writing and maintaining the ROS integration ourselves |

The deciding factor was simply that `ouster-ros` is the official ROS 2 driver.

## Launch / invocation

Use the Python launch file with the IBEX configuration:

```bash
ros2 launch ouster_ros driver.launch.py \
  params_file:=$HOME/ibex_ws/src/ibex/packages/ibex_bringup/config/ibex_ouster_sensor_config.yaml \
  viz:=false
```

It takes a moment to come up.

**Do not use the XML launch file.** See
[Known issues](#the-xml-launch-file-writes-metadata-to-the-working-directory).

If the sensor cannot be found:

```bash
avahi-browse -lrt _roger._tcp
```

**Preconditions** — not steps, see
[power-on.md](../../../02-operations/power-on.md):

- Compute and Sensing box powered, so the sensor and its interface box are up
- Volta's `enp46s0` configured for link-local addressing
- The sensor reachable as `os-122540007570.local`

> TODO(verify): replace the `$HOME` path with a package-relative one — something like
> `$(ros2 pkg prefix ibex_bringup)/share/ibex_bringup/config/...` — once it is confirmed
> the config installs into the share directory. Hardcoded home directories break for every
> user but one.

Note that the configuration lives in `ibex_bringup`, not inside the `ouster-ros`
submodule. That is deliberate: integration config belongs in the parent repo, so it is not
lost when the submodule pin moves. See
[_templates/README.md](../../../_templates/README.md).

## Topics

Captured with the driver running. Node is `os_driver` in the `/ouster` namespace.

| Topic | Type | QoS | Notes |
| --- | --- | --- | --- |
| `/ouster/points` | `sensor_msgs/msg/PointCloud2` | Best effort, volatile | The point cloud. Consumed by `kiss-icp` |
| `/ouster/imu` | `sensor_msgs/msg/Imu` | Best effort, volatile | From the built-in BMI085 |
| `/ouster/metadata` | `std_msgs/msg/String` | Reliable, **transient local** | Sensor metadata, including beam altitude angles |
| `/ouster/telemetry` | `ouster_sensor_msgs/msg/Telemetry` | Best effort, volatile | Sensor health and diagnostics |
| `/ouster/os_driver/transition_event` | `lifecycle_msgs/msg/TransitionEvent` | Reliable, volatile | Lifecycle state changes. Subscribed by the launch process |
| `/tf_static` | `tf2_msgs/msg/TFMessage` | Reliable, transient local | **The driver publishes transforms** — see below |

### Best effort is not a mistake, but it has a consequence

`/ouster/points` and `/ouster/imu` are **best effort**, which is correct for high-rate
sensor data — drop a sample rather than delay the stream.

**A subscriber requesting Reliable QoS will not connect to a best-effort publisher.** DDS
treats that as incompatible, and the symptom is no data with no error message. If a node
sees nothing on `/ouster/points` while `ros2 topic hz` shows it flowing, check the
subscriber's QoS before anything else.

### The metadata topic is transient local

Late subscribers still receive the last published metadata, so this works at any time
while the driver is up:

```bash
ros2 topic echo /ouster/metadata --once
```

**This is where the per-channel beam altitude angles live.** Anything doing a ground-plane
fit or a precise footprint calculation needs those rather than the 42.4° span — see
[the subsystem README](../README.md#ouster-mounting-geometry).

### The driver publishes to /tf_static

`os_driver` publishes its own sensor-internal transforms — the relationships between
`os_sensor`, `os_lidar`, and the IMU frame — derived from sensor metadata.

So the transform tree has two sources: this driver for the sensor's internals, and
`ibex_bringup` for the vehicle-to-sensor-rack chain including the 25° mount tilt.
[tf-frames.md](../../../05-reference/tf-frames.md) needs to record both and say which
publishes what.

### Topics not present

No `/ouster/scan`, and no range, signal, or near-infrared image topics, though the driver
supports them upstream. The configuration file determines which topics are published.

**The near-infrared data is already arriving.** The sensor's active profile is
`RNG19_RFL8_SIG16_NIR16`, so range, reflectivity, signal, and 16-bit NIR are all on the
wire — the driver is receiving them and discarding three of the four. Enabling the NIR,
signal, and range image topics therefore costs no additional bandwidth.

> TODO(verify): enable the NIR image topic and see what it looks like. It is a passive
> 865 nm image perfectly co-registered to the point cloud, which makes it a candidate for
> registering hyperspectral imagery to geometry without solving an extrinsic. Caveats and
> the reasoning are on [ouster-os1-64.md](../hardware/ouster-os1-64.md).

## Services and actions

**`os_driver` is a lifecycle node.** It has to be configured and activated before it
publishes anything; the launch file handles that, which is why the launch process appears
as a subscriber to the transition event topic.

Practical consequence: a driver that appears in `ros2 node list` but publishes nothing may
simply be inactive rather than broken. Check its state:

```bash
ros2 lifecycle get /ouster/os_driver
```

> TODO(verify): record the driver's lifecycle services and whether any are used directly —
> deactivating and reactivating to reconfigure the sensor without a restart would be
> useful if it works.

## Non-ROS interfaces

The driver talks to the sensor directly over UDP on Volta's `enp46s0`, on the link-local
`169.254.0.0/16` subnet. Addressing is in
[network.md](../../../05-reference/network.md); the sensor side is documented on
[ouster-os1-64.md](../hardware/ouster-os1-64.md).

The sensor's own configuration is reachable independently of this driver, through its web
dashboard and HTTP API — see the hardware page.

## Parameters

Set through `ibex_ouster_sensor_config.yaml` in `ibex_bringup`.

| Parameter | Upstream default | Our value | Effect |
| --- | --- | --- | --- |
| `min_scan_valid_columns_ratio` | `0.0` | `0.1` | Minimum ratio of valid columns required before a LidarScan is processed |
| `viz` | — | `false` | Suppresses the driver's visualizer |

**`min_scan_valid_columns_ratio` must be non-zero.** At the upstream default of 0.0 the
driver passes through scans with no valid columns, and KISS-ICP errors on them. Any value
above zero avoids it; 0.1 was chosen. See
[kiss-icp.md](../../state-estimation/software/kiss-icp.md).

> TODO(verify): record the rest of the configuration file — sensor hostname, UDP
> destination, lidar mode, and timestamp mode are the ones that matter. The lidar mode in
> particular determines the beam configuration, which the footprint geometry in
> [the subsystem README](../README.md#ouster-mounting-geometry) depends on.

## Dependencies

**Ibex packages**

- `ibex_bringup` — holds the sensor configuration file

**External**

- Upstream `ouster-ros` build dependencies, per the upstream README
- `ouster_sensor_msgs` — supplies `Telemetry`. Ships inside the same repository, so the
  `packages/ouster-ros` submodule provides more than one ROS package

> TODO(verify): list every ROS package the submodule contains. The repo-level count of
> "ten packages" counts submodule directories, not ROS packages, so the real number
> colcon builds is higher.

**Hardware that must be powered**

- Ouster OS1-64 and its interface box, from the Compute and Sensing box

**Network configuration**

- Volta's `enp46s0` set to link-local. Without it the interface takes no IPv4 address and
  the sensor is unreachable — see [Known issues](#linux-assigns-no-ipv4-address-on-a-direct-ethernet-link)

## Known issues & fixes

### The XML launch file writes metadata to the working directory

**Symptom:** a sensor metadata file appears in whatever directory you launched from.

**Cause:** `sensor.launch.xml` writes it to the current working directory.

**Fix:** use `driver.launch.py` instead. **Installed** — the Python launch file is the
documented path.

### The vendor manual's hostname was wrong

**Symptom:** the sensor could not be reached at the hostname given in Ouster's user
manual.

**Fix:** discover it on the network instead.

```bash
avahi-browse -lrt _roger._tcp
```

The sensor's real hostname is derived from its serial number —
`os-122540007570.local`. **Resolved.**

> This command came from another lab's sensor setup wiki rather than Ouster's
> documentation: <https://github.com/neufieldrobotics/NeuROAM/wiki/Sensor_setup>

### Linux assigns no IPv4 address on a direct ethernet link

**Symptom:** the sensor is connected by ethernet and completely unreachable — no ping, no
hostname resolution.

**Cause:** with the lidar cabled directly to Volta rather than through a DHCP server,
Linux leaves the interface without an IPv4 address, so there is no path between the two.

**Fix:** set that interface's IPv4 method to **Link-Local Only**, which auto-assigns an
address in `169.254.0.0/16`. Both ends then sit on the same subnet. **Installed and
persistent** — it survives reboots and needs no re-application.

### KISS-ICP errors on scans with no valid columns

Covered under [Parameters](#parameters). Fixed by setting
`min_scan_valid_columns_ratio` to 0.1. **Installed.**

## Understanding the software

**The sensor is configured in two places, and they are not the same.** This driver's
parameter file sets what the driver does with the data. The sensor's own settings — beam
mode, rotation rate, azimuth window — live on the sensor and are set through its web
dashboard or HTTP API. Changing the driver's config does not change the sensor, and vice
versa.

**Mounting tilt is not this driver's concern.** The 25° nose-down mount is handled by a
static transform published elsewhere, not by the driver. Points arrive in the sensor's
tilted frame and have to be transformed before any height reasoning — see
[tf-frames.md](../../../05-reference/tf-frames.md) for the transform and
[the subsystem README](../README.md#ouster-mounting-geometry) for what the tilt means for
coverage.

## Related pages

- [ouster-os1-64.md](../hardware/ouster-os1-64.md) — the sensor
- [Perception overview](../README.md) — mounting geometry and coverage
- [kiss-icp.md](../../state-estimation/software/kiss-icp.md) — the main consumer
- [ibex-state.md](../../state-estimation/software/ibex-state.md) — the factor graph
- [tf-frames.md](../../../05-reference/tf-frames.md) — the transform chain
- [network.md](../../../05-reference/network.md) — link-local addressing
- [running-the-system.md](../../../02-operations/running-the-system.md) — launching it
- [launch-files.md](../../../05-reference/launch-files.md) — `ibex_bringup` launch files
