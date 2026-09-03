# Filesystems & Raw Flash — SquashFS, UBI, JFFS2, ext, FAT, CPIO, Sparse, NAND

Prefer read-only userspace tools. Check installed `--help`/`-h` — releases
differ. Never run extracted code; review symlinks/dev-nodes before copying
trees elsewhere.

## 1. SquashFS (read-only rootfs staple)

```bash
unsquashfs -version 2>&1 | head -n 2   # lowercase -version is correct
unsquashfs -s rootfs.squashfs | tee squashfs-superblock.txt
unsquashfs -ll rootfs.squashfs > squashfs-list.txt
mkdir -p extracted-squashfs
unsquashfs -d extracted-squashfs rootfs.squashfs
```

Record: version, compressor (gzip/xz/lzo/zstd), block size, fragments,
exports, mtime, UID/GID mapping, symlinks/dev-nodes. Valid magic + failed
extract ⇒ unsupported compressor, vendor-modified metadata, truncation, or
wrong carve boundary — keep the error output, re-verify the boundary before
hunting patched tools (`sasquatch` variants cover many vendor forks).

## 2. UBI / UBIFS (layered — do not treat as block FS)

```text
raw flash / MTD -> UBI container + volumes -> UBIFS inside a volume
```

Verified `ubi_reader` (underscore) syntax:

```bash
ubireader_display_info image.ubi | tee ubi-info.txt
ubireader_display_info --help 2>&1 | head -n 30
ubireader_extract_images image.ubi      # whole UBI/UBIFS from NAND dump
ubireader_extract_images -u UBI image.ubi   # force type: UBI or UBIFS
ubireader_extract_files image.ubi       # files out of the volumes
```

Ask: image count, volume names/IDs, static vs dynamic, content per volume
(UBIFS? kernel? config? recovery?), erase-block alignment, OOB presence, bad
blocks. Extraction failure is often geometry (PEB/LEB/min-IO/offset), not
corruption — record every guessed/supplied parameter.

## 3. JFFS2 / CramFS / ext / FAT / CPIO

JFFS2 (check endianness, erase size, clean markers, OOB):

```bash
jffs2dump -c -v image.jffs2 > jffs2dump.txt 2>&1
jefferson image.jffs2 -d extracted-jffs2
```

CramFS:

```bash
cramfsck -v image.cramfs
mkdir -p extracted-cramfs
cramfsck -x extracted-cramfs image.cramfs
```

ext (read-only! never let repair touch evidence):

```bash
dumpe2fs -h image.ext 2>&1 | tee ext-superblock.txt
e2fsck -fn image.ext 2>&1 | tee ext-check.txt     # -n = no writes
debugfs -R 'ls -l /' image.ext 2>&1 | tee ext-root-list.txt
```

FAT:

```bash
fsstat image.fat > fat-fsstat.txt
fls -r -p image.fat > fat-files.txt
# extract single files with icat/mtools; keep source image pristine
```

CPIO (list names first; isolate destination):

```bash
cpio -itv < archive.cpio > cpio-list.txt
mkdir -p extracted-cpio
(cd extracted-cpio && cpio --no-absolute-filenames -idmv < ../archive.cpio)
```

`--no-absolute-filenames` blocks one traversal class, not all — isolation +
name review still required. tar: `bsdtar -tf` list, `7z x` or `tar` extract
into empty dir.

## 4. Android sparse

```bash
simg2img system.img system.raw.img
sha256sum system.img system.raw.img
file -k system.raw.img
```

Record sparse + expanded lengths. Sparse chunks (raw/fill/don't-care) are not
compression — then analyze the raw image as partition/filesystem.

## 5. Raw NAND: OOB, ECC, geometry (measure twice, strip once)

Properties: page data size, OOB/spare size, pages/block, erase-block size,
bad-block marker position, ECC algo/layout, OOB included-or-removed by the
tool, bad-block skip/pad/preserve policy.

Common strides: `[2048+64]`, `[4096+128]`, `[4096+256]`, `[8192+…]`. Never
strip presumed OOB until geometry is proven — keep both images + exact
command.

```bash
python3 scripts/nand_split.py raw-nand.bin 2048 64 data-only.bin oob-only.bin
# refuses non-divisible lengths; try several geometries, keep the one whose
# output shows coherent structure (magic at block starts, valid FS, sane entropy)
```

Bad-block markers (often first/second OOB byte ≠ `0xFF`), ECC bytes, and
`0xFF`-heavy erased blocks all live in OOB — inspect `oob-only.bin` with
`fill_runs.py` + `window_entropy.py` before discarding anything. UBI on NAND
needs PEB-aligned input; a stray prefix offset kills parsing (see Lab 7 in
`automation-reporting.md`).
