# Finding Evidence Checklist (per finding — the audit unit)

A finding without complete evidence does not ship. This checklist is the capture standard for
EVERY finding, run at capture time (not reconstructed later — 15's doctrine).

## Per-finding capture standard

```text
[ ] Exact commands/requests recorded (paste-ready: an engineer reproduces without asking you)
[ ] Raw output captured to 02-findings/F-NNN/evidence/ (file, not screenshot, where possible)
[ ] Every evidence file hashed at creation (SHA256 → 04-evidence/hashes.txt)
[ ] UTC timestamps: capture time + target's clock time (clock-skew notes — 08's KRB_AP_ERR case)
[ ] Screenshot for impact moments (full screen, command visible, UTC clock in frame — 00's rule)
[ ] Target identity pinned: host/account/version (version-pin the vulnerable component — 01/02)
[ ] RoE citation: which scope entry + action class authorized THIS action (00's chain)
[ ] Confidence label: Observed | Inferred | Unknown (house standard — a finding ships only as
    Observed for the claimed impact; Inferred for the claimed class)
[ ] Credential/data minimization applied: no plaintext creds in notes/screenshots (mask in
    evidence), hash-sample-only for bulk data (00's rule), vault pointers for secret values
[ ] Blast-radius honesty: demonstrated impact vs theoretical ceiling — both stated, labeled
```

## Screenshot composition rules (impact evidence)

- Full desktop/terminal visible (no cropped-to-glory shots).
- The command that produced the result is in frame or the previous frame is numbered.
- Target identifier visible in the output (hostname/whoami/URL bar).
- UTC clock visible in frame.
- Sensitive values masked AT CAPTURE (post-capture editing = evidence-integrity question —
  never edit evidence files, mask in the command or blur at capture).

## Evidence file layout

```
02-findings/F-NNN/
├── commands.md          # reproduction steps (the paste-ready list)
├── evidence/            # raw captures (output files, PCAPs, registry exports, DB dumps-as-proof)
├── poc/                 # PoC scripts/payloads + hashes (0's lab-validation records attached)
├── notes.md             # analysis, root cause, confidence labels, impact reasoning
└── writeup.md           # the 15-finding-template output (the report imports this)
```

## Before the finding ships (per-finding review)

```text
[ ] Reproduction steps tested by a second pair of hands (or scripted re-run) — mechanical
[ ] Severity: CVSS vector string recorded (or qualitative justification for logic/physical class)
[ ] Root cause named (process gap, not just the instance — 15's root-cause rule)
[ ] Remediation written with a verification step (re-run → expected safe result)
[ ] No engagement OPSEC data leaked into the finding (infra details stay in 05-infra unless
    the finding IS about infra — then sanitized)
```
