#!/usr/bin/env python3
"""Find VALIDATED zlib streams. Magic alone lies; decompression decides.

Usage: python3 zlib_scan.py FILE [--min-out 16]
Prints offset, consumed bytes, decompressed size for streams reaching EOF.
"""
import argparse
import zlib
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--min-out", type=int, default=16)
    args = ap.parse_args()
    data = Path(args.path).read_bytes()
    found = 0
    for off in range(len(data) - 2):
        cmf, flg = data[off], data[off + 1]
        if (cmf & 0x0F) != 8:
            continue
        if ((cmf << 8) + flg) % 31 != 0:
            continue
        d = zlib.decompressobj()
        try:
            out = d.decompress(data[off:])
            out += d.flush()
        except zlib.error:
            continue
        if not d.eof:
            continue
        consumed = len(data[off:]) - len(d.unused_data)
        if consumed >= 8 and len(out) >= args.min_out:
            print(f"offset=0x{off:x} consumed={consumed} (0x{consumed:x}) output={len(out)}")
            found += 1
    if not found:
        print("no validated zlib streams (try raw-deflate/gzip/per-block variants manually)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
