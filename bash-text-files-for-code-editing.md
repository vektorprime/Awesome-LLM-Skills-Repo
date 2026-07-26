---
name: bash-cli-text-editing
description: Use when working with text-based files on Linux bash CLI
---

# Working with Text Files on the Bash CLI (Linux)
## A Precision Guide for Editing Code Files

A comprehensive guide that starts with the fundamentals and builds toward advanced, surgical text manipulation — with a focus on editing source code safely and precisely.

---

## Table of Contents

1. [Core Concepts](#1-core-concepts)
2. [Viewing and Reading Files](#2-viewing-and-reading-files)
3. [Creating and Modifying Files](#3-creating-and-modifying-files)
4. [Redirection and Pipes](#4-redirection-and-pipes)
5. [Searching with `grep`](#5-searching-with-grep)
6. [Measuring and Selecting Text](#6-measuring-and-selecting-text)
7. [Sorting, Deduplicating, and Comparing](#7-sorting-deduplicating-and-comparing)
8. [Transforming Text with `tr`, `cut`, `paste`, `join`](#8-transforming-text)
9. [Stream Editing with `sed`](#9-stream-editing-with-sed)
10. [Pattern Scanning with `awk`](#10-pattern-scanning-with-awk)
11. [Finding Files and Acting on Them](#11-finding-files-and-acting-on-them)
12. [Chaining Commands Together](#12-chaining-commands-together)
13. [Advanced Techniques](#13-advanced-techniques)
14. [Precision Code Editing Workflows](#14-precision-code-editing-workflows)
15. [Practical Recipes](#15-practical-recipes)
16. [Quick Reference Cheat Sheet](#16-quick-reference-cheat-sheet)

---

## 1. Core Concepts

Before diving into commands, understand the ideas that everything else builds on.

### Everything is a stream
On Linux, text tools read from **standard input (stdin)**, write to **standard output (stdout)**, and send errors to **standard error (stderr)**. Most commands can read from a file *or* from a stream, which is what makes them composable.

| Stream | File descriptor | Default destination |
|--------|-----------------|---------------------|
| stdin  | 0               | keyboard            |
| stdout | 1               | terminal            |
| stderr | 2               | terminal            |

### The Unix philosophy
Unix tools are designed to **do one thing well** and to **work together**. You rarely need one monolithic command — you build pipelines of small, focused tools. For code editing, this means you can isolate a transformation (rename a symbol, reindent a block, strip a comment style) into a single, testable step.

### Precision mindset
When editing code, small mistakes break builds. Adopt these habits:

- **Preview before you commit.** Run every destructive command *without* its in-place flag first and inspect the output.
- **Version control is your safety net.** Make sure files are committed (or at least backed up) before mass edits. `git diff` afterward is your verification step.
- **Anchor your patterns.** A regex like `id` matches `id`, `width`, `identifier`, and `android`. Use word boundaries (`\b`), line anchors (`^`, `$`), and surrounding context to target exactly what you mean.
- **Quote everything.** Unquoted variables and patterns are subject to word-splitting and glob expansion, which corrupts code.

### A note on shells and variants
- This guide assumes **bash**. Most examples also work in `zsh`.
- `sed` examples use **GNU sed** syntax (standard on Linux). BSD/macOS sed differs (e.g., `sed -i ''` vs `sed -i`).
- `awk` examples use POSIX features; GNU `awk` (`gawk`) adds extras like `gensub()` and `asort()`.
- `grep` examples occasionally use `-P` (Perl-compatible regex), a GNU extension.

---

## 2. Viewing and Reading Files

### `cat` — concatenate and print
Prints the entire file to stdout.

```bash
cat file.txt              # print whole file
cat a.txt b.txt           # print multiple files in sequence
cat -n file.txt           # number all lines
cat -b file.txt           # number non-blank lines only
cat -A file.txt           # show tabs (^I), line ends ($), and non-printing chars
cat -s file.txt           # squeeze multiple blank lines into one
cat file1.txt file2.txt > combined.txt   # combine files
```

`cat -A` is invaluable when debugging code: it reveals hidden characters like trailing whitespace, tabs vs. spaces, and CRLF (`^M$`) line endings that can break builds or diffs.

> **Tip:** `cat` is great for short files. For long source files, use a pager.

### `less` — page through content
Opens an interactive viewer. Unlike the older `more`, you can scroll backward and search.

```bash
less file.txt
less -N file.txt          # show line numbers
less -S file.txt          # chop long lines (no wrap)
```

Useful keys inside `less`:
- `/pattern` — search forward, `?pattern` — search backward
- `n` / `N` — next / previous match
- `g` / `G` — jump to start / end
- `:123` — jump to line 123
- `-S` (type at the `:` prompt) — toggle line chopping
- `-N` — toggle line numbers
- `&pattern` — display only matching lines (filter view)
- `q` — quit

### `head` and `tail` — the beginning and end
```bash
head file.txt             # first 10 lines (default)
head -n 20 file.txt       # first 20 lines
head -c 100 file.txt      # first 100 bytes

tail file.txt             # last 10 lines
tail -n 5 file.txt        # last 5 lines
tail -f /var/log/syslog   # "follow" — show new lines as they're appended
tail -n +15 file.txt      # start at line 15 and print to the end
```

Code-editing uses:
```bash
head -n 1 main.py                 # inspect the shebang line
tail -n 1 data.csv                # check the last record
sed -n '40,60p' source.c          # view a specific line range (see sed section)
```

`tail -f` is indispensable for watching build logs or test output in real time. Use `Ctrl-C` to stop following.

---

## 3. Creating and Modifying Files

### Creating files
```bash
touch newfile.txt                 # create empty file (or update timestamp)
echo "hello world" > file.txt     # write a line (overwrites)
echo "another line" >> file.txt   # append a line
printf "Name: %s\nAge: %d\n" "Ada" 36 > info.txt   # formatted output
```

`printf` gives precise control over formatting and does **not** add a trailing newline unless you include `\n`. This matters when generating code:

```bash
printf '#include "%s"\n' "config.h" > header.inc
```

### Here-documents and here-strings
A **here-document** feeds a block of text to a command — perfect for scaffolding code:

```bash
cat > main.c <<'EOF'
#include <stdio.h>

int main(void) {
    printf("Hello, world\n");
    return 0;
}
EOF
```

> **Quoting the delimiter** (`<<'EOF'`) prevents variable and command expansion inside the block. Use unquoted `<<EOF` when you *want* `$VAR` and `$(cmd)` to expand.

A **here-string** feeds a single string:

```bash
grep "port" <<< "server=localhost
port=8080"
```

### Reading files in a loop
```bash
while IFS= read -r line; do
    echo "Processing: $line"
done < input.txt
```

- `IFS=` preserves leading/trailing whitespace (critical for indented code).
- `-r` prevents backslash interpretation (critical for C/regex code with `\n`, `\t`).
- This is the idiomatic, safe way to process a file line by line.

Example — prefix every function name in a list:
```bash
while IFS= read -r func; do
    echo "extern void ${func}(void);"
done < functions.txt > declarations.h
```

---

## 4. Redirection and Pipes

Redirection is the glue of the command line.

### Output redirection
```bash
command > file        # write stdout to file (overwrite)
command >> file       # append stdout to file
command 2> errors     # write stderr to file
command 2>&1          # merge stderr into stdout
command &> all.log    # bash shorthand: both stdout and stderr to file
command > /dev/null   # discard stdout
command > /dev/null 2>&1   # discard everything
```

### Input redirection
```bash
command < file        # feed file as stdin
```

### Pipes
A pipe `|` connects the stdout of one command to the stdin of the next:

```bash
grep "error" build.log | grep -v "warning" | wc -l
```

> **Anti-pattern note:** `cat file | grep x` works, but `grep x file` is simpler and faster. Using `cat` unnecessarily is called "Useless Use of Cat" (UUOC). Pipes shine when you're genuinely chaining transformations.

### Why this matters for code editing
Pipelines let you build a transformation in **inspectable stages**. Instead of trusting one complex in-place edit, you can run each stage, eyeball the output, and only write to the file when you're satisfied:

```bash
# Stage 1: preview
grep -n "old_function" *.c
# Stage 2: transform to stdout and review
sed 's/old_function/new_function/g' main.c
# Stage 3: commit
sed -i 's/old_function/new_function/g' main.c
```

---

## 5. Searching with `grep`

`grep` filters lines matching a pattern. For code work, it's your primary tool for locating symbols, usages, and patterns before you edit them.

### Basics
```bash
grep "error" file.txt           # lines containing "error"
grep -i "error" file.txt        # case-insensitive
grep -r "TODO" ./src            # recursive search in a directory
grep -rn "TODO" ./src           # recursive + show line numbers
grep -w "cat" file.txt          # match whole word only
grep -v "debug" file.txt        # invert: lines NOT matching
grep -c "error" file.txt        # count matching lines
grep -l "main" *.c              # list filenames containing a match
grep -L "copyright" *.c         # list files WITHOUT a match
grep -E "err(or|ors)" file.txt  # extended regex
grep -P '\bint\b' file.c        # Perl regex with word boundary
```

### Context control — essential for code
Code is structured; you usually need surrounding lines to understand a match.

```bash
grep -A 3 "Exception" log.txt   # show 3 lines After each match
grep -B 2 "Exception" log.txt   # show 2 lines Before
grep -C 2 "Exception" log.txt   # show 2 lines of Context around
grep -n -A 5 "def parse" app.py # find a function def + its first 5 lines
```

### Regular expressions (quick reference)
```
.        any single character
*        zero or more of the preceding
+        one or more (use -E or \+)
?        zero or one (use -E or \?)
^        start of line
$        end of line
[abc]    any one of a, b, c
[a-z]    range
[^abc]   any character NOT in the set
\b       word boundary (GNU/Perl)
\        escape a special character
```

### Code-specific search patterns
```bash
grep -rn "^def " *.py                 # all top-level Python function defs
grep -rn "^\s*def " *.py              # all function defs, any indentation
grep -En '^\s*(public|private)\s' *.java   # methods with access modifiers
grep -rn "\bmalloc\b" *.c             # exact symbol "malloc", not "mallocx"
grep -En '#include\s*[<"]' *.c        # all include directives
grep -rn "FIXME\|TODO\|XXX\|HACK" .   # all common code markers
grep -Pn '(?<=\()(\d+)(?=\))' f.c     # numbers inside parentheses (lookaround)
```

### Combining patterns
```bash
grep -E "error|warning|fatal" log.txt   # any of these (OR)
grep "error" log.txt | grep -v "test"   # errors, but exclude "test"
grep -rn "import" . | grep -v "node_modules"   # skip a directory's noise
```

### Excluding paths (cleaner than piping)
```bash
grep -rn "config" --include="*.py" .
grep -rn "config" --exclude-dir={.git,node_modules,venv} .
```

> **Tip:** For large codebases, consider `ripgrep` (`rg`) or `ack`, which respect `.gitignore` and are far faster. The syntax above transfers directly to `rg` in most cases.

---

## 6. Measuring and Selecting Text

### `wc` — word, line, byte counts
```bash
wc file.txt          # lines, words, bytes
wc -l file.txt       # line count only
wc -w file.txt       # word count
wc -c file.txt       # byte count
wc -m file.txt       # character count (multibyte-aware)
wc -L file.txt       # length of the longest line (GNU)
ls *.c | wc -l       # count files (one per line)
```

Code uses:
```bash
wc -l *.c *.h                 # lines of code per file
find . -name "*.py" -exec wc -l {} +   # total across a tree
wc -L source.c                # find overly long lines to refactor
```

### `cut` — extract columns/fields
```bash
cut -d: -f1 /etc/passwd          # first field, delimiter ":"
cut -d' ' -f1,3 data.txt         # fields 1 and 3, space-delimited
cut -d',' -f2- report.csv        # field 2 to the end
cut -c1-10 file.txt              # characters 1 through 10
cut -c5- file.txt                # from character 5 to end of line
```

Code uses:
```bash
# Extract just filenames from "file:line:match" grep output
grep -rn "bug" . | cut -d: -f1 | sort -u

# Strip line numbers from `cat -n` output
cat -n file.c | cut -c9-
```

> **Limitation:** `cut` treats consecutive delimiters literally, so it struggles with irregular whitespace (common in code). For that, use `awk`, which splits on runs of whitespace by default.

---

## 7. Sorting, Deduplicating, and Comparing

### `sort`
```bash
sort file.txt                 # alphabetical sort
sort -r file.txt              # reverse
sort -n numbers.txt           # numeric sort
sort -k2 data.txt             # sort by 2nd field
sort -t, -k3 -n report.csv    # comma-delimited, numeric sort on field 3
sort -u file.txt              # sort and remove duplicates
sort -f file.txt              # case-insensitive (fold case)
sort -k1,1 -k2,2n data.txt    # sort by field 1, then field 2 numerically
sort -V versions.txt          # "version" sort (1.2 < 1.10)
```

### `uniq` — filter adjacent duplicate lines
`uniq` only removes **consecutive** duplicates, so it's almost always paired with `sort`.

```bash
sort file.txt | uniq          # remove duplicate lines
sort file.txt | uniq -c       # count occurrences of each line
sort file.txt | uniq -d       # show only duplicated lines
sort file.txt | uniq -u       # show only unique (non-repeated) lines
```

Code uses — find duplicated symbols or includes:
```bash
grep -h "#include" *.c | sort | uniq -c | sort -rn   # most-used headers
grep -rho '\b[a-z_]\{4,\}\b' *.c | sort | uniq -c | sort -rn | head  # frequent identifiers
```

### `diff` and `comm` — comparing files
```bash
diff file1.txt file2.txt        # line-by-line differences
diff -u file1.txt file2.txt     # unified diff (patch-friendly)
diff -y file1.txt file2.txt     # side-by-side
diff -r dir1 dir2               # compare directories recursively
diff -w file1.txt file2.txt     # ignore whitespace differences
diff -B file1.txt file2.txt     # ignore blank-line differences
diff -u -w -B old.c new.c       # compare code, ignoring formatting noise

comm file1.txt file2.txt        # three columns: only-in-1, only-in-2, both
comm -12 file1.txt file2.txt    # lines common to both (suppress cols 1 & 2)
```

> `comm` requires **sorted** input.

`diff -u` output is the basis of patches:
```bash
diff -u old.c new.c > fix.patch
patch old.c < fix.patch          # apply the patch
```

---

## 8. Transforming Text

### `tr` — translate/delete characters
`tr` works on characters, not lines, and reads from stdin.

```bash
echo "Hello" | tr 'a-z' 'A-Z'        # HELLO  (uppercase)
tr -d '\r' < win.c > unix.c          # delete carriage returns (fix CRLF)
tr -s ' ' < file.txt                 # squeeze repeated spaces
tr ',' '\t' < data.csv               # commas to tabs
tr -cd '0-9\n' < file.txt            # keep only digits and newlines
tr -d '[:blank:]' < file.txt         # remove all spaces and tabs
```

Code uses:
```bash
# Normalize a whole tree of files from Windows to Unix line endings
find . -name "*.c" -exec sh -c 'tr -d "\r" < "$1" > tmp && mv tmp "$1"' _ {} \;

# Turn a space-separated list into one symbol per line
echo "int float char" | tr ' ' '\n'
```

### `paste` — merge files side by side
```bash
paste file1.txt file2.txt            # join lines with a tab
paste -d',' file1.txt file2.txt      # join with a comma
paste -sd',' file.txt                # serialize: one line, comma-separated
```

Code use — build a comma-separated enum list from one-symbol-per-line:
```bash
paste -sd', ' symbols.txt
```

### `join` — relational join on a field
Like a SQL join for sorted text files.

```bash
# defs.txt:  name:type      values.txt:  name:value
join -t: defs.txt values.txt         # inner join on first field
```
Both files must be sorted on the join field.

### `column` — align into columns
```bash
column -t -s, data.csv               # pretty-print a CSV as aligned columns
grep "=" config.ini | column -t -s=  # align key=value pairs
```

---

## 9. Stream Editing with `sed`

`sed` is a non-interactive stream editor and the workhorse of precise code edits. It processes text line by line, applying commands to lines that match an address or pattern.

### The golden rule: preview first
Always run a substitution **without** `-i` and inspect stdout before touching the file:

```bash
sed 's/old/new/g' main.c        # 1. preview
git diff                         # (if you used -i) or compare manually
sed -i 's/old/new/g' main.c     # 2. commit only when satisfied
```

### Basic substitution
```bash
sed 's/old/new/' file.txt          # replace first occurrence on each line
sed 's/old/new/g' file.txt         # replace all occurrences (global)
sed 's/old/new/gi' file.txt        # global + case-insensitive (GNU)
sed -i 's/old/new/g' file.txt      # edit file in place (GNU sed)
sed -i.bak 's/old/new/g' file.txt  # in place, keeping a .bak backup
```

### Using different delimiters
Code is full of `/` (paths, regex, comments). Use another delimiter to avoid escaping:

```bash
sed 's|/usr/local|/opt|g' config          # | as delimiter
sed 's#http://old#https://new#g' urls.txt # # as delimiter
```

### Capture groups — restructure, don't just replace
Parentheses capture parts of the match; `\1`, `\2` reference them. This is the key to *restructuring* code, not just renaming.

```bash
# Swap "first last" to "last, first"
sed -E 's/(\w+) (\w+)/\2, \1/' names.txt

# Convert printf("%d", x) style arg order — wrap a value in a macro
sed -E 's/return ([a-z_]+);/return CHECK(\1);/' funcs.c

# Turn "int x = 5;" into "x = 5;" (strip the type)
sed -E 's/^\s*(int|float|char) ([a-z_]+) =/\2 =/' decls.c

# Convert snake_case function calls to camelCase (simple two-word case)
sed -E 's/\b([a-z]+)_([a-z]+)\b/\1\U\2/g' code.c
```

> `-E` enables extended regex so you can use `()` and `+` without backslashes. GNU sed also accepts `-r`.

### Addressing — act on specific lines or ranges
This is where precision comes from. You can restrict any command to exact lines, ranges, or pattern matches.

```bash
sed '3d' file.txt                  # delete line 3
sed '2,5d' file.txt                # delete lines 2 through 5
sed '$d' file.txt                  # delete the last line
sed '/^#/d' file.txt               # delete comment lines (starting with #)
sed '/^\s*$/d' file.txt            # delete blank/whitespace-only lines
sed -n '10,20p' file.txt           # print only lines 10–20 (-n suppresses default)
sed -n '/BEGIN/,/END/p' file.txt   # print block between markers (inclusive)
sed '5a\    inserted after line 5' f   # append a line after line 5
sed '5i\    inserted before line 5' f  # insert a line before line 5
sed '3c\replacement line' f        # change (replace) line 3 entirely
sed '/pattern/s/old/new/g' f       # substitute ONLY on lines matching "pattern"
sed '1,10 s/old/new/g' f           # substitute only within lines 1–10
```

The last form — **address + substitution** — is the precision tool. It limits a risky global replace to a safe scope:

```bash
# Rename "count" to "total" but only inside the validate() function region
sed '/^void validate/,/^}/ s/\bcount\b/total/g' module.c
```

### Multiple operations
```bash
sed -e 's/foo/bar/g' -e 's/baz/qux/g' file.txt
# or with a script file for complex edits
sed -f cleanup.sed file.c
```

Example `cleanup.sed`:
```sed
# Remove trailing whitespace
s/[[:space:]]*$//
# Convert tabs to 4 spaces
s/\t/    /g
# Delete debug print lines
/^\s*DEBUG_PRINT/d
```

### Useful code one-liners
```bash
sed '/^$/d' file.c                     # delete blank lines
sed 's/[[:space:]]*$//' file.c         # strip trailing whitespace
sed -n '/START/,/END/p' file.c         # extract a marked block
sed 's/^/    /' block.c                # indent every line by 4 spaces
sed 's/^    //' block.c                # de-indent by 4 spaces
sed 's|//.*$||' file.c                 # strip C++ line comments (naive)
sed -n '/^int main/,/^}/p' file.c      # print the main() function body
sed 's/\r$//' win.c                    # remove CR (CRLF -> LF)
sed '1i\/* AUTO-GENERATED — DO NOT EDIT */' out.c   # add a header comment
```

### Multi-line awareness (advanced)
`sed` is line-oriented, but you can pull in the next line with `N` to handle two-line patterns:

```bash
# Join a function call split across two lines: "foo(\n  bar)" -> "foo(bar)"
sed -E ':a; N; s/\(\s*\n\s*/(/; ta' code.c
```

For genuinely multi-line structural edits, `awk` or a real parser is usually safer (see below).

---

## 10. Pattern Scanning with `awk`

`awk` is a full programming language for field-oriented text processing. It automatically splits each line into fields `$1, $2, ...` with `$0` being the whole line. It excels at code tasks that need logic, counters, and state — things `sed` handles awkwardly.

### Basics
```bash
awk '{print $1}' file.txt              # print first field
awk '{print $1, $3}' file.txt          # print fields 1 and 3
awk -F: '{print $1}' /etc/passwd       # set field separator to ":"
awk '{print NR": "$0}' file.txt        # prefix line numbers (NR = record number)
awk '{print NF}' file.txt              # print number of fields per line
awk 'length($0) > 80' file.txt         # lines longer than 80 chars
```

### Filtering with patterns
```bash
awk '$3 > 100' data.txt                # rows where field 3 > 100
awk '/error/ {print $2}' log.txt       # field 2 of lines matching "error"
awk 'NR>=10 && NR<=20' file.txt        # lines 10 through 20
awk '$1 ~ /^A/' file.txt               # field 1 starts with "A" (regex match)
awk '/^{/ {print NR": "$0}' file.c     # line numbers of opening braces
```

### Arithmetic and aggregation
```bash
awk '{sum += $1} END {print sum}' nums.txt          # sum of field 1
awk '{sum += $1; n++} END {print sum/n}' nums.txt   # average
awk '{print $1, $2 * $3}' sales.txt                 # computed column
```

### Stateful editing — awk's superpower for code
Because awk keeps variables across lines, it can toggle behavior based on context:

```bash
# Comment out an entire function body (from "void foo" to its closing brace)
awk '
  /^void target_func/ {skip=1}
  skip {print "// " $0}
  skip && /^}/        {skip=0}
  !skip {print}
' module.c

# Delete everything between two markers
awk '/<REMOVE>/{f=1; next} /<\/REMOVE>/{f=0} !f' config.xml

# Number only non-blank, non-comment lines (like a compiler sees)
awk '!/^\s*#/ && !/^\s*$/ {n++; print n": "$0; next} {print}' script.sh
```

### Built-in variables
| Variable | Meaning |
|----------|---------|
| `NR`     | current record (line) number |
| `NF`     | number of fields in current record |
| `FS`     | input field separator |
| `OFS`    | output field separator |
| `RS`     | record separator |
| `$0`     | entire record |
| `$1..$n` | individual fields |

### BEGIN and END blocks
```bash
awk 'BEGIN {FS=":"; print "USER"} {print $1} END {print "DONE"}' /etc/passwd
```

### In-place editing with awk
GNU awk (4.1+) supports in-place editing:
```bash
awk -i inplace '{gsub(/old/, "new"); print}' file.c
```
But the safer, more portable pattern is to write to a temp file and move it:
```bash
awk '{gsub(/old/, "new"); print}' file.c > file.c.tmp && mv file.c.tmp file.c
```

---

## 11. Finding Files and Acting on Them

### `find`
```bash
find . -name "*.log"                    # by name (glob)
find /var -iname "error*"               # case-insensitive
find . -type f -size +1M                # files larger than 1 MB
find . -mtime -7                        # modified in last 7 days
find . -type d -name "node_modules"     # directories only
find . -empty                           # empty files/dirs
find . -name "*.c" -not -path "*/build/*"   # exclude a directory
```

### Acting on results
```bash
find . -name "*.tmp" -delete            # delete matches
find . -name "*.log" -exec gzip {} \;   # run a command on each ({} = file)
find . -name "*.bak" -exec rm {} +      # + batches args (more efficient)
find . -type f -exec grep -l "TODO" {} +   # find files containing TODO
```

### Applying an edit across many files
This is the core mass-refactoring pattern. **Always preview first.**

```bash
# Preview: which files contain the old symbol?
grep -rl "OldClass" --include="*.java" src/

# Dry-run the transformation on one file
sed 's/OldClass/NewClass/g' src/Main.java

# Apply across the whole tree, keeping backups
find src -name "*.java" -exec sed -i.bak 's/OldClass/NewClass/g' {} +

# Review, then remove backups once satisfied
find src -name "*.bak" -delete
```

### `xargs` — build command lines from stdin
```bash
find . -name "*.log" | xargs gzip
find . -name "*.tmp" -print0 | xargs -0 rm     # null-delimited (safe for spaces)
cat files.txt | xargs -I {} cp {} /backup/     # {} placeholder per line
grep -rl "deprecated" . | xargs sed -i 's/deprecated/legacy/g'
```

> **Safety tip:** Filenames can contain spaces or newlines. Prefer `find ... -print0 | xargs -0 ...` or `find ... -exec ... +` for robustness.

---

## 12. Chaining Commands Together

Beyond pipes, bash offers operators to control execution flow.

### Sequential and conditional operators
```bash
cmd1 ; cmd2          # run cmd2 regardless of cmd1's result
cmd1 && cmd2         # run cmd2 only if cmd1 SUCCEEDS (exit code 0)
cmd1 || cmd2         # run cmd2 only if cmd1 FAILS (non-zero exit)
```

Examples for code workflows:
```bash
make && ./run_tests.sh                 # test only if build succeeds
sed -i 's/foo/bar/g' f.c && make       # edit, then rebuild
grep -q "ready" status.txt && echo "Go!"
cd project || exit 1                   # bail out if cd fails
make clean; make                       # always rebuild from scratch
```

### Grouping commands
```bash
{ cmd1; cmd2; } > out.txt     # group in current shell, redirect together
( cmd1; cmd2 ) > out.txt      # run in a subshell
```

### Command substitution
Capture a command's output into a variable or argument:
```bash
files=$(ls *.txt)
today=$(date +%F)
echo "There are $(wc -l < data.txt) lines"
count=$(grep -rc "TODO" src/ | awk -F: '{s+=$2} END{print s}')
```
Prefer `$(...)` over the older backtick form — it nests cleanly.

### A realistic multi-stage pipeline
```bash
grep "ERROR" app.log \
  | awk '{print $4}' \
  | sort \
  | uniq -c \
  | sort -rn \
  | head -5
```
Reads: *find errors → extract the module field → sort → count duplicates → rank by frequency → top 5.*

---

## 13. Advanced Techniques

### Process substitution
Treat a command's output as if it were a file, using `<( )`:
```bash
diff <(sort file1.txt) <(sort file2.txt)     # compare sorted outputs
join <(sort -k1 a.txt) <(sort -k1 b.txt)     # join pre-sorted streams
# Compare a file against a transformed version of itself
diff main.c <(sed 's/old/new/g' main.c)
```

### Tee — split the stream
`tee` writes to a file **and** passes data downstream:
```bash
command | tee output.log | grep "error"      # save everything, filter onward
make 2>&1 | tee build.log                    # capture stdout+stderr and view
```

### Handling exit codes and strict mode
```bash
command
echo $?                 # exit status of the last command (0 = success)

set -e                  # exit immediately on any command failure
set -o pipefail         # a pipeline fails if ANY component fails
set -u                  # error on unset variables
set -euo pipefail       # the "strict mode" many scripts start with
```

For editing scripts that touch many files, strict mode prevents a failed `sed` from silently leaving your tree half-edited.

### Safe iteration over arbitrary filenames
```bash
while IFS= read -r -d '' file; do
    sed -i 's/old/new/g' "$file"
done < <(find . -type f -name "*.c" -print0)
```

### Parameter expansion on text
```bash
name="report.final.txt"
echo "${name%.txt}"        # report.final   (strip suffix)
echo "${name##*.}"         # txt            (extension)
echo "${name^^}"           # REPORT.FINAL.TXT (uppercase)
echo "${name/report/summary}"  # summary.final.txt
```

### Brace expansion for batch operations
```bash
cp main.c{,.bak}                 # copy main.c to main.c.bak
echo src/{main,util,io}.c        # expand to three filenames
mv config.{ini,conf}             # rename extension
```

---

## 14. Precision Code Editing Workflows

This section ties everything together into repeatable workflows for common code-editing tasks.

### Workflow A: Rename a symbol across a codebase
The danger: a naive replace of `id` corrupts `width`, `valid`, `identifier`.

```bash
# 1. Scope the search to relevant files, using word boundaries
grep -rnw "id" --include="*.c" --include="*.h" src/

# 2. Preview the exact change on one file
sed -E 's/\bid\b/user_id/g' src/model.c

# 3. Review the full diff without committing
for f in $(grep -rlw "id" --include="*.c" src/); do
    diff -u "$f" <(sed -E 's/\bid\b/user_id/g' "$f")
done

# 4. Commit with backups
grep -rlw "id" --include="*.c" --include="*.h" src/ \
  | xargs sed -i.bak -E 's/\bid\b/user_id/g'

# 5. Build, test, then clean up
make && make test && find src -name "*.bak" -delete
```

Key precision tools used: `-w` / `\b` for word boundaries, `--include` to scope file types, process substitution to preview diffs.

### Workflow B: Change a function signature everywhere
Suppose `int read(int fd)` becomes `ssize_t read(int fd, size_t len)`.

```bash
# Find all call sites and the definition
grep -rn "\bread\s*(" --include="*.c" src/

# Update the definition (anchored to line start + return type)
sed -i -E 's/^int read\(int fd\)/ssize_t read(int fd, size_t len)/' src/io.c

# Update call sites: read(x) -> read(x, BUF_SIZE)
# Capture the argument so we can reuse it
sed -i -E 's/\bread\(([^)]*)\)/read(\1, BUF_SIZE)/g' src/*.c
```

The capture group `\([^)]*\)` grabs whatever is inside the parentheses and `\1` puts it back — restructuring rather than blind replacement.

### Workflow C: Extract or delete a code block
Delete a function bounded by its signature and closing brace:

```bash
# Preview
sed -n '/^void legacy_helper/,/^}/p' module.c

# Delete it (with backup)
sed -i.bak '/^void legacy_helper/,/^}/d' module.c
```

For brace-matching that spans irregular indentation, prefer `awk` with a depth counter:

```bash
awk '
  /^void legacy_helper/ {skip=1; depth=0}
  skip {
    depth += gsub(/{/, "{")
    depth -= gsub(/}/, "}")
    if (depth <= 0 && /}/) {skip=0; next}
    next
  }
  {print}
' module.c
```

### Workflow D: Normalize formatting
```bash
# Strip trailing whitespace and convert tabs to 4 spaces, in place
find src -name "*.c" -exec sed -i -e 's/[[:space:]]*$//' -e 's/\t/    /g' {} +

# Ensure every file ends with exactly one newline
for f in src/*.c; do
    # remove all trailing blank lines, then add one newline
    printf '%s\n' "$(cat "$f")" > "$f"
done
```

### Workflow E: Generate code from a list
Turn a list of error names into a C enum and a lookup table:

```bash
# errors.txt contains one name per line: NOT_FOUND, TIMEOUT, ...

# Enum
{
  echo "typedef enum {"
  sed 's/^/    ERR_/' errors.txt | paste -sd',\n'
  echo "} ErrorCode;"
} > errors.h

# String lookup
awk '{printf "    case ERR_%s: return \"%s\";\n", $0, $0}' errors.txt > lookup.inc
```

### Workflow F: Safe bulk edit with a verification gate
Wrap risky edits so they only "stick" if the build still passes:

```bash
set -euo pipefail

# Snapshot
git stash || true
git status --porcelain && echo "Tree clean, proceeding"

# Edit
find src -name "*.py" -exec sed -i -E 's/\bold_api\b/new_api/g' {} +

# Verify
if make && make test; then
    echo "Edits verified."
else
    echo "Build failed — reverting." >&2
    git checkout -- src
    exit 1
fi
```

---

## 15. Practical Recipes

**1. Count lines of code in a project (excluding blanks/comments):**
```bash
find . -name "*.py" -exec cat {} + | grep -v '^\s*#' | grep -v '^\s*$' | wc -l
```

**2. Find the 10 most common words in a file:**
```bash
tr -cs 'A-Za-z' '\n' < book.txt | tr 'A-Z' 'a-z' | sort | uniq -c | sort -rn | head
```

**3. Extract email addresses from a file:**
```bash
grep -Eo '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' file.txt | sort -u
```

**4. List all functions defined in a C file:**
```bash
grep -En '^[a-zA-Z_][a-zA-Z0-9_ \*]+\([^;]*\)\s*\{?' module.c
```

**5. Show the 5 largest source files:**
```bash
find . -type f \( -name "*.c" -o -name "*.h" \) -exec wc -l {} + | sort -rn | head -6
```

**6. Rename all `.jpeg` files to `.jpg`:**
```bash
for f in *.jpeg; do mv "$f" "${f%.jpeg}.jpg"; done
```

**7. Add a license header to every source file (if missing):**
```bash
for f in src/*.c; do
  grep -q "Copyright" "$f" || { cat LICENSE_HEADER "$f" > tmp && mv tmp "$f"; }
done
```

**8. Watch a build log and highlight errors live:**
```bash
make 2>&1 | tee build.log | grep --line-buffered --color=always -E "error|warning"
```

**9. Compare two files ignoring whitespace and blank lines:**
```bash
diff -wB file1.txt file2.txt
```

**10. Convert all CRLF files in a tree to LF:**
```bash
find . -type f -name "*.c" -exec sed -i 's/\r$//' {} +
```

**11. Find files that contain a symbol but lack an include:**
```bash
for f in $(grep -rl "pthread_create" --include="*.c" .); do
  grep -q "#include <pthread.h>" "$f" || echo "Missing include: $f"
done
```

**12. Increment every version string `v1.2.3` patch number:**
```bash
sed -E 's/v([0-9]+\.[0-9]+\.)([0-9]+)/v\1$((\2+1))/e'  # GNU sed 'e' (use with care)
# Safer with awk:
awk -F. 'BEGIN{OFS="."} /^v/ {sub(/^v/,"",$NF); $NF=$NF+1; print "v"$0}' versions.txt
```

---

## 16. Quick Reference Cheat Sheet

| Task | Command |
|------|---------|
| View a file | `less file` |
| View a line range | `sed -n '40,60p' file` |
| First/last lines | `head -n 20 f` / `tail -n 20 f` |
| Follow a log | `tail -f log` |
| Search text (recursive) | `grep -rn "pattern" .` |
| Search whole words only | `grep -rnw "symbol" .` |
| Search with context | `grep -n -C 3 "pattern" f` |
| Count lines | `wc -l file` |
| Extract a column | `cut -d',' -f2 file` / `awk -F, '{print $2}'` |
| Sort | `sort -k2 -n file` |
| Unique + count | `sort f \| uniq -c \| sort -rn` |
| Find & replace (preview) | `sed 's/old/new/g' file` |
| Find & replace (in place) | `sed -i 's/old/new/g' file` |
| Replace with word boundary | `sed -E 's/\bold\b/new/g' file` |
| Restructure with capture | `sed -E 's/f\((.*)\)/g(\1)/' file` |
| Delete a line range | `sed '2,5d' file` |
| Delete a function block | `sed '/^void f/,/^}/d' file` |
| Field math | `awk '{s+=$1} END{print s}'` |
| Comment out a block | `awk '/start/{f=1} f{print "// "$0} /end/{f=0}'` |
| Find files | `find . -name "*.log" -mtime -7` |
| Act on many files | `find . -name "*.c" -exec sed -i '...' {} +` |
| Chain on success | `cmd1 && cmd2` |
| Capture output | `var=$(command)` |
| Compare files | `diff -u a b` |
| Compare ignoring space | `diff -wB a b` |
| Save & pass on | `cmd \| tee log \| next` |
| Preview a transform as diff | `diff f <(sed '...' f)` |

---

## Final Tips for Precise Code Editing

- **Quote your patterns and variables** (`"$var"`, `'pattern'`) to avoid word-splitting and glob surprises.
- **Anchor and bound your regex.** Use `^`, `$`, `\b`, and character classes so a rename never touches a substring by accident.
- **Scope edits** with `--include`, line ranges, and pattern addresses so a global replace only runs where intended.
- **Preview every destructive command** before adding `-i`. Use `diff file <(sed '...' file)` to see exactly what will change.
- **Keep backups** (`sed -i.bak`, `cp file{,.bak}`, or a clean `git` state) until the build passes.
- **Use capture groups** to restructure code rather than rewriting it wholesale.
- **Reach for the right tool:** `sed` for line-based substitution, `awk` for stateful/logic-driven edits, a real parser or formatter (`clang-format`, `black`, `gofmt`) for structural refactors that must respect language syntax.
- **Build pipelines incrementally** — run each stage alone and inspect its output before adding the next.
- Use `man <command>` and `command --help` to explore options; the manual pages are the authoritative reference.

With these building blocks, you can assemble arbitrarily powerful, surgical code-editing workflows directly in the shell — often in a single, reviewable line.
