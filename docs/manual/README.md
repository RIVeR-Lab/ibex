---
status: draft
owner: TODO(verify)
last-verified: 2026-11-09
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

## Current status

Most of the manual is written. What is not:

| | |
| --- | --- |
| **The system block diagram** | [04-subsystems/README.md](04-subsystems/README.md) has interconnect and processing diagrams. The combined view — sensors → compute → actuators with network segments **and** power rails overlaid — is still missing |
| `04-subsystems/learning/` | Scoped but not written. See [Learning](#04-subsystems) |
| `04-subsystems/simulation/` | Not written |
| `99-appendix/vendor-accounts.md` | Not written |
| `99-appendix/open-questions.md` | Not written |

**Pages carry `TODO(verify)` markers** where a fact is unconfirmed. Those are not
decoration — they mark things that were inferred, measured once, or taken from a note
rather than from the system. Check `last-verified` before trusting a safety or operations
page.

## Contents

### [00-onboarding/](00-onboarding/)
| Page | What it covers |
| --- | --- |
| [day-one.md](00-onboarding/day-one.md) | Ordered reading path for a new researcher |
| [workstation-setup.md](00-onboarding/workstation-setup.md) | Clone, submodule init, dependencies, `colcon build`, host configuration |
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
| [running-the-system.md](02-operations/running-the-system.md) | Bringing up the software stack, driving, and teleop troubleshooting |
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
Start with [04-subsystems/README.md](04-subsystems/README.md) before reading any
individual subsystem.

| Subsystem | Scope | Pages |
| --- | --- | --- |
| [motion/](04-subsystems/motion/) | Drive-by-wire, teleoperation, operator control unit | 4 hardware, 3 software |
| [perception/](04-subsystems/perception/) | Lidar, hyperspectral imagers, point spectrometers, cameras | 8 hardware, 4 software |
| [state-estimation/](04-subsystems/state-estimation/) | Lidar odometry and the GTSAM factor graph | 2 software, no hardware |
| [power/](04-subsystems/power/) | Batteries, converters, inverter, distribution, soft-start | 1 hardware, no software |
| [learning/](04-subsystems/learning/) | Material classification and traversability models | Scoped, not written |
| [simulation/](04-subsystems/simulation/) | Planned; not yet implemented | Not written |

Subsystems and code packages are not one-to-one. Perception spans several packages, some
subsystems have no code at all, and two things belong to no subsystem: `ibex_bringup`,
documented in [05-reference/launch-files.md](05-reference/launch-files.md), and Volta
itself, documented in [05-reference/compute.md](05-reference/compute.md).

**Motion is worth a note.** Three things configure or command the P4S4 and they are
different: `shared_link_bridge` on Volta sends runtime commands, Shepherd on the OCU opens
a VNC session into the controller, and JAUS_IVN runs on the P4S4 and holds its persistent
configuration. See [motion/software/](04-subsystems/motion/software/).

### [05-reference/](05-reference/)
Lookup tables. Skim once, return often.

| Page | What it covers |
| --- | --- |
| [ros-graph.md](05-reference/ros-graph.md) | Topics, message types, publishers, subscribers, QoS, rates |
| [tf-frames.md](05-reference/tf-frames.md) | Frame tree, extrinsics, and where each is set |
| [network.md](05-reference/network.md) | Address map for the on-vehicle network |
| [compute.md](05-reference/compute.md) | Volta — specifications, storage, thermal limits, access |
| [launch-files.md](05-reference/launch-files.md) | What each launch file brings up |
| [bag-schema.md](05-reference/bag-schema.md) | What to record, what it costs, and for how long |

### [99-appendix/](99-appendix/)
| Page | What it covers |
| --- | --- |
| [reorder.md](99-appendix/reorder.md) | Part numbers, serials, and vendors for everything on the vehicle |
| [bom.csv](99-appendix/bom.csv) | The dissertation parts list — the integration build |
| [vendor-accounts.md](99-appendix/vendor-accounts.md) | Vendor portals and account names — no credentials |
| [open-questions.md](99-appendix/open-questions.md) | Known unknowns and unresolved vendor questions |

`reorder.md` and `bom.csv` cover almost disjoint sets and both are needed — the first is
the vehicle's components, the second is what was bought to integrate them.

## Related material in this repository

This manual is authored prose. It links into, and does not duplicate, the asset library
that already exists alongside it:

| Path | Contents |
| --- | --- |
| `../hardware/` | Vendor manuals, datasheets, CAD |
| `../place_in_home/`, `../place_in_opt/` | Configuration files and vendor SDK trees |
| `../installer_archive/` | Archived vendor installers |
| `../ben_notes.md` | Working notes, including the derivation of empirically measured transforms |
| `../../command_sheet.md` | Frequently used commands |

Documents that are authoritative for their subject and should be committed alongside:

- **IBEX System Power Budget** — the load inventory and endurance derivation behind
  [04-subsystems/power/](04-subsystems/power/)
- **Kairos Autonomi bulletins**, e.g. BUL-023 behind
  [jaus-ivn.md](04-subsystems/motion/software/jaus-ivn.md)
- **The traversability pipeline plan**, behind the Learning subsystem

Vendor documentation is authoritative. Where this manual summarizes a vendor manual, the
PDF wins and the manual page should link to it.

### Configuration that lives outside the repository

Three files are load-bearing and not version-controlled. They would be lost with the
machine:

| File | What it is |
| --- | --- |
| `~/allied_vision_config.xml` | Alvium camera settings |
| `~/ibex_ws/config/fastdds_large_msgs.xml` | The DDS profile every node uses |
| `/etc/sysctl.d/60-ros2-dds.conf` | Kernel buffer settings for large-message DDS |

See [05-reference/compute.md](05-reference/compute.md).

## Contributing to this manual

Read [_templates/README.md](_templates/README.md) before adding a page. It covers the three
page types, where a given paragraph belongs, and the templates:

| Template | For |
| --- | --- |
| [software-page.md](_templates/software-page.md) | A ROS package or application |
| [hardware-page.md](_templates/hardware-page.md) | A physical component |
| [context-readme.md](_templates/context-readme.md) | A hyperspectral camera calibration context |

Every page carries `status`, `owner`, and `last-verified` frontmatter.

**Do not invent technical facts.** Topic names, parameters, pinouts, and torque values are
either measured, read from source, or marked `TODO(verify)` with a note saying what to go
and check.

## Credentials and physical security

No passwords, API keys, door codes, or key storage locations appear anywhere in this
manual. Credentials live in the lab password manager. Key control is governed by the SOP.
If you find a secret in this repository, report it — rotate the credential rather than
deleting the line, because git history is permanent.
