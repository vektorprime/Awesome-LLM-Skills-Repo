---
name: x64-assembly
description: Comprehensive reference for x86-64 (AMD64 / Intel 64) assembly language. Use when writing, reading, reviewing, or debugging 64-bit x86 assembly.
---

# x86-64 (x64) Assembly: A Detailed Reference

This document is a detailed guide to the **x86-64** instruction set architecture (ISA) — also marketed as **AMD64** (AMD's name) and **Intel 64** (Intel's name), and commonly called **x64**. It is the 64-bit extension of the 32-bit x86 (IA-32) architecture, first shipped by AMD in 2003 (the Opteron / Athlon 64) and adopted by Intel shortly after. It is the dominant ISA for desktops, laptops, servers, and most cloud infrastructure.

The goal of this document is to be a working reference: it covers the full register file in depth (general-purpose, flags, instruction pointer, segment, x87 FPU, MMX, SSE, AVX, AVX-512, control, and debug registers), the instruction encoding model, addressing modes, the core instruction set, control flow, the stack, calling conventions for both major ABIs, Linux system calls, SIMD programming, and the toolchain.

---

## 1. Architecture Overview

x86-64 extends IA-32 with the following headline features:

- **64-bit general-purpose registers.** All eight legacy 32-bit registers were widened to 64 bits, and eight new registers (`r8`–`r15`) were added, for **16 GPRs** total.
- **A flat 64-bit address space.** The architecture defines 64-bit virtual addresses. Real implementations use a subset: current mainstream CPUs implement **48-bit virtual addressing** (256 TiB) with 4-level paging, and newer server CPUs support **57-bit virtual addressing** (128 PiB) with 5-level paging. Physical address width is implementation-defined (commonly 48–52 bits).
- **More SIMD registers.** The 8 XMM registers of 32-bit SSE2 became **16** (`xmm0`–`xmm15`), later widened to 256-bit YMM (AVX) and 512-bit ZMM with 32 registers (AVX-512).
- **RIP-relative addressing.** A new addressing mode relative to the instruction pointer, essential for position-independent code in a 64-bit address space.
- **The REX prefix.** A new instruction-prefix byte used to access the widened and new registers and to select 64-bit operand size.
- **SSE/SSE2 as the baseline floating-point model.** Scalar and vector floating point is done through XMM registers; the legacy x87 FPU stack is retained but de-emphasized.
- **Removal of some legacy features.** Instructions such as `pusha`/`popa`, the decimal-adjust instructions (`aaa`, `aad`, `aam`, `das`), and several segment-related operations are invalid in 64-bit mode.

Backward compatibility is strong: nearly all 32-bit, 16-bit, and 8-bit operand forms still work, and the low halves/bytes of the wide registers remain accessible.

---

## 2. Execution Modes

An x86-64 CPU operates in several modes. The relevant ones:

- **Long mode** — the 64-bit-capable mode, containing:
  - **64-bit mode** — the subject of this document. 64-bit operands and addresses, 16 GPRs, RIP-relative addressing.
  - **Compatibility mode** — runs legacy 32-bit and 16-bit protected-mode code under a 64-bit OS (this is how 32-bit programs run on a 64-bit kernel).
- **Protected mode** — the 32-bit/16-bit mode used before entering long mode.
- **Real mode / Virtual-8086 mode** — legacy 16-bit modes used at boot.

A CPU enters long mode from protected mode by enabling paging with the Long Mode Enable (LME) bit in the `IA32_EFER` MSR and setting `CR0.PG`. This document assumes 64-bit mode throughout.

---

## 3. The General-Purpose Registers

There are **16** 64-bit general-purpose registers. Each register can be accessed at several widths through aliased sub-register names:

| 64-bit | 32-bit | 16-bit | 8-bit low | 8-bit high* |
|--------|--------|--------|-----------|-------------|
| `rax`  | `eax`  | `ax`   | `al`      | `ah`        |
| `rcx`  | `ecx`  | `cx`   | `cl`      | `ch`        |
| `rdx`  | `edx`  | `dx`   | `dl`      | `dh`        |
| `rbx`  | `ebx`  | `bx`   | `bl`      | `bh`        |
| `rsp`  | `esp`  | `sp`   | `spl`     | —           |
| `rbp`  | `ebp`  | `bp`   | `bpl`     | —           |
| `rsi`  | `esi`  | `si`   | `sil`     | —           |
| `rdi`  | `edi`  | `di`   | `dil`     | —           |
| `r8`   | `r8d`  | `r8w`  | `r8b`     | —           |
| `r9`   | `r9d`  | `r9w`  | `r9b`     | —           |
| `r10`  | `r10d` | `r10w` | `r10b`    | —           |
| `r11`  | `r11d` | `r11w` | `r11b`    | —           |
| `r12`  | `r12d` | `r12w` | `r12b`    | —           |
| `r13`  | `r13d` | `r13w` | `r13b`    | —           |
| `r14`  | `r14d` | `r14w` | `r14b`    | —           |
| `r15`  | `r15d` | `r15w` | `r15b`    | —           |

\* The high-byte registers `ah`, `bh`, `ch`, `dh` access bits 8–15 of the first four registers. They are a legacy feature: they **cannot be used in any instruction that carries a REX prefix**. The new low-byte names `spl`, `bpl`, `sil`, `dil` (and `r8b`–`r15b`) are only accessible when a REX prefix is present.

### Bit layout of a register

```
 63                              31          15      7      0
┌────────────────────────────────┬───────────┬───────┬──────┐
│            (upper 32)          │   eax     │  ax   │  al  │  rax
└────────────────────────────────┴───────────┴───┬───┴──┬───┘
                                                 │ ah   │
                                                 └──────┘  (bits 8-15)
```

- `al` = bits 0–7, `ah` = bits 8–15, `ax` = bits 0–15, `eax` = bits 0–31, `rax` = bits 0–63.

### Conventional roles

The architecture allows any GPR to be used generally, but conventions (and some instructions) assign roles:

| Register | Conventional role |
|----------|-------------------|
| `rax` | Accumulator; return value; syscall number/return |
| `rbx` | Base; callee-saved |
| `rcx` | Count (loop/shift count); 4th integer arg (SysV) / 1st arg (Windows) |
| `rdx` | Data; high half of `rdx:rax` for mul/div; 3rd arg (SysV) / 2nd arg (Windows) |
| `rsi` | Source index (string ops); 2nd arg (SysV) |
| `rdi` | Destination index (string ops); 1st arg (SysV) |
| `rbp` | Frame pointer |
| `rsp` | Stack pointer |
| `r8`–`r11` | Extra arguments / caller-saved scratch |
| `r12`–`r15` | Callee-saved general purpose |

### Critical sub-register write semantics

This behavior is a frequent source of bugs and is worth memorizing:

- **Writing a 32-bit register zero-extends into the full 64-bit register.**
  `mov eax, 0xFFFFFFFF` sets `rax` to `0x00000000FFFFFFFF` (upper 32 bits cleared).
- **Writing a 16-bit or 8-bit register preserves the upper bits.**
  `mov ax, 0` clears only the low 16 bits of `rax`; the rest is unchanged.
- This is why `xor eax, eax` is the preferred way to zero `rax` — it is shorter (2 bytes vs. 7) and, on modern CPUs, recognized as a zeroing idiom that breaks dependency chains.

---

## 4. The Instruction Pointer (RIP)

`rip` is the 64-bit register holding the address of the **next** instruction to be executed. It has no smaller aliases. You cannot generally `mov` to or from `rip` directly; it is modified implicitly by:

- `jmp`, `call`, `ret`, `iret`, `sysret`
- Conditional jumps (`je`, `jl`, …)
- Interrupts and exceptions

`rip` becomes directly usable as an addressing base — **RIP-relative addressing** (`[rip + disp32]`) — which is the standard way to reference static data in position-independent 64-bit code, because a 32-bit absolute address can no longer reach arbitrary 64-bit locations.

---

## 5. The Flags Register (RFLAGS)

`rflags` is a 64-bit register (only the low 32 bits are defined; bits 32–63 are reserved/zero). It holds status, control, and system flags. You read/write it with `pushfq`/`popfq`, `lahf`/`sahf` (partial), and it is set implicitly by arithmetic.

### Status flags (set by arithmetic/logic)

| Bit | Flag | Name | Meaning |
|-----|------|------|---------|
| 0 | CF | Carry | Carry out / borrow in for unsigned arithmetic |
| 2 | PF | Parity | Low byte has an even number of set bits |
| 4 | AF | Adjust | Carry/borrow out of bit 3 (BCD helper) |
| 6 | ZF | Zero | Result was zero |
| 7 | SF | Sign | Result's sign bit (MSB) |
| 11 | OF | Overflow | Signed arithmetic overflow |

### Control flags

| Bit | Flag | Name | Meaning |
|-----|------|------|---------|
| 8 | TF | Trap | Single-step (debug) |
| 9 | IF | Interrupt Enable | Maskable hardware interrupts enabled |
| 10 | DF | Direction | String ops: 0 = forward (increment), 1 = backward (decrement) |
| 16 | RF | Resume | Suppress debug exceptions for one instruction |
| 17 | VM | Virtual-8086 | (legacy mode flag) |
| 18 | AC | Alignment Check | Enable alignment checking |
| 19 | VIF | Virtual Interrupt Flag | Virtual image of IF |
| 20 | VIP | Virtual Interrupt Pending | Virtual interrupt pending |
| 21 | ID | ID | CPUID supported |

### How flags drive conditional jumps

`cmp a, b` computes `a - b` and sets flags without storing the result; `test a, b` computes `a & b`. Conditional jumps then inspect combinations of flags:

- Signed comparisons use **SF, OF, ZF** (e.g., `jl` = "SF ≠ OF").
- Unsigned comparisons use **CF, ZF** (e.g., `jb` = "CF = 1").

This separation is why there are two families of "less/greater" jumps (`jl`/`jg` for signed, `jb`/`ja` for unsigned).

---

## 6. Segment Registers

x86-64 retains six 16-bit segment selectors: **`cs`, `ds`, `ss`, `es`, `fs`, `gs`**. Segmentation is largely disabled in 64-bit mode — `cs`, `ds`, `ss`, `es` are forced to a base of 0 and limit of 2⁶⁴−1 and are mostly ignored. Two remain important:

- **`fs` and `gs`** — their **base addresses** are still honored and are used by operating systems and runtimes for per-thread / per-CPU data:
  - On **Linux**, the kernel sets `gs` base (via the `arch_prctl(ARCH_SET_GS, …)` syscall or the `wrgsbase` instruction) to point at thread-local storage. The C library accesses TLS through `fs` (e.g., the stack canary lives at `fs:[0x28]` on x86-64 Linux).
  - On **Windows**, the `gs` base points to the **TEB** (Thread Environment Block); e.g., `gs:[0x30]` is the PEB pointer, `gs:[0x8]` is the stack base.

Segment overrides look like `mov rax, [gs:0x28]`. In 64-bit mode, only `fs` and `gs` overrides are meaningful; the others are either ignored or cause exceptions in certain cases.

---

## 7. The x87 Floating-Point Unit

The legacy x87 FPU is a register **stack** of eight 80-bit registers: **`st0`–`st7`** (also written `st(0)`–`st(7)`). `st0` is the top of stack; `st(n)` is relative to the top and rotates as you push/pop.

Associated control/state:
- **x87 control word** (rounding mode, precision, exception masks) — loaded/stored with `fldcw`/`fstcw`.
- **x87 status word** (condition codes, top-of-stack pointer, exception flags) — `fstsw`/`fnstsw`; `fstsw ax` is common.
- **x87 tag word** — marks each register as valid/zero/special/empty.

Representative instructions: `fld` (load/push), `fst`/`fstp` (store, optionally pop), `fadd`/`fsub`/`fmul`/`fdiv`, `fsin`/`fcos`/`fsqrt`, `fcom`/`fcomi` (compare), `fxch` (swap with `st0`).

In modern 64-bit code the x87 unit is rarely used directly — SSE2 scalar instructions (`addsd`, `mulsd`, …) replace it — but it still appears in legacy code, in `long double` (80-bit extended precision) handling, and in transcendental functions.

---

## 8. MMX Registers

**MMX** (1997) introduced eight 64-bit registers **`mm0`–`mm7`** for integer SIMD. They are aliased onto the low 64 bits of the x87 `st` registers, so MMX and x87 cannot be used simultaneously without an `emms` to reset the FPU state.

MMX is obsolete in 64-bit code — SSE2's 128-bit XMM registers supersede it entirely — but you will encounter it in old binaries. Instructions: `movq`, `paddb/w/d`, `pmullw`, `pcmpeqb`, etc. Always finish an MMX region with `emms`.

---

## 9. SSE and the XMM Registers

**SSE** (Streaming SIMD Extensions) introduced the 128-bit **XMM** registers. In 64-bit mode there are **16**: **`xmm0`–`xmm15`** (32-bit mode had only 8). Each holds:

- 4 × 32-bit single-precision floats (**ps** = packed single),
- 2 × 64-bit double-precision floats (**pd** = packed double),
- or integer vectors (16 bytes / 8 words / 4 dwords / 2 qwords).

Scalar forms operate on just the low element: **ss** (scalar single) and **sd** (scalar double).

### The MXCSR control/status register

SSE state is governed by the 32-bit **MXCSR** register (read/write with `stmxcsr`/`ldmxcsr`). It controls:
- Rounding mode (bits 13–14),
- Denormals-are-zeros (DAZ, bit 6) and flush-to-zero (FTZ, bit 15),
- Exception masks and flags for the six IEEE-754 exceptions (invalid, denormal, divide-by-zero, overflow, underflow, inexact).

`ldmxcsr` / `stmxcsr` are also used by `xsave`/`xrstor` state management.

### Representative SSE/SSE2/SSE3 instructions

| Instruction | Meaning |
|-------------|---------|
| `movaps` / `movups` | Move aligned / unaligned packed single (128-bit) |
| `movapd` / `movupd` | Move aligned / unaligned packed double |
| `movss` / `movsd` | Move scalar single / double |
| `addps` / `addpd` | Packed add (4 floats / 2 doubles) |
| `addss` / `addsd` | Scalar add |
| `mulps` / `mulpd` / `mulss` / `mulsd` | Multiply variants |
| `divss` / `divsd` | Scalar divide |
| `sqrtps` / `sqrtpd` | Packed square root |
| `maxps` / `minps` | Packed max/min |
| `cmpps` / `cmpss` | Packed/scalar compare → mask |
| `cvtsi2sd` / `cvtsi2ss` | Integer → float/double |
| `cvttsd2si` / `cvttss2si` | Float/double → integer (truncate) |
| `cvtsd2ss` / `cvtss2sd` | Double ↔ single conversion |
| `shufps` / `unpcklps` | Shuffle / unpack lanes |
| `xorps` / `xorpd` | Bitwise XOR (common to zero an XMM) |
| `paddb/w/d/q` | Packed integer add (SSE2) |
| `movd` / `movq` | Move between GPR/memory and XMM |

`movaps` requires 16-byte alignment (faults otherwise); `movups` does not. On modern CPUs with aligned data the two perform identically, but the alignment fault behavior still differs.

### Scalar double-precision instructions in detail (`*sd`)

The suffix **`sd`** means **scalar double**: the instruction operates on a single 64-bit IEEE-754 double-precision value held in the **low quadword (low 64 bits)** of an XMM register. The upper 64 bits of the destination are left **unchanged** by legacy SSE forms (VEX/AVX forms zero the upper bits of the full YMM). These are the workhorses of scalar floating-point math in 64-bit code, replacing the old x87 stack.

**`subsd xmm1, xmm2/m64` — scalar double subtract**
```asm
subsd  xmm0, xmm1        ; xmm0[63:0] = xmm0[63:0] - xmm1[63:0]
subsd  xmm0, [x]         ; subtract the double stored at memory address x
```
Computes `xmm0 = xmm0 - src` on the low double only. Sets no integer flags; floating-point exception flags go to **MXCSR**. Like all SSE scalar ops, it is **non-commutative in operand order**: the destination is the *left* operand and is overwritten.

**`mulsd xmm1, xmm2/m64` — scalar double multiply**
```asm
mulsd  xmm0, xmm1        ; xmm0[63:0] = xmm0[63:0] * xmm1[63:0]
mulsd  xmm0, [scale]     ; xmm0 *= the double at [scale]
```
Multiplies the low doubles. Multiplication is commutative, so operand order doesn't change the numeric result, but the destination is still the first operand. Honors the MXCSR rounding mode and reports overflow/underflow/inexact there.

**`divsd xmm1, xmm2/m64` — scalar double divide**
```asm
divsd  xmm0, xmm1        ; xmm0[63:0] = xmm0[63:0] / xmm1[63:0]
divsd  xmm0, [denom]
```
Computes `xmm0 = xmm0 / src`. **Operand order matters critically** — `divsd xmm0, xmm1` is `xmm0 / xmm1`, not the reverse. Division by zero does **not** trap by default; per IEEE-754 it produces `±infinity` or `NaN` and sets the divide-by-zero flag in MXCSR (unless unmasked). Division is the slowest of the four basic ops (high latency), so compilers hoist it out of tight loops when possible.

**`cvttsd2si r32/r64, xmm1/m64` — convert double to integer with truncation**
```asm
cvttsd2si  eax, xmm0     ; eax = (int32) truncate(xmm0 double)
cvttsd2si  rax, xmm0     ; rax = (int64) truncate(xmm0 double)
```
Converts the scalar double in the source to a **signed integer**, **truncating toward zero** (the extra `t` = truncate). This matches C's cast semantics `(int)x`. Key details:
- The **destination is a general-purpose register** (`eax`/`rax`), not an XMM — this is how floating-point results get back into integer code.
- A 32-bit destination (`eax`) zero-extends into `rax` (standard 32-bit write rule).
- **Out-of-range / NaN results saturate to the "integer indefinite" value** (`0x80000000` for 32-bit, `0x8000000000000000` for 64-bit) and set the invalid-op flag in MXCSR — they do *not* raise a hardware exception by default. So converting `NaN` or a huge double silently yields `INT_MIN`.
- The **non-`t`** variant, `cvtsd2si`, rounds according to the current MXCSR rounding mode (default: round-to-nearest-even) instead of truncating. Use `cvttsd2si` when you want C-cast behavior.

The reverse direction is `cvtsi2sd xmm, r32/m32` (integer → double). A typical scalar expression `double r = (a - b) * c / d;` compiles to a sequence of `subsd` / `mulsd` / `divsd`, and `int n = (int)r;` to a single `cvttsd2si`.

---

## 10. AVX and the YMM Registers

**AVX** (Advanced Vector Extensions, 2011) widened the vector registers to 256 bits, named **`ymm0`–`ymm15`**. The low 128 bits of `ymmN` are exactly `xmmN`; writing an XMM instruction in AVX (VEX-encoded) form zeroes the upper 128 bits of the corresponding YMM.

AVX introduced the **VEX** encoding prefix, which enables a cleaner **three-operand (non-destructive) syntax**:

```asm
vaddps  ymm0, ymm1, ymm2    ; ymm0 = ymm1 + ymm2   (source not clobbered)
vmulsd  xmm0, xmm1, xmm2    ; scalar double multiply
vfmadd231ps ymm0, ymm1, ymm2 ; fused multiply-add (FMA3): ymm0 += ymm1*ymm2
```

**AVX2** (2013) extended most integer SIMD operations to 256-bit YMM and added gather, broadcast, and shift instructions.

**AVX-512** (see next section) widens further and adds masking.

AVX state (the upper halves of YMM, and ZMM/opmask for AVX-512) is managed by **XSAVE/XRSTOR** and the `XCR0` extended control register; the OS must enable it, which is why you check CPUID and OS support before using AVX.

---

## 11. AVX-512: ZMM, Opmask, and Bound Registers

**AVX-512** (2016, in various subsets/foundations) widens vectors to 512 bits and adds substantial new machinery:

### ZMM registers
- **`zmm0`–`zmm31`** — 32 registers of 512 bits each.
- `zmmN` ⊃ `ymmN` ⊃ `xmmN`: the low 256 bits of `zmmN` are `ymmN`, the low 128 are `xmmN`.
- 16 × 32-bit floats, 8 × 64-bit doubles, or integer vectors per register.

### Opmask (writemask) registers
- **`k0`–`k7`** — eight 64-bit mask registers. Each bit selects whether the corresponding vector lane is written.
- Any AVX-512 instruction can be masked: `vaddps zmm1 {k3}, zmm2, zmm3` updates only the lanes where `k3` has a 1.
- `k0` as a mask means "no masking" (all lanes active).
- Masking can be **merging** (untouched lanes keep old value) or **zeroing** (`{z}` — untouched lanes set to 0): `vaddps zmm1 {k3}{z}, zmm2, zmm3`.

### Other AVX-512 features
- **Broadcast** from memory: `vaddps zmm1, zmm2, [rax]{1to16}` broadcasts one float to all 16 lanes.
- **Embedded rounding / SAE** (suppress-all-exceptions): `vaddpd zmm1, zmm2, zmm3, {rn-sae}`.
- **Compressed displacement** (EVEX encoding) for compact 8-bit displacements.
- New instructions: conflict detection (`vpconflictd`), ternary logic (`vpternlogd`), reciprocal approximations (`vrcp14ps`), and many more.

AVX-512 is delivered in **feature subsets** (F, CD, BW, DQ, VL, IFMA, VBMI, VNNI, BF16, FP16, …). Not all CPUs implement all subsets; Intel's 12th-gen+ hybrid "Alder Lake" client CPUs famously disabled AVX-512 on some cores, while AMD added AVX-512 starting with Zen 4 (double-pumped 256-bit datapaths). Always check CPUID feature bits before use.

---

## 12. Control Registers

Control registers configure CPU operation. They are privileged (ring 0) and accessed with `mov` to/from `crN`.

| Register | Purpose |
|----------|---------|
| `cr0` | Master control: PE (protected-mode enable), PG (paging), caching flags, WP (write-protect), etc. |
| `cr2` | Holds the faulting linear address on a page fault. |
| `cr3` | Page-table base: physical address of the PML4 (top-level paging structure) plus PCID/flags. Loaded on every context switch. |
| `cr4` | Extension enables: PAE, SMEP, SMAP, UMIP, PCIDE, OSFXSR/OSXMMEXCPT (SSE), OSXSAVE (AVX), CET, etc. |
| `cr8` | Task Priority Register (TPR) — controls interrupt priority (in 64-bit mode; replaces the APIC TPR access path). |

`cr1`, `cr5`–`cr7`, `cr9`–`cr15` are reserved/undefined.

Related model-specific configuration lives in **MSRs** (Model-Specific Registers), accessed with `rdmsr`/`wrmsr` — e.g., `IA32_EFER` (which holds the Long Mode Enable and NX-enable bits), `IA32_FS_BASE`, `IA32_GS_BASE`, `IA32_SYSENTER_*`, and `IA32_LSTAR` (the `syscall` entry point).

---

## 13. Debug Registers

Used for hardware breakpoints and watchpoints, accessed with `mov` to/from `drN` (privileged):

| Register | Purpose |
|----------|---------|
| `dr0`–`dr3` | Linear addresses of up to four breakpoints/watchpoints. |
| `dr4`–`dr5` | Reserved (alias `dr6`/`dr7` unless `CR4.DE` is set). |
| `dr6` | Debug status: which breakpoint fired, single-step flag, etc. |
| `dr7` | Debug control: enable local/global breakpoints, set condition (execute/write/read-write) and length per breakpoint. |

Debuggers (gdb's `hbreak`, `watch`) program these to get hardware-assisted breakpoints that don't patch code.

---

## 14. System Table Registers

These hold the addresses of kernel descriptor tables. They are not GPRs and are loaded with dedicated instructions:

| Register | Instruction | Purpose |
|----------|-------------|---------|
| `gdtr` | `lgdt` / `sgdt` | Global Descriptor Table register (base + limit). |
| `idtr` | `lidt` / `sidt` | Interrupt Descriptor Table register. |
| `ldtr` | `lldt` / `sldt` | Local Descriptor Table selector. |
| `tr`   | `ltr` / `str`  | Task State Segment selector (holds the 64-bit TSS with RSP/IST stacks for privilege-level and interrupt-stack switching). |

In 64-bit mode the GDT/LDT are mostly vestigial, but the **TSS** is essential: it provides the kernel stack pointers (`rsp0`) and **Interrupt Stack Table (IST)** entries used when handling interrupts/exceptions.

---

## 15. Instruction Encoding and the REX Prefix

x86 uses variable-length instructions (1–15 bytes). A 64-bit instruction may consist of:

```
[legacy prefixes] [REX prefix] [opcode] [ModR/M] [SIB] [displacement] [immediate]
```

### The REX prefix (0x40–0x4F)

The REX byte extends the register/opcode fields:

```
  7 6 5 4 3 2 1 0
┌─┬─┬─┬─┬─┬─┬─┬─┐
│0│1│0│0│W│R│X│B│
└─┴─┴─┴─┴─┴─┴─┴─┘
```

- **W** = 1 → 64-bit operand size (e.g., `mov rax, …` vs. `mov eax, …`).
- **R** extends the ModR/M `reg` field (access `r8`–`r15`).
- **X** extends the SIB `index` field.
- **B** extends the ModR/M `r/m` field, the SIB `base`, or the opcode register field.

A REX prefix with all extension bits 0 (`0x40`) is sometimes emitted just to force a low-byte register like `sil`/`dil`. Note that the opcodes `0x40`–`0x4F` were `inc`/`dec` in 32-bit mode; in 64-bit mode they were repurposed as REX, which is why single-byte `inc reg`/`dec reg` no longer exist in 64-bit mode (use `inc r/m` forms, `FF /0` and `FF /1`).

### Other prefixes
- **Operand-size override** `0x66` (16-bit operand).
- **Address-size override** `0x67` (32-bit addressing in 64-bit mode).
- **Segment overrides** (`0x64` = `fs`, `0x65` = `gs`, etc.).
- **`0xF2`/`0xF3`** — used as mandatory prefixes for SSE2 (`F2` = double, `F3` = single) and as `rep`/`repne` for string ops.
- **VEX** (2/3-byte) for AVX, **EVEX** (4-byte) for AVX-512 — these replace, not stack with, REX.

---

## 16. Instruction Syntax: Intel vs. AT&T

Two textual syntaxes exist. They describe the same machine code.

**Intel syntax** (NASM, MASM, and disassemblers via `objdump -M intel` / `ndisasm`):
```asm
mov  rax, rbx        ; destination, source
mov  rax, [rcx + 8]  ; brackets denote memory
add  rax, 5          ; bare immediate
```

**AT&T syntax** (GAS, the GNU assembler; default `objdump` output):
```asm
movq %rbx, %rax      ; source, destination  (reversed!)
movq 8(%rcx), %rax   ; displacement before (base)
addq $5, %rax        ; $ prefix on immediates, % prefix on registers
```

Key differences:
- **Operand order:** Intel is `dest, src`; AT&T is `src, dest`.
- **Sigils:** AT&T prefixes registers with `%` and immediates with `$`.
- **Size:** AT&T uses suffixes `b/w/l/q` (byte/word/long/quad); Intel uses keywords `byte/word/dword/qword` only when size is ambiguous (e.g., `mov qword [rax], 0`).
- **Memory:** AT&T writes `disp(base, index, scale)`; Intel writes `[base + index*scale + disp]`.

This document uses **Intel / NASM** syntax.

---

## 17. Data Sizes and Operand Types

| Keyword (NASM) | AT&T suffix | Size |
|----------------|-------------|------|
| `byte`  | `b` | 8 bits |
| `word`  | `w` | 16 bits |
| `dword` | `l` | 32 bits |
| `qword` | `q` | 64 bits |
| `tword` | `t` | 80 bits (x87 extended) |
| `oword` / `xmmword` | — | 128 bits |
| `yword` / `ymmword` | — | 256 bits |
| `zword` / `zmmword` | — | 512 bits |

The operand size must be inferable from the registers or stated explicitly: `mov [rax], 1` is ambiguous; `mov qword [rax], 1` is not.

---

## 18. Endianness

**Endianness** is the order in which the bytes of a multi-byte value are laid out in memory. x86-64 is a **little-endian** architecture: the **least-significant byte (LSB) is stored at the lowest address**, and the most-significant byte (MSB) at the highest.

### Example: a 32-bit value in memory

The `dword` value `0x11223344` stored at address `0x1000`:

```
address:   0x1000   0x1001   0x1002   0x1003
byte:       0x44     0x33     0x22     0x11
            └──────── LSB first ────────┘  ← little-endian
```

A 64-bit `0x0102030405060708` at `0x2000` would appear in memory as `08 07 06 05 04 03 02 01`.

This is the opposite of **big-endian** (used by network byte order, and historically by PowerPC, SPARC, and Motorola 68k), where the MSB comes first.

### How this shows up in registers

Registers themselves don't have an "endian" — a register is just a numbered set of bits, and `rax = 0x1122334455667788` means bit 63..56 = `0x11` down to bit 7..0 = `0x88`. Endianness only matters at the **register ↔ memory boundary**:

```asm
mov  qword [mem], 0x1122334455667788
; memory at [mem]: 88 77 66 55 44 33 22 11   (LSB at lowest address)

mov  rax, [mem]      ; loads those 8 bytes back, reconstructing 0x1122...7788
mov  al,  [mem]      ; loads ONLY the lowest-address byte → al = 0x88
mov  ah,  [mem]      ; (ah is bits 8-15 of rax, NOT the next memory byte!)
```

### Endianness gotchas

- **Byte order reverses between "value" and "memory dump."** A hex editor or `xxd` shows bytes low-address-first, so a 32-bit `0xDEADBEEF` appears as `EF BE AD DE`. This trips up everyone reading binary files or shellcode the first time.

- **Sub-register access is by bit position, not by memory position.** `al` is bits 0–7 of `rax` (the *least* significant byte), which happens to be the byte at the lowest address after a little-endian store. But `ah` is bits 8–15 — not "the byte after `al` in some abstract sense." When you load a single byte with `mov al, [mem]`, you get the lowest-address byte; the mapping to `ah`/`ax`/`eax` is fixed by bit numbering.

- **Partial loads don't "continue" where a smaller load left off in an obvious way.** After `mov al, [mem]` (gets byte at `mem`), doing `mov ah, [mem+1]` manually assembles the 16-bit value `ax = (mem+1 byte)<<8 | (mem byte)`, which equals `mov ax, [mem]` only because of little-endian layout. On a big-endian machine the same code would produce a different `ax`.

- **`movzx`/`movsx` and width mismatches.** Loading a `byte` into a 64-bit register without zero/sign extension leaves the upper bytes as garbage. Always match the load width to the data: `movzx eax, byte [p]` vs. `mov eax, [p]` read 1 vs. 4 bytes from memory.

- **Strings are endian-neutral.** A `db "hi"` is bytes `68 69` regardless of endianness, because each character is a single byte. Endianness only affects multi-byte units (`dw`, `dd`, `dq`).

- **Interfacing with big-endian data (network, some file formats).** Network protocols use **big-endian** ("network byte order"). You must convert with `htonl`/`htons`/`ntohl`/`ntohs` (or `bswap`) when moving data between the wire and x86 registers:
  ```asm
  mov   eax, [packet]    ; big-endian field as stored in memory
  bswap eax              ; reverse byte order → correct integer value
  ```
  `bswap r32/r64` reverses the bytes of a register (it has no 16-bit form; use `xchg ah, al` or `rol ax, 8` for words).

- **Serialization / struct padding.** When writing a struct to disk or the network, both endianness *and* compiler-inserted padding/alignment affect the byte layout. Don't assume a C struct's in-memory layout is portable.

- **Floating point is also little-endian on x86.** An IEEE-754 `double` is stored LSB-first too, so the same byte-reversal concerns apply when exchanging floats with big-endian systems.

**Rule of thumb:** within a single x86-64 program, endianness is invisible — loads and stores agree. It only becomes a problem at **I/O boundaries**: files, network sockets, shared memory with other architectures, and reading hex dumps.

---

## 19. Memory Addressing Modes

The general 64-bit addressing form is:

```
[ base + index*scale + displacement ]
```

- **base**: any GPR (often `rbp`/`rsp`/`rbx` or `r12`–`r15`).
- **index**: any GPR except `rsp`.
- **scale**: 1, 2, 4, or 8.
- **displacement**: 8-bit (sign-extended) or 32-bit signed offset.

Examples:
```asm
mov rax, [rbx]               ; indirect
mov eax, [rbx + 8]           ; base + displacement
mov rax, [rbx + rcx*8]       ; base + index*scale  (array of qwords)
mov rax, [rbp - 16]          ; stack local
mov rax, [rip + 0x2000]      ; RIP-relative (often written [rel sym])
mov rax, [rsp + rdx*4 + 12]  ; full SIB form
```

Special cases:
- `[rsp]` and `[r12]` as a base force a SIB byte (the encoding uses `rsp` to signal "SIB follows").
- There is **no** `[index*scale + disp]` without a base in the pure form — the assembler encodes it with a base of 0 via SIB.
- **RIP-relative** cannot combine with index/scale; it is `[rip + disp32]` only.

---

## 20. Core Instructions

### 19.1 Data movement
```asm
mov   rax, 42             ; immediate → register
mov   rax, rbx            ; register → register
mov   rax, [rbx]          ; memory → register
mov   [rbx], rax          ; register → memory
lea   rax, [rbx + rcx*4]  ; compute address, do NOT dereference
movzx eax, byte [rbx]     ; move with zero-extend
movsx rax, byte [rbx]     ; move with sign-extend
movsxd rax, ebx           ; sign-extend 32 → 64
xchg  rax, rbx            ; swap
push  rax                 ; rsp -= 8; [rsp] = rax
pop   rax                 ; rax = [rsp]; rsp += 8
movabs rax, 0x1122334455667788  ; full 64-bit immediate (only mov allows this)
```
`movabs` is the only instruction that takes a full 64-bit immediate. `lea` is heavily used for arithmetic: `lea rax, [rax + rax*4]` computes `rax*5` in one instruction without touching flags.

### 19.2 Arithmetic
```asm
add  rax, rbx
sub  rax, 1
imul rax, rbx             ; rax = rax * rbx (signed, low 64 bits)
imul rax, rbx, 10         ; rax = rbx * 10
imul rax, rbx             ; two-operand form
mul  rbx                  ; unsigned: rdx:rax = rax * rbx
div  rcx                  ; unsigned: rax = rdx:rax / rcx, rdx = rdx:rax % rcx
idiv rcx                  ; signed version
inc  rax
dec  rax
neg  rax                  ; two's-complement negate
cqo                       ; sign-extend rax → rdx:rax (prep for idiv)
cdq                       ; sign-extend eax → edx:eax
```
Division uses the implicit 128-bit dividend `rdx:rax`. For signed division, run `cqo` first to sign-extend `rax` into `rdx`; for unsigned, zero `rdx` (`xor edx, edx`).

### 19.3 Bitwise logic and shifts
```asm
and  rax, rbx
or   rax, rbx
xor  rax, rax             ; zero rax (idiomatic)
not  rax
shl  rax, 4               ; shift left = multiply by 16
shr  rax, 1               ; logical shift right (zero-fill; unsigned)
sar  rax, 1               ; arithmetic shift right (sign-fill; signed)
rol  rax, 1               ; rotate left
ror  rax, 1
shld / shrd               ; double-precision shifts
bsf  rax, rbx             ; bit scan forward (index of lowest set bit)
bsr  rax, rbx             ; bit scan reverse (index of highest set bit)
popcnt rax, rbx           ; population count (POPCNT feature)
tzcnt / lzcnt             ; trailing / leading zero count (BMI1 / LZCNT)
```
Shift counts come from an immediate or from `cl`.

### 19.4 Compare and test
```asm
cmp  rax, rbx             ; set flags as if rax - rbx, discard result
test rax, rax             ; set flags as if rax & rax (common zero/sign check)
```

### 19.5 String operations
`movs`, `stos`, `lods`, `scas`, `cmps` operate on `[rsi]`/`[rdi]` and auto-increment/decrement per `DF`. Prefixed with `rep`/`repe`/`repne`. `rep stosb` with `al` is the classic memset; `rep movsb` is memcpy (enhanced "ERMS" makes this fast on modern CPUs). Use `cld` to clear `DF` (forward) — ABIs require `DF=0` on function entry.

---

## 21. Relative Virtual Addresses and Navigating Large Programs

Real programs are not one flat blob of bytes at a fixed address. They are split into **sections**, loaded at **virtual addresses**, and (in modern systems) relocated at load time. Understanding **Relative Virtual Addresses (RVAs)**, the section layout, and the tooling is what lets you move around a large binary confidently.

### Virtual addresses, base addresses, and RVAs

- **Virtual Address (VA):** the actual address a running process uses, e.g. `0x00007ff6a1b2c3d0`. Each process has its own virtual address space.
- **Image base / load base:** the address at which the loader places the executable or shared library. A PIE (position-independent executable) or shared object can be loaded at *any* base; ASLR randomizes it each run.
- **Relative Virtual Address (RVA):** an offset **relative to the image base**:
  ```
  RVA = VA - image_base
  VA  = image_base + RVA
  ```
  RVAs are stable regardless of where the image lands, which is why file formats (especially the Windows **PE** format) store pointers internally as RVAs. On Windows you'll see RVAs everywhere: the PE optional header's `AddressOfEntryPoint`, the export table, the import table, and relocations are all RVAs. To get a usable runtime pointer you add the module's actual base: `func_ptr = module_base + export_rva`.
- **File offset:** the position of a byte within the on-disk file. This is **not** the same as the RVA or VA — sections are aligned differently on disk than in memory (see below).

On Linux ELF binaries the same idea appears as **VMA** (virtual memory address) vs. file offset, and ELF uses absolute virtual addresses in its program headers plus relocations, rather than PE-style RVAs; but the mental model — "where is this byte on disk, where does it live in memory, and what's the offset from the base?" — is identical.

### Sections (segments): how a binary is divided

A binary is divided into **sections** (ELF term) / **sections within segments** (PE term). The important ones:

| Section | Contents | Permissions |
|---------|----------|-------------|
| `.text` | Machine code | read + execute |
| `.rodata` | Constants, string literals, jump tables | read-only |
| `.data` | Initialized global/static variables | read + write |
| `.bss` | Uninitialized globals (zero-filled, occupies no file space) | read + write |
| `.plt` / `.got` | Procedure Linkage Table / Global Offset Table (dynamic linking) | varies |
| `.symtab` / `.strtab` | Symbol table / string table (ELF; often stripped in release builds) | — |
| `.dynsym` / `.dynstr` | Dynamic symbols / strings (needed at runtime) | — |
| `.rela.*` / `.reloc` | Relocations | — |

**Crucial distinction — file offset vs. memory address:** each section has *two* alignments. On disk, sections are aligned to the **file alignment** (often 512 bytes / `0x200`); in memory, to the **section alignment** (often 4096 bytes / `0x1000`, the page size). So a function at RVA `0x1234` is generally **not** at file offset `0x1234`. To convert, find the section containing the RVA and apply:
```
file_offset = rva - section_rva + section_file_offset
```
Tools do this for you, but knowing the formula explains why a hex editor offset never matches the disassembler address.

### Navigating a large assembly program

When a disassembly is tens or hundreds of thousands of lines, you navigate by **symbols, addresses, and structure**, not by scrolling:

- **Use symbols as landmarks.** Function names, labels, and imported symbols are your anchors. `objdump -d` interleaves symbol names with code; IDA/Ghidra/Binary Ninja build full symbol lists and cross-references.
- **Jump by address.** In a debugger or disassembler, go directly to an address (`gdb`: `disassemble 0x4011a0`; IDA: press `g`). Convert between RVA and VA with the module base when ASLR is in play (`info proc mappings` in gdb, or `vmmap` in GEF/pwndbg).
- **Follow the call graph.** From a function, list what it calls (callees) and what calls it (callers / cross-references, "xrefs"). This is the fastest way to trace behavior through a big program.
- **Read the control-flow graph (CFG).** Disassemblers render each function as a graph of basic blocks connected by jumps. Recognizing the shape — a loop back-edge, a diamond if/else, a switch jump table — tells you the high-level structure without reading every instruction.
- **Use the section headers to orient.** Knowing you're in `.rodata` means you're looking at constants/strings (a string reference often reveals a function's purpose); `.text` is code; `.data`/`.bss` are globals.
- **Trace strings and imports.** Searching for a string literal or an API name (e.g., `open`, `recv`, `CreateFileW`) and following xrefs to it is a standard way to locate the code that matters.

### Position-independent code and RIP-relative navigation

Modern 64-bit code is usually **position-independent** (PIE executables, shared libraries), so it cannot embed absolute addresses for its own data. Instead it uses **RIP-relative addressing** to reach globals and literals:
```asm
lea  rdi, [rel msg]        ; rdi = address of msg, computed relative to RIP
mov  rax, [rel counter]    ; load a global, wherever the image is loaded
```
`[rel sym]` assembles to `[rip + disp32]`, where the displacement is the offset from the *next* instruction to the symbol. This is effectively an RVA-style offset baked into the instruction, and it's why disassembly of PIC code is full of `lea ...,[rip+0x...]`. With `default rel` in NASM, RIP-relative becomes the default for symbolic memory operands.

Dynamic linking adds the **GOT/PLT**: a call to an external function goes through a PLT stub that resolves the real address (lazily) via the GOT, so the same code works regardless of where the library is loaded.

### Practical navigation commands
```bash
readelf -S prog              # section headers (addresses + file offsets)
readelf -l prog              # program headers / segments (load mapping)
readelf -s prog | less       # symbol table with addresses
objdump -d -M intel prog     # disassembly with symbols
objdump -h prog              # section header summary (VMA, LMA, file off)
nm -C prog                   # list symbols (demangled)
ldd prog                     # shared-library dependencies

# In gdb, with a PIE/ASLR binary:
(gdb) info proc mappings     # actual load addresses of every region
(gdb) disassemble /m main    # disassemble with source if available
(gdb) x/20i $pc              # examine 20 instructions at the program counter
```

**Rule of thumb:** think in three coordinate systems — *file offset*, *RVA (offset from image base)*, and *VA (live address)* — and let the section headers and your tools translate between them. Symbols and cross-references, not raw scrolling, are how you navigate a large program.

---

## 22. Control Flow

### 20.1 Unconditional
```asm
jmp  label
jmp  rax              ; indirect jump (computed target)
call function         ; push return address, jump
call rax              ; indirect call
ret                   ; pop return address and jump to it
ret  8                ; ret and add 8 to rsp (rare in 64-bit)
```

### 20.2 Conditional jumps

| Instruction | Condition (flags) | Meaning |
|-------------|-------------------|---------|
| `je` / `jz` | ZF=1 | equal / zero |
| `jne` / `jnz` | ZF=0 | not equal / not zero |
| `jl` / `jnge` | SF≠OF | signed less |
| `jle` / `jng` | ZF=1 or SF≠OF | signed less or equal |
| `jg` / `jnle` | ZF=0 and SF=OF | signed greater |
| `jge` / `jnl` | SF=OF | signed greater or equal |
| `jb` / `jc` / `jnae` | CF=1 | unsigned below / carry |
| `jbe` / `jna` | CF=1 or ZF=1 | unsigned below or equal |
| `ja` / `jnbe` | CF=0 and ZF=0 | unsigned above |
| `jae` / `jnc` | CF=0 | unsigned above or equal / no carry |
| `js` / `jns` | SF=1 / SF=0 | negative / non-negative |
| `jo` / `jno` | OF=1 / OF=0 | overflow / no overflow |
| `jp` / `jpe` | PF=1 | parity even |
| `jcxz`/`jecxz`/`jrcxz` | rcx=0 | rcx is zero |

### 20.3 Conditional set and move (branchless)
```asm
cmp    rax, rbx
setl   al            ; al = 1 if rax < rbx (signed), else 0
cmovl  rax, rbx      ; rax = rbx if rax < rbx  (branchless min)
```
`setcc` writes a 0/1 byte; `cmovcc` conditionally moves a full operand. Compilers favor these to avoid branch misprediction.

### 20.4 Example: if/else
```asm
    cmp  rax, 0
    jne  .else
    mov  rbx, 1
    jmp  .end
.else:
    mov  rbx, 2
.end:
```

### 20.5 Example: counted loop
```asm
    xor  ecx, ecx        ; i = 0  (also zeroes rcx)
    xor  eax, eax        ; sum = 0
.loop:
    add  rax, rcx
    inc  rcx
    cmp  rcx, 10
    jl   .loop
```
The `loop` instruction (decrement `rcx`, jump if ≠ 0) exists but is slow on many CPUs; explicit `dec`/`jnz` is preferred.

---

## 23. The Stack and Stack Frames

The stack grows **downward** (to lower addresses). `rsp` points at the last pushed item.

```asm
push rax        ; rsp -= 8; [rsp] = rax
pop  rax        ; rax = [rsp]; rsp += 8
```
`push`/`pop` in 64-bit mode always move 8 bytes (there is no 16-bit `push` default; `pushw` exists with an override).

### Standard frame layout
```
        high addresses
    ┌───────────────────────────┐
    │  arg N (7th+), if any     │  passed on stack
    ├───────────────────────────┤
    │  return address           │  ← pushed by CALL
    ├───────────────────────────┤
    │  saved rbp                │  ← rbp (frame pointer)
    ├───────────────────────────┤
    │  saved callee-saved regs  │  (rbx, r12-r15 …)
    ├───────────────────────────┤
    │  local variables          │
    │                           │  ← rsp
    └───────────────────────────┘
        low addresses
```

### Prologue / epilogue
```asm
func:
    push rbp
    mov  rbp, rsp
    sub  rsp, 32          ; 32 bytes of locals
    ; ... body ...
    leave                 ; == mov rsp, rbp ; pop rbp
    ret
```

### 16-byte alignment
Both ABIs require `rsp` to be **16-byte aligned immediately before a `call`**. Because `call` pushes an 8-byte return address, on function entry `rsp ≡ 8 (mod 16)`. Misalignment commonly crashes SSE instructions that require aligned stack spills.

### The red zone (System V only)
The **128 bytes below `rsp`** are a "red zone" that leaf functions may use freely without adjusting `rsp`. It is **not** preserved across calls or by signal handlers. The **Microsoft x64 ABI has no red zone** — Windows interrupt/exception handlers may write below `rsp`.

---

## 24. Calling Conventions

### 22.1 System V AMD64 ABI (Linux, macOS, BSD, Solaris, illumos)

**Integer/pointer arguments**, in order:
```
rdi, rsi, rdx, rcx, r8, r9
```
Further arguments go on the stack (pushed right-to-left, 16-byte aligned before `call`).

**Floating-point arguments**: `xmm0`–`xmm7`.

**Return value**: `rax` (integer/pointer); `xmm0` (float/double); `rdx:rax` for 128-bit integers; `xmm0:xmm1` for some aggregate floats. Large structs may be returned via a hidden caller-provided pointer passed in `rdi`.

**Caller-saved (clobbered by calls):** `rax`, `rcx`, `rdx`, `rsi`, `rdi`, `r8`–`r11`, and all `xmm`/`ymm`.

**Callee-saved (must be preserved):** `rbx`, `rbp`, `r12`–`r15`, and `rsp`.

**Variadic functions** (e.g., `printf`): `al` must hold the **number of vector (XMM) arguments** passed. For `printf` with no float args, set `xor eax, eax`.

Example — `printf("x = %d\n", 42)`:
```asm
    mov   rdi, fmt        ; 1st arg: format string pointer
    mov   esi, 42         ; 2nd arg
    xor   eax, eax        ; 0 vector args (required for varargs)
    call  printf wrt ..plt   ; (NASM ELF64 PIC form) or: call printf
```

### 22.2 Microsoft x64 ABI (Windows)

**Integer/pointer arguments**, in order:
```
rcx, rdx, r8, r9
```
**Floating-point arguments**: `xmm0`–`xmm3`.

**Shadow space (home space):** the **caller must reserve 32 bytes** (4 × 8) on the stack before the call, even for leaf functions; the callee may spill the first four register arguments there. The stack must be 16-byte aligned before `call`, and there is **no red zone**.

**Return value**: `rax` / `xmm0`.

**Caller-saved:** `rax`, `rcx`, `rdx`, `r8`–`r11`.

**Callee-saved:** `rbx`, `rbp`, `rdi`, `rsi`, `rsp`, `r12`–`r15`, and **`xmm6`–`xmm15`** (note: Windows preserves more XMM registers than System V).

> **Key contrasts:** argument registers differ (`rdi,rsi,rdx,rcx,r8,r9` vs. `rcx,rdx,r8,r9`); Windows requires 32 bytes of shadow space and has no red zone; Windows preserves `rdi`/`rsi` and `xmm6`–`xmm15`.

### 22.3 Complete function example (System V)

```asm
; long add(long a, long b)   — a in rdi, b in rsi
section .text
global add
add:
    lea  rax, [rdi + rsi]   ; rax = a + b
    ret                      ; return in rax
```

A function that must survive a call using callee-saved registers:
```asm
compute:
    push rbx                ; preserve callee-saved rbx
    mov  rbx, rdi
    call helper             ; may clobber rax, rcx, rdx, rsi, rdi, r8-r11
    add  rbx, rax           ; rbx survived
    mov  rax, rbx
    pop  rbx
    ret
```

---

## 25. Linux System Calls

Use the `syscall` instruction. Syscall number in `rax`; arguments in `rdi, rsi, rdx, r10, r8, r9` (note **`r10` replaces `rcx`** for the 4th argument, because `syscall` clobbers `rcx`). Return value in `rax`; negative values in the range `-4095..-1` indicate errors (`-errno`). `syscall` clobbers `rcx` and `r11`.

Common syscall numbers (x86-64): `read`=0, `write`=1, `open`=2, `close`=3, `stat`=4, `fstat`=5, `mmap`=9, `mprotect`=10, `munmap`=11, `brk`=12, `ioctl`=16, `access`=21, `exit`=60, `openat`=257, `exit_group`=231.

**"Hello, World" (Linux, static, NASM):**
```asm
section .data
    msg db "Hello, World!", 10
    len equ $ - msg

section .text
global _start
_start:
    mov  rax, 1          ; sys_write
    mov  rdi, 1          ; fd = stdout
    lea  rsi, [rel msg]  ; buffer (RIP-relative)
    mov  rdx, len        ; count
    syscall

    mov  rax, 60         ; sys_exit
    xor  rdi, rdi        ; status = 0
    syscall
```

---

## 26. SIMD Programming in Practice

### Scalar floating point (SSE2)
```asm
    movsd  xmm0, [a]        ; xmm0 = a (double)
    addsd  xmm0, [b]        ; xmm0 += b
    mulsd  xmm0, [c]        ; xmm0 *= c
    movsd  [result], xmm0
```

### Packed: add four floats at once (SSE)
```asm
    movaps xmm0, [vec1]     ; 4 floats (16-byte aligned)
    addps  xmm0, [vec2]
    movaps [out], xmm0
```

### AVX 256-bit, non-destructive
```asm
    vmovaps ymm0, [vec1]    ; 8 floats
    vaddps  ymm0, ymm0, [vec2]
    vmovaps [out], ymm0
    vzeroupper              ; avoid SSE/AVX transition penalty
```

### AVX-512 with masking and broadcast
```asm
    ; out[i] = (mask[i]) ? a[i] + scalar : out[i]
    vmovaps   zmm1, [a]
    vaddps    zmm1 {k2}{z}, zmm1, [scalar]{1to16}  ; masked, broadcast scalar
    vmovaps   [out] {k2}, zmm1
```

### Integer <-> float conversions
```asm
    cvtsi2sd  xmm0, eax     ; int → double
    cvttsd2si eax, xmm0     ; double → int (truncate toward zero)
    cvtsi2ss  xmm0, eax     ; int → float
```

**Practical notes:**
- Use `vzeroupper` (or `vzeroall`) when transitioning between AVX (VEX) code and legacy SSE code to avoid transition penalties on some Intel CPUs.
- Prefer aligned moves (`movaps`) with aligned data; ensure 16/32/64-byte alignment for `xmm`/`ymm`/`zmm` loads as appropriate.
- Check CPUID + OS XSAVE support before using AVX/AVX-512.

---

## 27. Assembler Directives (NASM)

```asm
section .data               ; initialized, writable data
    x   dq  0x1122334455667788   ; qword
    arr dd  1, 2, 3, 4           ; 4 dwords
    s   db  "hello", 0           ; byte string, NUL-terminated
    f   dq  3.14159              ; double constant

section .rodata             ; read-only data (typical for constants)

section .bss                ; uninitialized (zeroed at load), no space in file
    buf  resb 64            ; reserve 64 bytes
    qarr resq 16            ; reserve 16 qwords

section .text               ; code
global _start               ; export entry symbol
extern printf               ; import external symbol
```

Define: `db` (1), `dw` (2), `dd` (4), `dq` (8), `dt` (10), `do`/`dq` variants for 16/32/64-byte (`ddq`, `dy`, `dz`). Reserve: `resb`, `resw`, `resd`, `resq`, `rest`, `resdq`, `resy`, `resz`.

NASM size/rel helpers: `[rel sym]` forces RIP-relative; `default rel` makes RIP-relative the default (recommended for ELF64/PIC).

---

## 28. Building, Linking, and Debugging

### Assemble + link a freestanding Linux program
```bash
nasm -f elf64 hello.asm -o hello.o
ld  hello.o -o hello
./hello
```

### Link against the C library (for printf, etc.)
```bash
nasm -f elf64 main.asm -o main.o
gcc  main.o -o main -no-pie        # -no-pie avoids PLT/PIC complications
./main
```
For position-independent executables (the default on modern distros), use `default rel`, call through the PLT (`call printf wrt ..plt`), and pass `-pie`/`-fPIE` appropriately.

### Inspect and debug
```bash
objdump -d -M intel main           # disassemble with Intel syntax
readelf -a main                    # ELF structure
gdb ./main
```
Useful GDB commands:
```
(gdb) layout asm            # assembly view
(gdb) info registers        # all GPRs
(gdb) p/x $rax              # print register in hex
(gdb) x/16xb $rsp           # examine 16 bytes at rsp
(gdb) disassemble /r func   # disassemble with raw bytes
(gdb) stepi / nexti         # single-step one instruction
(gdb) tui enable            # text UI
```

---

## 29. Common Idioms, Performance Notes, and Pitfalls

### Idioms
| Idiom | Purpose |
|-------|---------|
| `xor eax, eax` | Zero `rax` (short, breaks dependency chain) |
| `xorps xmm0, xmm0` | Zero an XMM register |
| `test rax, rax` / `jz` | Null/zero check |
| `lea rax, [rbx + rcx*8]` | Fast multiply-add / address math |
| `lea rax, [rax + rax*4]` | Multiply by 5 |
| `cqo` before `idiv` | Sign-extend dividend |
| `xor edx, edx` before `div` | Zero high dividend (unsigned) |
| `leave` | Tear down frame (`mov rsp,rbp; pop rbp`) |
| `cdqe` | Sign-extend `eax` → `rax` |
| `vzeroupper` | Clear upper YMM to avoid AVX/SSE penalty |

### Performance notes
- Prefer 32-bit operations when values fit — they encode shorter and zero-extend for free.
- Use `xor reg, reg` for zeroing; CPUs special-case it.
- Avoid **partial-register writes** followed by full reads (e.g., write `al`, then read `rax`) — they can create false dependencies or merging stalls on some microarchitectures.
- Keep the stack 16-byte aligned before every `call`.
- Prefer `cmov`/`setcc` over branches when the branch is hard to predict.
- `rep movsb`/`rep stosb` are fast memset/memcpy on CPUs with ERMS/FSRM.

### Pitfalls
- Forgetting that 32-bit writes zero the upper 32 bits (but 8/16-bit writes do not).
- Using `ah`/`bh`/`ch`/`dh` with instructions that need a REX prefix (illegal).
- Misaligned `movaps`/`movapd` → `#GP`/`#AC` fault.
- Wrong calling convention (mixing SysV and Windows arg registers).
- Not setting `al` for variadic calls under System V.
- Using the red zone on Windows, or across a call/signal on Linux.
- Forgetting `syscall` clobbers `rcx` and `r11`.

---

## 30. What Changed from 32-bit x86

- GPRs widened to 64 bits; registers `r8`–`r15` added (16 total).
- XMM registers increased from 8 to 16; later YMM (AVX) and ZMM/k-masks (AVX-512).
- Default operand size is 32-bit; 64-bit operands need the REX.W prefix.
- Pointers are 8 bytes; `push`/`pop` move 8 bytes; the stack is always 64-bit.
- RIP-relative addressing added and widely used.
- Single-byte `inc reg`/`dec reg` opcodes repurposed as REX prefixes.
- Removed/invalid in 64-bit mode: `pusha`/`popa`, `aaa`/`aad`/`aam`/`das`, far jumps/calls in several forms, `lds`/`les`, and most segmentation semantics.
- Floating point done via SSE2 XMM by default rather than the x87 stack.
- New `syscall`/`sysret` fast system-call path (replacing `int 0x80` for 64-bit Linux).

---

## 31. Quick-Reference Tables

### GPR sub-register aliasing
```
rax ─ eax ─ ax ─ al      (and ah = bits 8-15)
rcx ─ ecx ─ cx ─ cl      (and ch)
rdx ─ edx ─ dx ─ dl      (and dh)
rbx ─ ebx ─ bx ─ bl      (and bh)
rsp ─ esp ─ sp ─ spl
rbp ─ ebp ─ bp ─ bpl
rsi ─ esi ─ si ─ sil
rdi ─ edi ─ di ─ dil
r8  ─ r8d ─ r8w ─ r8b     ... through r15 ─ r15d ─ r15w ─ r15b
```

### System V vs. Microsoft x64 calling convention
| Aspect | System V (Linux/macOS/BSD) | Microsoft x64 (Windows) |
|--------|----------------------------|--------------------------|
| Int args | `rdi, rsi, rdx, rcx, r8, r9` | `rcx, rdx, r8, r9` |
| FP args | `xmm0`–`xmm7` | `xmm0`–`xmm3` |
| Return | `rax` / `xmm0` | `rax` / `xmm0` |
| Shadow space | none | 32 bytes required |
| Red zone | 128 bytes | none |
| Callee-saved GPR | `rbx, rbp, r12-r15` | `rbx, rbp, rdi, rsi, r12-r15` |
| Callee-saved XMM | none | `xmm6`–`xmm15` |
| Varargs | `al` = # of XMM args | integer args also shadow-spilled |

### Register file summary
| Class | Registers | Width / count |
|-------|-----------|---------------|
| GPR | `rax`…`r15` | 64-bit × 16 |
| Instruction pointer | `rip` | 64-bit × 1 |
| Flags | `rflags` | 64-bit × 1 |
| Segment | `cs, ds, ss, es, fs, gs` | 16-bit selectors × 6 |
| x87 FPU | `st0`–`st7` | 80-bit × 8 (stack) |
| MMX | `mm0`–`mm7` | 64-bit × 8 (aliases x87) |
| SSE | `xmm0`–`xmm15` | 128-bit × 16 |
| AVX | `ymm0`–`ymm15` | 256-bit × 16 |
| AVX-512 vector | `zmm0`–`zmm31` | 512-bit × 32 |
| AVX-512 mask | `k0`–`k7` | 64-bit × 8 |
| Control | `cr0, cr2, cr3, cr4, cr8` | 64-bit |
| Debug | `dr0`–`dr3, dr6, dr7` | 64-bit |
| System tables | `gdtr, idtr, ldtr, tr` | base/limit or selector |

---

## Further Reading

- *Intel® 64 and IA-32 Architectures Software Developer's Manual* (SDM), Volumes 1–2 — the authoritative ISA reference.
- *AMD64 Architecture Programmer's Manual*, Volumes 1–5.
- *System V Application Binary Interface, AMD64 Architecture Processor Supplement*.
- *Microsoft x64 calling convention* documentation (learn.microsoft.com).
- Agner Fog's optimization manuals and instruction tables (agner.org).
