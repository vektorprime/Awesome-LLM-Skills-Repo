# 15 — Reporting, Remediation & Close-Out

**When to read:** Continuously (findings captured as they happen — end-of-engagement reconstruction is how findings die); at engagement close (the deliverable); at client debrief/purple-team handoff; retest scoping.
**Prerequisites:** Engagement log complete (00); finding evidence per `checklists/finding-evidence.md`; artifacts-left inventory complete.
**Primary ATT&CK mapping:** Report contains the engagement's full technique map (per-phase tables in 01–14 roll up here); this file's own workflow = deliverable production.

## The report doctrine (audit-grade = defensible)

1. **Every claim carries its evidence** (command + output + hash + timestamp + RoE citation). No evidence, no finding — opinions go in "observations," clearly labeled.
2. **Confidence labels enforced:** Observed (reproduced with artifacts) / Inferred (strong evidence, not fully reproduced) / Unknown (anomaly worth noting). House standard from SKILL.md — a report that mixes them is not audit-grade.
3. **No impact inflation.** A read-only XSS under strict CSP is not "full account takeover." Rate honestly — inflating findings to look impressive is the #1 audit failure mode; the client's remediation budget follows your severity.
4. **Write for two audiences:** exec summary (risk language, business impact, no acronyms) + technical body (reproduction-grade detail). Findings each self-contained: an engineer can reproduce, a manager can understand impact.
5. **Reproducible by a second analyst from the case dir alone** (SKILL.md definition of done — test this before delivery: pick a finding, rebuild the story from artifacts only).

## Report structure (deliverable skeleton — `checklists/report-template.md`)

1. **Executive summary** — engagement goals → what was achieved (foothold → domain admin in X days; or "not achieved, and why that matters" — a failed compromise with strong partial findings is an honest and valuable result) → top risks in business language → top-3 quick wins. One page, zero jargon.
2. **Scope & methodology** — what was in/out of scope (00 artifacts), method per phase (01–14 references), timeline, RoE deviations (none, or documented + why).
3. **Statistics** — findings by severity, time-to-foothold, time-to-DA (the client's headline metric), coverage of the MITRE tactics exercised.
4. **Findings** (each per template below, sorted by severity then effort-to-fix).
5. **Attack narrative** — chronological story: vector → path → pivot → objective, tied to engagement log timestamps. This is what executives read after the summary.
6. **ATT&CK heat-map table** — techniques executed per tactic, detection coverage per technique (from the technique→telemetry tables built in every phase).
7. **Detection coverage appendix (purple-team handoff)** — for EVERY technique used: the telemetry that SHOULD have caught it (per the phase tables), what DID (if client shared telemetry), the gap, and a concrete detection-engineering suggestion (log source + logic + test). This appendix often outvalues the findings themselves — its absence makes the report a vulnerability list instead of an improvement plan.
8. **Remediation plan** — phased (below).
9. **Artifacts left & removal verification** (below — hard gate for close-out).
10. **Appendices** — full evidence index (hashes), scope list, indicator package (IPs/domains/accounts/tool names used — the client's blocklist + hunt package), glossary as needed.

## Finding template (per finding — the audit unit)

```markdown
## F-<NNN> — <title: vulnerable thing + impact>
- Severity: <Critical/High/Medium/Low> — CVSS 3.1 vector + score (or justified qualitative for
  logic/physical classes where CVSS misleads) + business-impact line
- Class: <vulnerability/misconfiguration/exposure/process gap> + ATT&CK technique(s) exercised
- Affected: <exact hosts/accounts/objects — version-pinned>
- Confidence: Observed | Inferred | Unknown
- Description: what the issue is, why it exists (root cause, not just symptom)
- Reproduction: step-by-step commands/requests (paste-ready, exact)
- Evidence: artifacts + hashes (00 evidence rules) — screenshots for impact moments
- Impact: demonstrated path (what was done with it) + realistic ceiling (what could be done)
- Remediation: immediate fix + systemic fix + verification step
- References: client ticket/asset IDs where applicable
```

**Root-cause discipline:** every finding names the process reason (patch process gap, credential-hygiene gap, default-config culture) — fixing one instance without the process line means the finding returns at retest. Process findings ("edge fleet unmanaged" behind a single CVE) are report-headline material (02's rule).

## Severity model

- CVSS 3.1 (4.0 where the client prefers) for technical vulnerabilities — but **always pair with exploitability context from the engagement** (a CVSS-9 that required an unattainable precondition on THIS network is Medium in reality — say so explicitly).
- Qualitative-justified severity for logic/physical/org classes (03's authz logic, 14's culture findings).
- The pair (CVSS + engagement-contextual rating) is audit-defensible; either alone is not.

## Remediation plan quality bar

| Phase | Content | Client action |
|---|---|---|
| Quick wins (0–2 weeks) | critical fixes: leaked creds rotated, exposed service closed, patch-this-now CVEs | fast, low-effort, high-impact |
| Short-term (1–2 months) | systemic config fixes: signing enforcement, delegation cleanup, password policy | change-managed |
| Strategic (quarter+) | architecture/process: segmentation, tiering, telemetry gaps (the detection appendix), patch/credential-hygiene programs | roadmap |

Every remediation item carries a **verification step** ("after applying, re-run F-004 reproduction — expect 403") so retest is mechanical.

## Artifacts left & removal (the hard close-out gate)

1. Aggregate `03-hosts/*/artifacts-left.md` + `05-infra/` + phase artifact lists (05's domain-object changes, 09's persistence, 12's cloud resources, 13's cluster state, 14's physical devices) into the master list.
2. Removal per artifact class: hosts (delete services/tasks/persistence + verify with autoruns-class listing), domain (revert attribute/ACL changes — 05's before-values), cloud (delete keys/users/grants + confirm), physical (retrieve devices + count-in/out — 14's rule).
3. **Verification pass, not a trust pass:** re-enumerate each host/tenant/namespace with the client; every artifact confirmed gone (or explicitly accepted-in-writing by the client as retained for detection purposes — rare, needs sign-off).
4. Unremovable/unverifiable artifact = escalated to the client in writing BEFORE final report delivery — never discovered post-delivery.
5. Credential material disposition per RoE: vault delivered (client password) or destroyed with recorded proof (00 retention rules).

## Evidence retention & destruction (RoE-driven)

- Deliver-and-wipe (common): evidence media sanitized (documented method), engagement-log retained copy to client, your copies destroyed + destruction entry in log.
- Retention-period class: media held per contract period (inventory entry with dates), destruction calendar note.
- What NEVER gets destroyed during an active dispute or incident follow-up: the engagement log (00's incident rule — destruction during dispute = evidence-destruction optics).

## Retest & program guidance

- Offer retest scope for fixed findings (mechanical with the verification steps written as above).
- Longer-cycle suggestion: the detection appendix becomes their detection-engineering backlog; propose a purple-team exercise for next cycle (targeted, using THIS engagement's techniques).

## Close-out checklist (the final gate — all must be ✓)

```text
[ ] All findings evidence-complete (00 evidence rules) + confidence-labeled
[ ] Attack narrative reconstructable from case dir by second analyst (tested)
[ ] Technique→telemetry detection appendix complete (every technique used has a row)
[ ] Artifacts-left master list: every entry removed-and-verified OR client-waived in writing
[ ] Credential vault disposition executed + recorded per RoE
[ ] Indicator package delivered (blocklist/hunt package)
[ ] Evidence retention/destruction per RoE + logged
[ ] Client debrief delivered; Q&A documented
[ ] Engagement log final entry written (end time, final status)
```

## Common failures / misreads

| Symptom | Misread | Reality check |
|---|---|---|
| Findings written from memory at end | "Faster" | Memory reports lose evidence links, misquote commands, miss confidence labels — rebuild from case dir or the finding dies in review |
| Every finding Critical | "Looks thorough" | Severity inflation = audit failure; executives stop trusting the report (and the retest) |
| "No artifacts left" (unverified) | "Clean" | Verify by re-enumeration (above); trust-pass close-outs are where incidents hatch |
| Detection appendix skipped | "Optional extra" | The highest-value deliverable for the client's program; its absence is the most common top-tier audit complaint |
| Remediation = "patch it" | "Actionable" | No verification step = not actionable; no root cause = it returns |

## Tool fallback order

- Report pipeline: markdown source (case-dir `report/`) → delivered PDF/HTML (client-preferred format). No proprietary-only formats as source of truth.
- ATT&CK table: hand-built from phase tables (engagement-specific) > Navigator layer export for client's own tooling (JSON, per-tactic coverage).
- CVSS: calculator with vector string recorded in the finding (vector = audit trail for the number).

## Evidence handoff (final)

The report + case dir + indicator package + signed close-out checklist = the engagement's complete output. Second-analyst reproduction test result noted in the report's methodology section (it's a quality proof). Retest offer scoped from the remediation verification steps.
