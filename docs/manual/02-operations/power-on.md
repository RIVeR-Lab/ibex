---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Power on

Energizes the research payload: compute, sensors, and the drive-by-wire system.

**This page does not cover:**

- Starting the engine. The engine runs only to move the vehicle into or out of the
  building — see [sop.md](../01-safety/sop.md).
- Bringing up software. That is
  [running-the-system.md](running-the-system.md).

Do not skip steps and do not reorder them. Several steps have no visible feedback if you
get them wrong.

## Before you begin

- [ ] Pre-run checklist complete — see [checklists.md](../01-safety/checklists.md)
- [ ] Wheel chocks in place at the rear wheels
- [ ] Vehicle key in the `O` (off) position
- [ ] Everyone present knows where the stop controls are — see
      [estop-chain.md](../01-safety/estop-chain.md)

**If the system was powered off less than 60 seconds ago, wait.** The NTC thermistors must
return to room temperature before they can limit inrush current again. Re-energizing early
risks damage to the power circuit. This is the only mandatory wait in the sequence.

Key access is governed by the SOP. If you do not have a key, ask the vehicle access owner
in [ownership.md](../00-onboarding/ownership.md).

## Sequence

1. Press the power button on the **system battery** at the rear of the vehicle.
   - The button illuminates green. If it does not, stop and check the battery charge
     state.

2. Unlock the **main e-stop** on the Kairos power box.

3. Press the **main power button** on the Kairos power box.
   - The red LED illuminates. If it does not, stop.

   The P4S4 is now powered but not armed. Arming is step 9.

4. Switch on the **AC adapter**.

5. Confirm all three are powered before continuing:

   | Item | How to confirm |
   | --- | --- |
   | AC adapter | The power switch is flipped and the three LEDs on the far right of the adapter are lit |
   | Router | Green LEDs visible through the clear lid of its weatherproof enclosure |
   | SICK picoScan 150 | Confirm the device is reachable. TODO(verify): add the command. |

6. Press the **power button** on the **Compute and Sensing box**.
   - The red LED illuminates. If it does not, stop.

7. Confirm all three are powered before continuing:

   | Item | How to confirm |
   | --- | --- |
   | Volta | Attach a monitor over HDMI, or SSH in. Volta is set in BIOS to power on as soon as it receives power, so if the box is live Volta should be coming up on its own |
   | Ouster OS1-64 | The Ouster control box sits inside the Compute and Sensing box and lights a green LED when powered. Then confirm the sensor is reachable. TODO(verify): add the command. The sensor also becomes warm to the touch once it is spinning |
   | Hyperspectral system | Confirm the devices enumerate from a terminal on Volta. TODO(verify): add the command. |

   The Alvium RGB camera and the two point spectrometers need no action here. They are
   USB-connected to Volta and draw power from it, so they come up with Volta. No cables
   need connecting — every USB device stays plugged in between sessions.

   > TODO(verify): the source describes the hyperspectral system as three cameras and two
   > point spectrometers. If the Alvium is one of those three, it is USB-powered off Volta
   > rather than fed by the box — so the three do not share a power path and should not be
   > confirmed as one item. Establish which cameras the box actually feeds.

8. Power the external sensors. The Insta360's power button is on the side of the camera
   body.

9. **Arm the P4S4** — last, once everything above is up and software is ready to command
   it:
   1. Release the e-stop on the **vehicle integration module**.
   2. Switch the module from **pause** to **run**.
   3. Set the side **on/off** switch to **on**.
   4. Set the side **manual/auto** switch to **auto**.
   5. Confirm the VIM LEDs show enabled.

   All four controls are in series, so the actuators stay unpowered until every one of them
   is in position.

   > TODO(verify): record the position and colour of the VIM LEDs, and which one indicates
   > enabled.

The payload is now on and the P4S4 is armed.

**The armed P4S4 cannot drive the vehicle until the engine is running — but its actuators
are live now.** With the engine off the vehicle will not move, yet the steering, brake,
throttle, and transmission can still be driven under command. Arming is the last step so
the actuators are never live while compute is still coming up.

Commanded motion additionally requires the deadman to be held, so arming does not by
itself put anything in motion. That does not make an armed vehicle safe to work on — see
[estop-chain.md](../01-safety/estop-chain.md).

To disarm, switch the vehicle integration module to **pause**. The switch is non-latching,
so clicking it back to run re-arms without a power cycle. See
[estop-chain.md](../01-safety/estop-chain.md).

## Naming

The second box is the **Compute and Sensing box**. Its control is the **power button**.

The source notes called it the "hyperspectral 2.0 box," the "HyperDrive 2.0 Power Box,"
and "Power 2," and its button both "power 2" and "Power 2.0." All of those name the box
after one of its loads, which sends people looking in the wrong place — it also feeds
Volta, the compute for the entire vehicle, and the SICK lidar.

> TODO(verify): apply this name in three more places — [power-off.md](power-off.md),
> [04-subsystems/power/](../04-subsystems/power/), and the physical label on the box. If
> the SOP's Appendix A names it differently, revise the appendix rather than reintroducing
> a second name.

## If something does not power up

Stop the sequence. Do not continue past a failed step and do not work around it.

- A box whose LED does not illuminate: check the control upstream of it. The boxes are in
  series — see [estop-chain.md](../01-safety/estop-chain.md).
- Nothing at all: check the system battery charge state, then the main e-stop is actually
  unlocked.
- Actuators unresponsive with the Kairos box lit: check the vehicle integration module —
  its e-stop released, set to run rather than pause, and both side switches in position.
- One sensor missing while its box is lit: that is a device or cabling problem rather than a
  power problem. Go to that component's hardware page under
  [04-subsystems/](../04-subsystems/).
- Alvium or a spectrometer missing: check Volta first. They are USB-powered from it, so a
  Volta that has not booted looks like several dead sensors.
- The base vehicle will not start: that is a separate tree — see
  [troubleshooting.md](../03-base-vehicle/troubleshooting.md).

If you power down to retry, wait 60 seconds before powering on again.

## Related

- [power-off.md](power-off.md) — the shutdown sequence
- [running-the-system.md](running-the-system.md) — software bringup, after this completes
- [checklists.md](../01-safety/checklists.md) — what to confirm before starting
- [estop-chain.md](../01-safety/estop-chain.md) — what each control cuts
- [04-subsystems/power/](../04-subsystems/power/) — why the rails are split this way
