---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Standard Operating Procedure

The SOP is the governing safety document for operating IBEX in the EXP high bay. It is a
University document, approved outside this lab, and it is **not ours to edit**.

**File:** [`2025_07_14-EXP-vehicle-SOP.docx`](../../safety/2025_07_14-EXP-vehicle-SOP.docx)

> TODO(verify): confirm the path above matches where the file actually sits under `docs/`.

This page tells you what the SOP covers, what it requires of you, and how to navigate it.
It deliberately does not reproduce it. Read the document.

## Authority

- Where the SOP and this manual disagree, **the SOP wins.** Correct the manual.
- Changes go through the University — the IER lab, OARS, and the Provost's Office — not
  through a pull request. Editing the docx in this repository does not change the rule.
- Additional vehicles are added as addenda, subject to OARS and Provost's Office review.
- Some work requires its own separate approved SOP. Changing tires is called out
  specifically. If you are planning work that feels outside the envelope, assume it needs
  one and ask before starting.

## Scope

The SOP covers two vehicles sharing the high bay: a Lincoln MKZ owned by another lab, and
our Yamaha Wolverine. Sections addressing entry, exit, and working in the space apply to
both. Read past the Lincoln-specific material rather than assuming it is ours.

| Appendix | Vehicle | Contents |
| --- | --- | --- |
| A | Yamaha | Electrical component inventory |
| B | Yamaha | Sign-off sheet — trained personnel |
| C | Yamaha | Work and entry/exit log |
| D, E, F | Lincoln | The same three, for the other vehicle |

## Before you touch the vehicle

The SOP sets prerequisites that are not negotiable and not covered anywhere else in this
manual:

- **Training.** Orientation for Labs, Makerspaces and Studios, and Fundamentals of
  Laboratory Safety, both through SciShield. Plus task-specific safety training from the
  PI.
- **Sign-off.** You must be trained on and sign Appendix B before working on any part of
  the vehicle or its systems. This is a physical signature on the document, separate from
  the supervision sign-off described in [README.md](README.md).
- **Approved driver list.** Only named RIVeR members may drive the Yamaha. The list is in
  the SOP and is explicitly marked as subject to update — check the document, not this
  page.
- **University vehicle policy.** IBEX is a University vehicle and Northeastern's
  [Policy on Use of Vehicles for University Purposes](https://policies.northeastern.edu/policy614/)
  applies.

## What the SOP governs

Navigation aid only. Each item below is a section of the document, not a summary of it.

| Section | What it covers |
| --- | --- |
| Purpose, Overview | Why the SOP exists and what stages it addresses |
| Vehicles | The two vehicles and how others get added |
| Prerequisites | Training, fire extinguishers, first aid, emergency contacts, taped-out parking spots |
| Drivers | Who may drive each vehicle |
| Moving a vehicle into the high bay | Advance notification, clearing the space, door and ballast handling, driving in, engine shutdown, chocking, air exchange |
| Working on a vehicle in the high bay | What work is permitted, what is prohibited, electrical limits, and required practices |
| Moving a vehicle out | The exit sequence |
| Documentation — Appendices | The six appendices above |

Two constraints from the working-on-the-vehicle section are worth knowing before you read
it, because they shape what is possible in the bay at all: **work on the engine or fuel
system is prohibited**, and **the engine may only run to enter and leave the building**.
The electrical envelope is capped at 48 V DC.

## Obligations that recur

These are the parts people forget, because they are not part of any procedure in
`02-operations/`:

- **Advance notice** is required before moving IBEX in or out of the high bay, with a
  further notification made onward to Public Safety and the OARS building manager. Lead
  times and the specific contacts are in the SOP. Plan transport around them — see
  [transport.md](../02-operations/transport.md).
- **Log the work.** Every session on the vehicle, and every entry and exit, goes in
  Appendix C.
- **Keep Appendix A current.** It is the University-approved electrical inventory. Adding
  or changing a powered component on IBEX means the appendix is now wrong, and correcting
  it goes through the SOP revision process. Hardware pages under
  [04-subsystems/](../04-subsystems/) must agree with it.

## Review

`last-verified` on this page matters more than on any other page in the manual.

The SOP is reviewed on a fixed interval, with particular attention to the driver list. The
copy in this repository is dated **2025-07-14**.

> TODO(verify): confirm the review interval — six months has been the working assumption.
> On that basis the current copy is overdue, and the driver list is the section most
> likely to be stale.

## Open items inside the SOP

The document itself leaves several things unresolved. These are the University's open
items, not ours, but they affect operations:

- **Air exchange delay before closing the garage door** is marked to be determined by
  carbon monoxide sampling. The SOP is to be updated once sampling establishes a timing.
- **Where emergency contact information lives** is marked TBD, pending a decision once
  both vehicles are in the space. This is the same gap flagged in
  [README.md](README.md).
- **Parking spot assignment** is unresolved, and the order in which vehicles can enter and
  leave depends on it. It may not always be possible to move one vehicle without moving
  the other.
- The Lincoln driver list is empty, and the Yamaha list has a blank entry.

Track these in [99-appendix/open-questions.md](../99-appendix/open-questions.md) and check
whether a newer revision of the SOP has resolved them before relying on this page.

## Conflicts with this manual

Where the SOP's Appendix A disagrees with a hardware page, the appendix is the approved
record and the hardware page should be corrected — or the appendix revised, if the vehicle
has genuinely changed.

One known discrepancy: Appendix A lists the system battery as a Lossigy LiFePO4 48 V unit.
The installed battery is a **Vatrer 48 V 105 Ah**. The vehicle is correct and the appendix
is stale, which means the University-approved electrical inventory does not currently match
the vehicle.

> TODO(verify): Appendix A needs revising through the SOP process to record the Vatrer
> battery. Until it is, the inventory on file is wrong. Tracked in
> [open-questions.md](../99-appendix/open-questions.md).

The Appendix A figures for the Kairos P4S4 — 12 V, 240 W, with 5 A idle, 20 A running
actuators without the engine, and 10 A running actuators with the engine — are correct and
supersede the 18 W figure in the original Obsidian note.

## Related

- [README.md](README.md) — the lab's own safety rules, which sit inside the SOP's envelope
- [checklists.md](checklists.md) — pre-run and post-run
- [00-onboarding/ownership.md](../00-onboarding/ownership.md) — who owns the SOP
  relationship
