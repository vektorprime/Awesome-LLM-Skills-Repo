# 00 — Authorization, Rules of Engagement, Evidence, Engagement OPSEC

**When to read:** FIRST, at engagement kickoff — before any packet leaves your machine. Re-read whenever a scope, action, or stop-condition question arises mid-engagement. If any statement below conflicts with the client's signed RoE, the signed RoE wins — record the conflict in the engagement log and ask the client.
**Prerequisites:** Signed engagement letter / contract + Rules of Engagement document + scope list + contact matrix.
**Primary ATT&CK mapping:** None (meta-phase). This file defines the legality envelope for everything else.

## The non-negotiable core

No offensive action exists in a legal vacuum. Every scan, exploit, credential use, and persistence action must trace back to: **signed authorization → in-scope object → approved action class → inside time window → evidence destination**. If the chain is broken at any link, the action does not happen.

## Authorization artifact checklist (before kickoff)

| Artifact | Must contain | Verify |
|---|---|---|
| Engagement letter | Parties, dates, authorization signature | Signed by someone with authority to bind the client org (procurement ≠ security authority; confirm in writing) |
| Rules of Engagement (RoE) | Scope lists, action classes, time windows, exclusions, stop conditions, deconfliction channel | Dated, versioned; no verbal-only modifications — changes require email confirmation from the named approver |
| Scope list (external) | Domains, IP blocks, URL/app list | Resolve each target at kickoff — IP changes mid-engagement are the #1 accidental out-of-scope cause; re-resolve before every intrusive action |
| Scope list (internal) | CIDRs, hostnames, AD accounts, GPOs | Note shared/overlap infra (file servers, DCs) and handling limits (e.g., "DCs: read-only, no exploitation") |
| Contact matrix | Primary/technical/emergency contacts, both directions | Test the emergency phone path at kickoff — do not discover a stale number during an incident |
| Insurance / liability | Where applicable | Check before high-impact phases (physical, wireless, edge exploitation) |

**Cloud/SaaS third-party caveat:** attacking the client's tenant on a cloud provider's shared infrastructure can be out of scope even though the client "owns" the app. Shared-responsibility confusion is a finding-worthy gap in the client's own authorization, not your license. Require the client to name cloud tenants in scope and provide written confirmation of their right to authorize testing of that tenant. Same for hosted SaaS (third-party operated) — if the client doesn't operate it, you may not attack it without the operator's written consent.

**OT/SCADA/IoT caveat:** if included in scope at all, usually passive observation only. Physical safety systems, electrical, water, medical devices, industrial actuators: default exclusion — require explicit named authorization and a safety briefing before any interaction.

## Scope object model

Scope entries are objects, not vibes:

- **Host objects:** IP, hostname, FQDN, URL. Behind CDNs/load balancers: the *origin* is a different object — origin IPs in scope? ask, don't assume.
- **Account objects:** AD/ecloud usernames, email addresses, app roles. "Any employee account" ≠ "executive accounts" — some RoEs exclude execs/IT admins from phishing.
- **Action classes** (below).
- **Time window:** engagement dates + allowed hours (some RoEs restrict intrusive actions to business hours so staff are reachable).
- **Exclusions:** usually: production crown-jewel data stores, backup systems, safety systems, employee personal devices/accounts, third-party systems, medical/HR data, anything the client flags during the engagement (they can add exclusions any time — you can only subtract scope, never add it).

## Action-class matrix (defaults — RoE overrides)

| Class | Examples | Default stance |
|---|---|---|
| SCAN | port/service scans, content discovery, unauthenticated probes | Allowed on in-scope hosts |
| EXPLOIT | firing CVE PoCs, SQLi to extract data, phishing payloads, credential use | Allowed after lab validation; unvetted PoC against client edge = availability risk, forbidden |
| ESCALATE | privesc on owned hosts, token abuse | Allowed |
| PERSIST | new persistence on hosts | Often restricted: some clients require per-host approval, some allow with inventory + close-out removal guarantee |
| CREDENTIALS/EXFIL | dumping LSASS, reading DBs, "exfiltration" | Dump/copy allowed when needed for the finding; exfil only canary/marker files, never real PII/secrets |
| EVASION | AV/EDR bypass, log tampering | RoE-flagged; frequently "detect and report, don't evade" in purple-style engagements; log deletion is almost always forbidden |
| DESTRUCTIVE / DoS | crashing services, wiping, password spraying to lockout | Excluded by default. Lockout-aware spraying rules apply (see 08). If DoS testing is explicitly in scope, it requires a separate written approval and a tested rollback |
| PHYSICAL / WIRELESS | entry, badge cloning, RF | Requires explicit RoE clause + insurance; never improvise physical actions |

**Rule of escalation for gray areas:** if the action is not clearly covered by the RoE, treat it as prohibited until the client confirms in writing. Log the question and answer in the engagement log — the Q&A itself is evidence of diligence and often becomes a report finding ("client lacked a defined policy for X").

## Stop conditions (immediate full-stop triggers)

1. Client declares emergency / stop (any channel).
2. Suspected unintended impact: crash, hang, error storm on target systems.
3. Discovery of out-of-scope compromise evidence (e.g., a real breach, real attacker TTPs on the network). Stop, preserve evidence, notify client — you are now in incident-response support mode, not red team mode.
4. Personal-identifying or regulated data (PII/PHI/PCI/HR/legal) encountered: capture minimal proof (count + type, one sanitized example), do not bulk-collect.
5. Safety risk (physical/electrical/OT).
6. Legal risk discovered (jurisdiction, third-party owned infra, unexpected data subject territories).
7. Scope ambiguity that cannot be resolved by reading the RoE.

**Emergency procedure (STOP):** cease active operations → snapshot your own tooling state (what's running where, which sessions exist) → write the timeline entry → preserve target evidence read-only → call the emergency contact → wait for direction. Do not "quickly finish" anything. Do not delete anything (even your own artifacts) — deletion during an incident looks like destruction of evidence.

## Evidence handling (chain of custody)

Case directory layout (created at kickoff, from the kickoff checklist):

```
case-<client>-<date>/
├── roe/                  # signed RoE, scope lists, change confirmations, insurance
├── 00-recon/             # recon outputs, OSINT notes, asset inventory
├── 01-scans/             # nmap/masscan/nuclei output (-oA all the things)
├── 02-findings/
│   ├── F-001/            # one dir per finding: commands.md, evidence/, poc/, sanitized-outputs/
│   └── ...
├── 03-hosts/             # per-compromised-host: fingerprint, session notes, artifacts left
├── 04-evidence/          # immutable copies: hashes.txt, chain-of-custody log
├── 05-infra/             # your infra: domains, redirectors, listeners, deployment notes
├── engagement-log.md     # chronological: every action, decision, RoE Q&A, timestamp UTC
└── attack-graph.md       # current state: access levels, paths, pivots, gaps
```

Rules:

- **UTC timestamps everywhere.** Local time causes irreconcilable timelines when correlating with client telemetry.
- Every file that becomes report evidence gets `Get-FileHash -Algorithm SHA256` (Windows) / `sha256sum` (Linux) recorded in `04-evidence/hashes.txt` at creation time.
- Screenshots include: full screen (tooling visible), command line, target identifier, and a UTC clock in frame. See `checklists/finding-evidence.md`.
- Never store real credentials collected during the engagement in plaintext notes — store in the engagement password vault (`04-evidence/vault.kdbx`, client notified it exists) and reference by pointer ("see vault entry svc-backup-01").
- Engagement log entry format: `UTC | PHASE | ACTION | TARGET | RESULT | RoE reference`. Write it as if opposing counsel will read it — because in a dispute, they will.
- Retention/destruction per RoE at close-out: either deliver-everything-and-wipe, or deliver-and-retention-period. Record the destruction (see 15).

## Engagement OPSEC

Your own operational hygiene, separate from target evasion:

1. **Infrastructure separation:** recon infrastructure (your scanning box) ≠ C2 infrastructure ≠ phishing infrastructure. If the client blue team burns your recon IP and you shared it with C2, you lose the whole engagement's C2 as well.
2. **Log everything you do to yourself.** Not just for evidence — for the "was that us or a real attacker?" deconfliction question at 3 AM.
3. **Don't attack your own infrastructure** (DNS rebind and relay mistakes) and don't scan out-of-scope addresses that appear in DNS (CDN nodes — see 01).
4. **Personal devices / accounts:** never. Burner engagement identities only, and keep them recorded in `05-infra` so they can be disclosed at close-out.
5. **No social-media boasting, no engagement artifacts in personal cloud.** Working from personal accounts is an OPSEC finding against you.

## Deconfliction with the client's defenders

- Establish the channel at kickoff (email, phone, shared chat). Emergency "is that you?" responses have a max-agreed latency (e.g., 30 minutes).
- Provide the client an **indicator list** (your source IPs, domains, callback patterns, tool username patterns like `svc-<random>`) — update as it evolves. At close-out this list becomes their hunt package.
- Purple-team engagements: share the technique timing before execution so they can watch telemetry live. Red-only engagements: share nothing until close-out except the emergency protocol.

## Common RoE pitfalls (seen repeatedly in audits)

- "They told us verbally it was OK" — verbal scope changes are void. Email from named approver or nothing.
- Scope stated as company name but subsidiaries/datacenters/holding companies not named → treat each unnamed entity as out of scope; report the ambiguity.
- DHCP/cloud elastic IPs: yesterday's in-scope IP may now belong to someone else. Re-resolve, re-verify, before intrusive actions.
- Client "owns" the app but not the platform (shared hosting, SaaS): attack the app logic only, never the platform or neighbors.
- Physical scope written loosely ("office in Baltimore") — specific address, specific entry methods allowed, specific rooms. Loose physical scope = no physical.
- Phishing targets: get the approved account list *in the RoE*, including whether executives/IT admins/security team are excluded (spoofed executive phishing of a CFO without explicit approval = client-relations incident).
- DoS assumed included "because that's hacking" — explicitly excluded unless separately approved.

## Evidence handoff

- The engagement log + scope table from this phase is the reference every later phase cites in its evidence entries.
- Every finding cites: RoE authorization (this file's artifacts) + command + output + hash. Without the RoE link, a finding is not audit-grade.
