# 04 — Initial Access (External → Foothold)

**When to read:** Converting external attack surface (01/02/03) into a foothold; any phishing/edge-device/pre-auth exploitation task; designing callback infrastructure before first payload.
**Prerequisites:** Authorization gate with action class EXPLOIT; RoE-approved target list and payload classes; lab validation environment ready; callback infrastructure deployed and recorded (indicator list, 00).
**Primary ATT&CK mapping:** T1566 Phishing (T1566.001 Spearphishing Attachment, T1566.002 Spearphishing Link), T1204 User Execution, T1027.006 HTML Smuggling, T1190 Exploit Public-Facing Application, T1133 External Remote Services, T1078 Valid Accounts, T1110 Brute Force (T1110.003 Password Spraying, T1110.004 Credential Stuffing).

## Decision tree (external surface → foothold)

```text
External inventory
  ├─ web app vuln (03) ──────────────→ shell/webshell foothold (→06 privesc)
  ├─ edge appliance (VPN/FW/LB/EGW) ──→ fingerprint→CVE→lab→exploit (below)
  ├─ exposed auth portal (VPN/RDP/SSH/mail)
  │     ├─ MFA enforced? ──no──→ cred-stuff/spray (RoE rules below) → session (→08)
  │     └─ MFA + no password risk → phishing for creds/token capture (below)
  ├─ code-leak creds (01) ────────────→ RoE decision point (usage may exceed scope class — ask)
  └─ supply-chain/trusted-rel vector (client-flagged, explicit RoE only)
```

**Non-negotiable:** every payload fired at a human or edge device was lab-validated first, and every payload's hash is in the case evidence log before it leaves your infra.

## Edge device exploitation (appliance/edge class)

Methodology (per device):

1. **Fingerprint precisely** (01/02): version from headers/cert/cookies/API endpoints (`/remote/login` FortiSSLVPN style paths, `Server: bigip`, cookie names, favicon hash, admin portal JS bundle versions). Appliance CPE mapping is evidence — the exact build string, not "Fortigate-ish".
2. **Map to CVEs**: vendor advisory pages for that build; public exploit-db/GitHub PoC hunting; read the PoC **code** line-by-line before it runs anywhere:
   - Does it write files / execute commands on target or just crash it? (Crash-class PoCs against an edge appliance = availability incident = 00 stop-condition.)
   - Does it leak config only (read) or drop a shell (write)?
   - Is it authenticated vs pre-auth? (Pre-auth RCE class ≠ "external user can..." — read the advisory preconditions carefully.)
3. **Lab validate**: matched-version VM/appliance (client may provide an image) → run PoC → record behavior (what files/process/persistence it touches).
4. **Client-approved window** for the target run; log the exact timestamp; notify contact before + after.
5. **Post-exploit appliance discipline**: appliance shell ≠ Linux host. Read-only investigation first (enumeration minimalism): extract config (contains LDAP bind creds, internal VPN accounts, shared secrets, certificate keys — all big findings, all into the vault, 00), enumerate internal interfaces (pivot notes for 02-internal). Do NOT modify appliance state beyond the exploitation artifact; document every artifact left (close-out, 15).
6. Appliance patch-level finding: report both the exploited path AND the patch-gap process finding (the real audit value is "edge fleet is unmanaged", not "one CVE").

## Credential-based external access

- **Password spraying** (T1110.003): RoE rules: lockout policy researched first (O365/internal portal lockout thresholds), approved account list, 1 password/user/round, rounds spread days apart. Passwords from client's provided policy or common corporate-pattern list; never random hammering. Target SSO/ADFS portals over raw auth APIs where MFA callback loops exist. All attempts logged (target, timestamp, result) — the spray log is both evidence and lockout forensics.
- **Credential stuffing** (T1110.004): only with RoE-provided/approved breach corpus (01's rule); rate-limited; locked-account callbacks monitored (00 emergency path if lockout storm).
- **Breach-leaked internal creds found in OSINT (01)**: usage requires an explicit client decision — a cred that "leaks" may belong to a real breach the client doesn't know about → that's an incident-report path, not a free foothold (00 stop-condition 3: suspected real compromise evidence).

## Phishing (T1566) — full workflow

**RoE prerequisites (all in writing):** approved target list (execs/IT-admin inclusion explicit), approved pretext class (finance/HR/IT-helpdesk/etc.), allowed payload classes, allowed action on click/credential capture, disclosure/notify plan for phished users, opt-out/monitoring plan for any credential captured (vault + notify, 00).

**Infrastructure:**

- Engagement sending domain (lookalike/selected-per-RoE; recorded in `05-infra/` + indicator list). Sending domain gets SPF/DKIM/DMARC for YOUR domain (deliverability, not spoofing the client's domain). Spoofing the client's own domain requires explicit RoE authorization — it uses their identity, some clients say no.
- Landing pages: engagement-approved clone of a client asset, or vendor-style fake; hosted on engagement infra; TLS cert per domain; all page traffic logged to case evidence.
- Callback/OOB endpoints: interactsh/canarytoken/webhook listeners — callback domain = execution proof.

**Payload classes (selection by detection posture + RoE):**

| Class | Current detection reality | Notes |
|---|---|---|
| Macro docs (mml) | AV/mail-gateway heavy detection | Use only as "gateway detected it" control experiment if RoE wants mail-security metrics |
| LNK shortcut | Frequent gateway block | Embedded command visible to analysts — sometimes the point (blue-teaming feed) |
| ISO/IMG/VHD containers | Mark-of-the-Web propagation gaps | Mount-based execution; current-era classic |
| OneNote (.one) | Blocked in current Office builds | Legacy-only |
| HTML smuggling (T1027.006) | Gateway JS sandboxing varies | Blob-constructed payload in browser context |
| OOXML remote-template (DOTM/DLL fetch) | Moderate | Remote template fetch via initial file |
| Browser-exploit class | Out of RoE scope normally | Requires explicit client authorization (memory-corruption against employees' browsers = 11 + legal review) |

**Payload discipline:** stage-0 = minimal canary beacon (callback + host fingerprint only). Real stage-1 (implant) only after callback + RoE confirmation. Detonate every payload class in lab (matching Office/OS builds) before first send; hash + record each payload version sent to which targets.

**Credential-capture phishing:** capture → hash password immediately → vault storage (00); no plaintext in notes/screenshots (mask in evidence). OTP/MFA interception requires explicit RoE authorization. Token-replay (evilginx-style session proxy) = higher authorization class (credential + session theft — some clients approve creds but not sessions; ask).

**Evidence:** delivery table `04-evidence/phishing-delivery.md`: target | timestamp | payload hash | sent | clicked (callback) | executed | result. Metrics feed the report (15) — click/exec rates are the client's risk number.

## Wireless/physical initial access → route to `14` (RoE-gated separately).

## Common failures / misreads

| Symptom | Misread | Reality check |
|---|---|---|
| CVE matches banner version | "Exploitable" | Backport/patch-tuesday divergence; the decisive test is the lab |
| PoC works in lab, hangs on target | "Retry harder" | Hardware/config divergence — retry escalates crash risk; stop, diff configs with client |
| Payload "delivered" = sent | Foothold gained | Delivery ≠ click ≠ execute; only callback is execution proof |
| Spray gets one hit | "Spray works, scale it" | Lockout risk scales too — one more controlled round per RoE, not a hammer |
| Phished user calls helpdesk | "Blown, abort" | Expected — per-RoE: either stop (red) or watch SOC handle it (purple) — this is the exercise data |

## Detection footprint

- Mail gateways log payloads; EDR logs execution at stage-0; the client's SIEM sees it — deconfliction indicators (00) make it correlation-friendly instead of incident-generating.
- Edge exploit: firewall/session logs on the appliance (record the pre/post timestamps for the client's timeline reconstruction, 15).
- Spray: auth-failure storms are the loudest signal in the whole engagement — pre-declare the exact source/time window.

## Tool fallback order

- Spray: custom RoE-conformant script > SprayingToolkit-class (throttle control) > raw hydra (last — no lockout-awareness, avoid).
- Phishing: GoPhish-class framework (delivery + tracking) > manual infra (client-restricted environments).
- Callback: interactsh (self-hosted) > canarytokens > webhook.site (quick one-shots only).

## Evidence handoff

`03-hosts/` gains the foothold entry: how access was gained (phish/edge/cred), timestamp, account context (who/privileges), first-host fingerprint (checklists/host-fingerprint.md), callback → implant mapping. Foothold entry feeds: 06 (privesc if user-context), 08 (creds/lateral), 09 (persistence decision — RoE-gated).
