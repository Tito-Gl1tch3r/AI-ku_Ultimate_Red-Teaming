#  Copyright 2025 Remco van der Meer. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

# Load the C# ETW monitor (once per session).
# Add-Type cannot replace an already-loaded type, so if the .cs changed since the
# last import we warn the user to restart their PowerShell session.
$csPath = Join-Path $PSScriptRoot "SyscallMonitor.cs"
$_existingType = ([System.Management.Automation.PSTypeName]'SyscallEvent').Type
if ($_existingType) {
    if (-not $_existingType.GetProperty('Endpoint')) {
        Write-Warning "[SyscallMonitor] SyscallMonitor.cs has been updated but the old type is still loaded. Please restart your PowerShell session to pick up the changes."
    }
} else {
    Add-Type -Path $csPath
}

# Module-scoped monitor instance
$script:_SyscallMonitor = $null

<#
.SYNOPSIS
Start monitoring kernel File and Registry events for the fuzzer canary string.
.DESCRIPTION
Creates an ETW real-time trace session that captures every kernel file I/O and
registry operation whose payload contains the canary. Requires administrator
privileges.  Results are retrieved with Get-SyscallEvents or Stop-SyscallMonitor.
.PARAMETER Canary
The canary prefix to filter on (default: "incendiumrocks_").
.EXAMPLE
Start-SyscallMonitor -Canary "incendiumrocks_"
#>
function Start-SyscallMonitor {
    param(
        [string]$Canary = "incendiumrocks_"
    )

    if ($script:_SyscallMonitor) {
        Write-Warning "[SyscallMonitor] Already running. Stopping previous instance."
        Stop-SyscallMonitor | Out-Null
    }

    $script:_SyscallMonitor = [SyscallMonitor]::new("RpcFuzzerSyscallMonitor")

    try {
        $script:_SyscallMonitor.Start($Canary)
        Write-Host "[+] SyscallMonitor started  (canary: '$Canary')" -ForegroundColor Cyan
    }
    catch {
        $script:_SyscallMonitor.Dispose()
        $script:_SyscallMonitor = $null
        Write-Host "[!] SyscallMonitor failed to start: $_" -ForegroundColor Red
        throw
    }
}

<#
.SYNOPSIS
Stop the syscall monitor and return all captured events.
.DESCRIPTION
Stops the ETW trace session and returns an array of SyscallEvent objects sorted
by timestamp.  The monitor is disposed after calling this function.
.EXAMPLE
$events = Stop-SyscallMonitor
$events | Format-Table Timestamp, ProcessName, Operation, Path
#>
function Stop-SyscallMonitor {
    if (-not $script:_SyscallMonitor) {
        Write-Warning "[SyscallMonitor] No monitor is running."
        return @()
    }

    $events = $script:_SyscallMonitor.Stop()
    $script:_SyscallMonitor.Dispose()
    $script:_SyscallMonitor = $null

    Write-Host "[+] SyscallMonitor stopped  ($($events.Count) events captured)" -ForegroundColor Cyan
    return $events
}

<#
.SYNOPSIS
Get events captured so far without stopping the monitor.
.EXAMPLE
Get-SyscallEvents | Where-Object { $_.Operation -eq 'Create' }
#>
<#
.SYNOPSIS
Register the canary values generated for an RPC call so syscall events can be
attributed to the originating procedure.
.DESCRIPTION
Scans the parameter array for string (and Byte[]) values that contain the canary
prefix and registers each with the monitor.  Call this right before Method.Invoke().
Safe to call when no monitor is running (no-op).
.PARAMETER RpcServer
Name/path of the RPC server DLL.
.PARAMETER RpcInterface
Interface UUID string.
.PARAMETER Procedure
Procedure/method name.
.PARAMETER Params
The parameter array about to be passed to Method.Invoke.  Can be a flat array of
values (DefaultFuzzer) or an array of objects with a .Value property (SortedFuzzer).
.PARAMETER Canary
The canary prefix used during input generation.
#>
function Find-SyscallCanaryValues {
    param($Value, [string]$Canary, [int]$Depth = 0)
    if ($Depth -gt 10 -or $null -eq $Value) { return }

    if ($Value -is [string]) {
        if ($Value.Contains($Canary)) { $Value }
        return
    }
    if ($Value -is [byte[]]) {
        try {
            $str = [System.Text.Encoding]::UTF8.GetString($Value)
            if ($str.Contains($Canary)) { $str }
        } catch {}
        return
    }
    if ($Value -is [System.Array]) {
        foreach ($elem in $Value) {
            Find-SyscallCanaryValues -Value $elem -Canary $Canary -Depth ($Depth + 1)
        }
        return
    }

    $t = $Value.GetType()

    # NdrEmbeddedPointer<T> exposes a public GetValue() method — use it directly
    # instead of relying on private field reflection.
    if ($t.IsGenericType -and $t.Name -like 'NdrEmbeddedPointer*') {
        try {
            $inner = $Value.GetValue()
            if ($null -ne $inner) {
                Find-SyscallCanaryValues -Value $inner -Canary $Canary -Depth ($Depth + 1)
            }
        } catch {}
        return
    }

    # General complex type: scan fields and public readable properties
    $bf = [System.Reflection.BindingFlags]'Public,NonPublic,Instance'
    try {
        foreach ($f in $t.GetFields($bf)) {
            try {
                $fv = $f.GetValue($Value)
                if ($null -ne $fv) {
                    Find-SyscallCanaryValues -Value $fv -Canary $Canary -Depth ($Depth + 1)
                }
            } catch {}
        }
    } catch {}
    try {
        foreach ($prop in $t.GetProperties([System.Reflection.BindingFlags]'Public,Instance')) {
            if ($prop.CanRead -and $prop.GetIndexParameters().Length -eq 0) {
                try {
                    $pv = $prop.GetValue($Value)
                    if ($null -ne $pv) {
                        Find-SyscallCanaryValues -Value $pv -Canary $Canary -Depth ($Depth + 1)
                    }
                } catch {}
            }
        }
    } catch {}
}

function Register-SyscallCall {
    param(
        [string]$RpcServer,
        [string]$RpcServerPath,
        [string]$RpcInterface,
        [string]$Procedure,
        [string]$Endpoint,
        $Params,
        [string]$Canary
    )

    if (-not $script:_SyscallMonitor) { return }
    if (-not $Params) { return }

    foreach ($p in $Params) {
        # SortedFuzzer wraps values in objects with a .Value property
        $val = if ($p.PSObject.Properties.Name -contains 'Value') { $p.Value } else { $p }

        # SortedFuzzer stores Value = ,$value (single-element array); unwrap it
        if ($val -is [System.Array] -and $val.Count -eq 1) { $val = $val[0] }

        foreach ($s in (Find-SyscallCanaryValues -Value $val -Canary $Canary)) {
            $script:_SyscallMonitor.RegisterCall($RpcServer, $RpcServerPath, $RpcInterface, $Procedure, $Endpoint, $s)
        }
    }
}

<#
.SYNOPSIS
Drain and display high-privilege syscall alerts in red on the console, and
incrementally flush new events to JSON files.
.DESCRIPTION
Call this after each Method.Invoke() to get real-time visibility when the fuzzer's
canary string triggers a File or Registry operation under NT AUTHORITY\SYSTEM,
NETWORK SERVICE, or LOCAL SERVICE.  Also appends any new events captured since the
last call to Syscalls.json and HighPrivSyscalls.json so that results are preserved
even if fuzzing is interrupted.  No-op when no monitor is running.
.PARAMETER OutPath
Output directory for JSON files.
#>
function Show-SyscallAlerts {
    param(
        [string]$OutPath
    )
    if (-not $script:_SyscallMonitor) { return }

    $alerts = $script:_SyscallMonitor.TakeAlerts()
    foreach ($a in $alerts) {
        $proc = if ($a.RpcProcedure) { $a.RpcProcedure } else { "Unknown" }
        $rewriteTag = if ($a.PathRewritten) { " [PATH REWRITTEN by RPC server]" } else { "" }
        Write-Host "[!] HIGH-PRIV SYSCALL: $proc - $($a.Provider):$($a.Operation): $($a.Path) - $($a.UserName)$rewriteTag" -ForegroundColor Red
    }

    # Incrementally flush new events to disk
    if ($OutPath) {
        Flush-SyscallEvents -OutPath $OutPath
    }
}

<#
.SYNOPSIS
Append newly captured syscall events to the JSON output files.
.DESCRIPTION
Drains only the events captured since the last flush, reads the existing JSON
files from disk, appends the new entries, and writes back.  This ensures that
if fuzzing is stopped mid-run all results collected so far are on disk.
#>
function Flush-SyscallEvents {
    param(
        [Parameter(Mandatory)]
        [string]$OutPath
    )
    if (-not $script:_SyscallMonitor) { return }

    $newEvents = $script:_SyscallMonitor.TakeNewEvents()
    if ($newEvents.Count -eq 0) { return }

    $highPrivSids = @("S-1-5-18", "S-1-5-19", "S-1-5-20")

    # --- Syscalls.json (append) ---
    $jsonFile = Join-Path $OutPath "Syscalls.json"
    $newEntries = $newEvents | ForEach-Object {
        [ordered]@{
            Timestamp     = $_.Timestamp.ToString("yyyy-MM-dd HH:mm:ss.fffffff")
            ProcessId     = $_.ProcessId
            ProcessName   = $_.ProcessName
            ThreadId      = $_.ThreadId
            UserSid       = $_.UserSid
            UserName      = $_.UserName
            Provider      = $_.Provider
            Operation     = $_.Operation
            EventId       = $_.EventId
            Path          = $_.Path
            PathRewritten = $_.PathRewritten
            RpcServer     = $_.RpcServer
            RpcServerPath = $_.RpcServerPath
            RpcInterface  = $_.RpcInterface
            RpcProcedure  = $_.RpcProcedure
            Endpoint      = $_.Endpoint
        }
    }

    if (Test-Path $jsonFile) {
        $existing = @(Get-Content -Path $jsonFile -Raw | ConvertFrom-Json)
    } else {
        $existing = @()
    }
    $merged = @($existing) + @($newEntries)
    $merged | ConvertTo-Json -Depth 5 | Set-Content -Path $jsonFile -Encoding utf8

    # --- HighPrivSyscalls.json (append high-priv subset) ---
    $hpNew = $newEvents | Where-Object { $_.UserSid -and $highPrivSids -contains $_.UserSid }
    if ($hpNew) {
        $hpFile = Join-Path $OutPath "HighPrivSyscalls.json"
        $hpEntries = $hpNew | ForEach-Object {
            [ordered]@{
                Timestamp     = $_.Timestamp.ToString("yyyy-MM-dd HH:mm:ss.fffffff")
                ProcessId     = $_.ProcessId
                ProcessName   = $_.ProcessName
                ThreadId      = $_.ThreadId
                UserSid       = $_.UserSid
                UserName      = $_.UserName
                Provider      = $_.Provider
                Operation     = $_.Operation
                EventId       = $_.EventId
                Path          = $_.Path
                PathRewritten = $_.PathRewritten
                RpcServer     = $_.RpcServer
                RpcServerPath = $_.RpcServerPath
                RpcInterface  = $_.RpcInterface
                RpcProcedure  = $_.RpcProcedure
                Endpoint      = $_.Endpoint
            }
        }
        if (Test-Path $hpFile) {
            $hpExisting = @(Get-Content -Path $hpFile -Raw | ConvertFrom-Json)
        } else {
            $hpExisting = @()
        }
        $hpMerged = @($hpExisting) + @($hpEntries)
        $hpMerged | ConvertTo-Json -Depth 5 | Set-Content -Path $hpFile -Encoding utf8
    }
}

<#
.SYNOPSIS
Invoke an RPC method with a timeout.
.DESCRIPTION
Runs the method on a background thread and throws a TimeoutException if it
does not complete within the specified number of milliseconds.
.PARAMETER Method
The MethodInfo to invoke.
.PARAMETER Client
The RPC client instance.
.PARAMETER Params
Parameter array to pass to the method.
.PARAMETER TimeoutMs
Timeout in milliseconds (default 5000).
#>
function Invoke-RpcWithTimeout {
    param(
        [System.Reflection.MethodInfo]$Method,
        $Client,
        [object[]]$Params,
        [int]$TimeoutMs = 5000
    )
    return [RpcInvokeHelper]::InvokeWithTimeout($Method, $Client, $Params, $TimeoutMs)
}

function Get-SyscallEvents {
    if (-not $script:_SyscallMonitor) {
        Write-Warning "[SyscallMonitor] No monitor is running."
        return @()
    }
    return $script:_SyscallMonitor.GetEvents()
}

<#
.SYNOPSIS
Export captured syscall events to a JSON file.
.DESCRIPTION
Writes the supplied SyscallEvent array to a JSON file using the same output
directory structure as the rest of the fuzzer.  Typically called automatically
by the fuzzer when -MonitorSyscalls is set.
.PARAMETER Events
Array of SyscallEvent objects (from Stop-SyscallMonitor or Get-SyscallEvents).
.PARAMETER OutPath
Directory to write the Syscalls.json file into.
.EXAMPLE
Export-SyscallEvents -Events $events -OutPath .\output
#>
function Export-SyscallEvents {
    param(
        [Parameter(Mandatory)]
        $Events,
        [Parameter(Mandatory)]
        [string]$OutPath
    )

    if ($Events.Count -eq 0) {
        Write-Host "[*] SyscallMonitor: no events to export." -ForegroundColor DarkGray
        return
    }

    $jsonFile = Join-Path $OutPath "Syscalls.json"

    # Build an ordered list of objects for clean JSON output
    $exportList = $Events | ForEach-Object {
        [ordered]@{
            Timestamp     = $_.Timestamp.ToString("yyyy-MM-dd HH:mm:ss.fffffff")
            ProcessId     = $_.ProcessId
            ProcessName   = $_.ProcessName
            ThreadId      = $_.ThreadId
            UserSid       = $_.UserSid
            UserName      = $_.UserName
            Provider      = $_.Provider
            Operation     = $_.Operation
            EventId       = $_.EventId
            Path          = $_.Path
            PathRewritten = $_.PathRewritten
            RpcServer     = $_.RpcServer
            RpcServerPath = $_.RpcServerPath
            RpcInterface  = $_.RpcInterface
            RpcProcedure  = $_.RpcProcedure
            Endpoint      = $_.Endpoint
        }
    }

    $exportList | ConvertTo-Json -Depth 5 | Set-Content -Path $jsonFile -Encoding utf8
    Write-Host "[+] SyscallMonitor: exported $($Events.Count) events to $jsonFile" -ForegroundColor Cyan

    # Also export high-privilege events to a separate file for quick triage
    $highPrivSids = @("S-1-5-18", "S-1-5-19", "S-1-5-20")
    $highPrivEvents = $Events | Where-Object { $_.UserSid -and $highPrivSids -contains $_.UserSid }
    if ($highPrivEvents) {
        $hpFile = Join-Path $OutPath "HighPrivSyscalls.json"
        $hpList = $highPrivEvents | ForEach-Object {
            [ordered]@{
                Timestamp     = $_.Timestamp.ToString("yyyy-MM-dd HH:mm:ss.fffffff")
                ProcessId     = $_.ProcessId
                ProcessName   = $_.ProcessName
                ThreadId      = $_.ThreadId
                UserSid       = $_.UserSid
                UserName      = $_.UserName
                Provider      = $_.Provider
                Operation     = $_.Operation
                EventId       = $_.EventId
                Path          = $_.Path
                PathRewritten = $_.PathRewritten
                RpcServer     = $_.RpcServer
                RpcServerPath = $_.RpcServerPath
                RpcInterface  = $_.RpcInterface
                RpcProcedure  = $_.RpcProcedure
                Endpoint      = $_.Endpoint
            }
        }
        $hpList | ConvertTo-Json -Depth 5 | Set-Content -Path $hpFile -Encoding utf8
        Write-Host "[+] SyscallMonitor: exported $(@($highPrivEvents).Count) high-privilege events to $hpFile" -ForegroundColor Red
    }
}
