$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Build = Join-Path $Root "build"
New-Item -ItemType Directory -Force $Build | Out-Null

$VsWhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path $VsWhere)) {
    throw "vswhere.exe not found. Install Visual Studio Build Tools or run this from a Developer PowerShell."
}

$VsInstallOutput = & $VsWhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $VsInstallOutput) {
    throw "Visual Studio C++ tools were not found."
}
$VsInstall = @($VsInstallOutput) |
    ForEach-Object { $_ -split '\r?\n' } |
    ForEach-Object { $_.Trim() } |
    Where-Object { $_ } |
    Select-Object -First 1
$VsInstall = ($VsInstall -replace '[\r\n]+', '').Trim()

$VcVars = Join-Path $VsInstall "VC\Auxiliary\Build\vcvars64.bat"
if (-not (Test-Path $VcVars)) {
    throw "vcvars64.bat not found under $VsInstall"
}
$VcVars = ($VcVars -replace '[\r\n]+', '').Trim()

$CommonIncludes = @(
    "/I$Root\include",
    "/I$Root\third_party\minhook\include",
    "/I$Root\third_party\minhook\src",
    "/I$Root\third_party\minhook\src\hde",
    "/I$Root\third_party\krabsetw",
    "/I$Root\third_party\zydis\include",
    "/I$Root\third_party\zydis\src",
    "/I$Root\third_party\zydis\dependencies\zycore\include"
)

$CommonDefines = @(
    "/DUNICODE",
    "/D_UNICODE",
    "/DNOMINMAX",
    "/DZYDIS_STATIC_BUILD",
    "/DZYCORE_STATIC_BUILD",
    "/DZYDIS_DISABLE_ENCODER",
    "/DZYDIS_DISABLE_FORMATTER"
)
$CommonFlags = @("/nologo", "/W4", "/EHsc", "/std:c++20", "/O2", "/bigobj", "/Zm200", "/Fo$Build\", "/Fd$Build\vc.pdb") + $CommonDefines + $CommonIncludes

function Quote-CmdArg {
    param([Parameter(Mandatory = $true)][string]$Arg)
    $Arg = ($Arg -replace '[\r\n]+', '').Trim()
    $Escaped = $Arg.Replace('"', '\"')
    if ($Escaped.EndsWith("\")) {
        $Escaped += "\"
    }
    return '"' + $Escaped + '"'
}

function Build-ZydisStaticLibrary {
    $ObjDir = Join-Path $Build "zydis_obj"
    New-Item -ItemType Directory -Force $ObjDir | Out-Null

    $ZydisSources = @(
        "third_party\zydis\src\Zydis.c",
        "third_party\zydis\src\Utils.c",
        "third_party\zydis\src\String.c",
        "third_party\zydis\src\SharedData.c",
        "third_party\zydis\src\Segment.c",
        "third_party\zydis\src\Register.c",
        "third_party\zydis\src\Mnemonic.c",
        "third_party\zydis\src\MetaInfo.c",
        "third_party\zydis\src\Decoder.c",
        "third_party\zydis\src\DecoderData.c",
        "third_party\zydis\dependencies\zycore\src\API\Memory.c",
        "third_party\zydis\dependencies\zycore\src\API\Process.c",
        "third_party\zydis\dependencies\zycore\src\API\Synchronization.c",
        "third_party\zydis\dependencies\zycore\src\API\Terminal.c",
        "third_party\zydis\dependencies\zycore\src\API\Thread.c",
        "third_party\zydis\dependencies\zycore\src\Allocator.c",
        "third_party\zydis\dependencies\zycore\src\ArgParse.c",
        "third_party\zydis\dependencies\zycore\src\Bitset.c",
        "third_party\zydis\dependencies\zycore\src\Format.c",
        "third_party\zydis\dependencies\zycore\src\List.c",
        "third_party\zydis\dependencies\zycore\src\String.c",
        "third_party\zydis\dependencies\zycore\src\Vector.c",
        "third_party\zydis\dependencies\zycore\src\Zycore.c"
    )

    $ZydisFlags = @(
        "/nologo",
        "/c",
        "/TC",
        "/O2",
        "/W3",
        "/D_CRT_SECURE_NO_WARNINGS"
    ) + $CommonDefines + $CommonIncludes

    $Objects = @()
    $BatchLines = @(
        "@echo off",
        "call `"$VcVars`" >nul || exit /b 1"
    )
    foreach ($Source in $ZydisSources) {
        $ObjName = ($Source -replace '[:\\/\.]', '_') + ".obj"
        $ObjPath = Join-Path $ObjDir $ObjName
        $Args = $ZydisFlags + @("/Fo:$ObjPath", $Source)
        $BatchLines += 'cl ' + (($Args | ForEach-Object { Quote-CmdArg $_ }) -join ' ') + ' >nul || exit /b 1'
        $Objects += $ObjPath
    }

    $LibPath = Join-Path $Build "zydis_static.lib"
    $BatchLines += 'lib /nologo /OUT:' + (Quote-CmdArg $LibPath) + ' ' + (($Objects | ForEach-Object { Quote-CmdArg $_ }) -join ' ') + ' >nul || exit /b 1'
    $BatchPath = Join-Path $ObjDir "build_zydis.cmd"
    Set-Content -LiteralPath $BatchPath -Value $BatchLines -Encoding ASCII
    cmd /c ("call " + (Quote-CmdArg $BatchPath))
    if ($LASTEXITCODE -ne 0) { throw "Zydis library creation failed with exit code $LASTEXITCODE" }
    return $LibPath
}

Push-Location $Root
try {
    $ZydisLib = [string](Build-ZydisStaticLibrary | Select-Object -Last 1)

    $AnalyzerArgs = @($CommonFlags) + @(
        "src\analyzer.cpp",
        $ZydisLib,
        "/Fe:$Build\StackSentry64.exe",
        "/link", "/CETCOMPAT", "Psapi.lib", "Advapi32.lib", "Bcrypt.lib", "Tdh.lib", "Ole32.lib"
    )

    $MonitorArgs = @($CommonFlags) + @(
        "/LD",
        "src\monitor.cpp",
        "third_party\minhook\src\buffer.c",
        "third_party\minhook\src\hook.c",
        "third_party\minhook\src\trampoline.c",
        "third_party\minhook\src\hde\hde64.c",
        $ZydisLib,
        "/Fe:$Build\CallstackMonitor.dll",
        "/link", "/CETCOMPAT", "/MAP:$Build\CallstackMonitor.map"
    )

    $AnalyzerCommand = 'call "' + $VcVars + '" >nul && cl ' + (($AnalyzerArgs | ForEach-Object { Quote-CmdArg $_ }) -join ' ')
    cmd /c $AnalyzerCommand
    if ($LASTEXITCODE -ne 0) { throw "Analyzer build failed with exit code $LASTEXITCODE" }

    $MonitorCommand = 'call "' + $VcVars + '" >nul && cl ' + (($MonitorArgs | ForEach-Object { Quote-CmdArg $_ }) -join ' ')
    cmd /c $MonitorCommand
    if ($LASTEXITCODE -ne 0) { throw "Monitor build failed with exit code $LASTEXITCODE" }
}
finally {
    Pop-Location
}

Write-Host "[i] Build complete:"
Write-Host "    $Build\StackSentry64.exe"
Write-Host "    $Build\CallstackMonitor.dll"
