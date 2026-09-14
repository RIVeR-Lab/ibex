---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Base vehicle troubleshooting

Faults in the Wolverine itself — the engine, the battery, the doors.

## First, which "won't turn on"?

"IBEX won't turn on" means two completely different things and sends you to two different
pages:

| Symptom | Go to |
| --- | --- |
| The engine will not crank or start | This page |
| The research payload will not power up — boxes, Volta, sensors | [power-on.md](../02-operations/power-on.md), the failure section |
| The software stack will not come up | [running-the-system.md](../02-operations/running-the-system.md), known issues |
| An actuator will not respond | [kairos-p4s4.md](../04-subsystems/motion/hardware/kairos-p4s4.md) |

The engine and the payload are on entirely separate supplies. A dead vehicle battery does
not affect the payload, and a dead system battery does not stop the engine.

## The engine will not start

Work these in order before calling anyone.

### 1. Rule out the drive-by-wire system

Check this first, because it is IBEX-specific and a dealer will not think of it.

- Is the VIM disarmed? If the P4S4 is armed, an actuator may be holding the throttle,
  brake, or transmission out of position.
- Is the transmission actually in the gear the lever shows? The shift linkage can slip out
  of alignment — see [maintenance.md](maintenance.md).

A throttle actuator holding the throttle open has previously produced a high-RPM start
rather than a no-start, so this can present as a bad start rather than no start at all. See
[estop-chain.md](../01-safety/estop-chain.md).

> TODO(verify): confirm whether an armed P4S4 can actually prevent the engine from
> starting, or only affect how it starts. The distinction changes whether this belongs
> first in the tree or further down.

### 2. Fuel

- Is there enough fuel in the tank?
- When was fuel last added?
- Has it been in the tank longer than three to six months? Separated fuel causes running
  problems that look like ignition or starting faults.

See [fuel.md](fuel.md).

### 3. Vehicle battery

- When was the battery last charged?
- Does it read above the charged threshold at rest?

See [batteries.md](batteries.md) for charging rules.

> The Renegade AGM battery currently fitted must **not** live on a battery tender. Older
> notes ask whether the backup battery has been sitting on a tender — that guidance
> predates the Renegade and applied to the OEM battery. Do not act on it.

### 4. Basics worth confirming

- Key fully in the run position, main switch on.
- Coolant level — checked as part of pre-run, see
  [checklists.md](../01-safety/checklists.md).

> TODO(verify): complete this tree. The Wolverine has starting interlocks that the source
> notes do not mention — gear position, brake pedal, and seatbelt are the usual ones, and
> any of them will produce a no-crank that looks like a battery fault. Read the owner's
> manual in [`docs/hardware/Wolverine/`](../../hardware/Wolverine/) and record which
> interlocks apply, plus the starter and fuse checks.

## Doors will not close

Doors that no longer close quietly, or that need slamming, want lubricant on the hinge. See
[maintenance.md](maintenance.md).

## Escalating to the dealer

If the tree above does not identify the problem, the service department below handles
mechanical work on the Wolverine. The lab has an account.

| | |
| --- | --- |
| Service department | MOM's Foxboro |
| Web | <https://foxboro.moms73.com> |
| Address | 1000 Washington St, Foxborough, MA 02035 |
| Phone | (508) 543-1734 |
| Account name | RIVER LAB Co. |

> TODO(verify): the account name is recorded two ways in the source material — "RIVER LAB
> Co." and "RiverLabCo." Confirm which the dealer has on file and correct the other. See
> [vendor-accounts.md](../99-appendix/vendor-accounts.md), which is the registry for
> vendor accounts.

Before the vehicle goes to the dealer, read the note in
[maintenance.md](maintenance.md) about dealer service on a modified vehicle. Nobody has yet
established whether the Kairos hardware needs removing first, or who re-verifies the
drive-by-wire afterwards.

## What to record

A fault that gets diagnosed and not written down gets diagnosed again by the next person.

- Symptom, what you checked, and what fixed it
- If the dealer was involved, what they did and what they charged
- If it recurs, say so — a second occurrence is a different problem from a first

> TODO(verify): decide where this goes. The SOP's Appendix C work log is one option;
> alongside maintenance records is another. Same open question as in
> [maintenance.md](maintenance.md).

## Related

- [specifications.md](specifications.md) — what the vehicle is
- [maintenance.md](maintenance.md) — scheduled service and the shift linkage
- [batteries.md](batteries.md) — the 12 V battery and its charging rules
- [fuel.md](fuel.md) — fuel age and handling
- [power-on.md](../02-operations/power-on.md) — payload power faults
- [field-sites.md](../02-operations/field-sites.md) — if this happens away from campus
- [`docs/hardware/Wolverine/`](../../hardware/Wolverine/) — owner's manual
