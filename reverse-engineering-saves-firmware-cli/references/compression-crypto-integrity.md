# Compression, Obfuscation, Encryption — Telling Them Apart

Small logical change ⇒ huge byte churn usually means compression or
encryption (or nondeterministic serialization). High entropy alone decides
nothing. Work this order: **decompressors → weak obfuscation → keyed crypto
verdict**.

## 1. Compression detection and recovery

Suspects: structured low-entropy header + high-entropy payload; declared
`comp_len`/`raw_len` pairs; repeated chunk headers; whole-file churn with
stable size; known magic (see `survey.md` catalogue).

Candidates: zlib/deflate, gzip, xz/LZMA, bzip2, LZ4, Zstandard, LZO, plus
per-block variants. Test at the boundary offset, not offset 0:

```bash
scripts/carve.py save.bin payload.bin --offset 0x40 --length 0x800 --metadata payload.json
file payload.bin
python3 - payload.bin out.bin <<'PY'
import sys, zlib
from pathlib import Path
src = Path(sys.argv[1]).read_bytes()
Path(sys.argv[2]).write_bytes(zlib.decompress(src))
print(f"compressed={len(src)} decompressed={len(Path(sys.argv[2]).read_bytes())}")
PY
```

If it fails, vary: header-skewed offset (±1..16), raw deflate
(`decompressobj(-15)`), gzip wrapper, multiple concatenated streams,
trailing data (`unused_data`), dictionary. `7z l payload.bin` and
`binwalk payload.bin` catch non-zlib streams.

Scan-then-validate (never trust magic alone — `78 9C`-likes occur by chance):

```bash
python3 scripts/zlib_scan.py "$F"
# prints only streams that decompress to EOF with sane consumed/output sizes
```

Round-trip vocabulary: **semantic round trip** (decompress→parse→rebuild→app
accepts) vs **byte-identical round trip** (rebuilt bytes == original).
Recompression often differs (level, lib version, dict, block split,
timestamps) — semantic success is the real gate; byte-identity is a bonus.
State which one you achieved.

Whole-file vs per-block: one header + one stream + global churn ⇒ whole-file;
repeated tag+len pairs + localized churn + independent chunk decompresses +
`comp_len`/`raw_len` in entry headers ⇒ per-block. Carve with
`scripts/carve.py` (logged offsets/hashes), never bare `dd bs=1` on big files.

## 2. Obfuscation (weak, keyless, deterministic)

Indicators: repeating-key XOR, add/sub constant, nibble swap, rotation,
fixed substitution table, interleave, Base64/custom alphabet, stable output
for identical input (no nonce).

Single-byte XOR brute force (score for structured/text output):

```bash
python3 scripts/xor_tools.py single-byte payload.bin --top 5
python3 scripts/xor_tools.py repeating-key payload.bin --max-keylen 16
python3 scripts/xor_tools.py known-plaintext payload.bin --offset 0x40 --plaintext "Player"
```

Known-plaintext method: `keystream = ciphertext ⊕ known_plaintext` at the
suspected offset; a repeating derived key across several known values +
offsets ⇒ repeating-XOR confirmed. ADD/SUB: same but subtract. Always confirm
with 2+ independent known strings before declaring victory — compression
artifacts mimic short XOR runs.

Base64: find `[A-Za-z0-9+/]{64,}={0,2}` runs, decode, re-survey the output.
Custom alphabets: frequency + `=`-pad position give the mapping away.

## 3. Encryption (keyed, strong)

Indicators: structured header + high-entropy body; per-save random nonce/IV;
fixed-size tag (8/12/16 B); block alignment (16 B); identical plaintext ⇒
unrelated ciphertext; algorithm/key-derivation strings; key/cert material
nearby.

Decision procedure:

1. Rule out compression + weak obfuscation above (with commands logged).
2. Test determinism: save identical state 3×. Identical bytes ⇒ deterministic
   (ECB? no nonce? obfuscation?); differing bytes ⇒ nonce/IV or nondeterminism
   — locate the changing prefix (usually 8–16 B nonce) vs full diffusion.
3. Bound the ciphertext: first high-entropy offset → last byte before
   tag/trailer. Note alignment and tag length.
4. Hunt key sources **inside authorized data only**: config partitions,
   key files, manifest KDF parameters, device-unique derivations you are
   entitled to. Never exfiltrate or brute-force production keys as "training".
5. If no testable key hypothesis exists, STOP and document (below). Do not
   burn days guessing at random bytes.

Stop-and-document template:

```text
Plaintext header fields (offsets):
Ciphertext range (offsets):
Nonce/IV/tag candidates (offsets, widths, determinism):
Determinism across identical saves:
Key sources tested:
Why blocked (key / docs / producer instrumentation needed):
```

## 4. Distinguishing table

| Test | Compression | Obfuscation | Encryption |
|---|---|---|---|
| Identical saves identical? | yes | yes | often no (nonce) |
| Known header magic? | often (`78 9C`, `1F 8B`, …) | sometimes (custom) | rarely in body |
| Carve decompresses? | **yes** | no | no |
| XOR/keystream repeats? | short false runs | **yes, stable** | no (keystream looks random) |
| Key/nonce/tag fields? | lengths, not tags | no | **yes** |
| Outcome | semantic round trip | invert function + re-apply | boundary + key request |

## 5. Where checksums fit

Compression and integrity interact: CRC may cover compressed bytes,
decompressed bytes, or header-minus-field. Test all three explicitly with
`scripts/checksum_candidates.py` (see `saves-differential.md`). Recompress
before checksumming when the spec says the CRC is over stored bytes; checksum
before compressing when it covers raw bytes. Getting this order wrong is the
#1 "my fix never validates" cause.
