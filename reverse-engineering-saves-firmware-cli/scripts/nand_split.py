#!/usr/bin/env python3
"""Test a raw-NAND page/OOB geometry hypothesis. Streams; refuses bad strides.

Usage: python3 nand_split.py RAW PAGE OOB DATA_OUT [OOB_OUT]
Example: python3 nand_split.py dump.bin 2048 64 data.bin oob.bin
Keep BOTH outputs + exact command. Compare several geometries; the winner
shows coherent structure (magic at block starts, valid FS, sane entropy).
"""
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 5:
        print("usage: nand_split.py RAW PAGE OOB DATA_OUT [OOB_OUT]", file=sys.stderr)
        return 2
    raw, page, oob = Path(sys.argv[1]), int(sys.argv[2], 0), int(sys.argv[3], 0)
    data_out, oob_out = Path(sys.argv[4]), Path(sys.argv[5]) if len(sys.argv) > 5 else None
    stride = page + oob
    size = raw.stat().st_size
    if stride <= 0 or page <= 0 or oob < 0:
        raise SystemExit("PAGE>0, OOB>=0 required")
    if size % stride:
        raise SystemExit(f"size {size} (0x{size:x}) not divisible by stride {stride} — wrong geometry")
    pages = size // stride
    with raw.open("rb") as f, data_out.open("wb") as d:
        o = oob_out.open("wb") if oob_out else None
        try:
            for _ in range(pages):
                chunk = f.read(stride)
                if len(chunk) != stride:
                    raise SystemExit("short read")
                d.write(chunk[:page])
                if o is not None:
                    o.write(chunk[page:])
        finally:
            if o is not None:
                o.close()
    print(f"pages={pages} page={page} oob={oob} data={data_out} ({data_out.stat().st_size} B)"
          + (f" oob={oob_out}" if oob_out else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
