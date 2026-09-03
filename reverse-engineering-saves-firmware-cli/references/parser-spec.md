# Parser, Spec, Tests — From Hypothesis to Executable Truth

Write the spec **while** investigating — a live spec exposes contradictions
early. Start handwritten Python; graduate to Kaitai only when stable.

## 1. Spec skeleton (`templates/spec-template.md`)

Applicability (producer/versions/variants/acquisition) → byte order +
primitives → layer diagram → outer header table → directory/records →
payloads/chunks/partitions → transforms → integrity → rebuild procedure →
validation corpus → unknowns + rival hypotheses → change history.

Type language (precise vs vague):

```text
GOOD: u32le payload_length from 0x40 to EOF; CRC-32/ISO-HDLC over decompressed
      payload excluding the 4-byte field at 0x0C (matches 12/12, predicts edits)
BAD:  "integer", "name field", "some hash", "encrypted stuff"
```

## 2. Bounded parser first (`scripts/reader.py`)

`scripts/reader.py` is an importable `Reader` — bounds-checked, explicit
endian, exact error offsets. Pattern:

```python
from pathlib import Path
from scripts.reader import ParseError, Reader  # or copy into case scripts/

def parse_header(data: bytes):
    r = Reader(data)
    magic = r.take(4, "magic")
    if magic != b"SAVE":
        raise ParseError(f"bad magic: {magic!r} at 0x0")
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
    return (version, header_size, payload_size, record_count)
```

Parser law: reject truncation; reject overflow/out-of-range offsets; cap
counts AND decompressed sizes (zip-bomb guard, e.g. `raw_len <= 256 MiB` and
`ratio <= 100×`); preserve unknown bytes; no native endianness; parsing ≠
interpretation; strict vs exploratory modes labeled.

## 3. Safe rebuilds (preserve unknowns)

Surgical pattern: parse confirmed fields → pass through unmodeled ranges
byte-exact → replace only target → recalc confirmed dependents → assert
nothing else moved:

```python
changed = {0x120, 0x121, 0x122, 0x123, 0x0c, 0x0d, 0x0e, 0x0f}
for i, (a, b) in enumerate(zip(original, rebuilt)):
    if a != b and i not in changed:
        raise AssertionError(f"unexpected change at 0x{i:x}")
```

Adapt for variable-length/recompressed structures (compare semantic trees +
declared dependents, not raw bytes).

## 4. Kaitai Struct (after stability)

```yaml
meta: {id: example_save, endian: le}
seq:
  - {id: magic, contents: [0x53, 0x41, 0x56, 0x45]}
  - {id: version, type: u2}
  - {id: header_size, type: u2}
  - {id: payload_size, type: u4}
  - {id: record_count, type: u4}
  - {id: reserved, size: header_size - 16}
  - {id: records, type: record, repeat: expr, repeat-expr: record_count}
  - {id: trailing, size-eos: true}
types:
  record:
    seq:
      - {id: tag, type: u1}
      - {id: flags, type: u1}
      - {id: length, type: u2}
      - {id: value, size: length}
```

```bash
kaitai-struct-compiler -t python -d generated spec/example_save.ksy
```

Handwritten first when: format churning, integrity ranges experimental,
custom crypto/compression, irregular recovery, precise rebuild needed. Kaitai
when sharing a stable grammar.

## 5. Tests + corpus

Minimum corpus: several normal samples; min/max values; empty lists; long +
non-ASCII strings; each supported version; truncated; bad length/count/
offset; corrupt checksum; unknown version.

```bash
mkdir -p tests/fixtures/valid tests/fixtures/invalid
python3 -m pytest -q
```

Round trips: byte-preserving (`build(parse(x)) == x`) or semantic
(reparse + app-accepts + declared diffs). Fuzz the parser locally (mutation /
hypothesis / AFL-style), never the device:

```python
# 10k bounded bit-flips: must raise ParseError or return sane object —
# never crash, hang, or allocate unbounded memory
```

Do not send random malformed firmware to hardware as "testing".
