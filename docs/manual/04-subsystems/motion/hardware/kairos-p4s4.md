---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Kairos Pronto 4 Series 4 (P4S4)

The drive-by-wire controller that actuates IBEX's throttle, brake, steering, and
transmission. Serves [Motion](../README.md).

## Overview

The P4S4 is an off-the-shelf drive-by-wire and autonomy kit from Kairos Autonomi. It
converts a conventional vehicle into one that can be commanded electronically, by adding
actuators to the driver's controls and a controller that drives them.

It ships with more than we use. The kit includes the Shepherd operator application and
path-playback autonomy, which IBEX does not use for control — see
[Why not Shepherd](../README.md#why-not-shepherd). What IBEX uses is the actuation
hardware and the SharedLink protocol.

The P4S4 also carries the GPS receiver whose data reaches the factor graph in
[state-estimation](../../state-estimation/).

## Physical location on vehicle

Distributed. One controller, one integration module, and four actuators at separate points
on the vehicle.

| Piece | Location | Access |
| --- | --- | --- |
| P4S4 controller | TODO(verify) | TODO(verify) |
| Vehicle integration module | TODO(verify) | TODO(verify) |
| Mounting rack | TODO(verify) | TODO(verify) |
| Throttle, brake, steering, transmission actuators | See [actuators.md](actuators.md) | |

> TODO(verify): this table is the most-asked question about this subsystem and none of it
> is recorded. Locate each piece specifically enough that someone who has never opened the
> vehicle can find it, and note what has to be removed to reach it.

## Power source / rail

Fed by the **Kairos box**. The main power button on that box energizes the P4S4; the main
e-stop cuts it.

The router that carries commands from Volta is on the same box, so the command path and
the actuators lose power together. See [power/](../../power/) for the rail design and
[power-on.md](../../../02-operations/power-on.md) for the sequence.

Powering the P4S4 does not arm the actuators. Arming happens at the
[vehicle integration module](vehicle-integration-module.md).

## Hardware specs

| | |
| --- | --- |
| Manufacturer | Kairos Autonomi |
| Model | Pronto 4 Series 4 (P4S4) |
| Part number | TODO(verify) |
| Serial number | TODO(verify) |
| Supply voltage | 12 V DC |
| Power | 240 W |

Current draw varies by what the system is doing:

| State | Current |
| --- | --- |
| Not driving, actuators not running | 5 A |
| Running actuators, engine off | 20 A |
| Running actuators, engine running | 10 A |

These figures come from **Appendix A of the SOP**, which is the University-approved
electrical inventory and is authoritative — see [sop.md](../../../01-safety/sop.md). They
supersede an 18 W figure recorded in the original Obsidian notes, which was wrong by more
than an order of magnitude and is not plausible for a system that actuates the steering of
an 1,800 lb vehicle.

Note that actuator draw is *higher* with the engine off (20 A) than with it running
(10 A) — worth knowing when working on a powered vehicle that is not running, which is
most of the time.

> **Adding or changing a powered component puts Appendix A out of date.** Correcting it
> goes through the SOP revision process, not a commit.

## Additional components

- [Vehicle integration module](vehicle-integration-module.md) — ships as part of the P4S4
  and appears in Kairos's inventory as part of it
- [OCU](kairos-p4s4-ocu.md) — the rugged laptop
- GPS receiver
- Five 3D-printed parts, made to interface the P4S4 with the Wolverine:

| Part | CAD |
| --- | --- |
| Throttle coupler | TODO(verify) |
| Transmission bracket | TODO(verify) |
| Gear shift bracket | TODO(verify) |
| Transmission cable bracket | TODO(verify) |
| Steering wheel mount | TODO(verify) |

> TODO(verify): map each printed part to its CAD file under
> [`docs/hardware/CAD Designs/`](../../../../hardware/CAD%20Designs/). The folders are
> `throttle_mount`, `transmission/cable_bracket`, `transmission/transmission_base`,
> `transmission/steering_column`, and `Steering Ring to Steering Wheel Connection` — five
> folders against five named parts, but the names do not align one-to-one and "gear shift
> bracket" versus "transmission bracket" is not resolvable from filenames alone.

## Software

| Software | Role |
| --- | --- |
| [shared-link-bridge.md](../software/shared-link-bridge.md) | What IBEX runs. Implements SharedLink on Volta |
| [shepherd.md](../software/shepherd.md) | Vendor OCU application. Not in the current control path |

### Data structure / output format

The P4S4 exchanges state and commands over the SharedLink protocol. Telemetry returning
from the vehicle includes speed, engine RPM, fuel level, battery voltage, brake and
throttle percentage, steering angle, gear state, GPS fix and satellite count, enabled
state, system temperature, and link quality.

> TODO(verify): confirm which of those fields `shared_link_bridge` actually exposes as ROS
> 2 topics. The list above is what the Shepherd interface displays, which is the vendor's
> view of the protocol rather than evidence of what our bridge publishes. Topic names
> belong in [ros-graph.md](../../../05-reference/ros-graph.md).

## Networking

### Physical interface

The P4S4 has an ethernet port, cabled to the IBEX router. Volta reaches it through that
router rather than directly — Volta's onboard ethernet port is taken by the Ouster, so the
router connects to Volta through a USB hub over USB-C.

`shared_link_bridge` speaks SharedLink over UDP across this path.

### Addressing

The P4S4 is at `192.168.200.220` on the router network. Full address map:
[network.md](../../../05-reference/network.md).

## Setup & calibration

### Physical installation

Vendor installation is documented in
[`docs/hardware/Kairos/Kairos Installation`](../../../../hardware/Kairos/), including the
Installation Guide and a steering ring, chain, and gear assembly drawing. That is the
authority; this page should record only what is specific to IBEX.

> TODO(verify): the source note has five empty headings here — mounting rack, brake
> connection, steering wheel, throttle connection, and transmission. Fill in only the
> IBEX-specific parts: which printed bracket goes where, what was fabricated rather than
> supplied, and any deviation from the vendor guide. Do not re-transcribe the vendor
> procedure.

### Calibration

Steering calibration exists in the vendor workflow — Shepherd exposes a calibrate,
bump-left, bump-right, and force-zero set of controls against a centred steering wheel and
straight wheels.

> TODO(verify): establish how steering is calibrated without Shepherd. If
> `shared_link_bridge` does not expose an equivalent, then either calibration is done once
> via the OCU and persists in the P4S4, or it is not being done at all. This determines
> whether the OCU is needed at setup even though it is not in the control path.

## Known issues & fixes

### GPS failure — resolved

**Symptom:** GPS connection lost.
**Cause:** a broken cable inside the unit, found after the unit was returned to Kairos.
**Fix:** repaired by the manufacturer. **Installed.**

### Not reliably back-drivable — status unknown

**Symptom:** with the system engaged, the throttle, steering, brake, and transmission have
each been difficult or impossible to move by hand, making it hard to return to manual
control.

Observed per control:

| Control | Observed behaviour |
| --- | --- |
| Throttle | Held open. Produced the high-RPM-on-start behaviour seen early in testing |
| Steering | Locked; the wheel could not be turned |
| Brake | Difficult to return to manual |
| Transmission | Difficult to return to manual |

**This is a safety gap, not just an inconvenience.** Manual takeover is not a reliable
override, and it is cross-referenced as a known gap from
[estop-chain.md](../../../01-safety/estop-chain.md). Stop the vehicle with the key and
disarm at the VIM instead.

> TODO(verify): **is this still current?** The source note does not say whether it was
> fixed, mitigated, or simply lived with. Nothing in the manual is more worth resolving:
> the answer determines what a new person is told about taking the wheel.

> TODO(verify): establish whether the `manual` position of the VIM's manual/auto switch is
> the designed route back to manual control. If it is, that is the answer to this problem
> and it belongs here rather than only in the control inventory.

### Transmission linear-to-arc mismatch — fix proposed, not confirmed installed

**Symptom:** the transmission actuator is a linear actuator, but the gear shifter travels
along an arc. Linear motion has to become angular motion.

**Proposed fix:** a lower mounting point plus a gear ratio, so the cable delivers the same
large movement from the actuator's small range of travel.

> TODO(verify): **is this installed or still a proposal?** The source note describes it in
> a way that reads as done but is grammatically a suggestion. If it is installed, record
> the ratio and the mounting point. If it is not, the transmission actuator's current
> range of travel is a live limitation.

### Throttle cable connection — incompletely recorded

> TODO(verify): the source note breaks off mid-sentence at "The connection point as to
> where the throttle cable from the". Complete it. Given the throttle is the control with
> the worst failure history, this is not a gap to leave.

### Steering — recorded with no content

> TODO(verify): the source note lists "Issues with the Steering wheel" as a heading with
> nothing under it. Either there is a problem worth recording or the heading should go.

## Datasheets

- Vendor product page: <https://www.kairosautonomi.com/pronto4-series-4>
- [`docs/hardware/Kairos/`](../../../../hardware/Kairos/) — System User Manual,
  Installation Guide, and the steering ring, chain, and gear assembly drawing

Prefer the local copies. Cite page numbers when referencing a specific figure.

## Reorder

> TODO(verify): nothing recorded. Needed: the P4S4 part number, Kairos's support and
> ordering contact, and whether spares exist for the actuators or the printed brackets.
> Consolidate into [reorder.md](../../../99-appendix/reorder.md).

## Related pages

- [Motion overview](../README.md) — the control path and subsystem-level issues
- [vehicle-integration-module.md](vehicle-integration-module.md) — arming and disarming
- [actuators.md](actuators.md) — the four actuators and their brackets
- [kairos-p4s4-ocu.md](kairos-p4s4-ocu.md) — the rugged laptop
- [shared-link-bridge.md](../software/shared-link-bridge.md) — the driver
- [estop-chain.md](../../../01-safety/estop-chain.md) — what stops actuator motion
- [power/](../../power/) — the Kairos box
- [specifications.md](../../../03-base-vehicle/specifications.md) — the 19/32 in, 29-spline
  steering shaft the actuator mounts to
- [sop.md](../../../01-safety/sop.md) — Appendix A, the approved electrical inventory
