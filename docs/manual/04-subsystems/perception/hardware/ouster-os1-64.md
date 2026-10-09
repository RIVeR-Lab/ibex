---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Ouster OS1-64

The primary 3D lidar. Serves [Perception](../README.md) and
[State estimation](../../state-estimation/).

## Overview

A 64-channel rotating lidar producing dense 3D point clouds, with an IMU built in. It does
four jobs on IBEX:

**Depth and range sensing.** Point clouds for obstacle detection, terrain geometry, and
the geometric half of the traversability pipeline.

**Localization front end.** The point cloud feeds KISS-ICP lidar odometry, which produces
relative-pose factors for the factor graph in
[`ibex_state`](../../state-estimation/software/ibex-state.md).

**Inertial measurement.** The onboard BMI085 IMU supports motion estimation and IMU
preintegration in the fusion stack, which matters given the yaw observability gaps
consumer-grade IMUs have at standstill.

**Frame anchoring.** The sensor frame is a key node in the static transform tree, tying
lidar, camera, hyperspectral, and GPS data into one reference frame — see
[tf-frames.md](../../../05-reference/tf-frames.md).

### Why this sensor

IBEX originally carried a Velodyne VLP-16. The OS1-64 replaced it:

| | VLP-16 | OS1-64 |
| --- | --- | --- |
| Channels | 16 | 64 |
| Points per second | ~300,000 | 8–10× denser |
| Vertical resolution | 2° | 64 channels over 42.4° |

The deciding argument was range overlap with the hyperspectral instruments. Combining
hyperspectral imaging with lidar works best at medium distances, roughly 10–100 m, and the
OS1-64's useful density range is about 20–120 m — where the VLP-16's was shorter. Better
range means the lidar and the spectral data describe the same ground at useful distances.

Integration was low-risk: similar form factor to the VLP-16, existing ROS drivers, and a
similar data format.

> **The mounting angle partly undercuts that reasoning.** At 25° nose-down the sensor's
> ground intersection caps at roughly 25 m — see
> [mounting geometry](../README.md#ouster-mounting-geometry). So of the 20–120 m density
> range that justified the upgrade, only the near end is available for *ground* returns.
> Taller objects remain visible further out. Worth resolving whether the tilt is the right
> trade, or documenting deliberately that IBEX uses the OS1-64 for near-field terrain
> rather than for its range.

## Physical location on vehicle

Roof-mounted, on the sensor rack, secured by four screws.

Mounted **25° nose-down** rather than level, so it scans terrain ahead rather than the
horizon. The tilt comes from the `sensor_rack` → `os_mount` static transform — values in
[tf-frames.md](../../../05-reference/tf-frames.md), coverage consequences in
[the subsystem README](../README.md#ouster-mounting-geometry).

> TODO(verify): record the screw size and torque, and whether the mount is shimmed to set
> the tilt or whether the bracket fixes it. This determines whether the angle can drift.

## Power source / rail

Fed by the **Compute and Sensing box**, via the Ouster interface box.

The interface box sits inside the Compute and Sensing box and **lights a green LED when
powered** — that is the power-on confirmation for this sensor. See
[power-on.md](../../../02-operations/power-on.md) step 7.

| | |
| --- | --- |
| Voltage | 24 V |
| Current | 0.667 A |
| Power | 16 W nominal |
| Startup | 28 W, if operating at −40 °C |

## Hardware specs

| | |
| --- | --- |
| Manufacturer | Ouster |
| Product line | OS-1-64-U13 |
| Part number | OS1-071-64U-AX |
| Serial number | 122540007570 |
| Firmware | `ousteros-image-prod-bootes-v3.1.0+20240426041747` |
| Firmware build | v3.1.0, built 2024-04-26 |
| Vertical field of view | 42.36° — from +21.03° to −21.33° |
| Horizontal field of view | 360° (azimuth window 0–360000 mdeg) |
| Vertical resolution | 64 channels |
| Lidar mode | `1024x10` — 1024 columns at 10 Hz |
| Range | 170 m |
| Minimum range | 0.5 m (`min_range_threshold_cm: 50`) |
| Range resolution | 0.1 cm |
| Return order | Strongest to weakest |
| Integrated IMU | Bosch BMI085 |
| Reflectivity calibration | Valid, 2025-10-09 |

The serial number is also the hostname — see [Networking](#networking).

**On the vertical field of view.** The 42.36° span is read from this unit's
`beam_altitude_angles`, and it is **not symmetric** — the extremes are +21.03° and
−21.33°. Ouster's datasheet gives a nominal 45° for the OS1 line. Use the metadata
figures for geometry; they describe this sensor.

The 64 beams are also **not evenly spaced**. The first gap is 0.57° where uniform spacing
across 42.36° would be 0.67°. Anything fitting a ground plane or computing a precise
footprint needs the full angle list, not an assumed distribution.

**The beams are azimuthally interleaved.** `beam_azimuth_angles` alternates between about
+4.2° and −1.4°, and `pixel_shift_by_row` alternates 12 and −4. The point cloud is
therefore not a clean 64 × 1024 grid — adjacent rows are offset in azimuth. Treating the
data as a rectangular image without accounting for that will shear features.

> TODO(verify): record the date the firmware was last checked. The version string carries a
> 2024-04-26 build date, which says when it was built, not when it was installed or last
> confirmed.

> TODO(verify): the horizontal resolution and rotation rate are configurable and interact —
> confirm which combination is actually loaded, since the tilt geometry and the
> `min_scan_valid_columns_ratio` setting both depend on the beam configuration. The web
> dashboard reports it.

## Sensor configuration

These live on the sensor, not in the driver. Read them with:

```bash
ros2 topic echo /ouster/metadata --once --full-length
curl -s http://os-122540007570.local/api/v1/sensor/metadata | python3 -m json.tool
```

| Setting | Value | Notes |
| --- | --- | --- |
| `lidar_mode` | `1024x10` | 1024 columns, 10 Hz |
| `azimuth_window` | `0–360000` mdeg | Full 360°, no bandwidth reduction applied |
| `udp_profile_lidar` | `RNG19_RFL8_SIG16_NIR16` | Range, reflectivity, signal, **and near-infrared** |
| `udp_profile_imu` | `LEGACY` | |
| `udp_dest` | `169.254.223.140` | Volta's `enp46s0`. **A literal address** — see [Known issues](#the-sensors-udp-destination-is-a-hardcoded-address) |
| `udp_port_lidar` | `58293` | **Not** the 7502 default |
| `udp_port_imu` | `59631` | **Not** the 7503 default |
| `timestamp_mode` (sensor) | `TIME_FROM_INTERNAL_OSC` | The sensor's internal setting |
| `timestamp_mode` (driver) | **`TIME_FROM_ROS_TIME`** | What the driver config requests — ROS messages are stamped on Volta's clock |
| `columns_per_packet` | 16 | |
| `operating_mode` | `NORMAL` | |
| `phase_lock_enable` | `false` | |
| `multipurpose_io_mode` | `OFF` | The sync pulse and NMEA inputs are unused |
| `signal_multiplier` | 1 | |

> TODO(verify): save the full metadata JSON into `docs/hardware/Ouster/` and commit it. It
> is a few kilobytes and it is the authoritative record of this unit's beam geometry,
> intrinsics, and configuration. Committing it makes the beam angles greppable in the repo
> instead of only retrievable from a powered sensor.

### Near-infrared is already on the wire

The active profile is `RNG19_RFL8_SIG16_NIR16`, so the sensor is already transmitting
range, reflectivity, signal, and **16-bit near-infrared** for every return.

The NIR channel is ambient 865 nm light collected by the same detector array between laser
firings — effectively a passive NIR image, perfectly registered to the point cloud because
it comes from the same photodiodes at the same instant.

That registration is the interesting part: 865 nm falls inside the band the Ximea VNIR
camera covers, so this is an ambient NIR measurement already aligned to geometry, with no
extrinsic calibration to solve. It is a plausible bridge for registering hyperspectral
imagery to the point cloud.

Caveats: single broad band rather than a spectrum, radiometrically uncalibrated,
ambient-light dependent (bright in daylight, near-black at night — the opposite of the
signal channel), and only 64 rows.

**Enabling the driver's NIR image topic costs no additional bandwidth**, because the data
is already arriving and being discarded. See
[ouster-ros.md](../software/ouster-ros.md).

## Additional components

**Ouster interface box.** Sits inside the Compute and Sensing box, takes power and provides
the sensor's ethernet connection. Green LED when powered.

> TODO(verify): record its model or part number, and whether it is the standard Ouster
> interface box or something else.

## Software

| Software | Role |
| --- | --- |
| [ouster-ros.md](../software/ouster-ros.md) | The driver. Forked submodule |
| [kiss-icp.md](../../state-estimation/software/kiss-icp.md) | Consumes the point cloud for odometry |
| [ibex-state.md](../../state-estimation/software/ibex-state.md) | Consumes the odometry and the IMU |

### Data structure / output format

Point cloud and IMU data. Topic names, types, and rates are in
[ros-graph.md](../../../05-reference/ros-graph.md).

## Networking

### Physical interface

The Ouster connects to **Volta's onboard ethernet port** (`enp46s0`), **not** the USB
adapter. The USB adapter carries the router uplink.

That choice is deliberate: the onboard port outperforms the USB adapter for the OS1's
packet volume. **Do not swap them.** If cables move, re-verify with:

```bash
ip -br addr
```

The interface on the `169.254.x.x` subnet is the sensor link; the one on
`192.168.200.x` is the uplink.

### Addressing

Both ends sit on link-local (APIPA) addresses in `169.254.0.0/16`. The sensor is not
statically configured and did not take a DHCP lease — both ends fell back to
auto-assignment. They are correctly on the same subnet, but the pairing is fragile:
link-local addresses can shift between sessions.

**Address the sensor by hostname, not by IP:**

```
os-122540007570.local
```

The hostname is derived from the serial number and is stable across reboots. The IP is
not. Anything referencing the hostname keeps working if the address shifts.

The address table lives in [network.md](../../../05-reference/network.md).

> TODO(verify): for reproducible bag capture, consider assigning a static address on
> `enp46s0` and pinning the sensor to a matching static subnet. Currently unresolved; the
> mDNS hostname mitigates most of the fragility.

### Web dashboard

Browsing to the sensor from Volta opens Ouster's configuration UI:

```
http://os-122540007570.local/
```

It exposes beam and lidar mode, rotation rate, azimuth window, live diagnostics, and
firmware version. **This is the fastest way to check or change sensor configuration**, and
it is not obvious that it exists.

The same values are available over HTTP:

```bash
curl http://os-122540007570.local/api/v1/sensor/config | python3 -m json.tool
```

## Setup & calibration

### Physical installation

Four screws to the roof rack. See
[Physical location](#physical-location-on-vehicle).

### Calibration

No intrinsic calibration. What the sensor needs is an accurate extrinsic — the static
transform accounting for its mounting tilt.

Values live in [tf-frames.md](../../../05-reference/tf-frames.md). The reasoning about what
the tilt buys and costs is in [the subsystem README](../README.md#ouster-mounting-geometry).

> TODO(verify): the 25° is the design tilt recorded in the transform tree. Confirm the
> installed tilt with an inclinometer, or by fitting the ground plane in a static point
> cloud on level ground. Every coverage number depends on it.

Driver installation and launch commands are not here — see
[ouster-ros.md](../software/ouster-ros.md) and
[running-the-system.md](../../../02-operations/running-the-system.md).

## Known issues & fixes

### The sensor's UDP destination is a hardcoded address

`udp_dest` is set to `169.254.223.140` — Volta's current link-local address on `enp46s0`.

**Consequence:** the sensor sends data to that literal address. If Volta's link-local
address changes, the sensor keeps transmitting to the old one and **data simply stops
arriving**, even though the sensor is still reachable by hostname and responds to the
dashboard. Everything looks healthy and nothing publishes.

This is the reverse of the fragility the original notes worried about. Addressing the
sensor by hostname protects the command path; it does nothing for the data path, which
depends on Volta's address staying put.

> TODO(verify): decide how to make this robust. Options: assign a static address on
> `enp46s0` and leave `udp_dest` matching it, or have the driver set `udp_dest` at startup
> from the interface's current address. The second is what the upstream driver's
> `udp_dest` parameter is for — check whether the IBEX config sets it.

### Lidar timestamps come from the sensor's own clock

The sensor timestamps internally on its own oscillator, but **the driver is configured
with `timestamp_mode: TIME_FROM_ROS_TIME`**, so the ROS messages it publishes are stamped
with the reception time of each scan's first packet, on Volta's system clock.

**The ROS stamps are what consumers see**, so lidar and IMU data arrive on the same clock
as everything else. What is lost is intra-scan timing and a variable network-plus-driver
latency between capture and stamp, rather than a free-running clock offset.

**Consequence:** the sensor's clock drifts relative to everything else on the vehicle.
That matters for the factor graph in
[`ibex_state`](../../state-estimation/software/ibex-state.md), which fuses lidar odometry,
the Ouster IMU, and GPS arriving through a completely separate path — the P4S4 over
SharedLink. Nothing is currently synchronising those clocks.

Alternatives the sensor supports: `TIME_FROM_PTP_1588`, or `TIME_FROM_SYNC_PULSE_IN`
driven from a GPS pulse. `multipurpose_io_mode` is currently `OFF`, so the sync pulse
input is unused.

> TODO(verify): establish whether clock drift is affecting state estimation, and whether
> PTP or a GPS sync pulse is worth setting up. This is a state estimation question more
> than a perception one — raise it with that subsystem's owner.

### Non-default UDP ports

Lidar data is on port `58293` and IMU on `59631`, not the 7502 and 7503 defaults.

Worth knowing before packet-capturing: `tcpdump ... udp port 7502` will show nothing on
this system.

### MTU is 1500, and jumbo frames are a host-side decision only

**The sensor has no MTU setting.** Its configurable parameters are the returns profile,
lidar mode, azimuth window, UDP destination host and ports, and timing source — bandwidth
is managed by reducing returns or narrowing the azimuth window, not by changing packet
size.

The sensor emits large UDP datagrams and lets IP fragmentation handle the rest. At
1024 × 10 Hz a lidar datagram is roughly 12.5 kB, so `tcpdump` on port 58293 reports
something like `UDP, bad length 12544 > 1472`. **That message is normal for Ouster**, not
a fault.

Volta's interface is currently at the standard 1500:

```bash
ip link show enp46s0      # mtu 1500, confirmed
```

Raising it to 9000 cuts a 12.5 kB datagram from roughly nine fragments to two. That is a
reduction in fragmentation overhead, not elimination.

To test:

```bash
sudo ip link set enp46s0 mtu 9000
```

**That does not survive a reboot.** To persist, set it in whichever tool manages the
interface — check with `nmcli device status` first:

```bash
# NetworkManager
sudo nmcli connection modify "<connection-name>" 802-3-ethernet.mtu 9000
sudo nmcli connection up "<connection-name>"
```

Or add `mtu: 9000` under the interface in `/etc/netplan/*.yaml` and run
`sudo netplan apply`. Setting it in the tool that does *not* manage the interface silently
does nothing.

Because the Ouster is direct-attached to Volta with no switch in the path, nothing else
needs to agree with the change.

> TODO(verify): confirm there is a symptom before changing anything. If
> `ros2 topic hz /ouster/points` holds a steady 10 Hz and bags have no gaps, 1500 is
> working and this is optimization without a problem. Record the outcome either way, so
> the next person does not re-investigate.

### Link-local addressing is not reproducible

Covered under [Addressing](#addressing). Mitigated by using the hostname.

### Driver issues

The `.xml` launch file writes a metadata file into the working directory; use the Python
launch file instead. That is a driver behaviour, not a sensor one — see
[ouster-ros.md](../software/ouster-ros.md).

## Datasheets

- [Ouster OS1 datasheet, rev 7 v3p1](https://data.ouster.io/downloads/datasheets/datasheet-rev7-v3p1-os1.pdf)
- [Product page](https://ouster.com/products/hardware/os1-lidar-sensor)

> TODO(verify): save a copy of the datasheet into `docs/hardware/` rather than relying on
> the vendor URL, which can move.

## Reorder

> TODO(verify): nothing recorded. Needed: Ouster's ordering contact, lead time, and whether
> the interface box is separately orderable. Record in
> [reorder.md](../../../99-appendix/reorder.md).

The displaced Velodyne VLP-16 may still be in the lab and is worth recording as a fallback,
with the caveat that the transform tree, driver configuration, and anything tuned against
64 channels would need revisiting.

> TODO(verify): does the lab still have the VLP-16, and where is it?

## Related pages

- [Perception overview](../README.md) — the sensor set and the mounting geometry analysis
- [ouster-ros.md](../software/ouster-ros.md) — the driver
- [state-estimation/](../../state-estimation/) — what consumes this sensor's output
- [tf-frames.md](../../../05-reference/tf-frames.md) — the extrinsic and the frame chain
- [network.md](../../../05-reference/network.md) — addressing
- [power-on.md](../../../02-operations/power-on.md) — the green LED confirmation, step 7
- [glossary.md](../../../00-onboarding/glossary.md) — ICP, IMU preintegration, link-local
