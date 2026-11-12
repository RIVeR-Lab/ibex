---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Recording and analysing bags

How to record field data on Volta, move it off safely, and pull teleop data out of it.

## Recording

Use `record_field.sh` (Ibex workspace). It records every topic except large data that can
be regenerated on playback, and applies the QoS override that keeps the bursty Insta360
IMU from losing samples.

```bash
record_field.sh --teleop <bag_name>          # teleop sessions
record_field.sh <bag_name>                   # manual drives
```

| Flag | Effect |
| --- | --- |
| `--teleop` | Also require `/joy` and `/vehicle_control` to be publishing |
| `--hyperspectral` | Also require `/synchronous_cubes` |
| `--keep-maps` | Record RTAB-Map's map products (otherwise excluded; they grow with the map) |
| `--keep-visualizer` | Record `/visualizer/*` |

- **Stop with Ctrl+C once** and wait for the prompt. A second Ctrl+C can leave the bag
  without its index.
- **Data rate.** About 81 MB/s with sensors and Alvium (~5 GB a minute, ~290 GB an hour);
  about 194 MB/s with the hyperspectral system. Check free space before a session.
- **Names.** One bag per maneuver, named so they sort: `<test>_<level>_<direction>_<rep>`.
  The script refuses a name that already exists.
- Suggested change: add `/kairos_values` to the topics `--teleop` requires. Without it a
  teleop bag is useless for characterisation, and the script won't currently warn.

## Topic rates (measured, November 2026)

| Topic | Rate | Notes |
| --- | --- | --- |
| `/kairos_values`, `/gps_values` | 9.9 Hz | Kairos telemetry rate. One ~1.1 s gap per bag so far |
| `/joy` | 17–20 Hz | `joy_node` autorepeat |
| `/vehicle_control` | Follows `/joy` | One command per joystick message |
| `/outbound_msgs` | 21 Hz | 20 Hz command frames plus pings |
| `/ouster/imu` | 100 Hz | |
| `/insta360/imu/data` | 94–100 Hz | Arrives in bursts (median gap 0 ms): time it by header stamp, not receive time |
| `/insta360/imu/data_raw` | ~490 Hz | |
| `/kiss/odometry`, `/rtabmap/odom` | 10 Hz | |

## Moving bags off Volta

Verify every copy. A copy of `steering_wheel_sweep_02` on the Expansion drive was missing its
last ~28 s (only 84% of messages readable, "no message indices found") while the original on
Volta was complete.

```bash
rsync -av --checksum ~/ibex_ws/rosbag_library/<bag> /media/<user>/Expansion/ibex_bags/
# or compare: sha256sum on both copies of the .mcap file
```

A damaged MCAP file can be checked and partly recovered with the `mcap` CLI:
`mcap doctor <file>.mcap` and `mcap recover <file>.mcap -o <file>_recovered.mcap`.

## Setting up an analysis machine

```bash
sudo apt install ros-humble-rosbag2-storage-mcap python3-pandas python3-matplotlib
source ~/ibex_ws/install/setup.bash    # shared_link_bridge messages must be importable
```

- Without the MCAP plugin, `ros2 bag info` still works (it only reads `metadata.yaml`), but
  reading messages fails with "Could not load/open plugin with storage id 'mcap'".
- Install pandas and matplotlib with apt, not pip. Pip can upgrade NumPy underneath ROS.
- If a topic is skipped with "cannot load shared_link_bridge/msg/…", the workspace on that
  machine doesn't build the current messages.

## extract_steering_bags.py

`~/ibex_ws/src/ibex/scripts/extract_steering_bags.py` pulls teleop data out of bags and checks
the steering chain.

```bash
python3 extract_steering_bags.py <bag_dir> [<bag_dir> ...] -o ~/ibex_analysis
```

Writes, per bag, to `~/ibex_analysis/<bag_name>/`:

| Output | Contents |
| --- | --- |
| `<topic>.csv` | One row per message for `/joy`, `/vehicle_control`, `/kairos_values`, `/gps_values`, `/outbound_msgs`, both IMUs, `/kiss/odometry`. `t` = seconds from the first message |
| `outbound_msgs.csv` | Sent frames parsed back into values (`out_*` columns) and checksum length |
| `steering_aligned.csv` | Joystick axis, command, sent value and `steerang` on one timeline |
| `steering_holds.csv` | Each steady steering hold and how fast the angle was still moving at its end |
| `summary.txt` | Topic rates and largest gaps, sign of each step in the steering chain, lag, ranges, checksum check |
| `steering_timeseries.png`, `steering_scatter.png` | Plots |

Since the steering fix, `/outbound_msgs` carries Kairos's convention while the other topics
carry ROS's, so the sign table shows two INVERTED steps by design. Joystick →
`steerang` should read "same".

## Related pages

- [shared-link-bridge.md](../motion/software/shared-link-bridge.md) — the topics recorded
- [running-the-system.md](running-the-system.md) — bringup
