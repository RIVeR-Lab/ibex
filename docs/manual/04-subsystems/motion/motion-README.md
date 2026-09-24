---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Motion

Everything that makes IBEX drive itself: the drive-by-wire hardware, the actuators on the
vehicle's controls, and the software that commands them.

This is the subsystem where a mistake moves an 1,800 lb vehicle. Read
[estop-chain.md](../../01-safety/estop-chain.md) before working on anything here.

## The control path

```
Operator gamepad
  └─ shared_link_bridge (on Volta)
       └─ SharedLink over UDP
            └─ router (192.168.200.0/24)
                 └─ Kairos P4S4 (192.168.200.220)
                      └─ Vehicle integration module
                           ├─ Throttle actuator
                           ├─ Brake actuator
                           ├─ Steering actuator
                           └─ Transmission actuator
```

Data also flows back: the P4S4's GPS returns with the SharedLink messages, gets converted
into a ROS 2 GPS message by `shared_link_bridge`, and is consumed by the factor graph in
[state-estimation](../state-estimation/).

Three things about this path are worth holding in your head:

**Commands cross the network.** The P4S4 is an ethernet device on the router network, not
something Volta talks to directly. The router is on the Kairos box, the same supply as the
P4S4 — so the command path and the actuators lose power together rather than one
outliving the other.

**Everything passes through the VIM.** Nothing reaches an actuator without going through
it, which is what makes it the only place actuator motion can be stopped. See
[vehicle-integration-module.md](hardware/vehicle-integration-module.md).

**Motion needs three conditions, not one.** The P4S4 powered, the VIM armed, and the
deadman held. Removing any one stops commanded motion, and releasing the deadman returns
the actuators to neutral rather than leaving them where they were.

## Why not Shepherd

Kairos ships Shepherd, an operator application for the OCU that speaks SharedLink and
provides teleoperation, path recording, and path playback.

IBEX does not use it for control. `shared_link_bridge` runs on Volta and implements the
SharedLink protocol directly, which puts vehicle commands inside ROS 2 where the rest of
the stack lives — so autonomy, logging, and the factor graph all see the same data without
a translation layer sitting on a separate laptop.

The cost is that the path-playback and path-recording features Shepherd provides are not
available to us, and anything Shepherd does that we need has to be reimplemented. See
[shepherd.md](software/shepherd.md) for what exists on the OCU, and
[shared-link-bridge.md](software/shared-link-bridge.md) for what we run instead.

## Known issues spanning the subsystem

Component-specific problems live on component pages. These are the ones that touch more
than one:

**The system may not be back-drivable.** Engaged actuators have locked the throttle, the
steering, the brake, and the transmission on separate occasions. Taking manual control is
not a guaranteed override. Mechanism and current status:
[kairos-p4s4.md](hardware/kairos-p4s4.md).

**The software e-stop channel is inert.** `estop_beacon.py` publishes a hardcoded
`EStopState.RUN`, so nothing in software can assert a stop through it. See
[shared-link-bridge.md](software/shared-link-bridge.md).

**Autonomous mode's safety properties are unestablished.** The deadman requirement and
return-to-neutral behaviour are known for teleoperation. Whether they hold for autonomous
or path-playback operation is unknown — and that is the case where no hand is on a
deadman.

## Pages

### Hardware

| Page | Covers |
| --- | --- |
| [kairos-p4s4.md](hardware/kairos-p4s4.md) | The drive-by-wire controller: specs, power, installation, known issues |
| [vehicle-integration-module.md](hardware/vehicle-integration-module.md) | The VIM — its four controls, LEDs, and what arming means |
| [actuators.md](hardware/actuators.md) | Throttle, brake, steering, and transmission actuators, their brackets and printed parts |
| [kairos-p4s4-ocu.md](hardware/kairos-p4s4-ocu.md) | The rugged laptop |

The VIM is a component of the P4S4 as delivered and appears in Kairos's inventory as part
of it. It has its own page because four other pages in this manual link to it and because
it is the only place actuator motion can be stopped — not because it is a separate
purchase.

### Software

| Page | Covers |
| --- | --- |
| [shared-link-bridge.md](software/shared-link-bridge.md) | The SharedLink implementation we run, including teleoperation. Also covers its interface definitions |
| [shepherd.md](software/shepherd.md) | The vendor OCU application. Stub — not in the current control path |

## Open questions

| Question | Why it matters |
| --- | --- |
| Is the back-drivability problem still current? | Determines whether manual takeover is a fallback at all |
| Do autonomous modes require a held deadman? | The only protection against unattended commanded motion |
| Is the transmission gear-ratio fix installed or proposed? | The source note reads as a proposal written in the past tense |
| Does an armed P4S4 prevent the engine from starting, or only affect how it starts? | Changes the order of the no-start tree in [troubleshooting.md](../../03-base-vehicle/troubleshooting.md) |

## Related

- [estop-chain.md](../../01-safety/estop-chain.md) — every stop control and what it cuts
- [power-on.md](../../02-operations/power-on.md) — arming, step 9
- [power-off.md](../../02-operations/power-off.md) — disarming, step 1
- [running-the-system.md](../../02-operations/running-the-system.md) — launching the
  controller
- [state-estimation/](../state-estimation/) — consumer of the GPS data returning from the
  P4S4
- [power/](../power/) — the Kairos box that feeds all of this
- [specifications.md](../../03-base-vehicle/specifications.md) — the steering shaft the
  actuator mounts to
