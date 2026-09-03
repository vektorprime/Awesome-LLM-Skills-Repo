#!/usr/bin/env python3
"""Fill sample-matrix.csv sizes + SHA-256 (streaming-safe for large firmware).

Usage: python3 sample_matrix_fill.py MATRIX.CSV SAMPLES_DIR
Matches sample names with or without .bin/.sav/.state/.img suffix.
"""
import csv
import hashlib
import sys
from pathlib import Path

SUFFIXES = (".bin", ".sav", ".state", ".img", ".dat")


def sha256_stream(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for blk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(blk)
    return h.hexdigest()


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: sample_matrix_fill.py MATRIX.CSV SAMPLES_DIR", file=sys.stderr)
        return 2
    csv_path, sample_dir = Path(sys.argv[1]), Path(sys.argv[2])
    rows = list(csv.DictReader(csv_path.open(newline="", encoding="utf-8")))
    for row in rows:
        cand = sample_dir / row["sample"]
        if not cand.exists():
            for suf in SUFFIXES:
                if (sample_dir / (row["sample"] + suf)).exists():
                    cand = sample_dir / (row["sample"] + suf)
                    break
        if cand.exists():
            row["size"] = str(cand.stat().st_size)
            row["sha256"] = sha256_stream(cand)
        else:
            print(f"warning: no file for sample {row['sample']}", file=sys.stderr)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"updated {len(rows)} rows in {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
