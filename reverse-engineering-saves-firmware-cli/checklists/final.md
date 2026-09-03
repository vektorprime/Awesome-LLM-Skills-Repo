# Checklist — Final Gate (every case)

```text
[ ] Authorization, provenance, versions, acquisition recorded
[ ] Original read-only + hashed; tool versions captured
[ ] Header/footer/strings/signatures/fill/entropy surveyed; survey note written first
[ ] Layers mapped, not just bytes named
[ ] Controlled matrix where possible; identical-state noise measured
[ ] Offsets/lengths/bases/endian/alignments explicit
[ ] Compression/serialization proven by parse, not appearance
[ ] Checksums/hashes/MACs/signatures distinguished with coverage stated
[ ] Every carve/extraction links parent offset/length + command + hash
[ ] Filesystems handled safely; special files reviewed
[ ] Parser bounds counts/lengths/offsets/decompression; unknowns preserved
[ ] Tests cover versions + malformed inputs; fuzz shows no crash/hang/OOM
[ ] Version diffs normalized at the right layer
[ ] Observed/Inferred/Unknown + confidence on all material claims
[ ] Peer reproduces from package without verbal help
```
