#!/usr/bin/env python3
"""extract_steering_bags.py - pull Ibex teleop data out of rosbag2 bags and
check the steering chain end to end.

For each bag directory given, writes to OUT_DIR/<bag_name>/:
  <topic>.csv              one row per message, flattened to columns.
                           t = seconds since the first extracted message,
                           t_ns = recorder receive time
  outbound_msgs.csv        SharedLink frames parsed back into the command
                           values actually sent to the P4S4 (out_* columns)
  steering_aligned.csv     joystick axis, /vehicle_control, sent command and
                           /kairos_values.steerang on one timeline
  steering_holds.csv       every stretch where the steering command held
                           steady, and how fast the angle was still moving
                           at the end of it (position vs rate control)
  summary.txt              topic rates and largest gaps, the sign of each hop
                           in the steering chain, command-to-telemetry lag,
                           value ranges, outbound checksum check
  steering_timeseries.png  and steering_scatter.png, if matplotlib is present

Usage:
  source ~/ibex_ws/install/setup.bash    # shared_link_bridge must be importable
  python3 extract_steering_bags.py BAG [BAG ...] [-o OUT_DIR]
      [--steer-axis N] [--topics /extra/topic ...] [--storage mcap]

Example:
  python3 extract_steering_bags.py \\
      /media/jtukpah/Expansion/ibex_bags/steering_wheel_sweep_01 \\
      /media/jtukpah/Expansion/ibex_bags/steering_wheel_sweep_02 \\
      -o ~/ibex_analysis

Requires ROS 2 Humble (rosbag2_py, rclpy), numpy and pandas; matplotlib for
the plots.
"""
import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd

# Topics extracted by default, and the CSV name each one is written to.
# Point clouds and images are left out on purpose.
DEFAULT_TOPICS = {
    '/joy': 'joy',
    '/vehicle_control': 'vehicle_control',
    '/kairos_values': 'kairos_values',
    '/gps_values': 'gps_values',
    '/outbound_msgs': 'outbound_msgs',
    '/ouster/imu': 'ouster_imu',
    '/insta360/imu/data': 'insta360_imu',
    '/kiss/odometry': 'kiss_odometry',
}

# Order of the D fields in an outbound N0 frame (SharedLinkOutbound in
# shared_link_bridge_node.py). A bare 'D' means "unchanged since last frame".
OUTBOUND_FIELDS = ['video_mux1', 'veh_start', 'veh_enable', 'veh_motion', 'joy_steer',
                   'veh_steer', 'veh_brake', 'veh_throttle', 'veh_shift', 'veh_clutch']

MAX_SEQ = 64        # longer arrays are stored as a length only
HOLD_MIN_S = 1.5    # shortest steady command that counts as a hold
HOLD_TAIL_S = 0.5   # end-of-hold window used to measure residual motion
MAX_LAG_S = 2.0     # largest command-to-telemetry lag searched for
LAG_FS = 50.0       # resampling rate for the lag estimate, Hz


# ------------------------------------------------------------------ extraction

def flatten(msg, prefix=''):
    """Flatten a ROS 2 message to {column: value}. Nested messages become
    dotted names; short arrays become name.0, name.1, ..."""
    out = {}
    for name in msg.get_fields_and_field_types():
        val = getattr(msg, name)
        key = prefix + name
        if hasattr(val, 'get_fields_and_field_types'):
            out.update(flatten(val, key + '.'))
        elif isinstance(val, str):
            out[key] = val
        elif isinstance(val, (bytes, bytearray)):
            out[key + '.len'] = len(val)
        elif hasattr(val, '__len__'):
            if len(val) > MAX_SEQ:
                out[key + '.len'] = len(val)
                continue
            for i, item in enumerate(val):
                if hasattr(item, 'get_fields_and_field_types'):
                    out.update(flatten(item, f'{key}.{i}.'))
                else:
                    out[f'{key}.{i}'] = item
        else:
            out[key] = val
    return out


def parse_outbound(frame):
    """Parse one SharedLink frame as built by SharedLinkNode._prep_for_send():
    '[:BA|N0||D<v>|D<v>|...|C<checksum>]'."""
    row = {'raw': frame}
    body = frame.strip()
    if body.startswith('[') and body.endswith(']'):
        body = body[1:-1]
    parts = body.split('|')
    row['msg_type'] = parts[1] if len(parts) > 1 else ''
    checksum = parts[-1][1:] if parts and parts[-1].startswith('C') else ''
    row['checksum'] = checksum
    row['checksum_len'] = len(checksum)
    d_fields = [p for p in parts[2:-1] if p.startswith('D')]
    if row['msg_type'] == 'N0' and len(d_fields) == len(OUTBOUND_FIELDS):
        row['full_frame'] = all(p != 'D' for p in d_fields)
        for name, p in zip(OUTBOUND_FIELDS, d_fields):
            try:
                row['out_' + name] = float(p[1:]) if len(p) > 1 else math.nan
            except ValueError:
                row['out_' + name] = math.nan
    return row


def read_bag(bag_path, topics, storage_id):
    """Return {topic: DataFrame} for each requested topic present in the bag."""
    import rosbag2_py
    from rclpy.serialization import deserialize_message
    from rosidl_runtime_py.utilities import get_message

    reader = rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=str(bag_path), storage_id=storage_id),
                rosbag2_py.ConverterOptions(input_serialization_format='cdr',
                                            output_serialization_format='cdr'))
    in_bag = {t.name: t.type for t in reader.get_all_topics_and_types()}

    msg_types = {}
    for topic in topics:
        if topic not in in_bag:
            print(f'  skip {topic}: not in this bag')
            continue
        try:
            msg_types[topic] = get_message(in_bag[topic])
        except (AttributeError, ModuleNotFoundError, ValueError) as exc:
            print(f'  skip {topic}: cannot load {in_bag[topic]} ({exc}). '
                  'Source the workspace that builds it.')
    if not msg_types:
        return {}
    reader.set_filter(rosbag2_py.StorageFilter(topics=list(msg_types)))

    rows = {topic: [] for topic in msg_types}
    while reader.has_next():
        topic, data, t_ns = reader.read_next()
        msg = deserialize_message(data, msg_types[topic])
        row = parse_outbound(msg.data) if topic == '/outbound_msgs' else flatten(msg)
        if 'header.stamp.sec' in row:
            row['header_t'] = row['header.stamp.sec'] + row['header.stamp.nanosec'] * 1e-9
        row['t_ns'] = t_ns
        rows[topic].append(row)
    del reader

    frames = {topic: pd.DataFrame(r) for topic, r in rows.items() if r}
    return add_relative_time(frames)


def add_relative_time(frames):
    """Add t (s since the first extracted message) as the first column."""
    if not frames:
        return frames
    t0 = min(int(df['t_ns'].min()) for df in frames.values())
    for topic, df in frames.items():
        df = df.sort_values('t_ns').reset_index(drop=True)
        df.insert(0, 't', (df['t_ns'] - t0) / 1e9)
        frames[topic] = df
    return frames


# -------------------------------------------------------------------- analysis

def corr(a, b):
    """Pearson correlation over finite pairs; NaN if either side is constant."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 3 or a[ok].std() == 0 or b[ok].std() == 0:
        return math.nan
    return float(np.corrcoef(a[ok], b[ok])[0, 1])


def varies(df, col):
    return df is not None and col in df and df[col].dropna().std() > 0


def topic_rates(frames):
    lines = ['Topic rates (recorder receive time)']
    for topic, df in frames.items():
        t = df['t'].to_numpy()
        if len(t) < 2:
            lines.append(f'  {topic:22s} {len(t):6d} msgs')
            continue
        gaps = np.diff(t)
        lines.append(f'  {topic:22s} {len(t):6d} msgs  {(len(t) - 1) / (t[-1] - t[0]):6.1f} Hz  '
                     f'median period {np.median(gaps) * 1e3:6.1f} ms  '
                     f'max gap {gaps.max() * 1e3:7.1f} ms')
    return lines


def checksum_check(ob):
    if ob is None or 'checksum_len' not in ob or len(ob) == 0:
        return []
    short = int((ob['checksum_len'] == 1).sum())
    return ['', f'Outbound checksums: {short} of {len(ob)} frames have a 1-digit checksum '
                f'({100 * short / len(ob):.1f}%). Nonzero means checksums are not zero-padded.']


def pick_steer_axis(joy, vc, override):
    """The /joy axis that best tracks the steering command in /vehicle_control."""
    if override is not None:
        return f'axes.{override}', 'set by --steer-axis'
    axes = [c for c in joy.columns if c.startswith('axes.')]
    ref = next((c for c in ('veh_steer', 'joy_steer') if varies(vc, c)), None)
    if not axes or ref is None:
        return None, 'no varying steering field in /vehicle_control'
    m = pd.merge_asof(joy[['t'] + axes], vc[['t', ref]], on='t',
                      direction='nearest', tolerance=0.1)
    scores = {c: abs(corr(m[c], m[ref])) for c in axes}
    scores = {c: s for c, s in scores.items() if np.isfinite(s)}
    if not scores:
        return None, 'no joystick axis moved'
    best = max(scores, key=scores.get)
    return best, f'auto: best match to /vehicle_control.{ref}, |r| = {scores[best]:.2f}'


def lag_estimate(t_cmd, cmd, t_meas, meas):
    """Delay (s) at which the sent command best matches the reported angle,
    and the correlation there. The command is held between samples (it is a
    step signal); the telemetry is interpolated."""
    t_cmd, cmd = np.asarray(t_cmd, float), np.asarray(cmd, float)
    t_meas, meas = np.asarray(t_meas, float), np.asarray(meas, float)
    ok_c, ok_m = np.isfinite(cmd), np.isfinite(meas)
    t_cmd, cmd, t_meas, meas = t_cmd[ok_c], cmd[ok_c], t_meas[ok_m], meas[ok_m]
    if len(cmd) < 3 or len(meas) < 3:
        return math.nan, math.nan
    lo, hi = max(t_cmd[0], t_meas[0]), min(t_cmd[-1], t_meas[-1])
    if hi - lo < 2 * MAX_LAG_S:
        return math.nan, math.nan
    grid = np.arange(lo, hi, 1.0 / LAG_FS)
    c = cmd[np.clip(np.searchsorted(t_cmd, grid, side='right') - 1, 0, len(cmd) - 1)]
    m = np.interp(grid, t_meas, meas)
    best_lag, best_r = math.nan, 0.0
    for k in range(int(MAX_LAG_S * LAG_FS) + 1):
        r = corr(c[:len(c) - k], m[k:])
        if np.isfinite(r) and abs(r) > abs(best_r):
            best_lag, best_r = k / LAG_FS, r
    return best_lag, (best_r if np.isfinite(best_lag) else math.nan)


def find_holds(t, cmd, meas):
    """Stretches where the command stayed within 1% of its range for at least
    HOLD_MIN_S, with the angle's rate of change over the last HOLD_TAIL_S."""
    t, cmd, meas = (np.asarray(x, float) for x in (t, cmd, meas))
    ok = np.isfinite(t) & np.isfinite(cmd) & np.isfinite(meas)
    t, cmd, meas = t[ok], cmd[ok], meas[ok]
    if len(t) < 2:
        return pd.DataFrame()
    tol = max(0.01 * (cmd.max() - cmd.min()), 1e-9)
    holds, start = [], 0
    for i in range(1, len(t) + 1):
        if i < len(t) and abs(cmd[i] - cmd[start]) <= tol:
            continue
        dur = t[i - 1] - t[start]
        if dur >= HOLD_MIN_S:
            ts, ms = t[start:i], meas[start:i]
            tail = ts >= ts[-1] - HOLD_TAIL_S
            span = ts[tail][-1] - ts[tail][0]
            rate = (ms[tail][-1] - ms[tail][0]) / span if span > 0 else 0.0
            holds.append({'t_start': t[start], 'duration_s': dur, 'command': cmd[start],
                          'steerang_start': ms[0], 'steerang_end': ms[-1],
                          'steerang_rate_at_end_per_s': rate})
        start = i
    return pd.DataFrame(holds)


def steering_analysis(frames, steer_axis=None):
    """Align the steering chain on the /kairos_values timeline and summarize it."""
    kv = frames.get('/kairos_values')
    vc = frames.get('/vehicle_control')
    joy = frames.get('/joy')
    ob = frames.get('/outbound_msgs')
    res = {'aligned': None, 'holds': pd.DataFrame(), 'axis_col': None,
           'cmd_col': None, 'lines': ['', 'Steering chain']}
    lines = res['lines']
    if kv is None or 'steerang' not in kv:
        lines.append('  /kairos_values.steerang missing; steering analysis skipped.')
        return res

    aligned = kv[['t', 'steerang']].copy()
    sources = {}  # column -> (t, values) at its own rate, for the lag estimate

    def attach(df, cols, prefix=''):
        nonlocal aligned
        cols = [c for c in cols if c in df]
        if not cols:
            return
        sub = df[['t'] + cols].rename(columns={c: prefix + c for c in cols})
        for c in cols:
            sources[prefix + c] = (df['t'].to_numpy(), df[c].to_numpy(float))
        aligned = pd.merge_asof(aligned, sub, on='t', direction='backward')

    if joy is not None and vc is not None:
        axis_col, how = pick_steer_axis(joy, vc, steer_axis)
        lines.append(f'  Joystick steering axis: {axis_col} ({how})')
        if axis_col in joy:
            res['axis_col'] = axis_col
            attach(joy.rename(columns={axis_col: 'joy_axis'}), ['joy_axis'])
    if vc is not None:
        attach(vc, ['joy_steer', 'veh_steer', 'veh_motion', 'veh_enable'], prefix='vc_')
    if ob is not None and 'out_veh_steer' in ob:
        n0 = ob[ob['msg_type'] == 'N0'].copy()
        out_cols = [c for c in n0.columns if c.startswith('out_')]
        n0[out_cols] = n0[out_cols].ffill()  # bare D = unchanged since last frame
        attach(n0, ['out_joy_steer', 'out_veh_steer', 'out_veh_motion'])
    res['aligned'] = aligned

    lines.append('  Sign of each hop (r = correlation; negative = inverted):')
    hops = [
        ('joystick axis -> /vehicle_control.veh_steer', 'joy_axis', 'vc_veh_steer'),
        ('joystick axis -> /vehicle_control.joy_steer', 'joy_axis', 'vc_joy_steer'),
        ('/vehicle_control.veh_steer -> sent veh_steer', 'vc_veh_steer', 'out_veh_steer'),
        ('/vehicle_control.joy_steer -> sent joy_steer', 'vc_joy_steer', 'out_joy_steer'),
        ('sent veh_steer -> /kairos_values.steerang', 'out_veh_steer', 'steerang'),
        ('sent joy_steer -> /kairos_values.steerang', 'out_joy_steer', 'steerang'),
        ('joystick axis -> /kairos_values.steerang', 'joy_axis', 'steerang'),
    ]
    for label, a, b in hops:
        if a in aligned and b in aligned:
            r = corr(aligned[a], aligned[b])
            verdict = ('one side constant' if not np.isfinite(r)
                       else 'same' if r > 0 else 'INVERTED')
            lines.append(f'    {label:46s} r = {r:+.2f}  {verdict}')
    lines.append('  ROS joy drivers usually report stick-right as a NEGATIVE axis value '
                 '(REP 103: left is positive).')
    lines.append('  Confirm with `ros2 topic echo /joy` while pushing the right stick right.')

    cmd_col = next((c for c in ('out_veh_steer', 'out_joy_steer', 'vc_veh_steer', 'vc_joy_steer')
                    if c in aligned and aligned[c].dropna().std() > 0), None)
    res['cmd_col'] = cmd_col
    if cmd_col:
        t_c, v_c = sources[cmd_col]
        lag, r = lag_estimate(t_c, v_c, kv['t'], kv['steerang'])
        lines.append(f'  Lag {cmd_col} -> steerang: {lag * 1e3:.0f} ms (r = {r:+.2f}). '
                     'Resolution is limited by the /kairos_values rate.')
        holds = find_holds(aligned['t'], aligned[cmd_col], aligned['steerang'])
        res['holds'] = holds
        if len(holds):
            lines.append(f'  Holds of {HOLD_MIN_S:.1f} s or longer: {len(holds)}. Median |steerang '
                         f'rate| over the last {HOLD_TAIL_S:.1f} s: '
                         f'{holds["steerang_rate_at_end_per_s"].abs().median():.3f} per s.')
            lines.append('  Near zero at the end of each hold = position-commanded; still moving '
                         'toward the stop = rate-commanded. See steering_holds.csv.')
        else:
            lines.append('  No steady holds found.')

    lines.append('  Ranges (min .. max):')
    for c in ('joy_axis', 'vc_joy_steer', 'vc_veh_steer', 'out_joy_steer', 'out_veh_steer',
              'steerang'):
        if c in aligned:
            s = aligned[c].dropna()
            if len(s):
                lines.append(f'    {c:14s} {s.min():10.3f} .. {s.max():10.3f}')
    if 'vc_veh_motion' in aligned:
        on = (aligned['vc_veh_motion'].dropna() != 0).mean()
        lines.append(f'  veh_motion nonzero (likely deadman held) for {100 * on:.0f}% of samples.')
    return res


# ----------------------------------------------------------------------- plots

def plot_steering(out_dir, frames, res, title):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print('  matplotlib not installed; skipping plots')
        return
    aligned, axis_col, cmd_col = res['aligned'], res['axis_col'], res['cmd_col']
    joy, vc = frames.get('/joy'), frames.get('/vehicle_control')
    kv = frames['/kairos_values']

    fig, ax = plt.subplots(3, 1, sharex=True, figsize=(12, 8))
    if joy is not None and axis_col in joy:
        ax[0].plot(joy['t'], joy[axis_col], lw=0.8)
        ax[0].set_ylabel(f'/joy {axis_col}')
    if varies(vc, 'veh_steer'):
        ax[1].plot(vc['t'], vc['veh_steer'], lw=0.8, color='C1')
        ax[1].set_ylabel('veh_steer', color='C1')
    if varies(vc, 'joy_steer'):
        twin = ax[1].twinx()
        twin.plot(vc['t'], vc['joy_steer'], lw=0.8, color='C2')
        twin.set_ylabel('joy_steer', color='C2')
    ax[2].plot(kv['t'], kv['steerang'], lw=0.8, color='C3')
    ax[2].set_ylabel('steerang')
    ax[2].set_xlabel('time since first message (s)')
    if 'vc_veh_motion' in aligned:
        off = aligned['vc_veh_motion'].to_numpy() == 0  # NaN (before first command) is not shaded
        for a in ax:
            a.fill_between(aligned['t'], 0, 1, where=off, step='post', color='0.88',
                           transform=a.get_xaxis_transform(), zorder=0)
    for a in ax:
        a.grid(alpha=0.3)
    fig.suptitle(f'{title}: /joy -> /vehicle_control -> /kairos_values '
                 '(grey = veh_motion 0)')
    fig.tight_layout()
    fig.savefig(out_dir / 'steering_timeseries.png', dpi=120)
    plt.close(fig)

    if cmd_col:
        fig, a = plt.subplots(figsize=(6.5, 6))
        sc = a.scatter(aligned[cmd_col], aligned['steerang'], c=aligned['t'], s=6)
        fig.colorbar(sc, label='time (s)')
        a.set_xlabel(cmd_col.replace('out_', 'sent ').replace('vc_', '/vehicle_control.'))
        a.set_ylabel('/kairos_values.steerang')
        a.set_title(f'{title}: command vs reported angle')
        a.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(out_dir / 'steering_scatter.png', dpi=120)
        plt.close(fig)


# ------------------------------------------------------------------------ main

def process(frames, out_dir, title, topics, steer_axis):
    for topic, df in frames.items():
        df.to_csv(out_dir / f'{topics.get(topic, topic.strip("/").replace("/", "_"))}.csv',
                  index=False)
    lines = topic_rates(frames) + checksum_check(frames.get('/outbound_msgs'))
    res = steering_analysis(frames, steer_axis)
    lines += res['lines']
    if res['aligned'] is not None:
        res['aligned'].to_csv(out_dir / 'steering_aligned.csv', index=False)
        if len(res['holds']):
            res['holds'].to_csv(out_dir / 'steering_holds.csv', index=False)
        plot_steering(out_dir, frames, res, title)
    return lines


def main():
    ap = argparse.ArgumentParser(description='Extract Ibex teleop bags to CSV and '
                                             'check the steering chain.')
    ap.add_argument('bags', nargs='+', help='bag directories')
    ap.add_argument('-o', '--out', default='bag_analysis', help='output root directory')
    ap.add_argument('--storage', default='mcap', help='rosbag2 storage id (default: mcap)')
    ap.add_argument('--steer-axis', type=int, help='/joy axis index for steering '
                    '(default: detected from /vehicle_control)')
    ap.add_argument('--topics', nargs='+', default=[], help='extra topics to extract')
    args = ap.parse_args()

    topics = dict(DEFAULT_TOPICS)
    for t in args.topics:
        topics[t] = t.strip('/').replace('/', '_')

    for bag in args.bags:
        bag = Path(bag).expanduser().resolve()
        out_dir = Path(args.out).expanduser() / bag.name
        out_dir.mkdir(parents=True, exist_ok=True)
        print(f'== {bag.name}')
        frames = read_bag(bag, list(topics), args.storage)
        if not frames:
            print('  nothing extracted')
            continue
        lines = [f'Bag: {bag}', ''] + process(frames, out_dir, bag.name, topics,
                                              args.steer_axis)
        (out_dir / 'summary.txt').write_text('\n'.join(lines) + '\n')
        print('\n'.join(lines))
        print(f'  -> {out_dir}\n')


if __name__ == '__main__':
    main()
