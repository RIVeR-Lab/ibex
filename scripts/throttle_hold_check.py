#!/usr/bin/env python3
"""throttle_hold_check.py - first-pass throttle calibration from throttle-hold bags
(11/9 test B3), already extracted by extract_steering_bags.py.

For every held throttle level in each bag it reports:
  - the level held (median veh_throttle) and how steady the stick was
  - the gear, from the bag name: throttle_<high|rev>_..., or the first runs' 'forward' =
    High and 'backward' = Reverse (the transmission is under manual control, so Kairos's
    veh_shift and veh_gear only show its default, Park)
  - delay from throttle applied to the vehicle moving
  - initial acceleration: slope of speed over the first ACCEL_WINDOW_S of motion
  - peak speed, and steady speed if speed levelled off before the hold ended
  - distance covered during the hold
then a summary by gear and level across all bags, and plots.

Usage:
  python3 extract_steering_bags.py ~/ibex_ws/rosbag_library/throttlehold_*/ -o ~/ibex_analysis
  python3 throttle_hold_check.py 'throttlehold_*' [--root ~/ibex_analysis]

Writes throttle_holds.csv and throttle_holds.png in each bag's folder, and
throttle_holds_all.csv and throttle_map.png in the root.
"""
import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd

MIN_THROTTLE = 20       # veh_throttle above this counts as throttle applied
LEVEL_TOL = 0.10        # within 10 % of the level (or 15 units) counts as held
MIN_HOLD_S = 2.0        # shorter holds are ignored
MOVE_SPEED = 0.15       # m/s; KISS-ICP reads ~0.05 m/s at rest
ACCEL_WINDOW_S = 1.5    # s of motion used for the initial acceleration
STEADY_WINDOW_S = 1.0   # s at the end of the hold checked for a steady speed
STEADY_ACCEL = 0.15     # m/s2; slower change than this counts as steady


def gear_from_name(name):
    """Gear from a bag name: throttle_<high|rev>_..., or the first runs' forward / backward."""
    tok = name.lower().replace('-', '_').split('_')
    if 'high' in tok:
        return 'High'
    if 'rev' in tok or 'reverse' in tok:
        return 'Reverse'
    if any(t.startswith('forward') for t in tok):
        return 'High (forward)'
    if any(t.startswith('backward') for t in tok):
        return 'Reverse'
    return '?'


def speed_from_odometry(odo):
    x, y, t = (odo[c].to_numpy(float) for c in
               ('pose.pose.position.x', 'pose.pose.position.y', 't'))
    v = np.hypot(np.diff(x, prepend=x[0]), np.diff(y, prepend=y[0])) / np.maximum(
        np.diff(t, prepend=t[0] - 0.1), 1e-3)
    return pd.Series(v).rolling(5, center=True, min_periods=1).median().to_numpy()


def slope(t, v):
    if len(t) < 3 or t[-1] - t[0] < 0.3:
        return math.nan
    return float(np.polyfit(t, v, 1)[0])


def segments(vc):
    """Contiguous stretches with throttle applied and motion on (gaps < 0.3 s bridged)."""
    on = (vc['veh_throttle'] > MIN_THROTTLE) & (vc['veh_motion'] == 1)
    t = vc['t'].to_numpy()
    out, start, last = [], None, None
    for ti, o in zip(t, on):
        if o and start is None:
            start = ti
        if o:
            last = ti
        if not o and start is not None and ti - last > 0.3:
            out.append((start, last))
            start = None
    if start is not None:
        out.append((start, last))
    return out


def analyse_bag(d):
    vc = pd.read_csv(d / 'vehicle_control.csv')
    odo = pd.read_csv(d / 'kiss_odometry.csv')
    odo_t = odo['t'].to_numpy(float)
    xy = odo[['pose.pose.position.x', 'pose.pose.position.y']].to_numpy(float)
    speed = speed_from_odometry(odo)
    rows = []
    for t0, t1 in segments(vc):
        seg = vc[(vc.t >= t0) & (vc.t <= t1)]
        level = float(seg['veh_throttle'].median())
        held = seg[(seg['veh_throttle'] - level).abs() <= max(LEVEL_TOL * level, 15)]
        if not len(held):
            continue
        th0, th1 = held.t.iloc[0], held.t.iloc[-1]
        if th1 - th0 < MIN_HOLD_S:
            continue
        row = {'bag': d.name, 't_apply': t0, 'hold_start': th0, 'hold_s': th1 - th0,
               'level': level, 'stick_std': float(held['veh_throttle'].std()),
               'brake_max': int(seg['veh_brake'].max())}
        row['gear'] = gear_from_name(d.name)
        i_apply = np.searchsorted(odo_t, t0)
        v_apply = speed[min(i_apply, len(speed) - 1)]
        row['speed_at_apply_mps'] = v_apply
        moving = np.where((odo_t >= t0) & (odo_t <= th1) & (speed > MOVE_SPEED))[0]
        if len(moving):
            tm = odo_t[moving[0]]
            row['delay_to_move_s'] = tm - t0 if v_apply <= MOVE_SPEED else math.nan
            w = (odo_t >= tm) & (odo_t <= min(tm + ACCEL_WINDOW_S, th1))
            row['accel_initial_mps2'] = slope(odo_t[w], speed[w])
        else:
            row['delay_to_move_s'] = math.nan   # never moved: below the deadband?
            row['accel_initial_mps2'] = math.nan
        h = (odo_t >= th0) & (odo_t <= th1)
        if h.any():
            row['peak_speed_mps'] = float(speed[h].max())
            tail = (odo_t >= th1 - STEADY_WINDOW_S) & (odo_t <= th1)
            end_slope = slope(odo_t[tail], speed[tail])
            row['end_accel_mps2'] = end_slope
            row['steady_speed_mps'] = (float(speed[tail].mean())
                                       if not math.isnan(end_slope) and abs(end_slope) < STEADY_ACCEL
                                       else math.nan)
            i0, i1 = np.where(h)[0][[0, -1]]
            row['hold_distance_m'] = float(np.hypot(*(xy[i1] - xy[i0])))
        rows.append(row)
    return pd.DataFrame(rows), vc, odo_t, speed


def plot_bag(d, res, vc, odo_t, speed, plt):
    fig, ax = plt.subplots(2, 1, sharex=True, figsize=(12, 6))
    ax[0].plot(odo_t, speed, lw=0.8)
    ax[0].set_ylabel('speed (m/s)')
    ax[1].plot(vc.t, vc.veh_throttle, lw=0.8, label='throttle')
    ax[1].plot(vc.t, vc.veh_brake * 10, lw=0.8, label='brake x10')
    ax[1].set_ylabel('command (0-1000)')
    ax[1].legend(loc='upper right')
    ax[1].set_xlabel('time since first message (s)')
    for r in res.itertuples():
        for a in ax:
            a.axvspan(r.hold_start, r.hold_start + r.hold_s, color='C2', alpha=0.12)
    for a in ax:
        a.grid(alpha=0.3)
    fig.suptitle(f'{d.name}: throttle holds (green)')
    fig.tight_layout()
    fig.savefig(d / 'throttle_holds.png', dpi=120)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description='First-pass throttle map from throttle-hold bags.')
    ap.add_argument('bags', nargs='+', help="extracted bag names; patterns like 'throttlehold_*' work")
    ap.add_argument('--root', default='~/ibex_analysis')
    args = ap.parse_args()
    root = Path(args.root).expanduser()
    dirs = []
    for b in args.bags:
        dirs += sorted(p for p in root.glob(b) if p.is_dir()) if any(c in b for c in '*?[') \
            else [root / b]
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        plt = None

    pd.set_option('display.width', 250)
    allres = []
    for d in dirs:
        if not (d / 'vehicle_control.csv').exists() or not (d / 'kiss_odometry.csv').exists():
            print(f'== {d.name}: missing vehicle_control.csv or kiss_odometry.csv, skipped')
            continue
        res, vc, odo_t, speed = analyse_bag(d)
        print(f'== {d.name}: {len(res)} hold(s)')
        if len(res):
            res.to_csv(d / 'throttle_holds.csv', index=False)
            cols = [c for c in ('gear', 'level', 'hold_s', 'stick_std', 'speed_at_apply_mps',
                                'delay_to_move_s', 'accel_initial_mps2', 'peak_speed_mps',
                                'steady_speed_mps', 'hold_distance_m', 'brake_max') if c in res]
            print(res[cols].round(2).to_string(index=False))
            allres.append(res)
        if plt is not None:
            plot_bag(d, res, vc, odo_t, speed, plt)
    if not allres:
        print('No throttle holds found.')
        return

    allr = pd.concat(allres, ignore_index=True)
    allr.to_csv(root / 'throttle_holds_all.csv', index=False)
    allr['level_bin'] = (allr['level'] / 10).round() * 10
    keys = ['gear', 'level_bin'] if 'gear' in allr else ['level_bin']
    summary = allr.groupby(keys).agg(
        runs=('level', 'size'),
        accel_mean=('accel_initial_mps2', 'mean'), accel_std=('accel_initial_mps2', 'std'),
        peak_speed=('peak_speed_mps', 'mean'), steady_speed=('steady_speed_mps', 'mean'),
        steady_runs=('steady_speed_mps', 'count'), delay_to_move=('delay_to_move_s', 'mean'))
    print('\nBy gear and level (veh_throttle rounded to 10):')
    print(summary.round(2).to_string())
    if allr['steady_speed_mps'].isna().any():
        print(f'\nsteady_runs < runs: in some holds speed was still changing by more than '
              f'{STEADY_ACCEL} m/s2 when the hold ended. Their peak speed is only a lower bound '
              'on the steady speed for that level.')

    if plt is not None:
        fig, ax = plt.subplots(1, 2, figsize=(12, 5))
        for gear, g in (allr.groupby('gear') if 'gear' in allr else [('all', allr)]):
            ax[0].scatter(g['level'], g['accel_initial_mps2'], label=gear, s=25)
            ax[1].scatter(g['level'], g['peak_speed_mps'], label=f'{gear}, peak', s=25,
                          facecolors='none', edgecolors='C0' if gear != 'Reverse' else 'C1')
            ax[1].scatter(g['level'], g['steady_speed_mps'], label=f'{gear}, steady', s=25)
        ax[0].set_xlabel('veh_throttle held')
        ax[0].set_ylabel('initial acceleration (m/s2)')
        ax[1].set_xlabel('veh_throttle held')
        ax[1].set_ylabel('speed (m/s)')
        for a in ax:
            a.grid(alpha=0.3)
            a.legend()
        fig.suptitle('Throttle holds: first-pass throttle map')
        fig.tight_layout()
        fig.savefig(root / 'throttle_map.png', dpi=120)
        print(f'\n-> {root / "throttle_holds_all.csv"}, {root / "throttle_map.png"}')


if __name__ == '__main__':
    main()
