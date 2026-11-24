#!/usr/bin/env python3
"""
Analyze /joy and /vehicle_control in a rosbag for message gaps and deadman releases.

Usage:
    source ~/ibex_ws/install/setup.bash
    python3 joy_gaps.py <bag_dir> [deadman_button_index]

    deadman_button_index defaults to 5 (RB on the F710 in X mode).
    Use the index from BUTTON in controller_teleop.py.
"""
import sys

from rosbag2_py import SequentialReader, StorageOptions, ConverterOptions, StorageFilter
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import Joy

GAP_MS = 150          # report gaps longer than this
SHORT_RELEASE_S = 0.3  # flag deadman releases shorter than this as suspicious
TOPICS = ['/joy', '/vehicle_control']

if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(1)

bag_dir = sys.argv[1]
DEADMAN_IDX = int(sys.argv[2]) if len(sys.argv) > 2 else 5

reader = SequentialReader()
reader.open(StorageOptions(uri=bag_dir, storage_id='mcap'),
            ConverterOptions('cdr', 'cdr'))
reader.set_filter(StorageFilter(topics=TOPICS))

t0 = None
prev = {}
counts = {t: 0 for t in TOPICS}
gaps = {t: [] for t in TOPICS}

# Deadman tracking
releases = []        # (time released [s], duration released [s])
released_at = None
state = None
bad_index_warned = False

while reader.has_next():
    topic, data, t_ns = reader.read_next()
    if t0 is None:
        t0 = t_ns
    counts[topic] += 1
    stamp = None

    if topic == '/joy':
        msg = deserialize_message(data, Joy)
        h = msg.header.stamp
        stamp = h.sec * 10**9 + h.nanosec
        now_s = (t_ns - t0) / 1e9

        if DEADMAN_IDX < len(msg.buttons):
            b = msg.buttons[DEADMAN_IDX]
            if state == 1 and b == 0:
                released_at = now_s
            elif state == 0 and b == 1 and released_at is not None:
                releases.append((released_at, now_s - released_at))
                released_at = None
            state = b
        elif not bad_index_warned:
            print(f'WARNING: deadman index {DEADMAN_IDX} out of range '
                  f'(message has {len(msg.buttons)} buttons)')
            bad_index_warned = True

    if topic in prev:
        p_t, p_s = prev[topic]
        recv_gap = (t_ns - p_t) / 1e6
        if recv_gap > GAP_MS:
            stamp_gap = (stamp - p_s) / 1e6 if stamp is not None and p_s is not None else None
            gaps[topic].append(((t_ns - t0) / 1e9, recv_gap, stamp_gap))
    prev[topic] = (t_ns, stamp)

if t0 is None or '/joy' not in prev:
    print('No /joy messages found in bag.')
    sys.exit(1)

end_ns = max(p[0] for p in prev.values())
dur = (end_ns - t0) / 1e9

# Gap report
for t in TOPICS:
    hz = counts[t] / dur if dur > 0 else 0.0
    print(f'\n{t}: {counts[t]} msgs, {hz:.1f} Hz, {len(gaps[t])} gaps > {GAP_MS} ms')
    for at, rg, sg in gaps[t]:
        sg_txt = f'{sg:.0f} ms' if sg is not None else 'n/a'
        print(f'  t={at:7.1f}s  receive gap {rg:6.0f} ms   header-stamp gap {sg_txt}')

# Deadman report
short = [r for r in releases if r[1] < SHORT_RELEASE_S]
print(f'\nDeadman (button index {DEADMAN_IDX}) releases: {len(releases)} '
      f'({len(short)} shorter than {SHORT_RELEASE_S*1000:.0f} ms)')
for at, d in releases:
    flag = '  <-- suspicious (short)' if d < SHORT_RELEASE_S else ''
    print(f'  t={at:7.1f}s  released for {d*1000:7.0f} ms{flag}')
if released_at is not None:
    print(f'  t={released_at:7.1f}s  released, not pressed again before end of bag')