# 04 — Managed & Runtime-Heavy EXEs (.NET / Go / Rust / MSVC)

If triage shows huge size, thousands of functions, or runtime strings, do NOT force a C mental model. Identify runtime first or you will waste hours in scaffolding.

## 1. .NET (PE + CLR)

Indicators (any one is enough to branch):

- `mscoree.dll` + `_CorExeMain` import, CLR DataDir non-zero (`pefile`: `pe.OPTIONAL_HEADER.DATA_DIRECTORY[14]`).
- Strings: `v4.0.30319`, `System.`, `mscorlib`, `#Strings/#Blob/#GUID` streams.
- `file` says `PE32 executable (console) ... Mono/.Net assembly`.

CLI workflow (no GUI):

```bash
# confirm CLR header
python3 - "$F" <<'PY'
import pefile, sys
pe=pefile.PE(sys.argv[1])
d=pe.OPTIONAL_HEADER.DATA_DIRECTORY[14]
print(f"CLR VA={hex(d.VirtualAddress)} Size={hex(d.Size)} -> {'DOTNET' if d.Size else 'native'}")
PY
monodis --assembly "$F" 2>/dev/null | head -n 40
ilspycmd "$F" -o "$CASE/artifacts/static/ilspy/" 2> "$OUT/ilspy.stderr" || dotnet-ildasm "$F" || true
# dnfile for metadata without runtime:
python3 -m dnfile "$F" 2>/dev/null | head -n 80 || pip show dnfile
```

Rules:

- Preserve IL + native stubs for mixed-mode (C++/CLI). Obfuscated names (`a.b.c`) ≠ encrypted — try `de4dot` only if authorized and licensed.
- `capa`/`FLOSS` underperform on .NET; use IL + `strings -e l` on `#US` heap.
- Record runtime version (`TargetFramework`) — affects decompiler choice.

## 2. Go

Indicators: `gopclntab`, `Go build`, `golang.org/x/`, huge `.text` + `.rodata`, `runtime.` symbols, no `mscoree`.

```bash
rg -a -o 'Go build[a-z0-9 .,;:-]*' "$F" | head
rz-bin -S "$F" | rg -i 'gopclntab|pclntab'
strings -a "$F" | rg -o 'golang.org[^ ]*|main\.[A-Za-z0-9_]+' | sort -u | head -n 30
# build info (Go >=1.18 embeds it):
go version -m "$F" 2>/dev/null | head -n 40 || true
```

Strategy: ignore `runtime.*`, `type:*`, `reflect` scaffolding. Narrow to `main.*` package + distinctive app strings. Large size ≠ packing. Use `goreconstruct`/`redress` only as helpers; verify in asm.

## 3. Rust

Indicators: `rustc/`, `core::panicked`, `std::`, long mangled `_ZN...` symbols, `panic!` strings.

```bash
rustfilt < "$CASE/artifacts/static/symbols.txt" | head -n 40
strings -a "$F" | rg 'panicked at|core::|alloc::' | head
```

Demangle everywhere (`rustfilt`, `rz-bin` with `bin.demangle=true`). Separate `std/core/alloc` from app logic. Monomorphized generics inflate function count — cluster by `imports-uniq + normalized strings`, don't read in address order.

## 4. MSVC / Clang / MinGW fingerprint

- PDB path (`C:\...\vc143.pdb`), `Rich` header, `MSVC` version strings → MSVC. `GCC:`/`clang version` → MinGW/Clang.
- Equivalent logic compiles differently per toolchain — note toolchain in triage summary; it changes startup (`mainCRTStartup` vs `WinMainCRTStartup`) and SEH shape.
- Startup first: `mainCRTStartup → __scrt_common_main → main`. Don't mistake CRT init for app logic. TLS callbacks + `.CRT$XCU` initializers run before `main` too.

## 5. Senior expectation for this file

State in one paragraph how the runtime changes strategy, e.g.: ".NET → IL-first, native-stub second; Go → pclntab + main-package filter; Rust → demangle + std-exclusion". If you can't state the shift, you haven't branched yet.
