# 01 — Recon & OSINT (Attack Surface Mapping)

**When to read:** At external engagement start; whenever a new domain/subsidiary/cloud tenant is discovered; when a finding needs "what else exists like this" context. Passive phases produce zero target-side telemetry; active phases here require the authorization gate and route to `02`/`03`.
**Prerequisites:** Authorization gate satisfied (00); target domain / org name from scope list.
**Primary ATT&CK mapping:** T1593 Search Open Websites/Domains (T1593.002 Search Engines, T1593.003 Code Repositories), T1596 Search Open Technical Databases (T1596.001 DNS/Passive DNS, T1596.002 WHOIS, T1596.003 Digital Certificates), T1589.002 Gather Victim Identity Info: Email Addresses, T1592 Gather Victim Host Info, T1591 Gather Victim Org Info, T1595.003 Wordlist Scanning (active content discovery).

## Methodology (decision tree)

```text
Root assets (WHOIS/NS/DNS)
  → subdomain enumeration (OSINT sources FIRST: CT logs, passive DNS, engines)
  → resolution + liveness (httpx)          [no packets to target yet]
  → fingerprint (tech, headers, favicon, cookies)
  → asset classification:
      CDN/WAF fronted? ──yes──→ find ORIGIN, mark CDN nodes as do-not-scan (shared infra, out of scope)
      |                        └── brute origin via CT history, DNS records, misconfig headers
      cloud storage? (S3/azure/gcs) → takeover check (dangling CNAME / unclaimed bucket)
      code leaks? → credential/config discovery (trufflehog/gitleaks)
      people? → email format + phishing target list (feeds 04)
  → ATTACK SURFACE INVENTORY table (the deliverable of this phase)
```

**Ordering rule:** cheapest-and-silent first. Every active step (DNS bruteforce, content discovery, origin probing) is a scan under T1595 and takes the gate again.

## Phase A — passive mapping (no packets to target)

### A1. Root assets and organizational boundaries

```bash
whois <domain>                        # registrar, creation date, registrant org, name servers
dig NS <domain> +short                # authoritative NS — clustered hosting (e.g., awsdns) tells hosting provider
dig MX <domain> +short                # mail provider (Google/M365/on-prem Exchange → phishing relevance)
dig TXT <domain> +short               # SPF/DKIM/DMARC + verification records (Zoho, Atlassian, cloud tenants)
```

Expected/interpretation:

- `whois` registrant org ≠ client legal name → subsidiary/holding pattern; each discovered org entity must be checked against the scope list before anything else (00).
- SPF ending `-all` (hard fail) + DMARC `p=reject` → domain spoofing hard; `~all` + `p=none` → spoofable-domain risk finding for the report (feeds 04 phishing feasibility and a finding on email hardening).
- TXT records leak SaaS footprint: `google-site-verification`, `MS=ms…` (M365), `atlassian-domain-verification`, `Zoho` → tenant names for 12 (cloud phase).

**OPSEC:** whois/DNS queries hit registrars/resolvers, not the target's infra. Fine to run from engagement infra; still log commands.

### A2. Subdomain enumeration (OSINT-first order)

Tool fallback order: **certificate transparency + passive DNS (crt.sh / censys) → subfinder/assetfinder (multi-source APIs) → amass intel -passive (thorough, slow) → dnsgen permutations → validated with dnsx**. Active brute (amass enum -active, shuffledns) is Phase B (gate).

```bash
# CT logs (the highest-yield single source)
curl -s "https://crt.sh/?q=%.<domain>&output=json" | jq -r '.[].name_value' | sort -u > ct-subs.txt

# Multi-source passive aggregation
subfinder -d <domain> -all -silent >> subs.txt
assetfinder --subs-only <domain> >> subs.txt
amass intel -d <domain> -passive >> subs.txt        # heaviest, run once

# Permutation/enrichment (catches dev/staging naming)
cat subs.txt | dnsgen - | dnsx -silent -a -resp >> resolved.txt   # also answers wildcard test below
```

Expected/interpretation:

- CT log noise: wildcard certs (`*.<domain>`) return hundreds of random subdomains — filter. Wildcard DNS test: `dig <random-string>.<domain>` → answers → wildcard zone; subdomain results from bruteforce must be re-tested against a random control (common misread).
- High-value naming patterns for the inventory: `vpn`, `rdp`, `citrix`, `owa`, `mail`, `dev`, `staging`, `test`, `uat`, `jenkins`, `git`, `admin`, `backup`, `internal`, `storage`, `sso`, `idp`, `dashboard`.
- Historical subdomains in CT that no longer resolve → check dangling DNS/CNAME → takeover candidates (A4).

### A3. Liveness + fingerprint (no target-side alerting beyond normal web hits)

```bash
dnsx -l subs.txt -silent -a -resp                       # resolve; drop non-resolving
cat resolved.txt | httpx -silent -title -tech -w "\n"    # live HTTP/HTTPS + title + tech fingerprint
cat resolved.txt | httpx -silent -status-code -content-length -no-color -ports 80,443,8080,8443
```

Interpretation: `httpx -tech` (Wappalyzer signatures) + title triage: admin panels, "Index of /", default credentials pages, infrastructure portals (printers, iLO/DRAC, IPMI) go to the priority queue for 02/03.

Fingerprint refinement (only against in-scope live hosts — this is active):

```bash
whatweb -a 3 https://<host>                             # framework/plugin versions
curl -skI https://<host> | sed -n '1,30p'               # headers: Server, X-Powered-By, CSP, cookies
# favicon hash → match against known product/favicon DBs (Shodan: http.favicon.hash:<n>)
curl -s https://<host>/favicon.ico | python -c "import sys,mmh3,codecs; print(mmh3.codecs...)"; # mmh3 base64 → favicon hash for Shodan correlation
```

Cookie reading table (high-signal): `JSESSIONID` Java/Tomcat; `csrftoken` Django; `laravel_session` Laravel; `bigipserver` F5; `AWSELB` AWS ELB; `XSRF-TOKEN` modern SPA; `ASP.NET_SessionId`+`__VIEWSTATE` IIS ASP.NET; `ASPXAUTH` forms auth.

### A4. Takeover checks and cloud asset footprint

```bash
# dangling CNAME detection
cat subs.txt | dnsx -silent -cname -resp | grep -Ei "cloudfront|herokuapp|github.io|azurewebsites|trafficmanager|aws-api|elasticbeanstalk|zendesk|shopify"
# resolved-but-dead (NXDOMAIN of provider) + takeover service mapping = reportable finding
# S3/azure/gcs enumeration
cloud_enum -k <keywords> -t 5                # or s3scanner, GCPBrute — check provider existence + ACL
python -m s3scanner scan --provider-file s3-buckets.txt   # existing-bucket discovery, then ACL audit (auth'd GETs are active → gate)
```

Takeaway table for report: `dangling CNAME to takeoverable service` = finding (unauthorized-takeover class). Existing cloud storage with public-list or public-read on non-public data = finding; capture proof listing only (minimal data exposure rule, 00).

### A5. Code leak hunting (T1593.003)

```bash
# live repos (org/employee)
gitleaks detect --source https://github.com/<org> --no-banner
trufflehog github --org=<org> --only-verified          # verified working secrets, lower false positives
# repo-level dorking (manual, via API to avoid triggering abuse detection)
#   in:file filename:.env | .npmrc | id_rsa | .aws/credentials | ".git/config" | WEB-INF
#   "org:<client>" password / smtp / PRIVATE KEY / BEGIN RSA / api_key
# exposed .git on web servers (active GETs → gate): 
ffuf -w subs.txt:HOST -u https://HOST/.git/HEAD -mc 200 -mr "ref:"
```

Interpretation: verified secret in code → do NOT use it live without re-authorization decision (using leaked prod credentials can cross RoE action classes — log, ask, then use). `.git/HEAD` readable → directory listing of `.git/` → full source + config → finding + feeds 03.

### A6. People / email infrastructure (feeds 04 phishing)

- Email format discovery: `hunter.io`-class sources or manual sampling from public PDFs/press releases (`firstname.lastname@`, `f.last@`, `flast@`).
- Employee role mapping (LinkedIn) → phishing pretexts, priority targets with published roles in finance/HR/helpdesk (04).
- Breach data: **RoE-gated.** Only sources the client provides or approves (their own breach corpus, privileged feeds). Downloading random dump collections is often illegal regardless of RoE — refuse and note it.
- M365/Google tenant enumeration (active — gate): user existence via auth endpoints response-timing/content differences; feed to 12 if cloud-scoped.

### A7. Public-document metadata

```bash
# Google dork set (engine = third party; target sees nothing)
#   site:<domain> (filetype:pdf | filetype:docx | filetype:xlsx | filetype:pptx)
#   site:<domain> inurl:admin | inurl:login | inurl:dashboard | inurl:backup
#   site:files.<domain> | site:ftp.<domain>
metagoofil -d <domain> -t pdf,docx,xlsx -l 50 -o meta/
exiftool -r meta/ | grep -Ei "Author|Creator|Email|@|Path|Software"
```

Metadata yields: internal usernames (`DOMAIN\jsmith`), internal fileserver paths (`E:\...`? no — `\\file01\finance\…` shares), internal software/version disclosure → seeds 02 internal scan, 04 pretexts, 08 credential targets.

## Phase B — active external (requires gate; routes onward)

- DNS bruteforce against authoritative NS (`amass enum -active`, `shuffledns`): T1595-class scanning of target DNS servers.
- Content discovery on in-scope web roots: route to `03` (it owns web methodology).
- Port/origin scanning: route to `02`.

## Common failures / misreads

| Symptom | Misread | Reality check |
|---|---|---|
| Hundreds of "subdomains" found | Asset growth | Wildcard DNS/CERT — random-control test before inventory |
| Host resolves to CDN IP | "In scope, will scan" | CDN shared nodes are likely NOT client-owned — find origin; scanning CDN hits out-of-scope third parties |
| CT-log host not resolving | "Dead, ignore" | Check dangling CNAME → takeover finding |
| GitHub dork hit | "Client code leak" | Often mirrors of public docs or vendor code — verify author/org before reporting |
| SPF `~all` | "Email protected" | Soft-fail usually unenforced — spoofable domain, finding |
| `httpx -tech` says WordPress | "Definitely WP" | Verify with a second signal (login page, `/wp-content/`) — tech fingerprints mislabel proxies/gateways |

## Detection footprint (what the client sees)

- Phase A: **zero target-side telemetry** (registrars, CT logs, Shodan are third parties). Their public-site web analytics may see your browsing hits — keep browsing light, no automation hammering.
- Phase B: DNS query bursts to their NS; web-server logs get your `httpx`/`whatweb` UA hits. Use engagement infra (recorded in indicator list, 00) — never personal IP.

## Tool fallback order

- Subdomain enum: CT logs (crt.sh/censys) + subfinder → assetfinder → amass intel (slowest, most complete). Validate resolution always with dnsx.
- Fingerprint: httpx -tech → whatweb -a 3 → manual header/cookie read.
- Secret scanning: trufflehog --only-verified → gitleaks.
- Cloud: cloud_enum → provider-specific (s3scanner / AzAdvertizer-style tooling for Azure).
- If a source API is rate-limited/dead: rotate to the next in order; never retry-storm (abuse detection gets your engagement infra blocked, and looks like an attack).

## Evidence handoff

Deliverable = **Attack Surface Inventory** (00-recon/attack-surface.md):

```markdown
| host/IP | origin? | tech | classification | exposure notes | routes to |
|---------|---------|------|----------------|-----------------|-----------|
```

Feeds: `02` (live origins/IPs to port-scan), `03` (web app roots, API surfaces), `04` (phishing target list, email feasibility), `12` (cloud tenants/buckets), `15` (recon findings: takeover, spoofable email, public secrets).
