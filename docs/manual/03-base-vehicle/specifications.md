---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Base vehicle specifications

The Yamaha Wolverine underneath IBEX, as delivered. Nothing on this page accounts for the
research payload.

For anything beyond the figures here, the owner's manual is authoritative — see
[`docs/hardware/Wolverine/`](../../hardware/Wolverine/).

## Identification

| | |
| --- | --- |
| Make and model | Yamaha Wolverine X-4 850 R-Spec |
| Model year | 2022 |
| Class | Side-by-side / UTV |

## Powertrain

| | |
| --- | --- |
| Engine | 847 cc parallel-twin, liquid-cooled, DOHC, 4 valves |
| Fuel delivery | Yamaha Fuel Injection (YFI), dual 36 mm throttle bodies |
| Transmission | Ultramatic V-belt CVT with all-wheel engine braking |
| Gear selections | Low, High, Neutral, Reverse |
| Final drive | On-Command 3-way locking differential |
| Drive modes | 2WD, 4WD, Diff Lock 4WD |

The Ultramatic is a CVT, so there is no gear to hold — engine braking is continuous.
Relevant to how the vehicle behaves when the throttle is released, which is an open
question in [checklists.md](../01-safety/checklists.md).

## Chassis

| | |
| --- | --- |
| Front suspension | Independent double wishbone, anti-sway bar, fully adjustable KYB piggyback shocks, 8.7 in travel |
| Rear suspension | Independent double wishbone, anti-sway bar, fully adjustable KYB piggyback shocks, 9.3 in travel |
| Steering shaft | 19/32 in (15 mm), 29 splines |

The steering shaft dimensions matter because the Kairos steering actuator mounts to it —
see [kairos-p4s4.md](../04-subsystems/motion/hardware/kairos-p4s4.md).

### Brakes

The brake master cylinder is mounted to the vehicle on a bracket.

Part reference:
[Partzilla — 2022 Wolverine X4 EPS R-Spec master cylinder](https://www.partzilla.com/catalog/yamaha/side-by-side/2022/wolverine-x4-eps-r-spec-yxf85wtans-barj/master-cylinder)

> TODO(verify): the source note's description of the master cylinder mounting is cut off
> mid-sentence at "generally affixed to the firewall. The firewall". Complete it, and
> record where the Kairos brake actuator interfaces with the stock system.

> TODO(verify): migrate `Wolverine Brake System.jpg` from the Obsidian vault to
> `assets/images/wolverine-brake-system-stock.jpg`. It shows the brake system before the
> Kairos installation, which is the only record of the original configuration.

## Capacities

| | |
| --- | --- |
| Fuel capacity | 35 L / 9.2 US gal |
| Fuel type | Regular unleaded, minimum 86 octane (R+M)/2 or 91 RON |
| Vehicle battery | 12 V VRLA |

Fuel handling, storage limits, and the half-tank target are in [fuel.md](fuel.md). Battery
options and charging rules are in [batteries.md](batteries.md).

## Dimensions

| | Imperial | Metric |
| --- | --- | --- |
| Length | 122.0 in / 10.2 ft | 3.10 m |
| Width | 62.2 in / 5.2 ft | 1.58 m |
| Height | 77.7 in / 6.5 ft | 1.97 m |
| Wet weight (spec) | 1,786 lb | 810 kg |

> TODO(verify): confirm what the 77.7 in height measures to — presumably the top of the
> roll cage. The sensor rack sits above it, so the as-built height of IBEX is greater and
> is the figure that matters for garage clearance and transport. Measure and record it in
> [Modified vehicle](#modified-vehicle) below.

## Weight and distribution

Measured on scales. **Pounds are authoritative** on this page; the metric column below is
computed from them, because the source note's kilogram figures contain transcription
errors.

### Corner weights

| Corner | Weight | Share |
| --- | --- | --- |
| Front left | 393 lb / 178.3 kg | 21.3% |
| Front right | 383 lb / 173.7 kg | 20.7% |
| Rear left | 496 lb / 225.0 kg | 26.9% |
| Rear right | 575 lb / 260.8 kg | 31.1% |
| **Total** | **1,847 lb / 837.8 kg** | 100% |

### Derived distribution

| Axis | Split | Percentage |
| --- | --- | --- |
| Front / rear | 776 lb / 1,074 lb | 41.9% / 58.1% |
| Left / right | 891 lb / 959 lb | 48.2% / 51.8% |
| Cross, FL + RR | 968 lb | 52.4% |
| Cross, FR + RL | 881 lb | 47.6% |

### How to read this

**These are five separate weighings, not one dataset.** The same corner was recorded as
496, 497, and 498 lb across the source tables, and the totals range from 1,847 to
1,850 lb. Treat individual corner figures as ±2 lb rather than exact, and do not expect
the derived splits above to reconcile to the corner table to the pound.

The source also notes a small disagreement between the scale's reported front percentage
(41.9%) and the percentage computed from the corner weights (42.0%). At this precision that
is measurement noise, not an error to chase.

**The vehicle is rear-biased at 58.1%**, and rear right is the heaviest corner at 31.1%.
That was measured on the base vehicle, before the 48 V system battery went in the rear and
the sensor rack went on the roof — both of which push the bias further rearward and raise
the centre of gravity. Relevant to rollover margin on the side slopes at
[Olin](../02-operations/field-sites.md).

> TODO(verify): the measured total of 1,847 lb exceeds the 1,786 lb wet weight spec by
> 61 lb. Establish whether that is accessories already fitted at the time of weighing,
> scale calibration, or a difference in what the spec counts.

## Modified vehicle

> TODO(verify): **empty, and it is the section most often needed.** IBEX as built has
> never been weighed. This blocks three things: confirming the auto transport is rated for
> the load ([transport.md](../02-operations/transport.md)), any centre-of-gravity work, and
> knowing the vehicle's real height for clearance.
>
> You own vehicle scales and have taken them to Olin. Record, with the payload fitted:
> corner weights, total, front/rear and left/right splits, overall height to the top of the
> sensor rack, and the date.

## Related

- [maintenance.md](maintenance.md) — service intervals and the shift linkage
- [batteries.md](batteries.md) — vehicle battery options
- [fuel.md](fuel.md) — fuel handling
- [troubleshooting.md](troubleshooting.md) — when it will not start
- [`docs/hardware/Wolverine/`](../../hardware/Wolverine/) — owner's manual and vendor
  documentation
- [transport.md](../02-operations/transport.md) — dimensions and weight against trailer
  limits
