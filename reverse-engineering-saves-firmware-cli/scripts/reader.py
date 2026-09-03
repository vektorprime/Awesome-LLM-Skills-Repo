#!/usr/bin/env python3
"""Bounded binary Reader. Import this — do not retype it.

from reader import ParseError, Reader
r = Reader(data); magic = r.take(4, "magic"); ver = r.u16le("version")
Laws: explicit endian, exact error offsets, caps on counts/sizes.
"""
from __future__ import annotations
import struct
from dataclasses import dataclass


class ParseError(ValueError):
    pass


@dataclass
class Reader:
    data: bytes
    offset: int = 0

    def remaining(self) -> int:
        return len(self.data) - self.offset

    def require(self, size: int, label: str = "data") -> None:
        if size < 0:
            raise ParseError(f"negative size for {label}: {size}")
        if self.offset + size > len(self.data):
            raise ParseError(
                f"truncated {label}: need {size} bytes at 0x{self.offset:x}, "
                f"only {self.remaining()} remain")

    def take(self, size: int, label: str = "data") -> bytes:
        self.require(size, label)
        out = self.data[self.offset:self.offset + size]
        self.offset += size
        return out

    def unpack(self, fmt: str, label: str):
        size = struct.calcsize(fmt)
        self.require(size, label)
        vals = struct.unpack_from(fmt, self.data, self.offset)
        self.offset += size
        return vals[0] if len(vals) == 1 else vals

    def u8(self, label: str):  # type: ignore[no-untyped-def]
        v = self.unpack("<B", label)
        return v if isinstance(v, int) else v[0]

    def u16le(self, label: str):  # type: ignore[no-untyped-def]
        v = self.unpack("<H", label)
        return v if isinstance(v, int) else v[0]

    def u16be(self, label: str):  # type: ignore[no-untyped-def]
        v = self.unpack(">H", label)
        return v if isinstance(v, int) else v[0]

    def u32le(self, label: str):  # type: ignore[no-untyped-def]
        v = self.unpack("<I", label)
        return v if isinstance(v, int) else v[0]

    def u32be(self, label: str):  # type: ignore[no-untyped-def]
        v = self.unpack(">I", label)
        return v if isinstance(v, int) else v[0]

    def u64le(self, label: str):  # type: ignore[no-untyped-def]
        v = self.unpack("<Q", label)
        return v if isinstance(v, int) else v[0]

    def u64be(self, label: str):  # type: ignore[no-untyped-def]
        v = self.unpack(">Q", label)
        return v if isinstance(v, int) else v[0]

    def seek(self, offset: int, label: str = "offset") -> None:
        if not 0 <= offset <= len(self.data):
            raise ParseError(f"invalid {label}: 0x{offset:x}")
        self.offset = offset
