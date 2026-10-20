"""One-time cleanup of Hyper-Drive JPG segmentation masks -> clean label-ID PNGs.

The raw masks are single-channel (grayscale) images whose pixel values ARE the class IDs,
saved as JPG. JPEG compression leaves the region interiors intact but creates in-between
values along class boundaries (e.g. 7-11 between classes 6 and 12). Because the label map
uses every ID from 1 to 16, most of those artifacts ARE valid IDs (7 = Sky, 9 = Vehicle, ...),
so checking values alone cannot catch them. Cleanup is therefore spatial:
  1. Pixels outside VALID_IDS, and pixels in tiny connected components (< MIN_COMPONENT_PX,
     i.e. thin JPEG speckle along edges), are replaced by the majority label around them.
  2. Optionally, a band of BOUNDARY_PX pixels around every class boundary is set to IGNORE_ID.

Usage:
  python3 snap_masks.py --src /path/to/SEGMENTATIONS_RAW --survey
      Histogram of values across all masks (values above 16 are artifacts).
  python3 snap_masks.py --src /path/to/SEGMENTATIONS_RAW --dst /path/to/SEGMENTATIONS_RAW_PNG
      Clean all masks.
  python3 snap_masks.py --src /path/to/SEGMENTATIONS_RAW_PNG --pattern '*_labeled.png' --survey
      Survey the cleaned output (true class distribution; 255 = ignore).
Reads  {src}/{f_base}_labeled.jpg
Writes {dst}/{f_base}_labeled.png   (originals untouched; dst defaults to {src}_PNG next to src)
"""
import os
import argparse
import glob
import cv2
import numpy as np

SRC_DIR = './SEGMENTATIONS_RAW'
IGNORE_ID = 255
VOTE_WINDOW = 7    # window for majority vote on invalid pixels (odd)
BOUNDARY_PX = 3    # ignore band around class boundaries; 0 disables
MIN_COMPONENT_PX = 50  # connected regions smaller than this are treated as artifacts

# From label_map.json: 1 Dirt ... 16 Water. 0 = unlabeled (not in the map, kept as its own value).
VALID_IDS = list(range(0, 17))


def artifact_pixels(mask: np.ndarray, valid_ids, min_px: int) -> np.ndarray:
    """Pixels with invalid values, or in connected components too small to be real labels."""
    bad = ~np.isin(mask, valid_ids)
    for cid in np.unique(mask):
        if cid not in valid_ids:
            continue
        n, comp, stats, _ = cv2.connectedComponentsWithStats((mask == cid).astype(np.uint8), connectivity=8)
        small = np.nonzero(stats[1:, cv2.CC_STAT_AREA] < min_px)[0] + 1
        if small.size:
            bad |= np.isin(comp, small)
    return bad


def majority_fill(mask: np.ndarray, valid_ids, window: int) -> np.ndarray:
    """Replace artifact pixels with the most common non-artifact label in a window around them."""
    invalid = artifact_pixels(mask, valid_ids, MIN_COMPONENT_PX)
    if not invalid.any():
        return mask.copy()
    best_count = np.full(mask.shape, -1.0, dtype=np.float32)
    best_id = np.full(mask.shape, IGNORE_ID, dtype=np.uint8)
    for cid in valid_ids:
        count = cv2.boxFilter(((mask == cid) & ~invalid).astype(np.float32), -1, (window, window), normalize=False)
        better = count > best_count
        best_count[better] = count[better]
        best_id[better] = cid
    out = mask.copy()
    out[invalid] = best_id[invalid]
    out[invalid & (best_count <= 0)] = IGNORE_ID  # no valid neighbor at all
    return out


def ignore_boundaries(mask: np.ndarray, px: int) -> np.ndarray:
    if px <= 0:
        return mask
    kernel = np.ones((3, 3), np.uint8)
    edges = cv2.dilate(mask, kernel) != cv2.erode(mask, kernel)
    band = cv2.dilate(edges.astype(np.uint8), np.ones((2 * px + 1, 2 * px + 1), np.uint8)) > 0
    out = mask.copy()
    out[band] = IGNORE_ID
    return out


def survey(paths):
    total = np.zeros(256, dtype=np.int64)
    files_with = np.zeros(256, dtype=np.int64)
    for p in paths:
        m = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
        counts = np.bincount(m.ravel(), minlength=256)
        total += counts
        files_with += counts > 0
    print(f'{len(paths)} masks surveyed')
    for v in np.nonzero(total)[0]:
        flag = '  <-- outside valid IDs' if v not in VALID_IDS and v != IGNORE_ID else ''
        print(f'value {v:3d}: {total[v]:>13d} px ({100 * total[v] / total.sum():7.3f}%)  '
              f'in {files_with[v]:4d} files{flag}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--src', default=SRC_DIR, help='folder with *_labeled.jpg masks')
    ap.add_argument('--dst', default=None, help='output folder (default: <src>_PNG)')
    ap.add_argument('--survey', action='store_true', help='only report value histogram')
    ap.add_argument('--pattern', default='*_labeled.jpg',
                    help="file pattern in src (use '*_labeled.png' to survey cleaned output)")
    args = ap.parse_args()
    src = os.path.abspath(os.path.expanduser(args.src))
    dst = os.path.abspath(os.path.expanduser(args.dst)) if args.dst else src.rstrip(os.sep) + '_PNG'
    paths = sorted(glob.glob(os.path.join(src, args.pattern)))
    if not paths:
        raise SystemExit(f'No {args.pattern} files found in {src}')
    if args.survey:
        survey(paths)
        return
    os.makedirs(dst, exist_ok=True)
    for p in paths:
        name = os.path.splitext(os.path.basename(p))[0]
        raw = cv2.imread(p, cv2.IMREAD_GRAYSCALE)  # single channel: no BGR/RGB issue
        clean = ignore_boundaries(majority_fill(raw, VALID_IDS, VOTE_WINDOW), BOUNDARY_PX)
        cv2.imwrite(os.path.join(dst, f'{name}.png'), clean)
        print(f'{name}: {100 * (raw != clean).mean():.2f}% changed, '
              f'{100 * (clean == IGNORE_ID).mean():.2f}% ignored')


if __name__ == '__main__':
    main()
