#!/usr/bin/env python3
"""Windowed Shannon entropy map: python3 entropy.py FILE [window] -> CSV offset,size,entropy."""
import math
import pathlib
import sys
from collections import Counter

path = pathlib.Path(sys.argv[1])
window = int(sys.argv[2]) if len(sys.argv) > 2 else 4096
data = path.read_bytes()
print("offset,size,entropy")
for off in range(0, len(data), window):
    block = data[off:off + window]
    if not block:
        break
    n = len(block)
    counts = Counter(block)
    ent = -sum((c / n) * math.log2(c / n) for c in counts.values())
    print(f"0x{off:08x},{n},{ent:.5f}")
