---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Ownership

Who to ask. Every `<name>` below is a blank to fill in.

An owner is one person, not a team. Owning a subsystem means two things: you are the
person to ask about it, and you are responsible for its pages in this manual being
current. If you own something and its `last-verified` dates are a year old, that is your
backlog.

The one exception is "qualified to supervise," which lists everyone holding a
qualification rather than assigning a responsibility to one person.

> Do not put email addresses or phone numbers on this page. This repository is public.
> Names here, contact details in the lab directory.

## Subsystems

| Subsystem | Owner | Notes |
| --- | --- | --- |
| [Motion](../04-subsystems/motion/) | `<name>` | Drive-by-wire, P4S4, OCU, teleoperation |
| [Perception](../04-subsystems/perception/) | `<name>` | Lidar, hyperspectral, spectrometers, cameras |
| [State estimation](../04-subsystems/state-estimation/) | `<name>` | Odometry, localization, frame estimation |
| [Power](../04-subsystems/power/) | `<name>` | Batteries, converters, distribution |
| [Learning](../04-subsystems/learning/) | `<name>` | Not yet implemented |
| [Simulation](../04-subsystems/simulation/) | `<name>` | Not yet implemented |

Perception is the largest subsystem by a wide margin — six packages and eight sensors. If
one person owning all of it turns out to be unworkable, split it by sensor class here
rather than restructuring the manual.

## Packages

Package ownership does not follow subsystem ownership automatically. `ibex_bringup`
belongs to no subsystem, and several packages have a different natural owner than the
subsystem they serve.

| Package | Owner | Type |
| --- | --- | --- |
| `hyper_drive` | `<name>` | in-repo |
| `hyper_drive_interfaces` | `<name>` | in-repo |
| `ibex_bringup` | `<name>` | in-repo, cross-cutting |
| `ibex_state` | `<name>` | in-repo |
| `spectrometer_drivers` | `<name>` | in-repo |
| `spectrometer_interfaces` | `<name>` | in-repo |
| `ouster-ros` | `<name>` | submodule, fork |
| `insta360_ros_driver` | `<name>` | submodule, fork |
| `shared_link_bridge` | `<name>` | submodule, fork |
| `kiss-icp` | `<name>` | submodule, tracks upstream |

For the three forks, the owner decides what gets carried on the fork and what gets offered
upstream. For `kiss-icp`, the owner decides when to advance the pin.

## Cross-cutting responsibilities

These are not subsystems but they need a named person.

| Area | Owner | Scope |
| --- | --- | --- |
| Safety and SOP | `<name>` | Keeps the SOP current, owns [01-safety/](../01-safety/). The SOP is reviewed on a fixed interval — see [sop.md](../01-safety/sop.md). |
| Vehicle access | `<name>` | Governs access and key control under the SOP. Ask this person if you need access. |
| Qualified to supervise | James, Aidan, Ben | May supervise a new person operating the vehicle. More than one person by design — this is a qualification, not an ownership role. |
| Supervision sign-off | Tom, lab manager | Releases a new person to operate unsupervised. See [01-safety/README.md](../01-safety/README.md) for the rule. |
| Base vehicle | `<name>` | Wolverine mechanical work and the dealer service relationship. See [03-base-vehicle/](../03-base-vehicle/). |
| Electrical / wiring | `<name>` | Physical power distribution on the vehicle. Overlaps Power but is distinct: one owns the design, one owns the wiring. |
| Network and compute | `<name>` | Volta, the router, addressing. See [network.md](../05-reference/network.md). |
| Vendor accounts | `<name>` | Holds the password manager entries. See [vendor-accounts.md](../99-appendix/vendor-accounts.md). |
| Purchasing and reorder | `<name>` | Consumables and replacement parts. See [reorder.md](../99-appendix/reorder.md). |
| This manual | `<name>` | Owns structure and conventions. See [_templates/README.md](../_templates/README.md). |
| Data management | `<name>` | Bag storage, retention, the `metadata.yaml` convention. See [data-collection.md](../02-operations/data-collection.md). |

## Off-repo systems

Some things are not ours to fix.

| System | Internal contact | External |
| --- | --- | --- |
| Shepherd / OCU | `<name>` | Kairos Autonomi support |
| P4S4 hardware | `<name>` | Kairos Autonomi support |
| Wolverine service | `<name>` | Dealer service — see [troubleshooting.md](../03-base-vehicle/troubleshooting.md) |
| IMEC HSI Mosaic | `<name>` | IMEC HSI support portal |
| Pleora eBUS SDK | `<name>` | Pleora support |
| Ximea SDK | `<name>` | Ximea support |
| Allied Vision / Vimba X | `<name>` | Allied Vision support |
| Ibsen spectrometers | `<name>` | Ibsen support |
| Ouster | `<name>` | Ouster support |

TODO(verify): vendor support channels are recorded in
[vendor-accounts.md](../99-appendix/vendor-accounts.md) rather than here, so this column
should hold only the vendor name and that page should hold the routes.

## Routing common questions

| If you need to | Ask |
| --- | --- |
| Get access to the vehicle | Vehicle access owner |
| Operate the vehicle for the first time | Supervision sign-off owner |
| Fix a build that will not complete | The relevant package owner, after working the troubleshooting table in [workstation-setup.md](workstation-setup.md) |
| Get a sensor talking to Volta | The sensor's subsystem owner |
| Change a launch file that brings up multiple subsystems | `ibex_bringup` owner |
| Add or move a topic other packages consume | The package owner, then update [ros-graph.md](../05-reference/ros-graph.md) |
| Change an extrinsic or add a frame | State estimation owner, then update [tf-frames.md](../05-reference/tf-frames.md) |
| Advance a submodule pin | That submodule's owner |
| Order a part | Purchasing owner |
| Get vendor SDK credentials | Vendor accounts owner. Credentials come from the password manager, never from a file in this repository. |
| Update the SOP | Safety owner |
| Report that a manual page is wrong | The page's `owner` in its frontmatter |
| Escalate anything unresolved | `<name>` |

## Keeping this current

This page goes stale faster than anything else in the manual, because people leave. Two
rules:

- When someone leaves or hands off, update this page in the same week. An unowned
  subsystem is better recorded as `unassigned` than left pointing at someone who is gone.
- The `owner` field in each page's frontmatter must agree with this page. If they
  disagree, this page wins and the frontmatter gets corrected.

TODO(verify): decide a review interval and record it here. Every six months, matching the
SOP review, is the obvious choice.
