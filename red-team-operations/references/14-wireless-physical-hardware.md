# 14 — Wireless, Physical & Hardware Access

**When to read:** RoE includes wireless networks, physical premises, badge/RFID systems, or hardware implant classes; entry-method decisions for on-site engagements; radio-based vectors.
**Prerequisites:** RoE PHYSICAL/WIRELESS class approved IN WRITING (00 default exclusion — these vectors are the highest-liability classes: insurance requirement, specific named site/address, non-destructive-only clause); equipment list per RoE; site-safety briefing acknowledged; buddy/second-person rule for on-site work where RoE requires it.
**Primary ATT&CK mapping:** T1557 Adversary-in-the-Middle (wireless AITM classes), T1557.001-adjacent credential capture (rogue-AP phishing class), T1200 Hardware Additions (rogue devices/drop boxes), T1056 Input Capture (credential capture portals), T1110.003 spraying only where AD-joined WiFi auth classes apply, name-based mappings elsewhere (badge cloning / RF replay have no clean ATT&CK ID — map to the outcome technique in the chain, e.g., T1078 Valid Accounts after badge use).

## Safety & legality first (physical/wireless special rules)

1. **Personal safety > engagement success.** No electrical rooms, no climbing, no restricted-area improvisation. If entry needs it, it's out.
2. **Non-destructive only:** no lock picking on safety/exit hardware, no forcing doors, no badge-cloning of strangers (only RoE-named accounts), no tailgating through emergency exits (alarms = safety systems = 00 excluded class).
3. **Third parties:** public/shared buildings contain non-client space. RoE must name the tenant/floor/address precisely. Target only the named footprint.
4. **Stranger-interaction ethics:** tailgating/social engineering of identifiable third parties (guards, cleaning staff) usually RoE-restricted to observation-only. Impersonating staff with client-approved pretexts only; never impersonate law/emergency services (universal hard rule).
5. **RF classes:** stay in-license bands (ISM), never interfere with licensed/safety radio (medical, industrial pagers, emergency comms). Record transmit-frequencies to the engagement log.

## WiFi (enterprise + guest)

### Recon (passive-first)

```bash
# monitor mode + survey
iw dev <iface> set channel <n>
airodump-ng <iface> --manufacturer --uptime        # BSSID/ESSID/channel/client map; noise filter
```

- Classification first: WPA2-PSK (shared-key class) vs WPA2/WPA3-Enterprise (802.1X) vs open+ captive-portal; each routes differently.
- Probe for the real SSID behind hidden networks only by passive client-association observation — active deauth/deassoc is a DISRUPTION class (availability impact) — RoE-gated, never default.

### PSK classes

- Handshake capture (4-way) → offline crack: `hashcat -m 22000 pmkidhandshake` (WPA-PMKID + EAPOL combined mode — capture PMKID from AP without client where AP vulnerable, else handshake with a client). Wordlist + rule chains; client-side capture evidence (hash into evidence, 00).
- Finding = weak PSK (crackable) + guest/production segregation check (same key on guest VLAN = finding class).

### Enterprise (802.1X) classes

- PEAP/MSCHAPv2 with invalid-server-cert acceptance → credential capture (rogue-AP + challenge capture → offline crack of MSCHAPv2 → AD credential via NTLM semantics → route 05/08 chain). RoE: rogue-AP class needs explicit EVASION/credential-capture approvals + controlled-user list (only approved employee accounts associate — stop others by portal text).
- TLS-cert validation state on clients (their GPO config — the finding is "clients accept any cert" even if you don't run the rogue AP); server-cert check via client config analysis where access allows.

### Rogue AP / captive-portal phishing (credential capture class)

- Engagement-approved SSID (lookalike per RoE, or client-named), portal on engagement infra, capture → hash → vault (04's phishing discipline verbatim: notify + close-out disclosure). No WPA-password display logging in plaintext.
- Time-boxed deployment (hours, recorded); deconfliction entry with the client's monitoring (00).

## Bluetooth / BLE

- Scanning/enumeration (hcitool/nRF-class tooling): device inventory, tracking-identifier stability (privacy finding for the CLIENT's deployed devices — badges/trackers), pairing-mode misconfigurations on client devices.
- Active pairing/PIN attacks on client-owned devices only; no third-party devices.

## RFID / NFC (badge systems — with the client's OWN badges per RoE)

```bash
# Proxmark3-class workflow (LF HID Prox / iClass, HF MIFARE)
# LF 125kHz: read client badge → clone to T5577 emulation (client-approved badge only)
# HF MIFARE Classic: key-dictionary check against client's system keys first (default-key findings),
#   then nested-auth crack only where RoE allows
```

- **Default/unread key findings:** the finding class = "system ships with default keys / unencrypted UID mode" — reportable from the READ check alone; clone/emulate only the client's own badge, only with the named account's badge, only during approved window.
- Badge-format leakage (HID facility codes from a read = internal-format finding; feeds building-attack narrative).
- Cloning evidence: read + clone demo + RETURN the original badge state; emulated-badge usage on the access reader only inside the approved window with client awareness.

## SDR (software-defined radio) — fixed-code / OOK classes

- Signal ID (rtl_power/inspectrum-class): identify the client's remote classes (garage/gate/industrial remotes) per RoE list.
- Fixed-code replay: capture → replay to verify access (roaming/crash-free classes only); rolling-code systems: capture-phase replay findings ONLY (no code-rolling bypass classes — that's destructive + safety-adjacent).
- NEVER touch: medical telemetry, emergency/safety radio, licensed-band devices (00's excluded classes — no engagement value justifies it).

## Physical entry & on-site hardware

### Entry decision tree (RoE-approved classes only)

```text
Badge access (cloned/issued per RoE) → normal entry through client-controlled doors
Tailgating (approved + observed by client escort or camera-aware per RoE)
  → ONLY through client-tenant doors, never safety/emergency exits
Lock classes (approved: non-destructive picking on client-owned, non-safety locks ONLY,
  with client watching per purple-team RoE; return everything to locked state + log relock time)
```

### On-site tradecraft (equipment + rules)

| Class | Equipment | RoE/ethics notes |
|---|---|---|
| Drop box (network implant) | engagement-built, labeled (deconfliction per 00), plugged into CLIENT-named drops only | each = artifact-left (15); removal at close-out verified physically |
| Rogue USB device (keystroke-injector class) | client-approved target machines ONLY | input-capture class RoE; never on third-party machines |
| Badge-cloning kit | reader/Proxmark/T5577 | client-named badges only (above) |
| Photo/video evidence | timestamped, faces of third parties blurred | 00 evidence rules |

### On-site workflow discipline

1. Entry method + time + witnesses logged (engagement log, 00).
2. Every action photographed/video'd where possible (both evidence + self-protection: the log is your alibi for "why was someone at that door").
3. Departure sweep: equipment count-in/count-out — a forgotten drop box or cloned badge = incident class (not just cleanup).
4. Exit exactly the way entered; no opportunistic additional access ("we were already inside" ≠ scope).

## Common failures / misreads

| Symptom | Misread | Reality check |
|---|---|---|
| Handshake captured | "PSK crackable" | Handshake ≠ crack — quality of PSK decides; report Inferred until crack proof |
| Rogue AP got assoc | "Enterprise creds captured" | Challenge ≠ crackable (complexity + domain policy); classify honestly |
| Badge clone reads | "Access compromised" | Read ≠ door-open (format + reader model may reject emulation) — test only in approved window |
| Fixed-code replay works | "Gate compromised, Critical" | Availability-era rating: often Low-impact physical finding — rate honestly (15) |
| Hidden SSID observed | "Obscure = finding" | Hidden SSIDs are trivially discovered — not a finding alone |

## Detection footprint

- Rogue-AP class: their wireless IDS (if any — the finding when silent), portal access logs.
- Badge events: access-control system logs (reader + timestamp + badge ID — your cloned-badge demo events = their audit trail; the close-out narrative cites them, 15).
- Physical: cameras (timeboxed entry = expected on footage; RoE-cleared with client monitoring or not, per engagement type).
- RF: no target-side telemetry unless their spectrum monitoring exists (rare — coverage-gap note for 15).

## Tool fallback order

- WiFi: aircrack-ng suite > hcxdumptool (PMKID-lean capture) > internal tooling; WPA3-SAE classes = read-only findings (no practical crack — report config, don't pretend).
- RFID: Proxmark3 > dedicated readers per frequency class.
- SDR: HackRF One > RTL-SDR (RX-only classes).
- BLE: nRF-class > hcitool.

## Evidence handoff

Per vector: photos/video with UTC timestamp (00 evidence rules), RF captures (hash files), badge read/clone demo records (badge ID + approved-account citation from RoE), entry/exit log lines (engagement log), every device deployed → artifacts-left with physical location + serial (15 close-out). Physical-class findings: badge-system key-management, camera-coverage gaps, no-tailgate-culture (the process finding), drop-box network placement unchallenged (the org finding).
