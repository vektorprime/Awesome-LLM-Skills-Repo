#!/usr/bin/env python3
"""Apply one byte patch with evidence: verify --old, write --new, log a ledger row.

Usage: python3 patch_bytes.py FILE --offset 0x4012A3 --old 0F84 --new 0F85 \
          --why "invert update-check branch" [--ledger patches.tsv]

Refuses to patch if the bytes at --offset do not equal --old (wrong-offset
guard). Prints before/after + SHA-256, and appends a ledger row (offset,
old, new, why, timestamp, output sha256) so a patch is always reviewable.
"""
import argparse
import datetime
import hashlib
from pathlib import Path


def parse_bytes(v: str) -> bytes:
    v = v.replace(" ", "")
    if v.lower().startswith("0x"):
        v = v[2:]
    if len(v) % 2:
        raise argparse.ArgumentTypeError(f"odd hex length: {v}")
    try:
        return bytes.fromhex(v)
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"bad hex: {e}")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for blk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(blk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--offset", required=True, type=lambda x: int(x, 0))
    ap.add_argument("--old", required=True, type=parse_bytes)
    ap.add_argument("--new", required=True, type=parse_bytes)
    ap.add_argument("--why", required=True, help="reason, recorded in the ledger")
    ap.add_argument("--ledger", default=None, help="ledger TSV to append to")
    args = ap.parse_args()
    if len(args.old) != len(args.new):
        raise SystemExit("--old and --new must be the same length "
                         "(length-changing patches need a code cave, see 14-binary-patching.md)")
    path = Path(args.file)
    if not path.exists():
        raise SystemExit(f"no such file: {path}")
    before = sha256(path)
    data = bytearray(path.read_bytes())
    if not 0 <= args.offset <= len(data) - len(args.old):
        raise SystemExit(f"offset 0x{args.offset:x}+{len(args.old)} outside file "
                         f"({len(data)} bytes)")
    at = bytes(data[args.offset:args.offset + len(args.old)])
    if at != args.old:
        raise SystemExit(f"mismatch at 0x{args.offset:x}: found {at.hex(' ')} "
                         f"expected {args.old.hex(' ')} — wrong offset or wrong build; refusing")
    data[args.offset:args.offset + len(args.old)] = args.new
    path.write_bytes(bytes(data))
    after = sha256(path)
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    row = (f"{args.offset:#x}\t{args.old.hex()}\t{args.new.hex()}\t{stamp}\t"
           f"{after}\t{args.why}")
    if args.ledger:
        lp = Path(args.ledger)
        if not lp.exists():
            lp.write_text("offset\told\tnew\ttimestamp\toutput_sha256\twhy\n", encoding="utf-8")
        with lp.open("a", encoding="utf-8") as f:
            f.write(row + "\n")
    print(f"patched 0x{args.offset:x}: {args.old.hex(' ')} -> {args.new.hex(' ')}")
    print(f"  why: {args.why}")
    print(f"  sha256 before: {before}")
    print(f"  sha256 after:  {after}")
    print(f"  ledger row: {row}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
