# Fundamentals — Evidence, Layers, Scope (read first)

## 1. What this skill teaches

Given an opaque non-executable blob, answer with evidence:

- Is it a container, compressed stream, filesystem, database, serialized
  object, encrypted blob, or nested combination?
- Which bytes are metadata, offsets, lengths, counters, timestamps, records,
  padding, checksums, signatures, payloads?
- How does one game-state change alter a save? Which savestate bytes are RAM,
  device state, screenshot, metadata? How is a firmware package divided into
  manifest, boot, partitions, filesystems, config, integrity data?
- What transforms outer file → inner data, and can a modified artifact be
  rebuilt without corrupting offsets/lengths/compression/integrity?

Senior deliverables (all four):

1. **Layer map** — every confirmed transformation and embedded region.
2. **Format specification** — confirmed fields + explicit unknowns.
3. **Bounded parser** — tested on valid AND malformed samples.
4. **Reproduction package** — hashes, commands, tool versions, scripts, outputs.

## 2. Scope

In scope: custom saves and configs; emulator saves and full-machine
savestates; console/handheld save containers; vendor firmware downloads;
authorized hardware dumps; raw NAND/NOR/SPI/eMMC/partition images; U-Boot
legacy + FIT; device tree blobs; SquashFS/CramFS/JFFS2/UBIFS/ext/FAT/CPIO/tar;
proprietary headers, manifests, partition tables, checksums, signatures;
compression, serialization, authorized modification.

Out of scope: disassembly, parser recovery from application code, signature
bypass on deployed devices, exploits, unauthorized extraction, modifying
signed firmware for production. You may inventory executables inside firmware
(hash, compare) but stop before code analysis — hand off with exact hashes
(see `automation-reporting.md`).

## 3. Evidence standard

Every field and layer gets a status + confidence. Never report a guess as fact.

| Status | Meaning | Example language |
|---|---|---|
| **Observed** | Shown directly by bytes, parser, or experiment | "bytes 0x08–0x0B equal remaining file length in 14/14 samples" |
| **Inferred** | Best explanation, not yet independently proven | "0x0C–0x0F behave as CRC-32 over payload (12/12 match, predicted change after edit)" |
| **Unknown** | Untested / conflicting / insufficient | "16 bytes at 0x20 change every save; nonce vs UUID untested" |

| Confidence | Bar |
|---|---|
| **High** | Multiple independent samples, or parser + controlled modification |
| **Medium** | One direct observation or several consistent clues |
| **Low** | Plausible, awaiting a decisive test |

Field-map row format (also in `templates/field-map.md`):

```text
| Offset | End | Length | Name | Type | Status | Confidence | Evidence |
| 0x0000 | 0x0003 | 4 | magic | ASCII "SAVE" | Observed | High | constant in 12 samples |
| 0x0004 | 0x0005 | 2 | version | u16le | Inferred | Medium | values 3,4 track game version |
```

## 4. Layer model (think layers, not files)

Typical firmware nesting:

```text
vendor download wrapper
  -> archive/installer
    -> update manifest + signatures
      -> device container
        -> partition table / named images
          -> bootloader / kernel / DTB / rootfs / config
            -> filesystem files + databases
```

Raw flash dump instead:

```text
flash geometry + OOB
  -> bad-block markers / ECC / erase blocks
    -> boot + redundant partitions
      -> UBI volumes or raw filesystems
        -> files + config
```

Save nesting:

```text
header -> [obfuscation|encryption] -> compressed serialized state -> records
  + trailing checksum/MAC/tag
```

Savestate nesting:

```text
emulator header -> ROM identity -> compressed RAM pages
  -> CPU/device blocks -> screenshot -> per-block checksums
```

At every layer record: parent + parent-offset + stored length + raw length +
identification (magic? manifest entry? successful parse?) + encoding +
transform + integrity + rebuild obligations. A carved partition without its
source offset and source hash is incomplete evidence. Use
`templates/layer-ledger.md`.

First task is always the **layer map**, not per-byte meaning.

## 5. Case workspace and preservation

One directory per artifact family:

```text
case-001/
├── evidence/originals/ + hashes.sha256 + provenance.md
├── samples/baseline|experiments|versions/ + sample-matrix.csv
├── artifacts/survey|carved|extracted|normalized|diffs|reports/
├── scripts/  spec/  tests/  notes/  tool-versions.txt
```

Init (GNU/Linux; translate on other OSes):

```bash
set -Eeuo pipefail
umask 077
CASE=case-001
SOURCE=/path/to/authorized/artifact.bin
NAME=$(basename -- "$SOURCE")
mkdir -p "$CASE"/{evidence/originals,samples/{baseline,experiments,versions},artifacts/{survey,carved,extracted,normalized,diffs,reports},scripts,spec,tests,notes}
cp --reflink=auto --preserve=mode,timestamps -- "$SOURCE" "$CASE/evidence/originals/$NAME"
chmod 0444 "$CASE/evidence/originals/$NAME"
sha256sum "$CASE/evidence/originals/$NAME" | tee "$CASE/evidence/hashes.sha256"
stat --printf='path=%n\nsize=%s\nmtime=%y\nmode=%a\n' "$CASE/evidence/originals/$NAME" \
  > "$CASE/artifacts/survey/${NAME}.stat.txt"
```

Provenance (`evidence/provenance.md`): source, collection method, collector,
date/time, device/game/emulator + version, OS/HW revision, original filename,
any pre-receipt transfer/conversion, authorization reference. For hardware
dumps add: dump tool + exact command, flash chip + capacity, bus (SPI/NAND/
NOR/eMMC/JTAG/bootloader/vendor tool), OOB included?, read passes + hashes.

Tool versions (make failures visible, never fatal):

```bash
{
  date --iso-8601=seconds
  uname -a
  file --version | head -n 1
  python3 --version
  binwalk --help 2>&1 | head -n 5 || true
  unblob --help 2>&1 | head -n 5 || true
  7z i 2>/dev/null | head -n 3 || true
  unsquashfs -version 2>&1 | head -n 2 || true
  dumpimage -V 2>&1 || dumpimage -h 2>&1 | head -n 5 || true
  dtc -h 2>&1 | head -n 5 || true
} > "$CASE/tool-versions.txt"
```

Corrections to older guides: `unsquashfs` version flag is lowercase
`-version` (not `--version`); `dtc` historically uses `-v`/`-h` (not
`--version`); `dumpimage` version is `-V`, usage is `-h`; `7z i` shows
installed codecs. Always prefer the installed `--help`/`-h` over memory.

## 6. Safety and data handling

- Saved games: usernames, account IDs, chat, location, cloud IDs, auth
  material. Firmware: keys, certs, credentials, Wi-Fi, device IDs, customer
  data. Treat both as sensitive; restrict and redact.
- Disposable VM / restricted environment for recursive extraction; empty
  destination; resource limits (`ulimit -f`, `timeout`, disk quotas).
- Prefer userspace extraction (`unsquashfs`, `7z x`, `ubireader_*`,
  `jefferson`, debugfs) over kernel mounts. If you must mount: disposable VM,
  read-only (`-o ro,loop,noexec,nodev,nosuid`), `noauto`, never on production.
- Before opening an extracted tree: list symlinks/device nodes/FIFOs first
  (`scripts/tree_manifest.py` flags them), check for `../` and absolute
  symlink targets, cap decompression output (zip-bomb guard).
- Never execute extracted content. Never flash without authorization + tested
  recovery. Never bypass signatures to deploy.

## 7. Analytical failures (memorize)

| Fallacy | Correction |
|---|---|
| High entropy ⇒ encryption | Also compression, media, dedup, short-sample noise. Entropy is a clue; only successful decode/decompress or key-nonce-tag evidence proves the claim. |
| Binwalk hit ⇒ correct boundary | Scanner output is a lead. Validate with format-aware parse + declared lengths + successful extraction. |
| Binary ⇒ proprietary | Test SQLite/MessagePack/CBOR/protobuf/BSON/archives/filesystems first. |
| Changing u32 ⇒ checksum | Also timestamp, sequence, length, nonce, unrelated state. Checksums must *predict* post-edit values over a stated range. |
| Hash matches ⇒ signature valid | Hash-integrity, signature-structure, and trust are three separate claims. |
| Mounts ⇒ carve correct | Kernels tolerate truncation/padding. Prefer superblock/entry-table validation. |
| Loads after edit ⇒ understood | Apps repair/ignore/reset. Verify intended value + unrelated state + re-save persistence. |
| One sample parses ⇒ done | Must handle variants + reject truncation/overflow + cap decompression. |
| Version-diff file list ⇒ all meaningful | Separate semantic change from repacking noise (timestamps, allocation, compression level, signatures). |

## 8. Operating rhythm

```text
preserve -> classify layers -> one-variable experiments -> prove boundaries
  -> encode in parser -> test variants + malformed -> document unknowns
```

Daily note (`notes/experiment-log.md`): question, new observations,
confirmed/refuted hypotheses, artifacts + hashes, spec changes, unknowns,
next decisive test. Senior metric: uncertainty reduced per experiment, not
tools run. Cheapest decisive test wins (see `automation-reporting.md`).
