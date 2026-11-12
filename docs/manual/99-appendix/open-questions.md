---
status: draft
owner: TODO(verify)
last-verified: 2026-11-12
---

# Open questions

Known unknowns, grouped by who can answer them. **Questions that only need a measurement
live as `TODO(verify)` on their own page**; this page is for things that need a vendor, a
decision, or a test session.

## For Kairos Autonomi

| Question | Why it matters |
| --- | --- |
| Is `steerang` a measured angle or the commanded position on this unit? Does IBEX's P4S4 have steering position feedback at all? | On IBEX it tracks the command exactly, so there is **no steering feedback** |
| Which input feeds `rpm`, and with what pulses-per-revolution setting? | `rpm` reads 0–480 noise unrelated to the engine |
| How is the telemetry rate configured? | 9.9 Hz now; the Primer says it can be changed |
| Does the P4S4 implement the ServoPod variables — `enc2`, `ang`, `limit_r`, `limit_l`, `Hb*`, `spd`? | A steering encoder, limit switches, and motor current would give real feedback |
| What are the throttle and speed maximums set inside Kairos for IBEX? | A Kairos-side cap means 1000 is not full pedal |
| Does the P4S4 enforce the e-stop beacon's 3 s timeout? | Tells whether Volta's beacon is actually being received |
| Is freezing the actuators on motion disable the designed behaviour, and is there a setting to return them to neutral? | Determines whether the two-stage stop must stay |
| Which Windows versions does Shepherd support? | The OCU is a **discontinued** Panasonic CF-53, and it is the only route to the P4S4's configuration |

## For the lab

| Question | How to answer it |
| --- | --- |
| Does ±400 reach full steering lock, or should teleop go to 450? | On chocks, hold full stick and check the wheels; or read `limit_r` / `limit_l` if they exist |
| Where is the ~1.1 s telemetry gap — startup only, or mid-run? | `kairos_values.csv`: find `t.diff() > 0.2` |
| What caused the 291 ms `/vehicle_control` stall? | Check Volta CPU load while recording, mapping, and streaming NoMachine |
| What did Kairos PAUSE do in verification Part G? | Record in [estop-chain.md](../01-safety/estop-chain.md) |
| What hold time was set, from what measured actuator times? | Record in [estop-chain.md](../01-safety/estop-chain.md) and the configs |
| Can the actuators be moved by hand when the VIM is disarmed? | Back-drivability check, per actuator |
| Which shared variables exist on the P4S4? | The probing procedure, Part H of the verification document |
| **Where is the rest of Volta's storage?** | 8 TB understood, 2.0 TB mounted. `lsblk` and `sudo fdisk -l` |
| Is a PD adapter fitted to the USB-C dock? | Visual check. It carries a charging Insta360, a spectrometer, and a receiver on one bus-powered link |
| Does the e-stop carry full payload current? | Trace whether the SSR's input comes from Bus Bar 1 or directly from the fuse. Its 10 A thermal rating is below the pack's 13.9 A average |

## Decisions, not discoveries

These need somebody to choose, not somebody to measure.

| Decision | The trade |
| --- | --- |
| Does `wlo1` stay up during operation? | ROS 2 traffic, including the drive-by-wire path, currently reaches the lab network |
| `/synchronous_cubes` or `/corrected_cubes` for archival? | Raw is reproducible and keeps the RGB frame; corrected is 5 MB smaller and is what analysis consumes |
| Does RTAB-Map keep `-d`? | It deletes the database every launch, so no map survives a restart |
| Does KISS-ICP stay? | A second ICP pass on every 65k-point cloud, feeding nothing since `graph_frontender` was deprecated |
| Is `ibex_state` revived? | The only thing on IBEX that ever fused two IMUs, GPS, and a motion model. RTAB-Map is lidar-only |
| Best-effort or reliable for bag recording? | Reliable guarantees a complete bag; it also lets a slow recorder stall the Ouster driver |

## Resolved

Kept briefly so the same questions are not reopened.

| Question | Answer | When |
| --- | --- | --- |
| Is the Ximea VNIR camera calibrated? | **Yes** — dark and non-uniformity references now in `config/ximea/context/` | Oct 2026 |
| SWIR variant — 9 or 16 bands? | **SWIR 9**, 3 × 3 mosaic, 1119.5–1650.1 nm | Oct 2026 |
| What is the 25th Ximea mosaic position? | Position 20 at 659 nm, `selected=false`, outside the 656–974 nm bandpass | Oct 2026 |
| Is the Ouster tilt 25°? | **No — 22.44°**, derived empirically from a stationary IMU reading | Oct 2026 |
| Does anything publish `insta_imu`? | Yes — `ibex_bringup`'s static transform chain | Oct 2026 |
| Why does the gamepad fail over NoMachine? | The account was not in the `input` group; a NoMachine session is not the active local seat | Nov 2026 |
| Does `/kiss/odometry` carry a real timestamp? | Yes — KISS-ICP stamps from the input cloud, not its own sim-time clock | Oct 2026 |

## Related

- [test-log-2026-11.md](test-log-2026-11.md) — the sessions these came from
- [reorder.md](reorder.md) — vendor contacts, eight of nine still unrecorded
- Each page's own `TODO(verify)` markers
