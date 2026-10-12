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

<#
.SYNOPSIS
Manages a pool of acquired NdrContextHandle values for stateful RPC fuzzing.
.DESCRIPTION
Opaque RPC context handles must be obtained from "Open"-type procedures before they
can be used as inputs to stateful consumer procedures. This module provides a handle
pool that is populated during a pre-fuzzing acquisition pass and queried by parameter
generators when they encounter NdrContextHandle input parameters. Stale handles are
evicted after repeated failures.
#>

$script:NdrContextHandleTypeName = 'NtCoreLib.Ndr.Marshal.NdrContextHandle'

function New-HandlePool {
    <#
    .SYNOPSIS
    Creates an empty handle pool with lifecycle tracking.
    #>
    return [PSCustomObject]@{
        # List of PSCustomObject{Handle, OpenerName, Fails}
        Entries  = [System.Collections.Generic.List[PSCustomObject]]::new()
        MaxFails = 3
    }
}

function Add-HandleToPool {
    <#
    .SYNOPSIS
    Adds a valid NdrContextHandle to the pool, ignoring nulls and duplicates.
    #>
    param(
        [Parameter(Mandatory=$true)]$Pool,
        $Handle,
        [string]$OpenerName = ''
    )
    if ($null -eq $Pool -or $null -eq $Handle) { return }
    try {
        $nullHandle = [System.Activator]::CreateInstance([NtCoreLib.Ndr.Marshal.NdrContextHandle])
        if ($Handle.Equals($nullHandle)) { return }
        $key = $Handle.ToString()
        $exists = $Pool.Entries | Where-Object { $_.Handle.ToString() -eq $key }
        if (-not $exists) {
            $entry = [PSCustomObject]@{ Handle = $Handle; OpenerName = $OpenerName; Fails = 0 }
            $Pool.Entries.Add($entry)
            Write-Verbose ("[HandlePool] Added handle from {0}: {1}" -f $OpenerName, $key)
        }
    } catch { }
}

function Test-HandleIsNull {
    <#
    .SYNOPSIS
    Returns $true when the handle is null or zero-initialized.
    #>
    param($Handle)
    if ($null -eq $Handle) { return $true }
    try {
        $nullHandle = [System.Activator]::CreateInstance([NtCoreLib.Ndr.Marshal.NdrContextHandle])
        return $Handle.Equals($nullHandle)
    } catch { return $true }
}

function Get-HandleFromPool {
    <#
    .SYNOPSIS
    Returns a random non-evicted handle from the pool, or $null if the pool is empty.
    #>
    param($Pool)
    if ($null -eq $Pool) { return $null }
    $valid = @($Pool.Entries | Where-Object { $_.Fails -lt $Pool.MaxFails })
    if ($valid.Count -eq 0) { return $null }
    return $valid[(Get-Random -Minimum 0 -Maximum $valid.Count)].Handle
}

function Get-HandleEntriesFromPool {
    <#
    .SYNOPSIS
    Returns all valid pool entries (used by the sequence fuzzer to enumerate handles with opener names).
    #>
    param($Pool)
    if ($null -eq $Pool) { return @() }
    return @($Pool.Entries | Where-Object { $_.Fails -lt $Pool.MaxFails })
}

function Register-HandleFailure {
    <#
    .SYNOPSIS
    Increments the failure counter for a handle; evicts it when MaxFails is reached.
    #>
    param($Pool, $Handle)
    if ($null -eq $Pool -or $null -eq $Handle) { return }
    try {
        $key = $Handle.ToString()
        $entry = $Pool.Entries | Where-Object { $_.Handle.ToString() -eq $key } | Select-Object -First 1
        if ($entry) {
            $entry.Fails++
            if ($entry.Fails -ge $Pool.MaxFails) {
                $Pool.Entries.Remove($entry) | Out-Null
                Write-Verbose ("[HandlePool] Evicted stale handle after {0} failures: {1}" -f $Pool.MaxFails, $key)
            }
        }
    } catch { }
}

function Reset-HandlePool {
    <#
    .SYNOPSIS
    Clears all handles from the pool (call after reconnect or service restart).
    #>
    param($Pool)
    if ($null -eq $Pool) { return }
    $Pool.Entries.Clear()
}

function Invoke-HandleAcquisition {
    <#
    .SYNOPSIS
    Calls Opener procedures with seed inputs to populate the handle pool before fuzzing.
    .DESCRIPTION
    Tries each opener procedure with well-known RPC string seeds and a fixed set of small integer
    values that cover common access-flag bitmasks (0, 1, 2, 4, 8, …).  Pure Openers (no handle
    input) are tried first.  Mixed procedures (handle input + handle output) are tried in a second
    pass only after the pool already contains at least one handle.
    Any NdrContextHandle values returned from successful calls are added to the pool.
    #>
    param(
        [Parameter(Mandatory=$true)]$Client,
        [Parameter(Mandatory=$true)][PSCustomObject[]]$ClassifiedMethods,
        [Parameter(Mandatory=$true)]$HandlePool,
        [string]$Canary,
        [string]$Mode,
        [string]$remote_host,
        [string]$StringBinding = '',
        [string]$RpcServer,
        [string]$RpcServerPath,
        [string]$RpcInterface,
        $IntInput,
        $StringInput,
        $GuidInput,
        $minStrLen  = 5,  $maxStrLen  = 20,
        $minIntSize = 0,  $maxIntSize = 10,
        $minByteArrLen = 1, $maxByteArrLen = 16
    )

    $handleTypeName = $script:NdrContextHandleTypeName

    # Split into pure openers (no handle input) and mixed (handle input + handle output).
    # Pure openers are tried unconditionally; mixed are tried only after the pool has handles.
    $pureOpeners = @($ClassifiedMethods | Where-Object { $_.Class -eq 'Opener' })
    $mixedOpeners = @($ClassifiedMethods | Where-Object { $_.Class -eq 'Mixed' })
    $totalOpeners = $pureOpeners.Count + $mixedOpeners.Count

    if ($totalOpeners -eq 0) {
        Write-Verbose '[HandlePool] No opener procedures found; skipping acquisition.'
        return
    }

    Write-Host ("[*] Handle acquisition pass: {0} opener(s) found." -f $totalOpeners) -ForegroundColor Cyan

    # Resolve effective target host for seeding opener string parameters.
    $isNcalrpc = ($StringBinding -imatch '^ncalrpc:')
    $effectiveHost = $remote_host
    if (-not $effectiveHost -and -not $isNcalrpc -and $StringBinding -match '^[^:]+:([^[\\\s]+)') {
        $h = $Matches[1].Trim()
        if ($h) { $effectiveHost = $h }
    }
    if (-not $effectiveHost) { $effectiveHost = $env:COMPUTERNAME }

    if ($isNcalrpc -and -not $remote_host) {
        Write-Host ("[*] ncalrpc binding detected. If opener procedures need a remote server name, pass -remote_host <IP/hostname>.") -ForegroundColor Yellow
    }
    Write-Verbose ("[HandlePool] Effective seed host: {0}" -f $effectiveHost)

    # String seeds for the first (server-name) string parameter of opener procedures
    $strSeeds = [System.Collections.Generic.List[string]]::new()
    $strSeeds.Add('')
    $strSeeds.Add($null)
    $strSeeds.Add('\\localhost')
    $strSeeds.Add('\\localhost\,')
    $strSeeds.Add(',XcvMonitor Local Port')
    if ($effectiveHost) {
        $strSeeds.Add("\\$effectiveHost")
        $strSeeds.Add("\\$effectiveHost\,")
        $strSeeds.Add("\\$effectiveHost\print`$")
    }
    if ($remote_host -and $remote_host -ne $effectiveHost) {
        $strSeeds.Add("\\$remote_host")
        $strSeeds.Add("\\$remote_host\,")
    }

    # Integer seeds covering common access-flag bitmasks and small ordinals.
    # If the caller supplied an explicit -IntInput use only that value; otherwise try the full set.
    $intSeeds = if ($null -ne $IntInput -and $IntInput -ne 0) {
        @([int32]$IntInput)
    } else {
        @(1, 0, 2, 4, 8, 3, 7, 0x10, 0x100, 0x20000000, 0x02000000)
    }

    $nullHandle    = [System.Activator]::CreateInstance([NtCoreLib.Ndr.Marshal.NdrContextHandle])
    $emptyComplexList = @{ Type = @(); Value = @() }

    # Helper: invoke one opener attempt and harvest any returned handles.
    # Acquisition parameter strategy (mirrors user's manually-confirmed working calls):
    #   - NdrContextHandle : null handle (openers) or pool handle (mixed)
    #   - 1st String       : $seed (server/printer name)
    #   - Remaining Strings: empty string  (NOT the server-name seed — that breaks pDatatype etc.)
    #   - 1st Int32        : $intSeed (access flags candidate)
    #   - Complex structs  : zero-initialized via Activator.CreateInstance
    #                        (fuzzed structs corrupt DevModeContainer-like params → retval=87)
    #   - Everything else  : Format-SortedParameterType with no StringInput/IntInput override
    $tryOpenMethod = {
        param($entry, $seed, $intSeed, $poolHandle)
        $method     = $entry.Method
        $methodName = $method.Name
        $params     = $method.GetParameters()
        try {
            $invokeArgs = [System.Collections.Generic.List[object]]::new()
            $firstStr   = $true
            $firstInt   = $true

            foreach ($p in $params) {
                if ($p.ParameterType.FullName -eq $handleTypeName) {
                    $invokeArgs.Add($(if ($poolHandle) { $poolHandle } else { $nullHandle }))
                } elseif ($p.ParameterType -eq [System.String] -and $firstStr) {
                    # First string: server/printer name seed
                    $invokeArgs.Add($seed)
                    $firstStr = $false
                } elseif ($p.ParameterType -eq [System.String]) {
                    # Subsequent strings: empty (not the server-name seed — that corrupts datatype params)
                    $invokeArgs.Add('')
                } elseif ($p.ParameterType -eq [System.Int32] -and $firstInt) {
                    # First int: access-flags candidate from the seed set
                    $invokeArgs.Add([int32]$intSeed)
                    $firstInt = $false
                } elseif (Test-IsComplexType $p.ParameterType) {
                    # Complex structs: zero-initialize — fuzzed DevModeContainer-like structs
                    # produce inconsistent size/pointer fields and cause retval=87 silently
                    try { $invokeArgs.Add([System.Activator]::CreateInstance($p.ParameterType)) }
                    catch { $invokeArgs.Add($null) }
                } else {
                    $val = Format-SortedParameterType -Type $p.ParameterType -Canary $Canary `
                        -Mode $Mode -remote_host $remote_host `
                        -InterfaceComplexParameters $emptyComplexList `
                        -minStrLen $minStrLen -maxStrLen $maxStrLen `
                        -minIntSize $minIntSize -maxIntSize $maxIntSize `
                        -minByteArrLen $minByteArrLen -maxByteArrLen $maxByteArrLen
                    $invokeArgs.Add($val)
                }
            }

            Register-SyscallCall -RpcServer $RpcServer -RpcServerPath $RpcServerPath `
                -RpcInterface $RpcInterface -Procedure $methodName `
                -Endpoint $StringBinding -Params $invokeArgs -Canary $Canary
            $result = $method.Invoke($Client, $invokeArgs.ToArray())
            if ($result -and $result.PSObject.Properties) {
                foreach ($prop in $result.PSObject.Properties) {
                    if ($prop.TypeNameOfValue -like "*NdrContextHandle*") {
                        Add-HandleToPool -Pool $HandlePool -Handle $prop.Value -OpenerName $methodName
                    }
                }
            }
            # Log non-zero retval silently (retval!=0 means null handle — no exception is thrown)
            if ($result -and $result.PSObject.Properties['retval'] -and $result.retval -ne 0) {
                Write-Verbose ("[HandlePool] {0} seed='{1}' int={2} retval={3} (no handle)" -f $methodName, $seed, $intSeed, $result.retval)
            }
        } catch {
            Write-Verbose ("[HandlePool] {0} seed='{1}' int={2} failed: {3}" -f $methodName, $seed, $intSeed, $_)
        }
    }

    # Pass 1: pure openers (no handle input) — try all string × int seed combinations
    foreach ($entry in $pureOpeners) {
        foreach ($seed in $strSeeds) {
            foreach ($intSeed in $intSeeds) {
                & $tryOpenMethod $entry $seed $intSeed $null
            }
        }
    }

    # Pass 2: mixed openers (need an existing handle to produce a new one) — only if pool non-empty
    if ($mixedOpeners.Count -gt 0 -and $HandlePool.Entries.Count -gt 0) {
        foreach ($entry in $mixedOpeners) {
            $poolHandle = Get-HandleFromPool -Pool $HandlePool
            foreach ($seed in $strSeeds) {
                foreach ($intSeed in $intSeeds) {
                    & $tryOpenMethod $entry $seed $intSeed $poolHandle
                }
            }
        }
    }

    Write-Host ("[*] Handle pool populated: {0} handle(s) available." -f $HandlePool.Entries.Count) -ForegroundColor Cyan
}
