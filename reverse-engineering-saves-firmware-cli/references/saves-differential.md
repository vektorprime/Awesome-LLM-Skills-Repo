# Saved Games — Differential Analysis, Integrity, Safe Editing

Differential analysis with **controlled, one-variable** samples is the primary
method for opaque saves. Randomly collected saves validate; controlled samples
assign meaning.

## 1. Sample matrix (build before touching hex)

| Sample | Controlled change | Expected | Delay | Size | SHA-256 |
|---|---|---:|---:|---:|---|
| `S00` | baseline | — | — | | |
| `S01` | re-save, no change | — | 2 s | | |
| `S02` | re-save, no change | — | 60 s | | |
| `S10..S13` | currency | 1, 2, 255, 256 | | | |
| `S20..S21` | name | `A`, `ABCDEFG` | | | |
| `S30..S31` | one boolean | false, true | | | |

High-value integers: 0, 1, 2, 127, 128, 255, 256, 32767, 32768, 65535,
65536, 2³²−1, negatives. Strings: lengths 1/2/7/15/16/17/31/32/33/63/64/65 +
non-ASCII. Floats: `(1.25, −3.5, 100.0)`. One experiment = one question.

Record per sample: game/platform + version, DLC/mods, slot, profile, cloud
sync, locale, emulator/core version, clean-close?, exact action between
samples. Cloud sync, autosave, RNG seeds, background sim, playtime counters
all inject noise — that is why S01/S02 exist.

Track in CSV and fill hashes mechanically:

```csv
sample,parent,change,expected,app_version,size,sha256,notes
S00,,baseline,,1.2.3,,,
S01,S00,no intentional change,,1.2.3,,,
S10,S00,currency,1,1.2.3,,,
```

```bash
python3 scripts/sample_matrix_fill.py sample-matrix.csv samples/
```

## 2. Stability baseline (measure noise before mapping)

```bash
sha256sum S00.bin S01.bin S02.bin
stat --printf='%n %s\n' S00.bin S01.bin S02.bin
python3 scripts/diff_regions.py S00.bin S01.bin --merge-gap 4 --context 16
python3 scripts/diff_regions.py S01.bin S02.bin --merge-gap 4 --context 16
```

| Observation | Likely | Next test |
|---|---|---|
| Few header/footer bytes | timestamp, sequence, checksum | wall-clock correlation + integrity workup |
| One block differs | block compression, journal page, DB page | block boundaries + decompress |
| Most bytes differ, size stable | whole-payload compression, stream cipher, nondeterministic serialization | entropy + header check + repeated-save determinism |
| Size shifts slightly | variable-length field / compression | length-controlled values |
| Alternating regions | dual-slot/journal (see §6) | generation counters + selector |

If identical-state saves are highly nondeterministic, **stop offset-mapping
the payload** — you need decompression/decryption/normalization first.

⚠️ `cmp -l` trap: it prints **1-based decimal offsets and octal bytes**.
`1 101 102` means byte index 0 changed `0x41`→`0x42`. Prefer
`scripts/diff_regions.py` (0-based hex) unless you convert explicitly.

## 3. Byte/region/block diffs

Aligned diff with merged regions + context:

```bash
python3 scripts/diff_regions.py S10.bin S11.bin --merge-gap 4 --context 16
python3 scripts/block_hashes.py before.bin after.bin 4096
```

Shift-aware: an inserted byte makes positional diffs report "everything
changed". Confirm with `radiff2 before.bin after.bin` or block hashes to
localize the insertion, then align the tails before concluding. For huge
files, block hashes first (reveals compression chunks, RAM pages, DB pages,
erase blocks, redundant copies), byte diffs second on the hot region only.

## 4. Numeric field recovery

```bash
python3 scripts/find_int.py S10.bin 255
python3 scripts/find_int.py S10.bin 256
python3 scripts/find_int.py S11.bin 128   # includes LEB128 candidates
```

A match is a candidate. Promote only when N values (especially width-edge
values) change exactly the predicted bytes and nothing else (modulo
timestamp/checksum). Document width + endian + signedness + sentinel behavior.

## 5. Integrity: checksums, hashes, MACs, signatures

A field moving after **any** edit could be checksum, counter, timestamp, or
unrelated state. Width hints only:

```text
2 B: sum16, CRC-16, Fletcher-16, count, flags
4 B: CRC-32, Adler-32, length, sequence, unix time
16 B: MD5 / truncated hash / IV / UUID / GCM tag-part
20 B: SHA-1   32 B: SHA-256 / key / nonce+tag
larger structured trailer: signature block / certs / manifest
```

Systematic workup (never guess-one-and-pray):

```bash
python3 scripts/checksum_candidates.py candidate.bin 0x0c 4
# sums/CRC/Adler/hashes over: whole, header-ex-PT, payload-only,
# zeroed-field, one-block, decompressed variants
```

Narrow the range by structure first (payload-only? header-minus-field?
zero-filled field? single record? decompressed-not-compressed?). Then demand
**prediction**: the hypothesis must match ≥3 independent samples AND predict
the post-edit value after a controlled change. CRC specifics that must be
stated: polynomial, init, refin/refout, xorout, range, endian of stored
value. Use `pycrc`-style catalogues for non-ISO variants; do not brute-force
blindly.

Keyed/signed indicators: unkeyed hypotheses all fail; long high-entropy
field; certs/keys in strings; manifest names an algorithm; edits never
validate. Then: document the boundary, label it "unverified signature/MAC
candidate", do NOT call it encryption, and escalate (see
`automation-reporting.md`). Signature ≠ encryption.

## 6. Journaling, redundancy, dual-slot saves

Clues: two similar large regions; alternating hot region per save; duplicate
headers with different counters; one valid + one stale checksum; tiny
selector near head/tail. Test with 4+ successive saves, mapping which region
moves. Understand selection/recovery (generation + selector + per-slot CRC)
before editing either copy. Corrupt-slot recovery test belongs in the spec.

## 7. Safe edit-and-validate loop

1. Copy baseline → candidate. One minimal edit. Recalculate **only confirmed**
   dependents. Rebuild affected layer; verify offsets/lengths.
2. Parse with your own parser. Diff unaffected regions (must be identical
   modulo declared dependents).
3. Load in isolated profile/disposable emulator. Record accept/reject/repair
   + any rewritten file. Verify intended value + unrelated state + re-save
   persistence.

```bash
cp baseline.bin candidate.bin
python3 - candidate.bin 0x1234 999 <<'PY'
from pathlib import Path
import struct, sys
p, off, val = Path(sys.argv[1]), int(sys.argv[2],0), int(sys.argv[3],0)
d = bytearray(p.read_bytes())
struct.pack_into("<I", d, off, val)
p.write_bytes(d)
PY
sha256sum baseline.bin candidate.bin
python3 scripts/diff_regions.py baseline.bin candidate.bin
```

Application acceptance is necessary but not sufficient — apps silently repair,
ignore, or reset fields. Preservation rule: parse confirmed fields, pass
through unknown ranges byte-exact, assert no unintended changes (see
`parser-spec.md`).
