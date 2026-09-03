# 10 — Packing, Obfuscation, Anti-Analysis (EXE)

Decide first whether unpacking is even needed for the scoped question. Full devirtualization is research; often behavior can be confirmed dynamically without it.

## 1. Packing verdict (need 2+ indicators, never 1)

| Indicator | Check |
|---|---|
| Entry in non-`.text` (UPX1, .vmp, .themida) | `rz-bin -S` + `AddressOfEntryPoint` |
| 1–5 imports + `LoadLibrary/GetProcAddress/VirtualProtect` | `rz-bin -i` |
| High-entropy section + tiny imports | `entropy.py` + imports |
| `W+X` section, `RawSize=0` + large `VSize` | section table |
| Write → execute transfer at runtime | `catch syscall mprotect` / CDB `bp VirtualProtect` + `u @rip` after return |
| Static vs runtime module map disagree | `afl` count static vs `x sample!*` live |

One hit = `Unknown/Low`. Two+ = `Inferred/Medium`, confirm with runtime transfer.

## 2. UPX shortcut (only if confirmed)

```bash
cp -- "$F" "$CASE/artifacts/extracted/upx-input.bin"
upx -t "$CASE/artifacts/extracted/upx-input.bin" 2>&1 | tee "$CASE/artifacts/extracted/upx-test.txt"
upx -d -o "$CASE/artifacts/extracted/upx-unpacked.bin" "$CASE/artifacts/extracted/upx-input.bin" 2>&1 | tee -a "$CASE/artifacts/extracted/upx-test.txt"
sha256sum "$CASE/artifacts/extracted/"*.bin | tee "$CASE/artifacts/extracted/upx-hashes.txt"
```

Only if `upx -t` succeeds. Re-run triage (`02-...`) on unpacked output, record parent chain. Modified UPX (patched magic) fails here → go to generic workflow.

## 3. Generic runtime dump

1. Break on alloc/protect (`VirtualProtect`, `NtProtectVirtualMemory`, `mmap/mprotect`).
2. Note written region (addr + size + perms).
3. Break after control transfers into it (`u` shows unpacked code, imports resolved).
4. `dump binary memory` / CDB `.writemem` only that region.
5. Re-triage dump, record PID + VA range + parent SHA.

Raw dump ≠ rebuildable EXE. Rebuilding IAT is separate work — only do it if static analysis of unpacked code is required. Otherwise analyze behavior from trace + dump strings.

## 4. API hashing / dynamic resolution

If imports are just `LoadLibraryA + GetProcAddress` + hash constants (`0xA779563A`-style, ROR13):

- Break on `GetProcAddress`, log 2nd arg (`du poi(@rdx)` / `du @rdx`).
- Collect resolved names → reconstruct true import set in function note.
- Don't brute-force hashes blindly; runtime log is ground truth.

## 5. Anti-analysis catalog (check relevance first)

- Debugger: `IsDebuggerPresent`, `CheckRemoteDebuggerPresent`, `NtQueryInformationProcess (0x7/0x1E)`, `OutputDebugString` tricks, timing (`RDTSC`, `GetTickCount` deltas).
- VM/sandbox: `CPUID` hypervisor bit, MAC/disk/username blocklists, `Sleep` stalling (>5 min), mouse/keyboard wait.
- ETW/AMSI patching (`EtwEventWrite`, `AmsiScanBuffer` patch) → behavior-hiding, note but don't bypass out of scope.
- Exception-based control flow (SEH/VEH as logic) → step in debugger, don't assume linear flow.

Ask: does this check gate the scoped question? If no, document and route around (e.g. analyze gated function statically). If bypass needed, check engagement scope + licensing (Themida/VMProtect bypass may violate policy) and escalate per `11-...`. Never silently patch and report patched behavior as original.
