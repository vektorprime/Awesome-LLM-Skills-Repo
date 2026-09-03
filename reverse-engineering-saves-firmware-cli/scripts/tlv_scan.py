#!/usr/bin/env python3
"""Scan for ASCII-tag + u32-length chunk framing (LE and BE).

Usage: python3 tlv_scan.py FILE [--min-len 0] [--max-len 0x100000] [--max-hits 200]
A framing hypothesis is valid only if entries CHAIN gaplessly.
"""
import argparse
import struct
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--min-len", type=lambda x: int(x, 0), default=0)
    ap.add_argument("--max-len", type=lambda x: int(x, 0), default=0x100000)
    ap.add_argument("--max-hits", type=int, default=200)
    args = ap.parse_args()
    data = Path(args.path).read_bytes()
    shown = 0
    for off in range(0, len(data) - 8):
        tag = data[off:off + 4]
        if not all(0x20 <= b < 0x7F for b in tag):
            continue
        le = struct.unpack_from("<I", data, off + 4)[0]
        be = struct.unpack_from(">I", data, off + 4)[0]
        hit = None
        if args.min_len <= le <= min(args.max_len, len(data) - off - 8):
            hit = f"le_len=0x{le:x}"
        elif args.min_len <= be <= min(args.max_len, len(data) - off - 8):
            hit = f"be_len=0x{be:x}"
        if hit:
            print(f"0x{off:08x} tag={tag.decode()!r} {hit} next=0x{off+8+(le if 'le' in hit else be):x}")
            shown += 1
            if shown >= args.max_hits:
                print(f"... capped at {args.max_hits} hits; narrow the range")
                break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
