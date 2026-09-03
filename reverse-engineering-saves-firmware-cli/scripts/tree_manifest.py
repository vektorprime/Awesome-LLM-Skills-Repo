#!/usr/bin/env python3
"""Streaming JSONL tree manifest: type, mode, uid/gid, size, sha256, symlink target.

Usage: python3 tree_manifest.py ROOT > root.manifest.jsonl
Safe for weird filenames (JSONL, not TSV). Flags symlinks/dev-nodes/FIFOs for review.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import stat
from pathlib import Path


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for blk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(blk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    for path in sorted(root.rglob("*"), key=lambda p: os.fsencode(str(p.relative_to(root)))):
        rel = str(path.relative_to(root))
        info = path.lstat()
        rec = {"path": rel, "mode": stat.filemode(info.st_mode),
               "uid": info.st_uid, "gid": info.st_gid, "size": info.st_size,
               "mtime_ns": info.st_mtime_ns}
        m = info.st_mode
        if stat.S_ISREG(m):
            rec["type"] = "file"
            rec["sha256"] = hash_file(path)
        elif stat.S_ISDIR(m):
            rec["type"] = "directory"
        elif stat.S_ISLNK(m):
            rec["type"] = "symlink"
            rec["target"] = os.readlink(path)
        elif stat.S_ISCHR(m):
            rec["type"] = "char-device"
            rec["rdev"] = getattr(info, "st_rdev", 0)
        elif stat.S_ISBLK(m):
            rec["type"] = "block-device"
            rec["rdev"] = getattr(info, "st_rdev", 0)
        elif stat.S_ISFIFO(m):
            rec["type"] = "fifo"
        elif stat.S_ISSOCK(m):
            rec["type"] = "socket"
        else:
            rec["type"] = "other"
        print(json.dumps(rec, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
