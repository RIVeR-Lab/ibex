---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Vehicle battery

The 12 V battery under the hood that starts the Wolverine.

**This is not the system battery.** The 48 V Vatrer pack in the rear that powers the
research payload is a different thing with different rules — see
[04-subsystems/power/](../04-subsystems/power/). Confusing the two is easy and the care
requirements are not interchangeable.

## The two batteries

Two batteries can go in the vehicle. **The Renegade is the one currently installed.**

| | Renegade — installed | OEM — spare |
| --- | --- | --- |
| Type | 12 V sealed AGM | 12 V VRLA lead-acid |
| Rating | 400 CCA | TODO(verify) |
| Source | Aftermarket replacement | Shipped with the vehicle |

The care rules below are the Renegade's and are stricter than normal lead-acid practice.
Follow them, not habit.

> TODO(verify): record the Renegade model number here and in
> [reorder.md](../99-appendix/reorder.md), and record where the OEM battery is stored.

## Removing the battery

The battery sits at the front of the vehicle, under the hood. The owner's manual
recommends removing it to charge — see
[`docs/hardware/Wolverine/`](../../hardware/Wolverine/), pages 9-47 to 9-49.

1. Turn the key to **`O`** (off).
2. Remove the hood.
3. Remove the battery holding plate by removing its bolts.
4. Disconnect the **negative** lead first, then the **positive** lead.
5. Lift the battery out of its compartment.

> **Polarity order is not optional.** Main switch off, negative off first. Removing the
> positive lead first on a vehicle with a grounded chassis means a tool touching bodywork
> shorts the battery.

## Charging

1. Remove the battery from the vehicle.
2. Read the recommended charging rate from the label on the battery itself.
3. Use a charger that matches it and follow the charger's instructions — or have the
   dealer charge it.

If the vehicle has optional electrical accessories fitted, the battery discharges faster
than it otherwise would.

> TODO(verify): record which charger the lab owns and its output. The Renegade rules below
> cap charging at 1.5 A, so "a suitable charger" is a narrower category than it sounds, and
> using a higher-output automatic charger will shorten the battery's life.

## Installing

1. Confirm the battery is fully charged before fitting it.
2. Place it in its compartment.
3. Connect the **positive** lead first, then the **negative** lead.
4. Refit the battery holding plate.
5. Refit the hood.

> Reverse of removal: positive on first, negative on last, main switch off throughout.

## Renegade care rules

The AGM construction means this battery is maintained differently from most. The
manufacturer's guidance, in their words condensed:

**Do**

- Charge every 30 days when the vehicle is not in use
- Check terminals for cleanliness and loose connections
- Store between 62 °F and 82 °F
- Check your charger's output voltage regularly

**Do not**

- Use an automatic charger rated above **1.5 A**
- Leave it on a battery tender after every ride
- Let the voltage drop below **10 V**
- Charge for more than **48 hours at a time**

If the vehicle is used two to three times a month or more, no additional charging is
needed. If it will sit for more than 30 days, charge for 48 hours and then **remove the
charger**.

### Why the tender rule matters

Leaving this battery on a continuous trickle charge is the common way it gets killed — the
construction is not built to absorb a 24/7 charge, and power going in has to go somewhere.
People who believe they have maintained the battery carefully with a permanent tender have
usually shortened its life.

**Do not put the Renegade on a tender.** Older notes reference a battery tender, including
the "won't turn on" tree in [troubleshooting.md](troubleshooting.md). Those predate the
Renegade purchase and applied to the OEM battery. They do not apply to the battery
currently in the vehicle.

> TODO(verify): record the resting voltage that indicates a charged battery, from the
> Renegade documentation. The 10 V floor above tells you when it is ruined but not when it
> needs charging, and "check the charge state" appears in
> [checklists.md](../01-safety/checklists.md) without a number to check against.

## Related

- [specifications.md](specifications.md) — the OEM battery specification
- [maintenance.md](maintenance.md) — service intervals
- [troubleshooting.md](troubleshooting.md) — the vehicle will not start
- [checklists.md](../01-safety/checklists.md) — pre-run and post-run charge checks
- [04-subsystems/power/](../04-subsystems/power/) — the 48 V system battery, which is not
  this
- [reorder.md](../99-appendix/reorder.md) — replacement part numbers
- [hazardous-waste.md](../01-safety/hazardous-waste.md) — disposal at end of life
