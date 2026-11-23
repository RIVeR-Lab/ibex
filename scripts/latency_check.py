#!/usr/bin/env python3
"""latency_check.py - stick-to-motion latency from throttle-step bags, already extracted
by extract_steering_bags.py.

Every throttle step from rest (veh_throttle rising from <= 5 to at least MIN_STEP within
RISE_S, with the vehicle stopped and the brake off) becomes one event. For each it times:
  joy      the throttle stick leaving centre on /joy (axes.1)
  command  /vehicle_control.veh_throttle leaving 0
  sent     the first /outbound_msgs frame carrying the throttle to Kairos
  motion   the vehicle moving: from /kiss/odometry (speed crossing MOVE_SPEED, 10 Hz) and,
           finer, from /ouster/imu (acceleration departing from its at-rest value)
and reports each hop and the total from stick to motion. Steps below the launch deadband
(about 240 on Ibex) may never move the vehicle; they are reported as such.

Usage:
  python3 extract_steering_bags.py ~/ibex_ws/rosbag_library/latency_*/ -o ~/ibex_analysis
  python3 latency_check.py 'latency_*' [--root ~/ibex_analysis]

Writes latency.csv in each bag's folder and latency_all.csv in the root.
"""
import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd

MIN_STEP = 100          # veh_throttle a step must reach
RISE_S = 0.6            # ...within this long of leaving 0
STOP_SPEED = 0.15       # m/s; at rest before the step
MOVE_SPEED = 0.2        # m/s; odometry motion threshold
STICK_THRESHOLD = 0.03  # /joy throttle axis leaving centre
IMU_MIN = 0.15          # m/s2; smallest acceleration change counted as motion
IMU_SIGMAS = 4.0        # ...or this many at-rest standard deviations, whichever is larger
IMU_SMOOTH_S = 0.25     # moving average that removes engine vibration before detecting
MOTION_WINDOW_S = 6.0   # look this long after the command for motion


def speed_from_odometry(odo):
    x, y, t = (odo[c].to_numpy(float) for c in
               ('pose.pose.position.x', 'pose.pose.position.y', 't'))
    v = np.hypot(np.diff(x, prepend=x[0]), np.diff(y, prepend=y[0])) / np.maximum(
        np.diff(t, prepend=t[0] - 0.1), 1e-3)
    return pd.Series(v).rolling(3, center=True, min_periods=1).median().to_numpy()


def steps(vc, odo_t, speed):
    t = vc['t'].to_numpy(float)
    thr = vc['veh_throttle'].to_numpy(float)
    brake = vc['veh_brake'].to_numpy(float)
    out, i = [], 1
    while i < len(t):
        if thr[i - 1] <= 5 and thr[i] > 5:
            j = i
            while j < len(t) and t[j] - t[i] <= RISE_S and thr[j] < MIN_STEP:
                j += 1
            k = np.searchsorted(odo_t, t[i])
            at_rest = k < len(speed) and speed[max(k - 1, 0)] < STOP_SPEED
            if j < len(t) and thr[j] >= MIN_STEP and brake[i] == 0 and at_rest:
                out.append(i)
                i = j
        i += 1
    return out


def imu_onset(imu, t_cmd):
    if imu is None:
        return math.nan
    f = imu[[f'linear_acceleration.{c}' for c in 'xyz']].to_numpy(float)
    ti = imu['t'].to_numpy(float)
    # Engine vibration dominates the raw signal at idle, so smooth each axis first.
    n_smooth = max(1, int(round(IMU_SMOOTH_S / max(np.median(np.diff(ti)), 1e-3))))
    fs = pd.DataFrame(f).rolling(n_smooth, min_periods=1).mean().to_numpy()
    rest = (ti >= t_cmd - 1.5) & (ti <= t_cmd - 0.2)
    if rest.sum() < 20:
        return math.nan
    mean = fs[rest].mean(axis=0)
    sd = np.linalg.norm(fs[rest] - mean, axis=1).std()
    thr = max(IMU_MIN, IMU_SIGMAS * sd)
    w = (ti > t_cmd) & (ti <= t_cmd + MOTION_WINDOW_S)
    dev = np.linalg.norm(fs[w] - mean, axis=1)
    above = dev > thr
    for n in range(len(above) - 2):
        if above[n] and above[n + 1] and above[n + 2]:
            m = n                      # step back to where the departure began
            while m > 0 and dev[m - 1] > 0.3 * thr:
                m -= 1
            return float(ti[w][m])
    return math.nan


def analyse_bag(d):
    vc = pd.read_csv(d / 'vehicle_control.csv').sort_values('t')
    odo = pd.read_csv(d / 'kiss_odometry.csv').sort_values('t').reset_index(drop=True)
    joy = pd.read_csv(d / 'joy.csv').sort_values('t') if (d / 'joy.csv').exists() else None
    ob = pd.read_csv(d / 'outbound_msgs.csv').sort_values('t') if (d / 'outbound_msgs.csv').exists() else None
    imu = pd.read_csv(d / 'ouster_imu.csv').sort_values('t') if (d / 'ouster_imu.csv').exists() else None
    if ob is not None and 'msg_type' in ob:
        ob = ob[ob['msg_type'] == 'N0'].copy()
        ob['out_veh_throttle'] = ob['out_veh_throttle'].ffill()   # bare D = unchanged
    odo_t = odo['t'].to_numpy(float)
    speed = speed_from_odometry(odo)
    t_vc_all = vc['t'].to_numpy(float)
    thr_all = vc['veh_throttle'].to_numpy(float)
    rows = []
    for i in steps(vc, odo_t, speed):
        t_cmd = t_vc_all[i]
        level = float(np.median(thr_all[(t_vc_all >= t_cmd + 0.3) & (t_vc_all <= t_cmd + 1.3)]))
        row = {'bag': d.name, 't_command': t_cmd, 'level': level}
        if joy is not None and 'axes.1' in joy:
            jw = joy[(joy.t >= t_cmd - 1.0) & (joy.t <= t_cmd + 0.01) & (joy['axes.1'] > STICK_THRESHOLD)]
            row['joy_to_command_ms'] = 1e3 * (t_cmd - jw.t.iloc[0]) if len(jw) else math.nan
        if ob is not None and 'out_veh_throttle' in ob:
            ow = ob[(ob.t >= t_cmd - 0.01) & (ob['out_veh_throttle'] > 5)]
            row['command_to_sent_ms'] = 1e3 * (ow.t.iloc[0] - t_cmd) if len(ow) else math.nan
        k = np.where((odo_t > t_cmd) & (odo_t <= t_cmd + MOTION_WINDOW_S) & (speed > MOVE_SPEED))[0]
        if len(k):
            k = k[0]
            v0, v1, t0, t1 = speed[k - 1], speed[k], odo_t[k - 1], odo_t[k]
            row['command_to_motion_odom_s'] = (t0 + (MOVE_SPEED - v0) / max(v1 - v0, 1e-6) * (t1 - t0)) - t_cmd
        else:
            row['command_to_motion_odom_s'] = math.nan
        t_imu = imu_onset(imu, t_cmd)
        row['command_to_motion_imu_s'] = t_imu - t_cmd if not math.isnan(t_imu) else math.nan
        # The IMU onset can't legitimately come after the vehicle already reached MOVE_SPEED;
        # if it does, the detector missed the start (vibration), so use the odometry.
        by_imu, by_odom = row['command_to_motion_imu_s'], row['command_to_motion_odom_s']
        row['motion_source'] = 'imu' if (not math.isnan(by_imu) and (math.isnan(by_odom) or by_imu <= by_odom)) \
            else ('odom' if not math.isnan(by_odom) else 'none')
        motion = by_imu if row['motion_source'] == 'imu' else by_odom
        joy_ms = row.get('joy_to_command_ms', math.nan)
        row['stick_to_motion_s'] = motion + (joy_ms / 1e3 if not math.isnan(joy_ms) else 0.0)
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser(description='Stick-to-motion latency from throttle steps.')
    ap.add_argument('bags', nargs='+', help="extracted bag names; patterns like 'latency_*' work")
    ap.add_argument('--root', default='~/ibex_analysis')
    args = ap.parse_args()
    root = Path(args.root).expanduser()
    dirs = []
    for b in args.bags:
        dirs += sorted(p for p in root.glob(b) if p.is_dir()) if any(c in b for c in '*?[') \
            else [root / b]
    pd.set_option('display.width', 250)
    parts = []
    for d in dirs:
        if not (d / 'vehicle_control.csv').exists() or not (d / 'kiss_odometry.csv').exists():
            print(f'== {d.name}: missing vehicle_control.csv or kiss_odometry.csv, skipped')
            continue
        res = analyse_bag(d)
        print(f'== {d.name}: {len(res)} throttle step(s) from rest')
        if len(res):
            res.to_csv(d / 'latency.csv', index=False)
            print(res.drop(columns=['bag', 't_command']).round(3).to_string(index=False))
            parts.append(res)
    if not parts:
        print('No throttle steps from rest found (steps must reach '
              f'{MIN_STEP} within {RISE_S} s, from a standstill, brake off).')
        return
    allr = pd.concat(parts, ignore_index=True)
    allr.to_csv(root / 'latency_all.csv', index=False)
    moved = allr.dropna(subset=['stick_to_motion_s'])
    print(f'\n{len(allr)} step(s); {len(moved)} produced motion within {MOTION_WINDOW_S:.0f} s.')
    if len(allr) > len(moved):
        print('  Steps without motion were probably below the launch deadband (about 240).')
    if len(moved):
        print('Median of each hop:')
        for col, unit in (('joy_to_command_ms', 'ms'), ('command_to_sent_ms', 'ms'),
                          ('command_to_motion_imu_s', 's'), ('command_to_motion_odom_s', 's'),
                          ('stick_to_motion_s', 's')):
            if col in moved and moved[col].notna().any():
                print(f'  {col:26s} {moved[col].median():8.3f} {unit}   '
                      f'(range {moved[col].min():.3f} - {moved[col].max():.3f})')
        print('stick_to_motion uses the IMU onset where it is plausible (no later than the odometry), '
              'otherwise the odometry, which lags the true onset because it waits for 0.2 m/s. '
              'See motion_source per step.')
    print(f'\n-> {root / "latency_all.csv"}')


if __name__ == '__main__':
    main()
