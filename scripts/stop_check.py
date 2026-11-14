#!/usr/bin/env python3
"""stop_check.py - check deadman-release and watchdog stops in a bag already
extracted by extract_steering_bags.py.

For every release of the deadman (right bumper, /joy buttons.5, 1 -> 0) it reports:
  - whether the two-stage stop ran: right after the release, /vehicle_control must show
    throttle 0 and brake applied with veh_motion still 1, and veh_motion should drop
    to 0 only after the hold time. The old code dropped veh_motion immediately.
  - the hold time actually used (release -> veh_motion 0)
  - speed at release, time and distance to stop, from /kiss/odometry
  - deceleration overall, during the hold (motion still on) and after it
  - creep: how far the vehicle moved in the CREEP_WINDOW_S after it stopped

Releases while motion was already off (the interlock holding an enable back), and
stops interrupted by pressing the deadman again (which resumes control), are labelled
as such rather than counted as stops.

Watchdog stops (teleop killed while motion is on, verification test H2) are found as a
silence on /vehicle_control longer than WATCHDOG_GAP_S with motion enabled. Their
two stages are read from what the bridge actually sent (/outbound_msgs), and the
bridge's log lines are matched from /rosout when it was extracted (--topics /rosout).

Usage:
  python3 extract_steering_bags.py <bag_dir> -o ~/ibex_analysis --topics /rosout
  python3 stop_check.py <bag_name> [--root ~/ibex_analysis]

Writes stop_check.csv (deadman releases), stop_check_watchdog.csv (watchdog stops)
and stop_check.png next to the extracted CSVs.
"""
import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd

DEADMAN_COL = 'buttons.5'   # RB on the F710 in X mode
STOP_SPEED = 0.15           # m/s; KISS-ICP reads ~0.05 m/s at rest
CREEP_WINDOW_S = 5.0        # s after the stop over which creep is measured
STAGE_WINDOW_S = 5.0        # s after release in which to look for the stop sequence
BRAKE_APPLIED = 50          # veh_brake at or above this counts as braking
WATCHDOG_GAP_S = 0.45       # /vehicle_control silence that counts as teleop stopping


def speed_from_odometry(odo):
    """Speed (m/s) from position differences; KISS-ICP may leave twist empty."""
    x, y, t = (odo[c].to_numpy(float) for c in
               ('pose.pose.position.x', 'pose.pose.position.y', 't'))
    v = np.hypot(np.diff(x, prepend=x[0]), np.diff(y, prepend=y[0])) / np.maximum(
        np.diff(t, prepend=t[0] - 0.1), 1e-3)
    return pd.Series(v).rolling(5, center=True, min_periods=1).median().to_numpy()


def releases(joy):
    held = joy[DEADMAN_COL].to_numpy() == 1
    idx = np.where(held[:-1] & ~held[1:])[0] + 1
    return joy['t'].to_numpy()[idx]


def speed_at(odo_t, speed, t):
    return float(np.interp(t, odo_t, speed))


def check_release(t_rel, vc, odo_t, odo_xy, speed, next_press):
    row = {'t_release': t_rel}
    before = vc[vc.t <= t_rel]
    row['enabled_at_release'] = bool(len(before) and before.veh_motion.iloc[-1] == 1)
    # Teleop not publishing at the moment of release (killed, as in H2): the bridge
    # watchdog owns that stop, and it is reported in the watchdog section instead.
    row['teleop_silent'] = bool(not len(before) or t_rel - before.t.iloc[-1] > WATCHDOG_GAP_S)
    if row['teleop_silent']:
        i0 = np.searchsorted(odo_t, t_rel)
        if i0 < len(odo_t):
            row['speed_at_release_mps'] = speed[i0]
        return row
    after = vc[(vc.t > t_rel) & (vc.t <= t_rel + STAGE_WINDOW_S)]
    resume_t = math.inf
    if len(after):
        first = after.iloc[0]
        row['stage1_seen'] = bool(first.veh_motion == 1 and first.veh_throttle == 0
                                  and first.veh_brake >= BRAKE_APPLIED)
        row['old_behaviour'] = bool(row['enabled_at_release'] and first.veh_motion == 0)
        row['brake_cmd'] = int(after.veh_brake.max())
        # A re-press during the hold resumes control: motion stays on, brake released.
        resumed = after[(after.veh_motion == 1) & (after.veh_brake < BRAKE_APPLIED)]
        off = after[after.veh_motion == 0]
        t_off = off.t.iloc[0] if len(off) else math.inf
        if len(resumed) and resumed.t.iloc[0] < t_off:
            resume_t = resumed.t.iloc[0]
            row['resumed_after_s'] = resume_t - t_rel
        row['hold_time_s'] = t_off - t_rel if t_off < resume_t else math.nan
    i0 = np.searchsorted(odo_t, t_rel)
    if i0 >= len(odo_t):
        return row
    v0 = speed[i0]
    row['speed_at_release_mps'] = v0
    end = min(resume_t, next_press if not row['enabled_at_release'] else math.inf,
              t_rel + 20.0)
    stopped = np.where((odo_t >= t_rel) & (odo_t <= end) & (speed < STOP_SPEED))[0]
    if len(stopped):
        i1 = stopped[0]
        t_stop = odo_t[i1] - t_rel
        row['time_to_stop_s'] = t_stop
        row['stop_distance_m'] = float(np.hypot(*(odo_xy[i1] - odo_xy[i0])))
        i2 = np.searchsorted(odo_t, min(odo_t[i1] + CREEP_WINDOW_S, next_press)) - 1
        row['creep_m'] = float(np.hypot(*(odo_xy[max(i2, i1)] - odo_xy[i1])))
        if v0 > STOP_SPEED and t_stop > 0:
            row['decel_mean_mps2'] = (v0 - speed[i1]) / t_stop
            hold = row.get('hold_time_s', math.nan)
            if not math.isnan(hold) and t_stop > hold + 0.2:
                v_h = speed_at(odo_t, speed, t_rel + hold)
                row['decel_during_hold_mps2'] = (v0 - v_h) / hold
                row['decel_after_hold_mps2'] = (v_h - speed[i1]) / (t_stop - hold)
    else:
        row['time_to_stop_s'] = math.nan   # never dropped below STOP_SPEED in the window
    return row


def measure_stop(t0, t_hold_end, end, odo_t, odo_xy, speed, next_limit):
    """Speed at t0, then time and distance until speed < STOP_SPEED, creep afterwards,
    and deceleration overall, before t_hold_end and after it."""
    row = {}
    i0 = np.searchsorted(odo_t, t0)
    if i0 >= len(odo_t):
        return row
    v0 = speed[i0]
    row['speed_at_start_mps'] = v0
    stopped = np.where((odo_t >= t0) & (odo_t <= end) & (speed < STOP_SPEED))[0]
    if not len(stopped):
        row['time_to_stop_s'] = math.nan
        return row
    i1 = stopped[0]
    t_stop = odo_t[i1] - t0
    row['time_to_stop_s'] = t_stop
    row['stop_distance_m'] = float(np.hypot(*(odo_xy[i1] - odo_xy[i0])))
    i2 = np.searchsorted(odo_t, min(odo_t[i1] + CREEP_WINDOW_S, next_limit)) - 1
    row['creep_m'] = float(np.hypot(*(odo_xy[max(i2, i1)] - odo_xy[i1])))
    if v0 > STOP_SPEED and t_stop > 0:
        row['decel_mean_mps2'] = (v0 - speed[i1]) / t_stop
        hold = t_hold_end - t0
        if not math.isnan(hold) and 0 < hold and t_stop > hold + 0.2:
            v_h = speed_at(odo_t, speed, t_hold_end)
            row['decel_during_hold_mps2'] = (v0 - v_h) / hold
            row['decel_after_hold_mps2'] = (v_h - speed[i1]) / (t_stop - hold)
    return row


def watchdog_events(vc, ob, rosout, odo_t, odo_xy, speed):
    """Teleop silences with motion on, and what the bridge sent during each."""
    t = vc['t'].to_numpy(float)
    motion = vc['veh_motion'].to_numpy()
    n0 = ob[ob['msg_type'] == 'N0'].copy()
    cols = [c for c in n0.columns if c.startswith('out_')]
    n0[cols] = n0[cols].ffill()          # bare D = unchanged since the last frame
    ends = list(np.where(np.diff(t) > WATCHDOG_GAP_S)[0])
    if len(t) and len(odo_t) and odo_t[-1] - t[-1] > WATCHDOG_GAP_S:
        ends.append(len(t) - 1)           # teleop never came back in this bag
    rows = []
    for i in ends:
        if motion[i] != 1:
            continue                      # motion was off: nothing for the watchdog to do
        t_last = t[i]
        gap_end = t[i + 1] if i + 1 < len(t) else math.inf
        after = n0[(n0['t'] > t_last) & (n0['t'] < min(gap_end, t_last + 15))]
        s1 = after[(after['out_veh_motion'] == 1) & (after['out_veh_throttle'] == 0)
                   & (after['out_veh_brake'] >= BRAKE_APPLIED)]
        s2 = after[after['out_veh_motion'] == 0]
        t_s1 = s1['t'].iloc[0] if len(s1) else math.nan
        t_s2 = s2['t'].iloc[0] if len(s2) else math.nan
        row = {'t_teleop_last_cmd': t_last,
               'teleop_silent_s': gap_end - t_last,
               'stage1_after_s': t_s1 - t_last,
               'hold_s': t_s2 - t_s1,
               'brake_sent': after['out_veh_brake'].max() if len(after) else math.nan}
        if rosout is not None and 'msg' in rosout:
            win = rosout[(rosout['t'] > t_last) & (rosout['t'] < t_last + 15)]
            for key, text in (('log_stage1_after_s', 'stage 1'), ('log_stage2_after_s', 'stage 2')):
                hit = win[win['msg'].astype(str).str.contains(f'Watchdog stop {text}')]
                row[key] = hit['t'].iloc[0] - t_last if len(hit) else math.nan
        resumed = vc[(vc['t'] > t_last) & (vc['veh_motion'] == 1) & (vc['veh_throttle'] > 0)]
        end = min(resumed['t'].iloc[0] if len(resumed) else math.inf, t_last + 20.0)
        row.update(measure_stop(t_last, t_s2 if not math.isnan(t_s2) else math.nan,
                                end, odo_t, odo_xy, speed, end))
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser(description='Check deadman-release stops in an extracted bag.')
    ap.add_argument('bag_name')
    ap.add_argument('--root', default='~/ibex_analysis', help='extract_steering_bags.py output root')
    args = ap.parse_args()
    d = Path(args.root).expanduser() / args.bag_name

    joy = pd.read_csv(d / 'joy.csv')
    vc = pd.read_csv(d / 'vehicle_control.csv')
    odo = pd.read_csv(d / 'kiss_odometry.csv')
    odo_t = odo['t'].to_numpy(float)
    odo_xy = odo[['pose.pose.position.x', 'pose.pose.position.y']].to_numpy(float)
    speed = speed_from_odometry(odo)

    joy_t = joy['t'].to_numpy()
    held = joy[DEADMAN_COL].to_numpy() == 1
    press_t = joy_t[np.where(~held[:-1] & held[1:])[0] + 1]

    rows = []
    for t_rel in releases(joy):
        later = press_t[press_t > t_rel]
        next_press = later[0] if len(later) else math.inf
        rows.append(check_release(t_rel, vc, odo_t, odo_xy, speed, next_press))
    res = pd.DataFrame(rows)
    print(f'{args.bag_name}: {len(res)} deadman release(s)')
    if len(res):
        res.to_csv(d / 'stop_check.csv', index=False)
        print()
        print(res.round(3).to_string(index=False))
    moving = res[res.get('speed_at_release_mps', pd.Series(dtype=float)) > STOP_SPEED] \
        if len(res) else res
    if len(res):
        print(f'\nReleases while moving (> {STOP_SPEED} m/s): {len(moving)}')
    for r in moving.itertuples():
        g = lambda name: getattr(r, name, math.nan)
        if g('teleop_silent') is True:
            print(f'  t={r.t_release:7.2f} s  teleop was not running at release: part of a '
                  'watchdog stop, see below')
            continue
        if not g('enabled_at_release'):
            print(f'  t={r.t_release:7.2f} s  {r.speed_at_release_mps:.2f} m/s  motion was '
                  'already off at release: nothing to stop')
            continue
        verdict = ('two-stage stop' if g('stage1_seen') is True
                   else 'OLD single-stage behaviour' if g('old_behaviour') is True
                   else 'stop sequence unclear')
        resumed = g('resumed_after_s')
        if isinstance(resumed, float) and not math.isnan(resumed):
            print(f'  t={r.t_release:7.2f} s  {r.speed_at_release_mps:.2f} m/s  {verdict}; '
                  f'deadman pressed again after {resumed:.2f} s, control resumed (not a stop)')
            continue
        if math.isnan(g('time_to_stop_s')):
            stop = 'did NOT drop below the stop speed within 20 s'
        else:
            stop = (f'stopped in {r.time_to_stop_s:.2f} s over {r.stop_distance_m:.2f} m, '
                    f'creep {r.creep_m:.2f} m, mean decel {g("decel_mean_mps2"):.2f} m/s2')
            if not math.isnan(g('decel_after_hold_mps2')):
                stop += (f' (during hold {g("decel_during_hold_mps2"):.2f}, '
                         f'after {g("decel_after_hold_mps2"):.2f})')
        print(f'  t={r.t_release:7.2f} s  {r.speed_at_release_mps:.2f} m/s  {verdict}, '
              f'hold {r.hold_time_s:.2f} s; {stop}')

    wres = pd.DataFrame()
    if (d / 'outbound_msgs.csv').exists():
        ob = pd.read_csv(d / 'outbound_msgs.csv')
        rosout = pd.read_csv(d / 'rosout.csv') if (d / 'rosout.csv').exists() else None
        wres = watchdog_events(vc, ob, rosout, odo_t, odo_xy, speed)
        print(f'\nWatchdog stops (teleop silent > {WATCHDOG_GAP_S} s with motion on): {len(wres)}')
        if rosout is None:
            print('  (no rosout.csv: extract with --topics /rosout to match the bridge log lines)')
        if len(wres):
            wres.to_csv(d / 'stop_check_watchdog.csv', index=False)
            print(wres.round(3).to_string(index=False))
            for r in wres.itertuples():
                g = lambda name: getattr(r, name, math.nan)
                stage = ('two-stage stop' if not math.isnan(g('stage1_after_s'))
                         and not math.isnan(g('hold_s')) else 'stop sequence incomplete')
                if math.isnan(g('time_to_stop_s')):
                    stop = 'did NOT drop below the stop speed within 20 s'
                else:
                    stop = (f'stopped {r.time_to_stop_s:.2f} s after teleop went silent, over '
                            f'{r.stop_distance_m:.2f} m, creep {r.creep_m:.2f} m, mean decel '
                            f'{g("decel_mean_mps2"):.2f} m/s2')
                    if not math.isnan(g('decel_after_hold_mps2')):
                        stop += (f' (during hold {g("decel_during_hold_mps2"):.2f}, '
                                 f'after {g("decel_after_hold_mps2"):.2f})')
                print(f'  t={r.t_teleop_last_cmd:7.2f} s  {g("speed_at_start_mps"):.2f} m/s  {stage}: '
                      f'stage 1 after {g("stage1_after_s"):.2f} s, hold {g("hold_s"):.2f} s; {stop}')

    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, ax = plt.subplots(3, 1, sharex=True, figsize=(12, 8))
    ax[0].plot(odo_t, speed, lw=0.8)
    ax[0].axhline(STOP_SPEED, color='0.6', lw=0.6, ls='--')
    ax[0].set_ylabel('speed (m/s)')
    ax[1].plot(vc.t, vc.veh_throttle, lw=0.8, label='throttle')
    ax[1].plot(vc.t, vc.veh_brake * 10, lw=0.8, label='brake x10')
    ax[1].set_ylabel('command (0-1000)')
    ax[1].legend(loc='upper right')
    ax[2].step(vc.t, vc.veh_motion, where='post', lw=0.8, label='veh_motion')
    ax[2].step(joy.t, joy[DEADMAN_COL], where='post', lw=0.8, alpha=0.7, label='deadman')
    ax[2].set_ylabel('state')
    ax[2].legend(loc='upper right')
    ax[2].set_xlabel('time since first message (s)')
    for a in ax:
        for t_rel in (res.t_release if len(res) else []):
            a.axvline(t_rel, color='C3', lw=0.6, alpha=0.6)
        for t_w in (wres.t_teleop_last_cmd if len(wres) else []):
            a.axvline(t_w, color='C1', lw=0.9, alpha=0.8)
        a.grid(alpha=0.3)
    fig.suptitle(f'{args.bag_name}: deadman releases (red), teleop silent / watchdog (orange)')
    fig.tight_layout()
    fig.savefig(d / 'stop_check.png', dpi=120)
    print(f'\n-> results and stop_check.png in {d}')


if __name__ == '__main__':
    main()
