#!/usr/bin/env bash
# triage.sh SAMPLE CASE_DIR — static triage, never executes. Failures logged, not hidden.
set -Eeuo pipefail
umask 077
[[ $# -eq 2 ]] || { echo "usage: $0 SAMPLE CASE_DIR" >&2; exit 64; }
sample=$(readlink -f -- "$1")
case_dir=$2
[[ -f "$sample" ]] || { echo "not a regular file: $sample" >&2; exit 66; }
mkdir -p "$case_dir"/{evidence,artifacts/triage,notes,scripts}
copy="$case_dir/evidence/original.bin"
if [[ ! -e "$copy" ]]; then
  cp --reflink=auto --preserve=mode,timestamps -- "$sample" "$copy"
  chmod 0444 "$copy"
fi
out="$case_dir/artifacts/triage"
log="$out/commands.log"
: > "$log"
run() {
  local name=$1; shift
  printf '$' >> "$log"; printf ' %q' "$@" >> "$log"; printf '\n' >> "$log"
  "$@" > "$out/$name.stdout" 2> "$out/$name.stderr" || {
    rc=$?; printf '%s\t%s\n' "$name" "$rc" >> "$out/failures.tsv"; return 0
  }
}
sha256sum "$copy" | tee "$case_dir/evidence/hashes.txt"
sha1sum "$copy" >> "$case_dir/evidence/hashes.txt"
run file file -k -- "$copy"
run head xxd -g 1 -l 512 -- "$copy"
run tail xxd -g 1 -s -512 -- "$copy"
run strings-ascii strings -a -n 5 -t x -- "$copy"
run strings-utf16le strings -a -n 5 -e l -t x -- "$copy"
BINTOOL=""
command -v rz-bin >/dev/null && BINTOOL="rz-bin"
[[ -z "$BINTOOL" ]] && command -v rabin2 >/dev/null && BINTOOL="rabin2"
if [[ -n "$BINTOOL" ]]; then
  run info "$BINTOOL" -Ij "$copy"
  run sections "$BINTOOL" -Sj "$copy"
  run imports "$BINTOOL" -ij "$copy"
  run exports "$BINTOOL" -Ej "$copy"
fi
command -v diec >/dev/null && run diec diec "$copy"
command -v floss >/dev/null && run floss floss -j "$copy"
command -v capa >/dev/null && run capa capa -j "$copy"
python3 "$(dirname "$0")/entropy.py" "$copy" > "$out/entropy.csv" 2> "$out/entropy.stderr" || true
find "$case_dir/evidence" "$case_dir/artifacts" -type f -print0 | sort -z | xargs -0 sha256sum > "$case_dir/artifacts/SHA256SUMS"
printf 'triage complete: %s\n' "$case_dir"
