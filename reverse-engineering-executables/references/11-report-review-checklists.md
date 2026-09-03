# 11 — Report, Review, Escalation, Close-Out

## 1. Report template (`report/report.md`)

```markdown
# Analysis Report: <case ID>
## 1. Question and scope (authorized scope, question, exclusions)
## 2. Evidence identity (orig filename, SHA-256, size, provenance, tool versions)
## 3. Executive conclusion (answer + confidence + material limits, 3-5 sentences)
## 4. Technical classification (format, arch, runtime/toolchain, protections)
## 5. Confirmed capabilities | Finding | Confidence | Evidence | Function/offset |
## 6. Runtime observations | Test | Input SHA | Observation | Artifact |
## 7. Indicators (only behavior-linked: IPs/domains/hashes/paths + context)
## 8. Unknowns + alternative explanations
## 9. Reproduction (exact commands / script refs)
## 10. Recommendations (scoped, linked to findings)
```

Citation style: `Observed in artifacts/dynamic/run-003/strace.4121 lines with connect(5,...)=0; caller at 0x4019a2 in ghidra-decompile/00401920_build_connection.c`. Never cite screenshot-only or paraphrase.

## 2. Peer-review checklist (reviewer answers yes/NA)

Scope/safety: authorization logged, original read-only+hashed, exec necessary+contained.
Method: format/arch/base confirmed, PIE/ASLR VA math correct, decompiler checked in asm, imports not claimed as runtime, entropy not proof, failures disclosed.
Repro: commands/scripts/inputs/versions saved, derived artifacts hashed+parented, decisive test rerunnable.
Comms: facts/inferences/unknowns split, confidence justified, conclusion answers scope, recs don't exceed evidence.

## 3. Escalate (senior behavior, not failure)

- Unfamiliar arch where wrong guess changes conclusion; kernel/hypervisor/bootloader central.
- Commercial virtualization (VMP/Themida) blocks critical question; crypto-protocol verdict needs specialist.
- License/legal bar on circumvention; regulated/personal data inside; containment impossible; impact > confidence.

## 4. Close-out (all boxes before closing)

```text
[ ] Scoped question answered
[ ] Original preserved + hashed
[ ] Commands + versions recorded
[ ] Facts/inferences/unknowns split
[ ] Decompiler checked in asm
[ ] Dynamic claims have artifacts
[ ] Derived artifacts hashed + parented
[ ] Alternatives considered
[ ] Confidence + limits stated
[ ] Second analyst can reproduce
[ ] Reusable steps scripted
```

## 5. Failure mantras (paste into notes when tempted)

High entropy ≠ encrypted. Import ≠ behavior. Decompiler ≠ source. No strings ≠ no static. Entry ≠ main. Debugger VA ≠ file VA. 5 tools sharing one signature DB ≠ 5 confirmations. Senior = answers scope + bounds unknowns, not reads every function.
