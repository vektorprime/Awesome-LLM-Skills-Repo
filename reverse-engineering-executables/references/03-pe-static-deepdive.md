# 03 — PE Static Deep-Dive (EXE/DLL/SYS)

Use for every Windows executable. Run from Linux VM with Python + Rizin, or Windows Dev prompt with `dumpbin`.

## 1. Header chain (verify manually — loaders lie)

Order: `MZ` → `e_lfanew` → `PE\0\0` → COFF → Optional → Sections → DataDirs.

Fast check with Python (`pefile` preferred, `lief` fallback):

```bash
python3 - "$F" <<'PY'
import sys
pe_path=sys.argv[1]
try:
  import pefile
  pe=pefile.PE(pe_path)
  print(f"Machine={hex(pe.FILE_HEADER.Machine)} NumSections={pe.FILE_HEADER.NumberOfSections}")
  print(f"EntryPoint RVA={hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint)} ImageBase={hex(pe.OPTIONAL_HEADER.ImageBase)}")
  print(f"Subsystem={pe.OPTIONAL_HEADER.Subsystem} Char={hex(pe.FILE_HEADER.Characteristics)} DllChar={hex(pe.OPTIONAL_HEADER.DllCharacteristics)}")
  for s in pe.sections:
    print(f"{s.Name.decode(errors='ignore').strip(chr(0)):8} VSize={hex(s.Misc_VirtualSize)} VAddr={hex(s.VirtualAddress)} RawSize={hex(s.SizeOfRawData)} RawPtr={hex(s.PointerToRawData)} Char={hex(s.Characteristics)} entropy={s.get_entropy():.2f}")
  print("DataDirs:")
  for e in pe.OPTIONAL_HEADER.DATA_DIRECTORY:
    print(f"  {e.name}: VA={hex(e.VirtualAddress)} Size={hex(e.Size)}")
except ImportError:
  print("install pefile: pip install pefile")
PY
```

What each field decides:

- `Machine`: `0x8664`=x64, `0x14c`=x86, `0xaa64`=ARM64. Mismatch with `file` output → investigate.
- `Characteristics`: `0x0002`=executable, `0x2000`=DLL. A `.exe` with DLL flag (or vice versa) is a red flag.
- `Subsystem`: `2`=GUI, `3`=console, `1`=driver. GUI binary with console-only imports is odd.
- `DllCharacteristics`: `0x0040`=ASLR, `0x0100`=NX, `0x4000`=CFG, `0x0080`=SEH. Absence affects debugging/exploitation, not malice.
- `e_lfanew` at file offset `0x3C` (u32le). If it points past EOF → truncated/mangled.

RVA → file offset conversion (required for manual carving):

```text
if RVA in [VirtualAddress, VirtualAddress+max(VirtualSize,RawSize)):
  FileOffset = RVA - VirtualAddress + PointerToRawData
else: RVA is in headers or unmapped (overlay, packed)
```

## 2. Sections — the 60-second verdict

Dump with either:

```bash
rz-bin -S "$F" | tee "$CASE/artifacts/static/pe-sections.txt"
# Windows:
dumpbin /HEADERS sample.exe > pe-headers.txt
```

Checklist:

- [ ] Entry-point RVA falls in executable section (usually `.text`)? If in `UPX1`/`.vmp`/`.rsrc` → packer (see `10-...`).
- [ ] Any `W+X` (writable+executable, char `0xE0000020`+`0x80000000`)? Rare in clean MSVC; normal for packed/self-modifying.
- [ ] `RawSize=0` but `VirtualSize` large? Runtime-filled (unpacking, BSS-like).
- [ ] `RawSize >> VirtualSize`? Overlay-smuggling or appended data.
- [ ] Weird names (`.vmp0`, `.themida`, `UPX0/UPX1`, `.enigma`, single-char)? Packer/protector lead.
- [ ] `.rsrc` entropy >7.5 + large? Embedded PE/icon/encrypted blob — carve it, don't call it "encrypted" yet.

Save section table to `artifacts/static/`.

## 3. Imports — leads, not proof

```bash
rz-bin -i "$F" | tee "$CASE/artifacts/static/pe-imports.txt"
# Windows:
dumpbin /IMPORTS sample.exe > pe-imports.txt
```

High-value families:

| DLL / API | Lead | Must confirm |
|---|---|---|
| `kernel32!CreateFileW,ReadFile,WriteFile` | file access | path args + call site + runtime |
| `kernel32!CreateProcess*,ShellExecute*` | process launch | cmdline + condition |
| `advapi32!RegOpenKey*,RegSetValue*` | persistence | key path + write |
| `ws2_32!connect,WSAConnect`, `wininet!InternetOpen*`, `winhttp!WinHttp*` | networking | endpoint construction + `connect` return |
| `kernel32!VirtualAlloc,VirtualProtect`, `ntdll!NtProtectVirtualMemory` | unpacking/inject | target addr + later execution |
| `kernel32!LoadLibrary*,GetProcAddress` | dynamic resolution | resolved names (break at runtime) |
| `bcrypt!BCrypt*,advapi32!Crypt*` | crypto/hash | algo, key source, data flow |
| `ntdll!NtCreateThreadEx`, `kernel32!CreateRemoteThread,WriteProcessMemory` | injection | target proc + buffer |

Rules:

- Correct spelling is `ws2_32.dll`. APIs forward via API sets (`api-ms-win-*`) and `KernelBase` — confirm resolved target in debugger, don't trust static name.
- Delay imports (`dumpbin /IMPORTS` shows `Delay Load`) and bound imports may hide real IAT. Check DataDir entries 12/13.
- Few imports + `LoadLibrary/GetProcAddress` = resolve dynamically at runtime (see `08-...` for `bu` breakpoints). Do not list "no network imports = no network".
- DLL: check `dumpbin /EXPORTS` — missing exports on a DLL, or `DllMain` doing heavy work, is suspicious.

## 4. Exports, TLS, exceptions (run-before-main)

```bash
rz-bin -E "$F" | tee "$CASE/artifacts/static/pe-exports.txt"
dumpbin /EXPORTS sample.dll > pe-exports.txt
# TLS callbacks run BEFORE entry point:
rz-bin -S "$F" | rg -i tls; dumpbin /HEADERS sample.exe | rg -i -A5 TLS
llvm-objdump --private-headers "$F" | rg -i -A10 "TLS|Exception"
```

TLS callbacks and `DllMain` (`DLL_PROCESS_ATTACH`) execute before `main`. If present, analyze them first. `.pdata`/ExceptionDir on x64 holds unwind info — use for function-boundary recovery when symbols stripped.

## 5. Resources, overlay, certs, Rich header

- Resources (`.rsrc`): enumerate with `rz-bin -z` + `wrestool -l` (Linux) or Resource Hacker (GUI, avoid for CLI). Look for embedded PE (`MZ` inside), scripts, configs. Extract, hash, triage separately.
- Overlay: `SizeOfImage`-beyond-EOF data = installer payload / second stage. Carve: `dd if=sample.exe bs=1 skip=<cert_or_section_end> of=overlay.bin`.
- Authenticode: `osslsigncode verify sample.exe`, `Get-AuthenticodeSignature` (PS). Unsigned system-claimed binary, or valid sig with mismatched subject, both worth noting. Cert does not mean benign.
- Rich header (XOR-obfuscated MSVC build metadata at DOS stub): parse with `pefile` (`pe.RICH_HEADER`) or `richprint`. Gives toolchain versions — useful for Go/Rust/MSVC disambiguation.
- Debug dir: PDB path (`dumpbin /HEADERS | rg pdb`) leaks build host + version. Record it.

## 6. What to save

`artifacts/static/pe-{info,sections,imports,exports,resources,authenticode}.txt` + `pe-parse.json` (pefile dump). Mark every capability `Inferred/Low` until `05-...` (call site) and `08-...` (runtime) confirm.
