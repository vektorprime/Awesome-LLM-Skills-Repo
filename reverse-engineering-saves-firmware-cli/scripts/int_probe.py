#!/usr/bin/env python3
"""Decode ONE offset as every int/float width + endianness.

Usage: python3 int_probe.py FILE OFFSET  (OFFSET hex ok)
Beginner-proof replacement for eyeballing hex.
"""
import math
import struct
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: int_probe.py FILE OFFSET", file=sys.stderr)
        return 2
    data = Path(sys.argv[1]).read_bytes()
    off = int(sys.argv[2], 0)
    if not 0 <= off < len(data):
        raise SystemExit(f"offset 0x{off:x} outside file ({len(data)} bytes)")
    b = data[off:off + 8]
    print(f"bytes @0x{off:08x}: {b.hex(' ')}")
    for size, fmts in ((1, ("<B", ">B", "<b", ">b")),
                       (2, ("<H", ">H", "<h", ">h")),
                       (4, ("<I", ">I", "<i", ">i", "<f", ">f")),
                       (8, ("<Q", ">Q", "<q", ">q", "<d", ">d"))):
        if len(b) < size:
            continue
        for fmt in fmts:
            try:
                v = struct.unpack(fmt, b[:size])[0]
            except struct.error:
                continue
            extra = ""
            if "f" in fmt or "d" in fmt:
                extra = f" finite={math.isfinite(v)}"
            print(f"  {fmt:4s} {v!r}{extra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
