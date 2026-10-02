#!/usr/bin/env python3
"""Apply ONE integer-field edit in place (spec-guided, minimal-edit loop).

Usage: python3 patch_int.py FILE --offset 0x1234 --value 999 --width 4 --endian le
       python3 patch_int.py FILE --offset 0x20 --value -5 --width 4 --endian le --signed
       python3 patch_int.py FILE --offset 0x30 --value 6 --expect-current 5 --width 4

One edit per experiment. --expect-current refuses to patch if the field does
not currently hold that value (wrong-offset guard). Does NOT touch
checksums — recompute dependents with checksum_candidates.py per the spec.
"""
import argparse
import hashlib
import struct
import sys
from pathlib import Path

UNSIGNED = {1: "<B", 2: "<H", 4: "<I", 8: "<Q"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for blk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(blk)
    return h.hexdigest()


def fmt_for(width: int, endian: str, signed: bool) -> str:
    base = {1: "B", 2: "H", 4: "I", 8: "Q"}[width]
    if signed:
        base = base.lower()
    return ("<" if endian == "le" else ">") + base


def range_for(width: int, signed: bool):
    bits = width * 8
    if signed:
        return -(1 << (bits - 1)), (1 << (bits - 1)) - 1
    return 0, (1 << bits) - 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--offset", required=True, type=lambda x: int(x, 0))
    ap.add_argument("--value", required=True, type=lambda x: int(x, 0))
    ap.add_argument("--width", required=True, type=int, choices=(1, 2, 4, 8))
    ap.add_argument("--endian", choices=("le", "be"), default="le")
    ap.add_argument("--signed", action="store_true",
                    help="encode value as two's-complement signed")
    ap.add_argument("--expect-current", type=lambda x: int(x, 0), default=None,
                    help="refuse unless the field currently holds this value")
    args = ap.parse_args()
    lo, hi = range_for(args.width, args.signed)
    if not lo <= args.value <= hi:
        raise SystemExit(f"value {args.value} out of range for width={args.width} "
                         f"signed={args.signed} [{lo}, {hi}]")
    fmt = fmt_for(args.width, args.endian, args.signed)
    path = Path(args.file)
    data = bytearray(path.read_bytes())
    if not 0 <= args.offset <= len(data) - args.width:
        raise SystemExit(f"offset 0x{args.offset:x}+{args.width} outside file "
                         f"({len(data)} bytes)")
    current = struct.unpack_from(fmt, data, args.offset)[0]
    if args.expect_current is not None and current != args.expect_current:
        raise SystemExit(f"field @0x{args.offset:x} holds {current}, expected "
                         f"{args.expect_current} — wrong offset or wrong build; refusing")
    old_raw = bytes(data[args.offset:args.offset + args.width])
    struct.pack_into(fmt, data, args.offset, args.value)
    new_raw = bytes(data[args.offset:args.offset + args.width])
    before = sha256(path)
    path.write_bytes(bytes(data))
    after = sha256(path)
    print(f"patched 0x{args.offset:x}: {current} -> {args.value} "
          f"({args.width}B {args.endian} signed={args.signed})")
    print(f"  raw: {old_raw.hex(' ')} -> {new_raw.hex(' ')}")
    print(f"  sha256 before: {before}")
    print(f"  sha256 after:  {after}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
