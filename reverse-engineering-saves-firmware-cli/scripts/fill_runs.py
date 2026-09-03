#!/usr/bin/env python3
"""Report long 0x00 / 0xFF runs (padding, erase blocks, sparse regions).

Usage: python3 fill_runs.py FILE [--min 256]
"""
import argparse
from pathlib import Path


def parse_int(v: str) -> int:
    return int(v, 0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--min", type=parse_int, default=256)
    args = ap.parse_args()
    data = Path(args.path).read_bytes()
    for value, name in ((0x00, "00"), (0xFF, "ff")):
        start = None
        # sentinel forces flush of a trailing run
        for i, b in enumerate(data + bytes([value ^ 0xFF])):
            if b == value and start is None:
                start = i
            elif b != value and start is not None:
                length = i - start
                if length >= args.min:
                    print(f"{name} 0x{start:08x}-0x{i-1:08x} length=0x{length:x} ({length})")
                start = None
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
