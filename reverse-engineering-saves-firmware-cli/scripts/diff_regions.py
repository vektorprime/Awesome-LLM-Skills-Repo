#!/usr/bin/env python3
"""Zero-based hex diff with merged regions + context. Streams nothing (lab-sized).

cmp -l prints 1-based DECIMAL offsets and OCTAL bytes — this script avoids
that trap. Usage: python3 diff_regions.py BEFORE AFTER [--merge-gap 4] [--context 16]
"""
import argparse
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("before")
    ap.add_argument("after")
    ap.add_argument("--merge-gap", type=int, default=0)
    ap.add_argument("--context", type=int, default=8)
    args = ap.parse_args()
    a = Path(args.before).read_bytes()
    b = Path(args.after).read_bytes()
    limit = max(len(a), len(b))
    changed = [i for i in range(limit)
               if (a[i] if i < len(a) else None) != (b[i] if i < len(b) else None)]
    if not changed:
        print("identical")
        return 0
    regions = []
    start = prev = changed[0]
    for off in changed[1:]:
        if off <= prev + args.merge_gap + 1:
            prev = off
        else:
            regions.append((start, prev))
            start = prev = off
    regions.append((start, prev))
    print(f"before_size={len(a)} after_size={len(b)} changed_bytes={len(changed)}")
    for s, e in regions:
        left = max(0, s - args.context)
        right = min(limit, e + args.context + 1)
        print(f"region 0x{s:08x}-0x{e:08x} length=0x{e-s+1:x} ({e-s+1})")
        print(f"  context 0x{left:08x}-0x{right-1:08x}")
        print(f"  before {a[left:min(right, len(a))].hex(' ')}")
        print(f"  after  {b[left:min(right, len(b))].hex(' ')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
