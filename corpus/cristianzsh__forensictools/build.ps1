<#
.SYNOPSIS
    Builds the forensictools NSIS installer.

.DESCRIPTION
    Requires NSISBI (https://sourceforge.net/projects/nsisbi/).

.PARAMETER SrcDir
    Staged tool payload.

.PARAMETER MakeNsis
    Path to NSISBI's makensis.exe. Auto-detected if omitted.

.PARAMETER OutFileMode
    Optional. NSISBI 3.12 accepts aio (force a single .exe) or stub (force an
    external data file). Omit to let NSISBI decide.

.PARAMETER Detailed
    Verbose makensis output (/V4).

.EXAMPLE
    .\build.ps1
    .\build.ps1 -Detailed
    .\build.ps1 -MakeNsis "C:\Program Files\NSISBI\makensis.exe"
#>

[CmdletBinding()]
param(
    [string] $SrcDir = 'C:\ftools',
    [string] $MakeNsis,
    [ValidateSet('aio', 'stub')]
    [string] $OutFileMode,
    [switch] $Detailed
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not $MakeNsis) {
    $candidates = @()
    foreach ($base in @(${env:ProgramFiles}, ${env:ProgramFiles(x86)})) {
        if ($base) { $candidates += (Join-Path $base 'NSISBI\makensis.exe') }
    }
    $onPath = Get-Command 'makensis.exe' -ErrorAction SilentlyContinue
    if ($onPath) { $candidates += $onPath.Source }
    $MakeNsis = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}

if (-not $MakeNsis -or -not (Test-Path $MakeNsis)) {
    throw "makensis.exe not found. Install NSISBI or pass -MakeNsis <path>."
}
if (-not (Test-Path $SrcDir)) {
    throw "Payload directory '$SrcDir' not found."
}

$prev = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
$hdrInfo = & $MakeNsis /HDRINFO 2>&1 | Out-String
$ErrorActionPreference = $prev

if ($hdrInfo -notmatch 'NSIS_CONFIG_EXTERNAL_FILE_SUPPORT|nsisbi') {
    throw @"
'$MakeNsis' does not look like NSISBI.

Get NSISBI from https://sourceforge.net/projects/nsisbi/ and pass -MakeNsis.
"@
}

Write-Host "makensis : $MakeNsis"
Write-Host "payload  : $SrcDir"

$dist = Join-Path $root 'dist'
New-Item -ItemType Directory -Force -Path $dist | Out-Null

$nsi = Join-Path $root 'src\forensictools.nsi'
$nsisArgs = @("/DSRCDIR=$SrcDir")
if ($OutFileMode) { $nsisArgs += "/DFT_OUTFILEMODE=$OutFileMode" }
$nsisArgs += $(if ($Detailed) { '/V4' } else { '/V2' })
$nsisArgs += $nsi

Write-Host "`nBuilding $nsi ..." -ForegroundColor Cyan
$ErrorActionPreference = 'Continue'
& $MakeNsis @nsisArgs
$exit = $LASTEXITCODE
$ErrorActionPreference = $prev
if ($exit -ne 0) { throw "makensis failed with exit code $exit" }

Get-ChildItem $dist -Include '*.exe', '*.nsisbin' -Recurse |
    Select-Object Name, @{ n = 'SizeMB'; e = { [math]::Round($_.Length / 1MB, 1) } } |
    Format-Table -AutoSize

if (Get-ChildItem $dist -Filter '*.nsisbin' -ErrorAction SilentlyContinue) {
    Write-Warning "NSISBI produced an external data file."
}

Write-Host 'Done.' -ForegroundColor Green
