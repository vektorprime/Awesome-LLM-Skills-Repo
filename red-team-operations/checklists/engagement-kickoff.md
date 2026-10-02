# Engagement Kickoff Checklist (before the first packet)

Complete EVERY item. Any unchecked item = blocker (00's authorization gate) — resolve or stop.

## Authorization artifacts

```text
[ ] Signed engagement letter on file (parties, dates, named approver with authority)
[ ] Rules of Engagement (RoE) doc on file, version + date identified
[ ] Scope list (external: domains/IPs/apps; internal: CIDRs/hosts/accounts)
[ ] Scope entries resolved NOW (DNS/IP current-state — re-resolve at each phase start)
[ ] Action classes confirmed: SCAN / EXPLOIT / ESCALATE / PERSIST / CREDENTIALS / EXFIL
    / EVASION / DESTRUCTIVE / PHYSICAL / WIRELESS — allowed or not, each in writing
[ ] Time window + allowed hours confirmed
[ ] Exclusions list confirmed (safety systems, OT, employee personal devices, third-party, data classes)
[ ] Cloud tenants named in scope in writing (00 shared-infra caveat)
[ ] Stop conditions + emergency contacts confirmed (test the phone path)
[ ] Deconfliction channel + indicator-exchange format agreed
[ ] Insurance/liability requirement checked for physical/wireless classes
```

## Evidence infrastructure

```text
[ ] Case directory created (00's layout)
[ ] Engagement log started (first entry: kickoff time UTC)
[ ] Vault created (04-evidence/vault.kdbx, client notified it exists)
[ ] Evidence media identified (no personal devices/accounts anywhere)
[ ] Retention/destruction terms confirmed from RoE
```

## Attack infrastructure

```text
[ ] Recon infra separated from C2 infra separated from phishing infra (00's separation rule)
[ ] Engagement domains/redirectors deployed (or scheduled per phase) → recorded in 05-infra/
[ ] Indicator list drafted (source IPs, domains, account patterns, callback patterns)
[ ] Tooling lab-validated inventory started (tool + version + validated-on-build)
```

## Client-side alignment

```text
[ ] Kickoff meeting held: goals, detection objectives (red vs purple posture confirmed)
[ ] Client contacts confirmed (primary/technical/emergency — all directions)
[ ] RoE Q&A gaps logged (ambiguities asked + written answers filed under roe/)
[ ] Phishing target list / approved pretext classes confirmed in writing (if phishing class)
[ ] Persistence per-host approval process confirmed (if PERSIST class)
[ ] DCSync / DC-touching / domain-object-modification approval process confirmed
[ ] Close-out requirements confirmed (artifact removal verification, evidence disposition)
```

## Kickoff output (case-dir artifacts created by this checklist)

```text
roe/scope-table.md          # every scope object + current resolution + class allowed
roe/contacts.md             # contact matrix + tested-status
roe/roe-qa-log.md           # every ambiguity asked + the written answer
engagement-log.md           # started
attack-graph.md             # initialized (empty graph, current objective)
```
