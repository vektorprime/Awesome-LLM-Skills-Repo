# Host Fingerprint Template (run on EVERY new shell/foothold)

Store per host in `03-hosts/<host>/fingerprint.md`. Rerun the OS-class column set at each new
session (state drifts). UTC timestamp every capture. Everything here is READ-ONLY
enumeration (no state change — no action-class escalation needed beyond current access).

## Common header

```markdown
# Host fingerprint — <hostname> (<ip>)
- UTC captured: <ts>     | Access context: <how/what level> (from phase X)
- Case: <case-id>        | RoE citation: <scope entry this host matches> (00)
- Roles observed: <workstation/server/DC/app/edge/etc>
```

## Windows column set

```cmd
hostname & whoami /all & ver
systeminfo                                          :: OS build (potato/UAC validity — 06), patch state
net user & net localgroup administrators & net group /domain 2>nul
tasklist /v & net start
netstat -ano | findstr ESTABLISHED                  :: reachability map (02 route / 08 lateral)
wmic qfe get HotFixID,InstalledOn                    :: patch-gap evidence (CVE matching — 04)
whoami /priv                                        :: token table (06's escalation decision)
reg query HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run
dir /a C:\ & dir "C:\Program Files"                  :: software inventory (exploit surface)
schtasks /query /fo LIST /v                          :: scheduled-task surface (06/09)
sc query state= all                                 :: services inventory
:: EDR posture (10's posture decision):
tasklist | findstr /i "<edr-process-patterns>"
:: + Defender state, PowerShell CLM check, LAPS presence, domain-join state
```

## Linux column set

```bash
hostnamectl; uname -a; cat /etc/os-release; id
sudo -l 2>&1                                        # THE sudo surface (07's decision table)
ps aux | head -30; ss -tulpn
ls -la /home/ /root/ /opt/ /var/backups/ 2>/dev/null
find / -perm -4000 2>/dev/null | sort               # SUID inventory (07)
getcap -r / 2>/dev/null                             # capabilities (07)
crontab -l 2>/dev/null; ls -la /etc/cron*           # cron surface
cat /etc/passwd | cut -d: -f1,3,7 | head -30        # users + shells
:: container check (13's Phase 0): /proc/1/cgroup, /.dockerenv, K8s SA token
:: EDR/audit posture: ps for agents, auditctl -l, /etc/audit/ rules
```

## Both platforms — the reachability map (feeds the attack graph)

```text
Interfaces/subnets visible from here → new scope-check targets (00: in scope? re-resolve)
New services seen from here (differ from 02's external view) → 02-internal route
Cred material visible from here (07's Phase 6 / 08's files classes) → vault pointers
Persistence already present (misconfig'd legit persistence = finding + 09's surface)
```

## Classification output (fingerprint's job)

```markdown
- Host class: <DC/server/workstation/app/db/edge/appliance/container>
- Privilege context: <user/service/SYSTEM/root/container>
- Escalation candidates (per 06/07 tables): <list with confidence>
- Lateral targets visible: <hosts/services (scope-checked)>
- EDR posture: <none/detected-quiet/detected-hostile — 10's route decision>
- Artifacts so far (this phase left): <list — the artifacts-left seed>
```
