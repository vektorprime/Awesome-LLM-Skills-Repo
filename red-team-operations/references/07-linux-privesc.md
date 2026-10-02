# 07 — Linux Privilege Escalation

**When to read:** On any Linux foothold (user context shell — from 04/08/13); when `sudo -l` output exists; when SUID/capability findings appear in enumeration; before any container-escape decision (routes to 13).
**Prerequisites:** Shell on in-scope Linux host; host fingerprint run first (checklists/host-fingerprint.md); action class ESCALATE approved.
**Primary ATT&CK mapping:** T1548.001 Setuid and Setgid (SUID abuse), T1068 Exploitation for Privilege Escalation (kernel), T1548.002 abuse of sudo misconfigurations, T1574.007 PATH Environment Variable Hijacking (path interception class), T1053.003 Cron (cron abuse class), T1552.003 Unsecured Credentials: Bash History (credential hunting class), T1552.004 Private Keys (ssh keys).

## Methodology (decision tree)

```text
Fingerprint (kernel version — decides kernel-exploit validity; distro/package state)
  → sudo -l FIRST (cheapest, highest yield)
  → SUID/SGID inventory → classify (GTFOBins-class known tools vs custom binaries)
  → capabilities inventory
  → cron/systemd/service writable targets
  → credential artifacts (history/keys/configs)
  → PATH/env injection points (sudo scripts calling relative binaries)
  → container context? → docker/podman group, container runtime = route 13
  → kernel exploit LAST (crash rule)
```

## Phase 1 — Context enumeration

```bash
uname -a && cat /etc/os-release && id && hostnamectl
sudo -l                           # THE command — read its output surgically (below)
sudo -V | head -1                 # sudo version — vuln era map (Baron Samedit-class, etc.)
find / -perm -4000 -type f 2>/dev/null | sort          # SUID
find / -perm -2000 -type f 2>/dev/null | sort          # SGID
getcap -r / 2>/dev/null                                  # capabilities
ls -la /etc/cron* /var/spool/cron/crontabs/ 2>/dev/null
systemctl list-timers --all
env | grep -Ei "path|ld_"      # env injection points
find / -writable -type d 2>/dev/null | grep -Ev "^/proc|^/sys|/tmp"    # world-writable dirs (outside tmp)
find / -writable -type f 2>/dev/null | grep -Ev "^/proc|^/sys"         # world-writable files
```

Full fingerprint template in `checklists/host-fingerprint.md`.

## Phase 2 — sudo misconfigurations (read `sudo -l` like a table)

| `sudo -l` shows | Escalation class |
|---|---|
| `NOPASSWD: <known binary>` | Direct GTFOBins-class shell escape (`sudo <bin> <escape-args>`) — known-tool table lookup |
| `NOPASSWD: <script>` (custom) | Read the script: relative binaries? → PATH hijack (Phase 5); dangerous args? → injection |
| `SETENV:` | `sudo <bin>` with env override → `LD_PRELOAD`/`LD_LIBRARY_PATH` (Phase 5b) |
| Wildcards in commands (`sudo tar ...*`) | Wildcard injection (Phase 5c) |
| `sudoedit` allowed | Version check → known sudoedit shell escapes (era table) |

`sudo -l` output IS evidence — screenshot/record verbatim (15 severity input: "unrestricted root shell via misconfigured sudo" is a critical finding).

## Phase 3 — SUID/SGID classification

1. Compare SUID list against the known GTFOBins-class table (find, vim, nmap-era, bash, env, tee, time, wget-class...). Each match → documented escape command → root shell → evidence.
2. **Custom SUID binaries** (not in any table) → route to reversing (see `reverse-engineering-executables` skill — full static/dynamic protocol): look for `system()`/`popen()` calls with controllable strings, file ops with user-controlled paths, `dlopen` user paths. Never "run it and see" — custom SUID = analyze-first, run-under-controlled-context after.
3. SUID on interpreters (perl/python/php/node) → documented `-e`/`-c` escape classes.
4. SGID group-interesting (sudo, shadow, docker groups — docker group = host root via runtime → 13).

## Phase 4 — Capabilities

```bash
getcap -r / 2>/dev/null
```

High-yield table: `cap_setuid` (setuid processes — direct root), `cap_dac_override` (read/write any file — shadow/keys), `cap_sys_admin` (mount namespaces, container escape class → 13, kernel-module paths), `cap_setpcap` (capability re-arrangement), `cap_net_raw` (packet injection/sniffing class → 14 wireless/adjacent). Each → documented chain + evidence capture.

## Phase 5 — Injection classes (service/scheduled context)

- **PATH hijack:** sudo-run (or cron-run) script calls `binary` unqualified → export PATH with your dir first containing same-named shell-spawning fake → root execution. Verify with `sudo -l` script read first (Phase 2) — never assume.
- **LD_PRELOAD/LD_LIBRARY_PATH:** valid when `sudo -l` shows SETENV or `/etc/sudoers` has env_reset off; preload .so with constructor → root context execution.
- **Cron wildcard injection:** root cron tar/rsync/cp with `*` args in user-writable dir → argument injection (`--checkpoint=1 --checkpoint-action=exec=...` for tar class; `--use-compress-program` equivalents for others). Build payload file with safe name, verify cron runs it (log watch), capture evidence.
- **Writable cron scripts/systemd units/timers:** direct content modification → but that's an artifact-modification class → log original content + restore (15). Writable systemd unit → unit file with `ExecStart=/bin/...` root context; `systemctl daemon-reload` requirement noted.
- **PATH-writing via writable /etc files:** writable `/etc/profile`, `/etc/bash.bashrc`, `/etc/ld.so.preload` (system-wide preload — every root process loads it — powerful but noisy; artifact-log + restore mandatory).

## Phase 6 — Credential artifacts (often faster than escalation)

```bash
grep -REi "passw|secret|token|key" /home/ /root/ /opt/ /var/backups/ 2>/dev/null | grep -v Binary | head -50
cat ~/.bash_history ~/.mysql_history 2>/dev/null | grep -Ei "ssh|passw|sudo|mysql" 
find / -name "id_rsa" -o -name "*.pem" -o -name "authorized_keys" 2>/dev/null
ls -la /var/backups/                       # unattended configs, key backups
cat /etc/shadow 2>/dev/null                # readable shadow = finding + crackable hashes (00 data-minimal: copy hash sample only, not whole file)
grep -REi "password" /etc/ 2>/dev/null | grep -v "^Binary" | head -30
```

SSH keys (T1552.004): readable private keys → lateral movement (08) + finding (unprotected key material). Shadow-readable: hash-sample evidence only (00 minimal-data rule), crack offline (hashcat -m 1800 sha512crypt/$6$) → 08.

## Phase 7 — Kernel exploitation (LAST — crash rule)

- `uname -r` → era table: DirtyPipe-class (5.8–5.16.11 range), older DirtyCOW (pre-4.13-ish), and current-era entries — each with crash-risk label.
- **Read-only primitives preferred when available** (copy `/etc/passwd`-adjacent via pipe-class bugs over corruption-class).
- Kernel exploit = crash risk = RoE gate + client window + host-reboot plan (00). A crashed prod host without a documented window is an incident, not a finding.

## Common failures / misreads

| Symptom | Misread | Reality check |
|---|---|---|
| `sudo -l` requires password | "No sudo rights" | Password unknown ≠ no rights; if you have the password later, re-check |
| SUID on GTFOBins tool | "Root instantly" | Version/build flags matter (nmap --interactive removed in modern builds) — test the exact documented escape |
| World-writable /etc/passwd | "Append root line" | That's an ARTIFACT change — log + restore (15); also root-owned but group-writable is different finding class |
| Cron runs `bash /root/script.sh` | "Can't touch" | Read it — relative paths INSIDE root scripts still hijackable via PATH if sudo/env allows — chain check |
| getcap empty | "No cap abuse" | Check for ambient/inheritable via `capsh --print` context (esp. in containers → 13) |

## Detection footprint

- auditd (if configured): sudo invocations logged per-user; PATH/exec anomalies in audit trail.
- `.bash_history` = your own evidence trail — but ALSO the defender's (post-compromise IR sees everything typed — per 00 engagement-log discipline: assume host IR reads your session).
- Cron modifications: file-mtime + syslog entries (CRON job run lines). LD_PRELOAD-wide (/etc/ld.so.preload) is trivially detectable — high-noise; use only with RoE coverage.

## Tool fallback order

- Enumeration: manual command set (above) > linux-exploit-suggester-class scripts (on-host file drop — EDR-visible, 10 posture decision) > linPEAS-class (same caveat).
- Custom SUID: `reverse-engineering-executables` skill full protocol (static-first).
- Kernel: read-class primitive > corruption class; matched-version lab first.

## Evidence handoff

Per escalation: before/after `id` screenshots (UTC clock, 00), exact commands, every file modified logged with original content for restore (15). Sudo/SUID/cap misconfigs = the findings (client hardening items); escalation = impact proof. Credential artifacts → vault + 08 (reuse) + 15 (finding writeup). Container-context discoveries (docker group, cap_sys_admin in container) → route 13 with context notes.
