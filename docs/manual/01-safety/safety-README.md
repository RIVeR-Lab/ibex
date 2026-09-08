---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Safety

IBEX is an autonomous vehicle weighing over 1,800 lb with a combustion engine, a 48 V
battery system, and actuators that can move the steering, throttle, brake, and
transmission without a person touching them. It is capable of seriously injuring the
person operating it, someone working on it, or a bystander who happens to be nearby.

Everything in this section exists because of that. Read this page and
[estop-chain.md](estop-chain.md) before you are near IBEX while it is powered.

## Non-negotiables

If you remember nothing else from this page:

- **You do not operate IBEX unsupervised until you are signed off.** See below.
- **Never work underneath the vehicle.** See [Mechanical safety](#mechanical-safety) for
  the one narrow exception and who is allowed to invoke it.
- **Never work alone** on power systems, on the vehicle under its own power, or when
  lifting heavy components.
- **Disable autonomy before touching sensors, controllers, or wiring.** An engaged
  actuator can move without warning.
- **Disconnect power before any electrical work.**
- **Seatbelts on whenever the vehicle is moving**, including when someone else is driving
  it and including teleoperation with occupants aboard.
- **Engaging the drive-by-wire system does not guarantee you can take manual control.**
  See [estop-chain.md](estop-chain.md).

## Supervised period and sign-off

New researchers operate IBEX only under supervision. This is a requirement, not a
courtesy — most of what goes wrong with this vehicle goes wrong quickly, and reading a
procedure does not substitute for having done it once with someone watching.

| | |
| --- | --- |
| While supervised, you may | Observe power-on and power-off, execute procedures with a qualified person present, ride as a passenger |
| While supervised, you may not | Operate the vehicle alone, initiate autonomous or teleoperated motion, work on the electrical system unaccompanied |
| Qualified to supervise | See [ownership.md](../00-onboarding/ownership.md) |
| Releases the gate | The supervision sign-off owner in [ownership.md](../00-onboarding/ownership.md) |

Ask a qualified supervisor before doing anything with the vehicle. Sign-off comes from the
sign-off owner once a supervisor considers you ready; there is no fixed number of sessions.

Vehicle access and key control are governed by the [SOP](sop.md). If you need access, ask
the vehicle access owner. Do not look for a workaround.

## Working on the vehicle

### Personal protective equipment

Safety glasses and gloves for any work on the vehicle. Closed-toe shoes at minimum;
steel-toed boots when handling heavy components.

> TODO(verify): the source guidance lists steel-toed boots as required, then allows
> closed-toe shoes as acceptable. Pick one rule. "Required unless" is not a rule people
> can follow.

### Workspace

Keep the work area clear. Organize tools so nothing becomes a trip hazard around a vehicle
that may move.

Work with another person present when you are on the power system, lifting components, or
running the vehicle.

### Mechanical safety

**Do not go underneath IBEX.** Nothing that is routinely serviced is under there, so there
is no ordinary reason to be. Base vehicle service goes to the dealer — see
[03-base-vehicle/troubleshooting.md](../03-base-vehicle/troubleshooting.md).

The one exception: mechanical work that genuinely requires underbody access happens only
with a hydraulic lift or jack stands rated for the vehicle's weight, never on makeshift
supports and never relying on the suspension, and only with the base vehicle owner
involved. Chock the wheels first.

> TODO(verify): the source guidance says both "avoid working underneath the vehicle for
> any reason" and "never work underneath without proper lifting equipment," which are
> different rules. Written above as the stricter reading. Confirm, and record whether the
> lab has rated jack stands at all — if not, the exception should be deleted rather than
> documented.

Before moving or testing the vehicle, confirm bolts and fasteners are tight. The shift
linkage in particular needs periodic torque — see
[03-base-vehicle/maintenance.md](../03-base-vehicle/maintenance.md).

### Electrical safety

Disconnect the battery or power source before working on the electrical system. Inspect
wiring and insulation before restoring power; a loose or misplaced connection is a short
or a fire.

Use insulated tools. Verify circuits are within their rated capacity before loading them.

Power cycling has a mandatory wait — see [power-off.md](../02-operations/power-off.md).
Ignoring it damages components rather than people, but it is still a rule.

### Autonomous system safety

Disable autonomous functions before working on sensors, controllers, or software. An
actuator that is still enabled can drive the steering or throttle while your hands are
somewhere they should not be.

Clear the test area of people and obstacles before any motion. Use cones or barriers to
establish a perimeter.

When operating remotely, keep your distance, and make sure everyone present knows where
the stop controls are and what each one cuts.

## Occupant safety

Seatbelts are worn whenever the vehicle is moving.

IBEX will tell you when they are not. The vehicle sounds a seatbelt alarm while driving
with an unbelted occupant. It is most immediate in high gear, but it will eventually sound
in any gear if the vehicle is driven for a period with the driver unbelted. The alarm is
loud and continuous by design — it is not a fault, and the correct response is to fasten
the seatbelt rather than to look for a way to silence it.

## Fire, fumes, and first aid

- A fire extinguisher rated for electrical and fuel fires stays **in the vehicle**, not in
  the bay. Confirm it is aboard as part of the pre-run checklist.
- Ventilate when working with fuel or batteries.
- A first aid kit is kept in the workspace.
- Emergency service and supervisor contact information is posted in the work area.

> TODO(verify): record where the extinguisher is mounted, where the first aid kit lives,
> and where emergency contacts are posted. "Somewhere in the bay" is not findable under
> pressure.

## Fuel and hazardous materials

Gasoline is a hazardous material and the university does not permit storing it in the high
bay. Fuel in the vehicle's tank is acceptable; fuel in a container is not.

- Handling, storage limits, and refueling: [03-base-vehicle/fuel.md](../03-base-vehicle/fuel.md)
- Removing fuel from the vehicle and requesting disposal:
  [hazardous-waste.md](hazardous-waste.md)

## Reporting

Report near misses, not just incidents. A locked steering wheel that did not cause a crash
is the same defect as one that did.

> TODO(verify): name the reporting channel and who receives it. The lab has been recording
> lessons learned informally; this section should point at whatever becomes the real
> destination.

## This section

| Page | What it covers |
| --- | --- |
| [sop.md](sop.md) | The standard operating procedure governing vehicle use in the EXP high bay, and its review cycle |
| [estop-chain.md](estop-chain.md) | Every stop control, what each one cuts, and the known gaps |
| [checklists.md](checklists.md) | Pre-run and post-run checklists |
| [hazardous-waste.md](hazardous-waste.md) | Fuel disposal and hazardous waste requests through the university |

Related:

- [02-operations/power-on.md](../02-operations/power-on.md) and
  [power-off.md](../02-operations/power-off.md) — the sequences themselves
- [04-subsystems/motion/hardware/kairos-p4s4.md](../04-subsystems/motion/hardware/kairos-p4s4.md)
  — why back-drivability is a problem
- [00-onboarding/ownership.md](../00-onboarding/ownership.md) — who to ask
