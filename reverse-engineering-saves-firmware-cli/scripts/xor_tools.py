#!/usr/bin/env python3
"""XOR / ADD obfuscation toolkit: single-byte brute force, repeating-key guess, known-plaintext.

Subcommands:
  single-byte FILE [--top 5]            try all 256 keys, score printable+structured
  repeating-key FILE [--max-keylen 16]  normalized Hamming-distance keylen guess
  known-plaintext FILE --offset O --plaintext TEXT [--keylen N]
"""
import argparse
import string
from pathlib import Path


def score(buf: bytes) -> float:
    if not buf:
        return -1e9
    printable = sum(1 for b in buf if 32 <= b < 127 or b in (9, 10, 13))
    zeros = buf.count(0) / len(buf)
    return printable / len(buf) - zeros


def hamming(a: bytes, b: bytes) -> int:
    return sum(bin(x ^ y).count("1") for x, y in zip(a, b))


def cmd_single(args) -> int:
    data = Path(args.file).read_bytes()[:65536]
    ranked = sorted(((score(bytes(b ^ k for b in data)), k) for k in range(256)), reverse=True)
    for s, k in ranked[:args.top]:
        prev = bytes(b ^ k for b in data[:64])
        print(f"key=0x{k:02x} ({k:3d}) score={s:.3f} preview={prev.hex(' ')}")
        print(f"  ascii: {''.join(chr(b) if 32 <= b < 127 else '.' for b in prev)}")
    return 0


def cmd_repeating(args) -> int:
    data = Path(args.file).read_bytes()
    print("keylen  norm_hamming (lower = more likely repeating-XOR)")
    for kl in range(2, args.max_keylen + 1):
        blocks = [data[i:i + kl] for i in range(0, min(len(data), kl * 8), kl)]
        blocks = [b for b in blocks if len(b) == kl]
        if len(blocks) < 2:
            continue
        dists = [hamming(blocks[i], blocks[i + 1]) / kl for i in range(len(blocks) - 1)]
        print(f"{kl:6d}  {sum(dists) / len(dists):.3f}")
    return 0


def cmd_known(args) -> int:
    data = Path(args.file).read_bytes()
    pt = args.plaintext.encode()
    ks = bytes(c ^ p for c, p in zip(data[args.offset:args.offset + len(pt)], pt))
    print(f"derived keystream @0x{args.offset:x}: {ks.hex(' ')}")
    # repeating-key test
    for kl in ([args.keylen] if args.keylen else (1, 2, 4, 8, 16, 32)):
        if kl <= 0 or kl > len(ks):
            continue
        reps = len(ks) // kl
        ok = all(ks[i * kl:(i + 1) * kl] == ks[:kl] for i in range(1, reps))
        print(f"  keylen={kl}: repeats={ok} key={ks[:kl].hex(' ')}")
    print("confirm with 2+ independent plaintexts/offsets before declaring XOR")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("single-byte")
    p.add_argument("file")
    p.add_argument("--top", type=int, default=5)
    p = sub.add_parser("repeating-key")
    p.add_argument("file")
    p.add_argument("--max-keylen", type=int, default=16)
    p = sub.add_parser("known-plaintext")
    p.add_argument("file")
    p.add_argument("--offset", type=lambda x: int(x, 0), required=True)
    p.add_argument("--plaintext", required=True)
    p.add_argument("--keylen", type=int, default=0)
    args = ap.parse_args()
    return {"single-byte": cmd_single, "repeating-key": cmd_repeating,
            "known-plaintext": cmd_known}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
