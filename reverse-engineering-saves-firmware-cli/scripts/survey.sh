#!/usr/bin/env bash
# survey.sh — non-destructive first survey. Gathers evidence, concludes nothing.
# Usage: bash scripts/survey.sh <FILE> <OUTPUT_DIR>
set -Eeuo pipefail
umask 077

usage() { echo "usage: $0 FILE OUTPUT_DIR" >&2; exit 2; }
[[ $# -eq 2 ]] || usage
file_path=$1
out=$2
[[ -f "$file_path" ]] || { echo "not a regular file: $file_path" >&2; exit 1; }
mkdir -p "$out"

sha256sum -- "$file_path" > "$out/sha256.txt"
stat --printf='path=%n\nsize=%s\nmtime=%y\nmode=%a\n' -- "$file_path" > "$out/stat.txt" 2>/dev/null \
  || stat -f 'path=%N\nsize=%z\nmtime=%Sm\nmode=%p\n' -- "$file_path" > "$out/stat.txt"
file -k -- "$file_path" > "$out/file.txt"
xxd -g 1 -l 4096 "$file_path" > "$out/head-4096.txt"
tail -c 4096 -- "$file_path" | xxd -g 1 > "$out/tail-4096.txt"
strings -a -n 4 -t x -- "$file_path" > "$out/strings-ascii.txt"
strings -a -n 4 -e l -t x -- "$file_path" > "$out/strings-utf16le.txt"
strings -a -n 4 -e b -t x -- "$file_path" > "$out/strings-utf16be.txt"

if command -v binwalk >/dev/null 2>&1; then
  binwalk "$file_path" > "$out/binwalk.txt" 2>&1 || true
fi
if command -v 7z >/dev/null 2>&1; then
  7z l "$file_path" > "$out/7z-list.txt" 2>&1 || true
fi
if command -v fdisk >/dev/null 2>&1; then
  fdisk -l "$file_path" > "$out/fdisk.txt" 2>&1 || true
fi

printf 'survey complete: %s\n' "$out"
