---
status: draft
owner: TODO(verify)
last-verified: 2026-08-27
---

# Ibex User Manual

Ibex is an autonomous research vehicle in the RIVeR Lab at Northeastern, built on a Yamaha
Wolverine X-4 850 R-Spec (2022) base vehicle. This manual is the single information guide
for the system: hardware, software, electrical, mechanical, and field operations.

Throughout this manual, **Ibex** means the integrated research vehicle and **Wolverine**
means the base vehicle underneath it. They are documented separately.

## Start here

New to the vehicle? Read [00-onboarding/day-one.md](00-onboarding/day-one.md). It is the
ordered reading path for your first day and it is one page. Do not start with this file's
table of contents — it is organized for lookup, not for learning.

Two things to read before you are alone with the vehicle:

1. [01-safety/README.md](01-safety/README.md)
2. [01-safety/estop-chain.md](01-safety/estop-chain.md) — what each stop control actually cuts

Unfamiliar terms (P4S4, OCU, SharedLink, HSI, `hyper_drive`) are defined in
[00-onboarding/glossary.md](00-onboarding/glossary.md).

## How this manual is organized

Sections 00–03 are **task-ordered**: things you do, in roughly the order you will need to
do them. Sections 04–05 are **component-ordered**: how the system is built and why.

Every fact lives in exactly one place. Procedures give steps and link out to subsystem
pages for the reasoning behind them; subsystem pages do not restate procedures. If you
are following a procedure and want to know *why* a step exists, follow the link rather
than expecting the explanation inline.

## Contents

### [00-onboarding/](00-onboarding/)
| Page | What it covers |
| --- | --- |
| [day-one.md](00-onboarding/day-one.md) | Ordered reading path for a new researcher |
| [workstation-setup.md](00-onboarding/workstation-setup.md) | Clone, submodule init, dependencies, `colcon build` |
| [glossary.md](00-onboarding/glossary.md) | Acronyms, package names, vendor terms |
| [ownership.md](00-onboarding/ownership.md) | Who owns which subsystem and who to ask |

### [01-safety/](01-safety/)
| Page | What it covers |
| --- | --- |
| [README.md](01-safety/README.md) | Safety overview and non-negotiables |
| [sop.md](01-safety/sop.md) | The standard operating procedure governing EXP high bay use |
| [estop-chain.md](01-safety/estop-chain.md) | Every stop control, what it cuts, and known gaps |
| [checklists.md](01-safety/checklists.md) | Pre-run and post-run checklists |
| [hazardous-waste.md](01-safety/hazardous-waste.md) | Disposal instructions for hazardous waste from the vehicle |

### [02-operations/](02-operations/)
| Page | What it covers |
| --- | --- |
| [power-on.md](02-operations/power-on.md) | Full power-on sequence |
| [power-off.md](02-operations/power-off.md) | Full shutdown sequence |
| [running-the-system.md](02-operations/running-the-system.md) | Bringing up the software stack and driving |
| [data-collection.md](02-operations/data-collection.md) | Running a collection and the `metadata.yaml` convention |
| [transport.md](02-operations/transport.md) | Trailer rental and moving Ibex to a test site |
| [field-sites.md](02-operations/field-sites.md) | EXP high bay, Olin, and site-specific constraints |

### [03-base-vehicle/](03-base-vehicle/)
Wolverine-only content. Nothing here is specific to autonomy.

| Page | What it covers |
| --- | --- |
| [specifications.md](03-base-vehicle/specifications.md) | Drivetrain, dimensions, weight distribution |
| [maintenance.md](03-base-vehicle/maintenance.md) | Service intervals, shift linkage, doors |
| [batteries.md](03-base-vehicle/batteries.md) | Vehicle battery options and charging rules |
| [fuel.md](03-base-vehicle/fuel.md) | Fuel type, storage policy, refueling |
| [troubleshooting.md](03-base-vehicle/troubleshooting.md) | Diagnostic trees and dealer service contact |

### [04-subsystems/](04-subsystems/)
Start with the [system block diagram](04-subsystems/README.md) before reading any
individual subsystem.

| Subsystem | Scope |
| --- | --- |
| [motion/](04-subsystems/motion/) | Drive-by-wire, teleoperation, operator control unit |
| [perception/](04-subsystems/perception/) | Lidar, hyperspectral imagers, point spectrometers, cameras |
| [state-estimation/](04-subsystems/state-estimation/) | Odometry, localization, frame estimation |
| [power/](04-subsystems/power/) | Batteries, converters, inverter, distribution boxes |
| [learning/](04-subsystems/learning/) | Planned; not yet implemented |
| [simulation/](04-subsystems/simulation/) | Planned; not yet implemented |

Subsystems and code packages are not one-to-one. Perception spans several packages, some
subsystems have no code at all, and `ibex_bringup` belongs to no subsystem — it is
documented in [05-reference/launch-files.md](05-reference/launch-files.md).

### [05-reference/](05-reference/)
Lookup tables. Skim once, return often.

| Page | What it covers |
| --- | --- |
| [ros-graph.md](05-reference/ros-graph.md) | Topics, message types, publishers, subscribers, rates |
| [tf-frames.md](05-reference/tf-frames.md) | Frame tree, extrinsics, and where each is set |
| [network.md](05-reference/network.md) | Address map for the on-vehicle network |
| [launch-files.md](05-reference/launch-files.md) | What each launch file brings up |
| [bag-schema.md](05-reference/bag-schema.md) | Recorded topic set and bag layout |

### [99-appendix/](99-appendix/)
| Page | What it covers |
| --- | --- |
| [vendor-accounts.md](99-appendix/vendor-accounts.md) | Vendor portals and account names — no credentials |
| [reorder.md](99-appendix/reorder.md) | Consumables and replacement parts, with part numbers |
| [open-questions.md](99-appendix/open-questions.md) | Known unknowns and unresolved vendor questions |

## Related material in this repository

This manual is authored prose. It links into, and does not duplicate, the asset library
that already exists alongside it:

- `../hardware/` — vendor manuals, datasheets, CAD
- `../place_in_home/`, `../place_in_opt/` — configuration files and vendor SDK trees
- `../installer_archive/` — archived vendor installers
- `../../command_sheet.md` — frequently used commands

Vendor documentation is authoritative. Where this manual summarizes a vendor manual, the
PDF wins and the manual page should link to it.

## Contributing to this manual

Read [_templates/README.md](_templates/README.md) before adding a page. It covers the three
page types, where a given paragraph belongs, and the two page templates. Every page carries
`status`, `owner`, and `last-verified` frontmatter; check `last-verified` before trusting a
safety or operations page.

## Credentials and physical security

No passwords, API keys, door codes, or key storage locations appear anywhere in this
manual. Credentials live in the lab password manager. Key control is governed by the SOP.
If you find a secret in this repository, report it — rotate the credential rather than
deleting the line, because git history is permanent.
