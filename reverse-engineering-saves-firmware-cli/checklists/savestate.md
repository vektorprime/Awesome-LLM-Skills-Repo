# Checklist — Savestate

```text
[ ] Emulator + core + versions, platform, ROM hash, region, slot, settings recorded
[ ] T00/T01 determinism baseline + T10/T11 frame deltas + T20 memory delta captured
[ ] T30 compression-off and T40 second-version states captured where possible
[ ] Outer header + version fields mapped
[ ] Whole-file vs per-block compression decided by carve-and-decompress test
[ ] Chunk directory recovered (entry fields, endian, base); full gapless walk
[ ] ROM identity located (or binding absence qualified: normalized/per-track/DB-key checked)
[ ] Screenshot distinguished (PNG/JPEG with true end vs raw framebuffer with proven dimensions)
[ ] RAM-like regions proven by controlled in-game deltas (size alone never enough)
[ ] Version comparison done (magic, chunks, sizes, algos, load/migration tested on several states)
[ ] No register-level claims without decisive evidence
[ ] Chunk spec + compatibility matrix published with confidence labels
```
