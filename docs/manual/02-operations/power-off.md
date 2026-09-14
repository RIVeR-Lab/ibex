---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Power off

De-energizes the research payload and disarms the drive-by-wire system.

This is the reverse of [power-on.md](power-on.md). The P4S4 is armed last on the way up and
disarmed first on the way down, so the actuators are never live while nothing is commanding
them.

**This is not the emergency procedure.** To stop the vehicle or an actuator right now, see
[estop-chain.md](../01-safety/estop-chain.md).

## Before you begin

- **Offload anything you need from Volta first.** Once Volta is down the bags are
  unreachable until the next power-on. See
  [data-collection.md](data-collection.md).
- Know that restarting has a mandatory 60-second wait — see [power-on.md](power-on.md). If
  you are power cycling rather than shutting down for the day, plan for it.

## Sequence

1. **Disarm the P4S4** at the vehicle integration module:
   1. Switch it from **run** to **pause**.
   2. Engage the VIM e-stop.
   3. Set the side **on/off** switch to **off**.
   4. Confirm the VIM LEDs show not enabled.

2. Turn the vehicle key to **`O`** (off) if the engine is running.

3. **Stop all running software.** Kill every node and command so that nothing is capturing
   or streaming. The procedure is in
   [running-the-system.md](running-the-system.md) — stop the bag, `Ctrl-C` each launch in
   reverse order, then confirm `ros2 node list` comes back empty.
   - This is the step that makes the rest of the shutdown safe. Powering a camera down
     mid-capture risks damaging it, and the same applies to the Ouster — once the code has
     stopped, cutting power is fine.

   No cables need disconnecting. The SWIR camera stays plugged in, as do the other cameras
   and both point spectrometers. The IMEC manual's instruction to remove the USB connection
   before de-powering applies only if the camera is being physically disconnected for some
   other reason, which is not part of normal shutdown.

4. **Shut Volta down in software** before cutting its power. Volta is set in BIOS to power
   on as soon as it receives power, so it never shuts down on its own — pulling the box
   power on a running Volta is an unclean shutdown.

   The **Ximea VNIR camera, the Alvium RGB camera, and the Insta360** are USB-powered from
   Volta, so shutting it down powers them off. They need no separate action. The IMEC SWIR
   camera and both point spectrometers are fed by the Compute and Sensing box instead and
   go dark at step 6.

5. Turn off the **Insta360** camera.

6. Press the **power button** on the **Compute and Sensing box**.
   - The red LED extinguishes.

7. Switch off the **AC adapter**.

8. Press the **main power button** on the **Kairos box**, then engage the **main e-stop**.

9. Press the power button on the **system battery** at the rear of the vehicle.
   - Its green illumination goes out.

## Verify everything is off

| Item | How to confirm |
| --- | --- |
| Vehicle integration module | LEDs show not enabled |
| Compute and Sensing box | Red LED dark |
| Kairos box | Red LED dark, main e-stop engaged |
| AC adapter | Three LEDs on the far right dark, switch off |
| Monitor | Dark — it is fed by the AC adapter |
| Router | Green LEDs dark through the enclosure lid. It is on the Kairos box, so it goes dark at step 8, not step 7 |
| System battery | The power button's green illumination is out |
| Insta360 | Powered off at the camera body |
| Volta | No independent indicator — see below |

> **Volta has no shutdown confirmation.** There is currently no way to tell a fully
> shut-down Volta from one still mid-shutdown. In practice the only confirmation is that
> the Compute and Sensing box has been switched off afterwards, which is circular: it
> confirms power was removed, not that the shutdown completed cleanly first.
>
> TODO(verify): establish a confirmation method. Options worth testing — a chassis or
> power LED on the NUC itself, monitoring the HDMI output to a display, or watching for
> the SSH port to close from another machine. Until one exists, an unclean shutdown is
> undetectable and will only show up later as a corrupted bag or a filesystem error.

## Then

Run the post-run checklist — [checklists.md](../01-safety/checklists.md). Chocking the
wheels, setting the parking brake, and deciding whether the batteries need charging live
there. Do not skip them; shutdown is not finished until the checklist is.

## If something stays on

- A box whose LED stays lit after its button: check whether a downstream control is holding
  it, then check the control upstream. The boxes are in series — see
  [estop-chain.md](../01-safety/estop-chain.md).
- A sensor still live after its box is dark: it is fed from somewhere other than where you
  think. Stop and establish what, before assuming the vehicle is de-energized.
- Volta still running after the Compute and Sensing box is off: it is on a different supply
  than assumed. Treat this as a wiring problem, not an operational one.
- The VIM still showing enabled: do not work on the vehicle. Any one of its four controls
  should disarm it, so an armed VIM with a control in the off position is a fault.

## Related

- [power-on.md](power-on.md) — the startup sequence and the 60-second wait
- [checklists.md](../01-safety/checklists.md) — post-run
- [estop-chain.md](../01-safety/estop-chain.md) — emergency stops and what each cuts
- [04-subsystems/power/](../04-subsystems/power/) — why the rails are ordered this way
- [batteries.md](../03-base-vehicle/batteries.md) — charging
