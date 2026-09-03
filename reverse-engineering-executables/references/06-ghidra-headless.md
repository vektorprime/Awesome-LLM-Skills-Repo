# 06 — Headless Ghidra (Second Engine + Export)

Use when: function boundaries disputed, critical decompile looks wrong, loader misidentifies arch/base, indirect calls unclear, or report depends on one heuristic. Agreement between engines is support, not proof.

## 1. Import + analyze (Ghidra 10.3+/11.x)

```bash
GHIDRA_HOME=/opt/ghidra
PROJECT_DIR="$CASE/artifacts/static/ghidra-projects"
PROJECT_NAME=case001
mkdir -p "$PROJECT_DIR"
"$GHIDRA_HOME/support/analyzeHeadless" "$PROJECT_DIR" "$PROJECT_NAME" \
  -import "$F" -overwrite 2>&1 | tee "$CASE/artifacts/static/ghidra-import.log"
```

Source of truth is `analyzeHeadless -help` on the installed release — flags drift. Preserve stderr; fail loudly.

## 2. Export decompilation (headless script)

Save as `scripts/ExportFunctions.py`, add its dir via `-scriptPath`:

```python
#@category RE
from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor
import os
args = getScriptArgs()
if len(args) != 1:
    raise RuntimeError("usage: ExportFunctions.py OUTPUT_DIR")
out_dir = args[0]
os.makedirs(out_dir, exist_ok=True)
iface = DecompInterface()
iface.openProgram(currentProgram)
monitor = ConsoleTaskMonitor()
fm = currentProgram.getFunctionManager()
with open(os.path.join(out_dir, "functions.tsv"), "w") as index:
    index.write("entry\tname\tsize\tdecompiled\n")
    for func in fm.getFunctions(True):
        entry = str(func.getEntryPoint())
        name = func.getName()
        size = func.getBody().getNumAddresses()
        r = iface.decompileFunction(func, 60, monitor)
        ok = r.decompileCompleted()
        index.write("%s\t%s\t%s\t%s\n" % (entry, name, size, ok))
        if not ok:
            continue
        safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in name)
        with open(os.path.join(out_dir, "%s_%s.c" % (entry, safe)), "w") as fh:
            fh.write(str(r.getDecompiledFunction().getC()))
iface.dispose()
```

Run:

```bash
mkdir -p "$CASE/artifacts/static/ghidra-decompile"
"$GHIDRA_HOME/support/analyzeHeadless" "$PROJECT_DIR" "$PROJECT_NAME" \
  -process "original.bin" \
  -scriptPath "$CASE/scripts" \
  -postScript ExportFunctions.py "$CASE/artifacts/static/ghidra-decompile" \
  2>&1 | tee "$CASE/artifacts/static/ghidra-export.log"
```

If `-process original.bin` fails, list the project to learn the real program name — import renames spaces/case. Do not guess.

## 3. Verification rule

Before citing decompilation in a report:

1. Compare Rizin `pdf` vs Ghidra `.c` for the cited function. Note disagreements in function note.
2. Re-check critical arithmetic / sign / bounds / struct offsets in asm.
3. Confirm static VA → runtime VA math for PIE/ASLR (base + RVA), don't copy absolute addresses blindly.
