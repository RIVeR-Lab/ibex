---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Actuators

The four actuators that operate IBEX's driver controls: throttle, brake, steering, and
transmission. Serves [Motion](../README.md).

One page for all four because they share a controller, a supply, and a stop control. Where
they differ is the mechanical interface to the vehicle, and that is where most of the
content below sits.

## Overview

Each actuator replaces a driver's hand or foot on one of the Wolverine's controls. All four
are driven by the [P4S4](kairos-p4s4.md), gated by the
[vehicle integration module](vehicle-integration-module.md), and commanded from
[`shared_link_bridge`](../software/shared-link-bridge.md) running on Volta.

Because they act on the stock controls rather than replacing them, a human driver and the
actuators are working the same linkages. That is what makes back-drivability matter, and
it is why testing has been done with a human on some controls and the P4S4 on others.

**The actuators are live whenever the VIM is armed, engine or no engine.** They cannot
drive the vehicle with the engine off, but they can move the steering wheel, press the
brake, open the throttle, and shift the transmission. Disarm before working near any of
them — see [estop-chain.md](../../../01-safety/estop-chain.md).

## Physical location on vehicle

| Actuator | Location | Access |
| --- | --- | --- |
| Throttle | TODO(verify) | TODO(verify) |
| Brake | TODO(verify) | TODO(verify) |
| Steering | At the steering column / steering wheel | TODO(verify) |
| Transmission | At the gear shifter, under the centre console | Console must be removed — see [maintenance.md](../../../03-base-vehicle/maintenance.md) |

> TODO(verify): complete this table. Anyone working on the vehicle needs to know what is
> within reach of a moving actuator before they put their hands somewhere, and the brake
> and throttle are both in the footwell where a person's legs are.

## Power source / rail

Through the P4S4, from the **Kairos box**. Arming is at the VIM.

Actuator current is the dominant load on the P4S4: 20 A with the actuators running and the
engine off, 10 A with the engine running, against 5 A idle. Figures and their source are on
[kairos-p4s4.md](kairos-p4s4.md).

## Hardware specs

| Actuator | Type | Travel / range | Part number |
| --- | --- | --- | --- |
| Throttle | TODO(verify) | TODO(verify) | TODO(verify) |
| Brake | TODO(verify) | TODO(verify) | TODO(verify) |
| Steering | Rotary, via ring and chain drive | TODO(verify) | TODO(verify) |
| Transmission | Linear | 100 to 0 — see below | TODO(verify) |

> TODO(verify): none of the individual actuator specifications are recorded. Force or
> torque, travel, and speed all matter — travel in particular, because the transmission
> actuator's range is already known to be marginal against the shifter's arc. Kairos
> supplies these as part of the kit; the System User Manual in
> [`docs/hardware/Kairos/`](../../../../hardware/Kairos/) is the place to look first.

### Mechanical interfaces

**Steering** mounts to the Wolverine's steering shaft: 19/32 in (15 mm), 29 splines — see
[specifications.md](../../../03-base-vehicle/specifications.md). Drive is via a ring,
chain, and gear assembly; Kairos supplies a drawing for it in
[`docs/hardware/Kairos/`](../../../../hardware/Kairos/).

**Transmission** is a linear actuator driving a shifter that travels along an **arc**.
Linear motion has to become angular motion, which is a live design constraint rather than
a solved detail — see [Known issues](#transmission-linear-to-arc-mismatch).

Its commanded position runs **100 to 0**, and the scale is inverted relative to what most
people assume:

| Value | Actuator state |
| --- | --- |
| 100 | Fully retracted — pulled in |
| 0 | Fully extended |

Higher numbers mean *less* extension. Worth holding onto, because reading 100 as "fully
extended" inverts every gear command.

> TODO(verify): record which value in that range corresponds to each gear — Low, High,
> Neutral, and Reverse. The range alone does not tell anyone how to select a gear, and the
> arc mismatch below means the gear positions are unlikely to be evenly spaced across it.

> TODO(verify): confirm whether 100 and 0 are the actuator's mechanical limits or software
> limits imposed on it. If they are software limits, record where they are set.

**Throttle** and **brake** act through cables onto the stock controls.

> TODO(verify): record how the brake actuator interfaces with the stock system — whether
> it acts on the pedal, the master cylinder, or the line. The stock brake configuration is
> documented in an image in the Obsidian vault that has not been migrated, see
> [specifications.md](../../../03-base-vehicle/specifications.md).

## Additional components

Five 3D-printed parts were made to interface the actuators with the Wolverine:

| Part | Purpose | CAD |
| --- | --- | --- |
| Throttle coupler | Throttle | `throttle_mount/Throttle.STEP` |
| Transmission bracket | Transmission | TODO(verify) |
| Gear shift bracket | Transmission | TODO(verify) |
| Transmission cable bracket | Transmission | `transmission/cable_bracket/transmissioncordholder.STL` |
| Steering wheel mount | Steering | `Steering Ring to Steering Wheel Connection/` — `ClampTopSmall` and `ClampBottomSmall` |

All under [`docs/hardware/CAD Designs/`](../../../../hardware/CAD%20Designs/).

> TODO(verify): two of the five are unmapped. The remaining folders are
> `transmission/transmission_base` and `transmission/steering_column`, which do not
> obviously correspond to "transmission bracket" and "gear shift bracket" by name.
> Establish which is which, and whether any part has been revised since the printed version
> on the vehicle.

## Software

Commanded by [`shared_link_bridge`](../software/shared-link-bridge.md). The teleoperation
mapping as implemented:

| Control | Input |
| --- | --- |
| Throttle and brake | Left joystick |
| Steering | Right joystick |
| Gear selection | D-pad — right D-pad scrolls shift options |
| Enable | Right bumper — the deadman, held |

**Releasing the deadman returns the actuators to neutral.** They do not hold their last
commanded position.

Telemetry coming back includes brake percentage, throttle percentage, and steering angle.
Topic names belong in [ros-graph.md](../../../05-reference/ros-graph.md).

> TODO(verify): the input scalers in `controller_teleop.py` are separately configurable for
> joystick-pressed versus joystick-released and are currently set equal. Record what they
> are for and whether they should differ.

## Networking

Not applicable. The actuators are wired to the P4S4.

## Setup & calibration

### Physical installation

Vendor installation is covered by the Kairos Installation Guide in
[`docs/hardware/Kairos/`](../../../../hardware/Kairos/).

> TODO(verify): the source notes have empty headings for the mounting rack, brake
> connection, steering wheel, throttle connection, and transmission. Record only the
> IBEX-specific parts — which printed bracket goes where, what was fabricated, and any
> deviation from the vendor guide.

### Calibration

Steering requires a baseline: the vehicle's wheels straight and the steering wheel centred,
then a calibration action. In the vendor workflow that is done from Shepherd, which IBEX
does not use for control.

> TODO(verify): establish how steering is calibrated without Shepherd, and whether the
> calibration persists in the P4S4 across power cycles. This is the open question that
> could make the OCU necessary at setup despite being outside the control path. Same TODO
> as on [kairos-p4s4.md](kairos-p4s4.md).

> TODO(verify): record whether the throttle, brake, and transmission actuators need travel
> limits set, and where those live. A transmission actuator with mis-set limits either
> fails to reach a gear or drives past it.

## Known issues & fixes

### Back-drivability — status unknown

All four actuators have, at different times, been difficult or impossible to move by hand
while engaged. The per-control history and the safety consequence are on
[kairos-p4s4.md](kairos-p4s4.md); it is cross-referenced as a known gap from
[estop-chain.md](../../../01-safety/estop-chain.md).

What belongs here is the mechanical side: each actuator couples to a stock control that a
human also operates, so a jammed actuator is a jammed driver control.

### Throttle held open

The throttle has been left held open by the actuator, producing the high-RPM-on-start
behaviour seen early in vehicle testing. This is the failure with the most consequence —
an open throttle on a vehicle that starts is a vehicle that moves.

> TODO(verify): whether this can still occur, and what the current mitigation is. Also
> whether it interacts with starting: the no-start tree in
> [troubleshooting.md](../../../03-base-vehicle/troubleshooting.md) currently checks the
> VIM first on the assumption that it can.

### Transmission linear-to-arc mismatch

**Symptom:** the actuator moves linearly; the shifter moves along an arc. The actuator's
range of travel does not map cleanly onto the gear positions.

**Proposed fix:** a lower mounting point plus a gear ratio, so the cable delivers the same
large movement from a small range of actuator travel.

> TODO(verify): **installed or still proposed?** The source describes this in a way that
> reads as done but is grammatically a suggestion. If installed, record the ratio and the
> mounting point. If not, the transmission actuator's travel is a live limitation and gear
> selection may be unreliable.

This interacts with the shift linkage nuts working loose — see
[maintenance.md](../../../03-base-vehicle/maintenance.md). Both affect whether the
commanded gear is the selected gear.

### Throttle cable connection — incompletely recorded

> TODO(verify): the source note breaks off mid-sentence at "The connection point as to
> where the throttle cable from the". Complete it.

### Steering — recorded with no content

> TODO(verify): the source note lists a steering issue as a heading with nothing under it.
> Either there is a problem worth recording or the heading should go.

## Datasheets

- [`docs/hardware/Kairos/`](../../../../hardware/Kairos/) — System User Manual,
  Installation Guide, and the steering ring, chain, and gear assembly drawing
- [`docs/hardware/CAD Designs/`](../../../../hardware/CAD%20Designs/) — the printed parts

## Reorder

> TODO(verify): whether individual actuators are separately orderable from Kairos or only
> as part of a kit, and whether spares of the printed brackets exist. The printed parts can
> be remade from CAD, which is worth noting as the mitigation — but only if the CAD mapping
> above is resolved first. Record in [reorder.md](../../../99-appendix/reorder.md).

## Related pages

- [Motion overview](../README.md) — the control path
- [kairos-p4s4.md](kairos-p4s4.md) — the controller and the back-drivability history
- [vehicle-integration-module.md](vehicle-integration-module.md) — arming and disarming
- [shared-link-bridge.md](../software/shared-link-bridge.md) — what commands them
- [estop-chain.md](../../../01-safety/estop-chain.md) — stopping actuator motion
- [specifications.md](../../../03-base-vehicle/specifications.md) — the stock controls
  they act on
- [maintenance.md](../../../03-base-vehicle/maintenance.md) — the shift linkage they share
