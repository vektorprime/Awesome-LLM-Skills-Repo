---
name: reverse-engineering-saves-firmware-cli
description: CLI-first reverse engineering of non-executable blobs — saved-game files, emulator savestates, firmware update packages, raw flash dumps, filesystem images, and opaque binary data. Use when asked to map binary structure, carve layers, recover fields by differential analysis, identify compression/checksums/encryption, extract firmware filesystems, or build a bounded parser with tests. Does NOT cover disassembly, decompilation, or exploit development.
---

# CLI-First Reverse Engineering of Saves, Savestates & Firmware (Non-EXE)

**Goal:** produce a tested structural specification, a bounded parser, and an
evidence package that a second engineer can reproduce without talking to you.

> The objective is not to "open the file." The objective is to explain its
> layers, field boundaries, encodings, integrity mechanisms, and transformation
> steps **with evidence**.

**Out of scope:** disassembling binaries found inside firmware, decompilation,
debugger-based program analysis, bypassing signature verification on deployed
devices, exploit development, malware analysis, extracting content without
authorization.

## How to use this skill (progressive disclosure)

This `SKILL.md` is a **router**. Do NOT read every reference up front.

1. Read `references/fundamentals.md` first (evidence labels, layer model,
   definition of done, failure modes). It is short and mandatory.
2. Run the non-destructive survey (`references/survey.md`) and write the
   one-page survey note **before** carving, editing, or recursive extraction.
3. Classify with the decision tree in `references/survey.md`, then read **only**
   the reference(s) for your branch.
4. Use `scripts/` — do not retype long inline snippets. Every script has
   `--help`.
5. Follow one checklist in `checklists/`, fill one template in `templates/`,
   and close with `references/automation-reporting.md`.

## Mandatory workflow

```text
preserve (read-only original + hashes + provenance + tool versions)
  -> survey (header, footer, strings, signatures, entropy, fill runs)
    -> classify layers (archive / compression / filesystem / container / opaque save / savestate)
      -> one-variable experiments (sample matrix, stability baseline first)
        -> prove boundaries (offsets, lengths, counts, transforms, integrity coverage)
          -> encode in bounded parser + tests + fuzz
            -> document unknowns + handoff
```

**Evidence labels (use on every claim):**

| Label | Meaning |
|---|---|
| **Observed** | Directly shown by bytes, a parser, or a controlled experiment |
| **Inferred** | Best explanation of several observations, not yet independently proven |
| **Unknown** | Untested, conflicting, or insufficient evidence |

**Confidence:** **High** = multiple independent samples or parser + controlled
modification; **Medium** = one direct observation or several consistent clues;
**Low** = plausible hypothesis awaiting a decisive test.

**Definition of done:** the original question has a defensible answer; every
transformation is reproducible; the parser rejects truncated/malformed input;
findings hold across multiple samples; unknowns are documented; a peer can
reproduce the result from the package alone.

## Router — what to read next

| Situation | Read this | Scripts / templates |
|---|---|---|
| Always (principles, layers, failures) | `references/fundamentals.md` | `templates/field-map.md` |
| First 15 min survey, entropy, classification | `references/survey.md` | `scripts/survey.sh`, `scripts/window_entropy.py`, `scripts/fill_runs.py` |
| Integers, endianness, strings, floats, timestamps, tables, TLV, flags | `references/binary-structure.md` | `scripts/int_probe.py`, `scripts/float_probe.py`, `scripts/timestamp_probe.py`, `scripts/offset_probe.py`, `scripts/tlv_scan.py` |
| JSON/XML/SQLite/protobuf/MessagePack/CBOR/BSON | `references/serialization.md` | normalize with `jq`, `sqlite3`, `protoc --decode_raw` |
| Opaque save: matrix, stability, diffs, numeric recovery, edit loop | `references/saves-differential.md` | `scripts/diff_regions.py`, `scripts/find_int.py`, `scripts/block_hashes.py`, `templates/experiment-log.md` |
| Compression vs obfuscation vs encryption; CRC/hash/MAC/signature; journaling | `references/compression-crypto-integrity.md` | `scripts/zlib_scan.py`, `scripts/checksum_candidates.py`, `scripts/xor_tools.py` |
| Emulator savestate (chunks, RAM, thumbnail, versions) | `references/savestates.md` | `scripts/find_hash.py`, `checklists/savestate.md` |
| Firmware layers, provenance, binwalk/unblob, partitions, U-Boot/FIT, DTB | `references/firmware-containers.md` | `scripts/carve.py`, `templates/layer-ledger.md` |
| SquashFS, UBI/UBIFS, JFFS2, CramFS, ext, FAT, CPIO, sparse, raw NAND/OOB | `references/filesystems-flash.md` | `scripts/nand_split.py`, `scripts/tree_manifest.py` |
| Manifests, boot map, secrets, version-to-version diff | `references/firmware-analysis.md` | `checklists/firmware.md` |
| Spec writing, bounded parser, Kaitai, tests, fuzz, safe rebuild | `references/parser-spec.md` | `scripts/reader.py`, `templates/spec-template.md` |
| Playbooks, final checklist, peer review, report, escalation, command ref, training | `references/automation-reporting.md` | `checklists/*.md`, `templates/report-template.md` |

## Safety (non-negotiable)

- Confirm authorization and data ownership before starting.
- Work on copies; originals stay read-only (`chmod 0444`) and hashed.
- Never upload proprietary artifacts to public analysis services.
- Prefer userspace extraction over kernel mounts; never mount unknown
  filesystems on a production workstation.
- Recursive extraction only in a disposable VM / restricted environment with
  resource limits and an empty destination directory.
- Inspect symlinks, device nodes, FIFOs, absolute paths, `../` traversal, and
  decompression size **before** trusting an extracted tree.
- Never run scripts, installers, hooks, or binaries extracted from firmware.
- Never flash experimental firmware without explicit authorization plus a
  tested recovery path.
- Saved games and firmware may contain credentials, keys, PII, and customer
  data — restrict access, redact reports.

## Case layout (create per artifact family)

```text
case-001/
├── evidence/originals/  + hashes.sha256 + provenance.md
├── samples/baseline|experiments|versions/ + sample-matrix.csv
├── artifacts/survey|carved|extracted|normalized|diffs|reports/
├── scripts/  (copies or symlinks of the scripts you actually ran)
├── spec/     (live format specification)
├── tests/fixtures/valid|invalid/ + test_*.py
├── notes/field-map.md + hypotheses.md + experiment-log.md + decisions.md
└── tool-versions.txt
```

## Script index (run, don't retype)

```text
scripts/survey.sh <file> <outdir>          # non-destructive first survey
scripts/window_entropy.py <file>           # entropy + zero/ff fractions per window
scripts/fill_runs.py <file>                # long 0x00 / 0xFF runs (padding, erase blocks)
scripts/carve.py SRC DST --offset O --length L [--metadata JSON]
scripts/diff_regions.py BEFORE AFTER [--merge-gap N] [--context N]
scripts/block_hashes.py A B [blocksize]    # which 4K pages / chunks changed
scripts/find_int.py <file> <value>         # u8/u16/u32/u64 le+be + LEB128/zigzag search
scripts/int_probe.py <file> <offset>       # one offset as every int/float width + endian
scripts/float_probe.py <file> <offset>     # float32/64 le+be + plausibility flags
scripts/timestamp_probe.py <file> <offset> # unix/ms/us, FILETIME, DOS, Cocoa, GPS
scripts/offset_probe.py <file> [start] [len]
scripts/tlv_scan.py <file>                 # ASCII-tag + length walker (le+be)
scripts/zlib_scan.py <file>                # validated zlib streams (offset, consumed, outlen)
scripts/checksum_candidates.py <file> [off] [len]  # sums, CRCs, Adler, hashes over ranges
scripts/xor_tools.py ...                   # single-byte brute force, repeating-key, known-plaintext
scripts/find_hash.py STATE ROM             # MD5/SHA1/SHA256 binary+hex search (ROM identity)
scripts/nand_split.py RAW PAGE OOB OUT     # test a page/OOB geometry hypothesis
scripts/tree_manifest.py ROOT              # JSONL manifest: type, mode, uid, size, sha256, link
scripts/reader.py                          # importable bounded Reader (no CLI; use in your parser)
scripts/sample_matrix_fill.py MATRIX.CSV SAMPLES_DIR
```

Portability notes: examples assume GNU/Linux bash + coreutils + Python 3.8+.
On other platforms translate `stat --printf`, `dd bs=1 skip=`, `xxd` to local
equivalents (or work in WSL2 / a Linux VM). For multi-GB images prefer
`dd iflag=skip_bytes,count_bytes` or `scripts/carve.py` over `bs=1`, and stream
hashes instead of `read_bytes()`. Always check `binwalk --help`,
`unblob --help`, `dumpimage -h`, `dtc -h` first — major versions differ.

## Beginner traps (read before concluding anything)

1. High entropy ≠ encryption (also compression, media, dedup, short samples).
2. `binwalk` hit ≠ correct boundary — validate with a format-aware parser + length.
3. "Binary" ≠ proprietary — test SQLite, protobuf, MessagePack, CBOR, archives first.
4. A changing 4-byte field ≠ checksum — could be timestamp, counter, length, nonce.
5. Payload hash match ≠ valid signature — hash, structure, and trust are 3 claims.
6. Mountable carve ≠ correct carve — kernels tolerate boundary errors.
7. Loads-after-edit ≠ understood — apps repair/ignore/reset corrupt state.
8. `cmp -l` prints **1-based decimal offsets, octal bytes** — convert or use `diff_regions.py`.
9. `dd bs=1 skip=N` counts in blocks, is slow on GB images — use `iflag=skip_bytes`.
10. `Path.read_bytes()` on a 16 GB dump OOMs the box — stream or `mmap`.

Full catalogue with corrections: `references/fundamentals.md`,
`references/automation-reporting.md`.
