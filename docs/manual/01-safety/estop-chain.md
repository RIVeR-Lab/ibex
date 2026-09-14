---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Stop controls and the e-stop chain

> **This page is only partly verified.** The controls listed below are known to exist and
> the two-gate model is confirmed. What each individual control cuts has not been
> measured. Do not rely on any row marked `TODO(verify)` to decide whether something is
> safe to touch.
>
> The verification procedure is at the bottom of this page.

IBEX has fourteen stop and power controls. They are not equivalent, most are not emergency
stops, and cutting one does not imply the others are cut. This page exists so that nobody
has to guess.

## Two hazards, two different stops

The single most important thing on this page. IBEX presents **two independent hazards**,
and the control that stops one does not stop the other.

| Hazard | Stopped by | **Not** stopped by |
| --- | --- | --- |
| **The vehicle driving** — engine-driven motion | Key to `O`; or disarming at the VIM; or cutting Kairos box power | — |
| **An actuator moving** — the steering, brake, throttle, or transmission driven under command | VIM pause; VIM e-stop; or cutting Kairos box power | **The key.** Actuators move with the engine off |

**Turning the key off does not make the vehicle safe to work on.** The engine stops and
the vehicle cannot drive, but the P4S4 actuators remain powered and can still move the
steering wheel, the brake, the throttle, and the transmission. A person with their hands
on a linkage, under the dash, or at the steering column is exposed regardless of the key.

Before working anywhere near an actuator or its linkage:

1. Switch the VIM to **pause**, or put any one of its four controls into its off position.
2. Confirm the VIM LEDs show not enabled. This is what distinguishes unpowered from merely
   uncommanded.

In an emergency, which control you reach for depends on what is happening:

- **The vehicle is moving** → the key. It closes the gate that governs driving.
- **An actuator is moving and someone is exposed to it** → VIM pause or the VIM e-stop.
  The key will not help.

Arming is the last step of [power-on.md](../02-operations/power-on.md) for this reason:
the actuators are live from the moment the VIM is released, independently of the engine.

## What this page is for

Three different questions with different answers:

1. **"How do I stop the vehicle right now?"** — the emergency answer.
2. **"Is it safe to put my hands on this component?"** — the maintenance answer, which
   needs to know what is still energized.
3. **"How do I shut down properly?"** — that is
   [power-off.md](../02-operations/power-off.md), not this page.

This page answers 1 and 2.

## Control inventory

Every control is listed, including ones that are not emergency stops, because a person
looking for a way to stop the vehicle will reach for whichever is nearest.

### Vehicle integration module

The controls closest to the actuators. **These are the only controls that stop actuator
motion.** Reach for these first when someone is exposed to a linkage.

| # | Control | Type | Cuts | Does not cut |
| --- | --- | --- | --- | --- |
| 1 | VIM e-stop | Latching | Actuator power | Engine, payload power |
| 2 | Run / pause switch | Two-position, **non-latching** — click to pause, click back to run. No twist to reset | Actuator power | Engine, payload power |
| 3 | On / off switch | Two-position, on the side of the unit | Actuator power | Engine, payload power |
| 4 | Manual / auto switch | Two-position, on the side of the unit. `manual` is the disarmed position | Actuator power | Engine, payload power |

**All four are in series for arming, which means any one of them disarms.** The actuators
are powered only with the e-stop released, the run/pause switch at run, the on/off switch
at on, and the manual/auto switch at auto. Putting any single one of those four into its
off position removes actuator power.

That redundancy is the useful property: you do not have to remember which control is the
"right" one. The nearest one works.

### Confirming the actuators are unpowered

**The VIM carries LED indicators showing whether it is enabled.** Check them. They are the
positive confirmation that the actuators are unpowered rather than merely uncommanded —
which is the distinction that protects anyone with their hands on a linkage.

Two independent checks before working near an actuator:

1. At least one of the four controls above is in its off position.
2. The VIM LEDs show not enabled.

> TODO(verify): record which LED means what, and its colour and location on the unit. "The
> LEDs show whether it is enabled" is only followable by someone who already knows which
> LED to read.

**The run/pause switch is the preferred disarm.** It stays where you put it, needs no twist
or key to reset, and clicking back to run restores the armed state directly — so it does
not incur the 60-second thermistor wait that cutting power does. Use it for planned work
and for any non-emergency stop. It is the stop people will actually use rather than
hesitate over.

> TODO(verify): record what the `manual` position of the manual/auto switch does beyond
> removing actuator power — whether it also hands control back to the driver's mechanical
> linkages, and whether that is the intended route into manual driving.

### Main power chain

| # | Control | Location | Type | Cuts | Does not cut |
| --- | --- | --- | --- | --- | --- |
| 5 | Main e-stop | Kairos power box | Latching, must be unlocked to restore | TODO(verify) | Engine |
| 6 | Main power button | Kairos power box | Momentary, red LED | TODO(verify) | Engine |
| 7 | Compute and Sensing box power button | Compute and Sensing box | Momentary, red LED | TODO(verify) | P4S4, engine |
| 8 | AC adapter switch | TODO(verify) | Switch, three LEDs when live | TODO(verify) | P4S4, engine |
| 9 | System battery power button | Rear of vehicle | Switch | All payload power | Engine |

### Vehicle

| # | Control | Type | Cuts | Does not cut |
| --- | --- | --- | --- | --- |
| 10 | Vehicle key | Key, `O` = off | Engine, and vehicle motion | Payload power. **Actuator motion — steering, brake, throttle, and transmission still move with the key off** |
| 11 | Parking brake and park gear | Mechanical | Nothing electrical | Everything electrical |
| 12 | Wheel chocks | Mechanical restraint | Nothing | Everything |

### Software and operator

| # | Control | Type | Cuts | Does not cut |
| --- | --- | --- | --- | --- |
| 13 | Deadman | Gamepad right bumper, held-to-enable | Commanded motion. **Actuators return to neutral when it is released** | Actuator power |
| 14 | Insta360 power button | Camera body, side | That camera only | Everything else |

**The deadman is a required enable, not merely a stop.** The actuators do not move on
their own — an armed P4S4 with a controller running and nobody holding the deadman sits
still. Releasing it returns the actuators to neutral rather than leaving them wherever
they were last commanded, so a released deadman is a recovering state and not just a
frozen one.

This is why the order in [running-the-system.md](../02-operations/running-the-system.md) is
safe: arming the P4S4 before starting the controller cannot produce motion, because motion
additionally requires a held deadman.

> TODO(verify): the deadman requirement and the return-to-neutral behaviour are
> established for teleoperation. Whether autonomous or path-playback modes also require a
> held deadman is currently unknown. If they do not, neither protection applies to
> autonomous operation and this page must say so.

### What commands the actuators

Commands reach the P4S4 from `shared_link_bridge` running on **Volta**. That package
implements the SharedLink protocol directly and is used **in place of** the vendor's
Shepherd application.

Shepherd runs on the OCU, not on Volta, and is not part of the current control path. It is
therefore not listed as a control on this page.

**Not stop controls, despite appearances:**

- The seatbelt alarm. It is an indicator — see [README.md](README.md).
- Shutting down Volta. It stops software; it de-energizes nothing.
- **`Ctrl-C` on a launch file.** It stops publishing. With the deadman released the
  actuators return to neutral, but stopping the node that commands them is not the same as
  removing their power — see [Two hazards](#two-hazards-two-different-stops).

> TODO(verify): confirm this list is complete. Is there a stop control at the OCU or on a
> tether, and does the F17 joystick controller have one?

## The chain

These controls are in series. Cutting an upstream control makes downstream controls
irrelevant; cutting a downstream one leaves everything upstream live.

```
System battery (9)
  └─ Main e-stop (5) ─ Main power button (6)
       ├─ P4S4 ─ VIM (1,2,3,4) ─ actuators
       ├─ AC adapter (8)
       │    ├─ SICK picoScan 150
       │    └─ Router
       └─ Compute and Sensing box (7)
            ├─ Volta
            │    ├─ Alvium RGB camera      [USB-powered from Volta]
            │    └─ Point spectrometers    [USB-powered from Volta]
            ├─ Ouster OS1-64 (+ control box, green LED inside the box)
            └─ Hyperspectral cameras

Vehicle key (10) ─ Engine        [independent of everything above]
Insta360 (16)                    [self-powered, independent]
```

> TODO(verify): this tree is inferred from the power-on order plus the USB and enclosure
> relationships, not from tracing the harness. Confirm it before anyone relies on it. The
> open questions are whether the main e-stop is genuinely upstream of both the AC adapter
> and the Compute and Sensing box, and whether the Kairos actuators sit on the Kairos box
> or on a separate rail.

Note what the tree implies: **cutting the Compute and Sensing box kills Volta, which kills
the Alvium and both spectrometers.** One button takes out four devices, and three of them
have no indicator of their own.

## Known gaps

Established rather than inferred. Each is a way the system behaves differently from how a
reasonable person would expect.

### The system may not be back-drivable

When the P4S4 is engaged, its actuators have locked the throttle, the steering wheel, the
brake, and the transmission on separate occasions, making it difficult or impossible to
return to manual control.

**Consequence:** taking the wheel is not a guaranteed override. Do not plan around it, and
do not tell a new person that manual takeover is their fallback. Use the key.

The throttle case left the throttle held open, producing the high-RPM-on-startup behaviour
seen early in vehicle testing.

Mechanism and current status:
[kairos-p4s4.md](../04-subsystems/motion/hardware/kairos-p4s4.md).

> TODO(verify): whether this is still current behaviour or has been addressed. The source
> note does not say, and the difference matters enormously.

### The software e-stop state is hardcoded

`estop_beacon.py` in `shared_link_bridge` publishes the emergency stop state and is
hardcoded to `EStopState.RUN` at startup.

**Consequence:** that channel reports "running" regardless of actual state. Nothing in
software can currently assert a stop through it.

Details: [shared-link-bridge.md](../04-subsystems/motion/software/shared-link-bridge.md).

> TODO(verify): whether anything subscribes to it. If nothing does, the practical risk is
> lower than it looks — but the channel still cannot be used.

### The key does not disarm the actuators

Turning the key to `O` stops the engine and prevents the vehicle from driving. It leaves
the P4S4 actuators powered, and they can still move the steering, brake, throttle, and
transmission.

**Consequence:** "engine off" is not a safe state for work on or near a linkage. Anyone
reasoning from experience with conventional vehicles will assume it is. Disarm at the VIM
first — see [Two hazards](#two-hazards-two-different-stops).

This also means an unattended vehicle with the key removed but the VIM armed is not
inert.

### No single control cuts everything

The SOP requires an emergency stop that immediately cuts power to all systems. No control
on IBEX is confirmed to do that. The engine is outside the reach of every electrical
control, and the actuators are outside the reach of the key.

**Consequence:** stopping IBEX completely takes two actions — the key, and a disarm at the
VIM or a cut at the Kairos box. Neither alone is sufficient, and which one to reach for
first depends on which hazard is active.

This is a compliance gap as well as a safety one. Raise it with the lab manager rather than
only recording it here.

### Restoring power has a mandatory wait

After cutting power the system must stay off for 60 seconds before being re-energized, so
the NTC thermistors return to room temperature and can limit inrush current again.

**Consequence:** an emergency stop followed by an immediate restart risks the power
circuit. This is equipment damage rather than injury, but it constrains recovery — which
is why a non-latching disarm at the VIM is worth establishing. See
[power-on.md](../02-operations/power-on.md).

## Verifying this page

Two people, a powered vehicle on chocks, and an afternoon. Do it with the electrical owner
in [ownership.md](../00-onboarding/ownership.md).

**Disarm at the VIM before any hands go near an actuator or linkage. The engine being off is not sufficient.**

For each control in the inventory:

1. Bring the system up per [power-on.md](../02-operations/power-on.md) and confirm every
   subsystem is live.
2. Actuate the single control under test. Change nothing else.
3. Record what went dark: LEDs, Volta, each sensor, the router, the actuators. Remember
   that the Alvium and the spectrometers have no indicators of their own and must be
   checked from a terminal.
4. Record what stayed live. This column matters more than the first.
5. Confirm whether restoring that one control brings everything back, or whether a
   downstream control must also be re-actuated.
6. Wait 60 seconds before re-energizing.

Then, separately and with particular care. **The actuators move with the engine off, so
disarm at the VIM before any hands go near a linkage.**

- With the vehicle chocked, determine whether the P4S4 holds its last commanded actuator
  position when ROS 2 commands stop, when the VIM is switched to pause, and when the VIM
  e-stop is thrown. Releasing the deadman is known to return the actuators to neutral;
  these three cases are not established and may differ from each other.
- Determine whether each actuator can be back-driven by hand in each of those states.
- Record the VIM LED states and what each indicates, so the confirmation check above can
  be followed by someone who has not seen the unit before.

Record results in the inventory, set `last-verified`, and narrow the banner at the top of
this page.

## Related

- [README.md](README.md) — the safety rules this page supports
- [checklists.md](checklists.md) — pre-run verification that stop controls work
- [power-on.md](../02-operations/power-on.md) and
  [power-off.md](../02-operations/power-off.md) — the sequences
- [04-subsystems/power/](../04-subsystems/power/) — rail design and distribution
- [kairos-p4s4.md](../04-subsystems/motion/hardware/kairos-p4s4.md) — actuator behaviour
- [sop.md](sop.md) — the emergency stop requirement
