# Serialization & Database Recognition

Before calling anything "proprietary binary", rule out the standard library
of formats. Order matters: test the cheap whole-file hypotheses first, then
carve candidates at nonzero offsets (SQLite at `0x200` is a classic ambush).

## 1. Text-like formats

```bash
head -c 4096 "$F" | sed -n '1,80p'
jq . "$F" >/dev/null 2>&1 && echo JSON
xmllint --noout "$F" 2>/dev/null && echo XML
python3 - "$F" <<'PY' >/dev/null 2>&1 && echo plist
import plistlib, sys
with open(sys.argv[1], "rb") as f:
    plistlib.load(f)
PY
grep -a -m2 -o -E '<\?xml|{[[:space:]]*"|^[A-Za-z_]+=' "$F" || true
```

INI/CFG: look for `[section]` + `key=value`. YAML: `---` + `key:`.
Evidence bar: a decoder consuming the **entire** region with plausible values.
Partial output or exceptions = not confirmed.

## 2. SQLite (whole file or carved)

```bash
file "$F"
xxd -g 1 -l 16 "$F"   # expect "SQLite format 3\x00"
sqlite3 "$F" '.dbinfo' 2>/dev/null
sqlite3 "$F" '.tables' 2>/dev/null
sqlite3 "$F" '.schema' 2>/dev/null
```

Rules: never modify the only copy; collect `-wal`/`-shm` sidecars — without
them you read stale state. For diffs, dump canonically, never raw-page diff:

```bash
sqlite3 before.db .dump > before.sql
sqlite3 after.db  .dump > after.sql
diff -u before.sql after.sql
# or per-table: sqlite3 db "SELECT * FROM t ORDER BY rowid;"
```

Carved DB at offset O: `scripts/carve.py f.db carved.db --offset O --length L`
then inspect. Validate length by SQLite parse success to EOF, not by magic
alone.

## 3. Binary serialization clues

| Format | Tells | Confirm with |
|---|---|---|
| Protocol Buffers | varint tags, no global magic, small field numbers, LEN-delimited strings | `protoc --decode_raw < chunk` consumes all bytes plausibly |
| MessagePack | type markers `0x80–0x9F` (fixmap), `0xA0–0xBF` (fixstr), `0x91–0x9F` arrays | `msgpack` lib round-trip of carved region |
| CBOR | major-type high bits (`0x40`–`0x5B` text/bstr, `0xA0`+ maps) | `cbor2` decode, check trailing bytes == 0 |
| BSON | LE doc length at 0, null-terminated keys, typed values, trailing `0x00` | `bson` decode; length == region len |
| Java serialization | `AC ED 00 05` + class descriptors | `jdeserialize` / parser, not strings alone |
| .NET BinaryFormatter | `00 01 00 00 00 FF FF FF FF` + assembly-qualified type names | type-name strings + formatter lib |
| Unreal/Unity | engine version ints, object tables, `None`/property-name strings | engine-version correlation across builds |
| Base64-in-binary | `[A-Za-z0-9+/]{64,}={0,2}` runs decoding to structured bytes | decode run, re-survey output |
| ASN.1/DER | `30 82 …` SEQUENCEs, OIDs (`06 …`) | `openssl asn1parse -inform DER` |

Custom-alphabet base64, XOR+base64 stacks, and zlib-inside-protobuf are
common in saves — peel one layer at a time, hashing each child.

Protobuf worked probe:

```bash
scripts/carve.py save.bin cand.pb --offset 0x40 --length 0x200
protoc --decode_raw < cand.pb > cand.txt; echo "exit=$?"
wc -c cand.pb cand.txt
# full consumption + field numbers 1..N repeating = strong lead
```

## 4. Normalization before diffing (structured saves)

Byte diffs on JSON/XML/SQLite conflate meaning with whitespace, key order,
page allocation, timestamps. Normalize first:

```bash
jq -S . before.json > before.norm.json
jq -S . after.json  > after.norm.json
diff -u before.norm.json after.norm.json
xmllint --format --noblanks before.xml > before.norm.xml
# SQLite: canonical dump (above), or sorted CSV per table
```

Report logical changes ("inventory.count 3→4"), not page churn. Keep the raw
hashes too — normalization is a view, not a replacement.

## 5. Compression-in-serialization trap

A save that is "JSON but diffs everywhere" is usually
`header + zlib(JSON)` or `SQLite with compressed blobs`. Test: carve payload,
try `python3 -c "import zlib,sys;print(zlib.decompress(open('p.bin','rb').read())[:200])"`.
If it decompresses to `{"` or SQLite magic, you just found the real layer —
recurse (outer spec references inner spec, inner diffs happen post-decompress).
