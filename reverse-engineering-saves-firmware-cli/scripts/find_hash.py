#!/usr/bin/env python3
"""Find ROM/disc digests inside a savestate (binary + hex-lower + hex-upper).

Usage: python3 find_hash.py STATE ROM
Absence of a whole-file digest does NOT rule out identity binding
(headerless hashing, per-track, DB keys are all common).
"""
import hashlib
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: find_hash.py STATE ROM", file=sys.stderr)
        return 2
    state = Path(sys.argv[1]).read_bytes()
    rom = Path(sys.argv[2]).read_bytes()
    print(f"state={len(state)} rom={len(rom)}")
    found = False
    for name in ("md5", "sha1", "sha256"):
        digest = getattr(hashlib, name)(rom).digest()
        hexd = digest.hex().encode()
        for form, needle in (("binary", digest), ("hex-lower", hexd), ("hex-upper", hexd.upper())):
            off = state.find(needle)
            if off >= 0:
                print(f"{name} {form} @0x{off:x}")
                found = True
    # CRC-32 too (emulators love it)
    import zlib
    import struct
    for fmt, endian in (("<I", "le"), (">I", "be")):
        needle = struct.pack(fmt, zlib.crc32(rom) & 0xFFFFFFFF)
        off = state.find(needle)
        if off >= 0:
            print(f"crc32 {endian} @0x{off:x}")
            found = True
    if not found:
        print("no whole-file digest found (try headerless ROM / title strings / serials)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
