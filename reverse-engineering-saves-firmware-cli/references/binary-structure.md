# Binary Structure — Offsets, Types, Strings, Tables, TLV, Flags

Goal of this phase: a map of **boundaries and relationships**, not names for
every byte. Record everything in `templates/field-map.md` with
Observed/Inferred/Unknown + confidence.

## 1. Work in offsets, lengths, invariants

Track across samples: constant bytes; `filesize = f(fields)` relationships;
offsets that land on visible structures; lengths ending at known boundaries;
counts matching repeated records; fields moving with exactly one controlled
variable; fields moving on every save regardless of state; alignment to
`0x10/0x100/0x200/0x1000`/sector/page/erase-block.

A demonstrated relationship beats a plausible value: a u32 equal to
`filesize − header` in 20 samples ≫ a number that "looks like" a timestamp.

```bash
python3 scripts/int_probe.py artifact.bin 0x08
python3 scripts/offset_probe.py artifact.bin 0 0x100
```

## 2. Endianness and integer width (never eyeball)

Same 4 bytes, many readings. Probe mechanically:

```bash
python3 scripts/int_probe.py "$F" 0x04
# prints u8/s8, u16/s16/u32/s32/u64/s64 le+be, float32/64 le+be, hex context
```

Rules:

- Endianness is usually consistent **within one structure**, but containers
  wrapping arch-specific data are often mixed-endian. Test each layer.
- Signedness: `FF FF FF FF` could be −1 / 4294967295 / sentinel / 4 flags.
  Decide with controlled values straddling 0 and type limits
  (127/128, 255/256, 32767/32768, 65535/65536, negatives).
- Width: boundary values are decisive — if 255→256 grows the encoding or
  flips a second byte, you just learned the width (or found a varint, §5).
- Never use native-endian unpacking in parsers; always explicit `<`/`>`.

Alignment and padding:

```bash
python3 - 0x12345 <<'PY'
import sys
x = int(sys.argv[1], 0)
for a in (2, 4, 8, 16, 0x200, 0x1000, 0x10000, 0x20000):
    up = (x + a - 1)//a*a
    print(f"align 0x{a:x}: next=0x{up:x} pad=0x{up-x:x}")
PY
```

Padding may be `00`, `FF`, repeated pattern, stale data, or undefined. Do not
include padding in checksum ranges without evidence.

## 3. Strings and text encodings

Survey ASCII + UTF-16LE/BE first, then go deeper when warranted:

```bash
strings -a -n 4 -t x "$F"
strings -a -n 4 -e l -t x "$F"
strings -a -n 4 -e b -t x "$F"
OFFSET=0x120; LENGTH=128
dd if="$F" bs=1 skip=$((OFFSET)) count=$((LENGTH)) status=none | xxd -g 1
# large files: dd if="$F" iflag=skip_bytes,count_bytes skip=$OFFSET count=$LENGTH status=none | xxd -g 1
```

Encoding zoo: UTF-8 (multibyte), UTF-16 ±BOM, UTF-32, fixed-width
null-padded, length-prefixed, Pascal (1-byte len), string tables by
offset/index, interned strings (stored once, referenced many times).

Fixed-width vs length-prefixed vs terminated — decisive test is name lengths
1, 2, 7, 15, 31 (+ 16/17, 32/33, 64/65 boundaries) and non-ASCII:

- Fixed total size + stable following offsets ⇒ fixed-width.
- Followers shift by exactly Δlen ⇒ variable-length.
- Preceding small int == len ⇒ length prefix (is it bytes? UTF-16 units?
  code points? terminator included? — test with `é` / CJK / emoji).
- Trailing `00` alone proves little (padding mimics terminators; embedded
  `00` in UTF-16 mimics ends). Need the length-series result.

## 4. Floats, fixed point, coordinates

Games + calibration data use IEEE-754 f32/f64, fixed point, scaled ints,
quantized/normalized values, degrees/radians/turns/integer-angle units.

```bash
python3 scripts/float_probe.py "$F" 0x200
```

Method: set distinctive controlled values per axis, e.g.
`(1.25, −3.5, 100.0)`, plus `0, 1, −1, 0.5, 1.5, 10.25`. Raw bytes
`00 00 80 3F` LE = 1.0f; `00 00 00 00 00 00 F0 3F` LE = 1.0. For fixed point,
plot raw-int Δ vs known-value Δ — ratios 256/1000/4096/65536 are common but
must be demonstrated, not assumed. Watch for f16 (`3C00` = 1.0) and bfloat16
in ML/ sensor firmware. Reject non-finite (NaN/Inf) readings unless the
domain allows them.

## 5. Varints (LEB128, zigzag, protobuf-style)

Width changes at 127→128 and 16383→16384 scream varint. Search, don't stare:

```bash
python3 scripts/find_int.py S11.bin 128     # also tries ULEB128 + zigzag
python3 scripts/find_int.py S11.bin --zigzag -5
```

Formulas: ULEB128 = 7-bit groups, low first, high bit = continue.
Zigzag: `zz = (n << 1) ^ (n >> 31)` (32-bit) maps signed→unsigned
(0→0, −1→1, 1→2, −2→3…). Protobuf tags are `(field<<3)|wiretype` varints —
try `protoc --decode_raw < chunk.bin` on a carved candidate; full-consumption
+ plausible field numbers = evidence, partial/exception = not confirmed.

## 6. Timestamps and counters

Candidates: Unix s/ms/µs/ns, Windows FILETIME (100-ns since 1601-01-01),
DOS datetime bitfields, Cocoa (+978307200), GPS, game ticks/frames, durations,
save sequence numbers.

```bash
python3 scripts/timestamp_probe.py "$F" 0x20
```

Decisive test: save twice with no state change, delay 2 s then 60 s. A field
tracking wall-clock Δ is a timestamp; a +1-per-save field is a sequence;
both can coexist. Decode must hold across samples AND predict the next Δ.
DOS datetime: `((date>>9)+1980, (date>>5)&15, date&31, (time>>11), (time>>5)&63,
(time&31)*2)` — verify by setting the clock if possible.

## 7. Offsets, lengths, counts, tables

Heuristics (leads, not proof — small ints land inside files by chance):

- Offsets: point inside file, increase monotonically, aligned, land on magic
  or record starts, equal `base + field`.
- Lengths: end at next offset, sum to payload, match decompressed size, include
  or exclude header consistently.
- Counts: match repeated records / directory entries / inventory deltas.

```bash
python3 scripts/offset_probe.py "$F" 0 0x100
```

Always test the base: file start? section start? header end? entry-table
start? decompressed-payload start? **flash virtual address** (no direct file
mapping)? Record the winning base in the spec. Validate every entry: no
region past EOF, no unintended overlap, consistent base, names match embedded
signatures, alignment matches container/flash rules.

## 8. Records and TLV/chunk framing

Common shapes:

```text
fixed:      [type][flags][id][value][pad]
len-prefix: [type][len][payload]
TLV:        [tag][len][value]
chunk:      [4-byte tag][len][payload][pad-to-4]
dir-entry:  [name_off][data_off][comp_len][raw_len][flags]
```

Scan then **walk**:

```bash
python3 scripts/tlv_scan.py "$F" --min-len 0 --max-len 0x100000
```

A hypothesis that parses 2 entries then fails at the 3rd is incomplete.
A valid framing walks the whole region gapless: `next == off + header + len
(+ pad)`. Both LE and BE lengths are tried; the one that chains cleanly wins.
Counts must equal walked records. Preserve unknown tags on rebuild.

## 9. Bitfields and flags

Toggle exactly one boolean at a time, both directions, multiple saves:

```bash
python3 scripts/diff_regions.py before.bin after.bin --merge-gap 0
# look for 0xXX -> 0xYY with xor = single bit (01,02,04,08,10,20,40,80)
```

One-bit XOR + stable neighbors ⇒ flag. Multi-bit change ⇒ enum, counter, or
adjacent fields. Map bit→option in the field map; re-test after reload
(some UIs invert or combine flags).

## 10. Worked mini-example (how to read a header)

```text
00000000: 53 41 56 45 03 00 40 00 28 00 00 00 9a 1f 43 7c  SAVE..@.(....C|
int_probe @0x04: u16le=3 u16be=768 ... (3 plausible, 768 not)
int_probe @0x06: u16le=0x40=64 -> points exactly at first record in xxd
int_probe @0x08: u32le=0x28=40, filesize=104 -> 64+40=104 ✓ (Observed, High)
0x0C: changes every identical-state save; CRC over 0x40..EOF fails; wall-clock test fails
      -> Unknown (NOT "checksum"), needs integrity workup
```

That table — offset, stable relationship, sample count — is the spec seed.
Promote Inferred→Observed only with a second independent confirmation.
