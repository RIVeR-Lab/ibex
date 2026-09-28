---
status: draft
owner:
last-verified:
---

<!--
SOFTWARE PAGE TEMPLATE

Copy this file, rename it kebab-case, fill it in, delete these comments.

This page type is REASONING and REFERENCE. It owns what the software is, why we use it,
and the lookups needed to run it. It does NOT own operational procedures. If you are
writing "first do this, then do that, then check the LED," that belongs in 02-operations/
and this page should link to it.

Every section gets an answer. If a section does not apply, write "None" or "Not
applicable" — do not leave it blank. A blank section cannot be distinguished from an
unwritten one, which is what the `status` field in the frontmatter is for.

Do not invent values. Unknown topic names, parameter defaults, and versions get
TODO(verify) plus a note on what to run or read.
-->

# <Package or application name>

<!-- One sentence: what this is and which subsystem it serves. -->

## Source

<!--
- Upstream URL
- Where it lives in this repository (path under packages/, or "not in this repository"
  for vendor applications that run off-vehicle)
- Version, tag, or commit we are on
-->

## Fork status

<!--
For forked submodules only. Write "Not a fork" otherwise.

- Upstream URL and the branch we forked from
- Our fork URL and the branch we track
- What we changed, and why
- Is it upstreamable? If yes, has it been offered upstream?

Remember: integration documentation lives here in the parent repository, not inside the
submodule. Only genuinely upstreamable material goes in the submodule itself.
-->

## Description

<!-- Plain language. What does this software do? Assume the reader knows ROS but has
never heard of this package or this vendor. -->

## Capabilities

<!-- What you can actually do with it. Nodes and executables, one line each. -->

## Purpose

<!-- Why it is in our stack. What would break or be impossible without it. -->

## Alternative software

<!-- What else could do this job, and why we did not choose it. If we chose it because it
is the vendor's official driver, say so — that is a real reason. -->

## Launch / invocation

<!--
The exact command, copy-pasteable, with required arguments.

Use repository-relative or package-relative paths. Never hardcode a home directory or a
username — `/home/river/...` and `/home/jtukpah/...` both break for the next person.
Prefer `$(ros2 pkg prefix <pkg>)/share/...` or a path relative to the workspace root.

Note any preconditions that are NOT steps: hardware that must be powered, a network mode
that must be set, another node that must already be running. Link to the operations page
for the actual sequence rather than restating it.
-->

## Topics

<!-- Delete rows that do not apply. Direction is "pub" or "sub". -->

| Topic | Type | Direction | Notes |
| --- | --- | --- | --- |
| | | | |

## Services and actions

<!--
Write "None" if there are none.

A node that appears in `ros2 node list` but publishes nothing in `ros2 topic list` is not
necessarily broken — it may expose a service instead. Check `ros2 service list` before
concluding a node does nothing.
-->

| Service or action | Type | Node | Effect |
| --- | --- | --- | --- |
| | | | |

## Non-ROS interfaces

<!--
Write "None" if there are none.

Anything this package sends or receives outside ROS 2: raw sockets, serial, SPI, shared
memory, files. Record the address, port, direction, rate, and payload format.

This matters disproportionately. A ROS-native interface is discoverable with `ros2 topic
list`; a UDP socket is invisible to every introspection tool and will not appear in any
graph. If this package talks to hardware out-of-band, this is the only place that fact
gets written down.
-->

## Parameters

<!--
Include our value wherever it differs from the upstream default — that difference is
usually the most important thing on this page. If we changed a default, explain why in
the Effect column or link to the reason.
-->

| Parameter | Type | Upstream default | Our value | Effect |
| --- | --- | --- | --- | --- |
| | | | | |

## Dependencies

<!--
- Other Ibex packages this needs, and what it needs them for
- External SDKs or system packages, with a link to their install location
  (see docs/installer_archive/ and docs/place_in_opt/)
- Hardware that must be powered for this to do anything
-->

## Known issues & fixes

<!--
Things that have bitten us and how they were resolved. This is where setup war stories
belong — a wrong hostname in the vendor manual, a network interface that needs
reconfiguring, a config default that breaks a downstream consumer.

Format each as: symptom, cause, fix. Include the diagnostic command if there is one.
Unresolved issues stay here and get cross-referenced from 99-appendix/open-questions.md.
-->

## Understanding the software

<!--
Design rationale and anything a developer needs in their head before modifying this.
Protocol quirks, why the architecture is shaped the way it is, what the vendor got wrong.

Keep it to the software. Sensor mounting geometry, coverage analysis, and calibration
reasoning belong on the subsystem page, not here.
-->

## Related pages

<!--
Links out. Typical targets:
- The subsystem README this belongs to
- The hardware page for the device this drives
- 05-reference/ros-graph.md, tf-frames.md, network.md
- Vendor documentation in docs/hardware/ (percent-encode spaces as %20)
- Downstream consumers of this package's output
-->
