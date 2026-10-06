---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# SICK picoScan 150

A 2D lidar on a motor-driven base, sweeping to produce 3D point clouds. Serves
[Perception](../README.md).

> **Not currently in use.** It is powered at every startup and checked in
> [power-on.md](../../../02-operations/power-on.md), but no driver runs against it. A
> driver is planned. This page is deliberately thin and records what is known plus what
> the page will need when the driver lands.

## Overview

The picoScan 150 is a 2D scanning lidar — it sweeps a single plane. On IBEX it is mounted
on a **motor-controlled base** that rotates the whole sensor, so successive 2D scans at
different base angles compose into a 3D point cloud.

That makes it the second source of 3D geometry alongside the
[Ouster OS1-64](ouster-os1-64.md), and architecturally the opposite approach: the Ouster
has 64 fixed beams and spins internally at a fixed 10 Hz, while this produces its third
dimension mechanically and at whatever rate the base is driven.

### The motorized base changes what this sensor is

It is worth being explicit about, because none of it applies to any other sensor on the
vehicle:

**There is a moving mechanism on the roof.** The only one on IBEX besides the Ouster's
internal rotor and the P4S4's actuators. It needs power, control, and somewhere to fail.

**Each 2D scan is only meaningful with a base angle attached.** Composing a 3D cloud
requires knowing where the base was pointing at the instant of each scan. That needs
position feedback — an encoder or a commanded-position readback — and a timestamp
association between the two.

**It needs a dynamic transform**, not a static one. Every other sensor frame on IBEX is
fixed relative to the vehicle and published once to `/tf_static`. This one moves, so its
frame has to be published continuously to `/tf` as the base turns.
[tf-frames.md](../../../05-reference/tf-frames.md) will need to account for that, and it
is the only such case in the perception subsystem.

**Motion blur is a real constraint.** A sweeping sensor on a moving vehicle integrates
vehicle motion into the cloud, so sweep rate, vehicle speed, and point density trade
against each other in a way the Ouster's does not.

> TODO(verify): all of the above assumes a conventional sweep. Record what the base
> actually is — commercial pan unit, custom build, servo or stepper — its sweep range and
> rate, whether it sweeps continuously or steps, and how its position is read back. Until
> that is known, none of the 3D composition can be designed.

## Status

| | |
| --- | --- |
| Powered | Yes, at [power-on.md](../../../02-operations/power-on.md) step 3 |
| Driver | **None.** Planned |
| Motor control | TODO(verify) — unrecorded |
| Producing data | No |

Because it is checked during power-on without a driver to use it, a failed check is not
currently a blocker for a session. That changes when the driver lands.

## Physical location on vehicle

Recorded as the **top right of IBEX**.

> TODO(verify): reconcile this against the hyperspectral array layout, where the Alvium
> RGB camera occupies the far right — see
> [alvium-rgb-camera.md](alvium-rgb-camera.md). Either "top right of IBEX" means a
> different part of the roof from "far right of the array", or the two descriptions
> conflict. Record the position relative to the sensor rack and to the other sensors.

> TODO(verify): record the base's mounting and its swept volume. A rotating sensor needs
> clearance, and whether it can see the vehicle's own structure — the hyperspectral array,
> the Insta360 mast, the roll cage — determines how much of each sweep is self-occluded
> and should be masked.

## Power source / rail

Fed by the **Kairos box**, not the Compute and Sensing box. It comes up at step 3 of
[power-on.md](../../../02-operations/power-on.md), alongside the P4S4 and the router.

Confirmed from the power budget:

| | |
| --- | --- |
| Rail | Bank A — Cllena buck 51.2 V → 12 V / 30 A |
| Input range | 9–30 V |
| Power | **4.5 W** |
| Duty | Always-on |

It shares that 12 V rail with the Kairos P4S4 and the TP-Link router, behind a 25 A input
fuse. At 4.5 W it is the smallest load on the vehicle — under 1% of the payload budget —
so there is no power argument for leaving it unpowered.

That is worth noting: this is the only perception sensor on the Kairos box. Everything
else is on the Compute and Sensing box or USB from Volta. So cutting the Kairos main power
takes the SICK down with the drive-by-wire, while cutting the Compute and Sensing box
leaves it running.

> TODO(verify): **the motor is not in the power budget at all.** The appendix lists the
> picoScan at 4.5 W on Bank A and accounts for no motor anywhere in the tree — so either it
> is unpowered, it is fed from somewhere undocumented, or the base was not yet fitted when
> the budget was compiled. Establish which, and add it: a motor's draw and inrush differ in
> character from a sensor's, and Bank A's 12 V rail already reaches ~22 A of its 30 A
> capacity at full P4S4 actuation. See [power/](../../power/README.md).

## Hardware specs

| | |
| --- | --- |
| Manufacturer | SICK |
| Product family | picoScan 150 |
| Model / part number | TODO(verify) |
| Serial number | TODO(verify) |
| Scan plane | 2D, swept to 3D by the base |
| Aperture angle | TODO(verify) |
| Range | TODO(verify) |
| Angular resolution | TODO(verify) |
| Scan frequency | TODO(verify) |
| Interface | Ethernet |
| Supply | TODO(verify) |

> TODO(verify): the whole table. The picoScan family ships in several variants with
> materially different range and aperture, so the model and part number have to come first
> — the specs follow from which variant is fitted. SICK's product page and datasheet for
> that exact model are the source; save a copy into `docs/hardware/` rather than relying
> on a URL.

### Motor base

| | |
| --- | --- |
| Type | TODO(verify) |
| Sweep range | TODO(verify) |
| Sweep rate | TODO(verify) |
| Position feedback | TODO(verify) |
| Control interface | TODO(verify) |

## Additional components

> TODO(verify): unrecorded. At minimum the motor base, its controller, and the cabling
> between them. Record whether the base is a commercial product with a part number or a
> lab build, and if a build, where its design files live — alongside the printed parts in
> [`docs/hardware/CAD Designs/`](../../../../hardware/CAD%20Designs/) would be the natural
> place.

## Software

| Software | Role |
| --- | --- |
| `SICK-basic` | Referenced in the source note as the intended ROS package. Not present in this repository |

> TODO(verify): establish what `SICK-basic` refers to. SICK publishes ROS 2 drivers for
> its scanners, and `sick_scan_xd` is the one that covers the picoScan family — confirm
> whether that is what is meant, or whether something else was intended.

Three pieces of software will be needed, not one:

1. **A lidar driver** for the 2D scans.
2. **Motor control**, with position readback.
3. **A composer** that associates scans with base angles and assembles a 3D cloud —
   or a dynamic transform publisher that lets the standard tooling do it.

> TODO(verify): decide whether (3) is a custom node or whether publishing the base angle
> to `/tf` and letting a point cloud assembler handle it is sufficient. The second is less
> code and integrates with the rest of the stack, and it depends on the timestamp quality
> of the position feedback.

### Data structure / output format

A 2D driver publishes `sensor_msgs/LaserScan`; the composed product would be
`sensor_msgs/PointCloud2`, as the Ouster's is.

> TODO(verify): confirm once the driver exists, and record topics and rates in
> [ros-graph.md](../../../05-reference/ros-graph.md).

## Networking

**Ethernet to the IBEX router**, so Volta reaches it through the router rather than
directly. The Ouster has Volta's onboard port — see
[ouster-os1-64.md](ouster-os1-64.md).

> TODO(verify): record the sensor's IP address and whether it is static or assigned, then
> add it to [network.md](../../../05-reference/network.md). SICK scanners default to a
> fixed factory address and usually need configuring onto the local subnet.

> TODO(verify): a swept 2D scanner produces far less data than the Ouster, so the router
> path should be adequate. Worth confirming once the driver runs, since the router network
> also carries the P4S4 command path and should not be congested by sensor traffic.

## Setup & calibration

### Physical installation

> TODO(verify): unrecorded. Needed: how the base mounts to the vehicle, how the scanner
> mounts to the base, and the fasteners involved.

### Calibration

Two distinct things, and neither exists yet:

**Extrinsic.** The transform from the base's mount to `base_link`, which is static, and
from the scanner to the base, which is static relative to the base's own rotating frame.

**Base zero and scale.** Where the base's reported position of zero actually points, and
whether reported position matches actual. Without that, the 3D cloud is skewed in a way no
amount of software will correct.

> TODO(verify): write both procedures when the driver exists. The extrinsic can be
> cross-checked against the Ouster — both sensors see the same world, so fitting the two
> clouds to each other is a direct validation that no other sensor pair on IBEX offers.

## Known issues & fixes

None recorded, because it has never been run.

> TODO(verify): confirm the sensor and the motor still work. It has been powered at every
> startup for some time with nothing exercising it, which means a failure would be
> invisible. Worth connecting to it and commanding the base before writing any driver, so
> a hardware fault is not mistaken for a software one.

## Datasheets

> TODO(verify): none on file. Obtain SICK's datasheet and operating instructions for the
> exact model and save them into `docs/hardware/`, as with the Ouster and the hyperspectral
> cameras. SICK publishes both freely.

## Reorder

> TODO(verify): nothing recorded. Needed: the model and part number, SICK's ordering
> contact, and the motor base's provenance. Consolidate into
> [reorder.md](../../../99-appendix/reorder.md).

## Related pages

- [Perception overview](../README.md) — the sensor set
- [ouster-os1-64.md](ouster-os1-64.md) — the other 3D source, and the natural
  cross-validation target
- [power-on.md](../../../02-operations/power-on.md) — comes up at step 3, on the Kairos box
- [network.md](../../../05-reference/network.md) — the router network it sits on
- [tf-frames.md](../../../05-reference/tf-frames.md) — will need a dynamic transform for
  the base
- [power/](../../power/) — the Kairos box
