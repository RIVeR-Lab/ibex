#!/usr/bin/env python3
"""throttle_map.py - throttle calibration map from teleop bags, already extracted by
extract_steering_bags.py.

Instead of one number per run, every odometry sample where the throttle had been
steady for STEADY_S (and the brake off, motion on) becomes a data point:
(throttle held, current speed) -> acceleration. These are binned into a map, and for
each speed bin the throttle where acceleration crosses zero is interpolated: the
throttle needed to HOLD that speed, which is the feedforward a speed controller needs.
The same idea as Autoware's accel_brake_map_calibrator.

Gear and direction come from the bag name, because the transmission is under manual
control during these runs and Kairos's veh_shift / veh_gear only show its default (Park).
Names: throttle_<high|rev>_<level>_<a|b>_<rep>, where a and b are the two directions
along the stretch. The first runs' names still work: 'forward' = High, driven one way;
'backward' = Reverse, driven the other way.

When a gear has runs in both directions, the straight-line model gets a direction term:
accel = b0 + b_thr*throttle + b_v*speed + b_dir*dir (dir = +1 for a, -1 for b). b_dir is
the slope's effect, -9.81 * grade, so the hold throttle is computed at dir = 0: slope-free,
with no IMU needed. The implied grade of the stretch is reported.

Slope correction: gravity adds or removes about 9.81 * grade m/s2 along a slope, which
would otherwise end up in the map. The grade under each sample is fitted from the
odometry height over SLOPE_WINDOW_M of path, after levelling the odometry frame with
gravity: KISS-ICP's frame is the lidar's own frame at the first scan, so a vehicle that
starts on a slope sees a uniform grade as flat. Gravity comes from /ouster/imu while the
vehicle is at rest at the start of the bag, rotated into the frame the odometry reports.
On Ibex KISS-ICP reports base_link, and os_imu sits 22.44 deg nose-down relative to it
(the sensor_rack -> os_mount pitch in tf-frames.md, os_imu parallel to os_mount), so the
default convention 'ibex' rotates the IMU reading by that pitch; --imu-mount-pitch-deg
changes the angle. 'same' and 'flip' (180 deg about z) cover odometry reported in the
sensor's own frame. --imu-axes auto checks each convention against the IMU's gravity
reading when the vehicle is at rest again at the end of a bag, preferring 'ibex' unless
another fits clearly better. Every sample is then corrected to flat ground:
accel_flat = accel + 9.81 * sin(atan(grade)). --no-slope turns this off.

The IMU levelling only works when the odometry pose is in the sensor's own frame. If the
convention check misses by more than MAX_AXES_ERR_DEG, or a bag's median grade comes out
above MAX_PLAUSIBLE_GRADE, the correction is NOT applied: on Ibex the Ouster is mounted
pitched (~21 deg) while KISS-ICP may report a vehicle frame, which makes the levelling
invent a ~38 % slope. The reliable alternative is a measured grade:
--grade <percent> applies one uniform grade, positive = uphill in the 'forward' direction,
so 'forward' bags get +grade and 'backward' bags (driven the other way) get -grade.

Because the bins are usually sparse, it also fits one straight-line model per gear to all
samples, with outliers trimmed:  accel = b0 + b_thr * throttle + b_v * speed.  The throttle
to hold speed v is then -(b0 + b_v * v) / b_thr. A fit with R2 below 0.2, or where more
throttle doesn't mean more acceleration, is flagged as unusable: usually the runs never
cruised at a steady speed.

Usage:
  python3 throttle_map.py 'throttlehold_*' [--root ~/ibex_analysis]

Needs ouster_imu.csv (extracted by default) for the slope correction.

Writes throttle_accel_samples.csv, throttle_accel_map.csv, throttle_hold_speed.csv,
throttle_model.csv and throttle_accel_map.png in the root.
"""
import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd

STEADY_S = 1.5          # throttle steady over this long before a sample counts
STEADY_RANGE = 30       # max - min veh_throttle within that window
MIN_THROTTLE = 150      # below this the engine is near idle; ignored
ACCEL_FIT_S = 1.0       # centred window for the local acceleration fit
THROTTLE_BIN = 25
SPEED_BIN = 1.0         # m/s
MIN_SAMPLES = 5         # fewer samples in a bin and it is left empty
G = 9.81
SLOPE_WINDOW_M = 10.0   # path length over which the local grade is fitted
REST_SPEED = 0.15       # m/s; slower counts as standing still
REST_MIN_S = 1.0        # rest needed at the start / end of a bag to read gravity
IBEX_MOUNT_PITCH_DEG = 22.44   # os_mount nose-down pitch relative to base_link (tf-frames.md)


def ry(deg):
    a = math.radians(deg)
    return np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])


AXES = {'ibex': ry(IBEX_MOUNT_PITCH_DEG),            # IMU axes -> base_link
        'same': np.diag([1.0, 1.0, 1.0]), 'flip': np.diag([-1.0, -1.0, 1.0])}
MAX_AXES_ERR_DEG = 2.0      # convention check must match the end-of-bag gravity this well
MAX_PLAUSIBLE_GRADE = 0.15  # a bag whose median grade exceeds 15 % is not corrected


def parse_name(name):
    """(gear, direction) from a bag name; direction +1 = a / forward, -1 = b / backward."""
    tok = name.lower().replace('-', '_').split('_')
    if 'high' in tok:
        gear = 'High'
    elif 'rev' in tok or 'reverse' in tok:
        gear = 'Reverse'
    elif any(t.startswith('forward') for t in tok):
        gear = 'High (forward)'
    elif any(t.startswith('backward') for t in tok):
        gear = 'Reverse'
    else:
        gear = '?'
    if 'a' in tok or any(t.startswith('forward') for t in tok):
        direction = 1
    elif 'b' in tok or any(t.startswith('backward') for t in tok):
        direction = -1
    else:
        direction = 0
    return gear, direction


def gear_from_name(name):
    return parse_name(name)[0]


def speed_from_odometry(odo):
    x, y, t = (odo[c].to_numpy(float) for c in
               ('pose.pose.position.x', 'pose.pose.position.y', 't'))
    v = np.hypot(np.diff(x, prepend=x[0]), np.diff(y, prepend=y[0])) / np.maximum(
        np.diff(t, prepend=t[0] - 0.1), 1e-3)
    return pd.Series(v).rolling(5, center=True, min_periods=1).median().to_numpy()


def local_accel(t, v, half=ACCEL_FIT_S / 2):
    """Slope of a straight-line fit of speed over a centred window: robust to odometry noise."""
    a = np.full(len(t), math.nan)
    j0 = j1 = 0
    for i, ti in enumerate(t):
        while t[j0] < ti - half:
            j0 += 1
        while j1 < len(t) and t[j1] <= ti + half:
            j1 += 1
        if j1 - j0 >= 5:
            tt, vv = t[j0:j1], v[j0:j1]
            tc = tt - tt.mean()
            a[i] = float((tc * (vv - vv.mean())).sum() / (tc * tc).sum())
    return a


def quat_mat(x, y, z, w):
    n = math.sqrt(x * x + y * y + z * z + w * w) or 1.0
    x, y, z, w = x / n, y / n, z / n, w / n
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def odom_rotation(odo, i):
    cols = [f'pose.pose.orientation.{c}' for c in 'xyzw']
    if not all(c in odo for c in cols):
        return np.eye(3)
    return quat_mat(*(float(odo[c].iloc[i]) for c in cols))


def rest_window(t, v, from_end=False):
    """Indices of the rest stretch touching the start (or end) of the bag, if long enough."""
    idx = range(len(t) - 1, -1, -1) if from_end else range(len(t))
    still = []
    for i in idx:
        if v[i] >= REST_SPEED:
            break
        still.append(i)
    if len(still) < 2 or abs(t[still[-1]] - t[still[0]]) < REST_MIN_S:
        return None
    return sorted(still)


def gravity_up(imu, t0, t1):
    """Mean specific force at rest = 'up' in the IMU's axes."""
    w = imu[(imu['t'] >= t0) & (imu['t'] <= t1)]
    if len(w) < 20:
        return None
    f = w[[f'linear_acceleration.{c}' for c in 'xyz']].mean().to_numpy(float)
    return f / np.linalg.norm(f)


def angle_deg(a, b):
    return math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(a, b) / np.linalg.norm(a) / np.linalg.norm(b))))))


def level_info(d):
    """Gravity at the start (and end) of a bag, and how well each axis convention fits."""
    if not (d / 'ouster_imu.csv').exists():
        return None
    odo = pd.read_csv(d / 'kiss_odometry.csv').sort_values('t').reset_index(drop=True)
    imu = pd.read_csv(d / 'ouster_imu.csv')
    t = odo['t'].to_numpy(float)
    v = speed_from_odometry(odo)
    w0, w1 = rest_window(t, v), rest_window(t, v, from_end=True)
    if w0 is None:
        return None
    u0 = gravity_up(imu, t[w0[0]], t[w0[-1]])
    if u0 is None:
        return None
    R0 = odom_rotation(odo, w0[len(w0) // 2])
    info = {'tilt_start_deg': math.degrees(math.acos(max(-1.0, min(1.0, abs(u0[2]))))), 'u_odom': {}, 'err': {}}
    u1 = gravity_up(imu, t[w1[0]], t[w1[-1]]) if w1 is not None and w1[0] > w0[-1] else None
    R1 = odom_rotation(odo, w1[len(w1) // 2]) if u1 is not None else None
    for name, C in AXES.items():
        u_odom = R0 @ C @ u0                       # 'up' in the odometry frame
        info['u_odom'][name] = u_odom
        info['err'][name] = (angle_deg(R1.T @ u_odom, C @ u1) if u1 is not None else math.nan)
    return info


def grade_along_path(P, u_odom, moving):
    """Grade (rise over run) along the direction of travel, fitted over SLOPE_WINDOW_M."""
    h = P @ u_odom
    dP = np.diff(P, axis=0, prepend=P[:1])
    horiz = dP - np.outer(dP @ u_odom, u_odom)
    s = np.cumsum(np.linalg.norm(horiz, axis=1) * moving)   # path length, rest jitter excluded
    g = np.full(len(s), math.nan)
    half = SLOPE_WINDOW_M / 2
    j0 = j1 = 0
    for i in range(len(s)):
        while s[j0] < s[i] - half:
            j0 += 1
        while j1 < len(s) and s[j1] <= s[i] + half:
            j1 += 1
        ss, hh = s[j0:j1], h[j0:j1]
        if moving[i] and j1 - j0 >= 5 and ss[-1] - ss[0] >= 0.6 * SLOPE_WINDOW_M:
            sc = ss - ss.mean()
            g[i] = float((sc * (hh - hh.mean())).sum() / (sc * sc).sum())
    return g


def samples_for_bag(d, u_odom=None, const_grade=None):
    vc = pd.read_csv(d / 'vehicle_control.csv').sort_values('t')
    odo = pd.read_csv(d / 'kiss_odometry.csv').sort_values('t').reset_index(drop=True)
    t = odo['t'].to_numpy(float)
    v = speed_from_odometry(odo)
    a = local_accel(t, v)
    if const_grade is not None:
        grade = np.full(len(t), const_grade)
    elif u_odom is not None:
        P = odo[[f'pose.pose.position.{c}' for c in 'xyz']].to_numpy(float)
        grade = grade_along_path(P, u_odom, v >= REST_SPEED)
    else:
        grade = np.full(len(t), math.nan)
    vt = vc['t'].to_numpy(float)
    thr = vc['veh_throttle'].to_numpy(float)
    rows = []
    for ti, vi, ai, gi in zip(t, v, a, grade):
        if math.isnan(ai):
            continue
        w = (vt >= ti - STEADY_S) & (vt <= ti)
        if w.sum() < 5:
            continue
        seg = vc[w]
        if (seg['veh_motion'] != 1).any() or (seg['veh_brake'] > 0).any():
            continue
        th = thr[w]
        if th.min() < MIN_THROTTLE or th.max() - th.min() > STEADY_RANGE:
            continue
        corr = G * math.sin(math.atan(gi)) if not math.isnan(gi) else 0.0
        gear, direction = parse_name(d.name)
        rows.append({'bag': d.name, 't': ti, 'speed': vi, 'accel_raw': ai, 'grade': gi,
                     'accel': ai + corr, 'throttle': float(th.mean()),
                     'gear': gear, 'direction': direction})
    return pd.DataFrame(rows)


def hold_throttle(cell_means, speed_bins):
    """Per speed bin, the throttle where mean acceleration crosses zero (linear interpolation)."""
    out = []
    for sb in speed_bins:
        col = cell_means[sb].dropna() if sb in cell_means else pd.Series(dtype=float)
        if len(col) < 2:
            continue
        thr, acc = col.index.to_numpy(float) + THROTTLE_BIN / 2, col.to_numpy(float)  # bin centres
        cross = math.nan
        for k in range(len(thr) - 1):
            if acc[k] <= 0 <= acc[k + 1]:
                cross = thr[k] + (thr[k + 1] - thr[k]) * (-acc[k]) / (acc[k + 1] - acc[k])
                break
        out.append({'speed_mps': sb + SPEED_BIN / 2, 'throttle_to_hold': cross,
                    'note': '' if not math.isnan(cross) else
                    ('accelerating at every throttle seen' if (acc > 0).all() else
                     'decelerating at every throttle seen' if (acc < 0).all() else 'no clean crossing')})
    return pd.DataFrame(out)


def robust_fit(g, with_direction=False):
    """Least squares of accel on throttle and speed (and direction), trimming |residual| >
    2.5 robust sigma."""
    cols = [np.ones(len(g)), g['throttle'], g['speed']]
    if with_direction:
        cols.append(g['direction'])
    X = np.column_stack(cols)
    y = g['accel'].to_numpy()
    keep = np.ones(len(y), bool)
    for _ in range(5):
        b, *_ = np.linalg.lstsq(X[keep], y[keep], rcond=None)
        r = y - X @ b
        sigma = np.median(np.abs(r[keep] - np.median(r[keep]))) * 1.4826
        keep = np.abs(r) < 2.5 * max(sigma, 1e-6)
    r = y - X @ b
    r2 = 1 - (r[keep] ** 2).sum() / max(((y[keep] - y[keep].mean()) ** 2).sum(), 1e-9)
    return b, int(keep.sum()), float(r2), float(sigma)


def main():
    ap = argparse.ArgumentParser(description='Throttle x speed -> acceleration map.')
    ap.add_argument('bags', nargs='+', help="extracted bag names; patterns like 'throttlehold_*' work")
    ap.add_argument('--root', default='~/ibex_analysis')
    ap.add_argument('--imu-axes', choices=['auto', 'ibex', 'same', 'flip'], default='auto',
                    help="IMU vs odometry axes: 'ibex' = IMU pitched nose-down by --imu-mount-pitch-deg "
                         "relative to base_link; 'same'/'flip' = odometry in the sensor's own frame")
    ap.add_argument('--imu-mount-pitch-deg', type=float, default=IBEX_MOUNT_PITCH_DEG,
                    help='nose-down pitch of os_imu relative to base_link (default 22.44, tf-frames.md)')
    ap.add_argument('--no-slope', action='store_true', help='skip the slope correction')
    ap.add_argument('--grade', type=float, default=None,
                    help="measured uniform grade of the stretch in percent, positive = uphill in "
                         "direction a (or 'forward'); replaces the IMU levelling")
    args = ap.parse_args()
    AXES['ibex'] = ry(args.imu_mount_pitch_deg)
    root = Path(args.root).expanduser()
    dirs = []
    for b in args.bags:
        dirs += sorted(p for p in root.glob(b) if p.is_dir()) if any(c in b for c in '*?[') \
            else [root / b]

    dirs = [d for d in dirs if (d / 'vehicle_control.csv').exists()
            and (d / 'kiss_odometry.csv').exists()]
    use_imu = not args.no_slope and args.grade is None
    levels = {d.name: level_info(d) for d in dirs} if use_imu else {}
    axes = args.imu_axes
    if args.grade is not None and not args.no_slope:
        print(f"Slope correction: measured grade {args.grade:+.2f}% uphill in direction a "
              "(+ for a / forward bags, - for b / backward bags)")
    if use_imu:
        errs = {k: [lv['err'][k] for lv in levels.values() if lv and not math.isnan(lv['err'][k])]
                for k in AXES}
        if axes == 'auto':
            if all(errs[k] for k in AXES):
                m = {k: float(np.median(v)) for k, v in errs.items()}
                best = min(m, key=m.get)
                axes = 'ibex' if m['ibex'] - m[best] < 0.3 else best
                note = ('median gravity mismatch at the end of a bag: '
                        + ', '.join(f'{k} {m[k]:.2f} deg' for k in AXES))
                if axes == 'ibex' and best != 'ibex':
                    note += ' (ibex within 0.3 deg of the best, so the documented extrinsic is used)'
            else:
                axes = 'ibex'
                note = ('no bag ends at rest, so the convention cannot be checked; using ibex, '
                        f'the documented {args.imu_mount_pitch_deg:.2f} deg mount')
            print(f'Slope correction: IMU axes = {axes}; {note}')
        else:
            print(f'Slope correction: IMU axes = {axes} (set by --imu-axes)')
        if errs[axes] and float(np.median(errs[axes])) > MAX_AXES_ERR_DEG:
            print(f'  NOT APPLIED: the chosen convention still misses the end-of-bag gravity by more than '
                  f'{MAX_AXES_ERR_DEG} deg, so the IMU and odometry frames differ by more than a 180 deg '
                  'turn (a pitched sensor mount reported in a vehicle frame, for example). Measure the '
                  "stretch's grade and pass it with --grade instead.")
            levels = {}
            use_imu = False
    elif args.no_slope:
        print('Slope correction: off (--no-slope)')

    parts = []
    for d in dirs:
        lv = levels.get(d.name)
        if args.grade is not None and not args.no_slope:
            sign = parse_name(d.name)[1]
            s = samples_for_bag(d, const_grade=sign * args.grade / 100)
            line = f'  {d.name}: {len(s)} steady samples; grade along travel {sign * args.grade:+.2f}%'
            if sign == 0:
                line += " (no direction in the name, so no correction)"
            print(line)
            parts.append(s)
            continue
        s = samples_for_bag(d, lv['u_odom'][axes] if lv else None)
        if lv and len(s) and abs(s['grade'].median()) > MAX_PLAUSIBLE_GRADE:
            bad = s['grade'].median()
            s = samples_for_bag(d)
            print(f'  {d.name}: {len(s)} steady samples; NOT corrected: measured grade '
                  f'{100 * bad:+.0f}% is implausible')
            parts.append(s)
            continue
        line = f'  {d.name}: {len(s)} steady samples'
        if use_imu:
            if lv is None:
                line += '; no slope correction (no ouster_imu.csv, or not at rest at the start)'
            elif len(s):
                gr = s['grade'].dropna()
                u = lv['u_odom'][axes]
                tilt = math.degrees(math.acos(max(-1.0, min(1.0, abs(float(u[2]))))))
                line += (f'; vehicle tilt at start {tilt:.1f} deg, grade along travel '
                         f'{100 * gr.median():+.1f}% (median), correction '
                         f'{(s["accel"] - s["accel_raw"]).median():+.2f} m/s2'
                         if len(gr) else '; grade not measurable (too little distance)')
        print(line)
        parts.append(s)
    if not parts or not sum(len(p) for p in parts):
        print('No steady-throttle samples found.')
        return
    S = pd.concat(parts, ignore_index=True)
    S.to_csv(root / 'throttle_accel_samples.csv', index=False)
    S['throttle_bin'] = (S['throttle'] // THROTTLE_BIN) * THROTTLE_BIN
    S['speed_bin'] = (S['speed'] // SPEED_BIN) * SPEED_BIN

    pd.set_option('display.width', 250)
    maps, holds = [], []
    for gear, g in S.groupby('gear'):
        stats = g.groupby(['throttle_bin', 'speed_bin'])['accel'].agg(['median', 'size'])
        stats = stats[stats['size'] >= MIN_SAMPLES]
        if stats.empty:
            continue
        cell = stats['median'].unstack('speed_bin').sort_index()
        cell = cell[sorted(cell.columns)]
        print(f'\n== {gear}: median acceleration (m/s2), '
              f'rows = throttle bin, columns = speed bin (m/s)')
        print(cell.round(2).to_string())
        m = stats.reset_index().assign(gear=gear)
        maps.append(m)
        h = hold_throttle(cell, sorted(cell.columns)).assign(gear=gear)
        holds.append(h)
        if len(h):
            print('  Throttle to hold speed (acceleration crosses zero):')
            for r in h.itertuples():
                val = f'{r.throttle_to_hold:.0f}' if not math.isnan(r.throttle_to_hold) else '-'
                print(f'    {r.speed_mps:4.1f} m/s: {val:>4}  {r.note}')
    models = []
    print('\nStraight-line model per gear: accel = b0 + b_thr*throttle + b_v*speed')
    for gear, g in S.groupby('gear'):
        if len(g) < 20:
            print(f'  {gear}: only {len(g)} samples, no fit')
            continue
        dirs = set(g['direction']) if 'direction' in g else set()
        paired = {1, -1} <= dirs
        b, kept, r2, sigma = robust_fit(g, with_direction=paired)
        b0, bt, bv = b[:3]
        usable = bt > 0 and r2 >= 0.2
        row = {'gear': gear, 'b0': b0, 'b_thr': bt, 'b_v': bv, 'r2': r2, 'kept': kept,
               'samples': len(g), 'residual_sigma': sigma, 'usable': usable}
        dir_text = ''
        if paired:
            row['b_dir'] = b[3]
            row['implied_grade_pct'] = -100 * b[3] / G
            dir_text = f' {b[3]:+.3f}*dir'
        print(f'  {gear}: accel = {b0:+.3f} {bt:+.5f}*throttle {bv:+.3f}*speed{dir_text}  '
              f'(R2 {r2:.2f}, {kept}/{len(g)} samples kept, residual {sigma:.2f} m/s2)')
        if paired:
            n_a, n_b = int((g['direction'] == 1).sum()), int((g['direction'] == -1).sum())
            print(f'    both directions ({n_a} samples a, {n_b} b): slope removed; the stretch rises '
                  f'{row["implied_grade_pct"]:+.2f}% in direction a')
        elif len(dirs - {0}) == 1:
            print('    one direction only: the slope is still in this fit')
        if usable:
            print(f'    throttle to hold speed v = {-b0 / bt:.0f} + {-bv / bt:.1f} * v (v in m/s)')
            for v in (0.5, 2, 4, 6, 8):
                row[f'hold_{v:g}mps'] = -(b0 + bv * v) / bt
                print(f'      {v:3.1f} m/s: {row[f"hold_{v:g}mps"]:4.0f}')
        else:
            print('    UNUSABLE: throttle does not explain the acceleration. The runs probably '
                  'never cruised; hold each throttle until speed stops changing.')
        models.append(row)
    if models:
        pd.DataFrame(models).to_csv(root / 'throttle_model.csv', index=False)
    if maps:
        pd.concat(maps).to_csv(root / 'throttle_accel_map.csv', index=False)
    if holds:
        pd.concat(holds).to_csv(root / 'throttle_hold_speed.csv', index=False)

    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        return
    groups = [(k, g) for k, g in S.groupby('gear')]
    fig, ax = plt.subplots(1, len(groups) + 1, figsize=(6 * (len(groups) + 1), 5), squeeze=False)
    ax = ax[0]
    for a, (gear, g) in zip(ax, groups):
        sc = a.scatter(g['throttle'], g['accel'], c=g['speed'], s=6, cmap='viridis')
        fig.colorbar(sc, ax=a, label='speed (m/s)')
        a.axhline(0, color='0.4', lw=0.8)
        a.set_title(gear)
        a.set_xlabel('veh_throttle (steady 1.5 s)')
        a.set_ylabel('acceleration (m/s2)')
        a.grid(alpha=0.3)
    hold_all = pd.concat(holds) if holds else pd.DataFrame()
    a = ax[-1]
    for gear, h in (hold_all.groupby('gear') if len(hold_all) else []):
        a.plot(h['speed_mps'], h['throttle_to_hold'], 'o-', label=gear)
    a.set_xlabel('speed (m/s)')
    a.set_ylabel('throttle to hold speed')
    a.set_title('Feedforward: throttle where acceleration = 0')
    a.grid(alpha=0.3)
    if len(hold_all):
        a.legend()
    fig.tight_layout()
    fig.savefig(root / 'throttle_accel_map.png', dpi=120)
    print(f'\n-> {root}/throttle_accel_map.csv, throttle_hold_speed.csv, throttle_accel_map.png')


if __name__ == '__main__':
    main()
