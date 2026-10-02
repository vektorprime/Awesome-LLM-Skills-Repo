# Firmware Repack & Modify — Rebuild Pipeline, Recompute Obligations, Safe Testing

The inverse of `firmware-containers.md`: take a mapped/extracted firmware
apart, change a layer, and rebuild each layer so the device (or an
emulator) accepts it. Every rebuild row goes into the layer ledger
(`templates/layer-ledger.md`) with the **repack tool + options + output
hash** — a rebuilt child without provenance is unreviewable.

**Scope gates:** lab/own devices/dev boards/CTF only. Never flash modified
firmware to production or other people's devices. Never bypass vendor
signature enforcement to make a device accept unsigned images — that bar is
in `firmware-analysis.md` §1 and it stays. Always have a **tested recovery
path** before flashing anything (see §5).

## 1. Rebuild map (per layer, matching tools)

Byte-identical rebuild is rarely possible and rarely needed — the real
constraints are: declared sizes/offsets in parent layers, flash geometry,
and manifest hashes. Aim for **semantic round trip** first
(`compression-crypto-integrity.md` §1): rebuild → parses → boots/loads.

| Layer | Rebuild | Match-the-original options |
|---|---|---|
| SquashFS rootfs | `mksquashfs tree out.sqfs` | read `unsquashfs -s` first: `-comp X -b SIZE -all-root` or `-uid/-gid` maps, `-no-xattrs` vs xattrs, `-mkfs-time`, `-all-time` to normalize timestamps |
| UBIFS volume | `mkfs.ubifs` then `ubinize` | `-m <min-io> -e <leb> -c <max-leb>` from `ubireader_display_info`; volume ini (vol_id/vol_type/vol_size) from the volume table |
| FIT image (.itb) | `mkimage -f image.its out.itb` | ITS from `dumpimage -l`; `hash@` nodes auto-recomputed by mkimage; `data@` external or embedded to match `external-data` |
| legacy uImage | `mkimage -A arch -O os -T type -C comp -a addr -e entry -d data` | arch/os/type/comp/addrs/entry from `dumpimage -l` (0x27051956 header) |
| DTB | `dtc -I dts -O dtb` | keep the decompiled `.dts` unmodified besides intent; compare `fdtdump` output, not bytes |
| CPIO | `find tree \| cpio -H newc -o` | `-H newc` (magic "070701"); `--owner root:root`; **order matters** — build from a sorted manifest, device nodes via `mknod` first |
| partition image | plain carve-in-place | same offset, size ≤ partition, erase-block-aligned padding (`0xFF`) |
| outer container | vendor-format dependent | entry table lengths/hashes recomputed (below) |

Pin tool versions (`tool-versions.txt`): repack output differs across
squashfs-tools / u-boot releases even with identical options.

## 2. Recompute obligations (what breaks when a child changes)

Work **inside-out**; after each child, recompute every parent obligation:

1. **Lengths**: parent entry `stored_len`/`raw_len` (and any derived
   end-offset if the format stores `start+len` chains). A size change that
   exceeds the partition requires a partition-table change (§3).
2. **Hashes**: manifest/hash-table entries over the child (L1/L2 in
   `firmware-analysis.md` §1). Recompute with the exact algorithm + range
   the manifest itself uses (the `checksum_candidates.py` discipline —
   match, then predict, on the rebuilt bytes).
3. **Signatures**: recomputation is impossible without the signing key —
   a rebuild invalidates them (expected on lab devices; **stock boot chains
   that verify signatures will refuse the image** — that is the hard stop,
   not a puzzle). Say so in the ledger instead of shipping an
   unbootable image.
4. **Compression stream properties**: if the parent stores `comp_len`, the
   recompressed length must be re-derived from **your** compressor's output
   (not the original's) — `compression-...` §1 round-trip rules.
5. **Offsets**: resized children shift following entries; recompute
   position fields and every entry-table checksum range that includes
   them.
6. **Cross-references**: DTB `phandle` targets, bootargs `root=` device
   ids, partition labels, kernel cmdline matching DTB/`/chosen` — a
   renamed/renumbered partition breaks the boot chain *without* any
   corruption error. Diff the DTS (`grep -n 'phandle\|label\|aliases'`)
   before/after.
7. **Flash geometry**: children must stay erase-block/page-aligned in the
   raw image; padding is `0xFF` (NOR/NAND erased state), not `0x00`
   (`survey.md` §5 fill-runs say which the target uses).

## 3. Partition resize discipline (only when unavoidable)

1. Resize in whole **erase blocks** (`nand_split.py` geometry first).
2. Never move a partition another layer addresses by absolute offset
   unless you recompute that reference (§2.6).
3. Keep `boot`/`recovery`/`recovery-stock` untouched — they are your
   recovery path (§5).
4. Update: partition table (or manifest partition list) + entry sizes +
   hashes + any loader-side size field (`firmware-analysis.md` §2 sources).

## 4. Verify before it goes near hardware

```bash
# 1. structural: your own parser (parser-spec.md) accepts the rebuilt image
# 2. layer ledger complete: every child has parent+offset+len+cmd+hash
python3 scripts/tree_manifest.py rebuilt-root > rebuilt.manifest.jsonl
diff -u original.manifest.jsonl rebuilt.manifest.jsonl > tree.diff
# 3. semantic diff at the right layer (automation-reporting.md L3/L4):
#    report content changes, not recompression noise
# 4. emulator first (§5.1)
```

## 5. Testing safety ladder (never skip rungs)

1. **QEMU with the extracted pieces** — fastest, zero brick risk:
   `qemu-system-<arch> -M <machine-from-DTB> -kernel extracted-kernel
   -dtb extracted.dtb -drive format=raw,file=rebuilt-rootfs-attached-appropriately`
   Match the machine type from the DTB `compatible` strings; document the
   exact invocation + outputs in the case dir.
2. **Lab device with external recovery** (serial console wired, flash
   programmer + a saved known-good full dump — the `evidence/originals`
   read-only copy **is** the last-resort recovery source; never let any
   step overwrite it).
3. **A/B or recovery-slot device** — boot the modified slot with the
   fallback intact; rollback verified before a second flash.
4. Vendor recovery/update mode that re-flashes stock.
5. If no rung is available: **stop**. "It probably boots" is not a recovery
   path (`automation-reporting.md` escalation: brick risk).

Every flash attempt goes in the experiment log: tool + exact command +
image hash + result + rollback used.

## 6. Common repack failures (symptom → cause)

| Symptom | Usual cause |
|---|---|
| Stock bootloader rejects the image | signature invalidated by rebuild (§2.3) — expected, hard stop on production |
| Bootloader loads then kernel panics on rootfs | DTB `root=`/partition label mismatch (§2.6) |
| Kernel boots, rootfs mount fails | SquashFS compressor/block options differ (§1); partition offset/size fields stale (§2.1) |
| UBI attach fails | geometry mismatch (min-IO/LEB, OOB presence — `filesystems-flash.md` §5); PEB misalignment from an offset-shifted copy |
| Loads, config missing | CPIO order/permissions lost, xattrs/SELinux labels dropped (unsquashfs loses them; use a tar round-trip preserving xattrs) |
| Works in QEMU, bricks on device | machine-specific: board quirks in vendor container fields, MAC/calibration partition untouched mismatch, watchdog expectation |
| "Checksum error" on boot | manifest hash range covers old lengths (§2.2), not recomputed over your bytes |
