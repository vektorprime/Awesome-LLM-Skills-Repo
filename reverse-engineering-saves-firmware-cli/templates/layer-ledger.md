# Layer Ledger (every child links to its parent)

| Layer ID | Parent | Parent offset | Stored length | Raw length | Identification | Transform | Integrity | Output SHA-256 | Command |
|---|---|---:|---:|---:|---|---|---|---|
| L0 | — | 0x0 | 0x… | — | vendor update (magic …) | none | sig trailer @… | … | `cp …` |
| L1 | L0 | 0x… | 0x… | 0x… | payload (manifest entry …) | xz | SHA-256 in manifest §… | … | `scripts/carve.py …` |

A row without offset + command + hash is an anecdote, not evidence.
