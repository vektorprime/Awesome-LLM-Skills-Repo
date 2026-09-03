# Survey — First 15 Minutes, Entropy, Classification

Do this **before** carving, editing, or recursive extraction. Output is a
one-page survey note + raw artifacts in `artifacts/survey/`. Everything here
is non-destructive.

```bash
CASE=case-001
F="$CASE/evidence/originals/artifact.bin"
OUT="$CASE/artifacts/survey"
mkdir -p "$OUT"
# Or: bash scripts/survey.sh "$F" "$OUT"
```

## 1. Identity, size, hashes, head + tail

```bash
file -k -- "$F" | tee "$OUT/file.txt"
stat --printf='size=%s bytes\nblocks=%b\nmtime=%y\n' -- "$F" | tee "$OUT/stat.txt"
sha256sum -- "$F" | tee "$OUT/sha256.txt"
xxd -g 1 -l 4096 "$F" | tee "$OUT/head-4096.txt"
tail -c 4096 -- "$F" | xxd -g 1 | tee "$OUT/tail-4096.txt"
```

Why both ends: headers hold magic/version/count/length/offsets; footers hold
checksums, signatures, central directories, duplicate headers. Some formats
(ZIP-style) put the directory at EOF. A 512-byte window misses large headers —
use 4096 and grow if the header declares a larger `header_len`.

Portability: `stat --printf` is GNU; on BSD/macOS use `stat -f '%z %Sm %p'`.
`xxd -g 1` ≈ `od -Ax -tx1z -v` ≈ `hexdump -C`. `tail -c N | xxd` works
everywhere.

## 2. Strings with offsets (three encodings minimum)

```bash
strings -a -n 4 -t x -- "$F" | tee "$OUT/strings-ascii.txt"
strings -a -n 4 -e l -t x -- "$F" | tee "$OUT/strings-utf16le.txt"
strings -a -n 4 -e b -t x -- "$F" | tee "$OUT/strings-utf16be.txt"
```

Hunt for: product/game/emulator/board names, versions, paths, XML/JSON/INI/
SQL keys, compression labels, partition names (`boot rootfs kernel config
nvram recovery`), slot names, PEM markers (`BEGIN … PRIVATE KEY`,
`CERTIFICATE`), URLs. **Offsets matter more than text** — a `rootfs` string
near an entry table is a structural anchor. Strings are leads, not proof
(unused library strings and deliberate plants exist).

Also try UTF-32 and raw bytes when scripts suggest non-Latin text:

```bash
strings -a -n 4 -e L -t x -- "$F" > "$OUT/strings-utf32le.txt" 2>&1 || true
python3 -c "import pathlib,sys; d=pathlib.Path(sys.argv[1]).read_bytes(); print('00 runs:', d.count(b'\x00'))" "$F"
```

## 3. Signature scan (leads only)

```bash
binwalk "$F" | tee "$OUT/binwalk.txt"
```

Then check which binwalk you have — v2 (Python) and v3 (Rust) differ:

```bash
binwalk --help 2>&1 | head -n 30
```

- v2 classic: `binwalk -Me -C <outdir> <file>` (recursive), `-e`, `-d <depth>`,
  `-A` opcode scan, `-E` entropy, `-D 'type:ext:cmd'` custom carve.
- v3 rewrite: `binwalk --extract --matryoshka`, `--carve` (keep carved raws),
  `--entropy`, `--log`, `--include/--exclude` filters. Old `-B`/`--dd`
  recipes may not exist.

Scan ≠ boundary. Every hit needs parser/length validation (see §6).

Recursive extraction alternative (verified syntax):

```bash
unblob --show-external-dependencies || true
unblob --report "$CASE/artifacts/reports/unblob.json" \
       -e "$CASE/artifacts/extracted/unblob" "$F"
```

Notes: default output without `-e` is `<input>_extract`; `--report` takes a
JSON path; `-d` caps recursion depth (default 10); `-n` controls entropy
depth. Run only in an isolated workspace; review the JSON (offsets, handlers,
unknown gaps) before trusting the tree.

## 4. Whole-file archive probes

```bash
7z l "$F" | tee "$OUT/7z-list.txt" || true
bsdtar -tf "$F" > "$OUT/bsdtar-list.txt" 2>&1 || true
zipinfo -v "$F" > "$OUT/zipinfo.txt" 2>&1 || true
```

A failure proves only that offset 0 is not that archive — embedded archives
at nonzero offsets are still possible. `7z l` recognizes many formats beyond
ZIP (gzip, xz, zstd, SquashFS listings sometimes).

## 5. Entropy + fill-pattern maps

Entropy alone never proves encryption. Map **transitions**, not values.

```bash
python3 scripts/window_entropy.py "$F" --window 0x1000 > "$OUT/entropy-4k.csv"
python3 scripts/fill_runs.py "$F" --min 256 > "$OUT/fill-runs.txt"
```

Interpretation guide (window 4 KiB, Shannon 0–8 bits/byte):

| Pattern | Candidates | Next test |
|---|---|---|
| ~7.5–8.0 sustained | compression, encryption, compressed media | try decompressors at boundary; test determinism across identical saves |
| ~4–6 mixed | text, code, tables, serialization | strings + structure probes |
| ~0–2 with `00` runs | padding, sparse, zeroed pages | `fill_runs.py`, alignment check |
| ~0–2 with `FF` runs | erased NOR/SPI flash (`0xFF`), unused partition | flash geometry? (§filesystems) |
| Sharp step at aligned offset | header→payload, partition edge, chunk start | `xxd -s <off-64> -l 128`, signature scan at offset |
| Sawtooth per N KiB | per-block compression, page journaling | block-hash diff (§saves) |

Small regions (<256 B) give noisy entropy — widen the window or skip the
verdict. Short high-entropy blobs can be hashes, keys, UUIDs, or compressed
thumbnails, not "encryption".

Zero/`0xFF` runs mark padding, alignment, erase blocks, reserved space, or
unused capacity. Do not strip them — record offset/length; they constrain
geometry and checksum ranges.

## 6. Magic-number quick catalogue

Check head bytes and every entropy-transition offset against this (hex):

```text
PK\x03\x04            ZIP / APK / OTA / OOXML / JAR
1F 8B                 gzip
FD 37 7A 58 5A 00     xz / LZMA2
28 B5 2F FD           Zstandard
04 22 4D 18           LZ4 frame
42 5A 68 ("BZh")      bzip2
78 01 / 78 9C / 78 DA zlib/deflate (common levels; MUST validate by decompress)
53 51 53 48 ("SQSH")  SquashFS (hsqs/sqsh variants; check endianness)
55 42 49 23 ("UBI#")  UBI erase-block header
28 B5 ...             (see Zstd above)
75 73 74 61 72 ("ustar") tar (offset 257)
53 51 4C 69 ("SQLi")  SQLite ("SQLite format 3\x00" at 0)
89 50 4E 47           PNG   FF D8 FF  JPEG   42 4D  BMP
25 50 44 46           PDF   7F 45 4C 46  ELF   4D 5A  PE
D0 CF 11 E0           OLE/CFB (old Office)   %!PS  PostScript
D5 32 30 31 ("D201")  U-Boot legacy uImage (0x27051956 BE)
D0 0D FE ED           FIT / FDT (0xD00DFEED BE)
70 30 37 30 ("0707")  CPIO (070701/070702 newc)
1F 9E / 1F A0         old compress/LZH variants
3A 5F 41 52 43 48     ("ARCH"? check) vendor headers — treat as lead
```

Endianness flips magic (`hsqs` vs `sqsh`). Carve candidates with
`scripts/carve.py` (byte-exact, hashed, logged) — never bare `dd bs=1` on GB
images (slow; use `iflag=skip_bytes,count_bytes` if you must use `dd`).

## 7. Classification decision tree

```text
[Unknown blob]
  +-> readable/db-like? (JSON/XML/INI/plist/SQLite/LevelDB/...) -> normalize + logical diff
  +-> whole-file archive/compression? -> extract ONE layer, hash child, re-survey child
  +-> filesystem/partition image?     -> read-only list, safe extract, keep metadata
  +-> vendor/update container?        -> map header, manifest, entries, offsets, integrity
  +-> opaque save/savestate?          -> sample matrix + differential experiments
  +-> still opaque?                   -> constants, alignments, offsets, records, entropy, checksums
```

Reclassify triggers: `78 9c` after "random" header (test zlib before crying
encryption); SQLite magic at nonzero offset (carve + `.schema`); FIT magic
(use entry metadata, not raw carve); whole-file churn after 1-point change
(test whole-file compression, IV/nonce, nondeterministic state first).

## 8. Survey deliverable (required before deeper work)

Write `artifacts/survey/note.md`:

```text
Artifact identity + provenance:
Size + SHA-256:
Recognized outer format (or "unrecognized at offset 0"):
Candidate embedded regions + offsets:
Visible strings + encodings:
Entropy / fill boundaries (offsets):
Likely next branch:
Unknowns:
Next three decisive tests (cheapest first):
```

Gate: no editing, carving, or recursive extraction until this note exists.
Automate the mechanical part: `scripts/survey.sh FILE OUTDIR` (+
`scripts/window_entropy.py`, `scripts/fill_runs.py`), but the conclusions are
always written by a human.
