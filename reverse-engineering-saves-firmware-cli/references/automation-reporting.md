# Automation, Playbooks, Reporting, Training, Command Reference

## 1. Reusable automation (scripts + Makefile)

`scripts/survey.sh FILE OUTDIR` gathers evidence (hashes, file, head/tail,
strings×3, binwalk/7z/fdisk when present) — it concludes nothing.
`scripts/carve.py` carves byte-exact with JSON provenance. Validate helpers:

```bash
bash -n scripts/survey.sh
python3 -m py_compile scripts/*.py
```

Minimal Makefile (never let `clean` touch evidence/samples/specs/notes):

```make
SAMPLE ?= evidence/originals/artifact.bin
SURVEY := artifacts/survey
.PHONY: all survey entropy test clean
all: survey entropy test
survey:
	bash scripts/survey.sh "$(SAMPLE)" "$(SURVEY)"
entropy:
	python3 scripts/window_entropy.py "$(SAMPLE)" --window 0x1000 > "$(SURVEY)/entropy.csv"
test:
	python3 -m pytest -q
clean:
	rm -rf artifacts/survey/*
```

`sample-matrix.csv` + `scripts/sample_matrix_fill.py` keep sizes/hashes honest
(stream hashes for GB firmware — edit the script's `read_bytes()` to stream).

## 2. Playbooks (with checklists)

- Saved game: context → layer classification → field recovery → integrity +
  bounded parser → document. Checklist: `checklists/saved-game.md`.
- Savestate: emulator/ROM capture → same-frame vs +N-frames → whole vs block
  compression → chunk dir + ROM ID + thumbnail + RAM → version matrix.
  Checklist: `checklists/savestate.md`.
- Firmware: model/HW/version + repeated reads → outer package + sig/manifest
  preservation → layer ledger → partitions/entries → U-Boot/FIT/DTB →
  userspace FS → metadata/certs/config inventory → hash-vs-trust split →
  4-layer version diff → code/hWN handoff by hash. Checklist:
  `checklists/firmware.md`.
- Final gate for every case: `checklists/final.md`.

Cheapest-decisive-test table:

| Question | Weak | Decisive |
|---|---|---|
| currency field? | stare at hex | values 1,2,255,256 + representation sweep |
| compressed? | entropy | carve + successful decompress |
| checksum? | one-sample match | multi-sample match + predicted post-edit value |
| absolute offset? | assume file base | test file/section/payload/flash-VA bases on all entries |
| filesystem? | scanner label | read-only format-aware listing + boundary validation |
| signed? | long trailer | structure + algo + key + canonical bytes + verify |
| RAM block? | size ≈ RAM | controlled in-game deltas at stable offsets |
| encrypted? | high entropy | compression/nonce/determinism elimination + key evidence |

## 3. Report + language + peer review

Template: `templates/report-template.md` (question/scope, authorization,
identity table, executive conclusion, layer map, spec, experiments,
integrity, ledger, version comparison, parser/tests, unknowns, reproduction,
recommendations).

Finding language — good cites offsets, range, samples, confidence:

```text
Observed: bytes 0x08–0x0B (u32le) equal stored payload length in 14/14 samples.
Inferred (Medium): 0x0C–0x0F are CRC-32/ISO-HDLC over compressed payload; match
12/12 and predict post-edit values. Trailer last-4 coverage untested.
Unknown: 16 B at 0x20 change every save (nonce? UUID? MAC?). No decisive test yet.
```

Weak: "The header contains length, hash, and encryption information."
Peer review: `checklists/peer-review.md` (scope, method, spec, parser,
conclusions). Escalate when: encrypted + no authorized key; keyed MAC/sig
blocks rebuild; NAND geometry unresolvable; vendor-modified FS needed; delta
base missing; reads disagree; cloud/HSM in the loop; code analysis required;
brick risk without recovery; legal/ownership unclear. Handoff package: hashes,
ledger, opaque range, I/O samples, confirmed transforms, key/nonce/tag
candidates, versions, ruled-out tests, one precise question.

## 4. Command reference

General: `file -k`, `stat`, `sha256sum`, `xxd -g 1 -l 512`, `tail -c 512 |
xxd -g 1`, `strings -a -n 4 -t x` (+ `-e l/b`), `binwalk`, `7z l`.
Carve/diff: `scripts/carve.py`, `cmp -l` (1-based dec + octal!), `radiff2`,
`xxd -s OFF -l LEN`. Structured: `jq -S .`, `xmllint --format`,
`sqlite3 … '.dbinfo/.tables/.schema'`, `protoc --decode_raw`.
Firmware: `fdisk -l`, `sfdisk --dump`, `mmls`, `dumpimage -l` /
`dumpimage -p N -o out img`, `dtc -I dtb -O dts`, `unsquashfs -s/-ll/-d`,
`ubireader_display_info/_extract_images/_extract_files`, `dumpe2fs -h`,
`e2fsck -fn`, `debugfs -R 'ls -l /'`, `fls -r -p`, `cramfsck -v`,
`simg2img`. Always recheck installed `-h/--help`.

## 5. Training (6-week intensive, daily hands-on)

Wk1 binary literacy + evidence (hex/endian/strings/alignment/hashing;
Observed/Inferred/Unknown). Lab: fixed header map + parser. Gate: no
off-by-ones, reproducible hashes, truncation rejected, no heuristic-as-fact.
Wk2 differential saves (matrix, stability, region/block diffs, varints,
CRC + coverage, minimal edit). Lab: TLV + CRC + unknown-preserving rebuild.
Gate: ≥5-sample validation, controlled reload, unrelated-state check.
Wk3 compression/serialization/savestates (whole vs block, normalization,
chunk map, RAM ID, thumbnails, compat). Gate: reproducible extraction,
semantic-vs-byte round-trip stated, compat tested.
Wk4 firmware containers + filesystems (ledger, partitions, U-Boot/FIT/DTB,
SquashFS/ext/FAT/CPIO, UBI, NAND geometry). Gate: every child has
offset+len+cmd+hash; no blind trust in automation; safe handling.
Wk5 integrity + diffing + automation (MAC/sig split, tree normalization,
4-layer diff, tests, hostile-input handling). Gate: checksum/hash/MAC/sig
distinguished; noise separated; automation fails safe.
Wk6 capstone: unfamiliar family, ≥2 versions, nested compression/FS, unknown
table, integrity metadata, controlled variants, one false lead. Outputs: scope
+ survey pack + layer map + spec + parser/tests + diff + risk notes + 30-min
briefing + peer review. Pass = peer reproduces from package alone.

Daily rhythm: 30′ review Q/evidence/unknowns · 60′ cheapest experiments · 60′
parser/spec · 30′ tests/preservation · 30′ write-up + confidence · 30′ peer
review. Labs 1–8 (fixed header, TLV+strings, compressed save, dual-slot
journal, savestate chunks, firmware container, offset-shifted UBI, version
diff) and the 0–4 rubric live in repo history; ask the maintainer if you need
the full lab pack.

## 6. Labs (summaries)

1. Fixed header (magic/version/hdrlen/timestamp/name[32]/currency/flags/CRC):
   10 controlled samples → map + parser + coverage + edit + truncation tests.
2. Variable records (header/count/TLV/string-table/offsets/checksum) with
   empty/duplicate/unknown-tag/UTF-8/corrupt-length cases; preserve unknowns.
3. Compressed save (hdr/comp-len/raw-len/zlib/payload-CRC/file-CRC), varied
   levels so recompression ≠ byte-identical.
4. Dual-slot journal (selector + A/B × generation/payload/CRC); recover newest
   valid after corruption.
5. Savestate (hdr/version/ROM-SHA1/dir + META/CPU0/RAM0/VRAM/THMB; per-block
   compressed RAM/VRAM + PNG): chunk extract + version compare + memory delta.
6. Firmware container (vendor hdr/manifest/entries/kernel/DTB/SquashFS/
   config/sig): ledger + entry parser + DTB round trip + FS manifest +
   hash verification.
7. UBI image with known geometry + one offset-prefixed copy: find true start,
   list volumes, extract files.
8. Two releases (repacked outer, 1 config change, 1 cert swap, +recovery
   partition, FS timestamp churn): semantic vs noise separation.
