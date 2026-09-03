# Firmware Containers — Provenance, Layers, Partitions, U-Boot, DTB

"Firmware" is a family, not a format. Distinguish **update package** from
**raw flash dump** in the first paragraph of every report — they are rarely
interchangeable. Follow `checklists/firmware.md`.

## 1. Provenance and completeness

Record: vendor + exact model, HW revision, region/carrier variant, FW version
+ date, source/acquisition, package vs recovery vs full vs raw dump, dump
tool + command, flash chip + capacity, bus (SPI/NAND/NOR/eMMC/JTAG/
bootloader/vendor tool), OOB included?, read passes + hashes.

Hardware dumps: read at least twice before analysis:

```bash
sha256sum read-01.bin read-02.bin
cmp -l read-01.bin read-02.bin | head
```

Divergence ⇒ unstable reads, live-state change, ECC/OOB handling, wear, or
tool behavior. Resolve acquisition before format work.

## 2. Survey + layer ledger

Run `references/survey.md` first, then open `templates/layer-ledger.md`:

```markdown
| Layer | Parent | Parent off | Stored len | Raw len | ID | Transform | Integrity | SHA-256 |
| L0 | — | 0x0 | 0x800000 | — | vendor update | none | sig trailer | … |
| L1 | L0 | 0x400 | 0x7F0000 | 0x1000000 | payload | xz | SHA-256 in manifest | … |
```

Rule: every child has parent + offset + length + command + hash. A directory
named `_firmware.bin.extracted` is not a map.

Outer-form triage:

```bash
file -k firmware.bin
binwalk firmware.bin
xxd -g 1 -l 1024 firmware.bin
strings -a -n 5 -t x firmware.bin | head -n 200
7z l firmware.bin || true
```

Outers: ZIP/tar/CPIO/7z/CAB/vendor archive, uImage, FIT, Android
sparse/OTA, raw concatenation, UBI, vendor header+entries, signed
manifest+payloads, **delta update** (needs base version — stop if missing).

## 3. Recursive extraction without losing control

Scan first, extract second, reproduce manually third.

```bash
binwalk --help 2>&1 | head -n 30   # v2 vs v3 differ!
# v2: binwalk -Me -C out firmware.bin
# v3: binwalk --extract --matryoshka firmware.bin ; --carve keeps raws
binwalk firmware.bin | tee binwalk.txt
unblob --show-external-dependencies || true
unblob --report unblob-report.json -e extracted-unblob firmware.bin
```

Verified unblob facts: default output is `<input>_extract` unless `-e DIR` is
given; `--report PATH` writes JSON chunk metadata (offsets, handlers, gaps);
`-d` caps recursion (default 10). Review the JSON for unrecognized gaps.

Automation lies: false-positive sigs, missed proprietary headers, wrong
boundaries, variant compression/filesystems, dropped rebuild metadata. Use it
for leads; re-derive important layers with `scripts/carve.py` + explicit
offsets. Hash the tree with `scripts/tree_manifest.py` (JSONL, handles
weird filenames, flags symlinks/dev-nodes/FIFOs):

```bash
python3 scripts/tree_manifest.py extracted-root > root.manifest.jsonl
```

## 4. Partition tables and concatenated images

```bash
fdisk -l firmware.bin 2>&1 | tee fdisk.txt
sfdisk --dump firmware.bin 2>&1 | tee sfdisk.txt
parted -s firmware.bin unit B print 2>&1 | tee parted.txt
mmls firmware.bin 2>&1 | tee mmls.txt
```

Carve (byte-exact for tables; sector math for disks — record both):

```bash
scripts/carve.py firmware.bin partition-01.bin --offset 1048576 --length 8388608
# sector form: START=2048 COUNT=16384 SS=512 -> offset=START*SS length=COUNT*SS
```

Proprietary entry tables (`name/type, flash addr, file off, stored len, raw
len, flags, hash`): validate no past-EOF regions, no unintended overlaps,
one consistent base (file? section? header-end? decompressed? **flash VA**?),
names match embedded sigs, alignment fits container/flash geometry.

## 5. U-Boot legacy and FIT (verified syntax)

List (auto-detects type; `-T` forces):

```bash
dumpimage -l firmware.bin | tee dumpimage-list.txt
dumpimage -h 2>&1 | head -n 20   # confirm flags on YOUR build
mkimage -T list 2>&1 | head -n 30  # supported types
```

Extract (modern `dumpimage [-T type] [-p position] -o outfile image`;
older FIT guides show `-T flat_dt -i input -p N output` — both mean
position-N subimage to file):

```bash
dumpimage -p 0 -o subimage-0.bin firmware.bin
# FIT with explicit type:
dumpimage -T flat_dt -p 1 -o kernel.bin firmware.itb
sha256sum subimage-*.bin kernel.bin
```

FIT is device-tree-based: multiple kernels/ramdisks/FDTs/configs/hashes/
sigs. Record default config, per-config kernel+ramdisk+FDT refs, hash algos,
sig scope (image vs config), external-data flags, multi-variant packing.
Extraction success ≠ signature validity.

## 6. Device tree blobs

DTBs reveal boards, SoCs, memory, flash partitions, consoles, GPIOs, NICs,
MAC storage, bootargs.

```bash
dtc -h 2>&1 | head -n 10
dtc -I dtb -O dts -o board.dts board.dtb
dtc -I dts -O dtb -o board.roundtrip.dtb board.dts
grep -En 'compatible|model|partition@|reg =|bootargs|stdout-path|status =|mac-address|serial' board.dts
fdtdump board.dtb | head -n 60        # alternative viewer
fdtget board.dtb /chosen bootargs     # field query when supported
```

Round trips are rarely byte-identical (ordering/padding) — compare semantics.
`reg` needs parent `#address-cells`/`#size-cells`; never assume u32 pairs.
