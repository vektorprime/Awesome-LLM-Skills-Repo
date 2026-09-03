# 05 — Disassembly with Rizin (r2 Fallback)

Rizin-first. Radare2 (`r2`/`rabin2`) commands shown only as fallback — flags differ slightly, plugins are not interchangeable.

## 1. Open read-only + analyze deliberately

```bash
rizin -e io.cache=true -A "$F"
# batch (preferred for LLM: JSON out, no interactiveloat):
rizin -q -A -c 'aflj' "$F" > "$CASE/artifacts/static/functions.json"
```

Analysis depths (`-A` = `aaa`, not max). Deeper is not better — it creates false functions in data. Check `aaa?` and escalate only if entry point has no function.

Interactive essentials:

```text
iI                # binary info
iS                # sections
ii                # imports
iE                # exports
izzz              # strings (raw too)
afl               # functions
s entry0          # seek entry
pdf               # disassemble function
pdc               # pseudo-decompile (built-in, lossy)
```

r2 equivalents: `izz` (r2) ≈ `izzz` (rizin); `rabin2 -Ij` ≈ `rz-bin -Ij`.

## 2. JSON-first batch (do this before reading asm)

```bash
rizin -q -A -c 'aflj' "$F" > "$CASE/artifacts/static/functions.json"
rizin -q -A -c 'izj'  "$F" > "$CASE/artifacts/static/rizin-strings.json"
rizin -q -A -c 'iij'  "$F" > "$CASE/artifacts/static/rizin-imports.json"
jq -r '.[] | [.offset,.size,.name] | @tsv' "$CASE/artifacts/static/functions.json" | sort -k2,2nr | head -n 30 | column -t | tee "$CASE/artifacts/static/top-functions.txt"
```

Prioritize: entry point → exports/`DllMain` → TLS callbacks → `.CRT$XCU` initializers → string xrefs → import callers → large branchy functions touching input/crypto/paths/sockets. Never read in address order.

## 3. Anchor navigation (string → xref → caller)

```text
izzz~password            # filter strings
s <string_vaddr>         # seek string
axt                      # xrefs to here
s <xref_addr>
pdf                      # containing function
```

Batch form:

```bash
rizin -q -A -c 'izzz~password' "$F"
rizin -q -A -c 'axt @ <addr>' "$F"
```

Same for imports:

```text
ii~connect
s sym.imp.connect
axt                      # callers; walk UP to app logic that builds args
```

The xref function is the start of a path, not necessarily the implementer. Follow callers until you find arg construction + return-value check.

## 4. Rename + comment (demonstrated behavior only)

```text
af                       # ensure function exists
afn parse_config         # rename current
CC validates header and dispatches record parsers @ 0x140001230
```

Rules: `build_request_headers` > `network_function`. Append `_likely` if provisional (`decode_record_likely`). Record why in `checklists/function-note-template.md`. Export for portability:

```bash
rizin -q -A -c 'afnj; CCj' "$F" > "$CASE/artifacts/static/names-comments.json"
```

Save project (`Ps <name>` — check `P?` for version syntax) + JSON export. Shell history is not preservation.

## 5. Types + decompiler skepticism

```text
afs?   # signature help
td?    # types help
pf?    # format-string data help
```

Fixing a prototype (`int parse_config(char *out, char *in, size_t len)`) often fixes decompilation. Record why each type was assigned.

Decompilers: `pdc` (built-in) / `pdg` (rz-ghidra, if installed). Check with `e cmd.pdc=?`. Decompiler output is lossy — verify signedness, bounds, struct offsets, and control flow in asm before reporting. If two engines disagree on boundaries, see `06-ghidra-headless.md`.
