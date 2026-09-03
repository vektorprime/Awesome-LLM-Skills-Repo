# 02 — Triage Without Executing (EXE-First)

Goal: in <15 min classify format/arch/runtime/protections and pick the next 3 commands. No execution.

Setup:

```bash
CASE=case-2026-001
F="$CASE/evidence/original.bin"
OUT="$CASE/artifacts/triage"
mkdir -p "$OUT"
```

For full automation use `scripts/triage.sh` (Linux) or `scripts/triage-exe.ps1` (Windows). Below is what each step proves.

## 1. Identity + first/last bytes

```bash
file -k -- "$F" | tee "$OUT/file.txt"
xxd -g 1 -l 512 -- "$F" | tee "$OUT/head-512.txt"
xxd -g 1 -s -512 -- "$F" | tee "$OUT/tail-512.txt"
```

Interpret:

- `PE32+` = 64-bit EXE, `PE32` = 32-bit, `PE32+ DLL` / `ET_DYN` = DLL. `Mach-O`, `ELF`, `Java class`, `WebAssembly`, `Zip` (JAR/APK), `SQLite`, `CAB/MSIX` each force a different branch.
- `data` means libmagic has no signature — not "no structure". Compare magic yourself: EXE must start `4D 5A` (MZ), offset `0x3C` holds `e_lfanew` → `50 45 00 00` (PE\0\0). If extension says `.exe` but magic is `PK`/`ELF`/`MZ`-less, record spoofing.
- Tail often holds overlay / installer payload / certificate padding. Non-zero tail on a tiny EXE → check overlay in `03-pe-static-deepdive.md`.

Expected:

```text
$ file -k sample.exe
sample.exe: PE32+ executable (console) x86-64, for MS Windows
```

If `file` says `PE32+` but `xxd` shows `MZ` missing → truncated/corrupt or intentionally mangled.

## 2. Hashes

```bash
sha256sum "$F" | tee "$OUT/sha256.txt"
sha1sum "$F"   | tee "$OUT/sha1.txt"
md5sum "$F"    | tee "$OUT/md5.txt"  # compat only
```

SHA-256 is the evidence ID. Use it as directory key for batch sets.

## 3. Strings (ASCII + UTF-16LE is mandatory for EXE)

```bash
strings -a -n 5 -t x -- "$F" | tee "$OUT/strings-ascii.txt"
strings -a -n 5 -e l -t x -- "$F" | tee "$OUT/strings-utf16le.txt"
rg -n -i 'https?://|wss?://|user-agent|authorization|password|passwd|token|api[_-]?key|cmd\.exe|powershell|rundll32|regsvr32|\\\\[A-Za-z]|/etc/|/proc/|mutex|SOFTWARE\\Microsoft|Run\\\\' "$OUT"/strings-*.txt | tee "$OUT/strings-interesting.txt" || true
```

EXE-specific tells:

- `C:\...\.pdb`, `vctools`, `MSVC`, `Rich` → MSVC build, PDB path leaks version.
- `mscoree.dll`, `_CorExeMain`, `v4.0.30319`, `System.` → .NET (go to `04-managed-runtimes.md`).
- `gopclntab`, `Go build`, `golang` → Go. `panic:`, `core::panicked` → Rust.
- `UPX!`, `Themida`, `VMProtect`, `.vmp`, `Enigma` → packer (go to `10-packing...`).
- `ws2_32.dll` (note spelling: `ws2_32`, not `ws232`), `WinHttp`, `WSAConnect`, `InternetOpen` → networking lead only.

A string is never proof. Mark every hit `Inferred/Low` until call site + runtime confirm.

FLOSS (decodes stack/XOR-obfuscated strings):

```bash
floss -j "$F" > "$OUT/floss.json" 2> "$OUT/floss.stderr" || true
jq -r '.. | strings? // empty' "$OUT/floss.json" 2>/dev/null | rg -i 'https?://|password|token|cmd\.exe|powershell|rundll32' | tee "$OUT/floss-interesting.txt" || true
```

FLOSS misses .NET resources and Go strings; absence proves nothing.

## 4. Compiler/packer heuristics (DiE)

```bash
diec "$F" | tee "$OUT/diec.txt"
diec -j "$F" > "$OUT/diec.json" 2> "$OUT/diec.stderr" || true
```

Treat as heuristic. Confirm with section names + import plausibility + entry-point section (see `03-...`). Record DiE version.

## 5. Cross-format inventory (Rizin-first)

Prefer `rz-bin`; fall back to `rabin2` (radare2). Flags are near-identical:

```bash
rz-bin -Ij  "$F" > "$OUT/info.json"    2> "$OUT/info.stderr"    || rabin2 -Ij  "$F" > "$OUT/info.json" 2> "$OUT/info.stderr" || true
rz-bin -Sj  "$F" > "$OUT/sections.json" 2> "$OUT/sections.stderr" || true
rz-bin -ij  "$F" > "$OUT/imports.json"  2> "$OUT/imports.stderr"  || true
rz-bin -Ej  "$F" > "$OUT/exports.json"  2> "$OUT/exports.stderr"  || true
rz-bin -zzj "$F" > "$OUT/strings.json"  2> "$OUT/strings.stderr"  || true
jq -r '.sections[]? | [.name,.size,.vsize,.perm] | @tsv' "$OUT/sections.json" | column -t | tee "$OUT/sections.tsv"
jq -r '.imports[]?.name' "$OUT/imports.json" | sort -u | tee "$OUT/imports-uniq.txt"
```

Red flags for EXE:

- Entry point in non-`.text` (e.g. `UPX1`, `.vmp`, `.themida`) → packer.
- 1–5 imports + `LoadLibraryA + GetProcAddress + VirtualProtect` → dynamic resolution / packing.
- `WX` (writable+executable) section, `RawSize=0` but `VirtualSize` huge → unpacking stub.
- No exports on DLL, or EXE with huge export table → suspicious.

## 6. capa + YARA

```bash
capa -j "$F" > "$OUT/capa.json" 2> "$OUT/capa.stderr" || true
capa "$F" | tee "$OUT/capa.txt" || true
yara -r /path/to/approved/rules "$F" | tee "$OUT/yara.txt" || true
```

Use capa to prioritize manual review. For each interesting match (`anti-debug`, `inject`, `persistence`), record ATT&CK + function address, then verify at call site. Log YARA ruleset commit.

## 7. Entropy map (use script, don't eyeball)

```bash
python3 scripts/entropy.py "$F" > "$OUT/entropy.csv"
sort -t, -k3,3nr "$OUT/entropy.csv" | head -n 20 | tee "$OUT/entropy-top.txt"
```

Ask in order:

1. Does high-entropy region align with a named section or resource? (`UPX1` + 7.9 = packer; `.rsrc` + 7.9 = embedded payload/image, not crypto.)
2. Is region large enough (>4KB)? Tiny regions give noisy entropy.
3. Is there a decoder/decompressor xref to it? No decoder → stays `Unknown/Low`.

## 8. Deliverable

Fill `checklists/triage-summary-template.md` → `notes/triage-summary.md`. Must include Confirmed format, arch, entry-point section, strong observations vs heuristic leads, execution decision, and **next 3 commands** (forces prioritization, e.g. `rz-bin -S`, `dumpbin /IMPORTS`, `capa -vv`).
