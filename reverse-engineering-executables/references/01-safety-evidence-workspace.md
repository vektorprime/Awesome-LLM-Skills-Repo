# 01 — Safety, Evidence, Workspace

Read this first on every case. Do not skip to triage.

## 1. Authorization

Confirm before touching the sample:

- Written authorization to possess and analyze this exact sample.
- No upload to VirusTotal / public sandboxes unless owner explicitly approves.
- Privacy / export-control / license constraints checked.
- Scope: question to answer + explicit exclusions.

Log answers in `notes/decisions.md`. If authorization is ambiguous: stop.

## 2. Isolation standard

Disposable analysis VM:

- Known-good snapshot, revert after case (e.g. `clean-7`).
- No shared clipboard, shared folders, host mounts, host creds.
- No production network. Use host-only / simulated / disabled.
- Non-admin analysis account unless elevated privs are required for that observation.
- Time + command logging if auditability required.

Containers (`docker`, `chroot`, `firejail`, namespaces) are extra controls inside the VM, not a boundary for kernel-facing binaries.

## 3. Execution gate

Copy this into `notes/decisions.md` and fill all 5 before first run:

```markdown
- Q requiring exec:
- Observations (APIs/syscalls/files/net):
- Containment (VM/snapshot/net/user):
- Data reachable:
- Stop events (child proc / priv change / write outside scratch / debugger loss):
```

If static evidence answers the question, do not execute.

## 4. Evidence labels (use in every note/report)

- **Observed:** directly produced by command/trace/controlled experiment.
- **Inferred:** best explanation of multiple observations, not directly proven.
- **Unknown:** insufficient/conflicting/untested.

Confidence:

- **High:** 2+ independent strong sources, or demonstrated in controlled run.
- **Medium:** 1 strong source or several weak indicators.
- **Low:** plausible, heuristic-only, or untested.

Never write "encrypted/packed" on entropy alone. Never present import as executed behavior.

## 5. Case layout

```text
case-2026-001/
  evidence/original.bin  # read-only, never overwrite
  evidence/hashes.txt
  evidence/provenance.md
  artifacts/triage/ static/ dynamic/ memory/ extracted/
  scripts/
  notes/timeline.md hypotheses.md decisions.md triage-summary.md
  report/
  tool-versions.txt
```

Initialize (Linux; for Windows EXE triage from PS see `scripts/triage-exe.ps1`):

```bash
set -Eeuo pipefail
umask 077
CASE=case-2026-001
SAMPLE=/path/to/authorized/sample
mkdir -p "$CASE"/{evidence,artifacts/{triage,static,dynamic,memory,extracted},scripts,notes,report}
cp --reflink=auto --preserve=mode,timestamps -- "$SAMPLE" "$CASE/evidence/original.bin"
chmod 0444 "$CASE/evidence/original.bin"
sha256sum "$CASE/evidence/original.bin" | tee "$CASE/evidence/hashes.txt"
sha1sum "$CASE/evidence/original.bin" >> "$CASE/evidence/hashes.txt"
stat --printf='size=%s bytes\nmtime=%y\ninode=%i\n' "$CASE/evidence/original.bin" | tee "$CASE/artifacts/triage/stat.txt"
```

Work on copies under `artifacts/`. Hash every derived artifact and record parent:

```bash
sha256sum artifacts/extracted/* | tee -a artifacts/SHA256SUMS
echo "upx-unpacked.bin derived from evidence/original.bin via upx -d" >> artifacts/PROVENANCE.txt
```

## 6. Tool versions (pin for long cases)

```bash
{
  date --iso-8601=seconds
  uname -a
  file --version | head -n 1
  python3 --version
  rz-bin -v 2>/dev/null || rabin2 -v 2>/dev/null || echo "no rizin/radare2"
  rizin -v 2>/dev/null || r2 -v 2>/dev/null || true
  gdb --version | head -n 1
  capa --version 2>/dev/null || true
  floss --version 2>/dev/null || true
  yara --version 2>/dev/null || true
  diec --version 2>/dev/null || true
} | tee "$CASE/tool-versions.txt"
```

Heuristic output (DiE, capa, FLOSS) changes between releases — version is evidence.
