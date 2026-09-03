#!/usr/bin/env python3
"""Decode one offset as every common timestamp/counter encoding.

Usage: python3 timestamp_probe.py FILE OFFSET
Covers: unix32/64 s+ms+us, FILETIME, DOS datetime, Cocoa, GPS.
A decode is a LEAD — confirm with wall-clock delta tests.
"""
import struct
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

DOS_EPOCH_NOTE = "DOS datetime packs date+time into 2+2 bytes (see reference)"
COCOA_OFFSET = 978307200  # Cocoa seconds -> unix
GPS_OFFSET = 315964800    # GPS seconds -> unix (ignores leap seconds)


def show(label: str, ts, lo=-62135596800, hi=4102444800):
    try:
        if ts is None or not lo <= ts <= hi:
            print(f"  {label}: {ts} (out of range)")
            return
        print(f"  {label}: {datetime.fromtimestamp(ts, timezone.utc).isoformat()}")
    except (OverflowError, OSError, ValueError) as e:
        print(f"  {label}: {ts} ({e})")


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: timestamp_probe.py FILE OFFSET", file=sys.stderr)
        return 2
    data = Path(sys.argv[1]).read_bytes()
    o = int(sys.argv[2], 0)
    if not 0 <= o < len(data):
        raise SystemExit("offset outside file")
    print(f"bytes @0x{o:08x}: {data[o:o+8].hex(' ')}")
    for endian in ("<", ">"):
        tag = "le" if endian == "<" else "be"
        u32 = struct.unpack_from(endian + "I", data, o)[0] if o + 4 <= len(data) else None
        u64 = struct.unpack_from(endian + "Q", data, o)[0] if o + 8 <= len(data) else None
        d32 = struct.unpack_from(endian + "i", data, o)[0] if o + 4 <= len(data) else None
        print(f"[{tag}] u32={u32} s32={d32} u64={u64}")
        if u32 is not None:
            show(f"{tag} unix32-s", u32)
        if u64 is not None:
            show(f"{tag} unix64-s", u64)
            show(f"{tag} unix64-ms", u64 / 1000)
            show(f"{tag} unix64-us", u64 / 1_000_000)
            show(f"{tag} cocoa-s", u64 - COCOA_OFFSET if u64 > COCOA_OFFSET else None)
            show(f"{tag} gps-s", u64 - GPS_OFFSET if u64 > GPS_OFFSET else None)
            try:
                ft = datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=u64 / 10)
                print(f"  {tag} filetime: {ft.isoformat()}")
            except OverflowError:
                print(f"  {tag} filetime: out of range")
        if o + 4 <= len(data):
            d, t = struct.unpack_from(endian + "HH", data, o)
            try:
                dt = datetime(((d >> 9) + 1980), ((d >> 5) & 15) or 1, (d & 31) or 1,
                              (t >> 11), ((t >> 5) & 63), ((t & 31) * 2) % 60,
                              tzinfo=timezone.utc)
                print(f"  {tag} dos-datetime: {dt.isoformat()}")
            except ValueError as e:
                print(f"  {tag} dos-datetime: invalid ({e})")
    print(f"note: {DOS_EPOCH_NOTE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
