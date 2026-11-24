#!/usr/bin/env python3
"""brake_hold_check.py - brake calibration from brake-hold bags, already extracted by
extract_steering_bags.py.

Every brake application that starts while Ibex is moving (veh_brake held above MIN_BRAKE
with speed above START_SPEED) becomes one event. For each it reports:
  - the brake level held (median veh_brake) and how steady it was
  - speed at the brake command
  - dead time: brake command to the vehicle actually slowing
  - steady deceleration: median deceleration once braking has built up, until slow
  - peak deceleration, time and distance to stop
  - whether the deadman was released (from /joy) or motion switched off before the vehicle
    stopped: a deadman or watchdog stop, not a hold. Releasing the deadman after the vehicle
    has stopped is normal and doesn't count; the level is measured only over the part of the
    application before that point.
then a summary by level and a brake map. Both use applications that start above
MAP_MIN_SPEED at a steady level (slow positioning stops can't be measured); deadman stops
count for deceleration, which is read before the release, but not for stopping distance.
The map is a table by brake level (which can show a non-linear brake), plus a straight-line
fit, decel = k * (brake - b0), flagged when it doesn't describe the data (r below MIN_FIT_R).

Usage:
  python3 extract_steering_bags.py ~/ibex_ws/rosbag_library/brake_*/ -o ~/ibex_analysis
  python3 brake_hold_check.py 'brake_*' [--root ~/ibex_analysis]

Writes brake_holds.csv and brake_holds.png in each bag's folder, and brake_holds_all.csv
and brake_map.png in the root.
"""
import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd

MIN_BRAKE = 5            # veh_brake above this counts as braking
START_SPEED = 0.5        # m/s; an application must start faster than this to count
STOP_SPEED = 0.15        # m/s; KISS-ICP reads ~0.05 m/s at rest
ONSET_DROP = 0.10        # m/s below the starting speed marks the start of slowing
ACCEL_FIT_S = 0.6        # centred window for the local deceleration fit
STEADY_FROM_S = 1.0      # steady deceleration is measured from this long after onset (the
                         # brake takes about 1 s to build; 0.5 s for stops too short)...
STEADY_UNTIL_SPEED = 0.8 # ...until speed falls below this
TARGET_DECELS = (0.5, 1.0, 1.5, 2.0)
MIN_FIT_R = 0.9                # below this the straight-line map is flagged as a poor fit
MAP_MIN_SPEED = 2.5            # m/s; slower applications stop too quickly to measure steady braking
MAP_MAX_LEVEL_STD = 5          # applications whose level wandered more than this are left out
DEADMAN_COL = 'buttons.5'   # RB on the F710 in X mode
STOP_HOLD_GUESS_S = 2.0     # stop_hold_time, used only when a bag has no /joy


def speed_from_odometry(odo):
    x, y, t = (odo[c].to_numpy(float) for c in
               ('pose.pose.position.x', 'pose.pose.position.y', 't'))
    v = np.hypot(np.diff(x, prepend=x[0]), np.diff(y, prepend=y[0])) / np.maximum(
        np.diff(t, prepend=t[0] - 0.1), 1e-3)
    return pd.Series(v).rolling(5, center=True, min_periods=1).median().to_numpy()


def local_accel(t, v, half=ACCEL_FIT_S / 2):
    a = np.full(len(t), math.nan)
    j0 = j1 = 0
    for i, ti in enumerate(t):
        while t[j0] < ti - half:
            j0 += 1
        while j1 < len(t) and t[j1] <= ti + half:
            j1 += 1
        if j1 - j0 >= 4:
            tt, vv = t[j0:j1], v[j0:j1]
            tc = tt - tt.mean()
            a[i] = float((tc * (vv - vv.mean())).sum() / (tc * tc).sum())
    return a


def brake_segments(vc):
    on = vc['veh_brake'] > MIN_BRAKE
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


def deadman_releases(d):
    """Times the deadman was released, from /joy, or None when the bag has no /joy."""
    if not (d / 'joy.csv').exists():
        return None
    joy = pd.read_csv(d / 'joy.csv').sort_values('t')
    if DEADMAN_COL not in joy:
        return None
    held = joy[DEADMAN_COL].to_numpy() == 1
    return joy['t'].to_numpy()[np.where(held[:-1] & ~held[1:])[0] + 1]


def analyse_bag(d):
    vc = pd.read_csv(d / 'vehicle_control.csv').sort_values('t')
    releases = deadman_releases(d)
    odo = pd.read_csv(d / 'kiss_odometry.csv').sort_values('t').reset_index(drop=True)
    t = odo['t'].to_numpy(float)
    xy = odo[['pose.pose.position.x', 'pose.pose.position.y']].to_numpy(float)
    v = speed_from_odometry(odo)
    a = local_accel(t, v)
    rows = []
    for t0, t1 in brake_segments(vc):
        i0 = np.searchsorted(t, t0)
        if i0 >= len(t) or v[i0] < START_SPEED:
            continue
        seg = vc[(vc.t >= t0) & (vc.t <= t1)]
        v0 = float(v[i0])
        end = t1 + 5.0
        stopped = np.where((t >= t0) & (t <= end) & (v < STOP_SPEED))[0]
        t_stop = t[stopped[0]] if len(stopped) else math.inf
        off = seg[seg['veh_motion'] == 0]
        t_off = off['t'].iloc[0] if len(off) else math.inf
        # A deadman release starts the two-stage stop (brake 100, motion still on), so the
        # release, not motion going off, ends the application proper.
        if releases is not None:
            later = releases[releases > t0]
            t_rel = later[0] if len(later) else math.inf
        else:
            t_rel = t_off - STOP_HOLD_GUESS_S if t_off < math.inf else math.inf
        t_end_hold = min(t_rel, t_off)
        hold = seg[seg['t'] < min(t_stop, t_end_hold)]
        if not len(hold):
            hold = seg.iloc[:1]
        row = {'bag': d.name, 't_brake': t0, 'level': float(hold['veh_brake'].median()),
               'level_std': float(hold['veh_brake'].std()) if len(hold) > 1 else 0.0,
               'speed_at_brake_mps': v0,
               'throttle_at_brake': int(vc[vc.t <= t0]['veh_throttle'].iloc[-1]) if (vc.t <= t0).any() else 0,
               'deadman_released_after_s': t_rel - t0 if t_rel < math.inf else math.nan,
               'motion_disabled_during': bool(t_end_hold < t_stop)}
        slow = np.where((t >= t0) & (t <= end) & (v <= v0 - ONSET_DROP))[0]
        if len(slow):
            row['dead_time_s'] = float(t[slow[0]] - t0)
        if len(stopped):
            i1 = stopped[0]
            row['time_to_stop_s'] = float(t[i1] - t0)
            row['stop_distance_m'] = float(np.hypot(*(xy[i1] - xy[i0])))
            row['decel_mean_mps2'] = v0 / max(t[i1] - t0, 1e-3)
        else:
            row['time_to_stop_s'] = math.nan   # released before stopping, or still rolling
        if 'dead_time_s' in row:
            t_hold_end = min(t1, t_end_hold)
            for from_s in (STEADY_FROM_S, 0.5):
                ts = t0 + row['dead_time_s'] + from_s
                w = (t >= ts) & (t <= t_hold_end) & (v >= STEADY_UNTIL_SPEED)
                if w.sum() >= 3:
                    row['decel_steady_mps2'] = float(-np.nanmedian(a[w]))
                    row['steady_from_s'] = from_s
                    break
            wp = (t >= t0) & (t <= min(t1, end))
            if wp.any():
                row['decel_peak_mps2'] = float(-np.nanmin(a[wp]))
        rows.append(row)
    return pd.DataFrame(rows), vc, t, v


def plot_bag(d, res, vc, t, v, plt):
    fig, ax = plt.subplots(2, 1, sharex=True, figsize=(12, 6))
    ax[0].plot(t, v, lw=0.8)
    ax[0].set_ylabel('speed (m/s)')
    ax[1].plot(vc.t, vc.veh_brake, lw=0.8, label='brake')
    ax[1].plot(vc.t, vc.veh_throttle / 10, lw=0.8, label='throttle / 10')
    ax[1].set_ylabel('command')
    ax[1].legend(loc='upper right')
    ax[1].set_xlabel('time since first message (s)')
    for r in res.itertuples():
        for a_ in ax:
            a_.axvline(r.t_brake, color='C3', lw=0.7, alpha=0.7)
    for a_ in ax:
        a_.grid(alpha=0.3)
    fig.suptitle(f'{d.name}: brake applications (red)')
    fig.tight_layout()
    fig.savefig(d / 'brake_holds.png', dpi=120)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description='Brake map from brake-hold bags.')
    ap.add_argument('bags', nargs='+', help="extracted bag names; patterns like 'brake_*' work")
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
        res, vc, t, v = analyse_bag(d)
        print(f'== {d.name}: {len(res)} brake application(s) while moving')
        if len(res):
            res.to_csv(d / 'brake_holds.csv', index=False)
            cols = [c for c in ('level', 'level_std', 'speed_at_brake_mps', 'throttle_at_brake',
                                'deadman_released_after_s',
                                'dead_time_s', 'decel_steady_mps2', 'decel_peak_mps2',
                                'decel_mean_mps2', 'time_to_stop_s', 'stop_distance_m',
                                'motion_disabled_during') if c in res]
            print(res[cols].round(2).to_string(index=False))
            allres.append(res)
        if plt is not None:
            plot_bag(d, res, vc, t, v, plt)
    if not allres:
        print('No brake applications found.')
        return
    allr = pd.concat(allres, ignore_index=True)
    allr.to_csv(root / 'brake_holds_all.csv', index=False)
    # Only applications from a useful speed at a steady level feed the summary and the map;
    # slow stops while positioning and wandering levels are listed above but left out.
    usable = allr[(allr['speed_at_brake_mps'] >= MAP_MIN_SPEED) & (allr['level_std'] <= MAP_MAX_LEVEL_STD)]
    left_out = len(allr) - len(usable)
    if left_out:
        print(f'\n{left_out} application(s) started below {MAP_MIN_SPEED} m/s or at an unsteady level '
              f'(spread above {MAP_MAX_LEVEL_STD}): listed above, left out of the summary and the map.')
    holds = usable[~usable['motion_disabled_during']]   # clean holds: stopping distances
    if (usable['motion_disabled_during']).any():
        print(f'{int(usable["motion_disabled_during"].sum())} of the rest had the deadman released or '
              'motion switched off before the vehicle stopped. Their deceleration (measured before the '
              'release) is in the brake map; their stopping distance is not used.')
    usable = usable.assign(level_bin=(usable['level'] / 5).round() * 5)
    holds = holds.assign(level_bin=(holds['level'] / 5).round() * 5)
    summary = usable.groupby('level_bin').agg(
        runs=('level', 'size'), speed=('speed_at_brake_mps', 'mean'),
        dead_time=('dead_time_s', 'mean'), decel_steady=('decel_steady_mps2', 'mean'),
        decel_steady_std=('decel_steady_mps2', 'std'))
    summary = summary.join(holds.groupby('level_bin').agg(
        stop_distance=('stop_distance_m', 'mean'), stop_from_speed=('speed_at_brake_mps', 'mean')))
    print('\nBy brake level (veh_brake rounded to 5; stopping distance from clean holds only):')
    print(summary.round(2).to_string())

    fit = usable.dropna(subset=['decel_steady_mps2'])
    if len(fit):
        table = fit.groupby('level_bin')['decel_steady_mps2'].agg(
            readings='count', median='median', low='min', high='max')
        table.index.name = 'brake'
        print(f'\nBrake map table (steady deceleration in m/s2, {len(fit)} readings):')
        print(table.round(2).to_string())
        table.to_csv(root / 'brake_map_table.csv')
    if len(fit) >= 3 and fit['level'].nunique() >= 2:
        k, c = np.polyfit(fit['level'], fit['decel_steady_mps2'], 1)
        r = np.corrcoef(fit['level'], fit['decel_steady_mps2'])[0, 1]
        b0 = -c / k if k > 0 else math.nan
        print(f'\nStraight-line fit ({len(fit)} readings): decel = {k:.4f} * (brake - {b0:.0f})  (r = {r:.2f})')
        if r < MIN_FIT_R or b0 < 0:
            print(f'  POOR FIT (r below {MIN_FIT_R} or a negative threshold): the brake is not linear '
                  'in its command here. Use the table above, not this line.')
        if k > 0:
            print('  Brake command for a target deceleration:')
            for target in TARGET_DECELS:
                cmd = b0 + target / k
                note = '' if cmd <= 100 else '  (beyond brake 100: not reachable)'
                print(f'    {target:.1f} m/s2: {cmd:5.0f}{note}')
        print(f'  Highest steady deceleration seen: {fit["decel_steady_mps2"].max():.2f} m/s2 '
              f'at brake {fit.loc[fit["decel_steady_mps2"].idxmax(), "level"]:.0f}')
        pd.DataFrame([{'k': k, 'b0': b0, 'r': r, 'applications': len(fit)}]).to_csv(
            root / 'brake_model.csv', index=False)
    else:
        print('\nNot enough steady-deceleration measurements at two or more levels for a brake map.')

    if plt is not None:
        fig, ax = plt.subplots(1, 2, figsize=(12, 5))
        ax[0].scatter(holds['level'], holds['decel_steady_mps2'], s=25, label='steady')
        ax[0].scatter(holds['level'], holds['decel_peak_mps2'], s=25, facecolors='none',
                      edgecolors='C1', label='peak')
        ax[0].set_xlabel('veh_brake held')
        ax[0].set_ylabel('deceleration (m/s2)')
        ax[0].legend()
        ax[1].scatter(holds['speed_at_brake_mps'], holds['stop_distance_m'], c=holds['level'], s=25)
        ax[1].set_xlabel('speed at brake command (m/s)')
        ax[1].set_ylabel('stopping distance (m)')
        for a_ in ax:
            a_.grid(alpha=0.3)
        fig.suptitle('Brake holds: brake map')
        fig.tight_layout()
        fig.savefig(root / 'brake_map.png', dpi=120)
        print(f'\n-> {root / "brake_holds_all.csv"}, {root / "brake_map.png"}')


if __name__ == '__main__':
    main()
