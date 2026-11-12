---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# controller_teleop

The gamepad teleoperation node in the `shared_link_bridge` package. Serves
[Motion](../README.md).

## Overview

`controller_teleop.py` reads `/joy` from `joy_node`, turns stick and button input into
`/vehicle_control` commands for [`shared_link_bridge`](shared-link-bridge.md), and shows a
terminal UI (TUI). It publishes one command per `/joy` message, so its rate follows
`joy_node` (about 17–20 Hz with autorepeat on).

It runs on Volta, with the F710 receiver plugged into Volta. The whole control path stays
local; nothing passes through a remote desktop session.

## Controls

The F710 must be in **X mode** (switch on the back). X mode reports 11 buttons and 8 axes,
which is what the node expects. D mode reports 12 buttons and 6 axes; the node then warns
and ignores the input.

| Control | Input | Notes |
| --- | --- | --- |
| Throttle / brake | Left stick, up / down | Up = throttle, down = brake |
| Steering | Right stick, left / right | ROS convention: left = positive |
| Deadman | Right bumper (RB), held | See Motion states |
| Throttle boost | Left stick pressed in (LJ) | Uses `throttle_scale_boosted` |
| Steering boost | Right stick pressed in (RJ) | Uses `steer_scale_boosted` |
| TUI navigation | D-pad left / right = page, up / down = item; A = select | |
| Gear | TUI Shift page: drive, neutral, reverse, parking | Sends `veh_shift` 3, 2, 1, 0 |
| Ping | Logitech button | |

Joystick axis convention (ROS `joy`): stick right and stick down are **negative**. Steering
is axis 3, throttle/brake axis 1.

Kairos's own Quick Start Guide uses a different layout (left stick steering, right stick
throttle, LB or RB enable). IBEX's teleop does not follow it.

## Motion states

| State | Meaning | TUI |
| --- | --- | --- |
| disabled | `veh_motion` 0. Throttle is always sent as 0 | `disabled` |
| ENABLED | Deadman held; sticks drive the vehicle | `ENABLED` |
| STOPPING | Stage 1 of a stop: throttle 0, brake `release_brake`, motion still on, steering held | `STOPPING` |

Rules:

- **Arming.** After teleop starts, the deadman must be seen released once before it can
  enable. A node restarted with the button held never enables. TUI hint:
  `release deadman, then press to enable`.
- **Enable interlock.** Motion enables only with the throttle stick at or below
  `enable_throttle_max`. Pressing with the throttle up waits until the stick returns. TUI
  hint: `release throttle to enable`.
- **Deadman release** starts the two-stage stop: STOPPING for `stop_hold_time`, then
  disabled. Pressing the deadman again during STOPPING, with the stick centred, resumes.
- **Joystick loss.** No valid `/joy` for `joy_timeout` while ENABLED (receiver unplugged,
  wrong layout) starts the stop from teleop.

Why two stages: the P4S4 freezes the actuators when motion is disabled. See
[estop-chain.md](../../../01-safety/estop-chain.md).

## Configuration

`config/controller_teleop.yaml`:

```yaml
scales:
  throttle_scale: 1000            # 0-1000 = 0-100.0 % throttle
  throttle_scale_boosted: 1000
  steer_scale: 400.0              # steering-wheel degrees; ICD max is 450
  steer_scale_boosted: 400.0
  brake_max: 100
safety:
  stop_hold_time: 1.0             # s; TODO(verify): value set from measured actuator times
  release_brake: 100              # brake applied while stopping
  enable_throttle_max: 0.05       # throttle stick fraction
  joy_timeout: 0.5                # s
```

Scales above the ICD maxima are clamped. `throttle_scale: 1000` gives full throttle at full
stick without boost; consider a lower default for testing, with boost for more.

Steering stays at 400 until full lock is checked: if the wheels already reach full lock
before 400, commanding 450 only drives the actuator into the stop.

## Running

`bringup.launch.py` starts teleop in an `xterm` by default. For terminal-only sessions (SSH,
tmux), and for the watchdog tests, run it separately:

```bash
ros2 launch shared_link_bridge bringup.launch.py teleop_xterm:=false   # pane 1
ros2 run shared_link_bridge controller_teleop.py                       # pane 2
```

The TUI is curses-based and needs a real terminal, so it can't run inside `ros2 launch`
without the `xterm`.

## Known issues & fixes

### Joystick not readable over NoMachine — fixed

`joy_node` reads the F710 through SDL2, which opens `/dev/input/eventN` (root:input, mode
660), not `/dev/input/js0`. A NoMachine session isn't the active local seat, so the logind
access rule didn't apply. Fixed by adding the account that runs bringup to the `input`
group (`sudo usermod -aG input river`, then log in again). Repeat on any new Ibex computer.

### D mode crashed teleop — fixed

An `assert` on the button and axis counts killed the node. Now a throttled warning, and the
input is ignored.

### GUI lag over NoMachine

The lag seen between pressing the controller and the TUI updating is the remote-desktop
stream, not the control path. For lower latency use SSH and tmux instead of NoMachine, or
watch topics from a laptop over DDS. TODO(verify): Volta CPU load while recording,
mapping and streaming the desktop at once.

### Wireless receiver placement

USB 3 ports and hubs radiate 2.4 GHz noise that can cause input lag or dropouts. If the F710
misbehaves, move the receiver onto a short USB 2 extension away from the hub.

## Related pages

- [shared-link-bridge.md](shared-link-bridge.md) — the bridge it commands
- [actuators.md](../hardware/actuators.md) — what the commands move
- [estop-chain.md](../../../01-safety/estop-chain.md) — stopping behaviour
