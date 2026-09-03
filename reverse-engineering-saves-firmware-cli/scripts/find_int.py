#!/usr/bin/env python3
"""Search one integer value in every common encoding at once.

Usage: python3 find_int.py FILE VALUE [--zigzag-only]
VALUE accepts 0x-prefix and negatives. Reports u8/s8, u16/32/64 le+be,
ULEB128, and zigzag32/64 hits as 0-based hex offsets.
"""
import argparse
import struct
from pathlib import Path


def uleb128(v: int) -> bytes:
    if v < 0:
        raise ValueError("ULEB128 needs non-negative")
    out = bytearray()
    while True:
        byte = v & 0x7F
        v >>= 7
        if v:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            break
    return bytes(out)


def zigzag(n: int, bits: int) -> int:
    return ((n << 1) ^ (n >> (bits - 1))) & ((1 << bits) - 1)


def hits(data: bytes, needle: bytes):
    start = 0
    while True:
        off = data.find(needle, start)
        if off < 0:
            return
        yield off
        start = off + 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("value")
    args = ap.parse_args()
    value = int(args.value, 0)
    data = Path(args.path).read_bytes()
    print(f"searching value={value} in {args.path} ({len(data)} bytes)")
    for name, fmt in (("u8", "B"), ("u16le", "<H"), ("u16be", ">H"),
                      ("u32le", "<I"), ("u32be", ">I"),
                      ("u64le", "<Q"), ("u64be", ">Q")):
        try:
            if fmt == "B":
                if not 0 <= value <= 255:
                    continue
                needle = struct.pack(fmt, value)
            elif "H" in fmt:
                if not 0 <= value <= 65535:
                    continue
                needle = struct.pack(fmt, value)
            elif "I" in fmt:
                if not 0 <= value <= 0xFFFFFFFF:
                    continue
                needle = struct.pack(fmt, value)
            else:
                if not 0 <= value <= 0xFFFFFFFFFFFFFFFF:
                    continue
                needle = struct.pack(fmt, value)
        except struct.error:
            continue
        for off in hits(data, needle):
            print(f"{name} 0x{off:08x} {needle.hex()}")
    # signed 8-bit form for negatives
    if -128 <= value <= 127:
        needle = struct.pack("b", value)
        for off in hits(data, needle):
            print(f"s8 0x{off:08x} {needle.hex()}")
    if value >= 0:
        enc = uleb128(value)
        for off in hits(data, enc):
            print(f"uleb128 0x{off:08x} {enc.hex()}")
    for bits in (32, 64):
        try:
            zz = zigzag(value, bits)
            enc = uleb128(zz)
            for off in hits(data, enc):
                print(f"zigzag{bits} 0x{off:08x} {enc.hex()} (zz={zz})")
        except ValueError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
