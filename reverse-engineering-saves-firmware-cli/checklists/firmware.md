# Checklist — Firmware

```text
[ ] Device model/HW rev/variant/version/source + package-vs-dump type recorded
[ ] Repeated hardware reads match (or divergence explained) before format work
[ ] Signatures + manifests preserved before any extraction
[ ] Layer ledger complete: every child has parent + offset + length + transform + command + hash
[ ] Outer package identified; delta-update base present (or stopped with reason)
[ ] Partitions/entries validated (bounds, overlaps, base, names, alignment)
[ ] U-Boot/FIT listed; default config + per-config refs + hash/sig scope recorded
[ ] DTB converted; partitions cross-checked against carved regions
[ ] Filesystems extracted in userspace; symlinks/dev-nodes/FIFOs reviewed first
[ ] Tree manifest (JSONL) captured with modes/owners/hashes
[ ] Manifest hashes verified separately from signature trust (three verdicts kept apart)
[ ] Boot map built from config text only (no execution, no behavior claims beyond config)
[ ] Secrets handled: restricted, contextualized, redacted (no key material in general reports)
[ ] Version diff done at 4 layers; semantic change separated from repacking noise
[ ] Stopped before code analysis; handoff has hashes + opaque ranges + ruled-out tests
```
