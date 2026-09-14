---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Transport

Moving IBEX to a field site. Currently done with a rented U-Haul truck and auto transport
trailer.

Start this days ahead. The reservation is the easy part; the notification requirements are
what will delay you.

## Lead time

Before anything else, satisfy the SOP's notification requirements for moving a vehicle out
of the high bay — see [sop.md](../01-safety/sop.md). Advance notice goes to the lab
manager, who notifies Public Safety and the OARS building manager onward. The lead times
are in the SOP.

Public Safety handles the garage door, the ballasts, and clearing the sidewalk. None of
that happens spontaneously.

The full pre-departure list is in
[checklists.md](../01-safety/checklists.md) under field testing.

## Why an auto transport

IBEX will not fit a standard 5' × 9' utility trailer. It needs U-Haul's auto transport,
towed behind a 10' truck.

| Trailer specification | Value |
| --- | --- |
| Max outside tire width of towed vehicle | 6' 4" |
| Min inside tire width of towed vehicle | 3' 8" |
| Max outside body width of towed vehicle | 6' 7" |
| Outside width of vehicle platform | 6' 5" |
| Width between fenders | 6' 8" |
| Extended ramp length | 6' 6" |
| Outside width of ramps | 6' |
| Overall length, ramps stored | 12' 3" |
| Recommended hitch ball height | ~18" |

Against the Wolverine's dimensions — 122" long, 62.2" wide, 77.7" high — width is
comfortable: 62.2" against a 79" maximum body width.

> TODO(verify): **the loaded weight of IBEX is unknown, and it is the number that matters
> for towing.** The base vehicle weighs 1,786 lb dry per spec and measured 1,847 lb on
> scales. The modified vehicle — with the sensor rack, batteries, compute, and the Kairos
> hardware — has never been weighed. Weigh it, then confirm it against the auto
> transport's rated capacity before the next trip.

> TODO(verify): confirm IBEX's length fits the platform. The trailer's overall length with
> ramps stored is recorded but its usable platform length is not, and the vehicle is 10' 2"
> long.

## Reserving

Nearest location to campus: 985 Massachusetts Ave, Boston MA 02118.

1. Start at <https://www.uhaul.com/Trailers/Auto-Transport-Rental/AT/>
2. Set **02118** as both pick-up and drop-off, and set the pick-up date.
3. Click **Get Rates**.
4. Under "What are you towing with?" select **U-Haul Truck**.
5. Under "What are you towing?" select **ATV/Side-by-Side/UTV**.
6. Click **Check Compatibility**. The result should offer an **Auto Transport** and a
   **10' truck**.
7. Continue, choose a pick-up location, and set the date, time, and duration. **Six hours
   is a reasonable default** for a local trip.
8. For damage protection, select **Safemove Plus**.
9. Decline everything after that. U-Haul's checkout runs through several pages of add-ons
   — Safetrip, dollies and furniture pads, storage units, moving boxes, packing supplies,
   and moving labour twice. None are needed.

> The add-on pages change often, which is why they are described rather than enumerated.
> If the flow no longer matches, the selections in steps 4 through 8 are the ones that
> matter.

Cost as of April 2026 was roughly $89.90 plus $1.99 per mile.

## Picking up

Bring a valid driver's licence and the payment method used for the reservation.

## Loading

> TODO(verify): **this procedure is not documented.** Getting IBEX onto the trailer is the
> highest-risk part of transport — a 1,800 lb vehicle on ramps, with a spotter, near
> people. Record it: who drives, who spots, whether the vehicle is driven up under its own
> power or winched, which gear and drive mode, and where the spotters stand.
>
> Until it is written, do not let someone load IBEX for the first time without a qualified
> supervisor present.

## Securing

Four ratchet straps and two tow straps travel in the black container. Chock the wheels
once the vehicle is positioned.

> TODO(verify): record the tie-down points on IBEX and the strap pattern used. "Four
> ratchet straps" without attachment points is not a procedure, and the wrong attachment
> point on a research vehicle can damage the sensor rack or the Kairos hardware.

## What travels with the vehicle

The black container stays with IBEX for every trip:

- [ ] AVAPOW car battery jump starter
- [ ] Fire extinguisher
- [ ] First aid kit
- [ ] Tow straps ×2
- [ ] Ratchet straps ×4
- [ ] Deka tool kit
- [ ] Power inverter

The fire extinguisher and first aid kit are also SOP requirements for any run, not just
field trips — see [checklists.md](../01-safety/checklists.md).

Session-specific equipment is separate and goes on the field-testing checklist.

## Planning the day

A local trip takes a full day. From an actual Olin run:

| Time | Activity |
| --- | --- |
| 07:00 | Pick up the U-Haul |
| 07:20 | Arrive at Northeastern |
| 07:30 | Remove the vehicle from the high bay and load |
| 08:00 | Depart |
| 09:00 | Arrive on site |
| 09:15 | Unload |
| 09:30 | Begin testing |
| 13:00 | Load up |
| 13:30 | Lunch |
| 14:00 | Depart for campus |
| 15:00 | Unload |
| 15:30 | Return the U-Haul |

Three and a half hours of testing inside an eight and a half hour day. Plan objectives
accordingly — see [checklists.md](../01-safety/checklists.md).

## On return

Unload, return the vehicle to its assigned spot in the high bay, and work the post-run
checklist. Moving back into the bay has its own SOP requirements — notification, the
garage door, the air exchange delay before the door closes.

## Related

- [sop.md](../01-safety/sop.md) — notification requirements and high bay entry and exit
- [checklists.md](../01-safety/checklists.md) — field testing pre-run and post-run
- [field-sites.md](field-sites.md) — where you are going and what the terrain is like
- [specifications.md](../03-base-vehicle/specifications.md) — dimensions and weight
- [fuel.md](../03-base-vehicle/fuel.md) — fuel state before travel
