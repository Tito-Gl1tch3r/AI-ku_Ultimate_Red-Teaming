<#
.SYNOPSIS
    Install the x64dbg MCP plugin (.dp64 / .dp32) into your x64dbg installation.

.DESCRIPTION
    Finds x64dbg automatically - no hardcoded paths. Detection order:
      1. -Path argument
      2. Cached path from a previous run (.x64dbg-path)
      3. Shell registration  (HKCR\exefile\shell\Debug with x64dbg)
      4. A running x96dbg / x64dbg / x32dbg process
      5. x96dbg.exe on PATH
      6. Prompt (and remember the answer)

    Builds the plugins first if they're missing (with -Build), warns if x64dbg
    is running and has the DLL locked, and prints a tidy summary.

.EXAMPLE
    .\install.ps1                 # detect x64dbg, install both x64 + x32
    .\install.ps1 -Arch x64       # x64 only
    .\install.ps1 -Build          # build missing plugins first, then install
    .\install.ps1 -Path "D:\re\x64dbg\release"
    .\install.ps1 -Force          # ignore cached path and re-detect
#>

[CmdletBinding()]
param(
    [ValidateSet('x64', 'x32', 'both')] [string]$Arch = 'both',
    [string]$Path,
    [switch]$Build,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$Root      = $PSScriptRoot
$CacheFile = Join-Path $Root '.x64dbg-path'

# ── pretty printing ───────────────────────────────────────────────────────────
$E = [char]27
function Write-Banner {
    Write-Host ""
    Write-Host "$E[36m╔═══════════════════════════════════════════════╗$E[0m"
    Write-Host "$E[36m║$E[0m      $E[1mx64dbg MCP  ·  plugin installer$E[0m         $E[36m║$E[0m"
    Write-Host "$E[36m╚═══════════════════════════════════════════════╝$E[0m"
    Write-Host ""
}
function Write-Section($t) { Write-Host "$E[1m$E[97m$t$E[0m" }
function Write-Ok   ($t) { Write-Host "  $E[32m✓$E[0m $t" }
function Write-Info ($t) { Write-Host "  $E[36m→$E[0m $t" }
function Write-Warn ($t) { Write-Host "  $E[33m!$E[0m $t" }
function Write-Err  ($t) { Write-Host "  $E[31m✗$E[0m $t" }
function Write-Dim  ($t) { Write-Host "    $E[90m$t$E[0m" }

# ── helpers ───────────────────────────────────────────────────────────────────
# A valid x64dbg "root" is the release dir holding x32\ and x64\ subfolders.
function Test-X64dbgRoot([string]$dir) {
    if ([string]::IsNullOrWhiteSpace($dir) -or -not (Test-Path $dir)) { return $false }
    (Test-Path (Join-Path $dir 'x64\x64dbg.exe')) -or (Test-Path (Join-Path $dir 'x32\x32dbg.exe'))
}

# Normalize any x64dbg-related exe path to the release root.
function Resolve-RootFromExe([string]$exe) {
    if (-not $exe -or -not (Test-Path $exe)) { return $null }
    $leaf = Split-Path -Leaf $exe
    $dir  = Split-Path -Parent $exe
    switch -Regex ($leaf) {
        'x96dbg\.exe'           { return $dir }                       # <root>\x96dbg.exe
        '^(x64dbg|x32dbg)\.exe' { return (Split-Path -Parent $dir) }  # <root>\x64\x64dbg.exe
        default                 { return $dir }
    }
}

function Find-X64dbg {
    # 3. shell registration
    try {
        $cmd = (Get-ItemProperty 'Registry::HKEY_CLASSES_ROOT\exefile\shell\Debug with x64dbg\Command' `
                -ErrorAction Stop).'(default)'
        if ($cmd -match '"([^"]+x96dbg\.exe)"') {
            $r = Resolve-RootFromExe $Matches[1]
            if (Test-X64dbgRoot $r) { Write-Ok "found via shell registration"; return $r }
        }
    } catch {}

    # 4. running process
    foreach ($name in 'x96dbg', 'x64dbg', 'x32dbg') {
        $p = Get-Process -Name $name -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($p -and $p.Path) {
            $r = Resolve-RootFromExe $p.Path
            if (Test-X64dbgRoot $r) { Write-Ok "found via running $name process"; return $r }
        }
    }

    # 5. PATH
    $onPath = (Get-Command x96dbg.exe -ErrorAction SilentlyContinue).Source
    if ($onPath) {
        $r = Resolve-RootFromExe $onPath
        if (Test-X64dbgRoot $r) { Write-Ok "found on PATH"; return $r }
    }
    return $null
}

# ── main ──────────────────────────────────────────────────────────────────────
Write-Banner

# 1/2. explicit path, then cache
Write-Section "Locating x64dbg"
$x64dbgRoot = $null

if ($Path) {
    if (Test-X64dbgRoot $Path) { $x64dbgRoot = (Resolve-Path $Path).Path; Write-Ok "using -Path argument" }
    else { Write-Err "-Path '$Path' has no x32\x32dbg.exe or x64\x64dbg.exe"; exit 1 }
}
if (-not $x64dbgRoot -and -not $Force -and (Test-Path $CacheFile)) {
    $cached = (Get-Content $CacheFile -Raw).Trim()
    if (Test-X64dbgRoot $cached) { $x64dbgRoot = $cached; Write-Ok "using remembered path" }
}
if (-not $x64dbgRoot) { $x64dbgRoot = Find-X64dbg }

# 6. prompt
if (-not $x64dbgRoot) {
    Write-Warn "x64dbg not found automatically (it's portable / not registered)."
    Write-Dim "Enter the folder that contains the x32\ and x64\ subfolders"
    Write-Dim "(the x64dbg 'release' directory, where x96dbg.exe lives)."
    while (-not $x64dbgRoot) {
        $answer = Read-Host "  x64dbg path"
        if ([string]::IsNullOrWhiteSpace($answer)) { Write-Err "aborted."; exit 1 }
        $answer = $answer.Trim('"').Trim()
        if (Test-X64dbgRoot $answer) { $x64dbgRoot = (Resolve-Path $answer).Path }
        else { Write-Err "no x32\x32dbg.exe or x64\x64dbg.exe under '$answer' - try again." }
    }
}

Set-Content -Path $CacheFile -Value $x64dbgRoot -NoNewline
Write-Dim $x64dbgRoot
Write-Host ""

# is x64dbg running? (DLL may be locked)
$running = @(Get-Process -Name x64dbg, x32dbg -ErrorAction SilentlyContinue)
if ($running.Count) {
    Write-Warn "x64dbg is running - close it (or 'Reload plugins') if a copy is locked."
    Write-Host ""
}

# ── install ───────────────────────────────────────────────────────────────────
Write-Section "Installing plugins"
$targets = @()
if ($Arch -in 'x64', 'both') { $targets += [pscustomobject]@{ Arch = 'x64'; Ext = 'dp64' } }
if ($Arch -in 'x32', 'both') { $targets += [pscustomobject]@{ Arch = 'x32'; Ext = 'dp32' } }

$installed = 0
foreach ($t in $targets) {
    $src     = Join-Path $Root "plugin\build\$($t.Arch)-release\bin\x64dbg_mcp.$($t.Ext)"
    $destDir = Join-Path $x64dbgRoot "$($t.Arch)\plugins"

    if (-not (Test-Path $src)) {
        if ($Build) {
            Write-Info "$($t.Arch): not built - running build.ps1 -Arch $($t.Arch)"
            & "$Root\build.ps1" -Arch $t.Arch
        }
        if (-not (Test-Path $src)) {
            Write-Warn "$($t.Arch): skipped - not built. Run: .\build.ps1 -Arch $($t.Arch)"
            continue
        }
    }
    if (-not (Test-Path $destDir)) {
        Write-Warn "$($t.Arch): skipped - '$destDir' missing (no $($t.Arch) debugger in this install?)"
        continue
    }

    $dest = Join-Path $destDir "x64dbg_mcp.$($t.Ext)"
    try {
        Copy-Item -Path $src -Destination $dest -Force
        $kb = [math]::Round((Get-Item $dest).Length / 1KB)
        Write-Ok "$($t.Arch)  →  $dest  ($kb KB)"
        $installed++
    } catch {
        Write-Err "$($t.Arch): copy failed - $($_.Exception.Message)"
        Write-Dim "Is x64dbg running with the plugin loaded?"
    }
}

Write-Host ""
if ($installed) {
    Write-Section "Done"
    Write-Ok "$installed plugin(s) installed."
    Write-Dim "Restart x64dbg (or Plugins > Reload) - look for:"
    Write-Dim "[MCP] x64dbg MCP Server started on 127.0.0.1:27042"
} else {
    Write-Err "Nothing installed."
    Write-Dim "Build first:  .\build.ps1   (or pass -Build to do it here)"
    exit 1
}
Write-Host ""
