---
name: reverse-engineering-executables
description: Reverse engineer Windows EXE/DLL and other native executables from the CLI - triage, PE static analysis, disassembly, debugging, unpacking, and reporting. Use when asked to analyze an executable, DLL, packed binary, or unknown binary that executes code.
---

# Reverse Engineering Executables (CLI-First)

**Scope:** Authorized analysis of native executables, prioritizing Windows PE (EXE/DLL/SYS) with ELF/Mach-O appendix. For pure data/firmware/save formats with no code analysis, use `reverse-engineering-saves-firmware-cli` instead.
**Operating principle:** Every conclusion must be traceable to a command, an artifact, and a confidence label (Observed / Inferred / Unknown + High/Medium/Low).

## Mandatory loop (every task)

```text
Question -> cheapest safe observation -> hypothesis -> decisive test
  -> preserve artifact -> update confidence -> next question or stop
```

Do not execute a sample if static evidence already answers the question.

## Execution gate (must answer all 5 before running)

1. What exact question requires execution?
2. What behavior will be observed (syscalls, API, files, net)?
3. What containment is active (disposable VM, snapshot, no prod net, no shares)?
4. What data can the sample reach?
5. What event stops the run (child proc, priv-esc, write outside scratch, debugger loss)?

Treat every unknown EXE as hostile. Disposable VM + snapshot + host-only/disabled net. Container alone is not sufficient. See `references/01-safety-evidence-workspace.md`.

## Branch router — read only what you need

1. **Setup + safety:** `references/01-safety-evidence-workspace.md` — case dir, hashing, tool versions. Always do first.
2. **Triage (no exec):** `references/02-triage-exe.md` — `file`, hashes, strings, FLOSS, DiE, `capa`, YARA, entropy. Output: `notes/triage-summary.md` + next 3 commands.
3. **PE static deep-dive:** `references/03-pe-static-deepdive.md` — DOS/NT headers, sections, imports/exports, TLS, resources, overlay, Authenticode. Use for any EXE/DLL.
4. **Managed/runtime EXE:** `references/04-managed-runtimes.md` — .NET / Go / Rust / MSVC fingerprinting. Read if triage says runtime-heavy.
5. **Disassembly:** `references/05-disassembly-rizin.md` — Rizin-first (r2 fallback), strings→xref→caller, rename/comment rules.
6. **Decompilation:** `references/06-ghidra-headless.md` — headless import + export + verify-against-asm rule. Use when function boundaries disputed or report depends on one engine.
7. **ABI:** `references/07-windows-abi-x64.md` — x64 Windows calling convention, shadow space, SEH/.pdata, 32-vs-64-bit. Read before trusting arg recovery.
8. **Dynamic Windows:** `references/08-dynamic-windows-cli.md` — CDB/WinDbg, ProcMon, network sim, attempted-vs-successful. Requires execution gate.
9. **Linux ELF appendix:** `references/09-dynamic-linux-appendix.md` — `strace`, GDB, `rr`, Frida. Only if target is ELF.
10. **Packing/anti-analysis:** `references/10-packing-obfuscation-antianalysis.md` — UPX shortcut vs generic dump, API hashing, anti-debug catalog, when NOT to unpack.
11. **Reporting:** `references/11-report-review-checklists.md` — report template, citation style, peer-review, escalation, close-out checklist.

Templates: `checklists/triage-summary-template.md`, `checklists/dynamic-test-plan-template.md`, `checklists/function-note-template.md`.
Scripts: `scripts/triage.sh`, `scripts/triage-exe.ps1`, `scripts/entropy.py`, `scripts/ExportFunctions.py`.

## Tool fallback order

- PE info: `pefile/LIEF` (Python) > `rz-bin/rabin2` > `llvm-objdump` > `dumpbin` (Windows). If one loader misidentifies arch/base, confirm with a second engine.
- Strings: `strings` + `FLOSS` + `rz-bin -z`. A string is a lead, never proof of behavior.
- Capabilities: `capa` to prioritize, then verify at call site + runtime. Missing `capa` match proves nothing.
- Entropy >7.5 is a clue (compression/encryption/media/random), never proof. Must align with section + decoder loop.

## Definition of done

Scoped question answered + original preserved read-only and hashed + commands/versions/inputs saved + facts/inferences/unknowns separated + critical decompiler claims checked in asm + dynamic claims have runtime artifacts + second analyst can reproduce decisive test.
