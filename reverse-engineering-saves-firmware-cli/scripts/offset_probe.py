#!/usr/bin/env python3
"""Scan a header region for plausible LE/BE offset/length/count fields.

Usage: python3 offset_probe.py FILE [START 0] [LENGTH 0x100]
Lists u32 fields whose value falls inside the file (leads, not proof).
"""
import struct
import sys
from pathlib import Path


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if path is None:
        print("usage: offset_probe.py FILE [START] [LENGTH]", file=sys.stderr)
        return 2
    start = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0
    length = int(sys.argv[3], 0) if len(sys.argv) > 3 else 0x100
    data = path.read_bytes()
    end = min(start + length, len(data))
    print(f"{path} size={len(data)} scanning 0x{start:x}..0x{end:x}")
    for off in range(start, max(start, end - 3), 4):
        raw = data[off:off + 4]
        le = struct.unpack("<I", raw)[0]
        be = struct.unpack(">I", raw)[0]
        tags = []
        if le < len(data):
            tags.append(f"le->0x{le:x}")
        if be < len(data):
            tags.append(f"be->0x{be:x}")
        if tags:
            print(f"field@0x{off:08x} {raw.hex()} {' '.join(tags)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
