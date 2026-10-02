# 16 — Custom TCP Application Servers (Game/Proprietary Backends)

**When to read:** Custom (non-HTTP) TCP application server in scope — game servers, proprietary backend services, custom RPC/middleware, brokers with custom framing; an unknown/high-port TCP service from 02's scan that matches no known protocol; game-client-on-Windows → game-server-on-public-IP scenarios (client reversing + server attack).
**Prerequisites:** Authorization gate with action class EXPLOIT; server IP:port in scope and re-resolved (public-IP drift, 00); a working client + RoE-approved test account (own sessions only); lab copy of client binary; **production-server hazard assessed** (below — live players = shared-infra class, 00).
**Primary ATT&CK mapping:** T1595.002 Vulnerability Scanning (service probing), T1040 Network Sniffing (own-session capture), T1557 Adversary-in-the-Middle (relay phase), T1190 Exploit Public-Facing Application (server exploitation), T1203 Exploitation for Client Execution (client-side classes), T1210 Exploitation of Remote Services.

## The production-server hazard (read first)

A public-IP game/app server with live players is **shared infrastructure: other real users are on it.** Blind fuzzing, crash-triggering payloads, or aggressive connection storms = availability impact on third parties = 00 stop-condition territory, regardless of the client's ownership of the server. Rules:

1. Prefer a staging/shard server or an isolated instance (ask the client — most have one).
2. Production runs only in client-approved windows, with rate caps and connection limits, crash-tolerant plan (00).
3. Fuzzing coverage-guided only where you have the server binary in lab; black-box production fuzzing is near-blind + max blast radius — worst combination in this file.
4. Capture third-party players' traffic: never (privacy class, 00) — own sessions only.

## Methodology (decision tree)

```text
Unknown/custom TCP service (02 scan output)
  → Phase 1: service identification (gentle probes; framing class hypothesis)
  → Phase 2: passive protocol RE from OWN client sessions (capture → framing model)
  → Phase 3: client binary RE (the protocol spec lives in the client) → route reversing skill
  → framing model confirmed by BOTH sources (capture + client RE agree = Observed)
  → Phase 4: MITM relay (log/mutate/replay/drop/delay) on own session
  → Phase 5: stateful fuzzing (pre-auth surface first; staging-first rule)
  → Phase 6: game-logic abuse classes (client-trust/duplication/session findings)
  → memory corruption found → Phase 7: route to 11 (full exploit-dev chain)
```

## Phase 1 — Service identification (from 02, protocol-blind)

```bash
nmap -sV -Pn -n -p <port> --version-intensity=5 --script default,safe <ip> -oA 01-scans/custom-svc
# gentle framing probes (ONE connection each — no storms):
#   empty connect          → banner? timeout? immediate RST?
#   garbage bytes          → error string? disconnect? protocol hint?
#   single newline/null    → framed response?
nc -v <ip> <port>                       # interactive: observe reset-vs-banner-vs-silence
```

Interpretation: immediate RST on garbage = strict state machine; verbose error strings = finding-grade information disclosure (version, component names — capture verbatim); silence-then-timeout = waiting for a specific handshake (Phase 3 supplies it). Version-pin everything from error strings (01/02 discipline: banner-as-lead, cross-check).

## Phase 2 — Passive protocol RE (own sessions only — T1040)

```bash
# capture your own client sessions (RoE test account):
tcpdump -i <iface> host <server-ip> and port <port> -w 02-findings/proto-<ts>.pcap
# or Wireshark with a ring buffer for long sessions; then:
tshark -r proto.pcap -q -z conv,tcp          # session/byte-volume map
tshark -r proto.pcap -T fields -e tcp.payload -Y "tcp.src_port==<port>" | head
```

Framing analysis order (per direction of the stream):

1. **Message boundaries:** length-prefix class (2/4-byte header where first bytes predict payload size), delimiter class (fixed terminator), fixed-size records, or none (raw stream). Test: does byte-0..3 as little/big-endian length predict the rest?
2. **Endianness:** consistent per message class (check length fields against actual payload sizes, both interpretations).
3. **Checksums/CRC:** trailing/leading fields that change when payload changes (flip a captured payload byte, recompute candidate CRCs against the field — CRC32/Adler/sum classes).
4. **Compression magic:** payload starts `78 9c/78 01/78 da` (zlib), `04 22 4d 18` (LZ4 frame, read as 0x184D2204 BE), `28 b5 2f fd` (zstd) → decompress segments offline.
5. **Encryption:** high entropy payload + no visible structure + TLS absent = custom crypto (Phase 3 extracts keys/algorithms — custom crypto is USUALLY embedded-key class, not a dead end). TLS: standard interception route (Phase 4).

Session structure map: first N messages = auth/handshake (login flow), then steady-state opcodes + heartbeats, disconnect semantics. Build the **opcode/message-id table** (id → size class → direction → which client action triggers it — trigger one client action at a time and diff captures).

**Evidence-quality capture:** build a Wireshark Lua dissector for the framing model — the dissector makes captures second-analyst-readable (house standard) and is itself a deliverable artifact.

## Phase 3 — Client binary RE (the protocol spec — route `reverse-engineering-executables`)

The client implements the full protocol: serialization structs, opcode dispatch, crypto. Engine routing table:

| Client class | Route |
|---|---|
| Unity (Mono backend) | managed decompilation (dnSpy-class) → serializer/dispatch code directly |
| Unity (IL2CPP) | Il2CppDumper-class + Ghidra on `GameAssembly.dll` (script symbols from dump) |
| Unreal | SDK-dumper classes + native RE (full protocol below) |
| Native (C++/custom) | `reverse-engineering-executables` full protocol (static-first) |

Extraction targets (in priority order):

1. **Opcode dispatch table** — the switch/map from message id → handler function; gives the complete message list (more complete than capture-only) + the handler code per message.
2. **Serialization/deserialization structs** — field layouts, types, bounds checks (absent bounds checks on server side = Phase 5 fuzz targets).
3. **Crypto material** — embedded keys, nonce/IV handling, XOR/stream-cipher classes; hand-rolled crypto = finding class even before abuse (crypto finding + key extraction).
4. **Client-side validation logic** — every check done ONLY client-side (range/speed/ownership checks) = Phase 6 client-trust candidate (the server-side absence is the finding).
5. **Pinning/hardening** — certificate pinning, packet integrity, anti-tamper (affects Phase 4 relay feasibility; bypass decisions route to 10's RoE posture rules).

Output: the **protocol map** (opcode → struct → handler → client action) — the case-dir artifact every later phase cites; capture + client RE agreeing = Observed confidence (one source alone = Inferred).

## Phase 4 — MITM relay (T1557 — own session)

Custom relay (listen → log → forward) with per-message hooks: pass / mutate / drop / delay / reorder / duplicate / truncate / replay-later. The relay is your protocol lab: every game-logic test in Phase 6 and every fuzz mutation in Phase 5 runs through it so all traffic is evidence-logged (00).

- **TLS interception where applicable:** client pinning bypass = client-side hooking (local-device action, RoE class check — and route 10 for posture; detect-and-report pinning as a hardening observation instead where RoE says detect-only).
- **Replay testing:** capture a message → replay it later within the same session (idempotency: does a movement/purchase message re-apply?) and in a NEW session after logout (session-token binding: does the auth/session material survive reconnection?). Non-idempotent ops + replay = duplication finding candidate (Phase 6).
- **Out-of-order/state-confusion:** send post-auth messages pre-auth, or state-inconsistent sequences (use item before pickup etc.) — server-side validation gaps.
- Delay class (lag-switch analog): artificial latency on selected messages only, to trigger race windows in server logic (duplication races, 03's race-condition classes applied at protocol level).

## Phase 5 — Stateful protocol fuzzing

Two modes, chosen by server-binary availability + RoE (the hazard rules above):

| Mode | Available | Method |
|---|---|---|
| Coverage-guided (preferred) | server build in lab (ask client — staging binary) | instrumented server (AFLnet/StateAFL-class harnesses: network-input-aware, keeps server state machine alive between cases) + grammar-driven generational fuzzing from the Phase 3 protocol map |
| Black-box | public server only | capture-corpus mutation (seed messages → field-level mutation operators) through the Phase 4 relay; strict rate caps; staging-first rule |

Mutation operators (field-aware, from the protocol map — not random byte flips): length-field extremes (`0x00`, `0xFFFF`, negative-as-signed, integer overflow boundaries), enum out-of-range, string overflow (long + no-terminator), truncated message (length > payload), duplicate sequence numbers, opcode not-in-table, cross-field contradictions.

**State model:** unauthenticated → authenticated → in-session states. **Fuzz pre-auth surface FIRST** (unauthenticated memory corruption on a public server = the crown finding of the file). In-session: state-machine abuse (out-of-order opcodes) as a separate campaign.

**Crash triage:** every crash → 11's crash-analysis protocol (debugger attached, fault registers, control classification, exploitability honesty). Crash ≠ finding without control demonstration (11's rule).

## Phase 6 — Game-logic abuse (findings class — often no CVE, still the client's real risk)

- **Client-trust findings (server-authoritative gaps):** via relay mutation — position/movement packets with impossible deltas (teleport, speed), actions the server should re-validate (trade acceptance, item use eligibility, ownership). Server accepting = finding (severity by economy/competitive impact — qualitative, 15's rule).
- **Duplication classes:** replay + race combinations on non-idempotent ops (drop-and-trade timing, concurrent sessions racing a purchase — 03's single-packet race discipline applied via the relay).
- **Session handling:** session/token entropy (predictable session ids = account-takeover class), concurrent-session behavior, logout invalidation.
- **Anti-cheat validation coverage map:** the deliverable = which server-authoritative checks are MISSING (even where RoE is detect-only — the coverage map itself is the finding, 10's doctrine).
- **Economy impact rule:** demonstrate with canary/test items only — no real player-economy impact (00 non-production-data analog).

## Phase 7 — Server memory corruption → route 11

Full chain owned by `references/11-binary-exploitation.md` (mitigations inventory → primitive → chain → 10× stability). Note the raised bar: public server crash affects real players — the stability requirement in 11 is the minimum, plus approved-window + rollback plan (the hazard rules above).

## Common failures / misreads

| Symptom | Misread | Reality check |
|---|---|---|
| Encrypted payload, no keys found in 10 minutes | "Dead end" | Embedded-key classes live in client RE (Phase 3) — hand-rolled crypto almost always yields |
| Lua dissector misparses one message type | "Protocol wrong" | Framing may differ per opcode (mixed framing classes) — diff against client RE, don't force one model |
| Fuzz crashes server in lab | "Great, fire at prod" | Lab-only until 11's chain exists; prod needs the window + plan (hazard rules) |
| Replay of movement message "does nothing" | "No replay bugs" | Idempotent-by-design ops mask it — test NON-idempotent ops (purchases/trades), not movement |
| Client anti-tamper fires on your hook | "Engagement blown" | It's a client-hardening datapoint (finding) — switch to capture-only posture or RoE-approved bypass per 10 |
| Black-box fuzzing finds nothing in a day | "No bugs" | Near-zero coverage without the protocol map — Phase 3 first, then grammar-driven; black-box-only = coverage honesty note in report |

## Detection footprint

- Server-side: anomaly logging, rate limits, anti-cheat telemetry — assume fuzz patterns are logged WITH account identity (permanent attribution, cloud-class, 12) — RoE test accounts make the client's log review trivially scoped (00 deconfliction).
- Player-facing: relay-injected lag/crashes are visible to other players on shared servers — the hazard rules exist for this.
- Client-side: anti-tamper/anti-cheat on the client sees your hooks (Phase 4/3) — posture per 10.

## Tool fallback order

- Capture: Wireshark + Lua dissector (evidence-quality) > tshark + offline parsing > tcpdump raw.
- Relay: custom relay (full per-message control) > mitmproxy raw-TCP mode > socat-class forwarder (log-only).
- Client RE: `reverse-engineering-executables` full protocol; engine routing table above for game engines.
- Fuzzing: grammar/generative from protocol map > capture-corpus field mutation > AFLnet-class harness (server binary required) > raw black-box (last resort, coverage-honesty note).
- Crash analysis: 11's tool orders (gdb/pwndbg class, rr for nondeterminism).

## Evidence handoff

Per finding: capture files + dissector + hashes (finding-evidence checklist), the protocol map (opcode table + struct layouts + state model), relay logs for every mutation test (the reproduction record), crash artifacts → 11's chain. Findings classes: protocol/logic findings (qualitative severity, 15's rule) vs memory-corruption findings (CVSS + 11's chain). Client-side artifacts (hooked client, bypassed pinning) → artifacts-left note (15) if anything persisted on the client machine.
