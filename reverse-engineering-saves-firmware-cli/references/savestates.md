# Savestates — Chunks, RAM, Identity, Thumbnails, Versions

A save is application progress (inventory, quests, settings). A **savestate**
is machine state (CPU, RAM/VRAM, devices, timers, ROM binding, screenshot).
Savestates are version-sensitive and non-portable by design — aim for a
**chunk map + compatibility matrix**, not per-register truth.

Follow `checklists/savestate.md` alongside this file.

## 1. Acquisition plan

Record: emulator + exact version, core/plugins + versions, emulated platform,
ROM/disc hash, region/revision, state slot, rewind/run-ahead/cheats/mods,
paused?, compression setting.

Capture matrix:

| Sample | Change |
|---|---|
| `T00`, `T01` | same frame twice (determinism baseline) |
| `T10`, `T11` | +1 frame, +10 frames |
| `T20` | one benign in-game memory change (e.g. score+1 from a paused menu) |
| `T30` | same state, compression OFF (if supported) |
| `T40` | same state, second emulator/core version |

```bash
sha256sum game.rom T*.state | tee savestate-hashes.txt
```

Never compare across ROM revisions without recording it. Prefer paused/static
screens — a running frame changes timers, stack, VRAM, audio buffers, RNG.

## 2. First-pass survey

```bash
file -k T00.state
xxd -g 1 -l 1024 T00.state
strings -a -n 4 -t x T00.state | head -n 100
binwalk T00.state
7z l T00.state || true
```

Look for: emulator/core name + version, ROM title/CRC/MD5/SHA, timestamp,
chunk tags (`CPU RAM VRAM GPU APU CART SRAM THMB META`), comp/raw length
pairs, PNG/JPEG magic or raw-dimension hints, repeated block headers. Build
the chunk map before naming registers.

Savestate spec skeleton (`templates/spec-template.md` has the full form):

```markdown
## Outer header (offsets, version, flags)
## Chunk directory (entry fields, endian, base)
## Known chunks (tag, compression, raw size, meaning, confidence)
## ROM identity (algorithm, normalization, storage form)
## Integrity (per-file, per-chunk)
## Compatibility (old↔new behavior)
```

## 3. Whole-file vs per-block compression

- Whole-file: one small header + one stream; 1-byte logical change ⇒ global
  churn; decompress yields a second structured container.
- Per-block: repeated tag+len; localized churn; chunks decompress solo;
  entry headers carry comp+raw lengths.

```bash
OFFSET=0x100; LENGTH=0x2000
scripts/carve.py T00.state chunk-000.bin --offset $OFFSET --length $LENGTH
sha256sum chunk-000.bin; file -k chunk-000.bin
```

Log parent SHA + offset + length + command for every carve (layer ledger).

## 4. Memory-like regions

RAM-like traits: large fixed decompressed size ≈ platform region; many zeros;
localized change after small game action; visible strings/scores/tilemaps;
stable block position across states.

```bash
python3 scripts/diff_regions.py T00.ram T20.ram --merge-gap 16 --context 32
python3 scripts/block_hashes.py T00.ram T20.ram 4096
```

Size ≈ RAM size is a lead, not proof (could be VRAM, combined snapshot,
sparse, emulator buffer). Promote only with controlled-value changes at
stable offsets + repeated structure.

## 5. ROM identity and compatibility

Binding forms: filename/title, game code, CRC-32, MD5/SHA-1/SHA-256, disc
serial, DB ID, core content hash.

```bash
sha1sum game.rom; sha256sum game.rom
python3 scripts/find_hash.py T00.state game.rom
# searches binary + hex-lower + hex-upper for MD5/SHA1/SHA256
```

Absence of a whole-file digest does not clear you — emulators hash normalized
content (headerless ROM, per-track, DB key). Check strings for titles/serials
too.

## 6. Screenshots / thumbnails

```bash
binwalk T00.state | grep -Ei 'PNG|JPEG|bitmap|image' || true
scripts/carve.py T00.state thumb-and-tail.bin --offset 0x12340 --length 0x8000
file thumb-and-tail.bin
```

Use an image parser to find the true end (PNG `IEND`, JPEG `FFD9`) — never
assume image→EOF. Raw framebuffers: test
`len == w*h*4 (RGBA) / *3 (RGB) / *2 (RGB565)` against plausible console
resolutions from metadata; length alone never identifies the format.

## 7. Versioning and migration

```bash
sha256sum v1.state v2.state
python3 scripts/diff_regions.py v1.state v2.state --merge-gap 32
strings -a -n 4 -t x v1.state > v1.strings
strings -a -n 4 -t x v2.state > v2.strings
diff -u v1.strings v2.strings
```

Document: magic/version deltas, added/removed/reordered chunks, size +
algorithm changes, new IDs, load-old-in-new and resave-migration results.
One successful load ≠ compatibility — test several states and verify post-
migration integrity.
