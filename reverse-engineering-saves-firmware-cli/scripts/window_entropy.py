#!/usr/bin/env python3
"""Windowed entropy + zero/0xFF fractions. Transitions matter, not values.

Usage: python3 window_entropy.py FILE [--window 0x1000] [--step STEP]
"""
import argparse
import math
from collections import Counter
from pathlib import Path


def entropy(block: bytes) -> float:
    if not block:
        return 0.0
    counts = Counter(block)
    total = len(block)
    return -sum((n / total) * math.log2(n / total) for n in counts.values())


def parse_int(v: str) -> int:
    return int(v, 0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--window", type=parse_int, default=4096)
    ap.add_argument("--step", type=parse_int, default=None)
    args = ap.parse_args()
    data = Path(args.path).read_bytes()
    step = args.step or args.window
    print("offset,length,entropy,zero_fraction,ff_fraction")
    for off in range(0, len(data), step):
        block = data[off:off + args.window]
        if not block:
            break
        zeros = block.count(0) / len(block)
        ffs = block.count(0xFF) / len(block)
        print(f"0x{off:08x},{len(block)},{entropy(block):.4f},{zeros:.4f},{ffs:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
