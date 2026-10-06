---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Power

The electrical architecture that runs everything except the engine. No code — this
subsystem is entirely hardware.

**The authority for this subsystem is the power budget appendix**, which contains the full
load inventory, converter efficiencies, duty-cycle assumptions, and endurance derivation.
This page gives the architecture, the figures an operator needs, and the open questions.

> TODO(verify): commit the appendix into `docs/` and link it here, as with the vendor
> datasheets. It currently exists only as a Word document outside the repository, which
> means the manual's single most load-bearing reference is not version-controlled.

## Two power domains, deliberately separate

| | Vehicle battery | System battery |
| --- | --- | --- |
| Model | Renegade U1-35 AGM | [VATRER LiFePO₄, 16S](system-battery.md) |
| Rating | 12 V, 35 Ah | 51.2 V, 105 Ah, 5.376 kWh |
| Powers | The unmodified Yamaha electrical system — engine control, lighting, starter, factory accessories | The entire sensing and autonomy payload |
| Recharged by | The engine alternator, continuously | **A dedicated bench charger only** |

The separation is a design choice with three consequences worth stating plainly:

**A payload fault cannot strand the vehicle.** The Yamaha's electrical system is untouched
by anything we added.

**Engine cranking transients cannot disturb the payload.** Compute and sensing never see
the starter's current draw.

**The payload can run with the engine off**, which is the normal condition for stationary
data collection.

The cost is that **the system battery is never charged by the vehicle.** Runtime is
strictly bounded by what is in the pack when you leave, and recharging it is a between-
sessions bench operation that requires physically disconnecting the payload — see
[system-battery.md](system-battery.md). For the vehicle battery see
[batteries.md](../../03-base-vehicle/batteries.md).

### The pack is labelled 48 V and is actually 51.2 V

The label reads 48 V / 105 Ah / 5.376 kWh. **The 48 V figure is wrong and the energy
figure is right.**

| | |
| --- | --- |
| 51.2 V × 105 Ah | **5.376 kWh** — matches the label |
| 48.0 V × 105 Ah | 5.040 kWh — does not |

A 16-series LiFePO₄ pack has a true nominal of 51.2 V (16 × 3.2 V). **51.2 V is used for
every energy and runtime calculation**, and a fully charged pack rests at a measured
52.7 V.

> This supersedes the earlier recording of "48 V" in the manual and the stale Lossigy entry
> in the SOP's Appendix A. See [sop.md](../../01-safety/sop.md).

## The power tree

```
System battery  51.2 V  (5.376 kWh; 4.84 kWh usable at 90% DoD)
 │
 ├── 35 A fuse → E-stop → Latch button → BUS BAR 1 (40 A)
 │                                        │
 │   ┌── Soft-start front end ────────────┘
 │   │   pre-charge:  3 × 10 Ω thermistors in series (30 Ω cold)
 │   │   sequencing:  220 Ω resistor → Bus Bar 2 → Zener clamp (14.6 V)
 │   │                → Drok timer relay → SSR control input
 │   │   main switch: okpac SOM040100 SSR (100 V / 40 A)
 │   └── both paths converge on ↓
 │
RED WOLF MAIN BUS  (150 A)
 │
 ├── BANK A ── Cllena buck 51.2 → 12 V / 30 A (25 A in-fuse)
 │              → RECOIL DS21-516 distribution block
 │                 ├── Kairos P4S4 control      60 W idle / 240 W actuating
 │                 ├── TP-Link Archer A7 router            18 W
 │                 └── SICK picoScan150 lidar              4.5 W
 │
 ├── BANK B ── Latch #2 → BUS BAR 3 (40 A)
 │              ├── Drok variable buck 51.2 → 6 V → Bus Bar 4
 │              │    ├── Ibsen VIS-NIR spectrometer         0.8 W
 │              │    ├── Ibsen NIR spectrometer             0.8 W
 │              │    └── IMEC SWIR hyperspectral camera      18 W
 │              ├── Drok adjustable buck 51.2 → 19.6 V
 │              │    └── ASUS NUC "Volta"                   330 W  ← dominant
 │              └── Cllena buck 51.2 → 24 V / 20 A → Bus Bar 5
 │                   ├── Ouster OS1-64 lidar                 16 W
 │                   └── 2 × cooling fans (PWM, ~12 V)      ~20 W
 │
 └── AUX AC ── Cllena buck 51.2 → 24 V / 20 A
                └── MEAN WELL TS-1000-124 inverter (24 VDC → 120 VAC)
                     capacity-limited to ≤480 W by the Cllena ahead of it
                     └── laptop chargers + field monitors
                          ~250 W typical / ~400 W peak AC
```

**Bank A is what operations calls the "Kairos box"; Bank B is the "Compute and Sensing
box"; the Aux AC branch is what the monitor runs from.** The operational names and the
electrical names describe the same three things.

### The USB-powered sensors are inside the NUC's 330 W

Three sensors do not appear in the tree because they draw from Volta's USB ports rather
than from a rail:

- [Ximea VNIR camera](../perception/hardware/ximea-vnir-hsi.md) — 1.8 W
- [Alvium RGB camera](../perception/hardware/alvium-rgb-camera.md) — 2.0 W
- [Insta360 X4](../perception/hardware/insta360-x4.md) — USB-C, also charging

**Do not add them to the budget separately.** The NUC is carried at a flat 330 W worst
case, which covers them.

## Consolidated budget

All figures referred to the 51.2 V battery, so converter losses are counted explicitly
rather than as one lumped factor.

| Rail | Average (W) | Peak (W) | Pack current, avg (A) |
| --- | --- | --- | --- |
| 12 V — P4S4, router, SICK | 158 | 292 | 3.1 |
| 6 V — hyperspectral cluster | 23 | 23 | 0.45 |
| 19.6 V — ASUS NUC | **363** | **363** | 7.1 |
| 24 V — Ouster, fans | 40 | 47 | 0.8 |
| Aux AC — inverter at 40% duty | 122 | 489 | 2.4 |
| Housekeeping and control | 5 | 5 | 0.1 |
| **Total** | **~711** | **~1,219** | **~13.9** |

**Volta alone is just over half the payload draw** — 363 W of 711 W referred to the
battery, and it is carried at a flat worst case. The P4S4 and the inverter are the next
two largest and the only substantial swing loads. The sensing rails together draw under
65 W, which means powering sensors down to save energy is almost pointless.

## Engine-off endurance

| Scenario | Draw | Runtime |
| --- | --- | --- |
| Balanced mission, average | 711 W | ~6.8 h |
| **Average with 25% design margin** | — | **~5.1 h** |
| Inverter idle or off | 589 W | ~8.2 h |
| Sustained worst case, everything at peak | 1,219 W | ~4.0 h |

**Plan field sessions around the ~5 hour figure** unless a measured Volta profile justifies
extending it. See [field-sites.md](../../02-operations/field-sites.md) and
[data-collection.md](../../02-operations/data-collection.md).

Because Volta is budgeted at a conservative flat 330 W, real endurance should meet or
exceed these figures rather than fall short of them.

### The three levers, in order

**Compute load is the primary lever.** Measuring Volta's true average draw — the Drok
converter has an onboard current display — is the single most valuable refinement
available. Any reduction below 330 W extends runtime proportionally.

**Actuator duty cycle is secondary.** The P4S4 average scales directly with actuation time,
so a mission with less driving lasts longer.

**The inverter is discretionary and worth more than it looks.** At ~122 W average it is the
third-largest load; switching it off when laptops and monitors are not charging **recovers
over an hour of endurance.** Its standby saving mode caps idle draw at ~6 W.

Powering down the hyperspectral and 24 V rails is **not** a useful lever — under 65 W
between them.

## Open questions

### The e-stop's current rating needs resolving

**This is the one item on this page with a safety dimension.**

The emergency-stop switch is rated **10 A thermal current** (utilization category DC-13),
behind a 35 A fuse. The pack draws **13.9 A average and 23.8 A peak.**

| | Pack current | Versus the 10 A rating |
| --- | --- | --- |
| Average | 13.89 A | **+39%** |
| Peak | 23.81 A | **+138%** |

The appendix states that the e-stop and latch button "switch control-level current in the
power-on / interrupt path rather than the full payload current", and that the 35 A fuse
protects the heavy conductor feeding the main bus. If that is physically true, the ratings
are appropriate and there is no issue.

**But the same document also says Bus Bar 1 feeds the thermistor pre-charge path and the
SSR**, which would put the e-stop in series with the full payload current.

> TODO(verify): **trace the physical wiring and establish which it is.** Specifically,
> whether the SSR's input comes from Bus Bar 1 (downstream of the e-stop) or directly from
> the fuse (upstream of it).
>
> If the SSR is fed from Bus Bar 1, the e-stop is carrying roughly 39% above its thermal
> rating continuously, and more than twice it at peak — which is a derating issue rather
> than an immediate hazard, but it belongs in
> [estop-chain.md](../../01-safety/estop-chain.md) and in the SOP either way.
>
> DC-13 is a pilot-duty category, which supports the appendix's reading. The tree diagram
> supports the other. One of the two needs correcting.

### Everything else

| Question | Why it matters |
| --- | --- |
| Volta's measured average draw | The primary endurance lever, and the Drok converter already displays it |
| Converter efficiencies, measured | All four are estimates pending bench measurement — 90%, 85%, 91%, 90% |
| P4S4 actuation duty cycle, logged | Assumed 33%. The real fraction can be substituted directly |
| Inverter DC input voltage | Observed at 24.28 V against a 21–30 V input range and a 22.5 V low-voltage alarm. Comfortable but not generous — see below |
| Pack state-of-charge indication | Nothing recorded tells an operator how much is left mid-session |

### The inverter's low-voltage alarm

A previously recorded observation now makes sense: the inverter was reading **24.28 V**,
with a low-voltage warning at 22.5 V and shutdown at 21 V across a 21–30 V input range.

That is the **inverter's 24 V DC input from its Cllena buck**, not a battery voltage. So
the alarm concerns a converter setpoint, not pack health — and 24.28 V leaves only about
1.8 V of headroom above the warning threshold.

> TODO(verify): whether the Cllena feeding the inverter can be trimmed slightly higher.
> Under the ~400 W peak AC load this branch reaches ~489 W at the battery, essentially at
> the Cllena's 480 W ceiling, so sag under load is the likely cause.

## Design notes

### Why there is a soft-start sequence

Connecting a large capacitive load directly to a lithium pack arcs the contacts. The front
end avoids that with a timed pre-charge followed by relay bypass, which is the standard
method:

1. **Closing the main latch** energizes Bus Bar 1. Current reaches the payload only through
   three 10 Ω thermistors in series — 30 Ω cold — which charges the downstream capacitance
   gently.
2. **A 220 Ω resistor** feeds Bus Bar 2, where a 12 V Zener clamps the branch to a measured
   14.6 V to supply the Drok timer relay within its 6–30 V input range.
3. **The timer relay** times a delay, then closes and drives the SSR's control input
   (3.5–32 V, ~8.5 mA).
4. **The SSR closes**, connecting the full 51.2 V bus to the main bus and bypassing the
   now-warm thermistors, which thereafter carry negligible current.

**The operational consequence: let the sequence finish before commanding high loads.** This
is why [power-on.md](../../02-operations/power-on.md) has a wait in it rather than a
single switch throw.

### Why the inverter is capacity-limited

The MEAN WELL TS-1000-124 is rated 1000 W, and the 24 V / 20 A Cllena ahead of it caps the
branch at **≤480 W**. That is deliberate and acceptable — the intended operator load is
well inside it — but **this branch cannot be expanded without a larger converter**, and the
nameplate rating is unused headroom rather than available capacity.

### There is active cooling

Two fans run continuously through a Gebildet PWM speed controller, driven at roughly 12 V
effective rather than their rated 24 V to limit acoustic noise. That halves their power to
about 20 W from a 35 W rated figure.

> TODO(verify): record which enclosure they cool and what the temperature behaviour is on a
> hot day. At full speed the pair draws ~35 W, which shifts the system total by only ~15 W —
> so running them harder in heat costs almost nothing in endurance and should not be
> avoided for power reasons.

## Protection summary

| Element | Rating |
| --- | --- |
| Main fuse | 35 A |
| E-stop, latch buttons | 660 V, DC-13, 10 A thermal |
| Bus Bars 1 and 3 | 40 A |
| Red Wolf main bus | 150 A |
| Bank A Cllena input fuse | 25 A |
| SSR | 100 V / 40 A |

> The Red Wolf bus is marked 48 V against a 52.7 V fully charged pack — about 4% over.
> Bus-bar voltage markings are nominal insulation ratings with substantial margin, so this
> is noted for completeness rather than as a concern.

**Headroom is limited.** Peak draw is ~24 A from the pack and ~22 A on the 12 V rail
against a 30 A converter. **Verify converter capacity before adding any load to an existing
rail.**

## Related

- [system-battery.md](system-battery.md) — the VATRER pack, charging, and temperature
  limits
- [batteries.md](../../03-base-vehicle/batteries.md) — the vehicle battery
- [power-on.md](../../02-operations/power-on.md) and
  [power-off.md](../../02-operations/power-off.md) — the procedures
- [estop-chain.md](../../01-safety/estop-chain.md) — what each control actually cuts
- [sop.md](../../01-safety/sop.md) — Appendix A, which needs the battery entry corrected
- [field-sites.md](../../02-operations/field-sites.md) — planning around ~5 hours
- [04-subsystems/README.md](../README.md) — the interconnect diagram
- Per-sensor power draw is on each hardware page under **Power source / rail**
