# CLI-First Reverse Engineering of Saved Games, Savestates, and Firmware Images

**Audience:** Security engineers who work primarily from a terminal  
**Primary targets:** saved-game files, emulator savestates, firmware update packages, raw firmware dumps, flash images, filesystem images, configuration partitions, and other opaque binary data  
**Explicitly out of scope:** reverse engineering executable code, decompilation, debugger-based program analysis, exploit development, and malware analysis  
**Goal:** produce a tested structural specification, parser, and evidence package that another engineer can reproduce

> The objective is not to “open the file.” The objective is to explain its layers, field boundaries, encodings, integrity mechanisms, and transformation steps with evidence.

---

## 1. What This Guide Teaches

This guide trains the engineer to answer questions such as:

- Is the artifact a container, compressed stream, filesystem, database, serialized object, encrypted blob, or a combination of layers?
- Which bytes are stable metadata, offsets, lengths, counters, timestamps, records, padding, checksums, signatures, or payloads?
- How does one game-state change alter a saved-game file?
- Which portions of a savestate represent RAM, device state, screenshots, metadata, or emulator-specific bookkeeping?
- How is a firmware package divided into manifest, boot components, partitions, filesystems, configuration, and integrity data?
- Which transformations are required to go from the outer file to the meaningful inner data?
- Can the format be parsed safely and deterministically across multiple samples and versions?
- Can a modified artifact be rebuilt without corrupting offsets, lengths, compression, or integrity fields?

A senior-level result contains four deliverables:

1. A **layer map** showing every confirmed transformation and embedded region.
2. A **format specification** describing confirmed fields and unresolved areas.
3. A **bounded parser** with tests against valid and malformed samples.
4. A **reproduction package** containing hashes, commands, tool versions, notes, scripts, and outputs.

---

## 2. Scope Boundaries

### In scope

- Custom save files and configuration files
- Emulator save files and full-machine savestates
- Console or handheld save containers
- Device firmware downloaded from a vendor
- Firmware read from authorized hardware
- Raw NAND, NOR, SPI flash, eMMC, or partition images
- U-Boot legacy images and FIT containers
- Device tree blobs
- SquashFS, CramFS, JFFS2, UBIFS, ext, FAT, CPIO, tar, and similar embedded content
- Proprietary headers, manifests, partition tables, checksums, signatures, and update metadata
- Compression, serialization, checksums, and authorized content modification

### Out of scope

- Disassembling binaries found inside firmware
- Reverse engineering application code to discover a parser
- Bypassing signature verification on deployed devices
- Exploit development or vulnerability weaponization
- Extracting content without authorization
- Modifying signed firmware for production deployment

Firmware often contains executable files. This workflow may identify, hash, inventory, and compare them, but it stops before code-level analysis.

---

## 3. Senior-Level Operating Standard

A senior engineer does not report guesses as facts. Every field and layer receives a status:

| Status | Meaning |
|---|---|
| **Observed** | Directly shown by bytes, metadata, a parser, or a controlled experiment |
| **Inferred** | Best explanation of multiple observations but not yet independently proven |
| **Unknown** | Insufficient evidence, conflicting evidence, or not yet tested |

Use confidence labels:

| Confidence | Standard |
|---|---|
| **High** | Confirmed by multiple independent samples or by a parser plus controlled modification |
| **Medium** | Strongly supported by one direct observation or several consistent clues |
| **Low** | Plausible hypothesis awaiting a decisive test |

Example field map:

| Offset | Length | Candidate | Status | Confidence | Evidence |
|---:|---:|---|---|---:|---|
| `0x0000` | 4 | magic `SAVE` | Observed | High | constant in 12 samples |
| `0x0004` | 2 | little-endian version | Inferred | Medium | values track game versions |
| `0x0008` | 4 | payload length | Observed | High | equals file size minus header |
| `0x000c` | 4 | CRC-32 | Inferred | Medium | matches three samples over payload only |
| `0x0010` | variable | zlib stream | Observed | High | valid decompression and round trip |

### Definition of done

Analysis is complete when:

- The original question has a defensible answer.
- Every extraction or transformation is reproducible.
- The parser rejects truncated and malformed input safely.
- Findings hold across multiple samples rather than one file.
- Unknowns and alternative explanations are documented.
- A second engineer can reproduce the conclusions without verbal guidance.

---

## 4. Safety, Authorization, and Data Handling

Saved games may contain usernames, account identifiers, chat text, location data, cloud IDs, or authentication material. Firmware may contain private keys, certificates, credentials, wireless configuration, device identifiers, and customer data. Treat both as potentially sensitive.

Minimum controls:

- Confirm authorization and data ownership.
- Work on copies; preserve originals read-only.
- Do not upload proprietary artifacts to public analysis services.
- Do not mount unknown filesystems on a production workstation.
- Prefer userspace extraction over kernel mounting.
- Perform recursive extraction in a disposable VM or restricted analysis environment.
- Inspect symlinks, device nodes, FIFOs, path traversal, and decompression expansion before trusting extracted trees.
- Never run scripts, installers, package hooks, or binaries extracted from firmware.
- Do not write experimental firmware to hardware unless recovery procedures and authorization are explicit.

### Why extraction itself deserves isolation

An archive or filesystem image can contain:

- Paths such as `../../outside-target`
- Absolute symlinks
- Huge sparse files or decompression bombs
- Device nodes and named pipes
- Malformed structures targeting parser bugs
- Filenames that confuse terminals or scripts

Use resource limits and an empty destination directory. Review the extraction report before opening content recursively.

---

## 5. Case Workspace and Evidence Preservation

Use one directory per artifact family or controlled experiment.

```text
case-001/
├── evidence/
│   ├── originals/
│   ├── hashes.sha256
│   └── provenance.md
├── samples/
│   ├── baseline/
│   ├── experiments/
│   └── versions/
├── artifacts/
│   ├── survey/
│   ├── carved/
│   ├── extracted/
│   ├── normalized/
│   ├── diffs/
│   └── reports/
├── scripts/
├── spec/
├── tests/
├── notes/
│   ├── field-map.md
│   ├── hypotheses.md
│   ├── experiment-log.md
│   └── decisions.md
└── tool-versions.txt
```

Initialize a case:

```bash
set -Eeuo pipefail
umask 077

CASE=case-001
SOURCE=/path/to/authorized/artifact.bin
NAME=$(basename -- "$SOURCE")

mkdir -p "$CASE"/{evidence/originals,samples/{baseline,experiments,versions},artifacts/{survey,carved,extracted,normalized,diffs,reports},scripts,spec,tests,notes}
cp --reflink=auto --preserve=mode,timestamps -- "$SOURCE" "$CASE/evidence/originals/$NAME"
chmod 0444 "$CASE/evidence/originals/$NAME"
sha256sum "$CASE/evidence/originals/$NAME" | tee -a "$CASE/evidence/hashes.sha256"
stat --printf='path=%n\nsize=%s\nmtime=%y\nmode=%a\n' "$CASE/evidence/originals/$NAME" \
  > "$CASE/artifacts/survey/${NAME}.stat.txt"
```

Record provenance in `evidence/provenance.md`:

```text
Source:
Collection method:
Collector:
Collection date and time:
Device/game/emulator and version:
Operating system or hardware revision:
Original filename:
Any transfer, decompression, or conversion before receipt:
Authorization reference:
```

Record tool versions:

```bash
{
  date --iso-8601=seconds
  uname -a
  file --version | head -n 1
  xxd -h 2>&1 | head -n 1 || true
  python3 --version
  binwalk --help 2>&1 | head -n 2 || true
  unblob --version 2>/dev/null || true
  7z i 2>/dev/null | head -n 3 || true
  unsquashfs -version 2>&1 | head -n 2 || true
  dumpimage -V 2>&1 || true
  dtc --version 2>&1 || true
  kaitai-struct-compiler --version 2>&1 || true
} > "$CASE/tool-versions.txt"
```

Hash every derived artifact and document its parent and transformation command. A carved partition without its original offset and source hash is incomplete evidence.

---

## 6. The Core Mental Model: Layers, Not Files

Most difficult artifacts are nested transformations:

```text
outer vendor package
  -> signed manifest/container
    -> compressed update payload
      -> partition table
        -> filesystem image
          -> configuration database
            -> serialized record
```

A saved game may be:

```text
header
  -> encrypted or obfuscated payload
    -> compressed serialized state
      -> records and values
  -> checksum or authentication tag
```

A savestate may be:

```text
emulator header
  -> metadata and ROM identity
  -> compressed RAM pages
  -> CPU/device-state blocks
  -> screenshot or thumbnail
  -> per-block checksums
```

At every layer, record:

| Property | Questions |
|---|---|
| Offset | Where does the layer begin in its parent? |
| Length | Is length explicit, inferred, aligned, or extends to EOF? |
| Identification | Magic, filename, manifest entry, or successful parser? |
| Encoding | Endianness, integer width, string encoding, bit order? |
| Transformation | Compression, encryption, XOR, escaping, sparse conversion? |
| Integrity | CRC, hash, signature, authentication tag? |
| Relationship | Child of which region? Repeated, optional, versioned? |
| Rebuild | What must be recalculated after modification? |

The first task is always to build a layer map, not to assign meaning to every byte.

---

## 7. First 15 Minutes: Non-Destructive Survey

Set variables:

```bash
CASE=case-001
F="$CASE/evidence/originals/artifact.bin"
OUT="$CASE/artifacts/survey"
mkdir -p "$OUT"
```

### 7.1 Identity, size, hashes, and first bytes

```bash
file -k -- "$F" | tee "$OUT/file.txt"
stat --printf='size=%s bytes\nblocks=%b\nmtime=%y\n' -- "$F" | tee "$OUT/stat.txt"
sha256sum -- "$F" | tee "$OUT/sha256.txt"
xxd -g 1 -l 512 "$F" | tee "$OUT/head-512.txt"
tail -c 512 -- "$F" | xxd -g 1 | tee "$OUT/tail-512.txt"
```

Why inspect both ends:

- Headers commonly contain magic, version, count, length, and offsets.
- Footers commonly contain checksums, signatures, central directories, manifests, or duplicate headers.
- A valid format may place its directory at EOF rather than the beginning.

### 7.2 Strings with offsets

```bash
strings -a -n 4 -t x -- "$F" | tee "$OUT/strings-ascii.txt"
strings -a -n 4 -e l -t x -- "$F" | tee "$OUT/strings-utf16le.txt"
strings -a -n 4 -e b -t x -- "$F" | tee "$OUT/strings-utf16be.txt"
```

Look for:

- Product, game, emulator, or board names
- Version strings
- Filenames and paths
- XML, JSON, INI, SQL, or property names
- Compression labels
- Partition names such as `boot`, `rootfs`, `kernel`, `config`, `nvram`, or `recovery`
- Usernames, timestamps, IDs, or save-slot names
- Certificate markers and PEM headers

Strings are anchors, not a complete interpretation. Their offsets are more useful than the text alone.

### 7.3 Embedded signatures

```bash
binwalk "$F" | tee "$OUT/binwalk.txt"
```

Use `binwalk --help` for the installed release before enabling extraction because major versions differ in extraction syntax and dependency handling.

An alternative recursive extractor is:

```bash
F_ABS=$(realpath "$F")
mkdir -p "$CASE/artifacts/extracted/unblob" "$CASE/artifacts/reports"
(
  cd "$CASE/artifacts/extracted/unblob"
  unblob --report ../../reports/unblob.json "$F_ABS"
)
```

Confirm the exact options with `unblob --help`; package versions may expose different destination flags. Run extraction only in an isolated workspace.

### 7.4 Generic archive probes

```bash
7z l "$F" | tee "$OUT/7z-list.txt" || true
bsdtar -tf "$F" > "$OUT/bsdtar-list.txt" 2>&1 || true
zipinfo -v "$F" > "$OUT/zipinfo.txt" 2>&1 || true
```

A failed probe is evidence only that the installed tool did not recognize the whole file at offset zero. It does not rule out an embedded archive.

### 7.5 Byte distribution and entropy map

High entropy can indicate compression, encryption, encoded media, or simply diverse data. Low entropy can indicate padding, sparse regions, tables, text, or uncompressed structures. Entropy alone never proves encryption.

Create `scripts/window_entropy.py`:

```python
#!/usr/bin/env python3
import argparse
import math
from collections import Counter
from pathlib import Path


def entropy(block: bytes) -> float:
    if not block:
        return 0.0
    counts = Counter(block)
    total = len(block)
    return -sum((n / total) * math.log2(n / total) for n in counts.values())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--window", type=lambda x: int(x, 0), default=4096)
    ap.add_argument("--step", type=lambda x: int(x, 0), default=None)
    args = ap.parse_args()

    data = Path(args.path).read_bytes()
    step = args.step or args.window
    print("offset,length,entropy,zero_fraction,ff_fraction")
    for off in range(0, len(data), step):
        block = data[off:off + args.window]
        if not block:
            break
        zeros = block.count(0) / len(block)
        ffs = block.count(0xFF) / len(block)
        print(f"0x{off:08x},{len(block)},{entropy(block):.4f},{zeros:.4f},{ffs:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Run it:

```bash
python3 "$CASE/scripts/window_entropy.py" "$F" --window 0x1000 \
  > "$OUT/entropy-4k.csv"
```

Interpret transitions rather than isolated values. A sudden change at an aligned offset may mark a header-to-payload boundary, partition boundary, compressed region, or erased flash.

### 7.6 Zero and `0xff` runs

Raw flash often contains large erased areas of `0xff`; sparse or initialized data may contain zeros.

```bash
python3 - "$F" <<'PY'
from pathlib import Path
import sys

data = Path(sys.argv[1]).read_bytes()
for value, name in ((0x00, "00"), (0xff, "ff")):
    start = None
    for i, b in enumerate(data + bytes([value ^ 0xff])):
        if b == value and start is None:
            start = i
        elif b != value and start is not None:
            length = i - start
            if length >= 256:
                print(f"{name} 0x{start:08x}-0x{i-1:08x} length=0x{length:x}")
            start = None
PY
```

Long runs may be padding, erase blocks, alignment, reserved space, sparse regions, or unused partition capacity. Do not automatically discard them.

### 7.7 Initial survey deliverable

The first-pass note should state:

```text
Artifact identity and provenance:
Size and SHA-256:
Recognized outer format:
Candidate embedded regions and offsets:
Visible strings and encodings:
Entropy or fill-pattern boundaries:
Likely next branch:
Unknowns:
Next three decisive tests:
```

Do not begin editing, carving, or recursive extraction until this note exists.

---

## 8. Classification Decision Tree

```text
[Unknown data artifact]
       |
       +--> Human-readable or database-like?
       |       |--> JSON/XML/INI/plist/SQLite/LevelDB/etc.
       |       `--> Normalize and compare logically, not only byte-for-byte
       |
       +--> Recognized archive/compression?
       |       `--> Extract one layer, hash child, repeat survey
       |
       +--> Recognized filesystem/partition image?
       |       `--> List read-only, extract safely, preserve metadata
       |
       +--> Vendor/update container?
       |       `--> Map header, manifest, entries, offsets, lengths, integrity
       |
       +--> Opaque saved game/savestate?
       |       `--> Build controlled sample matrix and differential experiments
       |
       `--> Still opaque?
               `--> Map constants, alignments, offsets, records, entropy, checksums
```

### Stop and reclassify when new evidence appears

Examples:

- A “random” payload starts with `78 9c`: test zlib before assuming encryption.
- A save file contains an SQLite header at offset `0x200`: carve and inspect the database.
- A firmware image contains a FIT header followed by named subimages: use container metadata before raw carving.
- A savestate changes almost everywhere after a one-point score change: test timestamps, random IVs, whole-file compression, and nondeterministic state before concluding the format is encrypted.

---

# Part I — Binary Structure Fundamentals

## 9. Work in Offsets, Lengths, and Invariants

The first goal is a map of boundaries and relationships.

Create `notes/field-map.md`:

```markdown
| Offset | End | Length | Name | Interpretation | Status | Confidence | Evidence |
|---:|---:|---:|---|---|---|---:|---|
| 0x0000 | 0x0003 | 4 | magic | ASCII `SAVE` | Observed | High | 12 samples |
| 0x0004 | 0x0005 | 2 | version | u16 little-endian | Inferred | Medium | values 3 and 4 |
| 0x0006 | 0x0007 | 2 | header_len | first payload offset | Observed | High | points to 0x40 |
```

Track invariants across samples:

- Constant bytes
- File-size relationships
- Offsets that point to visible structures
- Lengths that terminate at known boundaries
- Counts matching repeated records
- Fields that change only when one controlled variable changes
- Fields that change on every save regardless of game state
- Values aligned to `0x10`, `0x100`, `0x200`, `0x1000`, erase-block, or page boundaries

A relationship is stronger evidence than a visually plausible value. For example, a four-byte integer equal to the remaining payload length across 20 samples is much stronger than a number that merely “looks reasonable.”

---

## 10. Endianness and Integer Width

The same four bytes can represent different values:

```bash
python3 - "$F" 4 <<'PY'
import struct
import sys
from pathlib import Path

path, offset = sys.argv[1], int(sys.argv[2], 0)
b = Path(path).read_bytes()[offset:offset + 8]
print("bytes:", b.hex(" "))
for size, fmts in ((2, ("<H", ">H", "<h", ">h")),
                   (4, ("<I", ">I", "<i", ">i", "<f", ">f")),
                   (8, ("<Q", ">Q", "<q", ">q", "<d", ">d"))):
    if len(b) >= size:
        for fmt in fmts:
            try:
                print(fmt, struct.unpack(fmt, b[:size])[0])
            except struct.error:
                pass
PY
```

Test candidate values across multiple samples. Endianness is usually consistent within a structure, but mixed-endian formats exist, especially where a container wraps architecture-specific data.

### Signedness

A coordinate stored as `ff ff ff ff` may be `-1`, `4294967295`, a sentinel, or four flag bytes. Use controlled values around zero and boundary values to distinguish interpretations.

### Alignment and padding

Compilers and format designers often align fields or records. Common alignments include 2, 4, 8, 16, sector size, page size, or erase-block size.

```bash
python3 - 0x12345 <<'PY'
import sys
x = int(sys.argv[1], 0)
for a in (2, 4, 8, 16, 0x200, 0x1000, 0x10000, 0x20000):
    up = (x + a - 1) // a * a
    print(f"alignment 0x{a:x}: next=0x{up:x}, padding=0x{up-x:x}")
PY
```

Padding bytes may be zero, `0xff`, a repeated pattern, stale data, or undefined. Do not include padding in a checksum range without evidence.

---

## 11. Strings and Text Encodings

Search for common encodings:

```bash
strings -a -n 4 -t x "$F"
strings -a -n 4 -e l -t x "$F"
strings -a -n 4 -e b -t x "$F"
```

Also test:

- UTF-8 with multibyte characters
- UTF-16 with or without byte-order marks
- UTF-32
- Fixed-width null-padded strings
- Length-prefixed strings
- Pascal strings
- String tables referenced by offsets or indices
- Interned strings stored once and referenced many times

Inspect a candidate string region:

```bash
OFFSET=0x120
LENGTH=128
dd if="$F" bs=1 skip=$((OFFSET)) count=$((LENGTH)) status=none | xxd -g 1
```

### Distinguishing fixed-width and length-prefixed strings

Create samples with names of lengths 1, 2, 7, 15, and 31 characters.

- Fixed file size and stable following offsets suggest fixed-width storage.
- Following data shifting by the exact name-length delta suggests variable-length storage.
- A preceding small integer matching the character or byte count suggests a length prefix.
- A following null byte suggests termination, but embedded nulls or fixed padding can mislead.

Unicode length may count code points, UTF-16 code units, or encoded bytes. Test non-ASCII characters deliberately.

---

## 12. Floating Point, Fixed Point, and Coordinates

Games and device calibration data frequently use:

- IEEE-754 `float32` or `float64`
- Signed or unsigned fixed point
- Integer values with an implied scale
- Quantized coordinates
- Normalized values from 0 to 1
- Angles in degrees, radians, turns, or integer units

Probe candidate offsets:

```bash
python3 - "$F" 0x200 <<'PY'
import math
import struct
import sys
from pathlib import Path

data = Path(sys.argv[1]).read_bytes()
o = int(sys.argv[2], 0)
chunk = data[o:o+8]
for fmt in ("<f", ">f", "<d", ">d"):
    size = struct.calcsize(fmt)
    if len(chunk) >= size:
        v = struct.unpack(fmt, chunk[:size])[0]
        print(fmt, v, "finite=" + str(math.isfinite(v)))
PY
```

Use controlled values that are easy to distinguish:

- `0`, `1`, `-1`
- `0.5`, `1.5`, `10.25`
- Coordinates with different values on each axis, such as `(1.25, -3.5, 100.0)`

For fixed-point detection, compare raw integer deltas to known value deltas. A ratio of 256, 1000, 4096, or 65536 is common but must be demonstrated.

---

## 13. Timestamps and Monotonic Counters

Potential encodings include:

- Unix seconds or milliseconds
- Windows FILETIME
- DOS date/time
- Cocoa/macOS absolute time
- GPS time
- Game ticks or frame counts
- Duration in seconds, milliseconds, or engine ticks
- A monotonically increasing save sequence number

Find fields that change when saving twice without changing state. Compare the delta to wall-clock time.

```bash
python3 - "$F" 0x20 <<'PY'
from datetime import datetime, timezone, timedelta
from pathlib import Path
import struct, sys

b = Path(sys.argv[1]).read_bytes()
o = int(sys.argv[2], 0)
for endian in ("<", ">"):
    u32 = struct.unpack_from(endian + "I", b, o)[0]
    u64 = struct.unpack_from(endian + "Q", b, o)[0]
    print(endian, "u32", u32)
    try:
        print("  unix32", datetime.fromtimestamp(u32, timezone.utc))
    except (OverflowError, OSError, ValueError):
        pass
    for divisor, label in ((1, "seconds"), (1000, "milliseconds"), (1_000_000, "microseconds")):
        try:
            print(" ", label, datetime.fromtimestamp(u64 / divisor, timezone.utc))
        except (OverflowError, OSError, ValueError):
            pass
    try:
        ft = datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=u64 / 10)
        print("  filetime", ft)
    except OverflowError:
        pass
PY
```

A timestamp hypothesis is strong when the value decodes correctly across samples and changes by the expected amount under controlled save timing.

---

## 14. Offsets, Lengths, Counts, and Tables

Candidate offsets often:

- Point inside the file
- Increase monotonically
- Align to a common boundary
- Land on recognizable magic or record starts
- Equal another field plus a base offset

Candidate lengths often:

- End at the next offset
- Sum to the parent payload length
- Match decompressed output size
- Include or exclude header bytes consistently

Candidate counts often:

- Match the number of repeated records
- Control the number of directory entries
- Match an inventory or object count changed in an experiment

Create a quick offset probe:

```bash
python3 - "$F" 0 0x100 <<'PY'
from pathlib import Path
import struct, sys

path = Path(sys.argv[1])
start = int(sys.argv[2], 0)
length = int(sys.argv[3], 0)
data = path.read_bytes()
end = min(start + length, len(data))
for off in range(start, end - 3, 4):
    raw = data[off:off+4]
    le = struct.unpack("<I", raw)[0]
    be = struct.unpack(">I", raw)[0]
    tags = []
    if le < len(data): tags.append(f"le->0x{le:x}")
    if be < len(data): tags.append(f"be->0x{be:x}")
    if tags:
        print(f"field@0x{off:08x} {raw.hex()} {' '.join(tags)}")
PY
```

This creates leads, not proof. Small ordinary integers also fall inside the file by chance.

### Absolute versus relative offsets

An offset may be relative to:

- Start of file
- Start of current section
- End of header
- Start of an entry table
- Start of a decompressed payload
- A virtual flash address rather than a file location

Test each base explicitly and record the chosen base in the format specification.

---

## 15. Record Structures and Tag-Length-Value Encodings

Common record layouts:

```text
fixed-width record:
[type][flags][id][value][padding]

length-prefixed record:
[type][length][payload]

tag-length-value:
[tag][length][value]

chunked container:
[four-byte tag][length][payload][padding]

directory entry:
[name offset][data offset][compressed size][raw size][flags]
```

Look for repeated tags and lengths that land exactly on the next record.

```bash
python3 - "$F" <<'PY'
from pathlib import Path
import struct, sys

data = Path(sys.argv[1]).read_bytes()
for off in range(0, len(data) - 8):
    tag = data[off:off+4]
    if all(0x20 <= b < 0x7f for b in tag):
        le = struct.unpack_from("<I", data, off + 4)[0]
        be = struct.unpack_from(">I", data, off + 4)[0]
        if 0 <= le <= len(data) - off - 8:
            print(f"0x{off:08x} tag={tag.decode(errors='replace')!r} le_len=0x{le:x}")
        elif 0 <= be <= len(data) - off - 8:
            print(f"0x{off:08x} tag={tag.decode(errors='replace')!r} be_len=0x{be:x}")
PY
```

Validate record hypotheses by walking the entire region without gaps or overruns. A structure that parses two entries but fails at the third is probably incomplete.

---

## 16. Bitfields and Flags

A one-byte change can encode multiple independent booleans.

Use experiments that toggle exactly one setting at a time:

```bash
python3 - before.bin after.bin <<'PY'
from pathlib import Path
import sys

a = Path(sys.argv[1]).read_bytes()
b = Path(sys.argv[2]).read_bytes()
for i, (x, y) in enumerate(zip(a, b)):
    if x != y:
        print(f"0x{i:08x}: {x:02x}->{y:02x} xor={x ^ y:02x} bits={x ^ y:08b}")
PY
```

If toggling one option consistently XORs one bit while neighboring fields remain stable, a flag interpretation is likely. Test both directions and multiple saves.

---

## 17. Serialization and Database Recognition

Before treating a file as a proprietary binary format, test common structured encodings.

### Text-like formats

```bash
head -c 4096 "$F" | sed -n '1,80p'
jq . "$F" >/dev/null 2>&1 && echo JSON
xmllint --noout "$F" 2>/dev/null && echo XML
python3 - "$F" <<'PY' >/dev/null 2>&1 && echo plist
import plistlib, sys
with open(sys.argv[1], "rb") as f:
    plistlib.load(f)
PY
```

### SQLite

```bash
file "$F"
sqlite3 "$F" '.dbinfo' 2>/dev/null
sqlite3 "$F" '.tables' 2>/dev/null
sqlite3 "$F" '.schema' 2>/dev/null
```

Never modify the only copy. SQLite sidecar files such as `-wal` and `-shm` may be essential to reconstruct current state.

### Common binary serialization clues

- Protocol Buffers: small varints, repeated field tags, no global magic by default
- MessagePack: type markers and compact maps/arrays
- CBOR: major-type initial bytes and compact structured data
- BSON: document lengths, null-terminated keys, typed values
- Java serialization: stream magic and class descriptors
- .NET BinaryFormatter or proprietary serializers: type names and assembly strings
- Unreal or Unity formats: engine-specific headers, object tables, and versioning

Use a candidate decoder only after preserving the original. A decoder successfully consuming the entire region and producing plausible values is evidence; partial output or exceptions are not confirmation.

### Logical normalization

When a save is JSON, XML, SQLite, or another structured format, byte diffs may mostly reflect ordering, whitespace, page allocation, or timestamps. Normalize first:

```bash
jq -S . before.json > before.normalized.json
jq -S . after.json  > after.normalized.json
diff -u before.normalized.json after.normalized.json
```

For databases, export sorted query results or a canonical SQL dump rather than comparing raw pages alone.

---

# Part II — Saved Games and Configuration Files

## 18. Build a Controlled Sample Matrix

Differential analysis is the primary method for opaque save formats. Randomly collected saves are useful for validation, but controlled samples are required to assign semantics.

Create a matrix:

| Sample | Controlled change | Expected value | Save delay | File size | SHA-256 |
|---|---|---:|---:|---:|---|
| `S00` | baseline | — | — | | |
| `S01` | save again, no state change | — | 2 s | | |
| `S02` | save again, no state change | — | 60 s | | |
| `S10` | currency | 1 | | | |
| `S11` | currency | 2 | | | |
| `S12` | currency | 255 | | | |
| `S13` | currency | 256 | | | |
| `S20` | player name | `A` | | | |
| `S21` | player name | `ABCDEFG` | | | |
| `S30` | one boolean option | false | | | |
| `S31` | one boolean option | true | | | |

### High-value test values

Use values that reveal width and encoding:

- `0`, `1`, `2`
- `127`, `128`, `255`, `256`
- `32767`, `32768`, `65535`, `65536`
- Negative values where permitted
- Strings around likely boundaries: 15/16/17, 31/32/33, 63/64/65
- Non-ASCII text
- Floats with distinctive binary forms

Do not change multiple game variables in one experiment. One experiment should answer one question.

### Capture the environment

Record:

- Game and platform version
- DLC/mod status
- Save slot
- Character/profile
- Cloud synchronization state
- Locale and language
- Emulator/core version if applicable
- Whether the application was cleanly closed
- Exact action performed between samples

Cloud sync, autosave, random seeds, background simulation, timestamps, and playtime counters can introduce unrelated changes.

---

## 19. Establish Save Stability Before Mapping Fields

Create three saves without intentionally changing state:

```bash
sha256sum S00.bin S01.bin S02.bin
stat --printf='%n %s\n' S00.bin S01.bin S02.bin
cmp -l S00.bin S01.bin | head -n 40
cmp -l S01.bin S02.bin | head -n 40
```

Questions:

- Is the file deterministic for identical state?
- Does the file size remain constant?
- Do only a few header/footer fields change?
- Does a large contiguous region change?
- Does the entire file change?
- Are changes aligned to blocks?

Interpretation examples:

| Observation | Likely explanations | Next test |
|---|---|---|
| Few bytes change near header | timestamp, sequence, checksum | correlate with time and recalculate integrity candidates |
| One block changes | block compression, page-level state, journal page | compare block boundaries and decompression |
| Most bytes change but size stable | whole-payload compression, stream cipher, randomized serialization | compare entropy, headers, and repeated saves |
| File size changes slightly | variable-length fields or compression | use length-controlled experiments |
| File alternates between two regions | dual-slot or journaled saves | inspect generation counters and active-slot markers |

If repeated identical saves are highly nondeterministic, field mapping by direct byte offset may be the wrong first approach.

---

## 20. Byte-Level Differential Analysis

### 20.1 Simple aligned diff

```bash
cmp -l before.bin after.bin > cmp.txt
```

`cmp -l` reports one-based byte positions and octal values. Convert carefully, or use a script that reports zero-based hex offsets.

Create `scripts/diff_regions.py`:

```python
#!/usr/bin/env python3
import argparse
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("before")
    ap.add_argument("after")
    ap.add_argument("--merge-gap", type=int, default=0)
    ap.add_argument("--context", type=int, default=8)
    args = ap.parse_args()

    a = Path(args.before).read_bytes()
    b = Path(args.after).read_bytes()
    limit = max(len(a), len(b))
    changed = []
    for i in range(limit):
        av = a[i] if i < len(a) else None
        bv = b[i] if i < len(b) else None
        if av != bv:
            changed.append(i)

    if not changed:
        print("identical")
        return 0

    regions = []
    start = previous = changed[0]
    for off in changed[1:]:
        if off <= previous + args.merge_gap + 1:
            previous = off
        else:
            regions.append((start, previous))
            start = previous = off
    regions.append((start, previous))

    print(f"before_size={len(a)} after_size={len(b)} changed_bytes={len(changed)}")
    for start, end in regions:
        left = max(0, start - args.context)
        right = min(limit, end + args.context + 1)
        aa = a[left:min(right, len(a))]
        bb = b[left:min(right, len(b))]
        print(f"region 0x{start:08x}-0x{end:08x} length=0x{end-start+1:x}")
        print(f"  context 0x{left:08x}-0x{right-1:08x}")
        print(f"  before {aa.hex(' ')}")
        print(f"  after  {bb.hex(' ')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Run:

```bash
python3 scripts/diff_regions.py S10.bin S11.bin --merge-gap 4 --context 16
```

### 20.2 Shift-aware comparison

When one inserted byte shifts everything after it, a positional diff reports the entire remainder as changed. Use a binary-aware visual diff, `radiff2`, or sequence alignment on a bounded region.

```bash
radiff2 before.bin after.bin | tee radiff.txt
```

For very large files, first locate the approximate insertion region by comparing fixed-size block hashes.

### 20.3 Block hash comparison

```bash
python3 - before.bin after.bin 4096 <<'PY'
from pathlib import Path
import hashlib, sys

a = Path(sys.argv[1]).read_bytes()
b = Path(sys.argv[2]).read_bytes()
block = int(sys.argv[3], 0)
for i in range(0, max(len(a), len(b)), block):
    ah = hashlib.sha256(a[i:i+block]).hexdigest()[:16]
    bh = hashlib.sha256(b[i:i+block]).hexdigest()[:16]
    if ah != bh:
        print(f"0x{i:08x} {ah} {bh}")
PY
```

Block-level changes can reveal compression chunks, RAM pages, database pages, flash erase blocks, or redundant copies.

---

## 21. Numeric Field Recovery

For a controlled integer sequence, search for each representation.

```bash
python3 - S10.bin 255 <<'PY'
from pathlib import Path
import struct, sys

data = Path(sys.argv[1]).read_bytes()
value = int(sys.argv[2], 0)
formats = [
    ("u8", "B"), ("u16le", "<H"), ("u16be", ">H"),
    ("u32le", "<I"), ("u32be", ">I"),
    ("u64le", "<Q"), ("u64be", ">Q"),
]
for name, fmt in formats:
    try:
        needle = struct.pack(fmt, value)
    except struct.error:
        continue
    start = 0
    while True:
        off = data.find(needle, start)
        if off < 0:
            break
        print(name, f"0x{off:08x}", needle.hex())
        start = off + 1
PY
```

A direct match is only a candidate. Confirm it by testing several values and checking whether exactly the expected bytes change.

### Varints

Some serializers use variable-length integers. Values around 127/128 and 16383/16384 are especially informative because the encoded width changes.

A basic unsigned LEB128 encoder for searching:

```bash
python3 - S11.bin 128 <<'PY'
from pathlib import Path
import sys

value = int(sys.argv[2], 0)
out = bytearray()
v = value
while True:
    byte = v & 0x7f
    v >>= 7
    if v:
        out.append(byte | 0x80)
    else:
        out.append(byte)
        break
needle = bytes(out)
data = Path(sys.argv[1]).read_bytes()
print("encoded", needle.hex())
start = 0
while True:
    off = data.find(needle, start)
    if off < 0:
        break
    print(f"0x{off:08x}")
    start = off + 1
PY
```

Signed varints may use zig-zag encoding. Demonstrate the encoding with controlled negative values before assigning it.

---

## 22. Compression Detection and Recovery

Compression often causes a small logical change to alter many later bytes. Look for:

- Known stream magic
- High entropy in the payload but structured low-entropy header
- Explicit compressed and uncompressed lengths
- Repeated chunk headers
- Whole-file stability in size but broad byte changes
- Successful decompression to plausible structured data

Common candidates include zlib/deflate, gzip, xz/LZMA, bzip2, LZ4, Zstandard, LZO, and proprietary block compression.

### 22.1 Test known stream offsets

If a signature begins at `0x40`:

```bash
dd if="$F" of=payload.bin bs=1 skip=$((0x40)) status=none
file payload.bin
7z l payload.bin || true
```

For zlib:

```bash
python3 - payload.bin decompressed.bin <<'PY'
from pathlib import Path
import sys, zlib

src = Path(sys.argv[1]).read_bytes()
out = zlib.decompress(src)
Path(sys.argv[2]).write_bytes(out)
print(f"compressed={len(src)} decompressed={len(out)}")
PY
```

If decompression fails, do not immediately reject zlib. The region may include a header, multiple streams, raw deflate, a dictionary, trailing data, or a slightly wrong offset.

### 22.2 Find zlib-like candidates cautiously

Many byte pairs resemble zlib headers by chance. Validate by actual decompression and consumed length.

```bash
python3 - "$F" <<'PY'
from pathlib import Path
import sys, zlib

data = Path(sys.argv[1]).read_bytes()
for off in range(len(data) - 2):
    cmf, flg = data[off], data[off+1]
    if (cmf & 0x0f) == 8 and ((cmf << 8) + flg) % 31 == 0:
        d = zlib.decompressobj()
        try:
            out = d.decompress(data[off:])
            out += d.flush()
            consumed = len(data[off:]) - len(d.unused_data)
            if d.eof and consumed >= 8 and len(out) >= 16:
                print(f"offset=0x{off:x} consumed={consumed} output={len(out)}")
        except zlib.error:
            pass
PY
```

### 22.3 Round-trip testing

A successful decompression proves the algorithm and stream boundary more strongly than a magic-byte match. Recompression may not reproduce identical bytes because compression level, library version, dictionaries, block choices, or timestamps differ.

Therefore distinguish:

- **Semantic round trip:** decompress, parse, rebuild, and the application accepts the result.
- **Byte-identical round trip:** rebuilt bytes exactly match the original.

Byte-identical output is ideal but not always required.

---

## 23. Checksums, Hashes, MACs, and Signatures

A field changing after any content edit may be:

- Additive checksum
- Fletcher checksum
- Adler-32
- CRC with a particular polynomial, initialization, reflection, and final XOR
- Cryptographic hash
- HMAC or another keyed MAC
- Digital signature
- Encryption authentication tag
- Length, timestamp, sequence, or unrelated metadata

### 23.1 Start with field placement and width

Heuristics:

- 2 bytes: simple sum, CRC-16, Fletcher-16, count, flags
- 4 bytes: CRC-32, Adler-32, length, sequence, timestamp
- 16 bytes: MD5, truncated hash, IV, UUID, MAC/tag
- 20 bytes: SHA-1
- 32 bytes: SHA-256, key, nonce plus tag, or arbitrary data
- Larger structured trailer: signature block, certificate, manifest

Width is only a clue.

### 23.2 Candidate checksum calculations

```bash
python3 - "$F" <<'PY'
from pathlib import Path
import hashlib, sys, zlib

data = Path(sys.argv[1]).read_bytes()
print("sum8", f"{sum(data) & 0xff:02x}")
print("sum16", f"{sum(data) & 0xffff:04x}")
print("sum32", f"{sum(data) & 0xffffffff:08x}")
print("crc32", f"{zlib.crc32(data) & 0xffffffff:08x}")
print("adler32", f"{zlib.adler32(data) & 0xffffffff:08x}")
print("md5", hashlib.md5(data).hexdigest())
print("sha1", hashlib.sha1(data).hexdigest())
print("sha256", hashlib.sha256(data).hexdigest())
PY
```

Do not brute-force every possible range initially. Narrow the likely range using structure:

- Payload only
- Header excluding checksum field
- Entire file with checksum field zeroed
- One record or block
- Decompressed rather than compressed data
- Concatenation of selected fields

### 23.3 Zeroing the checksum field

```bash
python3 - "$F" 0x0c 4 <<'PY'
from pathlib import Path
import sys, zlib

path, off, size = sys.argv[1], int(sys.argv[2], 0), int(sys.argv[3], 0)
data = bytearray(Path(path).read_bytes())
stored = bytes(data[off:off+size])
data[off:off+size] = b"\x00" * size
print("stored", stored.hex())
print("crc32_zeroed", f"{zlib.crc32(data) & 0xffffffff:08x}")
print("crc32_payload_after_field", f"{zlib.crc32(data[off+size:]) & 0xffffffff:08x}")
PY
```

### 23.4 Differential validation

A checksum hypothesis is high confidence only when it matches multiple independently generated samples and changes as predicted after a controlled edit.

### 23.5 Recognizing keyed integrity or signatures

Suspect a keyed MAC or digital signature when:

- Common checksum/hash hypotheses fail.
- The field is long and high entropy.
- A certificate or public key is present.
- A manifest names a signing algorithm.
- Modified data cannot be made acceptable with unkeyed recalculation.

Document the boundary. Do not label a signature as “encryption.” A signature provides authenticity/integrity; encryption provides confidentiality.

---

## 24. Obfuscation Versus Encryption

Potential obfuscation indicators:

- Repeating-key XOR
- Byte addition/subtraction
- Nibble swaps or byte rotations
- Fixed substitution table
- Data interleaving
- Base64 or custom alphabets
- A stable transformation with no apparent random nonce

Potential encryption indicators:

- High-entropy payload with structured header
- Random nonce or IV changing on each save
- Fixed-size authentication tag
- Block alignment or stream-cipher behavior
- Same logical state producing unrelated ciphertext
- Key derivation metadata or algorithm identifiers

These are clues, not proof.

### 24.1 XOR comparison

```bash
python3 - before.bin after.bin <<'PY'
from pathlib import Path
import sys

a = Path(sys.argv[1]).read_bytes()
b = Path(sys.argv[2]).read_bytes()
x = bytes(i ^ j for i, j in zip(a, b))
print(x[:256].hex(" "))
PY
```

A repeating XOR pattern may expose a simple obfuscator, but compression can also create misleading patterns.

### 24.2 Known-plaintext testing

If a controlled player name is expected in the payload, XOR the suspected ciphertext bytes with the known plaintext and inspect whether the derived key repeats. Use several known values and offsets before concluding.

### 24.3 Decision point

When the format appears genuinely encrypted and the key is unavailable within the authorized data set, document:

- Confirmed plaintext header fields
- Ciphertext boundary
- Nonce/IV/tag candidates
- Determinism across identical saves
- Key sources tested
- Why further progress requires keys, format documentation, or producer-side instrumentation

Do not spend days guessing at high-entropy bytes without a testable key hypothesis.

---

## 25. Journaling, Redundancy, and Dual-Slot Saves

Some formats protect against interrupted writes with:

- Two complete save slots
- A current/previous generation pair
- Append-only records
- Write-ahead journals
- Per-page checksums
- Active-slot flags
- Sequence counters

Clues:

- Two similar large regions
- Alternating changes between regions on successive saves
- Duplicate headers with different counters
- One valid and one stale checksum
- A small selector field near the beginning or end

Test by saving repeatedly and observing which region changes. Do not edit both copies until you understand selection and recovery logic.

---

## 26. Safe Edit-and-Validate Loop

Never begin by editing the only known-good save.

Workflow:

1. Copy the artifact.
2. Make one minimal edit.
3. Recalculate only confirmed dependent fields.
4. Recompress or rebuild the affected layer.
5. Verify all offsets and lengths.
6. Parse the result with your own parser.
7. Compare unaffected regions.
8. Load only in an isolated test profile or disposable emulator environment.
9. Record acceptance, rejection, repair behavior, and any generated replacement file.

Example patch:

```bash
cp baseline.bin candidate.bin
python3 - candidate.bin 0x1234 999 <<'PY'
from pathlib import Path
import struct, sys

path, off, value = Path(sys.argv[1]), int(sys.argv[2], 0), int(sys.argv[3], 0)
data = bytearray(path.read_bytes())
struct.pack_into("<I", data, off, value)
path.write_bytes(data)
PY
sha256sum baseline.bin candidate.bin
python3 scripts/diff_regions.py baseline.bin candidate.bin
```

A successful application load is useful evidence but not complete validation. Verify the intended value, unrelated state, subsequent save behavior, and persistence after reload.

---

# Part III — Emulator Savestates

## 27. Save Files Are Not Savestates

A game-created save normally contains application-level progress: inventory, quests, settings, world state, and profile data.

An emulator savestate often captures machine-level state:

- CPU registers and execution state
- RAM, VRAM, and cartridge RAM
- Audio/video device state
- Timers, interrupts, DMA state, and controller state
- Emulator core and format version
- ROM or disc identity
- Screenshot or thumbnail
- Compression and per-block metadata

Savestates are usually more version-sensitive and less portable than in-game saves. The goal is therefore often to understand block layout, compatibility, and memory regions rather than every individual machine register.

---

## 28. Savestate Acquisition Plan

Capture:

- Emulator name and exact version
- Core/plugin name and exact version
- Platform/console being emulated
- ROM/disc hash
- Region and revision
- State slot
- Whether rewind, run-ahead, cheats, or enhancements are enabled
- Whether the emulator was paused at capture
- Whether state compression is enabled

Create these samples:

| Sample | Change |
|---|---|
| `T00` | same frame, baseline state |
| `T01` | same frame if deterministic capture is possible |
| `T10` | advance one frame |
| `T11` | advance ten frames |
| `T20` | change one byte of known in-game memory through a benign game action |
| `T30` | same state with compression disabled, when supported |
| `T40` | same state using a second emulator/core version |

Hash the game image and every state:

```bash
sha256sum game.rom T*.state | tee savestate-hashes.txt
```

Do not compare states from different ROM revisions without recording that difference.

---

## 29. Savestate First-Pass Survey

```bash
file -k T00.state
xxd -g 1 -l 1024 T00.state
strings -a -n 4 -t x T00.state | head -n 100
binwalk T00.state
7z l T00.state || true
```

Look for:

- Emulator/core name
- State format version
- ROM title, CRC, MD5, or SHA digest
- Timestamp
- Chunk tags such as CPU, RAM, VRAM, GPU, APU, CART, SRAM, THUMB
- Compressed and uncompressed lengths
- Screenshot formats such as PNG or raw pixel dimensions
- Repeated block headers

Build a chunk map before assigning register-level meaning.

---

## 30. Determine Whole-File Versus Per-Block Compression

Compare a normal state and a state saved with compression disabled when the emulator supports that setting.

Indicators of whole-file compression:

- One small header followed by a single compressed stream
- One logical change affects most bytes after the header
- Decompression yields a second structured container

Indicators of per-block compression:

- Repeated tags and length pairs
- Changes confined to one or a few chunks
- Each chunk decompresses independently
- Both compressed and raw lengths appear in entry headers

Carve candidate chunks with `dd` only after confirming offsets and lengths:

```bash
OFFSET=0x100
LENGTH=0x2000
dd if=T00.state of=chunk-000.bin bs=1 skip=$((OFFSET)) count=$((LENGTH)) status=none
sha256sum chunk-000.bin
file -k chunk-000.bin
```

Record the parent SHA-256, source offset, length, and carving command.

---

## 31. Identify Memory-Like Regions

RAM regions often have these properties:

- Large, fixed decompressed size matching a platform memory region
- Many zeros or repeated values
- Localized changes after a small in-game action
- Visible strings, scores, inventory values, tile maps, or framebuffer-like patterns
- Similar block position across savestates

### 31.1 Compare decompressed blocks

```bash
python3 scripts/diff_regions.py T00.ram T20.ram --merge-gap 16 --context 32
```

### 31.2 Page-level hashes

```bash
python3 - T00.ram T20.ram 4096 <<'PY'
from pathlib import Path
import hashlib, sys

a = Path(sys.argv[1]).read_bytes()
b = Path(sys.argv[2]).read_bytes()
page = int(sys.argv[3], 0)
for off in range(0, max(len(a), len(b)), page):
    x, y = a[off:off+page], b[off:off+page]
    if hashlib.sha256(x).digest() != hashlib.sha256(y).digest():
        count = sum(i != j for i, j in zip(x, y)) + abs(len(x) - len(y))
        print(f"page=0x{off//page:x} offset=0x{off:08x} changed={count}")
PY
```

A one-frame difference may legitimately change timers, stack, video memory, audio buffers, and random state. A carefully chosen static menu or paused screen reduces noise.

### 31.3 Memory size is not enough

A block matching the console's nominal RAM size is a strong lead but not proof. It could be VRAM, a combined memory snapshot, a sparse representation, or an emulator buffer. Confirm with controlled values and repeated structure.

---

## 32. ROM Identity and Compatibility Fields

Savestates may bind to a game image through:

- Filename or title
- Platform-specific game code
- CRC-32
- MD5, SHA-1, or SHA-256
- Disc serial
- Emulator database ID
- Core-specific content hash

Search for known hashes in raw and binary forms:

```bash
sha1sum game.rom
sha256sum game.rom
```

```bash
python3 - T00.state game.rom <<'PY'
from pathlib import Path
import hashlib, sys

state = Path(sys.argv[1]).read_bytes()
rom = Path(sys.argv[2]).read_bytes()
for name in ("md5", "sha1", "sha256"):
    digest = getattr(hashlib, name)(rom).digest()
    hexd = digest.hex().encode()
    for form, needle in (("binary", digest), ("hex-lower", hexd), ("hex-upper", hexd.upper())):
        off = state.find(needle)
        if off >= 0:
            print(name, form, f"0x{off:x}")
PY
```

Failure to find a whole-file digest does not rule out identity binding. The emulator may hash normalized content, headers removed from a ROM, individual tracks, or an internal database key.

---

## 33. Screenshot and Thumbnail Recovery

Search embedded signatures:

```bash
binwalk T00.state | grep -Ei 'PNG|JPEG|bitmap|image' || true
```

For a confirmed PNG offset:

```bash
OFFSET=0x12340
dd if=T00.state of=thumbnail-and-tail.bin bs=1 skip=$((OFFSET)) status=none
file thumbnail-and-tail.bin
```

Use a parser or image tool to determine the exact end rather than assuming the image extends to EOF.

Raw thumbnails may appear as fixed-size RGB/RGBA/RGB565 buffers. Candidate length relationships:

```text
width * height * 4   RGBA8888
width * height * 3   RGB888
width * height * 2   RGB565 or another 16-bit pixel format
```

Confirm dimensions from metadata or by testing plausible console resolutions. Do not infer image format from length alone.

---

## 34. State Versioning and Migration

Compare savestates created by multiple emulator versions:

```bash
sha256sum v1.state v2.state
stat --printf='%n %s\n' v1.state v2.state
python3 scripts/diff_regions.py v1.state v2.state --merge-gap 32
strings -a -n 4 -t x v1.state > v1.strings
strings -a -n 4 -t x v2.state > v2.strings
diff -u v1.strings v2.strings
```

Document:

- Outer magic changes
- Version-field changes
- Added, removed, or reordered chunks
- Chunk-size changes
- New compression algorithms
- New compatibility IDs
- Whether old states load in the new version
- Whether loading and resaving migrates the format

Do not claim backward compatibility from one successful load. Test multiple states and verify state integrity after migration.

---

## 35. Savestate Format Specification Template

```markdown
# <Emulator/Core> Savestate Format

## Applicability
- Emulator versions:
- Core versions:
- Platform:
- Compression settings:

## Outer header
| Offset | Size | Type | Name | Meaning | Evidence |

## Chunk directory
| Entry field | Type | Meaning |

## Known chunk types
| Tag/ID | Compression | Raw size | Interpretation | Confidence |

## ROM identity
- Algorithm:
- Normalization:
- Storage form:

## Integrity
- Per-file:
- Per-chunk:

## Compatibility behavior
- Older reader/newer state:
- Newer reader/older state:

## Unknowns
```

---

# Part IV — Firmware Images and Update Packages

## 36. Firmware Layer Model

Treat “firmware” as an artifact family, not one format.

Typical layers:

```text
vendor download wrapper
  -> archive or installer package
    -> update manifest and signatures
      -> device-specific container
        -> partition table or named images
          -> bootloader / kernel / device tree / root filesystem / config
            -> filesystem files and databases
```

A raw flash dump may instead contain:

```text
flash geometry and out-of-band data
  -> bad-block markers / ECC / erase blocks
    -> boot partitions and redundant copies
      -> UBI volumes or raw filesystems
        -> files and configuration
```

The analysis report must distinguish a vendor update package from a complete raw flash image. They are rarely interchangeable.

---

## 37. Firmware Provenance and Completeness

Record:

- Device vendor and exact model
- Hardware revision
- Region/carrier/operator variant
- Firmware version and release date
- Download source or acquisition method
- Whether the file is an update package, recovery image, full image, or raw chip dump
- Dump tool and command
- Flash chip model and capacity, when known
- Bus and acquisition method: SPI, NAND, NOR, eMMC, JTAG, bootloader command, vendor tool
- Whether out-of-band bytes were included
- Number of read passes and whether hashes matched

### Multiple-read verification for hardware acquisition

When authorized hardware is being dumped, acquire at least two reads and compare:

```bash
sha256sum read-01.bin read-02.bin
cmp -l read-01.bin read-02.bin | head
```

Differences may indicate unstable reads, live state changes, ECC/OOB handling, wear, or tool behavior. Do not begin format analysis until acquisition reliability is understood.

---

## 38. Firmware Survey and Layer Ledger

Run the general survey, then create `notes/layer-ledger.md`:

```markdown
| Layer ID | Parent | Parent offset | Stored length | Raw length | Identification | Transform | Integrity | Output SHA-256 |
|---|---|---:|---:|---:|---|---|---|---|
| L0 | — | 0x0 | 0x800000 | — | vendor update | none | signature trailer | ... |
| L1 | L0 | 0x400 | 0x7f0000 | 0x1000000 | compressed payload | xz | SHA-256 in manifest | ... |
| L2 | L1 | 0x0 | 0x1000000 | — | partition image | none | per-entry CRC | ... |
```

Every extracted child gets a unique ID and parent relationship.

### Never lose offsets

A directory named `_firmware.bin.extracted` is not an adequate map. Preserve exact offsets, lengths, extraction commands, and hashes.

---

## 39. Recognizing Common Firmware Containers

Start with:

```bash
file -k firmware.bin
binwalk firmware.bin
xxd -g 1 -l 1024 firmware.bin
strings -a -n 5 -t x firmware.bin | head -n 200
7z l firmware.bin || true
```

Common outer forms include:

- ZIP, tar, CPIO, 7z, CAB, or vendor archive
- U-Boot legacy `uImage`
- U-Boot FIT image
- Android sparse image or OTA package
- Raw partition concatenation
- UBI image
- Vendor-specific header plus entries
- Signed manifest plus payloads
- Delta update rather than complete images

A magic match identifies a candidate parser; it does not prove the entire file follows that format or that the embedded instance is authentic.

---

## 40. Recursive Extraction Without Losing Control

### 40.1 Binwalk as a scanner

```bash
binwalk firmware.bin | tee binwalk.txt
```

Use the installed release's help for extraction. Binwalk's major versions have different implementations and option sets.

### 40.2 Unblob with a report

A basic invocation is:

```bash
unblob --report unblob-report.json firmware.bin
```

It recursively processes recognized layers and emits an extraction tree. Review its report for offsets, handlers, and unrecognized gaps. Exact destination and resource-limit options depend on the installed release.

### 40.3 Manual extraction remains authoritative

Automated extraction can:

- Produce false-positive signatures
- Miss proprietary headers
- Choose the wrong boundary
- Fail on modified compression/filesystem variants
- Omit metadata needed for rebuilding

Use automation for leads, then reproduce important layers with explicit commands and confirmed offsets.

### 40.4 Hash the extraction tree

Create a metadata-preserving inventory:

```bash
ROOT="$CASE/artifacts/extracted/root"
(
  cd "$ROOT"
  find . -xdev -printf '%y\t%m\t%u\t%g\t%s\t%T@\t%p\t%l\n' | LC_ALL=C sort
) > "$CASE/artifacts/reports/tree-metadata.tsv"

(
  cd "$ROOT"
  find . -xdev -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum
) > "$CASE/artifacts/reports/tree-sha256.txt"
```

Filenames can contain tabs and newlines, so machine-readable inventories should use null delimiters or a structured format when exact fidelity matters.

---

## 41. Partition Tables and Concatenated Images

Test standard partitioning:

```bash
fdisk -l firmware.bin 2>&1 | tee fdisk.txt
sfdisk --dump firmware.bin 2>&1 | tee sfdisk.txt
parted -s firmware.bin unit B print 2>&1 | tee parted.txt
```

For forensic-style listing:

```bash
mmls firmware.bin 2>&1 | tee mmls.txt
```

### Carve a partition by byte offset and length

```bash
OFFSET=1048576
LENGTH=8388608
dd if=firmware.bin of=partition-01.bin bs=1 skip="$OFFSET" count="$LENGTH" status=progress
sha256sum partition-01.bin
```

For sector-based tables, calculate carefully:

```bash
START_SECTOR=2048
SECTORS=16384
SECTOR_SIZE=512
dd if=firmware.bin of=partition-01.bin bs="$SECTOR_SIZE" \
  skip="$START_SECTOR" count="$SECTORS" status=progress
```

Record both sector and byte values.

### Proprietary entry tables

Look for repeated entries containing:

```text
name or type
flash address
file offset
stored length
raw length
flags
checksum/hash
```

Validate all entries:

- No region extends beyond the parent file.
- Entries do not overlap unless the format intentionally aliases data.
- Lengths and offsets use a consistent base.
- Names correlate with embedded signatures.
- Alignment matches flash/page/erase geometry or container rules.

---

## 42. U-Boot Legacy Images and FIT

### 42.1 List image metadata

```bash
dumpimage -l firmware.bin | tee dumpimage-list.txt
```

This can report image type, architecture metadata, compression, payload size, load/entry fields, hashes, and FIT subimages when the input is recognized.

### 42.2 Extract a subimage

The exact `dumpimage` extraction command depends on legacy versus FIT structure. Inspect `dumpimage -h` and the listing, then extract a named or indexed child into a new file. Hash the result and add it to the layer ledger.

### 42.3 FIT as a device-tree-based container

FIT packages can describe multiple kernels, ramdisks, device trees, configurations, hashes, and signatures. Treat the configuration relationship as important evidence: not every embedded image is used by every configuration.

Questions:

- Which configuration is default?
- Which kernel, ramdisk, and FDT does each configuration reference?
- Which hash algorithms are present?
- Are signatures attached to images or configurations?
- Are external data positions used?
- Are there multiple hardware variants in one package?

Do not assume a successful payload extraction validates the package signature.

---

## 43. Device Tree Blobs

Device trees describe hardware topology and configuration. They can reveal:

- Compatible board and SoC strings
- Memory ranges
- Flash partitions
- Serial consoles
- GPIO assignments
- Network interfaces and MAC-address storage
- Enabled/disabled peripherals
- Boot arguments

Convert a confirmed DTB to source:

```bash
dtc -I dtb -O dts -o board.dts board.dtb
```

Compile back as a structural check:

```bash
dtc -I dts -O dtb -o board.roundtrip.dtb board.dts
```

A round trip may not be byte-identical because ordering, padding, and tool output can differ. Compare semantics rather than only hashes.

Search high-value properties:

```bash
grep -En 'compatible|model|partition@|reg =|bootargs|stdout-path|status =|mac-address|serial' board.dts
```

Partition `reg` values must be interpreted using parent address and size cell widths. Do not assume every pair is two 32-bit numbers.

---

## 44. SquashFS

SquashFS is common for read-only root filesystems.

Inspect without extracting:

```bash
unsquashfs -s rootfs.squashfs | tee squashfs-superblock.txt
unsquashfs -ll rootfs.squashfs > squashfs-list.txt
```

Extract to an empty directory:

```bash
mkdir -p extracted-squashfs
unsquashfs -d extracted-squashfs rootfs.squashfs
```

Important observations:

- Filesystem version
- Compression algorithm
- Block size
- Fragment and export settings
- Creation time
- UID/GID mapping
- Symlinks and device nodes

Do not run extracted init scripts or binaries. Review special files and symlinks before copying the tree elsewhere.

### Vendor variants

A valid SquashFS signature with extraction failure may indicate:

- Unsupported compression
- Modified magic or metadata
- Truncated image
- Incorrect carve boundary
- Vendor-modified SquashFS tools required

Preserve the error output and test the boundary before seeking a patched extractor.

---

## 45. UBI and UBIFS

Understand the layers:

```text
raw flash / MTD
  -> UBI container and volumes
    -> UBIFS filesystem inside a volume
```

UBIFS is not simply a conventional block filesystem. Avoid treating a raw UBI image like ext4.

Useful read-only analysis commands from UBI Reader commonly include:

```bash
ubireader_display_info image.ubi | tee ubi-info.txt
ubireader_extract_images image.ubi
ubireader_extract_files image.ubi
```

Use `--help` for installed syntax and options. Record guessed or supplied parameters such as physical erase-block size, logical erase-block size, minimum I/O size, and image offsets.

Questions:

- How many UBI images and volumes exist?
- Which volumes are static or dynamic?
- What are their names and IDs?
- Is a volume UBIFS, raw data, kernel, config, or recovery content?
- Is the dump aligned to the start of an erase block?
- Does the dump include OOB data?
- Are there bad blocks or missing erase blocks?

A failed extraction may be a geometry problem rather than corruption.

---

## 46. JFFS2, CramFS, ext, FAT, and CPIO

### JFFS2

Potential tools:

```bash
jffs2dump -c -v image.jffs2 > jffs2dump.txt 2>&1
jefferson image.jffs2 -d extracted-jffs2
```

Check endianness, erase size, clean markers, padding, and whether the input includes OOB bytes.

### CramFS

```bash
cramfsck -v image.cramfs
mkdir -p extracted-cramfs
cramfsck -x extracted-cramfs image.cramfs
```

### ext filesystems

Prefer read-only userspace inspection:

```bash
dumpe2fs -h image.ext 2>&1 | tee ext-superblock.txt
e2fsck -fn image.ext 2>&1 | tee ext-check.txt
debugfs -R 'ls -l /' image.ext 2>&1 | tee ext-root-list.txt
```

`-n` or read-only modes matter. Do not let a repair utility modify evidence.

### FAT

```bash
fsstat image.fat > fat-fsstat.txt
fls -r -p image.fat > fat-files.txt
```

Extract individual files with forensic tools or mtools while preserving the source image.

### CPIO

```bash
cpio -itv < archive.cpio > cpio-list.txt
mkdir -p extracted-cpio
(
  cd extracted-cpio
  cpio --no-absolute-filenames -idmv < ../archive.cpio
)
```

Review names first. `--no-absolute-filenames` reduces one class of extraction risk but does not replace isolation and path review.

---

## 47. Android Sparse Images

Android sparse images represent large logical block images compactly.

Typical conversion:

```bash
simg2img system.img system.raw.img
sha256sum system.img system.raw.img
file -k system.raw.img
```

After conversion, inspect the raw image as a filesystem or partition image. Record both sparse and expanded lengths.

Do not confuse sparse chunks with compression. The sparse format can describe raw, fill, and skipped regions.

---

## 48. Raw NAND, OOB, ECC, and Geometry

Raw NAND analysis can fail if geometry is wrong.

Relevant properties:

- Page data size
- OOB/spare size
- Pages per erase block
- Erase-block size
- Bad-block marker placement
- ECC algorithm and layout
- Whether the acquisition tool included or removed OOB
- Whether bad blocks were skipped, padded, or preserved

Common patterns include page records such as:

```text
[2048 bytes data][64 bytes OOB]
[4096 bytes data][128 or 256 bytes OOB]
```

Do not strip presumed OOB bytes until geometry is confirmed. Preserve both original and transformed images, and document the exact conversion.

### Test a candidate page/OOB split

```bash
python3 - raw-nand.bin 2048 64 data-only.bin <<'PY'
from pathlib import Path
import sys

src = Path(sys.argv[1]).read_bytes()
page = int(sys.argv[2], 0)
oob = int(sys.argv[3], 0)
out_path = Path(sys.argv[4])
stride = page + oob
if len(src) % stride:
    raise SystemExit(f"input length {len(src)} is not divisible by stride {stride}")
out = bytearray()
for off in range(0, len(src), stride):
    out += src[off:off+page]
out_path.write_bytes(out)
print(f"pages={len(src)//stride} output={len(out)}")
PY
```

This is a hypothesis test, not a generic cleaning step. Compare multiple plausible geometries and look for improved structural consistency.

---

## 49. Firmware Manifests, Integrity, and Signatures

Update packages often include:

- Product and hardware compatibility
- Minimum/maximum version
- Anti-rollback counter
- Partition names and target addresses
- Payload sizes and hashes
- Compression method
- Build identifiers
- Certificate chain or key identifier
- Digital signature

Extract or normalize human-readable manifests:

```bash
jq -S . manifest.json > manifest.normalized.json 2>/dev/null || true
xmllint --format manifest.xml > manifest.normalized.xml 2>/dev/null || true
```

Validate declared hashes against extracted payloads:

```bash
sha256sum payload-*.bin
```

Keep three separate statements:

1. **Hash matches payload:** content integrity relative to the manifest.
2. **Signature structure is present:** a signed container appears to exist.
3. **Signature is cryptographically valid and trusted:** requires correct canonicalization, algorithm, public key/certificate chain, and trust decision.

Do not collapse these into “firmware is signed.”

---

## 50. Boot-Chain Mapping Without Code Analysis

A data-focused boot map can still identify:

```text
boot ROM assumptions
  -> first-stage loader location
    -> bootloader container
      -> selected configuration
        -> kernel image
        -> device tree
        -> initramfs or root filesystem
        -> configuration/NVRAM partition
```

Evidence sources:

- Partition names and offsets
- FIT configurations
- Device-tree `chosen` and partition nodes
- Boot configuration files
- Filesystem paths such as `/boot`, `/etc/inittab`, init scripts, and service units
- Manifest target names
- Duplicate/recovery partitions

Inventory startup configuration as text and metadata, but do not execute it.

```bash
grep -RInE '(^|[[:space:]])(init|rcS|systemd|procd|telnetd|dropbear|sshd|httpd|mount|ubiattach)' extracted-root/etc 2>/dev/null
```

Interpretation of service behavior may require code analysis and is outside this guide. Report only what configuration directly establishes.

---

## 51. Configuration, Credentials, Keys, and Certificates

Authorized firmware review commonly searches for:

- Default usernames and passwords
- Password hashes
- API tokens
- Wi-Fi keys
- Private keys
- Certificates and trust stores
- Cloud endpoints
- Update URLs
- Debug flags
- Serial-console settings
- Device-unique material accidentally embedded in a generic image

Search carefully:

```bash
grep -RInaE 'password|passwd|secret|token|api[_-]?key|private[_-]?key|BEGIN .*PRIVATE KEY|debug|telnet|dropbear|update|https?://' extracted-root 2>/dev/null \
  > sensitive-string-leads.txt
```

This output contains leads, false positives, and potentially sensitive data. Restrict access and verify context before reporting.

List certificates:

```bash
find extracted-root -type f \( -iname '*.pem' -o -iname '*.crt' -o -iname '*.cer' \) -print
```

Inspect without altering:

```bash
openssl x509 -in certificate.pem -noout -subject -issuer -serial -dates -fingerprint -sha256
```

Do not expose private-key material in general reports. Record location, fingerprint, scope, and handling restrictions.

---

## 52. Firmware Version-to-Version Diffing

Raw byte diffing is often dominated by recompression, timestamps, filesystem allocation, signatures, and padding. Diff at multiple layers.

### Layer 1: outer package

```bash
sha256sum old.bin new.bin
stat --printf='%n %s\n' old.bin new.bin
binwalk old.bin > old.binwalk
binwalk new.bin > new.binwalk
diff -u old.binwalk new.binwalk
```

### Layer 2: container entries and partitions

Compare:

- Names
- Offsets
- Stored/raw lengths
- Compression
- Hashes
- Version and compatibility metadata

### Layer 3: normalized filesystem trees

```bash
(
  cd old-root
  find . -xdev -type f -print0 | sort -z | xargs -0 sha256sum
) > old-files.sha256
(
  cd new-root
  find . -xdev -type f -print0 | sort -z | xargs -0 sha256sum
) > new-files.sha256

diff -u old-files.sha256 new-files.sha256 > files.diff || true
```

This command's hash lines contain paths relative to different directories but can still be compared when the tree structure is identical. For robust automation, create a structured manifest with path, type, mode, owner, size, link target, and hash.

### Layer 4: content-aware normalization

- Sort JSON keys.
- Pretty-print XML.
- Export SQLite tables in stable order.
- Normalize archives by listing members and hashes.
- Separate expected generated files, logs, caches, and timestamps.

### Report categories

- Added/removed partitions
- Changed partition size or address
- Files added/removed/modified
- Configuration changes
- Certificate/key changes
- New compression or signing metadata
- Changes that could be repacking noise
- Unknown changes requiring a deeper specialist track

---

# Part V — From Hypothesis to Specification

## 53. Write the Specification While Investigating

Do not wait until the end. A live specification exposes contradictions early.

Recommended structure:

```markdown
# Format Name and Version

## Applicability
- Producer/device/game versions:
- Known variants:
- Required acquisition assumptions:

## Byte order and primitive types

## Layer diagram

## Outer header
| Offset | Size | Type | Name | Meaning | Constraints | Evidence |

## Directory or record table

## Payloads/chunks/partitions

## Compression and transformation rules

## Integrity and authenticity

## Rebuild procedure

## Validation corpus

## Unknown fields and competing hypotheses

## Change history
```

### Use precise type language

Prefer:

```text
u32le payload_length measured from offset 0x40 to EOF
UTF-16LE byte-length-prefixed string, no terminator
16-byte opaque value; likely IV, low confidence
CRC-32/ISO-HDLC over decompressed payload, checksum field excluded
```

Avoid:

```text
integer
name field
some hash
encrypted stuff
```

---

## 54. Build a Bounded Parser Early

A parser turns assumptions into executable tests. It should never trust lengths or counts from the file.

Create `scripts/reader.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import struct
from dataclasses import dataclass


class ParseError(ValueError):
    pass


@dataclass
class Reader:
    data: bytes
    offset: int = 0

    def remaining(self) -> int:
        return len(self.data) - self.offset

    def require(self, size: int, label: str = "data") -> None:
        if size < 0:
            raise ParseError(f"negative size for {label}: {size}")
        if self.offset + size > len(self.data):
            raise ParseError(
                f"truncated {label}: need {size} bytes at 0x{self.offset:x}, "
                f"only {self.remaining()} remain"
            )

    def take(self, size: int, label: str = "data") -> bytes:
        self.require(size, label)
        out = self.data[self.offset:self.offset + size]
        self.offset += size
        return out

    def unpack(self, fmt: str, label: str):
        size = struct.calcsize(fmt)
        self.require(size, label)
        values = struct.unpack_from(fmt, self.data, self.offset)
        self.offset += size
        return values[0] if len(values) == 1 else values

    def u8(self, label: str) -> int:
        return self.unpack("<B", label)

    def u16le(self, label: str) -> int:
        return self.unpack("<H", label)

    def u32le(self, label: str) -> int:
        return self.unpack("<I", label)

    def u64le(self, label: str) -> int:
        return self.unpack("<Q", label)

    def seek(self, offset: int, label: str = "offset") -> None:
        if not 0 <= offset <= len(self.data):
            raise ParseError(f"invalid {label}: 0x{offset:x}")
        self.offset = offset
```

Use explicit constraints:

```python
from dataclasses import dataclass
from pathlib import Path
from reader import ParseError, Reader


@dataclass
class Header:
    version: int
    header_size: int
    payload_size: int
    record_count: int


def parse_header(data: bytes) -> Header:
    r = Reader(data)
    magic = r.take(4, "magic")
    if magic != b"SAVE":
        raise ParseError(f"bad magic: {magic!r}")

    version = r.u16le("version")
    header_size = r.u16le("header_size")
    payload_size = r.u32le("payload_size")
    record_count = r.u32le("record_count")

    if version not in {1, 2, 3}:
        raise ParseError(f"unsupported version: {version}")
    if not 16 <= header_size <= len(data):
        raise ParseError(f"invalid header size: {header_size}")
    if payload_size > len(data) - header_size:
        raise ParseError("payload extends past EOF")
    if record_count > 1_000_000:
        raise ParseError("unreasonable record count")

    return Header(version, header_size, payload_size, record_count)
```

### Parser requirements

- Reject truncated input.
- Reject arithmetic overflow and out-of-range offsets.
- Cap counts and decompressed sizes.
- Preserve unknown bytes.
- Report exact error offsets.
- Avoid implicit native endianness.
- Separate parsing from interpretation.
- Permit strict and exploratory modes only when clearly labeled.

A parser that silently clips invalid lengths creates false confidence.

---

## 55. Preserve Unknown Data During Rebuilds

Early rebuilders should make surgical changes.

Safer pattern:

1. Parse confirmed fields.
2. Preserve unmodeled byte ranges exactly.
3. Replace only the target field or payload.
4. Recalculate confirmed dependent lengths/checksums.
5. Assert that all other bytes remain identical.

This is safer than serializing a partially understood structure from scratch.

Example assertion:

```python
changed = {0x120, 0x121, 0x122, 0x123, 0x0c, 0x0d, 0x0e, 0x0f}
for i, (before, after) in enumerate(zip(original, rebuilt)):
    if before != after and i not in changed:
        raise AssertionError(f"unexpected change at 0x{i:x}")
```

Adapt the expected set for variable-length or recompressed structures.

---

## 56. Kaitai Struct

Kaitai Struct is useful after the core structure is stable. A `.ksy` description can generate parsers in multiple languages.

Example:

```yaml
meta:
  id: example_save
  endian: le
seq:
  - id: magic
    contents: [0x53, 0x41, 0x56, 0x45]
  - id: version
    type: u2
  - id: header_size
    type: u2
  - id: payload_size
    type: u4
  - id: record_count
    type: u4
  - id: reserved
    size: header_size - 16
  - id: records
    type: record
    repeat: expr
    repeat-expr: record_count
  - id: trailing
    size-eos: true
types:
  record:
    seq:
      - id: tag
        type: u1
      - id: flags
        type: u1
      - id: length
        type: u2
      - id: value
        size: length
```

Compile:

```bash
kaitai-struct-compiler -t python -d generated spec/example_save.ksy
```

Use a handwritten parser first when:

- The format is still changing quickly.
- Integrity ranges need experimentation.
- Data is encrypted or compressed through custom steps.
- The format has irregular recovery behavior.
- You need precise preservation and rebuilding.

Use Kaitai when the structure is stable enough to formalize and share.

---

## 57. Tests and Validation Corpus

A format claim based on one file is fragile.

Minimum corpus:

- Multiple normal samples
- Minimum and maximum practical values
- Empty lists/records
- Long and non-ASCII strings
- Different game/device/firmware versions
- At least one intentionally truncated sample
- Invalid length/count/offset samples
- Corrupt checksum sample
- Unknown-version sample

Example tests:

```python
from pathlib import Path
import pytest

from format_parser import ParseError, parse


def test_known_samples():
    for path in Path("tests/fixtures/valid").glob("*.bin"):
        parsed = parse(path.read_bytes())
        assert parsed is not None


def test_truncation_rejected():
    data = Path("tests/fixtures/valid/basic.bin").read_bytes()
    for end in range(min(len(data), 128)):
        with pytest.raises(ParseError):
            parse(data[:end])


def test_declared_length_past_eof_rejected():
    data = bytearray(Path("tests/fixtures/valid/basic.bin").read_bytes())
    data[8:12] = (0xffffffff).to_bytes(4, "little")
    with pytest.raises(ParseError):
        parse(bytes(data))
```

Run:

```bash
python3 -m pytest -q
```

### Round-trip tests

For a byte-preserving parser/rebuilder:

```python
parsed = parse(original)
rebuilt = build(parsed)
assert rebuilt == original
```

For normalized or recompressed output, test semantic equality and explicit accepted differences.

---

## 58. Fuzz the Parser, Not the Target Device

Once a parser exists, fuzz it locally with mutation or a fuzzing framework. The immediate objective is parser robustness and specification gaps.

Simple bounded mutation test:

```python
import random
from pathlib import Path

from format_parser import ParseError, parse

seed = Path("tests/fixtures/valid/basic.bin").read_bytes()
rng = random.Random(0)

for case in range(10_000):
    data = bytearray(seed)
    for _ in range(rng.randint(1, 8)):
        if data:
            index = rng.randrange(len(data))
            data[index] ^= 1 << rng.randrange(8)
    try:
        parse(bytes(data))
    except ParseError:
        pass
```

The parser may accept some mutations; acceptance is not automatically a bug. Investigate crashes, excessive memory use, infinite loops, or violations of documented invariants.

Do not send random malformed firmware to physical hardware as a training exercise.

---

# Part VI — Automation

## 59. Reusable Survey Script

Create `scripts/survey.sh`:

```bash
#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

usage() {
  echo "usage: $0 FILE OUTPUT_DIR" >&2
  exit 2
}

[[ $# -eq 2 ]] || usage
file_path=$1
out=$2
[[ -f "$file_path" ]] || { echo "not a regular file: $file_path" >&2; exit 1; }
mkdir -p "$out"

sha256sum -- "$file_path" > "$out/sha256.txt"
stat --printf='path=%n\nsize=%s\nmtime=%y\nmode=%a\n' -- "$file_path" > "$out/stat.txt"
file -k -- "$file_path" > "$out/file.txt"
xxd -g 1 -l 4096 "$file_path" > "$out/head-4096.txt"
tail -c 4096 -- "$file_path" | xxd -g 1 > "$out/tail-4096.txt"
strings -a -n 4 -t x -- "$file_path" > "$out/strings-ascii.txt"
strings -a -n 4 -e l -t x -- "$file_path" > "$out/strings-utf16le.txt"
strings -a -n 4 -e b -t x -- "$file_path" > "$out/strings-utf16be.txt"

if command -v binwalk >/dev/null 2>&1; then
  binwalk "$file_path" > "$out/binwalk.txt" 2>&1 || true
fi
if command -v 7z >/dev/null 2>&1; then
  7z l "$file_path" > "$out/7z-list.txt" 2>&1 || true
fi
if command -v fdisk >/dev/null 2>&1; then
  fdisk -l "$file_path" > "$out/fdisk.txt" 2>&1 || true
fi

printf 'survey complete: %s\n' "$out"
```

Syntax-check it:

```bash
bash -n scripts/survey.sh
```

The script gathers evidence; it does not make conclusions.

---

## 60. Layer-Carving Helper

Create `scripts/carve.py`:

```python
#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path


def parse_int(value: str) -> int:
    return int(value, 0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("output")
    ap.add_argument("--offset", required=True, type=parse_int)
    ap.add_argument("--length", required=True, type=parse_int)
    ap.add_argument("--metadata")
    args = ap.parse_args()

    source = Path(args.source)
    output = Path(args.output)
    size = source.stat().st_size
    if args.offset < 0 or args.length < 0:
        raise SystemExit("offset and length must be non-negative")
    if args.offset + args.length > size:
        raise SystemExit("requested region extends past EOF")

    with source.open("rb") as src:
        src.seek(args.offset)
        data = src.read(args.length)
    if len(data) != args.length:
        raise SystemExit("short read")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    record = {
        "source": str(source),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "offset": args.offset,
        "length": args.length,
        "output": str(output),
        "output_sha256": hashlib.sha256(data).hexdigest(),
    }
    text = json.dumps(record, indent=2, sort_keys=True)
    print(text)
    if args.metadata:
        Path(args.metadata).write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

For very large source files, replace `source.read_bytes()` in the source-hash calculation with streaming. The simple version is suitable for lab-sized artifacts.

---

## 61. Streaming Tree Manifest

Create `scripts/tree_manifest.py`:

```python
#!/usr/bin/env python3
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
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    args = ap.parse_args()
    root = Path(args.root).resolve()

    for path in sorted(root.rglob("*"), key=lambda p: os.fsencode(str(p.relative_to(root)))):
        rel = str(path.relative_to(root))
        info = path.lstat()
        record = {
            "path": rel,
            "mode": stat.filemode(info.st_mode),
            "uid": info.st_uid,
            "gid": info.st_gid,
            "size": info.st_size,
            "mtime_ns": info.st_mtime_ns,
        }
        if stat.S_ISREG(info.st_mode):
            record["type"] = "file"
            record["sha256"] = hash_file(path)
        elif stat.S_ISDIR(info.st_mode):
            record["type"] = "directory"
        elif stat.S_ISLNK(info.st_mode):
            record["type"] = "symlink"
            record["target"] = os.readlink(path)
        elif stat.S_ISCHR(info.st_mode):
            record["type"] = "char-device"
            record["major"] = os.major(info.st_rdev)
            record["minor"] = os.minor(info.st_rdev)
        elif stat.S_ISBLK(info.st_mode):
            record["type"] = "block-device"
            record["major"] = os.major(info.st_rdev)
            record["minor"] = os.minor(info.st_rdev)
        elif stat.S_ISFIFO(info.st_mode):
            record["type"] = "fifo"
        elif stat.S_ISSOCK(info.st_mode):
            record["type"] = "socket"
        else:
            record["type"] = "other"
        print(json.dumps(record, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Use JSON Lines so paths and link targets are represented safely:

```bash
python3 scripts/tree_manifest.py extracted-root > root.manifest.jsonl
```

---

## 62. Sample Matrix Automation

Create a CSV recording experiments:

```csv
sample,parent,change,expected,application_version,size,sha256,notes
S00,,baseline,,1.2.3,,,
S01,S00,no intentional change,,1.2.3,,,
S10,S00,currency,1,1.2.3,,,
S11,S00,currency,2,1.2.3,,,
```

Populate size and hashes:

```bash
python3 - sample-matrix.csv samples <<'PY'
import csv
import hashlib
from pathlib import Path
import sys

csv_path = Path(sys.argv[1])
sample_dir = Path(sys.argv[2])
rows = list(csv.DictReader(csv_path.open(newline="", encoding="utf-8")))
for row in rows:
    path = sample_dir / row["sample"]
    if not path.exists():
        for suffix in (".bin", ".sav", ".state", ".img"):
            if (sample_dir / (row["sample"] + suffix)).exists():
                path = sample_dir / (row["sample"] + suffix)
                break
    if path.exists():
        data = path.read_bytes()
        row["size"] = str(len(data))
        row["sha256"] = hashlib.sha256(data).hexdigest()
with csv_path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
PY
```

For large firmware, use streaming hashes rather than `read_bytes()`.

---

## 63. Makefile for Reproducible Analysis

```make
SAMPLE ?= evidence/originals/artifact.bin
SURVEY := artifacts/survey

.PHONY: all survey entropy test clean

all: survey entropy test

survey:
	bash scripts/survey.sh "$(SAMPLE)" "$(SURVEY)"

entropy:
	python3 scripts/window_entropy.py "$(SAMPLE)" --window 0x1000 > "$(SURVEY)/entropy.csv"

test:
	python3 -m pytest -q

clean:
	rm -rf artifacts/survey/*
```

Do not make `clean` delete evidence, samples, specifications, or manually curated notes.

---

# Part VII — Investigation Playbooks

## 64. Saved-Game Playbook

### Stage 1: Establish context

```text
[ ] Record game, platform, version, slot, profile, locale, mods, and cloud state.
[ ] Preserve at least one untouched baseline.
[ ] Capture repeated saves with no intentional change.
[ ] Build a one-variable-at-a-time sample matrix.
```

### Stage 2: Classify layers

```text
[ ] Test text, archive, database, serialization, compression, and encryption hypotheses.
[ ] Map header/footer and entropy transitions.
[ ] Determine whether file size is fixed or variable.
[ ] Identify journaling or redundant copies.
```

### Stage 3: Recover fields

```text
[ ] Use boundary values to determine widths and varints.
[ ] Test endianness and signedness.
[ ] Recover strings, counts, offsets, and record framing.
[ ] Separate timestamp/sequence noise from target changes.
```

### Stage 4: Integrity and rebuild

```text
[ ] Determine checksum/hash/MAC/signature boundaries.
[ ] Build a bounded parser.
[ ] Preserve unknown bytes.
[ ] Perform one minimal edit and validate application behavior.
```

### Stage 5: Document

```text
[ ] Publish field map and layer diagram.
[ ] Include sample hashes and exact experiments.
[ ] Provide parser, tests, and known limitations.
```

---

## 65. Savestate Playbook

```text
[ ] Record emulator, core, game hash, platform, and settings.
[ ] Compare same-frame and one-frame-apart states.
[ ] Determine whole-file versus per-block compression.
[ ] Recover chunk directory and version fields.
[ ] Identify ROM identity, screenshot, RAM-like, and device-state blocks.
[ ] Compare version compatibility and migration behavior.
[ ] Avoid assigning register-level meaning without decisive evidence.
[ ] Publish a chunk-level specification and compatibility matrix.
```

---

## 66. Firmware Playbook

```text
[ ] Establish device model, hardware revision, firmware version, and acquisition type.
[ ] Verify repeated hardware reads when applicable.
[ ] Identify outer package and preserve signatures/manifests.
[ ] Build a layer ledger with offsets, lengths, transforms, and hashes.
[ ] Map partitions or named payload entries.
[ ] Inspect U-Boot/FIT/device-tree metadata when present.
[ ] Extract filesystems in userspace where possible.
[ ] Inventory metadata, symlinks, special files, certificates, and configuration.
[ ] Validate manifest hashes separately from signature trust.
[ ] Diff versions at container, partition, filesystem, and normalized-content layers.
[ ] Stop before executable code analysis and hand off with exact artifact hashes.
```

---

## 67. Choosing the Cheapest Decisive Test

Examples:

| Question | Weak approach | Better decisive test |
|---|---|---|
| Is this field currency? | stare at hex | create values 1, 2, 255, 256 and compare representations |
| Is payload compressed? | rely on entropy | carve candidate region and successfully decompress it |
| Is field a checksum? | match one sample | match several samples and predict result after controlled edit |
| Is offset absolute? | assume start of file | test file, section, and payload bases across all entries |
| Is region a filesystem? | trust signature scan | list it with a format-aware read-only tool and validate boundaries |
| Is firmware signed? | see a long trailer | identify signature structure, algorithm, key, canonical data, and verify |
| Is block RAM? | size resembles RAM | show controlled in-game value changes at stable block offsets |
| Is data encrypted? | high entropy | test compression and nondeterminism; identify nonce/tag/key evidence |

Senior performance is measured by how quickly uncertainty is reduced, not by how many tools are run.

---

# Part VIII — Training Program

## 68. Six-Week Intensive Track

This track assumes daily hands-on work with frequent review. “Senior ASAP” still requires demonstrated judgment; calendar time alone cannot establish senior capability.

### Week 1 — Binary literacy and evidence discipline

Topics:

- Hex, offsets, lengths, endianness, signedness
- Strings and encodings
- Alignment, padding, counts, offsets, tables
- Hashing, provenance, case structure
- Observed versus inferred versus unknown

Labs:

- Map a simple fixed-width save format.
- Recover integer, float, string, timestamp, and flags.
- Produce a field map and bounded parser.

Gate:

- No off-by-one offsets.
- All commands and hashes reproducible.
- Parser rejects truncation.
- No heuristic presented as fact.

### Week 2 — Differential save analysis

Topics:

- Sample-matrix design
- Stability/noise baselines
- Byte, region, and block diffs
- Variable-length records and varints
- Checksums and redundant saves

Labs:

- Recover a TLV save format.
- Identify a CRC field and exact coverage.
- Modify one value while preserving unknown data.

Gate:

- Hypotheses validated across at least five samples.
- Successful controlled edit and reload.
- Unrelated state verified unchanged.

### Week 3 — Compression, serialization, and savestates

Topics:

- Whole-file and per-block compression
- JSON/XML/SQLite normalization
- Savestate chunk maps
- RAM-like region identification
- Compatibility/version fields

Labs:

- Recover a compressed save container.
- Map an emulator state at chunk level.
- Identify a thumbnail and game-identity field.

Gate:

- Reproducible extraction and decompression.
- Clear distinction between semantic and byte-identical round trips.
- Compatibility claims tested, not assumed.

### Week 4 — Firmware containers and filesystems

Topics:

- Layer ledgers
- Partition tables and carving
- U-Boot legacy images, FIT, and device trees
- SquashFS, ext, FAT, CPIO, CramFS
- UBI/UBIFS and raw flash geometry

Labs:

- Map and extract a multi-layer firmware package.
- Produce a filesystem manifest.
- Correlate device-tree partitions with carved regions.

Gate:

- Every child artifact has a parent offset, length, command, and hash.
- Extraction does not rely solely on an automated tool.
- Mounting and execution safety are observed.

### Week 5 — Integrity, version diffing, and automation

Topics:

- Checksums, hashes, signatures, manifests
- Tree normalization
- Firmware version comparison
- Reusable scripts and tests
- Handling malformed and hostile inputs

Labs:

- Verify manifest hashes.
- Diff two firmware versions at four layers.
- Add parser tests and a structured extraction report.

Gate:

- Correct distinction among checksum, hash, MAC, and signature.
- Diff report separates semantic changes from repacking noise.
- Automation fails safely and reports errors.

### Week 6 — Senior capstone

Provide an unfamiliar artifact family containing:

- At least two versions
- Nested compression or filesystems
- An unknown header or entry table
- Integrity metadata
- Several controlled saved states or firmware variants
- One misleading signature or false lead

Required outputs:

- Scope and acquisition assessment
- Reproducible survey package
- Layer map and field specification
- Bounded parser with tests
- Version or state-difference analysis
- Risk and limitations summary
- 30-minute peer briefing
- Review of another engineer's analysis

Gate:

The engineer passes only if another analyst can reproduce the main findings from the package without verbal assistance.

---

## 69. Daily Operating Rhythm

```text
30 min  Review question, evidence, and previous unknowns
60 min  Cheapest decisive experiments
60 min  Parser/specification updates
30 min  Tests and artifact preservation
30 min  Written findings and confidence updates
30 min  Peer review or explanation to another engineer
```

A written daily note should include:

```text
Question addressed:
New observations:
Hypotheses confirmed/refuted:
Artifacts created and hashes:
Specification changes:
Current unknowns:
Next decisive test:
```

---

## 70. Lab Design

### Lab 1 — Fixed Save Header

Format:

```text
magic | version | header length | timestamp | player name[32] | currency | flags | CRC
```

Provide ten samples with controlled values. Require:

- Field map
- Parser
- Checksum coverage
- One successful modification
- Truncation tests

### Lab 2 — Variable Records

Format:

```text
header | record count | TLV records | string table | offset table | checksum
```

Include:

- Empty record list
- Duplicate tag
- Unknown tag
- UTF-8 name
- Corrupt length

Require preservation of unknown tags during rebuild.

### Lab 3 — Compressed Save

Format:

```text
header | compressed length | raw length | zlib payload | payload CRC | file CRC
```

Vary compression level across samples so recompression is not always byte-identical.

### Lab 4 — Dual-Slot Journaled Save

Format:

```text
selector | slot A | slot B
```

Each slot contains generation, payload, and CRC. Alternate active slots on successive saves. Require recovery of the newest valid slot after intentional corruption.

### Lab 5 — Emulator Savestate

Format:

```text
header | version | ROM SHA-1 | chunk directory
chunks: META, CPU0, RAM0, VRAM, THMB
```

Compress RAM and VRAM independently. Include a PNG thumbnail. Require chunk extraction, version comparison, and identification of a controlled memory change.

### Lab 6 — Firmware Container

Format:

```text
vendor header | manifest | entry table | kernel placeholder | DTB | SquashFS | config | signature placeholder
```

No executable analysis is required. Require:

- Layer ledger
- Entry-table parser
- Device-tree conversion
- Filesystem extraction and manifest
- Declared-hash verification

### Lab 7 — UBI/UBIFS Image

Provide known geometry plus one image with an offset prefix. Require the engineer to determine the true image start, list volumes, and extract files.

### Lab 8 — Version-Diff Capstone

Provide two firmware releases with:

- Repacked outer container
- One changed configuration file
- One certificate replacement
- Added recovery partition
- Filesystem creation-time changes

Require separation of meaningful changes from packaging noise.

---

## 71. Senior-Level Scoring Rubric

Score each area from 0 to 4.

| Area | 0 | 2 | 4 |
|---|---|---|---|
| Authorization and handling | ignores boundaries | follows checklist | anticipates sensitivity and extraction risks |
| Evidence preservation | overwrites or loses provenance | hashes originals | maintains complete parent/child transformation chain |
| Experiment design | changes many variables | mostly controlled | selects boundary values and decisive experiments |
| Structural reasoning | labels bytes by appearance | recovers basic fields | proves relationships across versions and layers |
| Compression/serialization | guesses by entropy | identifies common formats | maps nested transformations and round-trip limits |
| Integrity analysis | calls every field a hash | tests common checksums | distinguishes checksum/hash/MAC/signature and proves coverage |
| Firmware extraction | trusts one extractor | extracts common filesystems | independently validates offsets, geometry, and metadata |
| Parser engineering | parses happy path | bounds lengths/counts | preserves unknowns, tests malformed input, supports variants |
| Reproducibility | screenshots and prose | commands and outputs | one-command workflow with deterministic reports |
| Communication | confident but vague | clear technical report | precise confidence, alternatives, stop conditions, and handoff |
| Peer leadership | works alone | accepts review | improves another analyst's method and evidence quality |

Recommended gate:

- No score below 2
- Average at least 3
- Scores of 4 in evidence preservation, experiment design, parser engineering, and communication
- Successful capstone reproduction by a peer

---

# Part IX — Reporting

## 72. Analysis Report Template

```markdown
# Analysis Report: <case ID>

## 1. Question and scope
What was requested? What artifact types and versions were included? What was excluded?

## 2. Authorization and handling
Acquisition source, sensitivity, storage controls, and extraction environment.

## 3. Evidence identity
| Artifact | Size | SHA-256 | Provenance |

## 4. Executive conclusion
A concise answer to the original question, with confidence and material limitations.

## 5. Layer map
Outer package through final meaningful content.

## 6. Format specification
Confirmed headers, entries, chunks, partitions, records, encodings, and constraints.

## 7. Controlled experiments
| ID | Change | Observation | Conclusion | Confidence |

## 8. Integrity and authenticity
Checksums, hashes, MACs, signatures, coverage, and validation status.

## 9. Extraction and transformation ledger
| Child | Parent | Offset | Length | Transform | Command | SHA-256 |

## 10. Version or state comparison
Meaningful changes separated from nondeterministic or repacking changes.

## 11. Parser and tests
Repository path, supported versions, test corpus, malformed-input behavior.

## 12. Unknowns and alternative explanations
Unresolved fields, conflicts, and the next decisive test.

## 13. Reproduction
Exact commands in execution order and required tool versions.

## 14. Recommendations
Operational, engineering, documentation, or follow-up actions.
```

---

## 73. Finding Language

Good:

```text
Observed: bytes 0x08-0x0b are a little-endian value equal to the stored payload length in all 14 samples.

Inferred, medium confidence: bytes 0x0c-0x0f are CRC-32/ISO-HDLC over the compressed payload. The value matches 12 valid samples and changes as predicted after a controlled payload edit. Coverage of the final four trailer bytes remains untested.

Unknown: the 16-byte value at 0x20 changes on every save. It may be a random IV, UUID, or authentication-related value. No decisive test has been performed.
```

Weak:

```text
The header contains length, hash, and encryption information.
```

Always include offsets, byte order, coverage, sample count, and confidence where practical.

---

## 74. Peer Review Checklist

### Scope and evidence

```text
[ ] Authorization and target versions are explicit.
[ ] Original hashes and provenance are present.
[ ] Derived artifacts link to parent offsets, lengths, and commands.
[ ] Sensitive material is handled appropriately.
```

### Method

```text
[ ] Controlled experiments change one variable at a time.
[ ] Identical-state noise was measured.
[ ] Entropy is treated as a clue, not proof.
[ ] Automated extraction results were independently validated.
[ ] Mounts and extraction were read-only or userspace where practical.
```

### Specification

```text
[ ] Offsets, lengths, endianness, and bases are explicit.
[ ] Counts and lengths have demonstrated relationships.
[ ] Unknown fields remain labeled unknown.
[ ] Format variants and version applicability are documented.
```

### Parser

```text
[ ] Truncation and invalid lengths are rejected.
[ ] Counts and decompression output are bounded.
[ ] Unknown bytes/records are preserved where required.
[ ] Valid and malformed fixtures are tested.
```

### Conclusions

```text
[ ] Checksums, hashes, MACs, and signatures are not conflated.
[ ] Compatibility claims are tested across multiple samples.
[ ] Firmware diffs separate semantic change from repacking noise.
[ ] Limitations and next decisive tests are stated.
```

---

# Part X — Command Reference

## 75. General Survey

```bash
file -k artifact.bin
stat --printf='size=%s mtime=%y\n' artifact.bin
sha256sum artifact.bin
xxd -g 1 -l 512 artifact.bin
tail -c 512 artifact.bin | xxd -g 1
strings -a -n 4 -t x artifact.bin
strings -a -n 4 -e l -t x artifact.bin
binwalk artifact.bin
7z l artifact.bin
```

## 76. Carving and Comparison

```bash
dd if=parent.bin of=child.bin bs=1 skip=$((0xOFFSET)) count=$((0xLENGTH)) status=progress
cmp -l before.bin after.bin
radiff2 before.bin after.bin
sha256sum before.bin after.bin
xxd -g 1 -s 0xOFFSET -l 0xLENGTH artifact.bin
```

## 77. Structured Data

```bash
jq -S . input.json
xmllint --format input.xml
sqlite3 database.sqlite '.dbinfo'
sqlite3 database.sqlite '.tables'
sqlite3 database.sqlite '.schema'
```

## 78. Firmware Containers and Filesystems

```bash
fdisk -l image.bin
sfdisk --dump image.bin
mmls image.bin
dumpimage -l image.bin
dtc -I dtb -O dts -o board.dts board.dtb
unsquashfs -s rootfs.squashfs
unsquashfs -ll rootfs.squashfs
unsquashfs -d root rootfs.squashfs
ubireader_display_info image.ubi
ubireader_extract_images image.ubi
ubireader_extract_files image.ubi
dumpe2fs -h image.ext
e2fsck -fn image.ext
debugfs -R 'ls -l /' image.ext
fls -r -p image.fat
cramfsck -v image.cramfs
simg2img sparse.img raw.img
```

Check each tool's installed help. Exact options and supported variants differ by release.

---

## 79. Common Analytical Failures

### “High entropy means encryption”

Wrong. Compression, encoded images, deduplicated data, and already-compressed assets can also be high entropy.

### “Binwalk found it, so the boundary is correct”

Wrong. Signature scans produce leads and false positives. Validate with a format-aware parser and consistent length.

### “The file is binary, so it is proprietary”

Wrong. It may be SQLite, MessagePack, CBOR, Protocol Buffers, a filesystem, or a known container.

### “A four-byte field that changes is the checksum”

Wrong. It may be a timestamp, sequence, length, random value, or unrelated state.

### “The hash matches, so the firmware signature is valid”

Wrong. A matching payload hash does not authenticate the manifest or establish trust.

### “The extracted root filesystem is the entire firmware”

Wrong. Bootloader, kernel, device tree, configuration, calibration, recovery, and redundant partitions may be separate.

### “A successful mount proves the carve is correct”

Wrong. Kernel tolerance, recovery, or coincidental signatures can hide boundary errors. Prefer format-aware metadata validation.

### “If an edited save loads, the format is understood”

Wrong. The application may repair, ignore, reset, or partially accept corrupt state.

### “All changed files between firmware versions are meaningful”

Wrong. Repacking, timestamps, generated caches, filesystem allocation, and signatures can create noise.

### “A parser that handles the sample is finished”

Wrong. It must handle variants, reject malformed input, and make bounds explicit.

---

## 80. Escalation Criteria

Escalate or request additional evidence when:

- The artifact is encrypted and no authorized key source is available.
- Integrity uses a keyed MAC or digital signature and the task requires rebuilding.
- Raw NAND geometry, ECC, or OOB layout cannot be determined confidently.
- Extraction requires a vendor-specific filesystem modification.
- The package is a delta update and the required base version is missing.
- The artifact is incomplete or repeated reads do not match.
- A cloud service or hardware secure element participates in save/firmware protection.
- Understanding requires executable code analysis, which is outside this guide.
- A modification could brick hardware and no tested recovery path exists.
- Legal, contractual, privacy, or ownership boundaries are unclear.

A senior engineer knows when the next step is a new experiment, a missing sample, a key, a hardware specialist, a filesystem specialist, or a code-analysis handoff.

---

## 81. Handoff Package for Code Analysts or Hardware Specialists

When escalation is necessary, provide:

- Original and derived hashes
- Layer ledger
- Exact opaque region offset and length
- Known input/output samples
- Confirmed transformations before and after the region
- Candidate keys, nonces, tags, checksums, or algorithm metadata
- Relevant device/game/emulator versions
- What has already been tested and ruled out
- A precise question

Good handoff question:

```text
Determine how the authorized producer calculates the 16-byte field at file offset 0x20. We confirmed that bytes 0x40-EOF are zlib-compressed records and that the field changes on every save, including identical-state saves. The 12 bytes at 0x10 are stable per profile. We need to distinguish nonce, IV, MAC, or UUID behavior; no executable analysis has been performed.
```

Weak handoff question:

```text
Please reverse the save encryption.
```

---

## 82. Final Operating Checklist

```text
[ ] Authorization, provenance, versions, and acquisition method recorded
[ ] Original preserved read-only and hashed
[ ] Tool versions captured
[ ] Header, footer, strings, signatures, fill patterns, and entropy surveyed
[ ] Artifact classified as layers rather than one opaque file
[ ] Controlled sample matrix created where possible
[ ] Identical-state noise measured
[ ] Offsets, lengths, bases, endianness, and alignments documented
[ ] Compression/serialization tested by successful parsing, not appearance
[ ] Checksums/hashes/MACs/signatures distinguished
[ ] Every carved or extracted artifact linked to parent offset/length and hash
[ ] Filesystems inspected safely and special files/symlinks reviewed
[ ] Parser bounds all counts, lengths, offsets, and decompression
[ ] Unknown data preserved during rebuilding
[ ] Tests cover multiple valid versions and malformed inputs
[ ] Version diffs normalized at the appropriate layers
[ ] Conclusions use observed/inferred/unknown and confidence labels
[ ] Another engineer can reproduce the result from the package
```

---

## 83. Recommended Tool Categories

The workflow is tool-independent. Maintain at least one tested tool in each category:

| Category | Examples |
|---|---|
| Byte inspection | `xxd`, `od`, `hexdump` |
| Identity and strings | `file`, `strings` |
| Signature scanning | Binwalk |
| Recursive firmware extraction | unblob, Binwalk extraction features |
| Archive handling | `7z`, `bsdtar`, `cpio` |
| Binary diff | `cmp`, `radiff2`, custom Python |
| Partition/forensic listing | `fdisk`, `sfdisk`, `mmls`, `fls` |
| U-Boot images | `dumpimage`, `mkimage` |
| Device trees | `dtc`, `fdtdump`, libfdt tools |
| SquashFS | `unsquashfs`, `sqfscat` |
| UBI/UBIFS | UBI Reader, mtd-utils |
| JFFS2 | `jffs2dump`, Jefferson |
| ext/FAT | `debugfs`, `dumpe2fs`, Sleuth Kit, mtools |
| Android sparse | `simg2img` |
| Structured formats | `jq`, `xmllint`, `sqlite3` |
| Formal specification | Kaitai Struct |
| Parser/testing | Python, `pytest` |

Pin versions for long investigations and preserve error output. A tool failure is often useful evidence about boundaries, variants, or missing parameters.

---

## 84. Closing Principle

The fastest path to understanding saved states and firmware is disciplined reduction of uncertainty:

```text
preserve
  -> classify layers
    -> design one-variable experiments
      -> prove boundaries and relationships
        -> encode them in a parser
          -> test variants and malformed input
            -> document what remains unknown
```

Tool familiarity helps. Senior performance comes from selecting decisive tests, preserving a complete evidence chain, refusing to overstate conclusions, and leaving behind a specification that survives peer review.
