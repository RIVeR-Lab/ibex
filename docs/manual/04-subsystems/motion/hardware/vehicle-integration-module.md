---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Vehicle integration module (VIM)

The unit that arms and disarms the P4S4's actuators. Serves [Motion](../README.md).

**This is the only place actuator motion can be stopped.** Not the key, not shutting down
Volta, not killing a launch file. If someone is exposed to a moving actuator, this is what
you reach for.

## Overview

The VIM sits between the P4S4 controller and the four actuators. Nothing reaches the
throttle, brake, steering, or transmission without passing through it.

It ships as part of the P4S4 and appears in Kairos's inventory as a component of it, not
as a separate purchase. It has its own page here because it is the single most
safety-relevant control on the vehicle and because several other pages in this manual
depend on it.

### What arming means

The P4S4 being powered is not the same as the actuators being live. Power comes from the
Kairos box; **arming** happens here, and requires all four of the VIM's controls to be in
position:

| Control | Armed position |
| --- | --- |
| E-stop | Released |
| Run / pause | Run |
| On / off | On |
| Manual / auto | Auto |

All four are **in series**, so any single one of them disarms. You do not have to remember
which control is the right one — the nearest one works.

Once armed, the actuators can move whether or not the engine is running. The engine gates
whether the *vehicle* drives; it does not gate actuator motion. See
[estop-chain.md](../../../01-safety/estop-chain.md).

Commanded motion additionally requires the deadman to be held, and releasing the deadman
returns the actuators to neutral.

## Physical location on vehicle

Inside the cab, mounted on top of the P4S4 controller. **Reachable from the driver's
seat.**

> TODO(verify): confirm whether it is reachable from *outside* the vehicle, and how
> easily. This has a consequence for how sessions are run: the pre-run role table in
> [checklists.md](../../../01-safety/checklists.md) gives one safety spotter stop
> authority, and a spotter standing outside a vehicle whose only actuator stop is on the
> transmission tunnel has a verbal stop, not a physical one. If the VIM cannot be reached
> from outside, establish which control the spotter is expected to use — the Kairos box
> main e-stop is the likely candidate — and record its accessibility too.

## Power source / rail

Powered through the P4S4, which is fed by the **Kairos box**. The Kairos box's main power
button and main e-stop are therefore upstream of everything here.

Cutting the Kairos box also cuts the router that carries commands to the P4S4, so the
command path and the actuators lose power together. See [power/](../../power/).

## Hardware specs

| | |
| --- | --- |
| Manufacturer | Kairos Autonomi |
| Part of | Pronto 4 Series 4 kit |
| Part number | TODO(verify) |
| Supply | Through the P4S4 |

### Controls

| Control | Type | Behaviour |
| --- | --- | --- |
| E-stop | Latching | Must be physically reset before the system can be re-armed |
| Run / pause | Two-position, **non-latching** | Click to pause, click back to run. No twist to reset |
| On / off | Two-position, on the side of the unit | TODO(verify): which physical switch |
| Manual / auto | Two-position, on the side of the unit | `manual` is the disarmed position. TODO(verify): which physical switch |

**The run/pause switch is the preferred disarm for planned work.** It stays where you put
it, needs no reset, and clicking back to run re-arms directly — so unlike cutting power it
does not incur the 60-second thermistor wait before the system can come back. A
recoverable stop is the stop people will actually use.

### Indicators

Two green LEDs on the unit:

| LED | Lit means |
| --- | --- |
| Ready | TODO(verify): presumably powered and healthy, but not necessarily armed |
| Enabled | Armed — the actuators can move |

**The Enabled LED is the confirmation that matters.** It is the positive check that the
actuators are unpowered rather than merely uncommanded, which is the distinction that
protects anyone with their hands on a linkage. Enabled dark means not armed.

The combination is what tells the full story: **Ready lit with Enabled dark is the safe
state** — the unit is powered and working, and the actuators are not live. Both dark could
mean the unit has lost power rather than that it is disarmed, which is a different
situation.

> TODO(verify): confirm the Ready and Enabled semantics above, and record each LED's
> position on the unit. Both are green, as are the other LEDs on the P4S4, so colour alone
> does not identify them — position does. This check is referenced from four other pages
> and nobody new can perform it without knowing which LED is which.

## Additional components

None. The VIM is itself a component of the [P4S4](kairos-p4s4.md).

## Software

No driver. The VIM is a hardware interlock between the P4S4 and the actuators, and is not
addressable from ROS 2.

That is the point: no software fault can arm it, and no software fault can prevent it from
disarming. Note that the software e-stop channel in
[shared-link-bridge.md](../software/shared-link-bridge.md) is separate, publishes a
hardcoded value, and is inert — the VIM is unaffected by it.

> TODO(verify): confirm the VIM state is not settable in software, and confirm whether its
> state is *readable* in software. A topic reporting armed state would be useful for
> logging and for pre-run checks; if one exists, it belongs in
> [ros-graph.md](../../../05-reference/ros-graph.md).

## Networking

Not applicable. The VIM is wired to the P4S4 and has no network interface.

## Setup & calibration

### Physical installation

> TODO(verify): the vendor Installation Guide in
> [`docs/hardware/Kairos/`](../../../../hardware/Kairos/) is the authority for mounting.
> Record only what is IBEX-specific: where it was mounted and why that position was chosen.

### Calibration

None.

## Known issues & fixes

No faults recorded against the VIM itself.

Two documentation gaps that function as operational problems:

**LED positions are unrecorded.** The Ready and Enabled indicators are both green, as are
the other LEDs on the P4S4, so a person who has not been shown the unit cannot tell which
is which. The manual instructs people to confirm the Enabled LED is dark before working
near a linkage; until positions are recorded, that check depends on being shown it once.

**The `manual` position is only partly understood.** It removes actuator power. Whether it
also hands the linkages back to the driver's mechanical controls is unknown.

> TODO(verify): resolve the second one. If `manual` is the designed route back to manual
> driving, it is very likely the intended answer to the back-drivability problem in
> [kairos-p4s4.md](kairos-p4s4.md) — which is the largest open safety question in this
> manual. That would move it from being one of four ways to disarm into being the
> documented takeover procedure.

## Datasheets

- [`docs/hardware/Kairos/`](../../../../hardware/Kairos/) — System User Manual and
  Installation Guide

> TODO(verify): confirm whether the vendor documentation covers the VIM's controls and
> indicators specifically, and cite the page. If it does, that closes the LED gap above.

## Reorder

> TODO(verify): whether the VIM is separately orderable from Kairos or only as part of a
> P4S4 kit. Given it is the sole stop point for actuator motion, its lead time is worth
> knowing before it fails rather than after. Record in
> [reorder.md](../../../99-appendix/reorder.md).

## Related pages

- [Motion overview](../README.md) — the control path
- [kairos-p4s4.md](kairos-p4s4.md) — the controller this sits downstream of
- [actuators.md](actuators.md) — what it gates
- [estop-chain.md](../../../01-safety/estop-chain.md) — the full stop control inventory and
  emergency guidance
- [power-on.md](../../../02-operations/power-on.md) — arming, step 9
- [power-off.md](../../../02-operations/power-off.md) — disarming, step 1
- [checklists.md](../../../01-safety/checklists.md) — pre-run and post-run VIM checks
