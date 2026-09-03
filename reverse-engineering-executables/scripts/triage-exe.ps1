<# triage-exe.ps1 -SamplePath <exe> -CaseDir <dir> : static triage, never executes. #>
param(
  [Parameter(Mandatory=$true)][string]$SamplePath,
  [Parameter(Mandatory=$true)][string]$CaseDir
)
$ErrorActionPreference = 'Stop'
$copy = Join-Path $CaseDir 'evidence\original.bin'
New-Item -ItemType Directory -Force -Path (Join-Path $CaseDir 'evidence'), (Join-Path $CaseDir 'artifacts\triage'), (Join-Path $CaseDir 'notes') | Out-Null
if (-not (Test-Path -LiteralPath $copy)) {
  Copy-Item -LiteralPath $SamplePath -Destination $copy
  Set-ItemProperty -LiteralPath $copy -Name IsReadOnly -Value $true
}
$out = Join-Path $CaseDir 'artifacts\triage'
$h = Get-FileHash -LiteralPath $copy -Algorithm SHA256
$h.Hash + '  original.bin' | Out-File (Join-Path $CaseDir 'evidence\hashes.txt') -Encoding ascii
& file -k -- $copy 2>&1 | Tee-Object (Join-Path $out 'file.txt')
& dumpbin /HEADERS $copy 2>&1 | Tee-Object (Join-Path $out 'dumpbin-headers.txt')
& dumpbin /IMPORTS $copy 2>&1 | Tee-Object (Join-Path $out 'dumpbin-imports.txt')
& dumpbin /EXPORTS $copy 2>&1 | Tee-Object (Join-Path $out 'dumpbin-exports.txt')
Get-AuthenticodeSignature -FilePath $copy | Format-List * | Out-File (Join-Path $out 'authenticode.txt')
strings -a -n 5 -t x -- $copy 2>&1 | Out-File (Join-Path $out 'strings-ascii.txt')
Write-Output "triage complete: $CaseDir"
