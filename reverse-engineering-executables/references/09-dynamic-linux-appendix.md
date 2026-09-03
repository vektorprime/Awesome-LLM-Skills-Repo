# 09 — Linux ELF Dynamic Appendix (Only If Target Is ELF)

Skip entirely for PE. Same execution gate applies.

## strace (bounded, per-facet)

```bash
mkdir -p "$CASE/artifacts/dynamic/run-001" && cd "$CASE/artifacts/dynamic/run-001"
strace -ff -o strace -s 256 -yy -ttt --kill-on-exit -- /path/to/target arg1 arg2
# focused:
strace -ff -o file.trace -e trace=%file -- /path/to/target
strace -ff -o net.trace  -e trace=%network -- /path/to/target
strace -ff -o proc.trace -e trace=%process -- /path/to/target
strace -ff -o mem.trace  -e trace=mmap,mprotect,munmap,brk,memfd_create -- /path/to/target
```

`openat(...) = -1 ENOENT` is an attempt, not a read. Quote return values.

## ltrace limits

```bash
ltrace -f -s 256 -o ltrace.txt -- /path/to/target
```

Only intercepts dynamic library calls. Useless for static binaries, direct syscalls, inlined code. Never present as solution for static targets.

## GDB batch + targeted breaks

`scripts/gdb-baseline.txt`:

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

```bash
gdb -q -nx -batch -x "$CASE/scripts/gdb-baseline.txt" --args /path/to/target arg1 arg2
```

Targeted:

```text
set breakpoint pending on
break main
catch syscall mmap
catch syscall mprotect
catch syscall memfd_create
run
```

For PIE: `runtime = base + RVA` after `info proc mappings`. `mprotect` alone ≠ unpacking — need write→execute transfer proof (see `10-...`).

Dump confirmed region only:

```text
info proc mappings
dump binary memory /case/artifacts/memory/region.bin 0xSTART 0xEND
```

Record PID/cmdline, mapping perms, why selected, SHA-256 of dump, VA→file-offset relation. Raw mapping is not a loadable ELF — reconstruct only what the question needs.

## rr + Frida

```bash
rr record /path/to/target arg1 arg2
rr replay
```

Use for nondeterministic crashes + reverse-step. Verify `rr` supports the CPU/container — it fails silently on some virtualized PMCs. Frida: trace narrowly (`frida-trace -f target -i 'open*' -i 'connect*'` with module qualifiers), validate arg types per-arch before interpreting.
