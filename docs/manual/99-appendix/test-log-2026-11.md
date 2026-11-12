---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Test log, November 2026

Teleop characterisation and safety work on IBEX. Newest first.

| Date | Session | Result |
| --- | --- | --- |
| Pending | Two-stage stop, Part H: rolling stops at walking pace; shared-variable probing | At the testing ground |
| Nov 2026 | Two-stage stop verification, Parts A–G, on chocks, engine off | All passed (see [estop-chain.md](../01-safety/estop-chain.md)) |
| Nov 11 | Chocks check of the bridge fixes | Steering direction correct; frames in ICD format; watchdog disabled motion but the brake only engaged on re-enable, which revealed the actuator freeze |
| Nov 10 | `ibex_first_run`: first teleop drive, 309 s | Throttle linkage travel too short; `rpm` shown not to be engine speed |
| Nov 10 | `steering_wheel_sweep_01` and `_02`: standstill steering sweeps | Steering inverted; `steerang` tracks the command; telemetry rates measured |
| Nov 9–10 | Standstill tests: transmission, steering, deadman | Transmission tables confirmed (second standstill test). TODO(verify): add the values |

## Bags

On Volta in `~/ibex_ws/rosbag_library/`. Copies on the Expansion drive must be re-verified
(see [bag-recording-and-analysis.md](../02-operations/bag-recording-and-analysis.md)).

| Bag | Recorded | Duration | Size | Contents |
| --- | --- | --- | --- | --- |
| `steering_wheel_sweep_01` | Nov 10, 13:32 | 97 s | 3.1 GiB | Standstill steering sweep and steps |
| `steering_wheel_sweep_02` | Nov 10, 13:34 | 177 s | 5.6 GiB | Same. The Expansion copy is incomplete |
| `ibex_first_run` | Nov 10, 14:28 | 309 s | 9.6 GiB | Teleop drive. Pre-fix bridge; throttle linkage issue |

These bags predate the bridge fixes: inverted steering, some one-digit checksums, and
`sys_thd` not requested. The Alvium camera was detached for maintenance.

## Findings

**Steering (sweep bags).**

- Every software step (joystick → `/vehicle_control` → sent frame → `steerang`) kept its
  sign. The inversion was a convention mismatch: the ROS joystick reports stick-right as
  negative, and Kairos treats negative as left.
- `steerang` matched the command: ±400 both, correlation 1.00, apparent lag 40–60 ms, and
  zero rate at the end of every steady hold. In `_01`, |`steerang` − sent| had median 0,
  mean 2.2 and max 271. It is the command, not a measurement.
- The bridge steers with `joy_steer` (±400 from teleop). `veh_steer` stayed 0.

**Telemetry and command path.**

- `/kairos_values` 9.9 Hz, with one ~1.1 s gap in every bag.
- `/vehicle_control` tracks `/joy` almost one-to-one (1,971 vs 1,966 messages). One 291 ms
  teleop stall in `_02`.
- One-digit checksums on 4.4% (`_01`), 0.8% (`_02`) and 0.9% (`first_run`) of frames.

**RPM.** 58% of samples 0, all values multiples of 8, max 480. No difference with steering
moving or still (means 19.7 vs 19.8), and none between stopped and driving (21 vs 25,
correlation with speed 0.06). Not engine speed.

**First drive.** Commanded throttle at 1000 for long stretches with little motion; top
speed about 2.4 m/s. Cause: the throttle attachment's limited travel, now being repaired.

**Actuator freeze (chocks).** Disabling motion leaves the actuators where they are, and
stored commands apply on re-enable. Led to the two-stage stop.

## Working documents

TODO(verify): export and attach, or keep the links.

- *Two-Stage Stop Verification Procedure*: https://claude.ai/artifact/HUM5rpsX8EB2BP7XFrhFqB
- *Ibex Test Procedure — 11/9/2026*: https://claude.ai/artifact/JHyvLxNsQsZ6vndA3HBJQQ
- *Ibex Autonomy To-Do List*: https://claude.ai/artifact/TZRRUZxCLyfPNtZd941doP
