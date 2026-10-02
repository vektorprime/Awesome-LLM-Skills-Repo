---
name: red-team-operations
description: Authorized red teaming, penetration testing, and adversary emulation - reconnaissance, network and web exploitation, Active Directory attack paths, privilege escalation, credential access, lateral movement, persistence, C2, defense evasion, cloud and container attacks, wireless/physical, custom TCP protocol servers (game/app backends), and engagement reporting. Use when asked to perform, plan, or verify offensive security testing against an authorized, in-scope target.
---

# Red Team Operations

**Scope:** Authorized offensive engagements (pen test, red team, adversary emulation, purple team feed) against targets covered by a signed Rules of Engagement (RoE). Malware/sample *analysis* routes to `reverse-engineering-executables`; shellcode/ASM authoring routes to `x64-assembly`; binary *exploitation methodology* stays here (`references/11`).
**Operating principle:** No offensive action without authorization; every claim is evidence-backed, confidence-labeled (Observed / Inferred / Unknown), and mapped to a MITRE ATT&CK technique. Assume every action is logged — the engagement goal is to demonstrate risk and produce remediable findings, not to be invisible at any cost.

## Authorization gate (must answer all 5 before ANY offensive action)

1. What signed authorization covers this action (engagement letter / RoE reference)?
2. Is the exact target object in scope *right now* (IP/hostname/account/app from the scope list, inside the time window)?
3. Is this action class approved (scan / exploit / escalate / persist / exfil)?
4. What are the stop conditions (client contact, detection callback, availability risk, safety risk)?
5. Where does the evidence go (case dir, artifact hash, engagement log)?

Any missing or "no" answer → stop, report the gap, do not improvise. Scope creep is a finding-worthy ethics violation. Read `references/00-authorization-rules-of-engagement.md` FIRST on every engagement, no exceptions.

## Engagement loop (every phase, every target)

```text
Scope check -> cheapest safe observation -> hypothesis -> decisive test
  -> capture evidence -> update attack graph -> next target or stop
```

- Cheapest safe observation first: passive > active, read > write, non-destructive > destructive.
- Decisive test = the one test whose result kills or confirms the hypothesis. Do not spray payloads when one crafted request answers the question.
- Never execute an unvetted PoC (especially edge-device exploits) against client infrastructure without lab validation first — crash = availability impact = RoE violation.
- Non-production data rule: demonstrate exfiltration with canary/marker files only, never real PII/PHI/secret data.

## Phase router — read only what you need

| Task / trigger | Read |
|---|---|
| Engagement start, scope check, stop conditions, evidence custody | `references/00-authorization-rules-of-engagement.md` (always first) |
| Company/asset recon, OSINT, subdomain and attack-surface mapping | `references/01-recon-osint.md` |
| Host discovery, port/service/OS scanning, service deep-dives, vuln scanning | `references/02-network-enumeration.md` |
| Web apps and APIs: injections, auth/session logic, Burp workflow | `references/03-web-api-exploitation.md` |
| Gaining first foothold: phishing, edge devices, payload delivery | `references/04-initial-access.md` |
| AD attack paths: enumeration, Kerberos abuse, relay, ADCS, dominance | `references/05-active-directory.md` |
| Elevation on a Windows host (service/triggers/token abuse) | `references/06-windows-privesc.md` |
| Elevation on a Linux host (sudo/SUID/caps/kernel) | `references/07-linux-privesc.md` |
| Dumping and using credentials; moving host-to-host | `references/08-credential-access-lateral-movement.md` |
| Surviving reboots, C2 infrastructure and egress design | `references/09-persistence-c2.md` |
| Working around AV/EDR/AMSI/ETW within RoE | `references/10-defense-evasion.md` |
| Exploiting memory corruption (lab/CVE targets, exploit dev) | `references/11-binary-exploitation.md` |
| Custom TCP/binary-protocol servers: game backends, protocol RE, MITM relay, stateful fuzzing | `references/16-tcp-application-servers.md` |
| AWS / Azure (Entra) / GCP compromise chains | `references/12-cloud-red-team.md` |
| Docker and Kubernetes escape/RBAC abuse | `references/13-containers-k8s.md` |
| WiFi, Bluetooth, RFID/NFC, SDR, physical entry | `references/14-wireless-physical-hardware.md` |
| Findings, risk rating, remediation, close-out, purple-team handoff | `references/15-reporting-remediation.md` |

Templates: `checklists/engagement-kickoff.md` (before first packet), `checklists/host-fingerprint.md` (on every new shell), `checklists/finding-evidence.md` (per finding), `checklists/report-template.md` (deliverable skeleton).

## Tool fallback order (global)

- Attack framework: `Sliver` (or Mythic) > Cobalt Strike > raw tooling; staged < stageless.
- AD collection: BloodHound CE (`bloodhound-python` / SharpHound) > PowerView manual LDAP.
- SMB/WMI/WinRM remote exec: Impacket (`psexec`/`wmiexec`/`smbexec`/`atexec`) > netexec (nxc) > native PSRemoting.
- Web proxy: Burp > mitmproxy (CI/automation) > manual requests.
- Wordlists/payloads: validate in lab before client use; every public PoC gets a lab run first.
- If a primary tool is detected/blocked, prefer quieter alternative over louder evasion unless RoE explicitly permits evasion work.

## Definition of done

Every finding has evidence artifacts (command, output, hash, timestamp) + reproduction steps + confidence label + ATT&CK technique ID + remediation that a sysadmin can act on. Attack path narrative reconstructable by a second analyst from the case dir alone. Evidence retention per RoE; no artifacts left on targets without written exception; close-out checklist in `references/15-reporting-remediation.md` signed off.
