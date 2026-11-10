#!/usr/bin/env python3
"""
bag_topic_sizes.py

Shows how much of an MCAP bag each topic takes up, which `ros2 bag info`
does not report. Use it to decide what to exclude from recordings.

Usage:
  python3 bag_topic_sizes.py <bag_folder_or_.mcap> [--top N]

Requires the mcap Python package:
  pip install mcap

Reads every message once, so a large bag takes a few minutes.
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

try:
    from mcap.reader import make_reader
except ImportError:
    sys.exit("The 'mcap' package is required: pip install mcap")


def mcap_files(path: Path):
    if path.is_dir():
        files = sorted(path.glob("*.mcap"))
        if not files:
            sys.exit(f"No .mcap files in {path}")
        return files
    return [path]


def main():
    ap = argparse.ArgumentParser(description="Per-topic size breakdown of an MCAP bag.")
    ap.add_argument("bag", type=Path)
    ap.add_argument("--top", type=int, default=25, help="number of topics to show (default 25)")
    args = ap.parse_args()

    sizes = defaultdict(int)
    counts = defaultdict(int)
    t_min, t_max = None, None

    for f in mcap_files(args.bag):
        print(f"Reading {f.name} ...", file=sys.stderr)
        with open(f, "rb") as fh:
            for _, channel, msg in make_reader(fh).iter_messages():
                sizes[channel.topic] += len(msg.data)
                counts[channel.topic] += 1
                t = msg.log_time
                t_min = t if t_min is None else min(t_min, t)
                t_max = t if t_max is None else max(t_max, t)

    total = sum(sizes.values())
    duration = (t_max - t_min) / 1e9 if t_min is not None and t_max > t_min else 0.0

    print(f"\nDuration {duration:.1f} s, total {total / 1e9:.2f} GB "
          f"({total / 1e6 / duration:.1f} MB/s)\n" if duration else "")
    print(f"{'Topic':<48} {'Count':>9} {'GB':>8} {'Share':>7} {'MB/s':>8} {'Avg size':>10}")
    print("-" * 94)
    for topic in sorted(sizes, key=sizes.get, reverse=True)[: args.top]:
        b = sizes[topic]
        rate = b / 1e6 / duration if duration else 0.0
        avg = b / counts[topic]
        avg_str = f"{avg / 1e6:.2f} MB" if avg >= 1e5 else f"{avg / 1e3:.1f} KB"
        print(f"{topic:<48} {counts[topic]:>9} {b / 1e9:>8.2f} {100 * b / total:>6.1f}% "
              f"{rate:>8.1f} {avg_str:>10}")


if __name__ == "__main__":
    main()
