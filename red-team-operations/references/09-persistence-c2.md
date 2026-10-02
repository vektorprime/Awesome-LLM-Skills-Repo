# 09 — Persistence & Command and Control

**When to read:** After foothold when surviving reboots/logons is RoE-approved and engagement-justified (persistence is usually gated — see 00 action class PERSIST); any C2 infrastructure design/deployment; callback/egress troubleshooting.
**Prerequisites:** Action class PERSIST explicitly approved per host (00 default: restricted); infrastructure plan (domains, redirectors, listeners) deployed and recorded in `05-infra/`; indicator list (00) updated with every callback domain.
**Primary ATT&CK mapping:** T1547 Boot or Logon Autostart Execution (T1547.001 Registry Run Keys / Startup Folder, T1547.009 Shortcut Modification), T1053 Scheduled Task/Job (T1053.005 Scheduled Task), T1543.003 Windows Service, T1546 Event Triggered Execution (T1546.003 WMI Event Subscription, T1546.013 PowerShell Profile, T1546.008 Accessibility Features), T1574.001 DLL Search Order Hijacking (persistence use), T1098 Account Manipulation (new accounts, T1136 Create Account), T1136.001 Local Account, T1218.011 System Binary Proxy Execution: Rundll32 (C2 execution class), T1071.001 Application Layer Protocol: Web Protocols, T1090.001 Internal Proxy / T1090.002 External Proxy, T1573 Encrypted Channel, T1104 Multi-Stage Channels, T1571/T1572 protocol classes.

## Persistence decision tree (Windows)

```text
RoE class PERSIST approved per host?
  → What survives? (reboot / logoff / password reset of compromised user?)
      reboot-survival needed?  → service/task/registry autorun class
      user-password reset?    → machine account / other-user material / ACL-based (not tied to user password)
      DC/domain level?        → route to 05 Phase 7 (domain-class persistence — separate approval class)
  → Stealth tier: (client asked for stealth test? default: LOW-noise persistence, findable by their stack)
  → EVERY mechanism = artifact-left inventory entry (15 close-out removal verification)
```

## Windows persistence catalog (selection by tier)

| Tier | Mechanism | Artifact to log (15) |
|---|---|---|
| Loud/simple | Registry Run key (HKCU/HKLM `...\CurrentVersion\Run`), Startup folder LNK (T1547.001) | key path + value, LNK file |
| Service | New service or binPath hijack (T1543.003) | service name, config, dropped exe |
| Scheduled task (T1053.005) | `schtasks /create /sc onstart /sc onlogon /ru SYSTEM` variants + trigger time-matched to engagement window | task name, action binary |
| WMI event subscription (T1546.003) | `__EventFilter` + `__EventConsumer` (CommandLineEventConsumer) + `__FilterToConsumerBinding` | all three object names (deletion requires all) |
| DLL search order hijack (T1574.001) | dropped DLL in app dir ahead of system32 for auto-starting app | dropped DLL path |
| COM object hijack (T1546) | InProcServer32 registry rewrite to your DLL for legit CLSID (e.g., shell extension classes) | CLSID, original value (restore = exact) |
| Winlogon/IFEO (T1546.012) | Helper/Debugger value rewrite | key, original value |
| Account class (T1136/T1098) | New local admin account — HIGH visibility (new-account events), usually client-detected fast; use only as detection-test | account name (close-out: disable+delete) |
| Credential-independent | Machine account material (password rotation risk — route 05), silver-ticket service access (route 05 Phase 7) | — (05 evidence rules) |

**Selection rules:** prefer reboot-survival + password-reset-survival mechanisms when engagement length demands it (multi-week engagement: user password WILL rotate — persistence tied to user password dies with it). Prefer LOW-noise by default (the goal is testing their control stack, not winning hide-and-seek forever — RoE's detection objectives matter more, 00). WMI-subscriptions are the highest-yield stealth tier but hardest to clean (three objects must all go — verify with `Get-WmiObject`/`Remove-WmiObject` triple check at close-out).

## Linux persistence catalog

| Mechanism | Class | Artifact |
|---|---|---|
| Cron (`/etc/cron*`, `crontab -l`) + at jobs | T1053.003 | entries |
| systemd unit/timer (`/etc/systemd/system/*.service`) | T1543.002 | unit file (content logged for restore) |
| Shell rc (`~/.bashrc`, `/etc/profile`) | T1546.004 | appended lines |
| SSH authorized_keys (new key — doesn't need password rotation) | T1098.004 | key fingerprint |
| ld.so.preload | system-wide library preload — NOISY (every process) | preload entry |
| Package-manager hooks (apt DPkg hooks class) | rare tier | hook file |

Password-rotation survival: SSH key/cron-root (not tied to user password) vs shell-rc (tied to account).

## C2 infrastructure design

### Architecture (defense-in-depth for YOUR infra)

```text
implant → CDN/cloud-front domain (allowed-category) → redirector (nginx/Caddy mod-rewrite,
          engagement-owned VPS, no implants touch it directly) → team server (never
          directly internet-facing; allowlist only redirector IPs)
```

- **Redirectors** strip/forward; compromise of a redirector ≠ compromise of team server. Team server egress-allowlist to specific C2 egress (kills reverse-engineering callbacks).
- **Domains:** engagement-purchased, category-aligned (cloud/CDN/SaaS-look-alike classes score better than random VPS IPs), SPF/DKIM set, age if timeline allows. ALL domains in indicator list (00) + `05-infra/`.
- **Certificate discipline:** per-domain TLS, never reuse client's real certs (impersonation legality line — 00), never wildcard across engagement phases.
- **Segmentation:** phishing infra (04) ≠ C2 infra ≠ scanning infra — 00's separation rule (client blue team burns one = you keep the others).

### Egress decision tree (host with implant)

```text
Outbound HTTPS allowed (proxy-inspected?) → mimic-allowed SNI/category, malleable HTTP(S) profile
Only DNS out?            → DNS tunnel class (slow, high-visibility in DNS logs — client-alerting risk)
Only ICMP out?           → ICMP tunnel (rare, last-resort, rate-limited)
Domain fronting/CDN allowed? → CDN front (allowed-category SNI + host-header routing)
Air-gapped/monitored?    → NO C2 — scheduled-task exfil-window class instead (RoE-designed)
```

### Framework tradecraft (tool-neutral posture rules)

| Concept | Rule |
|---|---|
| Staging | Stageless preferred (stager URLs = 1-request block-kill for whole campaign) |
| Sleep/jitter | Engagement-tuned (short during active ops, long during dormancy; sleep inactivity kills some analyst-velocity detections) |
| Profile (malleable class) | Match observed client egress profile (from 02/03 fingerprinting of THEIR real traffic patterns — not generic "chrome-like") |
| Implant naming | Engagement-marked (helps client IR distinguish you from real attacker — 00 deconfliction) |
| File drops | Minimal + logged; every dropped binary = artifact-left (15) |
| Memory-resident | Preferred where RoE detection testing wants it (and where close-out can verify clean exit) |
| P2P/star topologies | Multi-host engagements: chain through internal relay implants (egress only from one) — matches legit-admin pattern better |

**Tool selection (fallback order):** Sliver (open, multi-OS, per-implant profiles) > Mythic (payload-type variety, strong API) > client-provided/preferred framework (some engagements require THEIR stack for purple-team value — the client's detection stack is tuned to what they expect you to use; ask). Raw tooling-only mode (no framework) for tiny engagements: impacket + SSH + scheduled tasks suffice and leave least infra.

## Callback operations discipline

- Every callback = potential client-detection event. Pre-define what happens on suspected burn: report window (purple: immediately, red: at daily sync per RoE), implant retirement protocol (exit + artifact sweep attempt + note in engagement log).
- **Never C2 into out-of-scope hosts by accident:** implant config reviewed against scope list before ANY deployment; DHCP drift re-check (00).
- Callback domains: add to indicator list the MOMENT first used (retroactive discovery of undeclared callback infra = deconfliction incident, 00).

## Common failures / misreads

| Symptom | Misread | Reality check |
|---|---|---|
| Implant beacons, no tasking works | "Broken implant" | Egress asymmetry: callback out OK, tasking blocked by inspection proxy — check both directions |
| Persistence "survives" test reboot | "Done" | Logon-survival ≠ reboot-survival ≠ password-rotation-survival — test the survival CLASS the engagement needs |
| WMI sub deleted, still triggering | "Cleanup bug" | Three objects (filter/consumer/binding) — deleted only two |
| C2 dies after engagement day 3 | "Client blocked it" | Cloud rate-limit/domain reputation kill — check YOUR infra before blaming theirs |
| New admin account not noticed | "Stealth great" | Their IAM just doesn't alert (that's the finding) — don't celebrate, document the control gap |

## Detection footprint

- Autoruns-class scanning surfaces everything (their IR/hunting maturity test); sysmon 11/13/7/3 events map to each mechanism tier (purple-team table — 15).
- Service/task/persistence events: 7045, 4697/4698 (task), WMI-activity/5857-class, 4720 (account) — the client's telemetry per mechanism = the detection-coverage appendix rows.
- C2: netflow/SNI logging, DNS query logs (DNS-tunnel class = high-volume anomaly), proxy body-inspection kills naive HTTPS mimicry — malleable profile quality is measurable by their proxy alert rate (report it).

## Tool fallback order

- Implant framework: Sliver > Mythic > client-preferred stack > raw-tooling mode.
- Redirector: Caddy/nginx (mod-rewrite class) > cloud-function proxy (serverless redirect class) > CDN-front.
- Windows persistence: task/registry (simple tier) > service > WMI (stealth tier) — selected by engagement stealth objective.
- Linux persistence: cron/systemd > shell rc > ssh key.

## Evidence handoff

`05-infra/` gets the complete infra map (domains, IPs, redirector topology, listener configs — delivered to client at close-out for their blocklists). `03-hosts/<host>/artifacts-left.md` gets EVERY persistence mechanism with exact removal commands. 15 gets: persistence-per-host table (mechanism | host | removal verified ✓) + C2 domain/callback-pattern list + malleable-profile disclosure (purple-team handoff value). Close-out cannot sign off while any artifact-left entry is unverified-removed (15's hard rule).
