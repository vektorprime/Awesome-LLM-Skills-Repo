# 12 — Runtime Hooking on Windows (Frida, Detours, IAT, Injection, ETW)

Hooking = observing/changing behavior **in a live process without editing the
file on disk**. It answers questions static analysis cannot (what args does
this function get with real input? what does the unpacking stub decode to?),
and it is the bridge from `08-dynamic-windows-cli.md` to systematic logging.

**Scope gates (all must be true):** authorized target + disposable VM + snapshot
(see `01-...` execution gate). Hook only in the lab. Never hook anti-cheat,
DRM, banking, production, or third-party systems — that is tampering, not
analysis. Keep every hook script + version with the case; a hook run without
its script is not evidence.

## 1. Choose the hook layer (cheapest first)

| Question | Tool of choice | Why |
|---|---|---|
| Which APIs get called, in order | CDB `bu` (see `08-...`) or `frida-trace` | no code to write |
| What are the args/returns of a few functions | Frida `Interceptor` script | arg marshalling, buffers |
| Full call history with source module | ETW / `wpr` | no injection at all |
| Change a function's behavior | Frida `Interceptor.replace` or Detours DLL | real patching |
| Hook a function with no symbol | Frida + module base + RVA from `05/06` | ASLR-safe math |
| Hook everything a family of functions does | Detours/MinHook logging DLL | scale |

Hooking forwards APIs: `kernel32!CreateFileW` is a jump thunk into
`KernelBase`. Hooking either entry catches the call; hooking `KernelBase`
catches all forwarded callers. Confirm with `ln @rip` at the hit (`08-...`).

## 2. Frida quickstart (CLI-first, Windows)

```bash
frida --version | tee -a "$CASE/tool-versions.txt"
# attach to running process:
frida -p <PID> -l hooks.js -o frida-session.log
# spawn under Frida (catches startup + DLL_PROCESS_ATTACH):
frida -f "C:\\lab\\target.exe" -l hooks.js -- runtime-arg1
```

Minimal `hooks.js` — log every `CreateFileW` with the wide filename:

```js
const mod = Module.getExportByName("kernel32.dll", "CreateFileW");
Interceptor.attach(mod, {
  onEnter(args) {
    // x64: arg1..4 = rcx,rdx,r8,r9 (see 07-windows-abi-x64.md)
    this.path = args[0].readUtf16String();
    this.access = args[1].toInt32();
  },
  onLeave(retval) {
    send({api: "CreateFileW", path: this.path, access: this.access >>> 0,
          handle: retval.toInt32()});
  }
});
```

Log every `connect` with the decoded `sockaddr` (arg2 = rdx = `sockaddr*`):

```js
Interceptor.attach(Module.getExportByName("ws2_32.dll", "connect"), {
  onEnter(args) {
    const sa = args[1];
    const family = sa.readU16();
    const port = (sa.add(2).readU8() << 8) | sa.add(3).readU8(); // network order
    const ip = [3,4,5,6].map(i => sa.add(i).readU8()).join(".");
    send({api: "connect", family, port, ip});
  }
});
```

Dump a buffer at a hit (unpacking / config decode):

```js
onEnter(args) {
  const p = args[0], len = args[1].toInt32();
  if (len > 0 && len < 0x10000) {
    send({type: "buffer", len}, p.readByteArray(len)); // binary in message
  }
}
```

Essential API surface: `Module.getExportByName/findExportByName`,
`Process.enumerateModules()`, `Memory.read*/writeByteArray`, `Memory.scan`
(find patterns in memory), `Interceptor.attach/replace/detach`,
`Interceptor.flush()`, `send()/recv()`, `Module.findBaseAddress` for RVA math:
`runtime_addr = Module.findBaseAddress("target.exe").add(RVA)` (from `05/06`).

**Frida discipline:**
- One hook per question; log args **after** dereference (`08-...` evidence rules).
- Guard every dereference (`try/catch`) — a bad `readUtf16String` kills the
  process and your run.
- `frida-trace -f target.exe -i "CreateFileW" -i "ReadFile" -m "*"` generates
  per-API handler stubs in `__handlers__/` — edit those stubs instead of
  writing from scratch. Review `handlers` output with the same skepticism as
  strings: a hit is Observed, the *meaning* is still yours to prove.
- Attach vs spawn: spawn (`-f`) for startup/DllMain/TLS callbacks; attach
  (`-p`) only for post-startup behavior (state before attach is invisible).
- .NET targets: Frida sees the native CLR, not IL methods — decompile IL first
  (`04-...`) and hook the JIT-compiled native only with care; easier is
  `dotnet-dump`/IL instrumentation. Record the limitation, don't fake it.
- 32-bit target needs 32-bit Frida (and vice versa) — mismatch silently fails
  to attach.
- Anti-debug targets detect Frida (threads, hooks). If the target fights the
  observer, fall back to ETW/static + `10-...` catalog; do not silently lose
  data.

## 3. Building an analysis DLL (Detours / MinHook)

Use when you need scale (hundreds of APIs), stability, or logging to file from
a persistent DLL. Classic layout (C++, x64):

```cpp
// logger.cpp — sketch; build: cl /LD logger.cpp detours.lib /link /OUT:logger.dll
#include <windows.h>
#include <detours.h>
#pragma comment(lib, "detours.lib")

static BOOL (WINAPI *Real_CreateFileW)(LPCWSTR, DWORD, DWORD,
    LPSECURITY_ATTRIBUTES, DWORD, DWORD, HANDLE) = CreateFileW;

BOOL WINAPI Hook_CreateFileW(LPCWSTR name, DWORD access, DWORD share,
    LPSECURITY_ATTRIBUTES sa, DWORD disp, DWORD flags, HANDLE tmpl) {
  log_call("CreateFileW", name, access);          // your sink
  return Real_CreateFileW(name, access, share, sa, disp, flags, tmpl);
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID) {
  if (reason == DLL_PROCESS_ATTACH) {              // rdx==1, see 08-...
    DetourRestoreBeginWithID(0, nullptr);
    DetourTransactionBegin();
    DetourUpdateThread(GetCurrentThread());
    DetourAttach(&(PVOID&)Real_CreateFileW, Hook_CreateFileW);
    DetourTransactionCommit();                     // trampoline = Real_*
  }
  return TRUE;
}
```

Mechanics you must be able to state: an inline hook overwrites the first
bytes of the target with a jump to the hook, and keeps the displaced original
bytes in a **trampoline** (`Real_*`) so the hook can call through. Detours
handles x64 relocation of the stolen instructions; hand-rolled hooks that
naively copy 5/12 bytes without fixing up RIP-relative instructions will
crash — that is the #1 DIY-hooking failure.

MinHook (`MH_CreateHook/MH_EnableHook`) and PolyHook are lighter-weight
alternatives with the same model. Verify hooks took effect
(`MH_CreateHook` returns status; check target bytes `u` in CDB).

## 4. Injection options (get your DLL into the process)

Ordered by intrusiveness:

1. **Frida spawn/attach** — no DLL build at all; start here.
2. **App-initiated** — if the target already loads a configurable DLL
   (plugin systems, `DLL` imports), replace the *name it loads* in a copy and
   proxy the real one (see `14-binary-patching.md` proxy pattern).
3. **`CreateRemoteThread` + `LoadLibraryW`** — the classic flow:
   `OpenProcess` → `VirtualAllocEx` → `WriteProcessMemory` (DLL path) →
   `CreateRemoteThread(LoadLibraryW)`. Lab-only, authorized-only. Watch:
   Loader Lock (don't do heavy work in `DllMain` — spawn a thread or defer),
   architecture must match, and injected threads are trivially detectable
   (fine for lab telemetry, useless for stealth — not a goal here).
4. **`SetWindowsHookEx`** — inject into GUI threads on message delivery;
   fragile, session-scoped; mostly legacy.
5. **Debugger-based** — CDB breakpoint with a command that logs (`08-...`);
   no code in process, slowest, but zero DLL risk.

Record injection method + DLL SHA-256 + build command in provenance.

## 5. IAT hooking (no code bytes touched)

Patch the target's import table entry in memory (page in, make writable,
swap the function pointer, restore protection). Catches all calls that go
through the IAT; **misses** `GetProcAddress`-resolved calls, delay-load
before resolution, and forwarded-API edge cases. Good for quick, reversible
experiments in a debugger:

```text
# in CDB: patch the IAT slot for CreateFileW in module "target"
ed target!__imp_CreateFileW <hook_addr>   # symbol form varies; find via x target!*imp*
```

(IAT symbol availability varies — locate the slot from the import RVA in
`03-...` + module base instead of trusting symbols.)

## 6. VEH — AddVectoredExceptionHandler

First-chance exception *observation* without breakpoints: install a VEH,
log `EXCEPTION_RECORD` (code, address, parameters) for every exception,
`return EXCEPTION_CONTINUE_SEARCH`. Catches exception-driven control flow
(`10-...` §5), fault-based decoding loops, and crash triage in one DLL/script.

## 7. ETW when injection is not allowed

Kernel/OS-level truth without touching the target: process/thread/file/image
events from the OS itself. Capture + decode:

```bat
wpr -start GeneralProfile -filemode
target.exe arg1
wpr -stop run-001.etl
wpa -i "File I/O" run-001.etl   -- or: xperf -i run-001.etl -a fileio > fileio.txt
```

`xperf`/WPA give file+registry+process truth with zero in-process code. Limit:
no function-level args — combine with static knowledge (`05/06`) to name
what you see. Record the provider set (WPR profile name/version).

## 8. Hooking the unpacker (ties to `10-...`)

Runtime dump via hooks instead of a debugger:

1. `Interceptor.attach` on `VirtualAlloc/VirtualProtect/NtProtectVirtualMemory`.
2. Log region addr+size+perms; follow up with `Memory.scan` for the unpacked
   PE (`MZ` at region start or inside).
3. On `write→execute` transition, `readByteArray` the whole region to a file
   (Frida `File` API or `send()` binary message) → save as
   `artifacts/memory/dump-<addr>.bin` + SHA-256 + provenance (which hook,
   which write, when). Re-triage the dump (`02-...`) — raw dump ≠ rebuildable
   EXE (see `10-...` §3).

## 9. Evidence rules (hooks are experiments, not truth)

- Every logged call: process + PID + cmdline + module base at run start.
- Hook scripts are code: hash them (`sha256sum hooks.js`), version them, keep
  them in `case/scripts/`.
- A hooked API hit is **Observed**; "the app does X" is still **Inferred**
  until you show the caller's decision logic (`05-...` static + `08-...`
  return-value checks).
- Detached/lost hooks (target exited, module unloaded mid-run) = partial
  coverage — say so; never present a partial trace as complete behavior.
- Behavior *changes* caused by your hook (timing, extra threads) must be
  stated as limits in the report (`11-...`).

## 10. Common failure modes

- Wrong arg registers (x86 vs x64 vs ARM64EC — re-read `07-...` first).
- Dereferencing an arg that is not a pointer (`connect`'s rdx IS the pointer;
  `CreateFileW`'s rcx needs one `readUtf16String`, not two dereferences).
- Hooking the kernel32 thunk when you needed `KernelBase` (or vice versa) —
  missed calls.
- UTF-16 vs ASCII (`du`/`da` confusion in CDB, `readUtf16String` vs
  `readCString` in Frida).
- Loader-lock deadlock from heavy `DllMain` logging — defer to a thread.
- 32/64-bit mismatch (DLL or Frida arch).
- Assuming hook = coverage: `GetProcAddress` users, direct syscalls
  (`ntdll` hooks miss `syscall`-only stubs), and manually mapped modules all
  bypass IAT hooks.
