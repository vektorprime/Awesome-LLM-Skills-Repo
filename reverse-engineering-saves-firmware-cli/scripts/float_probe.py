#!/usr/bin/env python3
"""Decode one offset as float32/64 LE+BE with plausibility flags.

Usage: python3 float_probe.py FILE OFFSET
"""
import math
import struct
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: float_probe.py FILE OFFSET", file=sys.stderr)
        return 2
    data = Path(sys.argv[1]).read_bytes()
    off = int(sys.argv[2], 0)
    chunk = data[off:off + 8]
    print(f"bytes @0x{off:08x}: {chunk.hex(' ')}")
    for fmt in ("<f", ">f", "<d", ">d"):
        size = struct.calcsize(fmt)
        if len(chunk) < size:
            continue
        v = struct.unpack(fmt, chunk[:size])[0]
        sane = math.isfinite(v) and abs(v) < 1e9
        print(f"  {fmt:3s} {v!r} finite={math.isfinite(v)} plausible={sane}")
    # float16 hints
    if len(chunk) >= 2:
        for fmt in ("<e", ">e"):
            try:
                v = struct.unpack(fmt, chunk[:2])[0]
                print(f"  {fmt:3s} {v!r} finite={math.isfinite(v)}")
            except struct.error:
                print(f"  {fmt:3s} (struct without f16 support — use numpy if needed)")
                break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
