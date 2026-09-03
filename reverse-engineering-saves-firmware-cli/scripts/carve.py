#!/usr/bin/env python3
"""Byte-exact carve with provenance. Streams input; safe for large images.

Usage: python3 carve.py SOURCE OUTPUT --offset 0x100 --length 0x200 [--metadata out.json]
"""
import argparse
import hashlib
import json
from pathlib import Path


def parse_int(v: str) -> int:
    return int(v, 0)


def sha256_stream(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for blk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(blk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("output")
    ap.add_argument("--offset", required=True, type=parse_int)
    ap.add_argument("--length", required=True, type=parse_int)
    ap.add_argument("--metadata", default=None)
    args = ap.parse_args()
    src = Path(args.source)
    dst = Path(args.output)
    size = src.stat().st_size
    if args.offset < 0 or args.length < 0:
        raise SystemExit("offset and length must be non-negative")
    if args.offset + args.length > size:
        raise SystemExit(f"region 0x{args.offset:x}+0x{args.length:x} past EOF 0x{size:x}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    h_out = hashlib.sha256()
    with src.open("rb") as f, dst.open("wb") as o:
        f.seek(args.offset)
        remaining = args.length
        while remaining > 0:
            chunk = f.read(min(1024 * 1024, remaining))
            if not chunk:
                raise SystemExit("short read")
            o.write(chunk)
            h_out.update(chunk)
            remaining -= len(chunk)
    record = {
        "source": str(src),
        "source_sha256": sha256_stream(src),
        "source_size": size,
        "offset": args.offset,
        "offset_hex": hex(args.offset),
        "length": args.length,
        "length_hex": hex(args.length),
        "output": str(dst),
        "output_sha256": h_out.hexdigest(),
    }
    text = json.dumps(record, indent=2, sort_keys=True)
    print(text)
    if args.metadata:
        Path(args.metadata).write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
