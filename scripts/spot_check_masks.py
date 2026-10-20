"""Visual spot check of Hyper-Drive segmentation masks, before and after snap_masks.py cleanup.

For each selected frame, saves one figure with:
  1. Original RGB                     2. Raw grayscale mask (contrast-stretched)
  3. Raw mask colorized               4. Cleaned mask colorized          (needs --clean)
  5. RGB + cleaned mask overlay       6. Pixels changed / ignored by cleanup (needs --clean)
Without --clean, only the original 4 panels are drawn (RGB, grayscale, colorized, overlay).

Frame selection (default): one frame per class, choosing frames that actually contain each class
after cleanup (so small classes like Water or Person/Animal get checked), then random frames up to --n.

Usage:
  python3 spot_check_masks.py \
      --rgb   ~/ibex_ws/data/hyper_drive_data/RGB_RAW \
      --raw   ~/ibex_ws/data/hyper_drive_data/SEGMENTATIONS_RAW \
      --clean ~/ibex_ws/data/hyper_drive_data/SEGMENTATIONS_RAW_PNG \
      --out   ~/ibex_ws/data/hyper_drive_data/spot_checks --n 20
  Add --files name1 name2 ... to check specific frames (base names, e.g. olin_collection_05_15_23_parcel_b_0).
  Add --random to skip class-coverage selection.
"""
import os
import glob
import json
import random
import argparse
import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

IGNORE_ID = 255
MIN_CLASS_PX = 500  # a class counts as "present" in a cleaned mask above this many pixels

# Defaults from label_map.json and the legend; override names with --label-map.
CLASS_NAMES = {0: 'Unlabeled', 1: 'Dirt', 2: 'Rock/Gravel', 3: 'Paved', 4: 'Rock', 5: 'Grass',
               6: 'Vegetation', 7: 'Sky', 8: 'Clouds', 9: 'Vehicle', 10: 'Infrastructure',
               11: 'Directional', 12: 'Debris (leaves/mulch)', 13: 'Concrete', 14: 'Other',
               15: 'Person/Animal', 16: 'Water', IGNORE_ID: 'Ignore (cleanup)'}
PALETTE_RGB = {0: (0, 0, 0), 1: (139, 90, 43), 2: (190, 170, 130), 3: (90, 90, 100), 4: (120, 120, 120),
               5: (120, 220, 60), 6: (20, 110, 30), 7: (110, 170, 255), 8: (230, 240, 255),
               9: (255, 0, 0), 10: (255, 140, 0), 11: (255, 255, 0), 12: (180, 120, 60),
               13: (200, 200, 200), 14: (255, 0, 255), 15: (0, 255, 255), 16: (0, 60, 200),
               IGNORE_ID: (255, 255, 255)}
LUT = np.zeros((256, 3), np.uint8)
for k, c in PALETTE_RGB.items():
    LUT[k] = c  # values not in the palette (e.g. 17-22 artifacts) stay black


def find_rgb(rgb_dir, base):
    hits = sorted(glob.glob(os.path.join(rgb_dir, base + '.*')))
    return hits[0] if hits else None


def colorize(mask):
    return LUT[mask]


def overlay(rgb, mask, alpha=0.5):
    out = rgb.astype(np.float32).copy()
    sel = (mask >= 1) & (mask <= 16)
    out[sel] = (1 - alpha) * out[sel] + alpha * LUT[mask][sel]
    return out.astype(np.uint8)


def select_frames(bases, clean_dir, n, cover_classes, seed):
    rng = random.Random(seed)
    if not cover_classes or clean_dir is None:
        return rng.sample(bases, min(n, len(bases)))
    present = {}
    for b in bases:
        p = os.path.join(clean_dir, f'{b}_labeled.png')
        if not os.path.exists(p):
            continue
        counts = np.bincount(cv2.imread(p, cv2.IMREAD_UNCHANGED).ravel(), minlength=256)
        present[b] = {c for c in range(1, 17) if counts[c] >= MIN_CLASS_PX}
    chosen = []
    for cid in range(1, 17):  # one frame per class, if any frame contains it
        having = [b for b, s in present.items() if cid in s]
        if any(b in chosen for b in having):
            continue  # already covered by a frame chosen for another class
        if having:
            chosen.append(rng.choice(having))
        else:
            print(f'note: no cleaned mask has >= {MIN_CLASS_PX} px of class {cid} ({CLASS_NAMES[cid]})')
    rest = [b for b in bases if b not in chosen]
    rng.shuffle(rest)
    chosen += rest[:max(0, n - len(chosen))]
    return chosen


def legend_handles(mask):
    counts = np.bincount(mask.ravel(), minlength=256)
    total = mask.size
    handles = []
    for cid in sorted(CLASS_NAMES):
        if counts[cid] / total >= 0.001:
            color = np.array(PALETTE_RGB[cid]) / 255
            edge = 'black' if cid == IGNORE_ID else color
            handles.append(Patch(facecolor=color, edgecolor=edge,
                                 label=f'{cid} = {CLASS_NAMES[cid]} ({100 * counts[cid] / total:.1f}%)'))
    return handles


def plot_frame(base, rgb_path, raw_path, clean_path, out_dir):
    rgb = cv2.cvtColor(cv2.imread(rgb_path, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
    raw = cv2.imread(raw_path, cv2.IMREAD_GRAYSCALE)
    clean = cv2.imread(clean_path, cv2.IMREAD_UNCHANGED) if clean_path else None
    if rgb.shape[:2] != raw.shape:
        print(f'WARNING {base}: RGB {rgb.shape[:2]} and mask {raw.shape} sizes differ')

    if clean is None:
        panels = [(rgb, '1. Original RGB'),
                  (raw, '2. Raw grayscale mask (contrast-stretched)'),
                  (colorize(raw), '3. Raw mask colorized'),
                  (overlay(rgb, raw), '4. RGB + raw mask overlay')]
        rows, cols, legend_mask = 2, 2, raw
    else:
        changed = np.zeros((*raw.shape, 3), np.uint8)
        changed[(raw != clean) & (clean != IGNORE_ID)] = (255, 140, 0)   # relabeled
        changed[clean == IGNORE_ID] = (255, 0, 0)                         # ignored
        pct_changed = 100 * ((raw != clean) & (clean != IGNORE_ID)).mean()
        pct_ignored = 100 * (clean == IGNORE_ID).mean()
        panels = [(rgb, '1. Original RGB'),
                  (raw, '2. Raw grayscale mask (contrast-stretched)'),
                  (colorize(raw), '3. Raw mask colorized (JPG artifacts visible at edges)'),
                  (colorize(clean), '4. Cleaned mask colorized (white = ignore)'),
                  (overlay(rgb, clean), '5. RGB + cleaned mask overlay'),
                  (changed, f'6. Cleanup: orange relabeled {pct_changed:.1f}%, red ignored {pct_ignored:.1f}%')]
        rows, cols, legend_mask = 2, 3, clean

    fig, axes = plt.subplots(rows, cols, figsize=(7 * cols, 6.6 * rows))
    for ax, (img, title) in zip(axes.ravel(), panels):
        if img.ndim == 2:
            ax.imshow(img, cmap='gray', vmin=0, vmax=16)
        else:
            ax.imshow(img)
        ax.set_title(title, fontsize=12)
        ax.axis('off')
    fig.legend(handles=legend_handles(legend_mask), loc='lower center', ncol=6, fontsize=10, frameon=False)
    fig.suptitle(base, fontsize=14)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.93, bottom=0.07, wspace=0.03, hspace=0.12)
    out_path = os.path.join(out_dir, f'{base}_check.png')
    plt.savefig(out_path, dpi=80)
    plt.close(fig)
    return out_path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--rgb', required=True, help='RGB_RAW folder')
    ap.add_argument('--raw', required=True, help='SEGMENTATIONS_RAW folder (*_labeled.jpg)')
    ap.add_argument('--clean', default=None, help='cleaned folder from snap_masks.py (*_labeled.png)')
    ap.add_argument('--out', default='./spot_checks', help='output folder for figures')
    ap.add_argument('--n', type=int, default=20, help='number of frames to check')
    ap.add_argument('--files', nargs='*', default=None, help='specific base names to check')
    ap.add_argument('--random', action='store_true', help='random selection instead of class coverage')
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--label-map', default=None, help='label_map.json to override class names')
    args = ap.parse_args()

    if args.label_map:
        with open(os.path.expanduser(args.label_map)) as f:
            for name, cid in json.load(f).items():
                CLASS_NAMES[int(cid)] = name

    rgb_dir, raw_dir = os.path.expanduser(args.rgb), os.path.expanduser(args.raw)
    clean_dir = os.path.expanduser(args.clean) if args.clean else None
    out_dir = os.path.expanduser(args.out)
    os.makedirs(out_dir, exist_ok=True)

    bases = sorted(os.path.basename(p)[:-len('_labeled.jpg')]
                   for p in glob.glob(os.path.join(raw_dir, '*_labeled.jpg')))
    if not bases:
        raise SystemExit(f'No *_labeled.jpg files found in {raw_dir}')
    selected = args.files if args.files else select_frames(bases, clean_dir, args.n, not args.random, args.seed)

    for base in selected:
        rgb_path = find_rgb(rgb_dir, base)
        raw_path = os.path.join(raw_dir, f'{base}_labeled.jpg')
        clean_path = os.path.join(clean_dir, f'{base}_labeled.png') if clean_dir else None
        if rgb_path is None or not os.path.exists(raw_path):
            print(f'skip {base}: missing RGB or raw mask')
            continue
        if clean_path and not os.path.exists(clean_path):
            print(f'{base}: no cleaned mask, drawing raw panels only')
            clean_path = None
        print('saved', plot_frame(base, rgb_path, raw_path, clean_path, out_dir))


if __name__ == '__main__':
    main()
