# CLI-First Reverse Engineering Field Guide

**Audience:** Security engineers who work primarily from terminals  
**Goal:** Develop repeatable reverse-engineering judgment, not just familiarity with tools  
**Scope:** Authorized analysis of native executables, libraries, firmware, and unknown binary data formats  
**Operating principle:** Every conclusion must be traceable to a command, an artifact, and a confidence level

> A document cannot make an engineer senior by itself. Senior performance comes from forming good hypotheses, choosing the cheapest decisive test, preserving evidence, explaining uncertainty, automating repeatable work, and producing conclusions that another analyst can reproduce. This guide is organized around those behaviors.

---

## 1. What Changed from the Previous Tutorial

The previous tutorial had a useful high-level analysis loop, but it was not aligned with a CLI-only engineer and it left too much expert judgment implicit. This version makes the following changes:

- Replaces GUI-first workflows with shell commands, terminal debuggers, scriptable analysis, JSON output, and headless decompilation.
- Separates native executables, managed binaries, and data/firmware formats before deep analysis.
- Treats entropy as a clue rather than proof of packing or encryption.
- Adds evidence handling, reproducibility requirements, confidence labels, stop conditions, and escalation criteria.
- Adds architecture and ABI fundamentals, concrete decision points, expected observations, and common failure modes.
- Adds safe exercises, an accelerated progression plan, and a senior-level assessment rubric.
- Corrects several technical problems, including the `ws2_32.dll` name, the limitations of `ltrace`, and over-broad unpacking guidance.

---

## 2. Senior-Level Outcomes

A senior reverse engineer should be able to do more than identify APIs or recover pseudocode. The engineer should consistently produce these outcomes:

1. **Rapid classification** — identify format, architecture, execution model, likely toolchain, protection indicators, and the next best test.
2. **Evidence-driven hypotheses** — distinguish observed facts from inferences and guesses.
3. **Cross-layer reasoning** — connect file metadata, assembly, decompiler output, runtime traces, memory state, and external behavior.
4. **Efficient narrowing** — find the small set of functions, records, or runtime events that answer the question.
5. **Reproducibility** — preserve hashes, commands, tool versions, raw output, scripts, and analysis notes.
6. **Automation** — turn repetitive inspection into scripts without hiding uncertainty or tool failures.
7. **Communication** — explain capabilities, limitations, risk, and confidence to engineers, responders, and leadership.
8. **Technical leadership** — define scope, stop unsafe execution, identify when specialist help is needed, and review another analyst's work.

### Definition of done

An analysis is not complete because the analyst has “looked through the binary.” It is complete when the original question has a defensible answer and the evidence package allows a second analyst to reproduce the result.

---

## 3. Rules of Engagement and Safety

Only analyze software and data you are authorized to inspect. Confirm legal, contractual, privacy, and export-control constraints before beginning. Do not upload proprietary samples to public scanning services unless the data owner has explicitly approved it.

Treat every unknown executable as hostile until demonstrated otherwise.

### Minimum isolation standard

Use a disposable analysis VM with:

- A known-good snapshot.
- No shared clipboard, shared folders, host filesystem mounts, or host credentials.
- No production network access.
- Host-only, simulated, or fully disabled networking.
- A non-administrator analysis account unless elevated privileges are required for a specific observation.
- Centralized time and command logging when the engagement requires auditability.

A container, `chroot`, `firejail`, or namespace is not a complete security boundary for an unknown kernel-facing binary. They may be useful as additional controls inside a disposable VM.

### Execution gate

Do not execute a sample until all five questions have explicit answers:

1. What exact question requires execution?
2. What behavior will be observed?
3. What containment controls are active?
4. What data can the sample reach?
5. What event will cause the run to stop?

If static evidence already answers the question, do not execute the sample.

---

## 4. Evidence Model

Use three labels in notes and reports:

- **Observed** — directly produced by a command, trace, or controlled experiment.
- **Inferred** — the best explanation of multiple observations, but not directly proven.
- **Unknown** — insufficient evidence, conflicting evidence, or an untested hypothesis.

Use confidence labels:

- **High:** independently confirmed by at least two strong sources, or directly demonstrated in a controlled run.
- **Medium:** supported by one strong source or several weaker indicators.
- **Low:** plausible but not yet tested, or dependent on a heuristic tool result.

Example:

| Statement | Status | Confidence | Evidence |
|---|---|---:|---|
| The file is an x86-64 ELF PIE | Observed | High | `file`, `readelf -h`, `rabin2 -Ij` |
| The program probably opens a TLS connection | Inferred | Medium | imports `connect`, `SSL_new`, hostname string |
| The embedded payload is encrypted | Unknown | Low | high-entropy region only; no decoder confirmed |

Never write “the binary is encrypted” when the only evidence is high entropy.

---

## 5. Case Workspace

Create one case directory per sample or tightly related sample set.

```text
case-2026-001/
├── evidence/
│   ├── original.bin
│   ├── hashes.txt
│   └── provenance.md
├── artifacts/
│   ├── triage/
│   ├── static/
│   ├── dynamic/
│   ├── memory/
│   └── extracted/
├── scripts/
├── notes/
│   ├── timeline.md
│   ├── hypotheses.md
│   └── decisions.md
├── report/
└── tool-versions.txt
```

### Initialize the case

```bash
set -Eeuo pipefail
umask 077

CASE=case-2026-001
SAMPLE=/path/to/authorized/sample

mkdir -p "$CASE"/{evidence,artifacts/{triage,static,dynamic,memory,extracted},scripts,notes,report}
cp --reflink=auto --preserve=mode,timestamps -- "$SAMPLE" "$CASE/evidence/original.bin"
chmod 0444 "$CASE/evidence/original.bin"
sha256sum "$CASE/evidence/original.bin" | tee "$CASE/evidence/hashes.txt"
sha1sum "$CASE/evidence/original.bin" >> "$CASE/evidence/hashes.txt"
stat --printf='size=%s bytes\nmtime=%y\ninode=%i\n' "$CASE/evidence/original.bin" \
  | tee "$CASE/artifacts/triage/stat.txt"
```

Work on a copy. Preserve the original read-only. Hash every extracted or transformed artifact and document the relationship to its parent.

### Record tool versions

```bash
{
  date --iso-8601=seconds
  uname -a
  file --version | head -n 1
  objdump --version | head -n 1
  readelf --version | head -n 1
  r2 -v 2>/dev/null || true
  rabin2 -v 2>/dev/null || true
  gdb --version | head -n 1
  strace --version | head -n 1
  python3 --version
  floss --version 2>/dev/null || true
  capa --version 2>/dev/null || true
  yara --version 2>/dev/null || true
  binwalk --version 2>/dev/null || true
} | tee "$CASE/tool-versions.txt"
```

Pin tool versions for long-running investigations. Heuristic output can change between releases.

---

## 6. The CLI Analysis Loop

Use the same loop throughout the case:

```text
Question
  -> cheapest safe observation
  -> hypothesis
  -> decisive test
  -> preserve artifact
  -> update confidence
  -> next question or stop
```

A practical decision tree:

```text
[Unknown file]
      |
      v
[Hash, metadata, magic, format]
      |
      +--> Native executable/library? --> ELF / PE / Mach-O workflow
      |
      +--> Managed/runtime image? -----> .NET / JVM / Go / Rust-aware workflow
      |
      +--> Archive/firmware/data? -----> carving / differential / parser workflow
      |
      +--> Still unknown? -------------> raw architecture and entropy mapping

Deep analysis only after the branch is justified.
```

---

# Part I — Rapid Triage

## 7. Triage Without Executing the Sample

Set a convenient variable:

```bash
CASE=case-2026-001
F="$CASE/evidence/original.bin"
OUT="$CASE/artifacts/triage"
mkdir -p "$OUT"
```

### 7.1 Identity and first bytes

```bash
file -k -- "$F" | tee "$OUT/file.txt"
stat --printf='%n\nsize=%s\nmode=%A\nmtime=%y\n' "$F" | tee "$OUT/stat.txt"
xxd -g 1 -l 512 -- "$F" | tee "$OUT/head-512.txt"
xxd -g 1 -s -512 -- "$F" | tee "$OUT/tail-512.txt"
```

Interpretation:

- `ELF`, `PE32`, `PE32+`, `Mach-O`, Java class, WebAssembly, archive, filesystem, or document signatures establish the first branch.
- “data” means only that the signature database did not identify the file. It does not mean the file lacks structure.
- Compare the first bytes to the parser's claimed format. File extensions are untrusted metadata.

### 7.2 Hashes and fuzzy context

```bash
sha256sum "$F" | tee "$OUT/sha256.txt"
sha1sum "$F" | tee "$OUT/sha1.txt"
md5sum "$F" | tee "$OUT/md5.txt"   # compatibility only; not an integrity guarantee
```

Use cryptographic hashes for evidence identity. Similarity hashes may be useful for clustering, but they are not identity proofs.

### 7.3 Strings

```bash
strings -a -n 5 -t x -- "$F" | tee "$OUT/strings-ascii.txt"
strings -a -n 5 -e l -t x -- "$F" | tee "$OUT/strings-utf16le.txt"
strings -a -n 5 -e b -t x -- "$F" | tee "$OUT/strings-utf16be.txt"
```

Useful searches:

```bash
rg -n -i \
  'https?://|wss?://|user-agent|authorization|password|token|cmd\.exe|powershell|/bin/(sh|bash)|/etc/|/proc/|registry|mutex|\\\\' \
  "$OUT"/strings-*.txt | tee "$OUT/strings-interesting.txt"
```

Do not treat a string as proof of behavior. It may be unused, test data, a library artifact, or deliberately planted.

If FLOSS is available:

```bash
floss -j "$F" > "$OUT/floss.json" 2> "$OUT/floss.stderr" || true
jq -r '.. | strings' "$OUT/floss.json" 2>/dev/null \
  | rg -i 'https?://|password|token|cmd\.exe|powershell|/bin/' \
  | tee "$OUT/floss-interesting.txt" || true
```

FLOSS can recover several classes of decoded and stack strings. Its output is still a lead, not a final conclusion.

### 7.4 Signature and compiler/packer hints

If Detect It Easy's console program is available:

```bash
diec "$F" | tee "$OUT/diec.txt"
diec -j "$F" > "$OUT/diec.json" 2> "$OUT/diec.stderr" || true
```

Treat compiler and packer identification as heuristic unless confirmed by structural evidence.

### 7.5 Cross-format inventory with `rabin2`

```bash
rabin2 -Ij  "$F" > "$OUT/rabin-info.json"    2> "$OUT/rabin-info.stderr"    || true
rabin2 -Sj  "$F" > "$OUT/rabin-sections.json" 2> "$OUT/rabin-sections.stderr" || true
rabin2 -ij  "$F" > "$OUT/rabin-imports.json"  2> "$OUT/rabin-imports.stderr"  || true
rabin2 -Ej  "$F" > "$OUT/rabin-exports.json"  2> "$OUT/rabin-exports.stderr"  || true
rabin2 -zzj "$F" > "$OUT/rabin-strings.json"  2> "$OUT/rabin-strings.stderr"  || true
```

Inspect compact summaries:

```bash
jq . "$OUT/rabin-info.json" | less
jq -r '.sections[]? | [.name,.size,.vsize,.perm] | @tsv' "$OUT/rabin-sections.json" | column -t
jq -r '.imports[]?.name' "$OUT/rabin-imports.json" | sort -u | less
```

### 7.6 Capability heuristics with `capa`

For supported executable and runtime formats:

```bash
capa -j "$F" > "$OUT/capa.json" 2> "$OUT/capa.stderr" || true
capa -vv "$F" | tee "$OUT/capa-verbose.txt" || true
```

Use capa to prioritize manual analysis. A capability match should be checked against the underlying function and evidence. A missing match does not prove a capability is absent.

### 7.7 YARA classification

```bash
yara -r /path/to/approved/rules "$F" | tee "$OUT/yara.txt"
```

Use internally reviewed rule sets. Record the rule repository commit or release with the case.

### 7.8 Embedded content and firmware signatures

```bash
binwalk "$F" | tee "$OUT/binwalk.txt"
```

Binwalk v3 differs from older tutorials. Check `binwalk --help` before using extraction switches, run extraction in a disposable directory, and inspect the proposed offsets before trusting carved output.

### 7.9 Entropy map

Entropy is useful for locating regions whose byte distribution differs from their surroundings. It cannot by itself distinguish compression, encryption, encoded media, randomized tables, or short noisy data.

Create a windowed entropy map:

```bash
python3 - "$F" > "$OUT/entropy.csv" <<'PY'
import math
import pathlib
import sys
from collections import Counter

path = pathlib.Path(sys.argv[1])
data = path.read_bytes()
window = 4096
step = 4096
print("offset,size,entropy")
for off in range(0, len(data), step):
    block = data[off:off + window]
    if not block:
        break
    counts = Counter(block)
    n = len(block)
    entropy = -sum((c / n) * math.log2(c / n) for c in counts.values())
    print(f"0x{off:08x},{n},{entropy:.5f}")
PY

sort -t, -k3,3nr "$OUT/entropy.csv" | head -n 20 | tee "$OUT/entropy-top.txt"
```

Ask:

- Does a high-entropy region align with a named section or an embedded object?
- Is executable code compressed into a writable region?
- Is the region large enough for the estimate to be meaningful?
- Can a decompressor, decoder loop, or format signature explain it?

### 7.10 Triage deliverable

Write `notes/triage-summary.md` with:

```markdown
## Identity
- SHA-256:
- Size:
- Claimed format:
- Confirmed format:
- Architecture / bitness / endianness:
- Entry point or first structure offset:

## Strong observations
- 

## Heuristic leads
- 

## Unknowns
- 

## Execution decision
- Execute: yes/no
- Question requiring execution:
- Required controls:

## Next three commands
1. 
2. 
3. 
```

The “next three commands” requirement forces prioritization.

---

## 8. Triage Automation Script

Save as `scripts/triage.sh`:

```bash
#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

usage() {
  echo "usage: $0 SAMPLE CASE_DIR" >&2
  exit 64
}

[[ $# -eq 2 ]] || usage
sample=$(readlink -f -- "$1")
case_dir=$2
[[ -f "$sample" ]] || { echo "not a regular file: $sample" >&2; exit 66; }

mkdir -p "$case_dir"/{evidence,artifacts/triage,notes,scripts}
copy="$case_dir/evidence/original.bin"

if [[ ! -e "$copy" ]]; then
  cp --reflink=auto --preserve=mode,timestamps -- "$sample" "$copy"
  chmod 0444 "$copy"
fi

out="$case_dir/artifacts/triage"
log="$out/commands.log"
: > "$log"

run() {
  local name=$1
  shift
  printf '$' >> "$log"
  printf ' %q' "$@" >> "$log"
  printf '\n' >> "$log"
  "$@" > "$out/$name.stdout" 2> "$out/$name.stderr" || {
    rc=$?
    printf '%s\t%s\n' "$name" "$rc" >> "$out/failures.tsv"
    return 0
  }
}

sha256sum "$copy" | tee "$case_dir/evidence/hashes.txt"
sha1sum "$copy" >> "$case_dir/evidence/hashes.txt"

run file file -k -- "$copy"
run stat stat --printf='%n\nsize=%s\nmode=%A\nmtime=%y\n' "$copy"
run head xxd -g 1 -l 512 -- "$copy"
run tail xxd -g 1 -s -512 -- "$copy"
run strings-ascii strings -a -n 5 -t x -- "$copy"
run strings-utf16le strings -a -n 5 -e l -t x -- "$copy"

command -v rabin2 >/dev/null && {
  run rabin-info rabin2 -Ij "$copy"
  run rabin-sections rabin2 -Sj "$copy"
  run rabin-imports rabin2 -ij "$copy"
  run rabin-exports rabin2 -Ej "$copy"
  run rabin-strings rabin2 -zzj "$copy"
}

command -v diec >/dev/null && run diec diec "$copy"
command -v floss >/dev/null && run floss floss -j "$copy"
command -v capa >/dev/null && run capa capa -j "$copy"
command -v binwalk >/dev/null && run binwalk binwalk "$copy"

find "$case_dir/evidence" "$case_dir/artifacts" -type f -print0 \
  | sort -z \
  | xargs -0 sha256sum > "$case_dir/artifacts/SHA256SUMS"

printf 'triage complete: %s\n' "$case_dir"
```

Validate the script before team use:

```bash
bash -n scripts/triage.sh
shellcheck scripts/triage.sh
```

The script intentionally continues when optional tools fail. Tool failure is an artifact that must remain visible, not a reason to silently omit a step.

---

# Part II — Format-Specific Static Analysis

## 9. Branch A: ELF Executables and Shared Libraries

### 9.1 Header, program headers, and sections

```bash
readelf -hW "$F" | tee "$CASE/artifacts/static/elf-header.txt"
readelf -lW "$F" | tee "$CASE/artifacts/static/elf-program-headers.txt"
readelf -SW "$F" | tee "$CASE/artifacts/static/elf-sections.txt"
readelf -dW "$F" | tee "$CASE/artifacts/static/elf-dynamic.txt"
readelf -nW "$F" | tee "$CASE/artifacts/static/elf-notes.txt"
```

Questions:

- Is the file `ET_EXEC`, `ET_DYN` as PIE/shared object, or `ET_REL`?
- Which program header is executable?
- Do section permissions disagree with segment permissions?
- Is there an interpreter such as `/lib64/ld-linux-x86-64.so.2`?
- Are unusual `RWE` segments present?
- Are section headers absent even though program headers are valid?

A stripped ELF may still be fully analyzable from program headers, dynamic symbols, relocation tables, unwind information, and runtime behavior.

### 9.2 Symbols, imports, relocations, and dependencies

```bash
readelf -sW "$F" | tee "$CASE/artifacts/static/elf-symbols.txt"
readelf -rW "$F" | tee "$CASE/artifacts/static/elf-relocations.txt"
objdump -T "$F" | tee "$CASE/artifacts/static/elf-dynamic-symbols.txt"
objdump -p "$F" | tee "$CASE/artifacts/static/elf-private-headers.txt"
```

Do not use `ldd` on an untrusted executable. Some historical and nonstandard implementations may execute code or invoke the dynamic loader in unsafe ways. Prefer:

```bash
readelf -dW "$F" | rg 'NEEDED|RPATH|RUNPATH'
objdump -p "$F" | rg 'NEEDED|RPATH|RUNPATH'
```

### 9.3 Security properties

```bash
rabin2 -I "$F" | tee "$CASE/artifacts/static/security-properties.txt"
```

Check PIE, NX, stack canary, RELRO, and stripped status. These properties affect exploitation and debugging but do not establish whether the binary is benign or malicious.

### 9.4 Disassembly

```bash
objdump -d -M intel --disassemble-zeroes "$F" \
  | tee "$CASE/artifacts/static/objdump-intel.txt"
objdump -s "$F" | tee "$CASE/artifacts/static/objdump-contents.txt"
```

For another architecture, use an appropriate cross-binutils or LLVM build:

```bash
llvm-objdump --file-headers --section-headers --syms --disassemble "$F"
```

### 9.5 Initial function prioritization

Start from:

- Entry point.
- Exported functions.
- Constructors in `.init_array`.
- References to distinctive strings.
- Imports associated with the question.
- Large functions with many branches.
- Functions that touch input buffers, cryptographic constants, parsers, filesystem paths, or sockets.

Avoid reading every function in address order.

---

## 10. Branch B: PE Executables and DLLs

The CLI workflow can run on Windows or from a Linux analysis VM using cross-platform parsers.

### 10.1 Cross-platform inventory

```bash
rabin2 -I  "$F" | tee "$CASE/artifacts/static/pe-info.txt"
rabin2 -S  "$F" | tee "$CASE/artifacts/static/pe-sections.txt"
rabin2 -i  "$F" | tee "$CASE/artifacts/static/pe-imports.txt"
rabin2 -E  "$F" | tee "$CASE/artifacts/static/pe-exports.txt"
rabin2 -zz "$F" | tee "$CASE/artifacts/static/pe-strings.txt"
llvm-objdump --private-headers --section-headers --syms "$F" \
  | tee "$CASE/artifacts/static/pe-llvm.txt"
```

### 10.2 Microsoft command-line tools

From a Developer Command Prompt:

```bat
dumpbin /HEADERS sample.exe > pe-headers.txt
dumpbin /IMPORTS sample.exe > pe-imports.txt
dumpbin /EXPORTS sample.dll > pe-exports.txt
dumpbin /DEPENDENTS sample.exe > pe-dependents.txt
```

### 10.3 High-value PE questions

- Is the entry point in an executable section?
- Does the section table contain raw/virtual size anomalies?
- Are writable and executable permissions combined?
- Is the import table plausible for the program's claimed purpose?
- Are imports resolved normally or dynamically through `LoadLibrary*` and `GetProcAddress`?
- Does the file contain TLS callbacks that run before the nominal entry point?
- Are resources, overlays, certificates, debug paths, or embedded PEs present?
- Is the binary a .NET assembly? Check the CLR data directory and metadata rather than treating it as ordinary native code.

Correct networking library name: `ws2_32.dll`, not `ws232.dll`.

### 10.4 Import interpretation examples

Imports are leads, not proof:

| Import family | Possible meaning | Required confirmation |
|---|---|---|
| `CreateFile*`, `ReadFile`, `WriteFile` | file access | arguments and call sites |
| `RegOpenKey*`, `RegSetValue*` | registry access | key path and write semantics |
| `WinHttp*`, `Internet*`, `WSA*` | networking | endpoint construction and runtime call |
| `VirtualAlloc`, `VirtualProtect` | memory management or unpacking | permissions, destination, subsequent execution |
| `CreateProcess*`, `ShellExecute*` | process launch | command line and conditions |
| `Crypt*`, `BCrypt*` | cryptography or hashing | algorithm, key source, data flow |

Common libraries import broad APIs that an application never invokes directly.

---

## 11. Branch C: Mach-O

```bash
file -k "$F"
llvm-objdump --macho --private-header "$F"
llvm-objdump --macho --dylibs-used "$F"
llvm-objdump --macho --exports-trie "$F"
llvm-objdump --macho --syms "$F"
llvm-objdump --macho --disassemble "$F"
```

For universal binaries, identify and analyze each architecture slice separately. Record code-signing and entitlements information where relevant to the investigation.

---

## 12. Branch D: Managed and Language-Specific Binaries

Compiler and runtime artifacts can dominate a binary. Recognizing them prevents wasted effort.

### 12.1 .NET

Indicators:

- PE file with CLR header and metadata streams.
- Imports often center on `mscoree.dll`.
- Rich type and method metadata may remain even when symbol names are altered.

CLI options include `ildasm` from Microsoft tooling, `monodis`, `dotnet` metadata utilities, `rabin2`, and language-specific decompilers that provide command-line operation. Preserve both IL and native stubs when mixed-mode code is present.

### 12.2 JVM and Android

```bash
javap -classpath . -c -p -s -verbose ClassName | tee javap.txt
unzip -l application.jar | tee jar-list.txt
```

For Android packages, separate ZIP/APK structure, DEX bytecode, native libraries, resources, signing metadata, and manifest behavior.

### 12.3 Go

Go binaries often contain runtime metadata, type names, package paths, build information, and many statically linked functions. Do not interpret their large size or symbol profile as packing. Identify runtime scaffolding, then narrow to application packages and distinctive strings.

### 12.4 Rust

Rust binaries may contain long mangled symbols, panic strings, trait machinery, and monomorphized functions. Demangle symbols where available and distinguish standard-library code from application logic.

### 12.5 Senior expectation

The analyst should explain how the runtime changes the analysis strategy instead of forcing every binary through the same native C mental model.

---

# Part III — CLI Code Analysis

## 13. Radare2 Core Workflow

Radare2 is the default interactive CLI in this guide. Rizin may be substituted if the team standardizes on it, but commands and plugins are not always identical.

### 13.1 Start read-only and analyze

```bash
r2 -e io.cache=true -A "$F"
```

Inside radare2:

```text
?                 # help
q                 # quit
iI                # binary information
iS                # sections
ii                # imports
iE                # exports
izz               # strings, including raw strings
afl               # functions
s entry0          # seek to entry point
pdf               # disassemble current function
pdc               # built-in pseudo-decompiler
```

Radare2 has multiple analysis depths. `-A` is a reasonable starting point, but deeper analysis is not automatically better. It can be slow and may create false functions in data. Use `aaa?` to inspect available analysis passes and apply them deliberately.

### 13.2 JSON-first batch output

```bash
r2 -q -A -c 'aflj' "$F" > "$CASE/artifacts/static/functions.json"
r2 -q -A -c 'izj'  "$F" > "$CASE/artifacts/static/r2-strings.json"
r2 -q -A -c 'iij'  "$F" > "$CASE/artifacts/static/r2-imports.json"

jq -r '.[] | [.offset,.size,.name] | @tsv' "$CASE/artifacts/static/functions.json" \
  | sort -k2,2nr | head -n 30 | column -t
```

### 13.3 Navigate from a string

```text
izz~password                 # search the string list
s <string-address>           # seek to the string
axt                           # show references to current address
s <xref-address>
pdf                           # inspect the containing function
```

Alternative batch form:

```bash
r2 -q -A -c 'izz~password' "$F"
r2 -q -A -c 'axt @ <address>' "$F"
```

A high-value string is an anchor. The function referencing it is the beginning of an analysis path, not necessarily the function that implements the behavior.

### 13.4 Navigate from an import

```text
ii~connect
s sym.imp.connect
axt
```

Follow callers upward until reaching application logic that prepares arguments and handles the result.

### 13.5 Rename and comment

```text
af                       # ensure current function exists
afn parse_config         # rename current function
CC validates header and dispatches record parsers
```

At an explicit address:

```text
afn decode_record @ 0x00401230
CC XOR-decodes record payload using per-file key @ 0x00401230
```

Use names that express demonstrated behavior. Prefer `build_request_headers` to `network_function`. Add suffixes such as `_likely` when the identification is provisional.

### 13.6 Signatures and types

Radare2's type commands vary by workflow and version. Use command help before applying a change:

```text
afs?                      # function signature help
td?                       # type-definition help
pf?                       # formatted data help
```

A corrected function prototype can improve calling-convention recovery and pseudocode substantially. Record why each type was assigned.

### 13.7 Decompilers

The built-in `pdc` provides pseudocode. Optional plugins include:

```text
pdd                       # r2dec, when installed
pdg                       # r2ghidra, when installed
```

Check availability with `e cmd.pdc=?` or command help. Decompiler output is a lossy model. Verify critical arithmetic, signedness, bounds, and control flow in assembly.

### 13.8 Save analysis state

Use a project rather than relying on shell history. Project command details can vary by release; inspect `P?` and save a named project according to the installed version. Also export names and comments to a script or JSON artifact when the case requires long-term portability.

### 13.9 A disciplined function note

For each important function, capture:

```markdown
### `parse_config` at `0x401230`

**Purpose:** Parses a length-prefixed configuration buffer.

**Inputs:**
- `rdi`: destination configuration structure
- `rsi`: input buffer
- `rdx`: input length

**Outputs:**
- `eax = 0` on success
- negative error code on failure

**Observed behavior:**
- checks four-byte magic at offset 0
- validates declared length against input length
- dispatches records by one-byte type

**Open questions:**
- unknown semantics of record type 7
- checksum algorithm not confirmed

**Evidence:**
- disassembly addresses
- xrefs
- runtime watchpoint or test input
```

---

## 14. Headless Ghidra

Ghidra's headless analyzer supports automated import, analysis, and scripts without opening the user interface.

### 14.1 Import and analyze

```bash
GHIDRA_HOME=/opt/ghidra
PROJECT_DIR="$CASE/artifacts/static/ghidra-projects"
PROJECT_NAME=case001
mkdir -p "$PROJECT_DIR"

"$GHIDRA_HOME/support/analyzeHeadless" \
  "$PROJECT_DIR" "$PROJECT_NAME" \
  -import "$F" \
  -overwrite
```

Use `analyzeHeadless -help` from the installed release as the source of truth for flags.

### 14.2 Headless export script

Save as `scripts/ExportFunctions.py` in a configured Ghidra script path:

```python
#@category RE

from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor
import os

args = getScriptArgs()
if len(args) != 1:
    raise RuntimeError("usage: ExportFunctions.py OUTPUT_DIR")

out_dir = args[0]
if not os.path.isdir(out_dir):
    os.makedirs(out_dir)

iface = DecompInterface()
iface.openProgram(currentProgram)
monitor = ConsoleTaskMonitor()
fm = currentProgram.getFunctionManager()

index_path = os.path.join(out_dir, "functions.tsv")
with open(index_path, "w") as index:
    index.write("entry\tname\tsize\tdecompiled\n")
    for func in fm.getFunctions(True):
        entry = str(func.getEntryPoint())
        name = func.getName()
        body_size = func.getBody().getNumAddresses()
        result = iface.decompileFunction(func, 60, monitor)
        ok = result.decompileCompleted()
        index.write("%s\t%s\t%s\t%s\n" % (entry, name, body_size, ok))
        if not ok:
            continue
        safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in name)
        path = os.path.join(out_dir, "%s_%s.c" % (entry, safe))
        with open(path, "w") as fh:
            fh.write(str(result.getDecompiledFunction().getC()))

iface.dispose()
```

Run it:

```bash
mkdir -p "$CASE/artifacts/static/ghidra-decompile"

"$GHIDRA_HOME/support/analyzeHeadless" \
  "$PROJECT_DIR" "$PROJECT_NAME" \
  -process original.bin \
  -scriptPath "$CASE/scripts" \
  -postScript ExportFunctions.py "$CASE/artifacts/static/ghidra-decompile"
```

Check the actual imported program name in the project if `-process original.bin` does not match. Headless scripts should fail loudly and preserve stderr.

### 14.3 When to use both radare2 and Ghidra

Use a second engine when:

- Function boundaries are disputed.
- A critical decompilation looks suspicious.
- One loader misidentifies architecture or base address.
- Calling conventions or indirect calls are unclear.
- A report depends on a single heuristic result.

Agreement between tools is supporting evidence, not proof; they may share the same incorrect assumptions.

---

## 15. Assembly and ABI Fundamentals

A senior analyst must recognize the calling convention and data model before trusting variable names.

### 15.1 x86-64 System V

Common integer/pointer arguments: `rdi`, `rsi`, `rdx`, `rcx`, `r8`, `r9`. Return value: `rax`. Caller-saved and callee-saved register behavior matters when reconstructing data flow.

### 15.2 Windows x64

Common integer/pointer arguments: `rcx`, `rdx`, `r8`, `r9`; additional arguments on the stack. Return value: `rax`. Account for shadow space and Windows unwind conventions.

### 15.3 AArch64

Arguments commonly begin in `x0` through `x7`; return value in `x0`. Watch for paired load/store instructions, ADRP+ADD address construction, and link register handling.

### 15.4 Endianness and width

Always distinguish:

- Address size from operand size.
- Signed from unsigned comparisons.
- File offsets from virtual addresses.
- Relative virtual addresses from preferred image addresses.
- Host endianness from serialized endianness.

Decompiler errors around these distinctions can change the meaning of a vulnerability or parser condition.

---

# Part IV — Dynamic Analysis

## 16. Dynamic Analysis Plan

Write the plan before execution:

```markdown
## Dynamic test D-003

**Question:** Does `parse_config` reject a record whose declared length exceeds the input buffer?

**Containment:** Disposable VM; no network adapter; non-root account; snapshot `clean-7`.

**Input:** `tests/oversize-record.bin`, SHA-256 ...

**Observation points:**
- breakpoint at `parse_config`
- watch return value
- capture syscalls and crash state

**Stop conditions:**
- unexpected child process
- privilege-change attempt
- write outside case scratch directory
- debugger loses control
```

This prevents aimless execution.

---

## 17. Linux Runtime Observation

### 17.1 `strace`

Start broad but bounded:

```bash
mkdir -p "$CASE/artifacts/dynamic/run-001"
cd "$CASE/artifacts/dynamic/run-001"

strace -ff \
  -o strace \
  -s 256 \
  -yy \
  -ttt \
  --kill-on-exit \
  -- /path/to/target arg1 arg2
```

Focused traces:

```bash
strace -ff -o file.trace -e trace=%file -- /path/to/target
strace -ff -o net.trace  -e trace=%network -- /path/to/target
strace -ff -o proc.trace -e trace=%process -- /path/to/target
strace -ff -o mem.trace  -e trace=mmap,mprotect,munmap,brk,memfd_create -- /path/to/target
```

Interpret return values and ordering. An attempted `openat` that returns `ENOENT` is not a successful read.

### 17.2 `ltrace`

```bash
ltrace -f -s 256 -o ltrace.txt -- /path/to/target
```

`ltrace` observes dynamic library calls where interception is possible. It is often ineffective for statically linked code, direct syscalls, inlined functions, custom loaders, and anti-instrumentation. Do not describe it as a solution for statically linked binaries.

### 17.3 `gdb` batch baseline

Create `scripts/gdb-baseline.txt`:

```text
set pagination off
set confirm off
set disassembly-flavor intel
set logging file gdb.log
set logging overwrite on
set logging enabled on
set args arg1 arg2
starti
info files
info proc mappings
info registers
x/16i $pc
bt
quit
```

Run:

```bash
gdb -q -nx -batch -x "$CASE/scripts/gdb-baseline.txt" --args /path/to/target arg1 arg2
```

### 17.4 Targeted breakpoint script

```text
set pagination off
set confirm off
set disassembly-flavor intel
set breakpoint pending on
break main
break openat
break connect
commands 2
  silent
  printf "connect breakpoint\n"
  bt 8
  info registers
  continue
end
run
```

For stripped PIE binaries, calculate runtime addresses from module load base plus static relative virtual address. Confirm mappings after launch instead of copying an absolute static address blindly.

### 17.5 Catch memory permission changes

```text
catch syscall mmap
catch syscall mprotect
catch syscall memfd_create
run
```

This is useful when investigating self-modifying code or runtime unpacking. A call to `mprotect` is common and does not alone prove unpacking.

### 17.6 Dump a confirmed memory region

In GDB:

```text
info proc mappings
dump binary memory /case/artifacts/memory/region.bin 0xSTART 0xEND
```

Record:

- Process state and command line.
- Mapping start/end and permissions.
- Why the region was selected.
- Hash of the dump.
- Relationship between memory addresses and file offsets.

A raw mapping may not be a directly loadable executable. Reconstruct only what the analysis question requires.

### 17.7 Deterministic replay with `rr`

```bash
rr record /path/to/target arg1 arg2
rr replay
```

Inside replay, use GDB commands, reverse execution, and watchpoints. `rr` is valuable for nondeterministic crashes and data-flow questions, but it has platform, CPU, container, and workload constraints. Verify that recording is faithful for the target.

### 17.8 Frida CLI

Trace selected functions rather than every function:

```bash
frida-trace -f /path/to/target \
  -i 'open*' \
  -i 'read*' \
  -i 'connect*'
```

Use module-qualified include patterns when possible. Generated handlers are a starting point; validate argument types and architecture before interpreting values.

---

## 18. Windows Runtime Observation from the CLI

Use a disposable Windows VM and command-line debugger such as CDB.

### 18.1 Launch under CDB

```bat
cdb -o -logo cdb.log sample.exe arg1 arg2
```

Useful commands:

```text
.symfix
.reload
lm
x sample!*
bp kernel32!CreateFileW
bp ws2_32!connect
g
k
r
u @rip-20 @rip+40
dq @rsp L20
```

Use unresolved breakpoints (`bu`) for symbols in modules that are not yet loaded. For APIs forwarded through KernelBase or API sets, confirm the actual resolved target.

### 18.2 Scripted debugger commands

Create `commands.txt`:

```text
.symfix
.reload
sxe av
bu kernel32!CreateProcessW ".printf \"CreateProcessW hit\\n\"; k; g"
bu ws2_32!connect ".printf \"connect hit\\n\"; k; g"
g
```

Run according to the installed CDB command-file options. Preserve the command file with the case.

### 18.3 Runtime evidence questions

- Did the call occur, or was the API merely imported?
- What were the arguments after pointer dereference?
- Which caller constructed those arguments?
- Was the return value checked?
- Was behavior conditional on environment, time, privileges, or input?

---

## 19. Network Observation

Prefer no network when the question does not require it. If network behavior must be observed, use simulated services or an isolated network owned by the analysis team.

```bash
tcpdump -i eth0 -nn -s 0 -w "$CASE/artifacts/dynamic/run-001/traffic.pcap"
```

Also preserve DNS, TLS metadata, and application logs from the simulator. Do not allow a sample to contact real third-party systems merely to confirm that it can connect.

Distinguish:

- Embedded endpoint string.
- Attempted DNS lookup.
- Successful DNS response.
- TCP connection attempt.
- Completed connection.
- Application protocol exchange.
- Authenticated or encrypted session.

Each is a different claim.

---

# Part V — Packing, Obfuscation, and Anti-Analysis

## 20. Determine Whether an Unpacking Stage Is Needed

Indicators may include:

- Entry point in a small or unusual section.
- Very few static imports plus dynamic resolution APIs.
- Large data regions with high entropy.
- Runtime writes followed by execution from the written region.
- Section names or signatures associated with a known packer.
- Static and runtime code maps that disagree substantially.

No single indicator is conclusive.

### 20.1 Known UPX sample

On a working copy:

```bash
cp -- "$F" "$CASE/artifacts/extracted/upx-input.bin"
upx -t "$CASE/artifacts/extracted/upx-input.bin"
upx -d -o "$CASE/artifacts/extracted/upx-unpacked.bin" \
  "$CASE/artifacts/extracted/upx-input.bin"
sha256sum "$CASE/artifacts/extracted/"*.bin \
  | tee "$CASE/artifacts/extracted/upx-hashes.txt"
```

Only use this shortcut when the file is actually recognized and the test succeeds. Compare unpacked behavior and structure with the original.

### 20.2 Generic runtime unpacking workflow

1. Trace memory allocation and protection changes.
2. Identify a region written by the unpacking stub.
3. Confirm control flow transfers into that region.
4. Break after the transfer and inspect mappings/import resolution.
5. Dump only the confirmed region or reconstructed image required for static analysis.
6. Re-run triage on the dump and record its parent process and memory range.

### 20.3 Anti-debugging

Look for checks involving debugger APIs, `ptrace`, process information queries, timing, exception behavior, or hardware state. First answer whether the check affects the question. Do not immediately patch every check.

Escalate when bypassing protection would violate engagement scope, licensing restrictions, or team policy.

### 20.4 Virtualized code

VM-based protectors can replace native logic with a custom bytecode interpreter. Full devirtualization is specialized research. A senior analyst should recognize the pattern, extract behavior dynamically where possible, define the remaining uncertainty, and avoid spending days on devirtualization when the business question is already answerable.

---

# Part VI — Unknown Data Formats and Firmware

## 21. Data-First Workflow

Do not load a data file into a disassembler merely because it is binary.

### 21.1 Structural survey

```bash
file -k "$F"
xxd -g 1 -l 1024 "$F"
od -Ax -tx1z -N 1024 "$F"
binwalk "$F"
strings -a -n 4 -t x "$F"
```

Build a map:

| Offset | Length | Candidate type | Observation | Confidence |
|---:|---:|---|---|---:|
| `0x0000` | 4 | magic | constant across five samples | High |
| `0x0004` | 2 | version LE | values 1, 2 | Medium |
| `0x0006` | 2 | header size | points to first record | High |
| `0x0008` | 4 | record count | matches parsed records | High |

### 21.2 Endianness tests

```bash
# Interpret four bytes at offset 4 as little- and big-endian integers.
dd if="$F" bs=1 skip=4 count=4 status=none | od -An -tu4 -N4
dd if="$F" bs=1 skip=4 count=4 status=none | od -An -tx4 -N4
```

For reliable cross-endian interpretation, use a short Python script rather than assuming the host's `od` behavior:

```bash
python3 - "$F" 4 <<'PY'
import struct, sys
path, off = sys.argv[1], int(sys.argv[2], 0)
b = open(path, 'rb').read()[off:off+4]
print('bytes', b.hex())
print('u32le', struct.unpack('<I', b)[0])
print('u32be', struct.unpack('>I', b)[0])
PY
```

### 21.3 Differential experiments

Create controlled pairs where only one application-level value changes.

```bash
cmp -l before.bin after.bin | tee changed-bytes.txt
radiff2 before.bin after.bin | tee radiff.txt
```

Group contiguous changes:

```bash
python3 - before.bin after.bin <<'PY'
import pathlib, sys

a = pathlib.Path(sys.argv[1]).read_bytes()
b = pathlib.Path(sys.argv[2]).read_bytes()
limit = max(len(a), len(b))
changes = []
start = prev = None
for i in range(limit):
    av = a[i] if i < len(a) else None
    bv = b[i] if i < len(b) else None
    if av != bv:
        if start is None:
            start = prev = i
        elif i == prev + 1:
            prev = i
        else:
            changes.append((start, prev))
            start = prev = i
if start is not None:
    changes.append((start, prev))
for s, e in changes:
    print(f"0x{s:08x}-0x{e:08x} ({e-s+1} bytes)")
PY
```

One changed field can also change a checksum, compressed block, timestamp, offset table, or encryption IV. Use at least three values and multiple samples before assigning semantics.

### 21.4 Repeating records

Test candidate record widths:

```bash
python3 - "$F" <<'PY'
import pathlib, sys
from collections import Counter

data = pathlib.Path(sys.argv[1]).read_bytes()
for width in (8, 12, 16, 20, 24, 32, 48, 64):
    heads = [data[i:i+4] for i in range(0, len(data)-width+1, width)]
    common = Counter(heads).most_common(3)
    print(width, [(x.hex(), n) for x, n in common])
PY
```

This is only a probe. Real records may be variable-length, aligned, nested, compressed, or referenced through offsets.

### 21.5 Checksum hypothesis

When a small field changes in addition to the target value, test common checksums over plausible ranges:

```bash
python3 - "$F" <<'PY'
import binascii, pathlib, sys, zlib

data = pathlib.Path(sys.argv[1]).read_bytes()
print('crc32-all', f'{zlib.crc32(data) & 0xffffffff:08x}')
print('adler32-all', f'{zlib.adler32(data) & 0xffffffff:08x}')
print('crc_hqx-all', f'{binascii.crc_hqx(data, 0):04x}')
PY
```

Do not brute-force checksum ranges blindly. Use code references, field placement, and differential changes to reduce the search space.

---

## 22. Formalize the Format

### 22.1 Python parser first

A small explicit parser is often the quickest way to test hypotheses:

```python
#!/usr/bin/env python3
import dataclasses
import pathlib
import struct
import sys

@dataclasses.dataclass
class Header:
    magic: bytes
    version: int
    header_len: int
    record_count: int


def parse_header(data: bytes) -> Header:
    if len(data) < 12:
        raise ValueError("file is shorter than header")
    magic, version, header_len, record_count = struct.unpack_from("<4sHHI", data, 0)
    if magic != b"SAVE":
        raise ValueError(f"bad magic: {magic!r}")
    if header_len < 12 or header_len > len(data):
        raise ValueError(f"invalid header length: {header_len}")
    return Header(magic, version, header_len, record_count)


def main(path: str) -> int:
    data = pathlib.Path(path).read_bytes()
    header = parse_header(data)
    print(header)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1]))
    except (IndexError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
```

A parser should reject malformed lengths and counts rather than seeking outside the buffer.

### 22.2 Kaitai Struct

Example `save_game.ksy`:

```yaml
meta:
  id: save_game
  endian: le
seq:
  - id: magic
    contents: [0x53, 0x41, 0x56, 0x45]
  - id: version
    type: u2
  - id: header_len
    type: u2
  - id: record_count
    type: u4
  - id: records
    type: record
    repeat: expr
    repeat-expr: record_count
types:
  record:
    seq:
      - id: type
        type: u1
      - id: length
        type: u2
      - id: payload
        size: length
```

Compile and test:

```bash
ksc -t python -d generated save_game.ksy
python3 -m pytest -q
```

A format specification is credible only after validation against multiple valid samples and intentionally malformed cases.

### 22.3 Producer/consumer bridge

When the data format is opaque:

1. Identify the authorized program that reads or writes it.
2. Trace the file open and read calls.
3. Identify the buffer and parser caller.
4. Recover offset and length checks from the parser.
5. Compare those checks with the file map.
6. Convert confirmed structure into a parser and tests.

This is often faster than guessing from bytes alone.

---

## 23. Firmware Workflow

Firmware may combine boot headers, compressed kernels, filesystems, device trees, configuration, certificates, and application binaries.

### 23.1 Survey and extraction

```bash
binwalk firmware.bin | tee binwalk.txt
xxd -g 1 -l 1024 firmware.bin | tee head.txt
```

Extract into a new directory using the options supported by the installed Binwalk release. Never extract over evidence. Inspect symlinks, special files, path traversal, and decompression size before opening or mounting content.

### 23.2 Filesystem handling

Prefer read-only userspace extraction. If mounting is necessary, use a disposable VM, read-only options, and no automatic execution. Never trust init scripts, package hooks, or binaries inside the image.

### 23.3 Firmware questions

- What is the boot chain?
- Which CPU and endianness does each executable target?
- Which services start automatically?
- Where are credentials, keys, certificates, update URLs, and debug settings stored?
- How is update authenticity checked?
- Are native components stripped, packed, or duplicated across versions?
- Which findings are reachable in the deployed configuration?

### 23.4 Version-to-version diff

```bash
radiff2 -A old.bin new.bin | tee firmware-analysis-diff.txt
```

Also compare extracted trees using hashes and metadata. Distinguish vendor changes from filesystem repacking noise.

---

# Part VII — Automation and Scaling

## 24. Makefile-Oriented Workflow

A simple `Makefile` makes the analysis repeatable:

```make
SAMPLE := evidence/original.bin
TRIAGE := artifacts/triage
STATIC := artifacts/static

.PHONY: all triage static clean

all: triage static

triage: $(TRIAGE)/file.txt $(TRIAGE)/strings.txt $(TRIAGE)/rabin-info.json

$(TRIAGE):
	mkdir -p $@

$(STATIC):
	mkdir -p $@

$(TRIAGE)/file.txt: $(SAMPLE) | $(TRIAGE)
	file -k -- $< > $@

$(TRIAGE)/strings.txt: $(SAMPLE) | $(TRIAGE)
	strings -a -n 5 -t x -- $< > $@

$(TRIAGE)/rabin-info.json: $(SAMPLE) | $(TRIAGE)
	rabin2 -Ij $< > $@

static: $(STATIC)/functions.json

$(STATIC)/functions.json: $(SAMPLE) | $(STATIC)
	r2 -q -A -c 'aflj' $< > $@

clean:
	rm -rf artifacts/triage artifacts/static
```

Do not make the workflow so automated that the analyst stops reviewing stderr, tool failures, or unexpected format changes.

---

## 25. Batch Analysis

For a sample set:

```bash
find samples -type f -print0 \
  | sort -z \
  | while IFS= read -r -d '' f; do
      h=$(sha256sum "$f" | cut -d' ' -f1)
      mkdir -p "batch/$h"
      file -k "$f" > "batch/$h/file.txt"
      rabin2 -Ij "$f" > "batch/$h/info.json" 2> "batch/$h/rabin.stderr" || true
    done
```

Use hashes as stable keys. Preserve source path separately. Limit concurrency and memory use when running decompilers over large sets.

### 25.1 Cluster before deep analysis

Cluster by:

- Exact hash.
- Size and section layout.
- Import sets.
- Normalized strings.
- Function or basic-block similarity.
- Compiler/runtime family.
- Shared resources or configuration schema.

Deeply analyze representatives, then verify family assumptions against outliers.

---

# Part VIII — Reporting and Review

## 26. Analysis Report Template

```markdown
# Analysis Report: <case ID>

## 1. Question and scope
- Authorized scope:
- Question answered:
- Explicit exclusions:

## 2. Evidence identity
- Original filename:
- SHA-256:
- Size:
- Provenance:
- Tool versions:

## 3. Executive conclusion
A concise answer, including confidence and material limitations.

## 4. Technical classification
- Format:
- Architecture:
- Runtime/compiler:
- Protection indicators:

## 5. Confirmed capabilities or structure
| Finding | Confidence | Evidence | Function/offset |
|---|---:|---|---|

## 6. Runtime observations
| Test | Input | Observation | Artifact |
|---|---|---|---|

## 7. Indicators and extracted data
Only include indicators that are actually associated with confirmed behavior.

## 8. Unknowns and alternative explanations
- 

## 9. Reproduction
Exact commands or script references.

## 10. Recommendations
Actionable, scoped, and linked to findings.
```

### 26.1 Evidence citation style

Use references such as:

```text
Observed in `artifacts/dynamic/run-003/strace.4121`, lines containing
`connect(5, ...) = 0`; caller confirmed at `0x4019a2` in
`artifacts/static/ghidra-decompile/00401920_build_connection.c`.
```

Do not cite only a screenshot or a paraphrased recollection.

---

## 27. Peer Review Checklist

A reviewer should answer yes to all applicable items:

### Scope and safety

- Authorization and execution boundaries are recorded.
- The original evidence is read-only and hashed.
- Dynamic execution was necessary and contained.

### Technical method

- File format, architecture, and base assumptions are confirmed.
- Static addresses are translated correctly for PIE/ASLR.
- Decompiler claims are checked against assembly where material.
- API imports are not presented as executed behavior without runtime or call-site evidence.
- Entropy is not treated as proof of encryption or packing.
- Failed tools and contradictory observations are disclosed.

### Reproducibility

- Commands, scripts, inputs, and tool versions are preserved.
- Extracted artifacts have parent relationships and hashes.
- Another analyst can rerun the decisive tests.

### Communication

- Facts, inferences, and unknowns are separated.
- Confidence is justified.
- The conclusion answers the scoped question.
- Recommendations do not exceed the evidence.

---

# Part IX — Accelerated Training Program

## 28. Progression Principles

The fastest route to senior performance is not consuming more tutorials. It is completing increasingly ambiguous analyses under review, with strict evidence and communication standards.

Use short feedback cycles:

1. Engineer writes the question and plan.
2. Engineer performs a bounded analysis.
3. Reviewer challenges assumptions and asks for reproduction.
4. Engineer revises the evidence, not just the wording.
5. Reusable steps become scripts or team playbooks.

### Weekly operating rhythm

- Two individual lab analyses.
- One reviewed production-like case.
- One tool or script improvement.
- One written retrospective: wrong assumption, detection method, and prevention.
- One oral briefing with adversarial questions.

---

## 29. Six-Week Intensive Track

### Week 1 — Binary literacy and evidence discipline

Competencies:

- ELF/PE/Mach-O identification.
- Hex, endianness, integer widths, virtual addresses, file offsets.
- Calling conventions and stack frames.
- Reproducible case workspace.

Deliverables:

- Triage five benign binaries from different compilers/runtimes.
- Explain every field in one ELF header and one PE section table.
- Produce a triage script with tests and error handling.

Gate:

- No unsupported claims.
- Every conclusion has an artifact reference.

### Week 2 — Static narrowing

Competencies:

- Radare2 navigation, xrefs, functions, imports, strings, renaming, projects.
- Headless Ghidra analysis and export.
- Decompiler skepticism.

Deliverables:

- Recover the control flow of a stripped training binary.
- Identify and document ten key functions.
- Compare radare2 and Ghidra disagreements.

Gate:

- Can explain why selected functions matter and why others were deprioritized.

### Week 3 — Dynamic confirmation

Competencies:

- `strace`, GDB, CDB, breakpoints, watchpoints, mappings, ASLR.
- Bounded dynamic-test plans.
- Network and filesystem observation.

Deliverables:

- Confirm three static hypotheses at runtime.
- Produce a deterministic crash investigation with `rr` where supported.
- Demonstrate correct distinction between attempted and successful behavior.

Gate:

- No uncontrolled execution and no missing stop conditions.

### Week 4 — Data formats and firmware

Competencies:

- Differential analysis.
- Offset/count/length relationships.
- Parser validation and malformed-input tests.
- Firmware extraction and file-tree triage.

Deliverables:

- Reverse a training format from at least six samples.
- Publish a Python parser and Kaitai specification.
- Analyze two versions of a benign firmware image or synthetic filesystem bundle.

Gate:

- Parser rejects invalid lengths and passes multi-sample tests.

### Week 5 — Obfuscation, packing, and scale

Competencies:

- Distinguish packed, stripped, optimized, and runtime-heavy binaries.
- Confirm runtime-generated code.
- Batch triage and clustering.

Deliverables:

- Analyze an authorized UPX-packed training program before and after unpacking.
- Create a cluster report for a sample set.
- Document an anti-analysis indicator without overstating it.

Gate:

- Can state when full unpacking/devirtualization is unnecessary.

### Week 6 — Senior capstone

The engineer receives an ambiguous case with:

- Multiple related binaries.
- One custom data format.
- At least one misleading heuristic.
- A bounded business question.
- Incomplete context.

Required output:

- Written plan and risk assessment.
- Reproducible artifact set.
- Technical report.
- Ten-minute executive briefing.
- Thirty-minute technical defense.
- Automation contribution to the team repository.

Gate:

- The engineer adapts method to the question, handles uncertainty, and improves the team's future speed.

---

## 30. Safe Lab Exercises

Use programs built from source inside the lab. Do not begin training with live malware.

### Lab 1 — Stripped ELF

Create `lab1.c`:

```c
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint32_t checksum(const unsigned char *p, size_t n) {
    uint32_t h = 2166136261u;
    for (size_t i = 0; i < n; i++) {
        h ^= p[i];
        h *= 16777619u;
    }
    return h;
}

static int validate(const char *s) {
    static const uint32_t expected = 0x3253a764u;
    return strlen(s) == 9 && checksum((const unsigned char *)s, 9) == expected;
}

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s VALUE\n", argv[0]);
        return 2;
    }
    puts(validate(argv[1]) ? "accepted" : "rejected");
    return validate(argv[1]) ? 0 : 1;
}
```

Build variants:

```bash
gcc -O0 -g -o lab1-debug lab1.c
gcc -O2 -s -fPIE -pie -o lab1-stripped lab1.c
```

Tasks:

- Recover the validation algorithm.
- Explain how optimization changed the function layout.
- Confirm the input length and checksum dynamically.
- Do not solve by reading the source after compilation.

### Lab 2 — Custom format

Write a generator that emits:

```text
magic | version | header_length | record_count | records | checksum
```

Give the engineer six generated files and withhold the generator. Require a parser, tests, and a format specification.

### Lab 3 — Runtime-created buffer

Build a benign program that decompresses or decodes a data block in memory and calls a parser on it. The task is to identify the transformation, dump the decoded data, and connect the dynamic buffer to static code.

### Lab 4 — Cross-platform comparison

Compile equivalent logic with GCC, Clang, MSVC, Go, and Rust where practical. Require the engineer to identify compiler/runtime artifacts and isolate application logic.

### Lab 5 — Version diff

Provide two versions of a benign program with one security-relevant validation fix. Require identification of the changed function, explanation of semantic impact, and a regression test.

---

## 31. Senior-Level Scoring Rubric

Score each area from 0 to 4.

| Area | 0 | 2 | 4 |
|---|---|---|---|
| Scope and safety | ignores boundaries | follows checklist | anticipates and improves controls |
| Triage | tool dump only | correct classification | fastest decisive path with rationale |
| Static analysis | trusts decompiler | verifies key code | reconstructs types/data flow across functions |
| Dynamic analysis | exploratory execution | planned confirmation | minimal, instrumented, reproducible tests |
| Data formats | guesses fields | validates common fields | publishes robust parser/spec and malformed tests |
| Automation | manual only | useful scripts | reliable tooling adopted by team |
| Evidence | incomplete | reproducible | audit-ready, cross-confirmed, uncertainty explicit |
| Communication | technical dump | answers question | adapts message to audience and defends tradeoffs |
| Leadership | needs direction | works independently | reviews others and raises team capability |

A nominal “senior” result requires no score below 3 and demonstrated performance on multiple unfamiliar cases. Tool fluency alone is insufficient.

---

# Part X — Command Reference

## 32. Fast CLI Cheat Sheet

### Identity

```bash
sha256sum sample
file -k sample
stat sample
xxd -g 1 -l 512 sample
```

### Strings

```bash
strings -a -n 5 -t x sample
strings -a -n 5 -e l -t x sample
floss -j sample > floss.json
```

### Cross-format

```bash
rabin2 -I sample
rabin2 -S sample
rabin2 -i sample
rabin2 -E sample
rabin2 -zz sample
```

### ELF

```bash
readelf -hW sample
readelf -lW sample
readelf -SW sample
readelf -dW sample
readelf -sW sample
readelf -rW sample
objdump -d -M intel sample
```

### PE

```bash
llvm-objdump --private-headers --section-headers --syms sample.exe
rabin2 -I -S -i -E sample.exe
```

```bat
dumpbin /HEADERS sample.exe
dumpbin /IMPORTS sample.exe
dumpbin /EXPORTS sample.dll
```

### Radare2

```bash
r2 -A sample
r2 -q -A -c 'aflj' sample > functions.json
```

```text
iI iS ii iE izz afl
s entry0
pdf
pdc
axt
afn name
CC comment
```

### Dynamic Linux

```bash
strace -ff -o trace -s 256 -yy -ttt --kill-on-exit -- ./sample
ltrace -f -s 256 -o ltrace.txt -- ./sample
gdb -q -nx --args ./sample
rr record ./sample
rr replay
frida-trace -f ./sample -i 'open*' -i 'read*'
```

### Diff and format

```bash
cmp -l before.bin after.bin
radiff2 before.bin after.bin
binwalk blob.bin
ksc -t python -d generated format.ksy
```

---

## 33. Common Analytical Failures

### “High entropy means encrypted”

Wrong. It may be compressed, encoded media, random test data, a lookup table, or too short for a useful estimate.

### “The API is imported, so the program performs the behavior”

Wrong. Confirm call sites, arguments, conditions, and preferably runtime execution.

### “The decompiler shows C, so the original source has been recovered”

Wrong. Names, types, structure boundaries, signedness, and control flow may be reconstructed incorrectly.

### “No strings means no useful static analysis”

Wrong. Use imports, constants, control flow, relocations, metadata, dynamic resolution, and runtime buffers.

### “The entry point is main”

Often wrong. Startup code, constructors, TLS callbacks, loaders, and packer stubs may run first.

### “The debugger address equals the file address”

Often wrong under PIE, ASLR, rebasing, overlays, or packed mappings.

### “More tools increase confidence”

Only when they provide independent evidence. Five tools repeating the same signature database do not provide five independent confirmations.

### “A senior analyst must fully understand every function”

Wrong. A senior analyst understands enough to answer the scoped question and clearly defines what remains unknown.

---

## 34. Escalation Criteria

Escalate or bring in a specialist when:

- The sample targets an unfamiliar architecture and a wrong assumption would materially affect the conclusion.
- Kernel-mode, hypervisor, bootloader, or hardware behavior is central.
- Strong commercial virtualization prevents answering a critical question.
- Cryptographic protocol conclusions require formal expertise.
- Legal or license restrictions may prohibit circumvention.
- The sample may contain regulated, personal, or customer data.
- Dynamic execution cannot be safely contained.
- The business impact exceeds the confidence of the available evidence.

Escalation is a senior behavior, not a failure.

---

## 35. Official References

Use installed `--help` and version-specific manuals as the immediate source of truth.

- [Ghidra Headless Analyzer API](https://ghidra.re/ghidra_docs/api/ghidra/app/util/headless/AnalyzeHeadless.html)
- [Ghidra command-line analysis tutorial](https://ghidra.re/ghidra_docs/GhidraClass/BSim/BSimTutorial_Ghidra_Command_Line.html)
- [The Official Radare2 Book](https://book.rada.re/)
- [Radare2 code analysis](https://book.rada.re/analysis/code_analysis.html)
- [Radare2 decompilers](https://book.rada.re/arch/decompile.html)
- [capa usage](https://github.com/mandiant/capa/blob/master/doc/usage.md)
- [FLOSS usage](https://github.com/mandiant/flare-floss/blob/master/doc/usage.md)
- [YARA command-line documentation](https://yara.readthedocs.io/en/stable/commandline.html)
- [Frida CLI documentation](https://frida.re/docs/frida-cli/)
- [frida-trace documentation](https://frida.re/docs/frida-trace/)
- [strace project](https://strace.io/)
- [rr record and replay debugger](https://rr-project.org/)
- [Kaitai Struct user guide](https://doc.kaitai.io/user_guide.html)
- [Binwalk v3](https://github.com/ReFirmLabs/binwalk)
- [LLVM objdump documentation](https://llvm.org/docs/CommandGuide/llvm-objdump.html)
- [Microsoft CDB command-line options](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/cdb-command-line-options)
- [Microsoft DUMPBIN reference](https://learn.microsoft.com/en-us/cpp/build/reference/dumpbin-reference)

---

## 36. Final Operating Checklist

Before closing a case:

```text
[ ] The scoped question is answered.
[ ] Original evidence is preserved and hashed.
[ ] Tool versions and commands are recorded.
[ ] Facts, inferences, and unknowns are separated.
[ ] Critical decompiler output was checked against assembly.
[ ] Dynamic claims include actual runtime evidence.
[ ] Extracted artifacts are hashed and linked to their parent.
[ ] Alternative explanations were considered.
[ ] The report states confidence and limitations.
[ ] A second analyst can reproduce the decisive result.
[ ] Reusable work was converted into a script, test, or playbook.
```

The senior habit is not memorizing every command. It is preserving a trustworthy chain from question to evidence to conclusion.
