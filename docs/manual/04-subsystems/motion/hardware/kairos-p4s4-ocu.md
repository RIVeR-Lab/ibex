---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Operator Control Unit (OCU)

The rugged laptop that runs the Kairos Shepherd application. Serves
[Motion](../README.md).

## Overview

The OCU is the operator terminal supplied with the P4S4. It runs
[Shepherd](../software/shepherd.md), Kairos's application for teleoperating and
overseeing the vehicle.

**IBEX does not use it for normal operation.** Vehicle commands come from
`shared_link_bridge` running on Volta — see
[Why not Shepherd](../README.md#why-not-shepherd).

**It is still required.** Steering calibration is performed through Shepherd on the OCU,
so the vehicle cannot be set up without it. Keeping a laptop that is not in the control
path is deliberate for that reason, not an oversight.

## Physical location on vehicle

Stored inside the vehicle, so that it is to hand if needed.

> TODO(verify): record where in the cab, and whether it is secured. A loose laptop in a
> vehicle driven over marsh and mud is a projectile as well as an expensive item — see
> the pre-run check for unsecured cargo in
> [checklists.md](../../../01-safety/checklists.md).

## Power source / rail

Self-powered. Internal battery, charged from its own supply cable.

| | |
| --- | --- |
| Input | 15.6 V DC, 7.05 A |
| Power | ~110 W |
| Charger | Supplied cable, matching the above |

The OCU is **not** on the Kairos box, the Compute and Sensing box, or any vehicle rail. It
is therefore unaffected by every stop control on the vehicle, and it does not appear in
the power tree in [estop-chain.md](../../../01-safety/estop-chain.md).

> TODO(verify): where the OCU is charged, and whether it can be charged from the vehicle.
> The AC adapter on the vehicle feeds the monitor; whether it has capacity for a 110 W
> laptop as well is unrecorded. This matters for field sessions, where a flat OCU means no
> steering calibration.

> TODO(verify): record the battery's practical runtime, and whether the OCU is kept
> charged between sessions or charged on demand.

## Hardware specs

| | |
| --- | --- |
| Manufacturer | Panasonic |
| Model | CF-53 |
| Class | Rugged laptop |
| Input | 15.6 V, 7.05 A |
| Operating system | TODO(verify) |
| Storage | TODO(verify) |
| Serial number | TODO(verify) |

> TODO(verify): record the operating system, since Shepherd's version and its
> compatibility depend on it, and Shepherd writes video recordings to a Windows-style path
> (`C:/GC07_vids/`) according to the vendor documentation.

## Additional components

- Charging cable, 15.6 V 7.05 A
- TODO(verify): any network cable, dongle, or adapter needed to connect it to the vehicle

## Software

| Software | Role |
| --- | --- |
| [shepherd.md](../software/shepherd.md) | The Kairos operator application. Used for steering calibration; not in the control path |

Shepherd is vendor software and is not in this repository.

> TODO(verify): record the Shepherd version installed. The vendor documentation available
> to the lab is "Shepherd Overview 01_03_00" and covers only the asset view, so the
> installed version and what it includes — notably whether it has the pathing features —
> is unconfirmed. Tracked in
> [open-questions.md](../../../99-appendix/open-questions.md).

## Networking

| | |
| --- | --- |
| OCU address | `192.168.200.30` |
| Subnet mask | `255.255.0.0` — a /16, unlike the /24 used everywhere else |
| Default gateway | `192.168.200.1`, the router — **unreachable while direct-connected to the P4S4** |
| P4S4 address | `192.168.200.220` |

The mask is wider than the rest of the vehicle's. It does not break the direct link, but
it is worth narrowing to `255.255.255.0` — see
[network.md](../../../05-reference/network.md#the-ocus-address-and-its-odd-subnet-mask).


The OCU connects to the P4S4 by **ethernet cable — the same cable**. To connect the OCU,
the cable running from the P4S4 to the IBEX router is unplugged at the router end and
plugged into the OCU instead.

**The OCU and Volta cannot both reach the P4S4.** They share one cable, so connecting one
disconnects the other:

| Cable plugged into | Commands the P4S4 | Cannot reach the P4S4 |
| --- | --- | --- |
| Router | Volta, via `shared_link_bridge` | OCU |
| OCU | Shepherd | Volta |

This is a useful property during calibration — with the cable in the OCU, nothing on Volta
can command the vehicle while someone is working at the steering. It is also the most
likely way to lose an afternoon: **a cable left in the OCU after calibration presents as
`shared_link_bridge` failing to reach the P4S4**, which looks like a software fault and is
not one.

Reconnect the cable to the router before any session run from Volta.

> TODO(verify): record the OCU's own IP configuration. With the cable moved, the OCU is on
> a point-to-point link with the P4S4 at `192.168.200.220` rather than on the router
> network, so it needs an address on that subnet — presumably static. Record it and add it
> to [network.md](../../../05-reference/network.md).

> TODO(verify): confirm whether the P4S4 has only the one ethernet port. If it has a
> second, this swap is unnecessary and both machines could stay connected.

Kairos documentation describes OCUs as network assets that other OCUs can reach by VNC and
by file access. Whether any of that is enabled here is unknown and worth establishing —
an unmanaged laptop with remote access on the vehicle network is worth knowing about
deliberately.

## Setup & calibration

### Steering calibration

This is why the OCU exists on IBEX.

With the vehicle's wheels straight and the steering wheel centred, Shepherd's
teleoperation tab provides a **Calibrate Steering** action that sets the baseline
relationship between commanded steering and actual steering. The same tab provides **Bump
Left**, **Bump Right**, and **Force Zero Position** for adjusting that relationship during
operation.

**The calibration persists in the P4S4 across power cycles.** The OCU is therefore needed
at installation and after anything that disturbs the steering actuator — not at the start
of every session. A normal run does not require it.

> TODO(verify): write the calibration as a procedure — the exact sequence, and how you
> confirm it took. It is currently described only in terms of which buttons exist.

> TODO(verify): enumerate what requires recalibration. Dealer service is the obvious one —
> see [maintenance.md](../../../03-base-vehicle/maintenance.md), which flags that nobody
> currently re-verifies the drive-by-wire after a dealer visit. Removing or adjusting the
> steering mount, and any work on the ring and chain assembly, are the others worth
> confirming.

### Physical installation

None. The OCU is a portable laptop, not a fitted component.

## Known issues & fixes

None recorded.

> TODO(verify): the OCU is the least-exercised part of the motion subsystem, which means
> problems with it will surface at setup rather than during use. Worth confirming it still
> boots, still runs Shepherd, and still connects, rather than discovering otherwise the
> next time a calibration is needed.

## Datasheets

- [`docs/hardware/Kairos/`](../../../../hardware/Kairos/) — System User Manual and the
  Shepherd overview document

> TODO(verify): add a link to Panasonic's CF-53 documentation, and record which hardware
> revision this unit is. The CF-53 shipped in several configurations.

## Reorder

The CF-53 was supplied by Kairos with the system in 2022 and is a discontinued model.
Whether it is replaceable is **unknown and is a question for Kairos** — specifically
whether Shepherd will run on a machine the lab sources itself, or whether the OCU is
matched hardware that has to come from the vendor.

> TODO(verify): ask Kairos. Given the OCU is required for steering calibration and the
> model has been out of production for years, the answer is worth having before the
> laptop fails rather than after. Record it here and in
> [reorder.md](../../../99-appendix/reorder.md), along with Kairos's support contact.

## Related pages

- [Motion overview](../README.md) — why Shepherd is not in the control path
- [shepherd.md](../software/shepherd.md) — the application it runs
- [kairos-p4s4.md](kairos-p4s4.md) — the controller it calibrates
- [actuators.md](actuators.md) — the steering actuator being calibrated
- [network.md](../../../05-reference/network.md) — addressing
- [maintenance.md](../../../03-base-vehicle/maintenance.md) — when recalibration may be
  needed
