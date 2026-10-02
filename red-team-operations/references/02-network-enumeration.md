# 02 — Network Enumeration & Scanning

**When to read:** After attack-surface inventory (01) identifies live IPs; at internal-network foothold (post-exploitation pivot); before choosing any exploit — service/version truth lives here.
**Prerequisites:** Authorization gate (00) satisfied for the IP block; scope re-resolved (DHCP/cloud drift check); engagement scan infra (recorded in indicator list).
**Primary ATT&CK mapping:** T1595.001 Scanning IP Blocks (external), T1046 Network Service Scanning (internal/pivot), T1018 Remote System Discovery, T1595.002 Vulnerability Scanning (vuln scanning section).

## Methodology (decision tree)

```text
Scope block confirmed
  → host discovery (cheapest: -sn sweep; ARP if L2 access)
  → TCP port scan: top-1000 first → full 65535 on interesting hosts (masscan at scale)
  → service/version + OS detection on open ports (-sV -O)
  → script-based deep-dive per service (NSE / service-specific below)
  → UDP strategy: top-50 UDP ports on key hosts (slow, targeted)
  → service-specific enumeration (route table below)
  → vuln scan (nuclei templates matched to fingerprinted versions; Nessus-class where client-provided)
  → version → CVE match (lab-validate PoC BEFORE any exploit fires — see 04)
```

**Rate discipline:** default `-T3`. `-T4/-T5` only on dedicated ranges the client was told about. Fragile targets (OT-adjacent, printers, badge controllers, old NAS) get `-T2`, low parallelism, or skip the phase — availability beats coverage (00 exclusions).

## Host discovery

```bash
# External / large blocks (ICMP+TCP-ack based, light)
nmap -sn -n -PE -PS443,80 <cidr> -oA 01-scans/hostdisc
# Local L2 segment (post-exploitation foothold) — ARP is authoritative
nmap -sn -n -PR <cidr>
nmap -sn -n --script arp-scan <cidr>     # alternate arp sweep
# Windows-quiet alternatives
for /L %i in (1,1,254) do @ping -n 1 -w 100 10.10.1.%i > nul && echo 10.10.1.%i live
```

Interpretation: firewalled hosts drop ICMP — `-PE` alone undercounts. `-PS443,80` catches ICMP-filtered web hosts. On internal sweeps, hosts that only answer ARP but no TCP are still inventory (live host, all filtered → interesting host-level finding: host firewall).

## Port scanning

```bash
# Stage 1: top-1000 TCP, SYN scan, default rate
nmap -sS -Pn -n -T3 --top-ports 1000 --open -oA 01-scans/top1k <host|cidr>
# Stage 2: full range on selected hosts
nmap -sS -Pn -n -T4 -p- --open -oA 01-scans/full <host>
# Scale: full-range large CIDR → masscan for discovery, nmap -sV for detail
masscan -p0-65535 <cidr> --rate=1000 --open-only -oG 01-scans/masscan.grep
nmap -sV -p <masscan-ports> <host>    # masscan finds, nmap characterizes (never trust masscan banners)
```

- `-Pn` on filtered hosts (avoid discovery re-send cost), but keep discovery on ranges — host inventory is evidence.
- `--open` keeps output readable; run without it only when filtered-port patterns matter (firewall rule mapping — itself a report finding).
- Windows fallback (no nmap): `Test-NetConnection <ip> -Port 443` per port; `1..1024 | % { Test-NetConnection ... }` — slow; prefer uploading static nmap or use PowerShell TCP client with timeouts (record as transfer + run — OPSEC note: file drop on foothold host is an EDR-visible action, 10).

### UDP strategy

```bash
nmap -sU -Pn -n -T3 --top-ports 50 --open -oA 01-scans/udp50 <host>
# targeted: the services that matter
nmap -sU -Pn -p 53,88,123,161,500,1900,4500,5353,11211 -sV --version-intensity=0 -oA 01-scans/udp-svc <host>
```

UDP scanning is slow and false-negative prone (`open|filtered` dominant). SNMP (161) is the highest-yield UDP service on internal nets → deep-dive below.

## Service/version + OS detection

```bash
nmap -sV -Pn -n -p <ports> --version-intensity=5 -O --osscan-guess -oA 01-scans/svc <host>
```

Expected: banner, product, version, extrainfo, CPE. **Treat every banner as a lead, not truth** — banners lie (rewritten by proxies, frozen by packaging). Cross-check: `nmap -sV` vs web headers (03) vs `whatweb`. `192.168.x` OS guess `--osscan-guess` confidence table: keep only ≥ 90% as Observed, rest Inferred.

## Service deep-dives (route table)

| Service/port | High-value checks (commands) | Routes to |
|---|---|---|
| **SMB 445** | `nmap -p445 --script smb-vuln*` (ms17-010, smb-vuln-webexec), `--script smb2-security-mode` (signing!), `netexec smb <cidr> --gen-relay-list`, `--sam --local-auth` (creds phase, 08) | 05, 08 |
| **LDAP 389/636/3268** | `nmap -p 389 --script ldap-rootdse`; anonymous rootDSE dump (naming contexts, ForestFunctionalLevel) → domain enum (05) | 05 |
| **Kerberos 88** | AS-REQ user enumeration via timing/response (`kerbrute userenum`); pre-auth discovery (05) | 05 |
| **SNMP 161** | `snmpwalk -v2c -c public <ip>` (+ community brute `onesixtyone`/`nmap --script snmp-brute`); leaks: interfaces, routes, users (`snmpwalk ... 1.3.6.1.2.1.25.2`? processes/users tables), arp tables, config strings | 02 output feeds 06/08 |
| **SMTP 25** | `VRFY/EXPN` user enum; open relay test (client-approved only — spamming third parties = out-of-scope damage, 00); `nmap --script smtp-commands` | 04 |
| **DNS 53** | zone transfer attempt (`dig axfr @<ns> <domain>` — rarely but always tested), recursion open? cache snooping (`dig +norecurse`), wildcard test (01) | 01, 04 |
| **WinRM 5985/5986** | port + banner; valid-credential check belongs to 08 | 08 |
| **MSSQL 1433** | `nmap --script ms-sql-info,ms-sql-empty-password`; SA default creds; `sqsh`/`mssqlclient.py` post-cred (08); xp_cmdshell chain | 08 |
| **Redis 6379** | unauth access (`redis-cli -h <ip> ping` → PONG), `CONFIG GET *` → webshell via `SET`+`CONFIG SET dir` chain, `redis-rogue-getcom`? (lab-validate the module load — crash risk) | 06 (privesc via service account) |
| **Memcached 11211** | unauth stats/dump (sensitive session/data leak finding) | report finding |
| **FTP 21** | anonymous login (`ftp> anonymous:anonymous`), writable dirs (`nmap --script ftp-bounce,ftp-anon,ftp-syst`), bounce scan (old finding) | 04 |
| **NFS 2049** | `showmount -e <ip>`; mount exports with `no_root_squash` → root file write finding (mount from foothost, lab-test first) | 07 |
| **RDP 3389** | `nmap --script rdp-ntlm-info` (domain/host/NTLM info), restricted-admin mode notes (08), NLA state | 08 |
| **SSH 22** | version→CVE match; auth methods; key reuse (`ssh-keyscan` → compare known host keys → asset attribution finding) | 08 |
| **IPMI/BMC 623** | `ipmitool -I lanplus -H <ip> -U '' cipher 0 su` default; BMC default creds table (vendor matrix); + BMC-specific CVEs (lab-first — crash bricks hardware) | 06 (BMC→host) |
| **K8s 6443/10250/2379** | anonymous API, kubelet read endpoints, etcd exposure | 13 |
| **DB generic (Oracle 1521, MySQL 3306, PG 5432, Mongo 27017, Elastic 9200)** | default/unauth checks per product; snapshot exposure via `nmap --script <prod>-*`; data-minimal proof (00: no bulk data touch) | 08 |
| **Unknown/custom TCP (game servers, proprietary backends, custom framing — any high port)** | gentle framing probes only (empty/garbage, single connections — no storms); version-pin from error strings; protocol RE/fuzzing workflow next | 16 |

## Vulnerability scanning

```bash
# Version-matched template scan on fingerprinted services (targeted > blanket)
nuclei -l live-urls.txt -t cves/ -severity critical,high -o 01-scans/nuclei.txt
nuclei -l live-urls.txt -tags exposure,misconfig -o 01-scans/nuclei-exp.txt
# auth'd web scanning only with client-provided creds (scope)
```

- Blanket `-t all` wastes hours, buries signal, and generates alert storms (00 indicator discipline). Match templates to the fingerprinted stack (01).
- **False-positive triage rule:** nuclei "critical" without exploitability context is a lead. Verify by: version truth (cross-checked banner), vulnerable code path reachable (config-dependent), and where possible a non-destructive decisive test. Never report CVE from banner match alone as Observed; label Inferred with the exact evidence.
- Nessus/Greenbone-class: client-provided, configured, and preferably client-run (their infra, their data). You interpret, they execute — cleanest RoE posture.

## Internal vs external differences

- **External:** only exposed services matter; focus 02 output into 04 (edge exploitation) + 03 (web apps). Firewall-diff = "what the client thinks is exposed vs what is" — table of exposed services not in the client's asset list is a first-page report finding.
- **Internal (from foothold):** `-sn` ARP sweeps + SMB/LDAP/SNMP enumeration dominate; this is AD attack-path fuel → 05. Scan from foothold host with engagement-approved tooling (10: transfer discipline — Ingress Tool Transfer T1105 is EDR-visible).

## Common failures / misreads

| Symptom | Misread | Reality check |
|---|---|---|
| `open|filtered` UDP | "Open, vulnerable" | UDP needs protocol-specific probe; report as unverified |
| Banner version X | "CVE-Y applies" | Packaging backports (Debian/Ubuntu keep version, patch code); check package-changelog evidence or decisive test |
| SYN scan stall on one host | "Weird host" | IPS rate-shaping; slow down or skip — hammering escalates to a block (and burns infra) |
| masscan finds port, nmap sees closed | "Nmap broken" | masscan SYN backlog false positives; trust nmap |
| SMB `signing: False` | "Just an info note" | It's the relay prerequisite (05) — inventory it for ntlmrelayx targets |
| Printer/NAS old firmware "CVE" | "Exploit it" | Fragile targets — crash = availability incident (00); passive-only or client-approved window |

## Detection footprint

- IDS/IPS sees scan patterns (single-source bursts); edge WAF sees web scan UAs (route 03 discipline).
- Internal scans are the most-alerted red team action — 4624/5145 correlation, EDR network telemetry on foothold host. Space internal sweeps, use `-T2`, prefer credentialed/AD-based enumeration (05) over blanket SMB sweeps when possible.
- All scan source IPs already declared in indicator list (00). Scans from undeclared infra = deconfliction incident.

## Tool fallback order

- Port scan: nmap (detail) > masscan (speed, discovery only) > PowerShell TCP probes (Windows-native fallback).
- SNMP: snmpwalk > nmap snmp-* scripts > onesixtyone (brute).
- SMB: netexec > nmap smb-* > smbclient manual.
- Vuln: nuclei targeted > Nessus-class client-run > manual decisive test.

## Evidence handoff

- `-oA` output (nmap/masscan) into `01-scans/` + inventory table update: host | ports | service/version | OS guess | signing/flags | route decision.
- Exposed-service-vs-client-asset-list diff → report finding (goes to `02-findings/F-XXX`).
- Every service deep-dive result that feeds an exploit (04/05/06/08) cites the scan artifact filename — chain of evidence for the report (15).
