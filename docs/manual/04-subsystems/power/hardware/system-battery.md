---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# System battery

The VATRER LiFePO₄ pack that powers the entire sensing and autonomy payload. Serves
[Power](README.md).

**This is not the vehicle battery.** The Renegade AGM that starts the engine is a separate
domain with opposite care rules — see
[batteries.md](../../03-base-vehicle/batteries.md).

> **It is never charged by the vehicle.** No alternator connection exists. Runtime is
> bounded by what is in the pack when you leave, and recharging is a bench operation
> between sessions that requires physically unbolting the payload feed from the terminals.
> See [Charging](#charging) — including an unresolved question about whether switching the
> pack off actually de-energises them.

## Overview

A 16-series LiFePO₄ pack sold as a golf-cart conversion battery, repurposed as IBEX's
payload supply. Three of its features matter more here than they would in a golf cart:

**It self-heats for cold-weather charging.** Three internal heating pads, 200 W, triggered
by charger input. Relevant in a New England winter — see
[Temperature limits](#temperature-limits).

**It reports its own state.** A 2.8-inch LCD shows state of charge, current, voltage, and
health, with a Bluetooth app as a second route. This is IBEX's **only** state-of-charge
indication.

**It is IP67 and rated for 200 A continuous**, far beyond the ~24 A peak the payload
actually draws. The pack is substantially over-specified for this application, which is
why endurance rather than current capability is the binding constraint.

## The 48 V label is wrong

The product is marketed as "48 V" and **the vendor's own SKU reads
`D-51.2V-105AH-JR-KB`.** The tech specs list nominal voltage as 51.2 V.

| | |
| --- | --- |
| 51.2 V × 105 Ah | **5,376 Wh** — matches the published energy figure |
| 48.0 V × 105 Ah | 5,040 Wh — does not |

**51.2 V is correct and is used for every calculation in the manual.** 48 V is a product
category name, the way a "12 V" lead-acid battery rests at 12.6 V.

> This supersedes the "48 V" figure in earlier notes and the stale Lossigy entry in the
> SOP's Appendix A — see [sop.md](../../../01-safety/sop.md).

## Physical location on vehicle

Rear of the vehicle.

> TODO(verify): record exactly where and how it is secured. At **43.8 kg / 96.6 lb** it is
> one of the heaviest individual items added to the vehicle, so its mounting matters for
> both weight distribution and crash behaviour. It should appear in the weight distribution
> section of
> [specifications.md](../../../03-base-vehicle/specifications.md).

> TODO(verify): confirm clearance around it. The pack is 500 × 318 × 244 mm and needs
> access to both terminals for the charging swap.

## Hardware specs

| | |
| --- | --- |
| Manufacturer | Vatrer Power |
| SKU | `D-51.2V-105AH-JR-KB` |
| Chemistry | LiFePO₄, 16 series |
| Nominal voltage | **51.2 V** |
| Charge voltage | 58.4 V |
| Full-charge resting voltage | 52.7 V measured |
| Rated capacity | 105 Ah |
| Rated energy | 5,376 Wh |
| Discharge cut-off | **40 V** — 2.50 V per cell |
| Max continuous discharge | 200 A (400 A peak, 35 s) |
| Max continuous charge | 55 A |
| Max charge current | 100 A |
| Max load / inverter power | 10,240 W |
| Cycle life | ≥ 4,000 cycles |
| Weight | 43.8 kg / 96.6 lb |
| Dimensions | 500 × 318 × 244 mm |
| Ingress protection | IP67 |
| Warranty | 10 years |

> The vendor's comparison table gives the length as 19.96 in while its tech-spec table
> gives 19.69 in. One is a typo; measure before designing anything to fit.

### The design margin is real, not nominal

The power budget uses 90% depth of discharge as its design basis, giving 4.84 kWh usable.

The BMS cuts discharge at **40 V — 2.50 V per cell**, which is essentially empty for
LiFePO₄. So the 90% figure sits comfortably above the hard floor rather than against it,
and the endurance numbers in [README.md](README.md) are not relying on reaching the
cut-off.

### The payload barely loads this pack

| | Pack capability | Payload demand |
| --- | --- | --- |
| Continuous current | 200 A | ~13.9 A average |
| Peak current | 400 A | ~23.8 A |
| Load power | 10,240 W | ~1,219 W peak |

The payload uses about **7% of the pack's continuous current rating at average draw.**
Current capability will never be the limit; stored energy is. That also means adding loads
is constrained by the converters and bus bars, not by the battery — see the protection
table in [README.md](README.md#protection-summary).

## Additional components

Supplied with the battery:

- **58.4 V LiFePO₄ charger** — the vendor lists it as both 18 A and 20 A in different
  places
- **2.8-inch LCD screen and monitor cable**
- Communication cables
- M8 terminals
- Product manual

> TODO(verify): confirm the charger's actual rating from the unit itself, and record where
> the charger, the LCD, and the manual are kept.

## Software

**Vatrer Bluetooth app**, iOS and Android. Reports state of charge, voltage, current,
temperature, and operating status.

| | |
| --- | --- |
| iOS | `apps.apple.com/app/vatrer/id1641200046` |
| Android | `play.google.com/store/apps/details?id=com.vatrer.power` |

The app is the **backup** to the LCD, and worth having installed before you need it — see
[Known issues](#the-lcd-display-is-the-least-reliable-part-of-the-pack).

## Charging

**Charging requires physically disconnecting the payload.** There is no charge port and no
transfer switch.

### Procedure

1. Shut the system down properly first — see
   [power-off.md](../../../02-operations/power-off.md).
2. **Disconnect the ring connectors currently landed on the battery terminals**, which are
   the payload feed.
3. **Fit the charger's ring connectors** to the same terminals.
4. Connect the charger to mains and let it run.
5. On completion, reverse: remove the charger's rings, refit the payload rings.

**A full charge takes about 5.5 hours** from empty. Longer from a cold start — see below.

### Treat the terminals as live

**Nothing in the vehicle's wiring isolates them.** The 35 A fuse, the e-stop, and the
latching button are all downstream of the terminals, so none of those controls makes this
swap safe.

**The battery itself may have an output disconnect.** The LCD monitor appears to switch the
pack on and off — vendor reviews describe using it that way instead of the cart's own
switch — which would act at the BMS rather than in the wiring.

> TODO(verify): **measure it.** Switch the pack off at the monitor and put a meter across
> the terminals. This is a ten-second test that settles the question permanently, and the
> result should be recorded here.
>
> Expect voltage to still be present. A common-port LiFePO₄ BMS puts charge and discharge
> MOSFETs in series with body diodes in opposite orientations, so switching discharge off
> typically leaves the terminals near pack voltage with the charge path still able to
> conduct. This pack must detect a charger being connected in order to run its heating
> cycle, which means something on the terminal side stays awake. But that is reasoning from
> typical topology, not from this unit's manual — the manual or the meter is the authority.

**Until measured, and arguably afterwards, work as though they are live.** A BMS
disconnect is a semiconductor, not an air gap, and MOSFETs fail closed more often than they
fail open. A pack rated for 400 A peak puts real energy behind a tool dropped across both
terminals.

Minimum practice for the swap, which the manual should state and currently does not:

- Insulated tools
- One terminal at a time, never both exposed together
- No rings, watches, or metal wristbands
- Nothing metal resting on top of the pack
- Verify with a meter rather than assuming

> TODO(verify): whether the SOP covers battery servicing at all. See
> [sop.md](../../../01-safety/sop.md).

> TODO(verify): **is the 35 A fuse pullable?** If so, pulling it before the swap
> de-energises everything downstream and reduces the consequence of an error on the payload
> side. If the BMS turns out not to isolate the terminals, a proper battery disconnect
> switch between the pack and the fuse would be a worthwhile addition — it would make the
> swap both safer and faster.

### Charging is charger-limited, not pack-limited

| Current | Time for 105 Ah |
| --- | --- |
| Included charger, 18–20 A | **5.2 – 5.8 h** |
| Pack continuous maximum, 55 A | 1.9 h |
| Pack absolute maximum, 100 A | 1.1 h |

The pack would accept nearly three times the included charger's rate. A larger charger
would cut turnaround to about two hours, which matters if sessions are ever scheduled
back-to-back in one day.

> TODO(verify): whether faster turnaround is wanted. The 5.5-hour figure effectively means
> one field session per day, charging overnight.

## State of charge

Two routes, and **the pack's own instrumentation is the only state-of-charge indication on
the vehicle.** Nothing in the ROS stack reports it, and no rail voltage is logged.

| Route | Shows |
| --- | --- |
| 2.8-inch LCD | State of charge, current, voltage, health and status |
| Bluetooth app | State of charge, voltage, current, temperature, status |

**Check it before leaving**, and treat the ~5-hour planning figure from
[README.md](README.md#engine-off-endurance) as applying to a full pack.

> TODO(verify): the resting voltage is a useful cross-check — 52.7 V full, 40 V at the BMS
> cut-off. Record what the LCD reads at a few known states so an operator can sanity-check
> it against voltage.

> TODO(verify): consider logging pack voltage into the ROS graph. Nothing records it, so a
> bag carries no indication of how much energy was left during a run — which makes it
> impossible to correlate a late-session fault with a sagging supply.

## Temperature limits

**The three limits differ, and storage is the narrowest.**

| | Range | Note |
| --- | --- | --- |
| Charge | −20 °C to +45 °C | Low-temperature cut-off at **0 °C ± 4 °C** — heating engages |
| Discharge | −20 °C to +60 °C | BMS stops discharge at −20 °C |
| **Storage** | **−10 °C to +50 °C** | **Narrowest of the three** |

### Cold-weather charging is automatic

At 0 °C or below, charger input powers the **heating system first** and cell charging
pauses. Once the pack rises above 5 °C, heating stops and normal charging begins. A
cold-soaked pack therefore takes longer than 5.5 hours.

**Leave the charger connected and let it complete** rather than trying to bypass the
temperature protection.

Importantly, **the heating is triggered by charger input, not by pack energy** — so it
does not drain the battery while parked, and it does nothing at all when the charger is
disconnected.

### Winter storage is the real constraint

**An unheated space in a Boston winter can fall below −10 °C, which is outside the storage
range** — and because heating only runs on charger input, an unplugged pack in a cold
garage has no protection.

Two mitigations, both simple:

- **Store it somewhere heated**, or
- **Leave the charger connected during cold storage**, which both maintains charge and
  allows the heating system to engage

> TODO(verify): record where the vehicle overwinters and whether that space is heated. This
> is the one temperature limit the vehicle will realistically encounter — it will not see
> −20 °C discharge conditions or +50 °C storage in Boston, but −10 °C overnight is ordinary.

> TODO(verify): also note that cold reduces available energy regardless of protection, so
> the ~5-hour planning figure should be treated as optimistic for winter work.

## Known issues & fixes

### The LCD display is the least reliable part of the pack

**Four of the vendor's eleven published reviews describe the display failing** and being
replaced under warranty — the highest-frequency complaint by a wide margin, against an
otherwise strong review set.

**That matters more for IBEX than for a golf cart**, because this display is the only
state-of-charge indication on the vehicle.

**Mitigation:** install the Bluetooth app before relying on the LCD, so a display failure
costs visibility rather than eliminating it.

> TODO(verify): confirm the installed LCD is working, and that at least one lab phone has
> the app paired. If the display has already failed, the warranty covers it — Vatrer's
> support reportedly replaced units promptly.

### Nothing on the vehicle knows the pack's state

Covered under [State of charge](#state-of-charge). The pack reports to its own LCD and its
own app, and to nothing else. No ROS topic, no logging, no alarm.

### Charging blocks operation entirely

Covered under [Charging](#charging). Because the payload rings must come off for the
charger's rings to go on, the vehicle cannot be used while charging and cannot be charged
while used. With a 5.5-hour charge this effectively caps the vehicle at one field session
per day.

## Datasheets

Vendor product page:
<https://www.vatrerpower.com/products/vatrer-48v-105ah-heated-lithium-golf-cart-battery>

Purchase listing:
<https://www.amazon.com/VATRER-POWER-48V-105Ah-Rechargeable/dp/B0BPRR2GBR>

> TODO(verify): the product manual came in the box. **Scan it into `docs/hardware/` and
> link it here**, as with the other vendor documentation. The specifications above are
> transcribed from the vendor's website, which can change without notice; a committed PDF
> is the authority this page should be pointing at.

> TODO(verify): Vatrer publishes user guides at `vatrerpower.com/pages/user-guides` — check
> whether a PDF for this SKU is available there.

## Reorder

| | |
| --- | --- |
| Vendor | Vatrer Power |
| SKU | `D-51.2V-105AH-JR-KB` |
| Price at time of writing | $1,579.99, listed against $3,299.99 |
| Support email | `brand@vatrerpower.com` |
| Support phone | +1 (660) 260-0222, 9 am – 5 pm EST |
| Warranty | 10 years, registration at `vatrerpower.com/pages/register-warranty` |

> TODO(verify): **was the warranty registered?** A 10-year warranty on a $1,580 item is
> worth having active, and registration is usually required. Record the purchase date and
> the registration status.

Consolidate into [reorder.md](../../../99-appendix/reorder.md).

## Related pages

- [Power overview](README.md) — the tree, the budget, and endurance
- [batteries.md](../../../03-base-vehicle/batteries.md) — the vehicle battery, with
  opposite care rules
- [power-on.md](../../../02-operations/power-on.md) and
  [power-off.md](../../../02-operations/power-off.md) — the procedures
- [estop-chain.md](../../../01-safety/estop-chain.md) — what the e-stop does and does not
  isolate
- [specifications.md](../../../03-base-vehicle/specifications.md) — weight distribution
- [transport.md](../../../02-operations/transport.md) — moving a 43.8 kg lithium pack
