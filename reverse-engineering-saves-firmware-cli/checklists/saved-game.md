# Checklist — Saved Game

```text
[ ] Authorization, game/platform/version, slot, profile, locale, mods, cloud state recorded
[ ] Untouched baseline preserved read-only + hashed
[ ] Sample matrix built (S00/S01/S02 stability + one-variable experiments + boundary values)
[ ] Identical-state noise measured (diff S00/S01/S02 before mapping anything)
[ ] Layer classification done (text/db/archive/compression/encryption decided by test, not look)
[ ] Header/footer + entropy transitions mapped
[ ] Fixed vs variable size determined; journaling/dual-slot ruled in or out
[ ] Width/endian/signedness proven with boundary values (not eyeballed)
[ ] Strings counted as bytes/units/codepoints correctly (non-ASCII tested)
[ ] Offsets/lengths/counts validated (no past-EOF, consistent base, counts == walked records)
[ ] Integrity workup: range + algorithm + endian stated; 3+ samples + predicted post-edit value
[ ] Checksum vs hash vs MAC vs signature NOT conflated
[ ] Bounded parser rejects truncation/overflow, caps counts + decompression
[ ] Unknown bytes preserved on rebuild; no unintended changes asserted
[ ] One minimal edit validated in isolation (intended value + unrelated state + re-save)
[ ] Field map uses Observed/Inferred/Unknown + confidence; unknowns listed with next test
[ ] Peer can reproduce from package alone
```
