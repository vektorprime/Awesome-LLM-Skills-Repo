#@category RE
"""Ghidra headless export: decompile all functions to OUTPUT_DIR + functions.tsv."""
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
