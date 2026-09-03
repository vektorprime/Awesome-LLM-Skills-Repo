#!/usr/bin/env python3
"""Checksum/hash candidates over structured ranges.

Usage: python3 checksum_candidates.py FILE [FIELD_OFF] [FIELD_LEN]
Tests sums, CRC-32, Adler-32, MD5/SHA1/SHA256 over: whole, payload-after-field,
header-before-field, all-but-field, zeroed-field. Compare against stored bytes
(shown LE+BE) manually — a match must REPEAT on 3+ samples and PREDICT edits.
"""
import binascii
import hashlib
import struct
import sys
import zlib
from pathlib import Path


def show(name: str, val: int, width: int):
    print(f"  {name:22s} {val:0{width}x} ({val})")


def hash_ranges(data: bytes, label: str):
    print(f"[{label}] len={len(data)}")
    show("sum8", sum(data) & 0xFF, 2)
    show("sum16", sum(data) & 0xFFFF, 4)
    show("sum32", sum(data) & 0xFFFFFFFF, 8)
    show("crc32", zlib.crc32(data) & 0xFFFFFFFF, 8)
    show("crc_hqx", binascii.crc_hqx(data, 0) & 0xFFFF, 4)
    show("adler32", zlib.adler32(data) & 0xFFFFFFFF, 8)
    print(f"  md5                    {hashlib.md5(data).hexdigest()}")
    print(f"  sha1                   {hashlib.sha1(data).hexdigest()}")
    print(f"  sha256                 {hashlib.sha256(data).hexdigest()}")


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: checksum_candidates.py FILE [FIELD_OFF] [FIELD_LEN]", file=sys.stderr)
        return 2
    data = Path(sys.argv[1]).read_bytes()
    hash_ranges(data, "whole-file")
    if len(sys.argv) >= 4:
        off, size = int(sys.argv[2], 0), int(sys.argv[3], 0)
        stored = data[off:off + size] if 0 <= off <= len(data) - size else b""
        print(f"[stored field @0x{off:x} len={size}] raw={stored.hex()}")
        if size in (2, 4, 8) and stored:
            for e, n in (("<", "le"), (">", "be")):
                fmt = e + {2: "H", 4: "I", 8: "Q"}[size]
                print(f"  stored-{n}: {struct.unpack(fmt, stored)[0]} (0x{struct.unpack(fmt, stored)[0]:x})")
        variants = {
            "payload-after-field": data[off + size:],
            "header-before-field": data[:off],
            "all-but-field": data[:off] + data[off + size:],
            "zeroed-field": data[:off] + bytes(size) + data[off + size:],
        }
        for label, variant in variants.items():
            if variant:
                hash_ranges(variant, label)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
