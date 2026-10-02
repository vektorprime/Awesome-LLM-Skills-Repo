# 10 — Defense Evasion (within RoE)

**When to read:** ONLY after checking 00's action-class EVASION in the RoE. Default posture: detect-and-report — evasion is often NOT authorized (purple-style engagements want you caught). If authorized: any AV/EDR/AMSI/ETW/log-blocking technique decision; posture planning for all other phases (which techniques are on/off host).
**Prerequisites:** RoE EVASION class approved in writing; target EDR product identified (fingerprint from 06/08 host enum); lab with the SAME product deployed for validation; indicator list updated.
**Primary ATT&CK mapping:** T1562 Impair Defenses (T1562.001 Disable or Modify Tools), T1027 Obfuscated Files or Information (T1027.002 Software Packing, T1027.006 HTML Smuggling, dynamic-API-resolution class), T1055 Process Injection (+T1055.001 DLL Injection, T1055.003 Thread Execution Hijacking, T1055.012 Process Hollowing), T1134.004 Parent PID Spoofing, T1218.011 Rundll32 / proxy-execution class, T1202 Indirect Command Execution, T1027.005 Indicator Removal (rare — usually forbidden: log tampering, 00), T1211 Exploitation for Defense Evasion, T1620 Reflective Code Loading.

## Posture decision tree (read FIRST — most engagements stop here)

```text
RoE EVASION class?
  ├─ Not authorized (default) → detect-and-report posture: use loud, well-known tooling,
  │   let the EDR catch it, RECORD what it caught (that's the deliverable — detection coverage map)
  ├─ "Evasion allowed, log tampering forbidden" (common) → payload/concealment evasion only;
  │   never touch logs/security tools state
  └─ Full evasion scope (rare, long-duration red team) → below, still: never delete/alter
     client-side logs, never disable their tooling permanently
```

**Hard rules regardless of scope:** no deletion/tampering of client telemetry (that's destruction of evidence class); no permanent security-control disabling (report the COULD, not the DID, where the client's defense posture is the finding); unvetted evasion binaries still follow the 00 lab-first rule (evasion tools crash protections = BSOD/incident).

## Detection-model literacy (why techniques work/fail)

Posture decisions require knowing WHAT the sensor sees:

| Sensor layer | Visibility | Evasion surface |
|---|---|---|
| On-host EDR user-mode hooks | ntdll-export calls from instrumented processes | direct/indirect syscalls, unhooked fresh ntdll |
| On-host EDR kernel callbacks | process/file/registry/image-load events, thread starts | injection technique choice (callback vs remote-thread signatures) |
| ETW providers (.NET, PowerShell, WMI) | managed-code + script telemetry (4104 script-block, assembly loads) | provider patching (T1562-class), unmanaged execution |
| AMSI | script content scans pre-execution (PowerShell, .NET 4.8+) | content obfuscation, in-memory patch of `AmsiScanBuffer` class |
| Sysmon (if deployed) | process/image/net/registry/file events per config | artifact minimization (file-less, LOLBins-class execution) |
| Auth/logon telemetry (DC) | 4624/4768/4769 patterns | technique selection from 05/08 tables |
| Network (proxy/IDS) | SNI/HTTP/DNS patterns | egress profile tuning (09) |

**The engagement-relevant framing:** each layer you don't evade is a detection-coverage datapoint for the client (15 appendix). Full evasion WITHOUT reporting what you bypassed is a failed engagement — the map of gaps IS the deliverable.

## Technique classes (concept → trade-off → validation protocol)

### Script/managed-layer (PowerShell/.NET)

- **Constrained Language Mode (CLM):** check early (`$ExecutionContext.SessionState.LanguageMode`) — CLM blocks most tooling → routes to unmanaged execution or explicit CLM bypass classes (AppLocker-rule abuse family, public documented bypasses; RoE-flagged since they're policy escapes).
- **AMSI class (T1562.001):** patching `AmsiScanBuffer` in-proc is heavily signatured (EDR hooks + memory scans for the patched byte pattern); content-obfuscation (encoding/splitting payloads so scans never see the full malicious content) and off-PowerShell execution are lower-risk classes. Validate in lab with the client's actual product before any claim.
- **Script-block logging (4104):** assume every PowerShell you run is logged — script your on-host PowerShell usage accordingly (minimal, purposeful, engagement-marked commands).
- **.NET assembly load:** in-line execution (no file drop) vs fork-and-run (spawn+inject detected by child-process anomaly rules — inline is lower-noise).

### Execution-layer (native API / injection)

- **Direct syscalls class (T1106 + dynamic resolution):** resolving syscall numbers at runtime (Hell's/Halo's Gate-style patterns) avoids user-mode hooks — note syscall-number drift across Windows builds (validate per-build in lab; a wrong number = crash).
- **Indirect syscalls class:** jump to legitimate syscall instruction inside ntdll (keeps return-address legitimacy) — trade-off: complexity + build fragility vs. hook coverage.
- **Unhooking class (fresh ntdll):** map a clean ntdll copy from disk over the hooked one (concept: the on-disk copy bypasses in-memory EDR patches) — signatured by some products; validate.
- **Injection technique selection (T1055):** remote-thread create = classic, most-detected signature; callback-based execution (legitimate API callbacks: enumeration/property/windows-message classes) lower signature; process hollowing (T1055.012) mid-tier; phantom-dll/stomping classes lower-tier. Selection = lab-validated against THE client's product rules (their rule names = report content).
- **Reflective loading (T1620) / position-independent shellcode:** no file artifacts; sRDI-class tooling converts existing PE tooling — standard workflow for Rubeus-class tools into your implant (see x64-assembly skill for authoring).

### OPSEC-lifecycle techniques

- **Sleep obfuscation class (T1055.003-adjacent):** encrypt implant memory + swap out of memory during sleep (timer/fiber callback driven ROP chains — Ekko/Foliage-style public technique families). Memory-scan-resistant dormancy; build-fragile — lab-validated per-build.
- **PPID spoofing (T1134.004):** implant parent set to a legitimate long-running process (explorer/services class) so child-process anomalies look native.
- **Block-non-Microsoft DLL policy:** SetProcessMitigationPolicy class preventing EDR DLL injects into YOUR process — RoE-flagged (defensive-control interference — many clients prohibit; ask).
- **Staged loaders/clean memory hygiene:** full-PE parsing in-memory, sleep-time cleanup of decrypted sections, per-op memory allocation/dealloc patterns.

### File-layer

- **Packing/obfuscation (T1027.002):** packers = AV-scan evasion, but packed-PE entropy itself flags; better: custom trivial transformations (encoding, section naming) — check with ThreatCheck-style segmentation (find WHICH bytes the product flags — targeted fix, not blanket pack).
- **LOLBins/proxy execution (T1218.011 rundll32, T1218.010 regsvr32, T1202 indirect):** execution through signed binaries (esp. with network-fetch capability class) — detection surface = command-line analytics; select from the well-documented binary set; validate their command-line rules against the choice.
- **File-less classes (T1055/T1620/registry storage):** no disk artifacts — but note "file-less" ≠ invisible: process telemetry still records behavior; memory-forensics still catches resident payloads.

## Validation protocol (per technique, before ANY client-host use)

1. Lab detonation with client's product version + identical Windows build (00 lab rule).
2. Record: blocked? flagged-not-blocked? silent? + exact detection name if blocked (report content).
3. Drift-check: product config in lab matches client's? (policy differences change results — note uncertainty where unknown).
4. Plan the burn: if caught mid-engagement on real host — response per 09 callback-ops discipline (retire, note, continue with alternate path; never escalate into log tampering).

## Common failures / misreads

| Symptom | Misread | Reality check |
|---|---|---|
| Tool "ran fine" | "EDR bypassed" | EDR block≠alert≠silent — check the product console/telemetry in lab (purple: ask); "ran" without console check = unknown, report as such |
| AMSI patch succeeded | "All script telemetry dead" | Only AMSI's content scan bypassed; script-block logging, ETW, process telemetry still record execution |
| Direct syscalls work in lab | "Ship it" | Build drift: validate per Windows build — syscall table differences crash on mismatch |
| Injection silent | "Memory resident = invisible" | Kernel callbacks still record cross-process access — thread/process telemetry remains |

## Detection footprint (self-audit)

For EVERY evasion technique used, maintain the technique→telemetry row (15 appendix): what SHOULD have caught it (per layer table), what DID (if client shared console data), what the gap was. The evasion section of the report is written from THIS table — the client learns their coverage gaps from it, which is the engagement's actual value.

## Tool fallback order

- Posture triage: host fingerprint (06/08 enum output) → product/rules identification → lab replicate.
- Shellcode/tool conversion: sRDI-class (PE→sRDI) > custom loader authoring (x64-assembly skill).
- Segment-scanning for flagged bytes: ThreatCheck-style segmentation > blanket packer.
- Syscall resolution: dynamic (drift-tolerant) > static tables (build-fragile).

## Evidence handoff

Per technique exercised: lab validation record (detonation output + detection result) + host usage log (where/when/what result) + technique→telemetry row for 15. Every on-host artifact (loader, payload, config) → `03-hosts/<host>/artifacts-left.md` (15). RoE EVASION authorization citation on every evidence entry (00 chain).
