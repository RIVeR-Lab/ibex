---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Fuel

Handling gasoline for IBEX. Tank capacity and octane requirement are in
[specifications.md](specifications.md).

Gasoline is the one consumable on this vehicle that is regulated by the University, so the
rules here are compliance requirements rather than preferences.

## The rules

| Rule | Source |
| --- | --- |
| Gasoline may not be stored in the high bay | University policy, via the [SOP](../01-safety/sop.md) |
| Fuel in the vehicle's tank is acceptable | Same |
| No work on the engine or fuel system in the high bay | [SOP](../01-safety/sop.md) |
| Fuel removed from the vehicle becomes hazardous waste | [hazardous-waste.md](../01-safety/hazardous-waste.md) |

Two portable fuel containers are kept in the high bay. **They are stored empty.** That is
what reconciles them with the no-storage rule — the prohibition is on stored gasoline, not
on empty containers.

> TODO(verify): confirm that the containers are in fact stored empty, and that this is the
> understanding the SOP was written against. As recorded, the source note says both that
> gasoline must not be stored in the high bay and that the containers are stored there,
> which reads as a contradiction. If a container is ever left with fuel in it, that is a
> compliance problem and not a housekeeping one.

## Fuel age

Gasoline is good for three to six months. Past that it separates, and separated fuel
causes running problems that look like other faults — see
[troubleshooting.md](troubleshooting.md).

This is why the tank is not kept full. **Target roughly half a tank**: enough for a test
session, not enough to sit for a year going stale.

> TODO(verify): there is no record of when fuel was last added. The three-to-six-month
> limit cannot be enforced without one, and "how old is the fuel" is the first question in
> the no-start tree. Decide where that gets logged — alongside maintenance records is the
> obvious place, see [maintenance.md](maintenance.md).

## Refueling

Fuel is fetched by container rather than by driving the vehicle to a station.

1. Take the two portable containers to the filling station.
2. Fill them.
3. Return and transfer the fuel into the vehicle's tank.

> TODO(verify): record the station's name and address. "The gas station down the street
> from campus" is not directions for someone new, and they will be holding two empty
> containers when they need it.

> TODO(verify): **record where the transfer happens.** Pouring gasoline is the highest fire
> risk in the whole operation, and the high bay prohibits fuel system work. Establish
> whether refueling is done outside the building, in a designated area, or somewhere else
> entirely, then write it here as a step.

When transferring fuel:

- Engine off, key out, no ignition sources.
- Set the container on the ground, not in a vehicle or a truck bed. A container on an
  insulated surface can accumulate static charge.
- Keep the container's spout in contact with the filler neck while pouring.
- A fire extinguisher rated for fuel fires is within reach — see
  [checklists.md](../01-safety/checklists.md).

> TODO(verify): record the capacity of the two containers. Whether they cover a full tank
> matters for planning: the tank holds 9.2 US gal, so two 5-gallon containers cover it and
> two 2-gallon containers do not.

## Removing fuel

A siphon pump is kept for draining the tank. Removing fuel is needed when the fuel has
aged out, or before storage or service.

> TODO(verify): write this procedure. The siphon pump was purchased in May 2026 and the
> process was never recorded. It needs: where the pump lives, how it is used on this tank,
> what the fuel is drained into, and where that container goes afterwards.

Fuel that comes out of the vehicle is hazardous waste. It goes into an approved container,
gets labelled, and gets staged for University pickup — see
[hazardous-waste.md](../01-safety/hazardous-waste.md). Do not leave it in a portable
container in the high bay.

## Reading the fuel level

The dash gauge is the normal reference. Fuel level is also reported by the Kairos system
and appears on the OCU — see
[kairos-p4s4.md](../04-subsystems/motion/hardware/kairos-p4s4.md).

## Related

- [specifications.md](specifications.md) — capacity and octane requirement
- [maintenance.md](maintenance.md) — service intervals and records
- [troubleshooting.md](troubleshooting.md) — fuel-related no-start causes
- [hazardous-waste.md](../01-safety/hazardous-waste.md) — disposal requests
- [01-safety/README.md](../01-safety/README.md) — fuel and hazardous material rules
- [checklists.md](../01-safety/checklists.md) — pre-run fuel checks
- [transport.md](../02-operations/transport.md) — fuel state before travel
