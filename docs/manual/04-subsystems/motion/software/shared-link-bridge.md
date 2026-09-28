---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# shared_link_bridge

The ROS 2 package that commands the Kairos P4S4. Serves [Motion](../README.md).

This is IBEX's control path. It runs on Volta and speaks Kairos's SharedLink protocol
directly, in place of the vendor's Shepherd application.

## Source

| | |
| --- | --- |
| Repository | <https://github.com/RIVeR-Lab/shared_link_bridge> |
| In this repo | `packages/shared_link_bridge` — git submodule |
| Pinned commit | `e3d14ec5680543107f6b6e3dcd302f1263b7aaf6` |

## Fork status

A fork. Originally written by an intern in a personal repository, then forked into the
lab's account, which is what this repository's submodule points at.

| | |
| --- | --- |
| Upstream | A former intern's personal repository |
| Our fork | <https://github.com/RIVeR-Lab/shared_link_bridge> |
| Tracked | The lab fork. Upstream is not followed |
| Upstreamable | Not applicable — no active upstream to contribute back to |

**Treat the lab fork as authoritative.** Development continues here; the original is
historical. Nothing should be sent upstream and nothing is expected to arrive from it.

> TODO(verify): record the upstream URL for provenance, and confirm the original author is
> no longer maintaining it. A dependency whose upstream is a personal account that may be
> deleted is worth noting even when nothing breaks if it disappears.

Because this is a fork rather than first-party code, the submodule arrangement is
justified — integration-specific work still belongs in the parent repo.

## Description

A ROS 2 package implementing the SharedLink protocol, which is how Kairos hardware
exchanges state and commands with a controlling computer. The package translates between
SharedLink over UDP and ROS 2 topics, so the rest of IBEX's stack can command the vehicle
and consume its telemetry without knowing anything about the vendor protocol.

## Capabilities

Three nodes:

| Node | Role |
| --- | --- |
| `shared_link_bridge_node.py` | Implements the SharedLink protocol. Translates between ROS topics and Kairos's `/kairos_values` format |
| `controller_teleop.py` | Teleoperation. Converts `/joy` gamepad input into vehicle commands, with a live text GUI |
| `estop_beacon.py` | Broadcasts vehicle stop state to the P4S4 over UDP at 1 Hz. Controlled by a ROS 2 service, not a topic — see [Services](#services) |

> TODO(verify): the source note describes `shared_link_bridge_node.py` as "presumably"
> translating to and from `/kairos_values`. Read the node and confirm what it actually
> does, in both directions.

### Teleoperation

| Input | Effect |
| --- | --- |
| Left joystick | Throttle and brake |
| Right joystick | Steering |
| Right bumper | Deadman — must be held for any drive input |
| D-pad right | Scrolls shift options |
| D-pad left, `A` | Toggles connect / teleop |

**Releasing the deadman returns the actuators to neutral.** They do not hold their last
commanded position.

The GUI is text-based and reports publish frequency for both `/joy` and `/kairos_values`,
which makes it the fastest way to tell a dead gamepad from a dead link.

## Purpose

SharedLink is the only way to talk to the P4S4. This package is what puts that
conversation inside ROS 2, which is what lets autonomy, logging, and state estimation all
see vehicle data as ordinary topics.

It is also how GPS reaches the rest of the system: the P4S4's GPS returns with the
SharedLink messages and is republished as a ROS 2 message, consumed by the factor graph in
[state-estimation](../../state-estimation/).

## Alternative software

**Shepherd**, the vendor's OCU application, speaks the same protocol and offers
teleoperation plus path recording and playback. IBEX does not use it for control because
it runs on a separate laptop and keeps vehicle data outside ROS 2 — see
[Why not Shepherd](../README.md#why-not-shepherd). It is still required for steering
calibration.

Beyond that there is no alternative. Other packages may handle UDP transport generally,
but nothing else converts SharedLink into ROS 2 messages for the P4S4.

## Launch / invocation

```bash
ros2 launch shared_link_bridge bringup.launch.py
```

Or as part of system bringup:

```bash
ros2 launch ibex_bringup control.launch.py
```

**Preconditions** — these are not steps, see
[power-on.md](../../../02-operations/power-on.md) for the sequence:

- The Kairos box is powered, so the P4S4 and the router are up
- The P4S4's ethernet cable is plugged into the **router**, not the OCU — see
  [kairos-p4s4-ocu.md](../hardware/kairos-p4s4-ocu.md)
- The VIM is armed, for the commands to reach an actuator
- A gamepad is connected and publishing `/joy`, for teleoperation

> TODO(verify): record which node each launch file starts, and whether
> `control.launch.py` and `bringup.launch.py` differ in more than convenience. Details
> belong in [launch-files.md](../../../05-reference/launch-files.md).

## Topics

Captured live with `shared_link_bridge_node` and `joy_node` running. All use Reliable
reliability and Volatile durability, with default deadline, lifespan, and liveliness.

| Topic | Type | Direction | Notes |
| --- | --- | --- | --- |
| `/gps_values` | `shared_link_bridge/msg/GpsValues` | pub | GPS returning from the P4S4. Consumed by `ibex_state` |
| `/kairos_values` | `shared_link_bridge/msg/KairosValues` | pub | Vehicle state from the P4S4 |
| `/outbound_msgs` | `std_msgs/msg/String` | pub | TODO(verify): what this carries |
| `/vehicle_control` | `shared_link_bridge/msg/VehicleControl` | sub | Commands into the bridge |
| `/joy` | `sensor_msgs/msg/Joy` | sub | Gamepad input. Published by `joy_node`, not this package |
| `/joy/set_feedback` | `sensor_msgs/msg/JoyFeedback` | — | Subscribed by `joy_node`. Rumble and LED feedback |

**This list is incomplete in one direction and explained in another.**
`/vehicle_control` had a subscriber and no publisher when captured, so
`controller_teleop.py` was not running.

`estop_beacon.py` **was** running and correctly shows no topics: it exposes a ROS 2
service rather than a topic, and sends its output over raw UDP. See
[Services](#services).

> TODO(verify): re-capture with `controller_teleop.py` running and record what it
> publishes.

## Services

| Service | Type | Node | Effect |
| --- | --- | --- | --- |
| `set_estop_state` | `shared_link_bridge/srv/SetEStopState` | `estop_beacon` | Sets the broadcast stop state. Sends immediately on change |

Request field is `state`, taking the integer value of:

| Value | State |
| --- | --- |
| 0 | `ESTOP` |
| 1 | `PAUSE` |
| 2 | `RUN` |

This is a real stop path, not a placeholder. Calling it with `0` broadcasts an e-stop
packet to the P4S4 within one beacon cycle.

> TODO(verify): confirm what the P4S4 does on receipt of each state, and in particular
> what `PAUSE` does that `ESTOP` does not. Nothing in this repository documents the
> receiving side's behaviour.

> TODO(verify): `/outbound_msgs` is a `std_msgs/String` from a protocol bridge. Establish
> what it carries — raw SharedLink frames, status text, or debug output. A String topic
> carrying structured data is worth knowing about before someone tries to parse it.

> TODO(verify): `/vehicle_control` is Reliable with an unreported queue depth. For a
> command topic that matters: a backed-up reliable queue delivers stale commands rather
> than dropping them. Confirm the depth and whether Reliable is the intended choice.

### Message definitions

The package defines its own messages — `GpsValues`, `KairosValues`, and `VehicleControl` —
**inside the package**, rather than in a separate interfaces package. Confirmed.

That differs from the rest of the repo, where `hyper_drive` pairs with
`hyper_drive_interfaces` and `spectrometer_drivers` with `spectrometer_interfaces`. The
consequence is concrete: `ibex_state` consumes `/gps_values`, so it has to depend on the
whole of `shared_link_bridge` — driver, teleop GUI and all — to get one message
definition.

> TODO(verify): decide whether to split the messages into a `shared_link_bridge_interfaces`
> package for consistency with the rest of the repo and to decouple `ibex_state` from the
> driver. This is a breaking change for anything that depends on the current names, so it
> is cheaper now than later.

## Parameters

| Parameter | Type | Default | Effect |
| --- | --- | --- | --- |
| Input scaler, joystick pressed | TODO(verify) | TODO(verify) | Scales teleop input |
| Input scaler, joystick released | TODO(verify) | TODO(verify) | Scales teleop input |

The two scalers are separately configurable but currently set equal.

> TODO(verify): record the actual parameter names, whether they are ROS parameters or
> constants in code, and what the two are for. A scaler that differs between pressed and
> released implies a deliberate behaviour that nobody has written down — and if it is a
> code constant rather than a parameter, changing it requires a rebuild, which belongs on
> this page.

> TODO(verify): record where the P4S4's address is configured. The bridge has to know to
> reach `192.168.200.220`; whether that is a parameter, a config file, or hardcoded
> determines what happens if the address changes.

## Dependencies

**Ibex packages**

- `ibex_bringup` — provides `control.launch.py`
- `ibex_state` depends on this package, not just its topics. It consumes `/gps_values`,
  whose type `shared_link_bridge/msg/GpsValues` is defined here rather than in a separate
  interfaces package — so the whole driver is a build dependency of state estimation. See
  [Message definitions](#message-definitions).

**External**

- `joy_node` for gamepad input
- TODO(verify): any SharedLink library or vendor dependency, and whether it is bundled

**Hardware that must be powered**

- Kairos box — the P4S4 and the router
- The VIM armed, for commands to reach an actuator
- A gamepad, for teleoperation

## Known issues & fixes

### The beacon initializes to RUN instead of ESTOP — unresolved

`estop_beacon.py` sets its initial state in the constructor:

```python
self._state = EStopState.RUN  # CHANGE TO ESTOP AFTER TESTING
```

The comment is the author's own. The intended default is `ESTOP`; the shipped default is
`RUN`.

**Consequence:** the moment the node starts, it begins broadcasting "run" to the P4S4 at
1 Hz, before anybody has asked for anything. The fail-safe default was deliberately
inverted for testing and never restored.

> TODO(verify): change it to `EStopState.ESTOP` and establish what has to happen at
> startup to move it to `RUN` deliberately. That is the fix, but it is not a one-line
> change in practice — whatever currently relies on the vehicle being live at launch will
> stop working, which is presumably why it was inverted in the first place.

### The beacon broadcasts to 255.255.255.255 — unresolved

```python
# ESTOP_BROADCAST_ADDR = '192.168.200.255'
ESTOP_BROADCAST_ADDR = '255.255.255.255'
```

The subnet-directed broadcast for the vehicle network is commented out in favour of the
global broadcast address.

**Consequence:** a global broadcast is sent out one interface, chosen by the routing
table. Volta has three interfaces, and the wireless one may hold the default route —
see [04-subsystems/README.md](../../README.md). If it does, **the stop beacon is going out
the wireless interface and never reaching the P4S4.**

> TODO(verify): this is the highest-priority item on this page. Confirm which interface
> the beacon actually leaves on, with `ip route` and a packet capture on port 7001. If it
> is not the `192.168.200.0/24` interface, the e-stop service does not work at all and
> nobody would know, because nothing acknowledges the packets.
>
> Restoring the commented-out subnet-directed address is the obvious fix.

### The packet contains a hardcoded asset name — unverified

The beacon packets embed the ASCII string `**DOZER_BASE**`.

That is an asset identifier, and IBEX is not a dozer. It looks like a value inherited from
Kairos example code or another vehicle.

> TODO(verify): establish whether the P4S4 filters on this identifier. If it does, and it
> does not match what our P4S4 expects, the beacon is being ignored regardless of whether
> it reaches the right network — the same failure as above, from a different cause, and
> equally silent.

### No acknowledgement, in either direction

The beacon is fire-and-forget. It sends three copies of the packet each cycle, at 1 Hz,
and never reads a reply.

**Consequence:** there is no way to tell from Volta whether the P4S4 is receiving the
beacon. All three failures above — wrong interface, wrong asset name, or a P4S4 that is
simply not listening — look identical from the sending side, which is to say they look
like nothing at all.

> TODO(verify): does the P4S4 stop on loss of the beacon? The 1 Hz transmission and the
> "Rule 1: transmit 1 per second" comment suggest the receiver expects a heartbeat and has
> a timeout. If it does, a correctly-working beacon is load-bearing and killing the node
> should stop the vehicle — which would be a useful property and is worth testing
> deliberately, on chocks. If it does not, the beacon is advisory only.

### Autonomous mode safety properties are unestablished

The deadman requirement and return-to-neutral behaviour are known for teleoperation
through `controller_teleop.py`. Whether they hold for any autonomous or path-playback path
is unknown — and that is the case where nobody's hand is on a deadman.

### The hardware interlocks are unaffected

None of the above changes how the vehicle is stopped in practice. The
[VIM](../hardware/vehicle-integration-module.md) is not addressable from ROS 2, so no
software fault can arm it or prevent it disarming. That is why the vehicle is safe to
operate while these are open. Cross-referenced from
[estop-chain.md](../../../01-safety/estop-chain.md).

### Autonomous mode safety properties are unestablished

The deadman requirement and return-to-neutral behaviour are known for teleoperation
through `controller_teleop.py`. Whether they hold for any autonomous or path-playback path
is unknown — and that is the case where nobody's hand is on a deadman.

## Understanding the software

Built on top of Kairos's existing SharedLink communication framework rather than
reimplementing the wire protocol from scratch.

### The stop beacon is out-of-band

`estop_beacon.py` does not go through the SharedLink bridge. It opens its own UDP socket
and broadcasts directly:

| | |
| --- | --- |
| Destination | `255.255.255.255` port 7001 — subnet-directed `192.168.200.255` is commented out |
| Local port | 7000 |
| Rate | 1 Hz, per a "Rule 1: transmit 1 per second" comment |
| Redundancy | Three identical packets per cycle |
| Payload | 40-byte fixed packets, one per state |

Three packet constants are defined, differing in only two places: bytes 12–13 flip between
`55 AA` and `AA 55`, and bytes 35–36 carry `10 01` for `PAUSE` and zeros otherwise. The
packets also embed the ASCII asset name `**DOZER_BASE**` and terminate with `] CR LF`.

That separation is deliberate and worth preserving — a stop channel that does not depend
on the main bridge node still works if the bridge is wedged.

### Other notes

**The GUI is text-based**, not a graphical window. It runs in the terminal that launched
the node, which means killing that terminal kills teleoperation.

**Frequency monitoring is the diagnostic.** The GUI reports publish rates for `/joy` and
`/kairos_values` separately, which distinguishes three failures that otherwise look
identical: a disconnected gamepad, a dead link to the P4S4, and a node that is running but
not processing.

> TODO(verify): `UDPConnection.UdpSender` is imported as a bare module rather than from a
> package path. Record where it comes from and whether it is part of this package, a
> sibling, or something on the `PYTHONPATH`.

## Related pages

- [Motion overview](../README.md) — the control path and why Shepherd is not in it
- [kairos-p4s4.md](../hardware/kairos-p4s4.md) — the hardware this commands
- [vehicle-integration-module.md](../hardware/vehicle-integration-module.md) — what gates
  the commands
- [actuators.md](../hardware/actuators.md) — the teleop mapping in mechanical terms
- [shepherd.md](shepherd.md) — the vendor alternative
- [estop-chain.md](../../../01-safety/estop-chain.md) — the inert e-stop as a known gap
- [running-the-system.md](../../../02-operations/running-the-system.md) — launching it
- [ros-graph.md](../../../05-reference/ros-graph.md) — system-wide topic view
