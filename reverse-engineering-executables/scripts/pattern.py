#!/usr/bin/env python3
"""Cyclic pattern for crash triage: which input offset controls the crash?

Usage:
  python3 pattern.py create [LENGTH]            # default 6760 (max unique)
  python3 pattern.py offset VALUE [LENGTH]      # VALUE: 0x-hex u32/u64 or raw bytes

Feed `create` output as the crashing input, read the faulted value
(EIP/RIP/return slot) from the debugger, then `offset <value>` maps it back
to the input offset that controls it. Offset knowledge = write-where.
"""
import argparse
import struct
import sys

UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LOWER = "abcdefghijklmnopqrstuvwxyz"
DIGITS = "0123456789"
MAXLEN = len(UPPER) * len(LOWER) * len(DIGITS)  # 6760 3-byte groups


def make_pattern(length: int) -> bytes:
    if length > MAXLEN:
        raise SystemExit(f"max unique pattern is {MAXLEN} bytes")
    out = bytearray()
    for a in UPPER:
        for b in LOWER:
            for c in DIGITS:
                if len(out) >= length:
                    return bytes(out[:length])
                out.extend((a + b + c).encode())
    return bytes(out[:length])


def find_offset(value: str, length: int) -> int:
    pat = make_pattern(length)
    needles = []
    raw = value.encode() if not value.lower().startswith("0x") else None
    if raw is not None:
        needles.append(("raw", raw))
    else:
        v = int(value, 16)
        for bits in (32, 64):
            if v >= (1 << bits):
                continue
            fmt = {32: "I", 64: "Q"}[bits]
            for endian, name in (("<", "le"), (">", "be")):
                needles.append((f"u{bits}-{name}", struct.pack(endian + fmt, v)))
    for name, needle in needles:
        off = pat.find(needle)
        if off >= 0:
            print(f"match: {name} {needle.hex(' ')} -> offset {off} (0x{off:x})")
            return off
    print(f"no match in first {length} bytes; is the value from this pattern? "
          "(truncated/case-folded/adjusted by a decoder?)")
    return -1


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("create")
    p1.add_argument("length", nargs="?", type=lambda x: int(x, 0), default=MAXLEN)
    p2 = sub.add_parser("offset")
    p2.add_argument("value", help="0x-hex integer or raw character string")
    p2.add_argument("length", nargs="?", type=lambda x: int(x, 0), default=MAXLEN)
    args = ap.parse_args()
    if args.cmd == "create":
        sys.stdout.buffer.write(make_pattern(args.length))
        sys.stdout.buffer.write(b"\n")
        return 0
    return 0 if find_offset(args.value, args.length) >= 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
