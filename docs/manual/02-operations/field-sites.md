---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Field sites

Where IBEX operates, and what each location requires of you.

Getting there is [transport.md](transport.md). What to do before leaving is
[checklists.md](../01-safety/checklists.md).

## Sites

| Site | Type | Distance from campus | Status |
| --- | --- | --- | --- |
| EXP high bay | Indoor, on campus | — | Primary |
| Olin College | Outdoor, off-road | ~1 hour each way | Used |
| Hopkinton State Park | Outdoor | TODO(verify) | TODO(verify): whether it has been used |

## EXP high bay

The primary space. Indoor, on campus, shared with a Lincoln MKZ belonging to another lab.

Everything about operating here is governed by the SOP — see
[sop.md](../01-safety/sop.md). The constraints that shape what is possible:

| Constraint | Consequence |
| --- | --- |
| The engine may only run to enter and leave the building | No engine-running tests indoors |
| Work on the engine or fuel system is prohibited | That work happens elsewhere or at the dealer |
| Electrical work capped at 48 V DC | Fine for IBEX as built |
| Gasoline may not be stored in the space | Fuel in the tank is acceptable; fuel in a container is not — see [hazardous-waste.md](../01-safety/hazardous-waste.md) |
| The vehicle is never run with the garage door closed | Door open, ballasts down, and an air exchange delay before closing |
| Vehicles park in taped-out spots with clearance around them | Space is shared and finite |
| Shared with a second vehicle | It may not be possible to move IBEX without moving the Lincoln |

Access is governed by the SOP, including key control. Public Safety opens the garage door,
handles the ballasts, and clears the sidewalk. Ask the vehicle access owner in
[ownership.md](../00-onboarding/ownership.md).

## Olin College

**1000 Olin Way, Needham, MA 02492.** Roughly an hour from campus each way.

The off-road site used so far. Testing has taken place on the 180-acre field.

| Terrain | Notes |
| --- | --- |
| Open field | The `olin-emptyfield` collections |
| Mud | |
| Swamp-like vegetation | The `olin-swamp` collections |
| Marshland | |

Mud and marsh are the point — this is where traversability data comes from — and they are
also the realistic way to lose a day.

> TODO(verify): **there is no documented recovery plan.** IBEX is an 1,800 lb vehicle
> being driven into mud and marsh on purpose. Two tow straps travel in the black container
> and nothing records what they attach to, what recovers the vehicle if it beaches, or
> whether a second vehicle needs to be on site. Establish this before the next marsh
> session.

> TODO(verify): record the site contact and how access is arranged. Nothing in the notes
> says who at Olin grants permission, how far ahead, or whether there is a standing
> arrangement.

## Hopkinton State Park

**164 Cedar St, Hopkinton, MA 01748.**

> TODO(verify): the address is the only thing recorded about this site. Before anyone plans
> a session here, establish: whether it has ever been used, what the terrain is, and —
> most importantly — **what permitting a state park requires for operating an autonomous
> research vehicle.** Massachusetts DCR properties generally require a permit for
> organized or motorized activity. Assume it is not walk-in until someone confirms
> otherwise.

## What a site record needs

The two outdoor sites above are documented as an address and a terrain list. That is
enough to drive there and not enough to run a session safely. Any site added here, and
both existing ones, should record:

- **Access** — who grants permission, how far ahead, and any permit required
- **Contact on site** — a name and how to reach them on the day
- **Staging** — where the truck and trailer park, and where the vehicle is unloaded
- **Terrain** — what is drivable, what is not, and what is uncertain
- **Recovery** — what gets IBEX out if it becomes stuck, and whether that is available
  on site
- **Emergency access** — whether an ambulance can reach the operating area, and the
  nearest hospital
- **Communications** — cell coverage across the operating area. A site where spotters
  cannot reach each other by phone changes how the session is run
- **Facilities** — power, shelter, restrooms, somewhere to sit with a laptop

> TODO(verify): fill these in for Olin first, since it is the site actually in use. The
> emergency access and communications entries matter most — a marsh with no cell coverage
> and no vehicle access is a different risk profile from a field beside a car park, and
> right now the manual does not distinguish them.

## Related

- [transport.md](transport.md) — getting there
- [checklists.md](../01-safety/checklists.md) — field testing pre-run and post-run
- [sop.md](../01-safety/sop.md) — high bay entry, exit, and notification
- [data-collection.md](data-collection.md) — naming collections by site
- [troubleshooting.md](../03-base-vehicle/troubleshooting.md) — if the vehicle will not
  start in the field
