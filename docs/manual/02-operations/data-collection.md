---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Data collection

Recording a session, naming it, and registering it so someone else can find it later.

Assumes the stack is up — see [running-the-system.md](running-the-system.md). For what a
bag contains, see [bag-schema.md](../05-reference/bag-schema.md).

## Where data lives

Two locations, and the split matters:

| What | Where | In git? |
| --- | --- | --- |
| The bags themselves | `~/ibex_ws/rosbag_library/<collection-name>/` on Volta | **No** |
| A record of each collection | `data/<collection-name>/metadata.yaml` in this repository | **Yes** |

**Never commit a bag.** A single session with cameras running is tens of gigabytes, and
git keeps it forever. The repository tracks metadata describing each collection; the data
itself lives outside it.

`data/` contains a `COLCON_IGNORE` file so colcon does not try to build it as a package.
Leave it there.

> TODO(verify): where bags are archived long term. Recording to Volta is fine for a
> session, but Volta is not storage. Record the destination — lab NAS, external drive,
> institutional storage — and who is responsible for moving them there. Without this, the
> answer is "on Volta until someone needs the space," which is how data gets deleted.

## Before recording

- [ ] Stack up and verified — see [running-the-system.md](running-the-system.md)
- [ ] Every sensor the session needs is publishing. A bag missing a topic is often not
      noticed until analysis
- [ ] Enough free space on Volta for the expected duration
- [ ] Collection name decided, following `<site>-<subject>-<YYYY-MM-DD>` below

> TODO(verify): record how much free space a session needs. A rate figure — gigabytes per
> minute with cameras running — is more useful than a total, since it lets someone size
> any session.

## Recording

```bash
ros2 bag record -a -o $HOME/ibex_ws/rosbag_library/<collection-name> -s mcap
```

- `-a` records every topic being published.
- `-s mcap` sets the storage format.
- `-o` sets the output directory, which must not already exist.

> `-a` is the simple choice and the reason bags are large. If a session does not need the
> hyperspectral or camera streams, recording a topic subset instead will shrink the output
> by orders of magnitude. TODO(verify): record a standard subset for sessions that only
> need lidar and odometry.

Stop the recording with `Ctrl-C` before shutting down the rest of the stack.

## Naming a collection

```
<site>-<subject>-<YYYY-MM-DD>
```

All lowercase, kebab-case. Add a trailing `-<HHMM>` only when there is more than one
collection at the same site on the same day.

| Element | Meaning | Examples |
| --- | --- | --- |
| `<site>` | Where it was recorded | `exp`, `olin`, `hopkinton` |
| `<subject>` | What was being recorded — terrain, or the purpose of the run | `swamp`, `emptyfield`, `system-test` |
| `<YYYY-MM-DD>` | Date of the collection | `2026-03-31` |
| `-<HHMM>` | Optional. Start time, 24-hour, only to disambiguate same-day collections | `-1020` |

Good:

```
exp-system-test-2026-03-31
olin-swamp-2026-04-01
olin-emptyfield-2026-04-01-1020
olin-emptyfield-2026-04-01-1050
```

The directory name under `data/` and the bag directory name in `rosbag_library/` must
match. That correspondence is the only link between the metadata and the data it
describes.

### The three existing collections predate this

```
exp-systemTest-2026-03-31      # camelCase in the subject
olin-emptyfield-1020           # no date — a time where the date should be
olin-swamp-1050                # no date
```

The two Olin collections are already ambiguous: your test notes record Olin sessions on
both 2026-03-27 and 2026-04-01, and neither directory name says which trip it belongs to.

> TODO(verify): determine which date each Olin collection belongs to and rename both,
> along with their bag directories. `exp-systemTest-2026-03-31` needs only the camelCase
> corrected to `exp-system-test-2026-03-31`. Do this before there are more of them.

## metadata.yaml

Every collection gets one, committed to `data/<collection-name>/metadata.yaml`.

> TODO(verify): document the schema. Three `metadata.yaml` files already exist and none of
> their contents are recorded here, so a new person has to open an old one and imitate it —
> which is how fields drift. Paste one in and this section can be written properly.

At minimum the schema should let someone answer, without opening the bag: when and where
it was recorded, what the vehicle was doing, which sensors were live, what the intent was,
and whether the data is any good.

That last one matters more than it sounds. A collection where the throttle stuck or a
camera dropped out is still worth keeping, but only if the record says so.

## After recording

- [ ] Recording stopped before the stack came down
- [ ] `metadata.yaml` written and committed
- [ ] Bag offloaded from Volta, or its destination noted
- [ ] Anything that went wrong during the session recorded in the metadata

The rest of the post-session work is in
[checklists.md](../01-safety/checklists.md).

## Related

- [running-the-system.md](running-the-system.md) — bringing the stack up and stopping it
- [bag-schema.md](../05-reference/bag-schema.md) — recorded topic set and bag layout
- [ros-graph.md](../05-reference/ros-graph.md) — topics, types, and rates
- [checklists.md](../01-safety/checklists.md) — post-run
- [field-sites.md](field-sites.md) — where collections happen
