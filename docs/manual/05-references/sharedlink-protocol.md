---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# SharedLink protocol

How Volta and the P4S4 talk to each other. Serves [Motion](../motion/README.md) and
[`shared_link_bridge`](../motion/software/shared-link-bridge.md).

Sources: Kairos *SharedLink Teleop Only ICD* (BUL-110, v1.00.15, 2016), *Shared Element
Primer* (v1.00.00, 2016), *Shared Variables, Scripts, Protocols, and Formats Overview*
(v01.00.00, 2013), checked against bags recorded on IBEX in November 2026. Keep the PDFs in
[`docs/hardware/Kairos/`](../../hardware/Kairos/).

## Model

Kairos systems share **shared variables (SVs)**: named values with a type (0 long, 2 double,
4 string). SharedLink keeps two SV lists in sync over UDP:

- **OCU → vehicle** (the bridge's outbound list, the P4S4's inbound list): commands.
- **Vehicle → OCU** (the P4S4's outbound list, the bridge's inbound list): telemetry.

Fields are matched **by position**, so order and spelling (case-sensitive) are critical on
both ends. The bridge plays the OCU role.

## Frame format

```
[:BA|N0|D<value>|D<value>|...|D|C<xx>]
```

| Part | Meaning |
| --- | --- |
| `[` `]` | Open and close the frame |
| `:BA` | Address: to A (vehicle) from B (OCU). Replies come back as `:AB` |
| `N0` | Ordinal data, OCU → vehicle ("me to you", mode 2), starting at position 0 |
| `L0` | Ordinal data or list definition, vehicle → OCU ("you to me", mode 1) |
| `D<value>` | One field per SV, in list order. A bare `D` means **unchanged since the last frame** |
| `C<xx>` | Checksum, see below |

**Delta compression.** Most frames carry only changed values; every other field is a bare
`D`. A **full frame** with every value is sent at least once per second so the two ends
resynchronise. Losing a single frame is harmless by design.

**Rate.** The Primer gives a nominal 100 ms, changeable per system. IBEX's P4S4 sends
telemetry at 9.9 Hz (measured). The bridge sends commands at 20 Hz (`update_rate` 0.05 s).

### Checksum

The sum of the ASCII codes of every character from `:` through `C` inclusive, modulo 256,
written as **two uppercase hex digits, zero-padded**. Kairos's own examples confirm the
padding: `[:BA|N0|D0|D0|D0|D0|D0|D0|D100|D0|D0|D|C07]` sums to 0x07 and is written `07`.
Frames with a wrong checksum are ignored.

> Before November 2026 the bridge wrote one digit when the sum was under 0x10
> (about 1–4% of frames), and those frames were probably dropped. Fixed; see
> [shared-link-bridge.md](../motion/software/shared-link-bridge.md).

## Other frame types

| Frame | Purpose |
| --- | --- |
| `[:BA\|P0\|Cxx]` / `[:AB\|G0\|Cxx]` | Ping / pong |
| `[:BA\|Q<name>\|Cxx]` | Named query (mode 0). Reply: `[:AB\|R<name>\|D<value>\|Cxx]`. A variable that doesn't exist returns zero or null |
| `[:BA\|N?\|Cxx]`, `[:BA\|L?\|Cxx]` | Request the outbound / inbound list |
| `[:BA\|A?\|Cxx]` | Request all shared variables |
| `[:BA\|MUI\|Cxx]`, `[:BA\|MUO\|Cxx]` | Unlock the inbound / outbound list |
| `[:BA\|ML\|Cxx]` | Lock all lists. List-definition frames are then ignored |
| `[:BA\|MW\|Cxx]` | Write the lists to the P4S4's INI file (persistent). **The bridge does not send this** |
| `[:BA\|E<pipe>\|D<command>\|Cxx]` | Pipe command to a named endpoint on the vehicle |

A `D` field inside a named-query frame would write the variable. Queries must carry no `D`.

### Pipe commands used by IBEX

| Frame body | Effect |
| --- | --- |
| `ELink\|D0, SetIP, <volta ip>:<port>, 4000` | Tell the P4S4 where to send replies |
| `ELink\|D0, outbound, on` / `off` | Start / stop the P4S4's transmissions |
| `ELink\|D0, inbound, on` / `off` | Start / stop accepting commands |
| `EServoPod\|D0,TELEOP START` / `STOP` | Enter / leave teleoperation mode |

## Connect sequence (as the bridge sends it)

1. `SetIP`, then `outbound, on` and `inbound, on`.
2. `MUI`, `MUO` (unlock both lists).
3. The OCU → vehicle list (`N0|T0|Qvideo_mux1|…`) and the vehicle → OCU list (`L0|T2|QAutoGpsHead|…`).
4. `ML` (lock). No `MW`, so nothing is saved on the P4S4.

Disconnect: `TELEOP STOP`, then `outbound, off` and `inbound, off`. A session that isn't
terminated properly can linger on the P4S4; see Known issues in
[shared-link-bridge.md](../motion/software/shared-link-bridge.md).

## OCU → vehicle list (commands)

| # | SV | Type | Units and meaning |
| --- | --- | --- | --- |
| 0 | `video_mux1` | long | Video channel |
| 1 | `veh_start` | long | Start engine, 1 = start. Keep 0 unless starting deliberately |
| 2 | `veh_enable` | long | Enable vehicle, 1 = enable |
| 3 | `veh_motion` | long | Motion enable / deadman, 1 = enabled |
| 4 | `joy_steer` | double | Steering command, **steering-wheel degrees, ±450, positive = right** |
| 5 | `veh_steer` | long | Unused on IBEX (always 0) |
| 6 | `veh_brake` | long | Brake, 0–100 % |
| 7 | `veh_throttle` | long | Throttle, 0–1000 (= 0–100.0 %) |
| 8 | `veh_shift` | long | Gear: 0 Park, 1 Reverse, 2 Neutral, 3 Drive |
| 9 | `veh_clutch` | long | Unused |

Steering sign comes from the ICD's example stream: "Steer Left" sends `joy_steer` −359 and
"Steer Right" sends +350 and +450. Confirmed on IBEX in November 2026.

**While motion is disabled, the P4S4 stores commands but does not act on them, and applies
whatever is stored the moment motion is re-enabled.** See
[estop-chain.md](../01-safety/estop-chain.md).

## Vehicle → OCU list (telemetry)

Published by the bridge as `/kairos_values` (all fields) and `/gps_values` (GPS fields).

| # | SV | Kind | Meaning |
| --- | --- | --- | --- |
| 0–6 | `AutoGpsHead`, `Lat`, `Lon`, `Vel`, `References`, `Quality`, `Stamp` | Measured | GPS heading, position, velocity, satellites, quality 0–100 %, time stamp |
| 7 | `pause` | Status | Pause state, 1 = pause |
| 8 | `key_on` | Measured | Key on, 1 = on |
| 9 | `eng_enb` | Status | Engine enable state |
| 10 | `pe7` | Status | E-stop / manual state, 1 = e-stop or manual |
| 11 | `bbrake` | **Commanded** | Commanded brake position |
| 12 | `fbrake` | **Commanded** | Commanded transmission position |
| 13 | `steerang` | **Commanded on IBEX** | See below |
| 14 | `throttle` | **Commanded** | Commanded throttle position |
| 15 | `svp_enb_eng` | Status | ServoPod enabled state |
| 16 | `serialpck` | Status | Count of ServoPod serial messages |
| 17 | `veh_gear` | **Measured** | Gear achieved: 0 shifting, 1 Park, 2 Reverse, 3 Neutral, 4 Drive |
| 18 | `veh_state` | Status | Operational state |
| 19 | `veh_estop` | Measured | In-cab e-stop, 1 = e-stop |
| 20 | `veh_obstacle` | Status | Obstacles, if available |
| 21 | `vehicle_bat` | Measured | Vehicle battery voltage |
| 22 | `run_composite` | Status | Run state string |
| 23 | `VehicleName` | Status | Vehicle name |
| 24 | `Health_total` | Status | Health 0–100 %, if available |
| 25 | `rpm` | **Not engine speed on IBEX** | See below |
| 26 | `fuel` | Measured | Fuel 0–100 %, if available |
| 27 | `sys_thd` | Measured | Temperature, °C. Requested under the wrong name until November 2026 |

- **`steerang`.** The ICD's variable table calls it the actual steering angle, but its
  telemetry list calls it the commanded steering position. On IBEX it tracks the command
  exactly: the same ±400 range, correlation 1.00, and it catches up within one telemetry
  sample (about 100 ms) of a 400° step. A real actuator can't move that fast. **Treat it as
  the command, not feedback.**
- **`rpm`.** Reads 0–480 in steps of 8, with no relation to engine state: correlation with
  vehicle speed 0.06 while driving. The tachometer input isn't connected or configured.
- **Actuator feedback.** Of the actuators, only `veh_gear` reports a measured state. Vehicle
  motion has to come from IBEX's own sensors (IMUs, lidar odometry), plus Kairos GPS.

## Variables the P4S4 may hold but IBEX doesn't stream

The 2013 overview lists ServoPod variables that would be real sensor feedback, if this unit
implements them. Probe with named queries before relying on any of them.

| SV | Meaning (2013 overview) |
| --- | --- |
| `enc2`, `ang` | Steering encoder, raw |
| `limit_r`, `limit_l` | Steering limit switches (CW / CCW) |
| `Hb2`, `Hb5`, `Hb6` | Steering H-bridge status bits, temperature, current (raw 0–255) |
| `spd`, `accumulator`, `s_ft_per_sec` | Speed from speedometer pulses |
| `steerspd` | Steering slew rate, 0–255 |
| `user_brake`, `svp_stop` | Driver pressed brake; ServoPod forcing a stop |

Names are case-sensitive and the document mixes cases (`Hb1`–`Hb9` but `hb10`–`hb16`).
TODO(verify): which of these exist on IBEX's P4S4.

## E-stop beacon

Separate from SharedLink: UDP broadcast to `255.255.255.255:7000`, once per second and
immediately on a state change. Three messages: e-stop, pause, run.

Receiver rules (the vehicle):

| Condition | Result |
| --- | --- |
| No message for 3 s | Enter e-stop |
| E-stop message | Enter e-stop immediately |
| Pause message while running | Enter pause immediately |
| Run message while in e-stop or pause | Wait 5 s, then run |

TODO(verify): whether IBEX's P4S4 enforces the 3 s rule. If it does, the beacon from Volta
must be reaching it, because the vehicle runs.

## Ports

| Use | Type | Port |
| --- | --- | --- |
| SharedLink, OCU transmit | Unicast | 4000 |
| SharedLink, OCU receive | Unicast | 4xxx (IBEX bridge: 4220) |
| E-stop beacon | Broadcast | 7000, 7001 |
| ID beacon | Broadcast | 1901, 1902 |

## Related pages

- [shared-link-bridge.md](../motion/software/shared-link-bridge.md) — the implementation
- [kairos-p4s4.md](../motion/hardware/kairos-p4s4.md) — the hardware
- [estop-chain.md](../01-safety/estop-chain.md) — stopping behaviour
