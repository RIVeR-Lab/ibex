---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Stop controls and the e-stop chain

> **This page is not yet verified.** The controls listed below are known to exist. What
> each one actually cuts has not been measured. Do not rely on any row marked
> `TODO(verify)` to decide whether something is safe to touch.
>
> Verifying this page is the highest-value safety task outstanding on IBEX. The procedure
> is at the bottom.

IBEX has several independent stop and power controls. They are not equivalent, they are
not all emergency stops, and cutting one does not imply the others are cut. This page
exists so that nobody has to guess.

The SOP requires a functional emergency stop that immediately cuts power to all systems.
Whether any single control on IBEX does that is currently unestablished — see
[Known gaps](#known-gaps).

## What this page is for

Three different questions, and they have different answers:

1. **"How do I stop the vehicle right now?"** — the emergency answer.
2. **"Is it safe to put my hands on this component?"** — the maintenance answer. Requires
   knowing what is still energized.
3. **"How do I shut the system down properly?"** — the procedural answer, which is
   [power-off.md](../02-operations/power-off.md), not this page.

This page answers 1 and 2. It does not contain the shutdown sequence.

## Control inventory

Every control is listed, including ones that are not emergency stops, because a person
looking for a way to stop the vehicle will reach for whichever is nearest.

| # | Control | Location | Type | Cuts | Does not cut |
| --- | --- | --- | --- | --- | --- |
| 1 | Main e-stop | Kairos power box | Latching, must be unlocked to restore power | TODO(verify) | TODO(verify) |
| 2 | Main power button | Kairos power box | Momentary, red LED indicates state | TODO(verify) | TODO(verify) |
| 3 | System battery power button | Rear of vehicle | Switch | TODO(verify) | TODO(verify) |
| 4 | Power 2.0 button | HyperDrive 2.0 box | Momentary, red LED indicates state | TODO(verify) | TODO(verify) |
| 5 | AC adapter switch | TODO(verify) | Switch | TODO(verify) | TODO(verify) |
| 6 | Vehicle key | Ignition | Key, `O` = off | Engine | All payload power |
| 7 | Parking brake and park gear | Cab | Mechanical | Nothing electrical | Everything electrical |
| 8 | Wheel chocks | At the rear wheels | Mechanical restraint | Nothing | Everything |
| 9 | Deadman | Gamepad right bumper | Held-to-enable | Commanded motion while released | TODO(verify): whether an already-commanded actuator holds position or returns to neutral |
| 10 | Shepherd Action buttons | OCU | Software mode control | Teleoperation mode | Power to anything |
| 11 | Shepherd Engine buttons | OCU | Software | Engine enable and start | TODO(verify) |
| 12 | Insta360 power button | Camera body, side | Switch | That camera only | Everything else |

TODO(verify): items 5 and 12 aside, confirm this list is complete. In particular — is there
a stop control at the OCU or on a tether, and does the F17 joystick controller have one?

**Not stop controls, despite appearances:**

- The seatbelt alarm. It is an indicator. See [README.md](README.md).
- Shutting down Volta. It stops software; it does not de-energize anything.
- `Ctrl-C` on a launch file. Stops publishing. Whether the P4S4 holds its last commanded
  position when commands stop is `TODO(verify)`, and it is the single most important
  unknown on this page.

## The chain

Order matters, because these controls are in series. Cutting an upstream control makes
downstream controls irrelevant; cutting a downstream one leaves everything upstream live.

Inferred from the power-on sequence in [power-on.md](../02-operations/power-on.md):

```
System battery (3)
  └─ Main e-stop (1) ─ Main power button (2)
       ├─ AC adapter (5)
       │    ├─ SICK lidar
       │    └─ Router
       └─ Power 2.0 (4)
            ├─ Volta
            ├─ Ouster OS1-64
            └─ Hyperspectral systems

Vehicle key (6) ─ Engine          [independent of everything above]
Insta360 (12)                     [self-powered, independent]
```

> TODO(verify): this tree is inferred from the order of the power-on steps, not from
> tracing the wiring. Confirm it against the actual harness before anyone relies on it.
> The critical questions are whether the main e-stop is genuinely upstream of both the AC
> adapter and the Power 2.0 branch, and whether the Kairos actuators are on the Kairos box
> or on a separate rail.

The engine is independent. **No electrical stop control shuts off the engine.** Only the
key does.

## Known gaps

These are established, not inferred. Each one is a way the system can behave differently
from how a reasonable person would expect.

### The system may not be back-drivable

When the P4S4 is engaged, its actuators have locked the throttle, the steering wheel, the
brake, and the transmission on separate occasions, making it difficult or impossible to
return to manual control.

**Consequence:** taking the wheel is not a guaranteed way to override the system. Do not
plan around it, and do not tell a new person that manual takeover is their fallback.

The throttle case has been observed to leave the throttle held open, which produced the
high-RPM-on-startup behaviour seen early in vehicle testing.

Mechanism and current status: [kairos-p4s4.md](../04-subsystems/motion/hardware/kairos-p4s4.md).

> TODO(verify): whether this is still the vehicle's current behaviour or has been
> addressed. The source note does not say, and the difference matters enormously.

### The software e-stop state is hardcoded

`estop_beacon.py` in `shared_link_bridge` publishes the emergency stop state, and it is
hardcoded to `EStopState.RUN` at startup.

**Consequence:** the software e-stop channel reports "running" regardless of actual state.
Nothing in software is currently capable of asserting a stop through that channel.

Details: [shared-link-bridge.md](../04-subsystems/motion/software/shared-link-bridge.md).

> TODO(verify): whether any consumer acts on this topic. If nothing subscribes, the
> practical risk is lower than it appears — but the channel still cannot be used.

### No confirmed single stop for everything

The SOP requires an emergency stop that immediately cuts power to all systems. The main
e-stop on the Kairos power box is the candidate, but its actual coverage is unverified,
and the engine is definitely outside it.

**Consequence:** in an emergency, one action may not be enough. Until this is resolved,
assume stopping IBEX completely requires both the main e-stop and the key.

### Restoring power has a mandatory wait

After cutting power, the system must stay off for 60 seconds before being re-energized, so
the NTC thermistors return to room temperature and can limit inrush current again.

**Consequence:** an emergency stop followed by an immediate restart puts the electrical
system at risk. This is an equipment concern, not a personnel one, but it constrains
emergency recovery. See [power-off.md](../02-operations/power-off.md).

## Verifying this page

This needs two people, a powered vehicle on chocks with the engine off, and an afternoon.
It should be done by or with the electrical owner in
[ownership.md](../00-onboarding/ownership.md).

For each control in the inventory:

1. Bring the system up per [power-on.md](../02-operations/power-on.md) and confirm every
   subsystem is live.
2. Actuate the single control under test. Change nothing else.
3. Record what went dark: LEDs, Volta, each sensor, the router, the actuators.
4. Record what stayed live. This column matters more than the first one.
5. Confirm whether restoring that one control brings everything back, or whether a
   downstream control also has to be re-actuated.
6. Wait 60 seconds before re-energizing.

Then, separately and with particular care:

- With the engine off and the vehicle chocked, determine whether the P4S4 holds its last
  commanded actuator position when ROS 2 commands stop, when the deadman is released, and
  when the main e-stop is thrown. These three cases may differ.
- Determine whether each actuator can be back-driven by hand in each of those states.

Record the results in the inventory table, set `last-verified`, and remove the banner at
the top of this page.

## Related

- [README.md](README.md) — the safety rules this page supports
- [checklists.md](checklists.md) — pre-run verification that stop controls work
- [power-on.md](../02-operations/power-on.md) and
  [power-off.md](../02-operations/power-off.md) — the sequences
- [04-subsystems/power/](../04-subsystems/power/) — rail design and distribution
- [kairos-p4s4.md](../04-subsystems/motion/hardware/kairos-p4s4.md) — actuator behaviour
- [sop.md](sop.md) — the emergency stop requirement
