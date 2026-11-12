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

## Changes, November 2026

| Commit | What changed | Why |
| --- | --- | --- |
| Fix steering direction, match the ICD, add watchdog | Steering sign converted at the wire; commands clamped to ICD ranges; two-digit checksums; ICD frame layout (`N0\|D…`); explicit idempotent disconnect on shutdown; UDP sent before the ROS publish; unrecognised frames printed in full. Teleop: layout assert replaced by a warning; scales clamped | Stick right turned the wheels left; ~1–4% of frames had invalid checksums; disconnect frames were not reliably sent on Ctrl+C |
| Add two-stage stop and enable interlocks | Watchdog stops in two stages and latches; enable refused with throttle up; teleop deadman release, joystick loss and arming rules; `teleop_xterm` launch argument | The P4S4 freezes the actuators when motion is disabled, so disabling motion alone can leave the throttle open |
| Add read-only SharedLink query topic; fix connect list | `/sharedlink_query` and `/sharedlink_responses`; `premade_msgs.py` comma fix; `MW` deliberately not sent | Probing for steering encoder and motor current; `sys_thd` was being requested as `sys_thdMW` |

> TODO(verify): add the three commit hashes.

## Watchdog

Two-stage, because the P4S4 freezes the actuators when motion is disabled:

1. `/vehicle_control` silent for `command_timeout` while `veh_motion` is 1 → **throttle 0
   and brake `timeout_brake`, motion still enabled.** Logs `Watchdog stop stage 1`.
   Incoming commands ignored.
2. After `stop_hold_time` → motion and enable off. Logs `Watchdog stop stage 2`.
3. **Latched.** Commands with `veh_motion` 1 are ignored — logs `Watchdog stop is latched` —
   until one arrives with `veh_motion` 0, i.e. the deadman released.

**Enable interlock.** A `veh_motion` 0 → 1 transition is refused while `veh_throttle` is
above `enable_throttle_max`, whatever sends it. Logs `Motion enable refused`.

The bridge logs a `Safety:` line at startup with these values. Verified on chocks,
November 2026 — see [estop-chain.md](../../../01-safety/estop-chain.md).

## Conventions

**Steering sign.** The ROS side follows REP 103 (positive = left), matching the joystick and
Nav2. **Kairos uses positive = right.** The bridge negates `joy_steer` on the way out and
`steerang` on the way in. `/outbound_msgs` shows the Kairos convention.

**Clamping.** Every outbound value is clamped to its ICD range before sending:
`joy_steer` ±`steer_limit`, `veh_throttle` 0–`throttle_limit`, `veh_brake` 0–100,
`veh_shift` 0–3.

**Units** are on
[sharedlink-protocol.md](../../../05-reference/sharedlink-protocol.md).

## Probing shared variables

```bash
ros2 topic pub --once /sharedlink_query std_msgs/msg/String "{data: 'vehicle_bat'}"
ros2 topic pub -r 5 /sharedlink_query std_msgs/msg/String "{data: 'enc2,ang,Hb6'}"
ros2 topic echo /sharedlink_responses
```

Each name is sent as a bare named query, with no data field, **so the topic cannot write a
variable or send a pipe command.** Named replies are published but not printed, so polling
does not flood the console.

> **Query a known variable such as `vehicle_bat` first**, to prove the path works before
> trusting a zero.

## Known issues & fixes

### Steering inverted — fixed

Stick right turned the wheels left. The ROS joystick reports stick-right as negative, and
Kairos treats negative as a left turn. Fixed by `invert_steering`; confirmed on chocks.

### One-digit checksums — fixed

`get_checksum` used `:X`, so sums under 0x10 produced one digit — 4.4% and 0.8% of frames in
two bags. **Kairos ignores frames with a bad checksum.** Now `:02X`.

### Empty field after `N0` — fixed

Frames were sent as `N0||D…`. Kairos tolerated it, but the ICD layout is `N0|D…`.

### Disconnect not sent on shutdown — fixed

Disconnect lived in `__del__`, which Python does not guarantee to run on Ctrl+C, and the ROS
publish ran before the UDP send — so a failed publish during shutdown blocked it. `main()`
now calls `shutdown()` explicitly.

### `sys_thd` never requested — fixed

A missing comma in `premade_msgs.py` joined `"MW"` onto the vehicle → OCU list, so the last
variable was requested as `sys_thdMW` and `MW` was never sent. Fixed; `MW` is deliberately
left out, so the lists are still not saved on the P4S4.

### Last command held forever — fixed

With no command timeout, a dead teleop node left its last throttle and steering in force.
Replaced by the two-stage watchdog.

### `/vehicle_control` stall — open

In `steering_wheel_sweep_02`, `/vehicle_control` paused 291 ms while `/joy` never paused more
than 102 ms. Teleop publishes once per `/joy` message, so a teleop stall is a command stall.

> TODO(verify): cause. CPU load under NoMachine is one candidate.


### The gamepad does not work over NoMachine — fixed

**The worst property of this failure is that it is silent.** `joy_node` logs no error; it
simply never opens the device and `/joy` never publishes.

| Check | Local HDMI session | NoMachine session |
| --- | --- | --- |
| `joy_node` startup log | `Opened joystick: Logitech Gamepad F710` | **No line at all, and no error** |
| `controller_teleop.py` GUI | Updates with input | Appears, never updates |
| `ros2 topic hz /joy` | Publishing | **Nothing** |
| `ros2 topic hz /kairos_values` | ~10 Hz | ~10 Hz |
| `jstest /dev/input/js0` | Works | **Works** |

**`/kairos_values` still running rules out ROS networking. `jstest` working rules out the
controller and receiver.** Both are misleading, and disabling NoMachine's USB device
sharing does not help either.

**Cause: device permissions, and which device gets opened.**

`joy_node` in ROS 2 Humble reads the controller through **SDL2, which opens the evdev
device `/dev/input/eventN` — not `/dev/input/js0`.** The two have different permissions:

| Device | Mode | Owner:group | Readable by `river`? |
| --- | --- | --- | --- |
| `/dev/input/js0` | `crw-rw-r--` | `root:input` | **Yes** — world-readable |
| `/dev/input/event*` | `crw-rw----` | `root:input` | Only via the `input` group or a seat ACL |

On a **local HDMI session**, `systemd-logind`'s `uaccess` rule grants a per-user ACL on
input devices to the **active local seat**, so SDL can open the event device.

**A NoMachine session is not a local seat** — `loginctl` shows its sessions with no seat
assigned — so that ACL never applies. SDL cannot open the device, and `joy_node` waits
without complaining.

**That is also why `jstest` is misleading**: it reads `js0`, which anyone can read.

**Fix, installed:**

```bash
sudo usermod -aG input river
```

**The change takes effect only in a new login session.** Fully *terminate* the NoMachine
session — disconnecting is not enough — and log in again, or reboot. To test in an
existing shell, `newgrp input` first.

**This is a per-machine setup step**, not a one-off. See
[workstation-setup.md](../../../00-onboarding/workstation-setup.md).

> **Trade-off:** the `input` group can read every input device on Volta, keyboards and
> mice included. Acceptable on a dedicated vehicle computer, broader than strictly needed.
> A udev rule scoped to the F710 (`046d:c21f`/`c219`) would be narrower but needs a new
> rule per device. Switching to `joy_linux`, which reads `js0` directly, would avoid the
> permission question but changes the button and axis ordering and would need remapping.

### The F710's X/D switch must be on X

The gamepad has a physical **X / D** switch, and the two modes present entirely different
devices:

| Switch | Reports as | Buttons | Axes | Result |
| --- | --- | --- | --- | --- |
| **X** — XInput | `Logitech Gamepad F710` | 11 | 8 | **Correct** |
| D — DirectInput | `Logitech Cordless RumblePad 2` | 12 | 6 | **`controller_teleop.py` crashes** |

In D mode the node dies on:

```
AssertionError at  assert len(msg.buttons) == len(BUTTON) and len(msg.axes) == len(AXIS)
```

**The reported device name identifies the mode**, which makes the startup log the quickest
diagnosis. `Cordless RumblePad 2` means the switch is wrong.

**Keep the switch on X.**

> TODO(verify): replace that assertion with a throttled warning that skips the message, so
> a wrong layout degrades rather than killing the node.

> TODO(verify): **confirm teleop fails safe when joystick input stops.** If
> `controller_teleop` dies mid-session, the expectation is that the deadman handles it —
> releasing it returns actuators to neutral, and JAUS_IVN's "Park on Deadman Loss" option
> exists. But a crashed node is not the same as a released deadman, and nothing records
> which path actually applies. See [estop-chain.md](../../../01-safety/estop-chain.md) and
> [jaus-ivn.md](jaus-ivn.md).

### Debugging launch-file tracebacks

A node that crashes under `ros2 launch` can lose its traceback. Two ways to see it:

```python
Node(..., output='screen', emulate_tty=True)     # traceback in the launch terminal
```

Or wrap the node in `xterm -hold -e` to keep its own window open after it exits. The
first is tidier and is what the launch files should use.

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
