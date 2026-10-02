# 14 — Binary Patching & Rebuilding PE (Persistent Modification)

Hooking (`12-...`) changes behavior in memory per-run. Patching changes the
**file** so behavior persists across runs. Use for: fixing your own software,
interop shims, CTF patchmes, testing a hypothesis permanently (e.g. proving
a function is the check by removing it), and building proxy DLLs.

**Scope gates:** copies in the lab, hashes recorded (same evidence rules as
`01-...` — the original stays read-only; every patched copy is a derived
artifact with provenance). Redistributing patched licensed software, or
patching DRM/licensing of software you don't own, is out of scope and a
legal bar (`11-...` escalation).

## 1. Patch planning (never hex-edit blind)

1. State the behavior goal precisely ("skip the update check", "force UTF-16
   path handling").
2. From `05/06`, list **every** site that implements it (one logical check
   often has 2–3 code sites + a data constant).
3. Classify the change: **code patch** (compare/branch/constant), **data
   patch** (string, table entry, flag), **import/export patch**, or
   **proxy DLL** (a module boundary, not a byte in this file).
4. Decide same-length inline vs code-cave (below) vs rebuild-with-pefile.
5. Record the plan in `notes/decisions.md` before editing.

## 2. Inline code patches (same length — always prefer)

| Goal | Patch pattern (x64) |
|---|---|
| Skip a check | `jz/jnz` over the failure path → `jmp rel8` (`EB xx`) or invert the condition (`74↔75`, `0F 84↔0F 85`) |
| Force "true" return | `31 C0 40 C3` (`xor eax,eax; inc eax; ret`) — or `B0 01 C3` (`mov al,1; ret`) when only al matters |
| Force "false" | `31 C0 C3` (`xor eax,eax; ret`) |
| Remove one call | 5–6 bytes of `NOP` (`90`) / `MULTI-NOP` (`0F 1F /r`) preserving length |
| Widen a compare | immediate operand edit (`81 F9 imm32` → new imm32), same width only |

Rules: **byte-length must not change** (relative branches after the site
stay valid); disassemble the result (`05-...`) to prove it; a patched branch
is only as proven as your understanding of both targets (`06-...` second
engine for anything load-bearing).

## 3. Code caves (length-changing logic)

When you need *more* code than the site has bytes:

1. **Find space in the same image**: alignment padding between functions
   (`0xCC`/`0x90` runs in MSVC `.text`), the tail slack of the last section
   (`VirtualSize` < `SizeOfRawData` region — but stay inside
   `PointerToRawData+SizeOfRawData`), or **append a new section** (below).
2. **Route execution there**: a `jmp rel32` (`E9 rel32`, ±2 GiB — fine within
   one image) from the patch site to the cave; write your logic; `jmp rel32`
   back to the instruction after the original site.
3. **Preserve what you clobber**: the overwritten original instructions must
   be re-executed (or their effects compensated) in the cave — including
   **flags** if the following code tests them.
4. **RIP-relative fixups**: instructions you relocate that used RIP-relative
   addressing must be re-assembled with the new displacement (`rasm2`
   re-assembles; a naive byte copy breaks them). This is the most common
   hand-rolled cave bug.
5. **Keep cave code position-independent** (no absolute addresses) unless the
   module is non-ASLR (DllCharacteristics `0x0040` clear — `03-...`).

```bash
rasm2 -a x86 -b 64 'jmp 0x401000'     # encode your jump to check bytes
rasm2 -d -a x86 -b 64 'e9 xx xx xx xx'  # decode what you wrote back
```

## 4. Appending a section (pefile, programmatic)

```python
import pefile, hashlib
pe = pefile.PE("copy.exe")
# 1. headers must have room: SizeOfHeaders area after last section header
#    (NumberOfSections*40 + 0x18 + SizeOfOptionalHeader < first raw data)
# 2. align new section; update NumberOfSections, SizeOfImage (SectionAlignment),
#    write raw data at aligned file offset (FileAlignment), set flags
#    (0x60000020 = code|read|execute; W never together with X unless intended)
# 3. save; re-open + verify parse; hash; record every field change
```

Caveats: some packers/loader validators reject unknown sections; AV/EDR
score fresh writable-then-executable sections heavily (fine in lab, do not
ship); relocations for the new section are not generated automatically
(keep code RIP-relative, see §3.5).

## 5. Data patches

- Strings: same-or-shorter, keep the terminator, recompute nothing (no length
  is stored) unless a length-prefixed/UTF-16-counted field wraps it.
- Tables: vtable/function-pointer/index tables — patch the entry, keep
  alignment; an entry pointing into another module needs base math at load
  (imports are the sanctioned way — see §7).
- Constants in `.rdata`: often simpler + safer than code (e.g. flip a
  feature flag than patch the branch that tests it) — prefer data when both
  exist.

## 6. Rebuild obligations (the checklist after every patch)

- [ ] File offsets ≠ RVAs: patches target **file offsets**; convert from the
      function VA via section math (`03-...` / `07-...`), then verify by
      re-disassembling at the offset.
- [ ] Disassemble the patched region in a **second engine** (`06-...`).
- [ ] Header checksum: only drivers/boot components actually validate the PE
      `CheckSum` field — recompute with pefile if the target class demands it.
- [ ] Authenticode: any byte patch invalidates the signature — expected;
      note it (do not strip silently; `Get-AuthenticodeSignature` on the copy
      documents it).
- [ ] SizeOfImage/NumberOfSections consistent if you appended a section.
- [ ] Raw copy hash + patch ledger: RVA/file offset, old bytes, new bytes,
      reason, tool+version — a patch without its ledger is unreviewable.
- [ ] Runtime verify: behavior diff (ProcMon/log before-vs-after, `08-...`),
      and negative tests (goal behavior changed, unrelated behavior intact).

## 7. Import patching & DLL proxying (module-boundary patching)

**IAT swap (file):** edit the import entry to your DLL's export — only sane
when the import name/dll slot can be rewritten without rebuilding the whole
descriptor (pefile `DIRECTORY_ENTRY_IMPORT` edits + `write()`); otherwise
proxy:

**Proxy DLL (the load-order technique):**
1. See what the target loads (ProcMon/`02-...`) and which load path wins
   (application dir first for most; check DLL search order for the version).
2. Build a proxy: same name as the real DLL (renamed real one, e.g.
   `version_orig.dll`), forwarding every export:

```cpp
// proxy.def / or pragma forwards:
#pragma comment(linker, "/export:GetFileVersionInfoW=version_orig.GetFileVersionInfoW")
// DllMain: your logging/interop hook runs at DLL_PROCESS_ATTACH (rdx==1, 08-...)
```

3. Every export must be forwarded or the target's imports fail to resolve —
   enumerate the originals first (`dumpbin /EXPORTS real.dll`); misses crash
   at first call.
4. Keep hashes of the proxy build; note that signature checkers on the real
   DLL will fail on your proxy (expected, document).

This is the standard, *persistent* alternative to injection (`12-...` §4)
for plugin-less apps — no in-process patching at all, and it survives
anti-tamper that detects hot code changes.

## 8. Packed/protected targets

Don't byte-patch what you can't see: the on-disk bytes you'd patch are
decoder input, not the logic. Order: unpack decision (`10-...` §1) → either
(a) runtime-dump + rebuild + patch the dump (advanced; IAT rebuild —
`10-...` §3), (b) runtime hook instead (`12-...`), or (c) patch the
stub's behavior if the goal is achievable at that layer. Never report
"patched the check" when you patched the unpacker's input.

## 9. Patch application workflow (evidence-disciplined)

```bash
cp -- evidence/original.bin artifacts/patched/target-patched.exe
python3 scripts/patch_bytes.py artifacts/patched/target-patched.exe \
  --offset 0x4012A3 --old 0F84 --new 0F85 --why "invert update-check branch"
sha256sum artifacts/patched/target-patched.exe | tee -a artifacts/SHA256SUMS
rizin -q -c 'pd 6 @ 0x140012A3' artifacts/patched/target-patched.exe   # verify
```

`scripts/patch_bytes.py` refuses to apply if the bytes at the offset don't
match `--old` (protects against wrong-offset math), logs old→new, and
appends a patch ledger row — patch application with evidence, not vibes.
