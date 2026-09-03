# 07 — Windows x64 ABI (Read Before Trusting Args)

Wrong ABI = wrong args = wrong conclusion. Confirm bitness first (`PE32` vs `PE32+`, see `03-...`).

## 1. x64 Windows (most EXEs)

- First 4 integer/pointer args: `rcx, rdx, r8, r9`. Rest on stack (`[rsp+0x20]` and up after call).
- Return: `rax`. Floats: `xmm0-xmm3`.
- **Shadow space:** caller reserves 32 bytes (`sub rsp,0x20`) before `call`, callee may spill `rcx/rdx/r8/r9` there. Seeing `[rsp+0x...]` stores right after entry is normal, not a buffer.
- Caller-saved: `rax,rcx,rdx,r8-r11,xmm0-5`. Callee-saved: `rbx,rsi,rdi,rbp,r12-r15`. If a value survives a call in `rbx`, it was deliberately preserved.
- Unwind: `.pdata` + `.xdata` describe every function (required on x64). Use for boundary recovery when stripped.

Example — `CreateFileW(lpFileName, dwAccess, dwShare, lpSec, dwCreate, dwFlags, hTemplate)`:

```asm
lea  rcx, [path]     ; arg1
mov  edx, 0x80000000 ; GENERIC_READ
mov  r8d, 1          ; FILE_SHARE_READ
xor  r9d, r9d        ; NULL sec
push 0               ; hTemplate (arg7, stack)
push 0x80            ; FILE_ATTRIBUTE_NORMAL (arg6)
push 3               ; OPEN_EXISTING (arg5)
sub  rsp, 0x20       ; shadow (done before, shown here for clarity)
call CreateFileW
```

To recover the path: dereference `rcx` as UTF-16LE (`du poi(@rcx)` in CDB), not ASCII.

## 2. x86 (32-bit PE32) vs x64

- `__cdecl`: args on stack, caller cleans. `__stdcall` (WinAPI x86): args on stack, callee cleans. `__fastcall`: `ecx,edx` + stack.
- x86 has no shadow space, no `.pdata`. Don't apply x64 rules to PE32.
- WoW64: 32-bit EXE on 64-bit Windows goes through `ntdll32 → wow64` thunks. Syscall numbers and traces look different — note WoW64 in report.

## 3. AArch64 / ARM64EX (if encountered)

Args `x0-x7`, return `x0`. Watch `ADRP+ADD` address construction, paired `LDP/STP`, link register `x30`. ARM64EX (Win11) adds emulator thunks — confirm resolved target.

## 4. Universal traps

- File offset ≠ RVA ≠ VA. Convert: `VA = ImageBase + RVA`; `FileOffset = RVA - SectionVA + PointerToRawData`.
- Signed vs unsigned compare (`jl` vs `jb`) changes vuln/parse meaning. Check in asm, not decompiler.
- Host endianness (x86 LE) vs serialized BE (network/file magic) — use explicit `struct.unpack('>I')`, don't trust `od` defaults.
- Entry point ≠ `main`. CRT (`mainCRTStartup`), TLS callbacks, `.CRT$XCU` initializers, `DllMain`, packer stub all run first.
