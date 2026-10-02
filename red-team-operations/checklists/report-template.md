# Report Template (deliverable skeleton)

Fill from case-dir artifacts (15's doctrine: rebuild from evidence, never from memory).
Sections marked ⚠ must not ship empty — if empty, the engagement isn't ready to close.

---

# <CLIENT> — <ENGAGEMENT TYPE> Report

**Version:** 1.0 | **Date:** <UTC date> | **Classification:** <per contract>
**Prepared by:** <team> | **Engagement window:** <start> – <end>

## 1. Executive summary ⚠

```markdown
- Engagement goal (client's words) + type (red/purple/external/internal)
- Headline result: <foothold achieved in X; domain admin in Y days | compromise NOT achieved +
  the strongest partial result + why the gap matters anyway>
- Top risks (business language, 3 max) + business-impact sentence each
- Top quick wins (3 max, effort-rated)
- Statistics block: findings by severity | time-to-foothold | time-to-DA | ATT&CK tactics covered
```

## 2. Scope & methodology ⚠

- In-scope objects (from roe/scope-table.md) + out-of-scope + exclusions
- Method per phase (one line each: 01–14 route summary)
- RoE deviations: NONE, or documented with written client authorization (00's chain)
- Second-analyst reproduction test: performed? result (15's quality proof)

## 3. Findings ⚠ (sorted: severity → effort-to-fix)

One per F-<NNN> (15's finding template — imported from writeup.md):
title | severity (CVSS vector + engagement-context) | class + ATT&CK techniques | affected
(version-pinned) | confidence | description + root cause | reproduction | evidence (hashes) |
demonstrated impact vs realistic ceiling | remediation (immediate + systemic + verification step)

## 4. Attack narrative ⚠ (the story, from engagement-log timestamps)

```markdown
- Vector: <phish/edge/cred/...> (from 04) → first foothold (<UTC>, <host/account>)
- Path: <enum → exploit → escalate → creds → lateral → objective> (cites phase evidence)
- Objective reached: <what/when/UTC> | Not reached: <what stopped it + why that matters>
- Pivot points + key decisions (the misconfig chain that carried the path — the client's fix list)
```

## 5. ATT&CK coverage table ⚠

| Tactic | Techniques executed | Technique IDs | Detected by client | Coverage gap? |
|---|---|---|---|---|

## 6. Detection coverage appendix (purple handoff) ⚠

Per technique used (roll-up of phase tables — 10's self-audit + each phase's footprint section):
the telemetry that SHOULD have caught it → what DID (if client telemetry shared) → the gap →
concrete detection-engineering suggestion (log source + logic + test).

## 7. Remediation plan ⚠

- Quick wins (0–2 wks): <per 15's table> — each with verification step
- Short-term (1–2 mo): systemic config fixes
- Strategic (quarter+): architecture/process/telemetry program (from detection appendix)

## 8. Artifacts left & removal verification ⚠ (15's hard gate)

| Artifact | Host/tenant | Created (UTC) | Removal method | Verified (UTC+method) | Status |
|---|---|---|---|---|---|

Unverified/waived rows: escalated in writing BEFORE delivery (15's rule).

## 9. Indicator package (client hunt/block list)

Source IPs | domains | callback patterns | account names created | tool filename patterns |
persistence object names — from 05-infra + phase artifact lists.

## 10. Appendices

- A: Evidence index (file → SHA256 → finding)
- B: Scope list (as executed — with resolution history)
- C: Credential vault disposition record (delivered/destroyed + method + witnesses)
- D: Retest offer (scoped from remediation verification steps)
- E: Glossary (for exec readers)
