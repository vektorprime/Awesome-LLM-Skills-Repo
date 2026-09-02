---
name: powershell-text-editing
description: Use for all PowerShell shell work: reading, searching, and precisely editing text and code files with regex and pipeline
---

# Working with Text Files in PowerShell on Windows

## A Precision Guide to Reading, Editing, and Transforming Code Files

A progressive guide that starts with the fundamentals and builds toward
surgical, precise editing of source-code files from the PowerShell command line.

---

## Table of Contents

1. [Introduction & Core Concepts](#1-introduction--core-concepts)
2. [Setup, Help, and Environment](#2-setup-help-and-environment)
3. [Basic Commands](#3-basic-commands)
4. [Intermediate Operations](#4-intermediate-operations)
5. [The Pipeline & Chaining](#5-the-pipeline--chaining)
6. [Precise Code Editing Fundamentals](#6-precise-code-editing-fundamentals)
7. [Regular Expressions for Code](#7-regular-expressions-for-code)
8. [Advanced Editing Techniques](#8-advanced-editing-techniques)
9. [Structured & Multi-Line Edits](#9-structured--multi-line-edits)
10. [Bulk and Project-Wide Refactoring](#10-bulk-and-project-wide-refactoring)
11. [Safety, Backups, and Verification](#11-safety-backups-and-verification)
12. [Practical Recipes for Code Files](#12-practical-recipes-for-code-files)
13. [Performance & Pitfalls](#13-performance--pitfalls)
14. [Quick Reference](#14-quick-reference)

---

## 1. Introduction & Core Concepts

PowerShell treats everything as **objects**, not just raw text. When you read a
file, filter lines, or transform content, you are usually working with .NET
objects flowing through a **pipeline**. This is what makes PowerShell far more
powerful than a plain text shell — but it also means you must be deliberate
about *when* you want raw text versus structured objects.

For **precise code editing**, three ideas dominate:

1. **Preserve what you don't intend to change.** Indentation, line endings,
   encoding, and the byte-order mark (BOM) all matter in source files. A sloppy
   edit can silently reformat an entire file.
2. **Target exactly the text you mean.** Use anchors, capture groups, and
   context so a replacement touches only the intended occurrence.
3. **Verify before and after.** Diff your changes, keep backups, and confirm the
   edit count.

### Two flavors of PowerShell

| Version | Executable | Default output encoding | Notes |
|---|---|---|---|
| **Windows PowerShell 5.1** | `powershell.exe` | Often UTF-16LE or system ANSI | Ships with Windows. `Set-Content`/`Out-File` default to non-UTF-8. |
| **PowerShell 7.x** | `pwsh.exe` | UTF-8 (no BOM) | Cross-platform, modern defaults, `&&` / `||` operators. |

> ⚠️ **Encoding is the #1 source of "mysterious" diffs.** A script run in
> `pwsh` may rewrite a file as UTF-8, while the same script in `powershell.exe`
> writes UTF-16 or ANSI — producing a diff on *every line* even when you only
> changed one. **Always specify `-Encoding` explicitly** when editing code.

### Line endings: CRLF vs LF

Windows code files traditionally use `CRLF` (`\r\n`); Unix and many modern
repos use `LF` (`\n`). PowerShell's `Get-Content` strips line endings when it
returns an array of lines, and `Set-Content` re-adds them using the platform
default. If you need to preserve exact line endings, work with `-Raw` and be
explicit.

---

## 2. Setup, Help, and Environment

### Checking your version

```powershell
$PSVersionTable.PSVersion
$PSVersionTable.PSEdition   # 'Desktop' = Windows PowerShell, 'Core' = PS 7
```

### Getting help (the most important skill)

```powershell
Get-Help Get-Content              # Basic help
Get-Help Get-Content -Examples    # Practical examples
Get-Help Get-Content -Full        # Complete reference
Get-Help Get-Content -Online      # Opens the browser docs
Get-Help about_Regular_Expressions # Deep dive on regex syntax
```

### Useful environment defaults

```powershell
# See the current location
Get-Location

# Set a default encoding preference for the session (PS 7 respects this less;
# explicit -Encoding is still best)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)  # UTF-8, no BOM
```

### Detecting a file's encoding

```powershell
# Inspect the first bytes to spot a BOM
$bytes = [System.IO.File]::ReadAllBytes(".\file.cs")
$bytes[0..2] | ForEach-Object { '{0:X2}' -f $_ }
# EF BB BF = UTF-8 BOM | FF FE = UTF-16 LE | FE FF = UTF-16 BE
```

---

## 3. Basic Commands

### 3.1 Reading a file: `Get-Content`

The workhorse for reading text files.

```powershell
# Read an entire file (returns an array of lines)
Get-Content .\Program.cs

# Aliases: 'cat', 'gc', 'type'
cat .\Program.cs
gc .\Program.cs
```

**Useful parameters:**

```powershell
# Read the last 10 lines (great for logs)
Get-Content .\build.log -Tail 10

# Follow a file in real time (like Unix 'tail -f')
Get-Content .\build.log -Wait -Tail 20

# Read the first 5 lines
Get-Content .\data.txt -TotalCount 5

# Read the whole file as ONE string (preserves newlines)
Get-Content .\config.json -Raw

# Read a specific encoding
Get-Content .\legacy.cs -Encoding UTF8

# Read lines in batches (faster for large files)
Get-Content .\huge.log -ReadCount 1000
```

> 💡 **`-Raw` vs. default.** Without `-Raw`, you get a `string[]` with one
> element per line and the line endings removed. With `-Raw`, you get a single
> string with newlines intact. For precise whole-file edits and multi-line
> regex, **`-Raw` is usually what you want.**

### 3.2 Listing and finding files: `Get-ChildItem`

```powershell
# List files in the current directory (aliases: ls, dir, gci)
Get-ChildItem

# List only C# files
Get-ChildItem -Filter *.cs

# Recurse into subdirectories
Get-ChildItem -Recurse -Filter *.cs

# Multiple extensions with -Include (requires -Recurse or trailing \*)
Get-ChildItem -Path .\src\* -Recurse -Include *.cs,*.csproj

# Full paths of all source files, excluding build output
Get-ChildItem -Recurse -Include *.cs |
    Where-Object { $_.FullName -notmatch '\\(bin|obj)\\' }
```

### 3.3 Creating and overwriting files: `Set-Content` and `Out-File`

```powershell
# Create/overwrite a file with content
Set-Content -Path .\hello.txt -Value "Hello, World!"

# Write multiple lines (array becomes lines)
Set-Content -Path .\list.txt -Value "apple", "banana", "cherry"

# Control encoding explicitly (critical for code files)
Set-Content -Path .\Program.cs -Value $code -Encoding UTF8
```

`Out-File` formats output the way it would appear on the console (with column
alignment). For code, prefer `Set-Content` or `Out-File -Encoding utf8` with
raw strings.

```powershell
# Save formatted process list (example of Out-File's formatting behavior)
Get-Process | Out-File .\processes.txt
```

### 3.4 Appending: `Add-Content`

```powershell
# Add a line to the end of an existing file
Add-Content -Path .\CHANGELOG.md -Value "- Fixed null reference bug"
```

### 3.5 Reading a specific line range

```powershell
# Lines 40 through 60 (1-indexed)
(Get-Content .\Program.cs)[39..59]

# Using Select-Object
Get-Content .\Program.cs | Select-Object -Skip 39 -First 21
```

### 3.6 Quick reference table

| Task | Command |
|---|---|
| View a file | `Get-Content file.cs` |
| Last N lines | `Get-Content file.cs -Tail N` |
| First N lines | `Get-Content file.cs -TotalCount N` |
| Whole file as string | `Get-Content file.cs -Raw` |
| Specific line range | `(Get-Content file.cs)[start..end]` |
| Create/overwrite | `Set-Content file.cs -Value $code -Encoding UTF8` |
| Append | `Add-Content file.cs -Value "..."` |
| List files | `Get-ChildItem -Filter *.cs` |

---

## 4. Intermediate Operations

### 4.1 Searching within files: `Select-String`

PowerShell's equivalent of `grep`, and essential for locating code before
editing it.

```powershell
# Find lines containing "TODO"
Select-String -Path .\Program.cs -Pattern "TODO"

# Case-sensitive search (important for code identifiers)
Select-String -Path .\Program.cs -Pattern "MyClass" -CaseSensitive

# Search across many files
Select-String -Path .\src\*.cs -Pattern "Obsolete"

# Regular expressions: find method declarations
Select-String -Path .\src\*.cs -Pattern '(public|private|protected)\s+\w+\s+\w+\s*\('

# Return only the matched text, not whole lines
Select-String -Path .\data.cs -Pattern '\b\d+\b' -AllMatches |
    ForEach-Object { $_.Matches.Value }

# Context lines (2 before, 3 after) — like grep -C
Select-String -Path .\Program.cs -Pattern "catch" -Context 2,3

# List just the filenames that contain a match
Select-String -Path .\src\*.cs -Pattern "HttpClient" -List |
    Select-Object -ExpandProperty Path
```

Each result is a rich **MatchInfo** object with `.Line`, `.LineNumber`,
`.Path`, `.Filename`, and `.Matches` properties.

### 4.2 Filtering lines: `Where-Object`

```powershell
# Keep only lines longer than 100 characters (find overly long lines)
Get-Content .\Program.cs | Where-Object { $_.Length -gt 100 }

# Keep comment lines
Get-Content .\Program.cs | Where-Object { $_ -match '^\s*//' }

# Skip blank lines
Get-Content .\messy.cs | Where-Object { $_.Trim() -ne "" }
```

### 4.3 Selecting and skipping: `Select-Object`

```powershell
# First 3 lines
Get-Content .\Program.cs | Select-Object -First 3

# Last 3 lines
Get-Content .\Program.cs | Select-Object -Last 3

# Skip the first 2 header lines
Get-Content .\data.csv | Select-Object -Skip 2
```

### 4.4 Sorting and uniqueness

```powershell
# Sort lines alphabetically
Get-Content .\names.txt | Sort-Object

# Unique lines (like 'sort | uniq')
Get-Content .\imports.txt | Sort-Object -Unique

# Count of unique lines
(Get-Content .\words.txt | Sort-Object -Unique).Count
```

### 4.5 Measuring: `Measure-Object`

```powershell
# Count lines
(Get-Content .\Program.cs).Count

# Lines, words, and characters
Get-Content .\Program.cs | Measure-Object -Line -Word -Character
```

### 4.6 Comparing files: `Compare-Object`

```powershell
# Diff two files
Compare-Object (Get-Content .\old.cs) (Get-Content .\new.cs)

# Show only differences, with which side they came from
Compare-Object (Get-Content .\old.cs) (Get-Content .\new.cs) |
    Format-Table -AutoSize
```

`SideIndicator`: `<=` means only in the left (reference) file, `=>` means only
in the right (difference) file.

---

## 5. The Pipeline & Chaining

The pipe operator `|` passes the **output objects** of one command as **input**
to the next. This is where PowerShell becomes powerful.

### 5.1 Basic chaining

```powershell
# Count lines in every .cs file
Get-ChildItem -Filter *.cs -Recurse |
    ForEach-Object {
        $lines = (Get-Content $_.FullName).Count
        "$($_.Name): $lines lines"
    }
```

### 5.2 A realistic multi-stage pipeline

Goal: *Find every `TODO` comment across the project, sorted by file and line.*

```powershell
Get-ChildItem -Path .\src -Filter *.cs -Recurse |
    Select-String -Pattern "TODO" -CaseSensitive |
    Sort-Object Path, LineNumber |
    ForEach-Object { "$($_.Filename):$($_.LineNumber): $($_.Line.Trim())" } |
    Set-Content .\todo-report.txt
```

Stage by stage:
1. `Get-ChildItem` → emits **FileInfo** objects.
2. `Select-String` → searches each file, emits **MatchInfo** objects.
3. `Sort-Object` → orders by file path then line number.
4. `ForEach-Object` → reshapes each match into a readable string.
5. `Set-Content` → writes the report.

### 5.3 `ForEach-Object` vs the `foreach` statement

```powershell
# Pipeline form (streams, low memory)
Get-Content .\big.cs | ForEach-Object { $_.TrimEnd() }

# Statement form (loads all into memory first, faster for small sets)
foreach ($line in Get-Content .\big.cs) {
    $line.TrimEnd()
}
```

### 5.4 Chain operators (PowerShell 7+)

```powershell
# Run second command only if first succeeds
Get-Content .\input.cs && Write-Host "Read OK"

# Run second command only if first fails
Get-Content .\missing.cs || Write-Host "File not found"
```

> ⚠️ `&&` and `||` require **PowerShell 7+**. In Windows PowerShell 5.1, use
> `if ($?) { ... } else { ... }`.

### 5.5 Storing intermediate results

```powershell
$matches = Get-ChildItem .\src -Filter *.cs -Recurse |
    Select-String "Obsolete"
$files = $matches | Select-Object -ExpandProperty Path -Unique
Write-Host "Found $($matches.Count) usages across $($files.Count) files"
$matches | Set-Content .\obsolete-report.txt
```

---

## 6. Precise Code Editing Fundamentals

This section is the heart of the guide: how to change code **exactly** where
you intend, and nowhere else.

### 6.1 The core edit pattern

Almost every precise text edit follows this shape:

```powershell
# 1. Read the whole file as a single string
$content = Get-Content .\Program.cs -Raw

# 2. Transform it (replace, insert, etc.)
$updated = $content -replace 'oldText', 'newText'

# 3. Write it back with an explicit encoding
Set-Content .\Program.cs -Value $updated -Encoding UTF8 -NoNewline
```

Key details:
- **`-Raw`** keeps the file as one string so multi-line context and line
  endings are preserved.
- **`-NoNewline`** (PS 6+) prevents `Set-Content` from appending an extra
  trailing newline that wasn't there before.
- **`-Encoding UTF8`** avoids silent re-encoding.

### 6.2 Simple string replacement: `-replace`

`-replace` is **regex-based** and **case-insensitive by default**.

```powershell
$content = Get-Content .\Program.cs -Raw

# Replace every occurrence (case-insensitive!)
$content = $content -replace 'foo', 'bar'

# Case-SENSITIVE replacement (use -creplace)
$content = $content -creplace 'MyClass', 'MyRenamedClass'

# Replace only using literal strings (escape regex metacharacters)
$old = [regex]::Escape("array[0]")
$content = $content -replace $old, "array[1]"
```

> 💡 **`-replace` vs `-creplace` vs `-ireplace`:**
> - `-replace` / `-ireplace` → case-insensitive
> - `-creplace` → case-sensitive (usually what you want for code identifiers)

### 6.3 Replacing a specific occurrence only

`-replace` changes *all* matches. To change just one, anchor it with unique
surrounding context:

```powershell
# Instead of replacing every "count", target the specific declaration
$content = $content -creplace 'int count = 0;', 'int count = 1;'
```

Or use a regex with a capture group to change only part of a matched pattern:

```powershell
# Change the default value but keep the variable name
$content = $content -creplace '(int\s+timeout\s*=\s*)\d+', '${1}30'
```

### 6.4 Counting how many replacements happened

Always verify the edit count before trusting a bulk change.

```powershell
$before = ([regex]::Matches($content, 'OldName')).Count
$content = $content -creplace 'OldName', 'NewName'
$after = ([regex]::Matches($content, 'OldName')).Count
Write-Host "Replaced $($before - $after) occurrence(s)"
```

### 6.5 Editing a single line by line number

```powershell
$lines = Get-Content .\Program.cs          # array of lines
$lines[41] = '    private int _count;'     # line 42 (0-indexed array)
Set-Content .\Program.cs -Value $lines -Encoding UTF8
```

> ⚠️ Line-number edits are **fragile** — any earlier change shifts the numbers.
> Prefer pattern-based edits unless the file is stable.

### 6.6 Inserting a line before/after a matched line

```powershell
$lines = Get-Content .\Program.cs
$output = foreach ($line in $lines) {
    $line
    if ($line -match '^\s*using System;') {
        'using System.Linq;'   # inserted right after the match
    }
}
Set-Content .\Program.cs -Value $output -Encoding UTF8
```

### 6.7 Removing lines that match a pattern

```powershell
# Delete all "// DEBUG" comment lines
Get-Content .\Program.cs |
    Where-Object { $_ -notmatch '^\s*//\s*DEBUG' } |
    Set-Content .\Program.cs -Encoding UTF8
```

### 6.8 Trimming trailing whitespace (without touching anything else)

```powershell
$content = Get-Content .\Program.cs -Raw
$content = $content -replace '[ \t]+(\r?\n)', '$1'   # strip spaces/tabs before EOL
Set-Content .\Program.cs -Value $content -Encoding UTF8 -NoNewline
```

---

## 7. Regular Expressions for Code

Regex is the scalpel for precise edits. PowerShell uses .NET regular
expressions.

### 7.1 The `-match` operator and `$Matches`

```powershell
$line = 'public int MaxRetries = 5;'
if ($line -match '(public|private)\s+(\w+)\s+(\w+)\s*=\s*(\d+)') {
    $Matches[0]   # full match: 'public int MaxRetries = 5'
    $Matches[1]   # 'public'
    $Matches[2]   # 'int'
    $Matches[3]   # 'MaxRetries'
    $Matches[4]   # '5'
}
```

### 7.2 Common code-matching patterns

| Goal | Pattern |
|---|---|
| C# method declaration | `(public\|private\|protected\|internal)\s+[\w<>\[\]]+\s+\w+\s*\(` |
| `using` directive | `^\s*using\s+[\w.]+;` |
| A whole-line comment | `^\s*//.*$` |
| A GUID | `[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}` |
| An integer literal | `\b\d+\b` |
| A double-quoted string | `"[^"]*"` |
| CRLF line ending | `\r\n` |

### 7.3 Anchors and boundaries

```powershell
# ^ = start of line/string, $ = end, \b = word boundary
# Change only the standalone word "id", not "identity" or "valid"
$content = $content -creplace '\bid\b', 'identifier'

# Match a line that is exactly "}"
$content = $content -replace '(?m)^\}$', '    }'
```

> 💡 **`(?m)` multiline mode** makes `^` and `$` match the start/end of *each
> line* rather than the whole string. Essential when editing with `-Raw`.

### 7.4 Capture groups and backreferences in replacements

```powershell
# Swap "First Last" to "Last, First"
$content = $content -replace '(\w+)\s+(\w+)', '$2, $1'

# Rename a method but keep its arguments
$content = $content -creplace 'GetData\((.*?)\)', 'FetchData($1)'
```

### 7.5 Named capture groups (more readable)

```powershell
$pattern = '(?<type>\w+)\s+(?<name>\w+)\s*=\s*(?<value>[^;]+);'
if ($line -match $pattern) {
    $Matches.name    # variable name
    $Matches.value   # assigned value
}
```

### 7.6 Lookahead / lookbehind (edit without consuming context)

```powershell
# Insert text after a match without including the match in the replacement
# Add " readonly" after "private" only when followed by a field type
$content = $content -creplace '(?<=private)(\s+\w+\s+\w+\s*=)', ' readonly$1'
```

---

## 8. Advanced Editing Techniques

### 8.1 Multi-line replacements with `-Raw`

Because `-Raw` keeps newlines, you can match across lines:

```powershell
$content = Get-Content .\Program.cs -Raw

# Replace an entire method body spanning multiple lines
$pattern = '(?s)void OldMethod\(\)\s*\{.*?\}'   # (?s) makes . match newlines
$replacement = @'
void OldMethod()
{
    // new implementation
    Logger.Info("called");
}
'@
$content = $content -replace $pattern, $replacement
Set-Content .\Program.cs -Value $content -Encoding UTF8 -NoNewline
```

> 💡 **`(?s)` singleline mode** makes `.` match newline characters. Combine with
> `.*?` (lazy) to stop at the first closing brace.

### 8.2 Here-strings for multi-line replacement text

```powershell
$newMethod = @"
public int Add(int a, int b)
{
    return a + b;
}
"@

$content = Get-Content .\Math.cs -Raw
$content = $content -replace '(?s)public int Add\(int a, int b\)\s*\{.*?\}', $newMethod
Set-Content .\Math.cs -Value $content -Encoding UTF8 -NoNewline
```

Use single-quoted here-strings `@'...'@` when you don't want variable
expansion inside the replacement.

### 8.3 Using a callback for dynamic replacements

For logic-driven edits, use `[regex]::Replace` with a script block:

```powershell
$content = Get-Content .\Program.cs -Raw

# Double every integer literal in the file
$updated = [regex]::Replace($content, '\b(\d+)\b', {
    param($m)
    [string]([int]$m.Value * 2)
})

Set-Content .\Program.cs -Value $updated -Encoding UTF8 -NoNewline
```

### 8.4 Conditional edits (only if a pattern exists)

```powershell
$content = Get-Content .\Program.cs -Raw
if ($content -match 'OldApi') {
    $content = $content -creplace 'OldApi', 'NewApi'
    Set-Content .\Program.cs -Value $content -Encoding UTF8 -NoNewline
    Write-Host "Updated Program.cs"
} else {
    Write-Host "No changes needed"
}
```

### 8.5 Preserving the original encoding and BOM

```powershell
# Detect and reuse the original encoding
$path = ".\Program.cs"
$bytes = [System.IO.File]::ReadAllBytes($path)
$hasBom = ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF)

$content = Get-Content $path -Raw
$content = $content -creplace 'OldName', 'NewName'

# Write back preserving BOM presence
$utf8 = [System.Text.UTF8Encoding]::new($hasBom)
[System.IO.File]::WriteAllText((Resolve-Path $path), $content, $utf8)
```

### 8.6 Preserving exact line endings

```powershell
$content = Get-Content .\file.cs -Raw
$usesCrlf = $content -match "\r\n"

$updated = $content -creplace 'foo', 'bar'

# Normalize to the file's original style before writing
if (-not $usesCrlf) {
    $updated = $updated -replace "\r\n", "`n"
}
Set-Content .\file.cs -Value $updated -Encoding UTF8 -NoNewline
```

---

## 9. Structured & Multi-Line Edits

### 9.1 Editing JSON precisely

```powershell
$json = Get-Content .\appsettings.json -Raw | ConvertFrom-Json

# Modify a nested value
$json.ConnectionStrings.Default = "Server=prod;Database=app"
$json.Logging.LogLevel.Default = "Warning"

# Write back with readable indentation
$json | ConvertTo-Json -Depth 20 | Set-Content .\appsettings.json -Encoding UTF8
```

> ⚠️ `ConvertTo-Json` reformats the whole file. If you must preserve exact
> formatting, use a targeted `-replace` instead.

### 9.2 Editing XML / .csproj files

```powershell
[xml]$proj = Get-Content .\App.csproj
$proj.Project.PropertyGroup.TargetFramework = "net8.0"
$proj.Save((Resolve-Path .\App.csproj))
```

### 9.3 Editing CSV

```powershell
Import-Csv .\users.csv |
    ForEach-Object {
        if ($_.Department -eq "Eng") { $_.Role = "Engineer" }
        $_
    } |
    Export-Csv .\users.csv -NoTypeInformation -Encoding UTF8
```

### 9.4 Parsing custom log/text into objects

```powershell
Get-Content .\access.log | ForEach-Object {
    if ($_ -match '^(\S+) \S+ \S+ \[([^\]]+)\] "(\S+) (\S+)" (\d+)') {
        [PSCustomObject]@{
            IP     = $Matches[1]
            Time   = $Matches[2]
            Method = $Matches[3]
            Path   = $Matches[4]
            Status = [int]$Matches[5]
        }
    }
} |
Where-Object Status -ge 400 |
Group-Object Path |
Sort-Object Count -Descending |
Select-Object -First 10
```

---

## 10. Bulk and Project-Wide Refactoring

### 10.1 Rename an identifier across all source files

```powershell
Get-ChildItem -Path .\src -Recurse -Include *.cs |
    Where-Object { $_.FullName -notmatch '\\(bin|obj)\\' } |
    ForEach-Object {
        $content = Get-Content $_.FullName -Raw
        if ($content -cmatch '\bOldService\b') {
            $updated = $content -creplace '\bOldService\b', 'NewService'
            Set-Content $_.FullName -Value $updated -Encoding UTF8 -NoNewline
            Write-Host "Updated $($_.FullName)"
        }
    }
```

Note the use of `\b` word boundaries so `OldServiceClient` is **not** touched.

### 10.2 Add a header comment to every file

```powershell
$header = "// Copyright (c) 2025 Acme Corp. All rights reserved.`n"

Get-ChildItem -Path .\src -Recurse -Filter *.cs | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    if ($content -notmatch '^// Copyright') {
        Set-Content $_.FullName -Value ($header + $content) -Encoding UTF8 -NoNewline
    }
}
```

### 10.3 Dry-run first (preview changes without writing)

```powershell
Get-ChildItem -Path .\src -Recurse -Filter *.cs | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    $count = ([regex]::Matches($content, '\bOldService\b')).Count
    if ($count -gt 0) {
        Write-Host "$($_.FullName): $count match(es)"
    }
}
```

Run the dry run, confirm the counts, *then* run the real edit.

### 10.4 Parallel edits for large repos (PowerShell 7+)

```powershell
Get-ChildItem -Path .\src -Recurse -Filter *.cs | ForEach-Object -Parallel {
    $content = Get-Content $_.FullName -Raw
    if ($content -cmatch '\bOldService\b') {
        $updated = $content -creplace '\bOldService\b', 'NewService'
        Set-Content $_.FullName -Value $updated -Encoding UTF8 -NoNewline
    }
} -ThrottleLimit 8
```

---

## 11. Safety, Backups, and Verification

### 11.1 Always back up before bulk edits

```powershell
# Copy the whole project to a timestamped backup
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
Copy-Item .\src ".\src-backup-$stamp" -Recurse
```

### 11.2 Use Git as your safety net

```powershell
# Ensure a clean state before editing
git status
git stash            # if needed

# After editing, review exactly what changed
git diff
git diff --stat      # summary of files changed

# Undo everything if it went wrong
git checkout -- .
```

### 11.3 Verify with a diff after editing

```powershell
Compare-Object (Get-Content .\Program.cs.bak) (Get-Content .\Program.cs) |
    Format-Table -AutoSize
```

### 11.4 Confirm the file still parses (for PowerShell files)

```powershell
$errors = $null
[System.Management.Automation.Language.Parser]::ParseFile(
    ".\script.ps1", [ref]$null, [ref]$errors)
if ($errors) { $errors | ForEach-Object { Write-Warning $_.Message } }
else { Write-Host "Parses cleanly" }
```

---

## 12. Practical Recipes for Code Files

### Recipe 1: Rename a method everywhere, safely

```powershell
$old = 'CalculateTotal'
$new = 'ComputeTotal'

Get-ChildItem -Path .\src -Recurse -Include *.cs |
    Where-Object { $_.FullName -notmatch '\\(bin|obj)\\' } |
    ForEach-Object {
        $c = Get-Content $_.FullName -Raw
        if ($c -cmatch "\b$old\b") {
            ($c -creplace "\b$old\b", $new) |
                Set-Content $_.FullName -Encoding UTF8 -NoNewline
            Write-Host "Renamed in $($_.Name)"
        }
    }
```

### Recipe 2: Add a missing `using` directive to files that need it

```powershell
Get-ChildItem -Path .\src -Recurse -Filter *.cs | ForEach-Object {
    $c = Get-Content $_.FullName -Raw
    # Only if the file uses LINQ but lacks the using
    if ($c -match '\.Select\(|\.Where\(' -and $c -notmatch 'using System\.Linq;') {
        $c = $c -replace '(?m)^(using System;)', "`$1`nusing System.Linq;"
        Set-Content $_.FullName -Value $c -Encoding UTF8 -NoNewline
        Write-Host "Added using to $($_.Name)"
    }
}
```

### Recipe 3: Convert tabs to spaces (4-space indent)

```powershell
Get-ChildItem -Path .\src -Recurse -Filter *.cs | ForEach-Object {
    $c = Get-Content $_.FullName -Raw
    $c = $c -replace "\t", "    "
    Set-Content $_.FullName -Value $c -Encoding UTF8 -NoNewline
}
```

### Recipe 4: Remove all `Console.WriteLine` debug lines

```powershell
Get-ChildItem -Path .\src -Recurse -Filter *.cs | ForEach-Object {
    $lines = Get-Content $_.FullName
    $kept = $lines | Where-Object { $_ -notmatch '^\s*Console\.WriteLine' }
    if ($kept.Count -ne $lines.Count) {
        Set-Content $_.FullName -Value $kept -Encoding UTF8
        Write-Host "Cleaned $($_.Name)"
    }
}
```

### Recipe 5: Bump a version number in a project file

```powershell
$proj = ".\App.csproj"
$c = Get-Content $proj -Raw
$c = $c -replace '(<Version>)\d+\.\d+\.\d+(</Version>)', '${1}2.0.0${2}'
Set-Content $proj -Value $c -Encoding UTF8 -NoNewline
```

### Recipe 6: Find overly complex lines (long lines report)

```powershell
Get-ChildItem -Path .\src -Recurse -Filter *.cs | ForEach-Object {
    $file = $_.Name
    Get-Content $_.FullName | ForEach-Object {
        if ($_.Length -gt 120) {
            [PSCustomObject]@{ File = $file; Length = $_.Length; Line = $_.Trim() }
        }
    }
} | Sort-Object Length -Descending | Format-Table -AutoSize
```

---

## 13. Performance & Pitfalls

### Common pitfalls

| Pitfall | Solution |
|---|---|
| Forgetting `-Raw` for whole-file edits | Use `-Raw` for multi-line regex and replacements |
| `-replace` is case-insensitive by default | Use `-creplace` / `-cmatch` for code identifiers |
| Encoding surprises between PS 5.1 and PS 7 | Always specify `-Encoding` explicitly |
| Extra trailing newline added on write | Use `Set-Content -NoNewline` (PS 6+) |
| `\b` boundaries omitted in renames | Use `\bName\b` to avoid partial matches |
| Editing a file while reading it | Read fully with `-Raw` before writing back |
| `+=` on arrays in a loop (very slow) | Stream through the pipeline instead |
| Single-line file returns a string, not array | Wrap in `@(...)` to force an array |

### Performance tips

1. **Filter early.** Put `Where-Object` / `Select-String` close to the source.
2. **Prefer `-Filter` over `-Include`** on `Get-ChildItem` — it's faster.
3. **Use `-ReadCount`** for large files:
   ```powershell
   Get-Content .\huge.log -ReadCount 1000 | ForEach-Object {
       $_ | Where-Object { $_ -match "ERROR" }
   }
   ```
4. **For truly massive files**, stream with `[System.IO.File]::ReadLines()` or
   a `StreamReader` instead of loading everything into memory.
5. **Dry-run before bulk writes** to confirm match counts.

---

## 14. Quick Reference

### Unix → PowerShell command map

| Unix | PowerShell |
|---|---|
| `cat file` | `Get-Content file` |
| `tail -f file` | `Get-Content file -Wait -Tail 10` |
| `head -n 5 file` | `Get-Content file -TotalCount 5` |
| `grep pattern file` | `Select-String -Path file -Pattern pattern` |
| `grep -i pattern` | `Select-String -Pattern pattern` (default insensitive) |
| `wc -l file` | `(Get-Content file).Count` |
| `sort file \| uniq` | `Get-Content file \| Sort-Object -Unique` |
| `sed 's/a/b/' file` | `(Get-Content file -Raw) -creplace 'a','b'` |
| `find . -name "*.cs"` | `Get-ChildItem -Recurse -Filter *.cs` |
| `diff a b` | `Compare-Object (Get-Content a) (Get-Content b)` |

### The precision editing checklist

1. **Read** with `Get-Content -Raw`.
2. **Match** precisely: anchors (`^`, `$`), word boundaries (`\b`), context.
3. **Use `-creplace`** for case-sensitive identifier edits.
4. **Count** matches before and after to verify.
5. **Back up** (copy or Git) before bulk changes.
6. **Write** with explicit `-Encoding` and `-NoNewline`.
7. **Verify** with `git diff` or `Compare-Object`.

---

## Summary

- **Start simple:** `Get-Content`, `Set-Content`, `Add-Content`,
  `Get-ChildItem`.
- **Locate precisely:** `Select-String`, `Where-Object`, `-match`.
- **Edit surgically:** `-Raw` + `-creplace` + capture groups + anchors.
- **Chain with the pipeline (`|`)** to compose small commands into workflows.
- **Go advanced** with multi-line regex (`(?s)`, `(?m)`), `[regex]::Replace`
  callbacks, and structured formats (`ConvertFrom-Json`, XML, CSV).
- **Stay safe:** back up, dry-run, verify counts, and preserve encoding and
  line endings.

The core mental model for code editing:
**read raw, match precisely, replace case-sensitively, write with explicit
encoding, then verify the diff.**
