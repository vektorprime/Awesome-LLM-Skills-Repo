#!/usr/bin/env python3
"""Per-block SHA-256 comparison. Finds WHICH pages/chunks changed.

Usage: python3 block_hashes.py BEFORE AFTER [BLOCKSIZE]  (BLOCKSIZE default 4096, 0x-prefix ok)
"""
import hashlib
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: block_hashes.py BEFORE AFTER [BLOCKSIZE]", file=sys.stderr)
        return 2
    a = Path(sys.argv[1]).read_bytes()
    b = Path(sys.argv[2]).read_bytes()
    block = int(sys.argv[3], 0) if len(sys.argv) > 3 else 4096
    if block <= 0:
        raise SystemExit("blocksize must be positive")
    print(f"block=0x{block:x} ({block}) before={len(a)} after={len(b)}")
    for off in range(0, max(len(a), len(b)), block):
        x, y = a[off:off + block], b[off:off + block]
        if hashlib.sha256(x).digest() != hashlib.sha256(y).digest():
            n = sum(p != q for p, q in zip(x, y)) + abs(len(x) - len(y))
            print(f"0x{off:08x} changed_bytes={n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
