# 08 — Credential Access & Lateral Movement

**When to read:** After any foothold/escalation (06/07) — to harvest credentials and move host-to-host; whenever hashes/tickets exist and need using; before password spraying decisions.
**Prerequisites:** Action class CREDENTIALS approved; target hosts in scope re-verified; vault ready (00); EDR posture known (10) — dump technique choice is posture-driven.
**Primary ATT&CK mapping:** T1003 OS Credential Dumping (T1003.001 LSASS Memory, T1003.002 Security Account Manager, T1003.003 NTDS, T1003.006 DCSync, T1003.008 /etc/passwd and /etc/shadow), T1550 Use Alternate Authentication Material (T1550.002 Pass the Hash, T1550.003 Pass the Ticket), T1558.001 Golden Ticket / .002 Silver Ticket (usage class), T1021 Remote Services (T1021.002 SMB/Windows Admin Shares, T1021.003 DCOM, T1021.004 SSH, T1021.006 WinRM), T1050/T1543.003 service-based lateral, T1053.002 AT, T1555.004 Credential Manager (vault class), T1555.003 browsers, T1110.003 Password Spraying (internal).

## Credential dumping decision tree (Windows)

```text
Host-level access on a host with interactive logons (workstations/servers used by humans)
  → LSASS (T1003.001)  — highest yield; technique set chosen by EDR posture (10)
Host = DC OR replication rights (from 05 attack path)
  → DCSync (T1003.006) — RoE-gated (bulk domain credential pull — 05 Phase 6)
Any admin context on a host
  → SAM + SYSTEM + SECURITY (T1003.002) + local caches (domain cached creds)
  → DPAPI blobs + Credential Manager + browser stores
Service context / scheduled task service account
  → service account credentials (LSASS holds them too); Kerberos tickets in LSASS (Rubeus dump class)
```

### LSASS (T1003.001)

Technique selection by posture (full posture tree in 10):

| Context | Technique | Notes |
|---|---|---|
| EDR-blind host (rare) | `procdump -ma lsass.dmp` / `comsvcs.dll MiniDump` / `nanodump` classic | Comsvcs needs SeDebugPrivilege |
| PPL enabled on LSASS | Handle-duplication from an entitled process, or PPL-bypass via driver class (BYOVD — RoE-flagged) | Lab-validated |
| Hostile EDR | Off-host dump path: no on-host dump at all — use remote SAM/DCSync-style paths instead | The quiet path |

Dump → offline parse (pypykatz/mimikatz offline on YOUR box — parsing off-host keeps on-host footprint minimal): NTLM hashes, AES keys, plaintext where reversible-encryption/W_digest-provider active (default off since Win8.1 — if found, itself a hardening finding: WDigest `UseLogonCredential` = 1).

**Evidence discipline:** dump file hashed into evidence (04-evidence), NEVER parsed results pasted raw into notes — parsed creds go straight to vault (00); report cites vault entry pointers.

### SAM / caches / NTDS

```cmd
reg save hklm\sam sam.hive && reg save hklm\system system.hive     ;; parses offline: sam dump + boot key
```

NTDS extraction paths (if DCSync not viable / RoE prefers file-based): `ntdsutil` IFM-class (needs DC-local admin; creates install-media with dit — heavy artifact; log + delete), or SeBackupPrivilege route (06 → diskshadow script class). Both are DC-impact actions → RoE approval class (05's DC rules).

### Non-LSASS credential sources (usually quieter)

- Kerberos ticket dump from LSASS (Rubeus `dump` class) → use with T1550.003 without touching hashes.
- DPAPI: user blobs (`%APPDATA%\Microsoft\Protect`), Credential Manager (vault), saved RDP, Chrome/Edge `Login Data` (T1555.003), WiFi `wlan show` XML key extraction.
- Files: `unattend.xml`, `sysprep.inf`, Group Policy XML history, KeePass config + key file paths (0-day-free: check config for embedded key material + the client's key file handling — finding class), `ConsoleHost_history.txt` (PowerShell), web.config/appsettings.json connection strings, `ScheduledTasks` XML with stored creds, `SECRETS` in CI agents on build servers.
- Linux: `/etc/shadow` sample (00 minimal-data rule), `~/.ssh/*` keys (T1552.004), agent sockets (SSH agent hijack with session access), `docker` config auth, cloud CLI caches (`~/.aws/credentials`, `~/.azure`, `~/.gcloud` — feeds 12), CI/CD tokens, disk/backup mounts.

## Credential usage (move without cracking)

| Material | Technique | Command class |
|---|---|---|
| NTLM hash | **Pass the Hash** (T1550.002) | `netexec smb <host> -u <user> -H <hash> --sam`, impacket `wmiexec.py -hashes :<hash>`, `psexec.py -hashes` |
| Kerberos TGT | **Overpass-the-hash** (TGT from key) → request tickets as user | Rubeus `asktgt /rc4:<hash> /ptt` |
| TGS/service ticket | **Pass the Ticket** (T1550.003) | export `KRB5CCNAME`, or `Rubeus /ptt` on-host |
| AES keys | Pass-the-key / overpass-the-hash with AES (RoE-friendly: modern crypto, less noisy than RC4) | `asktgt /aes256:<key>` |
| Cert (.pfx, from 05 ADCS) | Certificate auth as user | `certipy auth` / `Rubeus /ptt` cert class |

**NTLMv1 capture** (Responder from 05 + client allowing LM/Legacy): NTLMv1 crackable → equivalent of hash-reuse; `--LM/--force-lm` flags class. Finding itself (NTLMv1 allowed) is a hardening item even without crack success.

## Lateral movement (host-to-host)

### Impacket suite semantics (default toolkit)

| Tool | Protocol | Semantics | On-host artifacts (report + close-out relevance) |
|---|---|---|---|
| `psexec.py` | SMB + service | Uploads service exe via ADMIN$ share, creates service, executes, cleans | ADMIN$ write + 7045 service install (service name pattern) + dropped exe |
| `wmiexec.py` | DCOM/WMI | Executes via WMI, file-less-ish, results over SMB temp files | WMI activity + temp `.bat`/output files in ADMIN$ |
| `smbexec.py` | SMB + service | Persistent service-based semi-interactive shell | Service + recurring file writes |
| `atexec.py` | SMB + schedule | AT job (legacy scheduler) | Task creation/run/delete triple |

Artifact discipline: EVERY lateral hop writes artifacts (dropped binaries, services, scheduled tasks) → each recorded in `03-hosts/<host>/artifacts-left.md` → close-out verification sweep (15).

### Native/service-based alternatives (choose by detection posture + RoE)

- **WinRM (T1021.006):** `winrs -r:<host>` / PSRemoting `New-PSSession` — legit-admin-pattern traffic; on hosts with WinRM enabled; low-artifact.
- **WMI event/DCOM (T1021.003):** MMC20-class DCOM object → remote shell — no file drops, but WMI-activity telemetry.
- **Scheduled tasks remote (T1053):** `schtasks /s <host> /create` — needs admin + ADMIN$-adjacent rights; artifacts = task.
- **RDP (T1021.001):** legit-session class; shadow-session hijack (needs SYSTEM); logon events high-visibility.
- **SSH (T1021.004, Linux):** keys from Phase "files"; agent forwarding risks; root login policy findings.

### Password spraying — internal (T1110.003)

Internal posture differs from external (04): lockout policy readable (`net accounts` — threshold/observation-window), so spraying is controlled: 1 password/user/round, rounds spaced past observation window, all targets+results logged (`04-evidence/spray-log.md`). Spray only accounts from approved list; seasonal-password patterns + org-name variants first; netexec spray module (conformant throttle).

## Common failures / misreads

| Symptom | Misread | Reality check |
|---|---|---|
| `netexec` `[-]` on valid creds | "Creds bad" | Distinguish: bad password vs account-locked vs firewall/SMB-signing vs local-auth flag missing — read status code, not just pass/fail |
| psexec works but "access denied" on shares | "Partial admin" | ADMIN$-write is the psexec bar; share-read ≠ admin — classify precisely for the report |
| LSASS dump parses empty | "Dump failed" | PPL blocked silent-partial dump — hash the dump file, compare sizes; retry class per 10 |
| Ticket used, "KRB_AP_ERR" | "Ticket bad" | Clock skew > 5 min (check `klist`/host time — w32time drift itself is a finding), or ticket crossed trust boundary it wasn't scoped for |
| Spray yields hit then lockouts | "Scale the win" | STOP spray rounds, harvest the one account — lockout storm = 00 stop-condition |

## Detection footprint

- 4624 type 3 (network logons) with 4672 (special privileges) = lateral fingerprint; 7045 (service installs — psexec-class); 4688/Sysmon 1 (dropped tool executions); 4104 PowerShell if PS-based; 4740 (lockouts — spray); RDP 4624 type 10/4778.
- Kerberos usage anomalies: RC4 etype in 4769 when account supports AES (05); pass-the-hash = NTLM logon (4624/4776) where Kerberos would be expected — purple-team table material (15).

## Tool fallback order

- Dump: nanodump (debugger-free, low footprint) > comsvcs (native, needs SeDebug) > procdump (Sysinternals signature); off-host > on-host under hostile EDR.
- Parse: pypykatz (offline, your box) > mimikatz (on-host = loud, avoid).
- Remote exec: WinRM/PSRemoting (lowest artifact) > wmiexec > psexec (noisiest); netexec for sweep-class validation, impacket for interactive.
- Spray: netexec module (lockout-conformant) > custom scripted rounds.

## Evidence handoff

Per hop: source host → technique → target host → credential material (vault pointer, NOT the value) → timestamps (UTC) → artifacts left → kill-chain entry in attack-graph.md. Credential inventory table (user | host | type | where found | used-where | vault pointer) — the client's credential-exposure metric for the report (15). All lateral hops in the timeline table = report's movement narrative (15). Credential material found but unused = still findings (exposure class) — record all.
