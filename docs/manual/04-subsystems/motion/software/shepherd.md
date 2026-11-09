---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Shepherd

Kairos's operator application for the OCU. Serves [Motion](../README.md).

> **Shepherd is not optional, and it is not legacy.** It is outside the runtime control
> loop — vehicle commands come from [`shared_link_bridge`](shared-link-bridge.md) on
> Volta — but it is **the route to the P4S4's configuration**, and nothing in our stack
> offers an alternative.
>
> **Shepherd is not itself the configuration tool.** Its Assets tab opens a VNC session
> into the P4S4, where [JAUS_IVN](jaus-ivn.md) runs and the Dynamic Knowledge Store holds
> the persisted values. Shepherd is the door; JAUS_IVN is the room.

## Source

Vendor software. Not in this repository and not available to us as source.

| | |
| --- | --- |
| Vendor | Kairos Autonomi |
| Runs on | The [OCU](../hardware/kairos-p4s4-ocu.md) — Panasonic CF-53 |
| Documentation | `Shepherd Overview 01_03_00`, in [`docs/hardware/Kairos/`](../../../../hardware/Kairos/) |
| Version installed | TODO(verify) |

> TODO(verify): the documentation available to the lab covers only the Asset View tab, and
> the version it describes may not be the version installed. Establish which version is on
> the OCU and whether Kairos can supply documentation for the Configuration tab.

## Fork status

Not applicable. Closed vendor software.

## Description

Shepherd is the operator terminal application supplied with the P4S4. It presents vehicle
telemetry, provides teleoperation, and — in versions with the pathing feature — records
and plays back driven paths.

It speaks SharedLink to the P4S4, the same protocol `shared_link_bridge` implements.

## Capabilities

Four operating modes, per the vendor documentation:

| Mode | Availability |
| --- | --- |
| Manual | All versions |
| Tele-operation | All versions |
| Single path playback | Versions with pathing only |
| Multiple path playback | Versions with pathing only |

> TODO(verify): whether the installed version has the pathing features. This is an open
> question from the original notes and has not been answered — see
> [open-questions.md](../../../99-appendix/open-questions.md).

The interface has two primary tabs, **Asset View** and **Configuration**. Asset View
contains the telemetry displays, the view tabs (map, video, browser), and the operational
tabs including tele-operation.

## Where configuration actually lives

The P4S4 has two things talking to it, and they do different jobs.

| Layer | Runs on | Role |
| --- | --- | --- |
| `shared_link_bridge` | **Volta** | Runtime commands over SharedLink UDP |
| **Shepherd** | **The OCU** | Operator app; its **VNC button** opens a session into the P4S4 |
| [**JAUS_IVN**](jaus-ivn.md) | **The P4S4** | The configuration application |
| **Dynamic Knowledge Store** | **The P4S4** | Where persisted values live |

So: **Volta commands the P4S4; the P4S4 configures itself through JAUS_IVN; the OCU is how
you reach it.**

Volta says *shift to this gear*. The P4S4 translates that into actuator travel using values
that **only Shepherd can set.** If those values are wrong, the command is correct and the
result is not.

**Any mechanical change to the coupling between an actuator and the vehicle can invalidate
the P4S4's configuration for that actuator.** That is not a hypothetical — see
[Transmission shift values](#transmission-shift-values).

### What IBEX uses it for

Two things, and the second was previously missing from this page.

**1. Steering calibration.** The tele-operation tab provides:

| Control | Effect |
| --- | --- |
| Calibrate Steering | Sets the baseline relationship between commanded and actual steering, with the wheels straight and the wheel centred |
| Bump Left / Bump Right | Temporary adjustment during operation, not intended to persist |
| ForceZero Position | Retains bump adjustments for the remainder of the operation |

The calibration persists in the P4S4 across power cycles, so this is an installation-time
task rather than a per-session one.

**2. VNC access to the P4S4**, through the **Assets** tab's VNC button. That session is how
every configuration change is made, including the transmission shift values. See
[jaus-ivn.md](jaus-ivn.md).

## Purpose

It is the vendor's intended operator interface, and **the only route we have into the
P4S4's configuration** — by way of the VNC session it opens into
[JAUS_IVN](jaus-ivn.md).

That makes the OCU a hard dependency for maintaining the vehicle, even though it takes no
part in driving it. The machine running Shepherd is a **Panasonic CF-53, long
discontinued** — so the dependency is on both the software and an unobtainable laptop. See
[reorder.md](../../../99-appendix/reorder.md).

## Alternative software

[`shared_link_bridge`](shared-link-bridge.md) is what IBEX runs instead, for control. It
puts vehicle commands inside ROS 2 rather than on a separate laptop — see
[Why not Shepherd](../README.md#why-not-shepherd).

The trade is real: Shepherd's path recording and playback have no equivalent in our stack,
so anything needing those would have to be reimplemented.

## Launch / invocation

Run on the OCU. Requires the P4S4's ethernet cable moved from the router to the OCU — see
[kairos-p4s4-ocu.md](../hardware/kairos-p4s4-ocu.md). **Volta cannot reach the P4S4 while
that cable is in the OCU.**

> TODO(verify): record how Shepherd is actually started on the OCU, and whether any
> configuration is needed before it will connect.

## Topics

None. Shepherd is not a ROS 2 node.

## Services and actions

None.

## Non-ROS interfaces

SharedLink to the P4S4, over the ethernet cable described above.

Video recordings are written locally on the OCU to `C:/GC07_vids/`, per the vendor
documentation.

> TODO(verify): whether anything has ever been recorded there, and whether it needs
> retrieving or clearing. A Windows path in the vendor docs also implies the OCU runs
> Windows, which should be confirmed on
> [kairos-p4s4-ocu.md](../hardware/kairos-p4s4-ocu.md).

## Parameters

> TODO(verify): the Configuration tab provides "development and installation level
> configuration options" according to the vendor overview, which does not document them.
> If any of IBEX's configuration lives there, it is currently unrecorded and would be lost
> if the OCU were replaced.

## Dependencies

- The [OCU](../hardware/kairos-p4s4-ocu.md), powered and booted
- The [P4S4](../hardware/kairos-p4s4.md), powered — the Kairos box on
- The ethernet cable moved from the router to the OCU

## Configuration changes

Shepherd's part is one click: **Assets tab → select the robot asset → VNC**.

Everything after that happens in [JAUS_IVN](jaus-ivn.md) on the P4S4 — including the
**transmission shift value calibration**, which is documented there in full from Kairos
Bulletin BUL-023.

**Prerequisite, which is Shepherd's side of it:** the P4S4's ethernet cable must be moved
from the router to the OCU, and **Volta cannot reach the P4S4 while it is there.** Move it
back afterwards.

> TODO(verify): more Kairos documentation covering other configuration tools is expected.
> Each should get its own page alongside `jaus-ivn.md` rather than being folded in here —
> Shepherd's own role stays small.

## Known issues & fixes

None recorded, because Shepherd is rarely exercised.

**The cable swap is the practical hazard.** Using Shepherd requires unplugging the P4S4
from the router, and a cable left in the OCU afterwards presents as
`shared_link_bridge` failing to reach the P4S4 — a software fault that is not one. See
[running-the-system.md](../../../02-operations/running-the-system.md).

> TODO(verify): confirm Shepherd still launches and still connects. It is the
> least-exercised software on the vehicle, so problems with it will surface at setup, which
> is exactly when they are most inconvenient.

## Understanding the software

Enough to navigate the interface if you have to.

**Asset View** shows the P4S4 as an asset that the OCU logs into. Kairos's model has four
asset types — vehicles, radio relays, cameras, and other OCUs — and IBEX presents as a
vehicle. Gaining control requires selecting the asset and clicking Login.

**Telemetry** on the P4S4 tab includes speed, engine RPM, fuel level, battery voltage,
brake and throttle percentage, and steering angle, with gear and auxiliary indicators
beside them. The bottom of the tab shows auto/manual state, GPS fix and satellite count,
enabled state, system temperature, and link quality.

**Two indicators are worth knowing.** The steering gauge's label reads `Deadman` when the
deadman is not applied and `MotionOn` when the system is in tele-op with the deadman held.
A red background on the auto/manual or link quality fields means lost communication or a
busy asset.

**Gear changes require tele-op mode and the deadman engaged.** The same conjunction that
governs [`shared_link_bridge`](shared-link-bridge.md).

### Unresolved vendor terminology

The vendor documentation references components the lab has not identified: `IVN`, `VAK`,
`Mobius`, `djDRIVEWB`, `djMimic`, and `djBasis`. Shepherd is described as validated
against several combinations of these.

These are tracked in [open-questions.md](../../../99-appendix/open-questions.md) and
listed in the [glossary](../../../00-onboarding/glossary.md) as unresolved. None appear to
be needed for IBEX's current use, which is why they remain unresolved.

## Related pages

- [Motion overview](../README.md) — why this is not in the control path
- [kairos-p4s4-ocu.md](../hardware/kairos-p4s4-ocu.md) — the laptop it runs on
- [kairos-p4s4.md](../hardware/kairos-p4s4.md) — the hardware it talks to
- [actuators.md](../hardware/actuators.md) — what steering calibration calibrates
- [jaus-ivn.md](jaus-ivn.md) — the configuration application this provides access to
- [shared-link-bridge.md](shared-link-bridge.md) — what IBEX runs instead
- [open-questions.md](../../../99-appendix/open-questions.md) — unresolved vendor questions
