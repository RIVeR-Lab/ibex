---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Pre-run and post-run checklists

These wrap around the power sequences. They do not replace them.

- **Pre-run** is everything to confirm *before* you begin
  [power-on.md](../02-operations/power-on.md).
- **Post-run** is everything to do *after* [power-off.md](../02-operations/power-off.md)
  completes.

The verification steps inside the power sequences — confirming each subsystem came up,
confirming each box went dark — belong to those pages and are not repeated here.

Copy the relevant list into your session notes or print it. Do not check items from
memory.

## Pre-run: every run

Applies whether you are running in the EXP high bay or in the field.

### Authorization

- [ ] You are signed off on the SOP (Appendix B) for the work you are about to do
- [ ] Either you are cleared to operate unsupervised, or a qualified supervisor is present
      — see [README.md](README.md)
- [ ] The work is within what the SOP permits. No engine or fuel system work. No tire
      changes without a separate approved SOP
- [ ] This session is entered in the work log (SOP Appendix C)

### Personnel and roles

- [ ] Every role below that the session needs is assigned to a named person
- [ ] Everyone present knows where the stop controls are and what each one cuts — see
      [estop-chain.md](estop-chain.md)
- [ ] Nobody is working alone on the power system or running the vehicle

| Role | Responsibility |
| --- | --- |
| Driver | In the seat, hands on the wheel, owns the manual override attempt |
| Kairos operator | Commands the P4S4, whether from the passenger seat or the OCU |
| Safety spotter ×2 | Outside the vehicle, watching the path and the perimeter. One holds the stop authority |
| Procedure documenter | Records what was run, what happened, and what broke |
| Photographer | Optional. Data capture for reporting |

> The spotter with stop authority calls a halt and everyone stops. That call is never
> questioned in the moment.

### Safety equipment

- [ ] ABC or CO2 fire extinguisher rated for electrical and fuel fires is **in the
      vehicle**
- [ ] A second extinguisher is available near the vehicle, per the SOP
- [ ] First aid kit present
- [ ] Emergency contact information on hand
- [ ] Wheel chocks on hand

### Vehicle

- [ ] Fuel level adequate for the session, and the fuel is not older than three to six
      months — see [fuel.md](../03-base-vehicle/fuel.md)
- [ ] Coolant level checked
- [ ] Vehicle battery charged
- [ ] Tires visually sound
- [ ] Bolts and fasteners tight, shift linkage included — see
      [maintenance.md](../03-base-vehicle/maintenance.md)
- [ ] Nothing loose in the cargo area that can move under acceleration or on rough terrain
- [ ] Seatbelts functional and worn by everyone who will be aboard
- [ ] Cabling, steering, and the stabilizing arm are clear of anything that will bind

> TODO(verify): add tire pressure and coolant specifications, and where to read each. "Check
> coolant" without a target level is not a check.

### Space

- [ ] Parking spot and the path the vehicle will travel are clear, plus three feet on all
      sides
- [ ] Floor dry — no water, snow, or ice
- [ ] Perimeter established with cones or barriers if the vehicle will move
- [ ] If the engine will run: garage door open, ballasts lowered, ventilation adequate.
      **The vehicle is never run with the door closed**

### Stop controls

- [ ] Main e-stop unlocked and its position known to everyone present
- [ ] Deadman tested before any commanded motion
- [ ] Everyone knows that manual takeover is not a guaranteed override — see
      [estop-chain.md](estop-chain.md)

> TODO(verify): this section should include a positive functional test of the main e-stop
> before each run. Write it once [estop-chain.md](estop-chain.md) establishes what the
> e-stop actually cuts.

### Then

- [ ] Run [power-on.md](../02-operations/power-on.md)

## Pre-run: additions for field testing

Everything above, plus the following. Start this days ahead, not on the morning.

### Lead time

- [ ] Lab manager notified of the vehicle move, with the required advance notice — see
      [sop.md](sop.md)
- [ ] Onward notification to Public Safety and the OARS building manager confirmed
- [ ] PI consulted on resources
- [ ] Safety consulted on the timetable
- [ ] Site access arranged and confirmed with the site
- [ ] Transport reserved — see [transport.md](../02-operations/transport.md)

### Equipment

- [ ] Black container packed per the manifest in
      [transport.md](../02-operations/transport.md)
- [ ] Every sensor the session depends on has been powered and confirmed working *before*
      departure, not on site
- [ ] Session-specific equipment loaded
- [ ] Storage media present and empty

### Plan

- [ ] Timetable written and shared with everyone attending
- [ ] Everyone attending knows the site, the terrain, and the plan
- [ ] Test objectives written down before departure

> A field session without written objectives becomes a drive. Write down what you are
> trying to learn.

## Post-run

Begin after [power-off.md](../02-operations/power-off.md) completes.

### Secure the vehicle

- [ ] Vehicle in park with the parking brake set
- [ ] Wheel chocks placed at the rear wheels
- [ ] Main e-stop engaged
- [ ] Doors closed
- [ ] Floor cleaned and dried if anything was tracked in

### Consumables

- [ ] System battery charge state checked, and charging started if needed — see
      [batteries.md](../03-base-vehicle/batteries.md)
- [ ] Vehicle battery charge state checked
- [ ] Fuel level noted. Do not leave the tank full for extended storage; around half a
      tank is the target — see [fuel.md](../03-base-vehicle/fuel.md)

### Data

- [ ] Bags offloaded from Volta
- [ ] Each bag has its `metadata.yaml` — see
      [data-collection.md](../02-operations/data-collection.md)
- [ ] Recordings from cameras and any handheld devices offloaded
- [ ] Volta has free space for the next session

### Equipment

- [ ] Tools returned to the black container and the manifest checked
- [ ] Fire extinguisher still in the vehicle
- [ ] Anything removed from the vehicle either returned or noted

### Record

- [ ] Work log completed (SOP Appendix C), including entry and exit if the vehicle moved
- [ ] Anything that broke, bound, locked, or behaved unexpectedly written down — including
      near misses that caused no damage
- [ ] New findings routed into the manual: a stale value corrected, an open question
      raised in [open-questions.md](../99-appendix/open-questions.md), or a `last-verified`
      date updated on a page you just exercised

> TODO(verify): name the reporting destination for near misses. Same gap as in
> [README.md](README.md).

## Open safety questions affecting these checklists

- **Unpowered stopping distance is unmeasured.** How long IBEX takes to come to rest after
  the throttle is released has been an open test objective across multiple sessions and
  does not appear to have been recorded. Until it is, spotters cannot judge a safe standoff
  distance. Tracked in [open-questions.md](../99-appendix/open-questions.md).
- **Whether the vehicle reliably coasts to a stop with no throttle input** is listed as
  unverified in the same test notes.

## Related

- [README.md](README.md) — the rules these checklists enforce
- [estop-chain.md](estop-chain.md) — what each stop control cuts
- [sop.md](sop.md) — sign-off, work log, and notification requirements
- [power-on.md](../02-operations/power-on.md) and
  [power-off.md](../02-operations/power-off.md) — the sequences these bracket
- [transport.md](../02-operations/transport.md) — trailer, packing manifest, timetable
- [field-sites.md](../02-operations/field-sites.md) — site-specific constraints
