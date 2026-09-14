---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Base vehicle maintenance

Keeping the Wolverine serviceable. Battery maintenance is in [batteries.md](batteries.md)
and fuel handling is in [fuel.md](fuel.md). If something is already wrong, start at
[troubleshooting.md](troubleshooting.md).

IBEX accumulates far less wear than a recreational side-by-side would — it spends most of
its life stationary in the high bay. That reduces how often service is needed; it does not
remove the need.

## Intervals

| Task | Interval | Done by |
| --- | --- | --- |
| Dealer service | Every 50 engine hours or 200 miles, whichever comes first | Dealer — see [troubleshooting.md](troubleshooting.md) |
| Shift linkage torque | Monthly | In house |
| Door hinge lubrication | As needed | In house |

> TODO(verify): **how engine hours and mileage are read.** A 50-hour interval is
> unenforceable if nobody knows where the hour meter is or what it currently reads. Record
> where to find both, and the readings at the last service.

> TODO(verify): transcribe the manufacturer's maintenance schedule from the owner's manual
> in [`docs/hardware/Wolverine/`](../../hardware/Wolverine/) into a table here. The three
> tasks above are what the lab has been tracking, not what Yamaha requires. Items almost
> certainly missing include engine oil and filter, air filter, coolant, brake fluid, spark
> plugs, and inspection of the Ultramatic V-belt — which is a wear item on any CVT and is
> not currently on anyone's list.

## Monthly: shift linkage torque

The nuts on the shifter linkage arm work loose. If they slip, the linkage falls out of
alignment and gear selection stops matching the lever — which matters more on IBEX than on
a stock vehicle, because the Kairos transmission actuator drives that same linkage.

The linkage arm sits under the centre console, where the cup holders are. The console has
to come off to reach it.

1. Remove the centre console.
2. Locate the shifter linkage arm.
3. Torque the linkage nuts.
4. Confirm gear selection still matches the lever through all four positions — Low, High,
   Neutral, Reverse.
5. Refit the console.

> TODO(verify): **no torque value is recorded.** "Torque the nuts" without a figure means
> each person guesses, and the failure modes run in both directions — loose enough to slip,
> tight enough to damage the linkage. Read the value from the owner's manual and put it in
> step 3, along with the socket size.

> TODO(verify): migrate `Shift Linkage Arm.png` from the Obsidian vault to
> `assets/images/shift-linkage-arm.png`. The source note says "below is an image of what to
> look for" — without it, step 2 depends on the reader recognizing a part they have never
> seen.

> TODO(verify): confirm whether the Kairos transmission actuator or its bracket has to be
> disturbed to reach the linkage nuts. If it does, that changes this from a five-minute job
> into one that needs the motion owner and a re-check afterwards.

## As needed: door hinges

Doors that no longer close quietly, or that need slamming, want lubricant on the hinge.

> TODO(verify): the source instruction is cut off at "a quick solution will be to WD40 the
> hinge in the". Complete it — which hinge, and where on it.

WD-40 will free a stiff hinge but evaporates and attracts grit, so it tends to need
repeating. A silicone or white lithium grease lasts longer on a door that gets used
regularly. Either is fine; the point is that this recurs.

## Recording maintenance

> TODO(verify): there is no maintenance log. Service dates, engine hours at service, and
> when the linkage was last torqued are not written down anywhere, which means the
> intervals above cannot actually be followed — nobody knows when the clock started.
>
> The SOP's Appendix C work log covers sessions on the vehicle. Decide whether maintenance
> goes there or in a separate log, then record where it lives here.

## Work that does not happen in house

- **Engine and fuel system work is prohibited in the high bay** by the SOP. See
  [sop.md](../01-safety/sop.md).
- **Do not work underneath the vehicle.** See [01-safety/README.md](../01-safety/README.md)
  for the rule and its one narrow exception.
- **Tire changes need their own approved SOP.** The current SOP calls this out explicitly.

> TODO(verify): IBEX goes to the dealer as a heavily modified vehicle — actuators on the
> throttle, brake, steering, and transmission, plus a 48 V system and a roof rack. Establish
> whether any of that needs removing before dealer service, who does it, and who
> re-commissions and re-verifies the drive-by-wire afterwards. A dealer disturbing the
> throttle actuator and nobody re-checking it is a plausible route to the throttle sticking
> open again.

## Related

- [specifications.md](specifications.md) — what the intervals apply to
- [batteries.md](batteries.md) — vehicle battery charging and care
- [fuel.md](fuel.md) — fuel age and storage
- [troubleshooting.md](troubleshooting.md) — diagnostics and the dealer contact
- [kairos-p4s4.md](../04-subsystems/motion/hardware/kairos-p4s4.md) — the actuators
  attached to the linkages above
- [`docs/hardware/Wolverine/`](../../hardware/Wolverine/) — owner's manual
