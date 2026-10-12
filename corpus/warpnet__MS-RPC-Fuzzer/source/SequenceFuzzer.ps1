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
Sequence-replay fuzzer that pairs opener procedures with consumer procedures.
.DESCRIPTION
Unlike the default and sorted fuzzers that treat each procedure independently, the
sequence fuzzer explicitly constructs (opener → consumer) call chains:

  1. Classify all procedures as Opener/Consumer/Mixed/Closer/Independent.
  2. Run openers with seed inputs to acquire valid NdrContextHandle values.
  3. For each (opener, consumer) pair, replay the sequence $Iterations times:
       a. Call the opener (with seed inputs) to obtain a fresh handle.
       b. Call the consumer with that handle plus fuzzed values for all other params.
       c. Record the full sequence — both steps — in Sequences.json.
  4. Procedures classified as Closer are skipped (blacklisted by default).
  5. Independent procedures are fuzzed once per consumer loop without an opener step.

Output:
  Sequences.json  — every attempted sequence with opener/worker inputs and results.
  Error.json      — worker calls that fail with a valid handle (real findings).
  NullHandle.json — worker calls that fail because no handle could be acquired.
  Allowed.json    — worker calls that succeed.
#>
function Invoke-SequenceFuzzer {
    param (
        $JsonFilePath,
        $Iterations,
        $Canary,
        $Mode,
        $remote_host,
        [Parameter(Mandatory=$true)]
        $OutPath,
        $StringInput,
        $intInput,
        $guidInput,
        $inputParameters,
        $minStrLen     = 5,
        $maxStrLen     = 20,
        $minIntSize    = 0,
        $maxIntSize    = 100,
        $minByteArrLen = 100,
        $maxByteArrLen = 1000,
        $Procedure,
        $Blacklist,
        $DbgHelpPath,
        [switch]$MonitorSyscalls
    )

    $ClientEntries = Get-Content -Path $JsonFilePath | ConvertFrom-Json

    # DbgHelp initialisation (same pattern as other fuzzers)
    if (Test-Path "$env:systemdrive\Program Files (x86)\Windows Kits\10\Debuggers\x64\dbghelp.dll") {
        Set-GlobalSymbolResolver -DbgHelpPath "$env:systemdrive\Program Files (x86)\Windows Kits\10\Debuggers\x64\dbghelp.dll"
        Write-Host "[+] dbghelp.dll successfully initialized" -ForegroundColor Green
    } elseif ($DbgHelpPath) {
        try {
            Set-GlobalSymbolResolver -DbgHelpPath $DbgHelpPath
            Write-Host "[+] dbghelp.dll successfully initialized" -ForegroundColor Green
        } catch {
            Write-Host "[!] dbghelp.dll not found, please provide path using -DbgHelpPath" -ForegroundColor Red
            return
        }
    } else {
        $continueWithoutDbg = Read-Host "[!] Could not find dbghelp.dll, continue? [Y/n] > "
        if ($continueWithoutDbg -eq 'n') { return }
    }

    if (-not (Test-Path $OutPath)) { New-Item -ItemType Directory -Path $OutPath | Out-Null }

    if ($Blacklist) { $Blacklist = Get-Content $Blacklist }

    Write-Host "[+] Starting sequence fuzzer..." -ForegroundColor Green

    # Start syscall monitoring if requested
    if ($MonitorSyscalls) {
        Start-SyscallMonitor -Canary $Canary
    }

    $handleTypeName = 'NtCoreLib.Ndr.Marshal.NdrContextHandle'
    $nullHandle     = [System.Activator]::CreateInstance([NtCoreLib.Ndr.Marshal.NdrContextHandle])

    # Well-known seed strings for opener calls — built lazily per stringbinding below
    $script:globalStrSeeds = $null  # will be populated per stringbinding

    foreach ($rpcServer in $ClientEntries.PSObject.Properties) {
        $serverName = $rpcServer.Name
        $interfaces = $rpcServer.Value

        try {
            $rpcServerObj = $serverName | Get-RpcServer -ErrorAction Stop
        } catch {
            if ($_ -match "ParsePeFile") {
                $rpcServerObj = $serverName | Get-RpcServer -IgnoreSymbols
            } else {
                Write-Verbose "[!] Could not get RPC server for $serverName"
            }
        }
        if (-not $rpcServerObj) {
            Write-Host "[!] Failed to retrieve RPC server for: $serverName" -ForegroundColor Red
            continue
        }

        $rpcServerName = Split-Path -Path $serverName -Leaf

        foreach ($interfaceEntry in $interfaces) {
            $interfaceId   = $interfaceEntry.InterfaceId
            $stringBindings = $interfaceEntry.StringBindings

            $rpcInterface = $rpcServerObj | Where-Object { $_.InterfaceId -eq $interfaceId }
            if (-not $rpcInterface) {
                Write-Host "[!] Interface $interfaceId not found in $serverName" -ForegroundColor Yellow
                continue
            }

            $service = if ($rpcInterface.ServiceName -ne '') { $rpcInterface.ServiceName } else { 'N.a.' }

            try {
                $client = $rpcInterface | Get-RpcClient
            } catch {
                Write-Verbose "[!] Could not get RPC client for interface $interfaceId"
                continue
            }
            if (-not $client) { continue }

            foreach ($stringbinding in $stringBindings) {
                Connect-Client -client $client -stringbinding $stringbinding

                $allMethods = $client.GetType().GetMethods() |
                    Where-Object { $_.IsPublic -and $_.DeclaringType -eq $client.GetType() }

                if ($Procedure) {
                    $allMethods = $allMethods | Where-Object { $_.Name -in @($Procedure) }
                }

                # Phase 1: classify
                $classified = Get-ClassifiedMethods -Methods $allMethods

                # Shared state (used by Format-SortedParameterType via dynamic scoping)
                $ComplexList = @{ Type = @(); Value = @() }
                $HandlePool  = New-HandlePool

                # Phase 2: handle acquisition (uses all methods, not filtered by -Procedure)
                $allMethodsForAcq = $client.GetType().GetMethods() |
                    Where-Object { $_.IsPublic -and $_.DeclaringType -eq $client.GetType() }
                $classifiedForAcq = Get-ClassifiedMethods -Methods $allMethodsForAcq
                Invoke-HandleAcquisition -Client $client -ClassifiedMethods $classifiedForAcq `
                    -HandlePool $HandlePool -Canary $Canary -Mode $Mode -remote_host $remote_host `
                    -StringBinding $stringbinding `
                    -RpcServer $rpcServerName -RpcServerPath $serverName -RpcInterface $interfaceId `
                    -IntInput $intInput -StringInput $StringInput -GuidInput $guidInput `
                    -minStrLen $minStrLen -maxStrLen $maxStrLen `
                    -minIntSize $minIntSize -maxIntSize $maxIntSize `
                    -minByteArrLen $minByteArrLen -maxByteArrLen $maxByteArrLen

                # Build seed list for sequence replay: resolve host from stringbinding automatically
                $seqEffectiveHost = $remote_host
                if (-not $seqEffectiveHost -and $stringbinding -match '^[^:]+:([^[\\\s]+)') {
                    $h = $Matches[1].Trim()
                    if ($h) { $seqEffectiveHost = $h }
                }
                if (-not $seqEffectiveHost) { $seqEffectiveHost = $env:COMPUTERNAME }
                $strSeeds = [System.Collections.Generic.List[string]]::new()
                $strSeeds.Add('')
                $strSeeds.Add($null)
                $strSeeds.Add('\\localhost')
                $strSeeds.Add('\\localhost\,')
                $strSeeds.Add(',XcvMonitor Local Port')
                if ($seqEffectiveHost) {
                    $strSeeds.Add("\\$seqEffectiveHost")
                    $strSeeds.Add("\\$seqEffectiveHost\,")
                    $strSeeds.Add("\\$seqEffectiveHost\print`$")
                }
                if ($remote_host -and $remote_host -ne $seqEffectiveHost) {
                    $strSeeds.Add("\\$remote_host")
                    $strSeeds.Add("\\$remote_host\,")
                }

                $openers   = @($classified | Where-Object { $_.Class -in @('Opener','Mixed') })
                $consumers = @($classified | Where-Object { $_.Class -in @('Consumer','Mixed','Independent') })

                # Limit consumer list to user-specified procedure if set
                if ($Procedure) {
                    $consumers = @($consumers | Where-Object { $_.Name -in @($Procedure) })
                }

                $endpoint  = $client.Endpoint.ToString().replace("\u", "*u")
                $totalSeqs = [math]::Max(1, $openers.Count) * $consumers.Count * $Iterations
                $done      = 0

                foreach ($consumerEntry in $consumers) {
                    $workerMethod = $consumerEntry.Method
                    $workerName   = $consumerEntry.Name

                    if ($Blacklist -contains $workerName) { continue }
                    if ($workerName -imatch '\b(close|delete|destroy|free|release|remove|unregister)\b') { continue }

                    # Determine which openers to pair with this consumer.
                    # Independent procedures have no handle inputs, so they run once without an opener.
                    $openerLoop = if ($consumerEntry.Class -eq 'Independent') { @($null) } else { $openers + @($null) }

                    foreach ($openerEntry in $openerLoop) {
                        for ($iter = 0; $iter -lt $Iterations; $iter++) {
                            $done++
                            $pct = [math]::Round(($done / $totalSeqs) * 100, 1)
                            Write-Progress -Activity "Sequence Fuzzer" `
                                -Status ("Opener={0} Worker={1} iter={2}" -f $(if($openerEntry){'('+$openerEntry.Name+')'}else{'(none)'}), $workerName, $iter) `
                                -PercentComplete ([math]::Min($pct, 100))

                            # --- Step 1: run opener to get a fresh handle for this sequence ---
                            $openerName  = '(none)'
                            $openerInput = '(none)'
                            $sequenceHandle = $nullHandle

                            if ($openerEntry) {
                                $openerMethod = $openerEntry.Method
                                $openerName   = $openerEntry.Name
                                $openerArgs   = [System.Collections.Generic.List[object]]::new()
                                $openerInputParts = [System.Collections.Generic.List[string]]::new()
                                $firstStr     = $true

                                # Pick a seed string for the opener
                                $seed = $strSeeds[(Get-Random -Minimum 0 -Maximum $strSeeds.Count)]

                                foreach ($p in $openerMethod.GetParameters()) {
                                    if ($p.ParameterType.FullName -eq $handleTypeName) {
                                        $openerArgs.Add($nullHandle)
                                        $openerInputParts.Add("$($p.Name)=(null handle)")
                                    } elseif ($p.ParameterType -eq [System.String] -and $firstStr -and $seed -ne '') {
                                        $openerArgs.Add($seed)
                                        $openerInputParts.Add("$($p.Name)=$seed")
                                        $firstStr = $false
                                    } else {
                                        $val = Format-SortedParameterType -Type $p.ParameterType `
                                            -Canary $Canary -Mode $Mode -remote_host $remote_host `
                                            -InterfaceComplexParameters $ComplexList `
                                            -minStrLen $minStrLen -maxStrLen $maxStrLen `
                                            -minIntSize $minIntSize -maxIntSize $maxIntSize `
                                            -minByteArrLen $minByteArrLen -maxByteArrLen $maxByteArrLen
                                        $openerArgs.Add($val)
                                        $openerInputParts.Add("$($p.Name)=$val")
                                    }
                                }
                                $openerInput = $openerInputParts -join '; '

                                Register-SyscallCall -RpcServer $rpcServerName -RpcServerPath $serverName -RpcInterface $interfaceId -Procedure $openerName -Endpoint $stringbinding -Params $openerArgs -Canary $Canary

                                try {
                                    $openerResult = Invoke-RpcWithTimeout -Method $openerMethod -Client $client -Params $openerArgs.ToArray()
                                    Show-SyscallAlerts -OutPath $OutPath
                                    if ($openerResult -and $openerResult.PSObject.Properties) {
                                        foreach ($prop in $openerResult.PSObject.Properties) {
                                            if ($prop.TypeNameOfValue -like "*NdrContextHandle*") {
                                                $candidate = $prop.Value
                                                if (-not (Test-HandleIsNull -Handle $candidate)) {
                                                    $sequenceHandle = $candidate
                                                    Add-HandleToPool -Pool $HandlePool -Handle $candidate -OpenerName $openerName
                                                }
                                            }
                                            # Feed other return values into ComplexList
                                            if ($prop.Value -notmatch '00000000-0000-0000-0000-000000000000') {
                                                $ComplexList["Type"] += $prop.TypeNameOfValue.ToString()
                                                $ComplexList["Value"] += $prop.Value
                                            }
                                        }
                                    }
                                } catch {
                                    if ($_ -match "timed out") {
                                        Write-Host "[TIMEOUT] Opener $openerName did not return within 5s — skipping" -ForegroundColor Yellow
                                        Disconnect-RpcClient $client
                                        Connect-Client -client $client -stringbinding $stringbinding
                                    } else {
                                        Write-Verbose ("[Sequence] Opener {0} failed: {1}" -f $openerName, $_)
                                    }
                                    # If opener fails, try a handle from the pool (may still work)
                                    $pooled = Get-HandleFromPool -Pool $HandlePool
                                    if ($pooled) { $sequenceHandle = $pooled }
                                }
                            }

                            # --- Step 2: fuzz the worker with the handle from step 1 ---
                            $workerArgs  = [System.Collections.Generic.List[object]]::new()
                            $workerInputParts = [System.Collections.Generic.List[string]]::new()
                            $workerHandleIsNull = (Test-HandleIsNull -Handle $sequenceHandle)

                            foreach ($p in $workerMethod.GetParameters()) {
                                if ($p.ParameterType.FullName -eq $handleTypeName) {
                                    $workerArgs.Add($sequenceHandle)
                                    $workerInputParts.Add("$($p.Name)=$(if($workerHandleIsNull){'(null)'}else{'(handle)'})")
                                } else {
                                    $val = Format-SortedParameterType -Type $p.ParameterType `
                                        -Canary $Canary -Mode $Mode -remote_host $remote_host `
                                        -InterfaceComplexParameters $ComplexList `
                                        -minStrLen $minStrLen -maxStrLen $maxStrLen `
                                        -minIntSize $minIntSize -maxIntSize $maxIntSize `
                                        -minByteArrLen $minByteArrLen -maxByteArrLen $maxByteArrLen
                                    $workerArgs.Add($val)
                                    $workerInputParts.Add("$($p.Name)=$val")
                                }
                            }
                            $workerInput  = ($workerInputParts -join '; ') -replace '"', ''
                            $workerDef    = $workerMethod.ToString()

                            # Log sequence attempt
                            $logEntry = "SEQUENCE: $openerName -> $workerName`nOpenerInput: $openerInput`nWorkerInput: $workerInput`n---`n"
                            $logEntry | Out-File -FilePath "$OutPath\log.txt" -Append -Encoding utf8

                            if ($sleep) { Start-Sleep -Seconds $sleep }

                            Register-SyscallCall -RpcServer $rpcServerName -RpcServerPath $serverName -RpcInterface $interfaceId -Procedure $workerName -Endpoint $stringbinding -Params $workerArgs -Canary $Canary

                            try {
                                $workerResult = Invoke-RpcWithTimeout -Method $workerMethod -Client $client -Params $workerArgs.ToArray()
                                Show-SyscallAlerts -OutPath $OutPath

                                # Collect output
                                $workerOutput = ''
                                $winMsg       = 'No Windows Message'
                                if ($workerResult -and $workerResult.PSObject.Properties.MemberType) {
                                    $workerResult.PSObject.Properties | ForEach-Object {
                                        if ($_.Value -notmatch '00000000-0000-0000-0000-000000000000') {
                                            $ComplexList["Type"] += $_.TypeNameOfValue.ToString()
                                            $ComplexList["Value"] += $_.Value
                                        }
                                        if ($_.TypeNameOfValue -like "*NdrContextHandle*") {
                                            Add-HandleToPool -Pool $HandlePool -Handle $_.Value -OpenerName $workerName
                                        }
                                    }
                                    $workerOutput = ($workerResult | Get-Member -MemberType Properties |
                                        ForEach-Object { "$($_.Name): $($workerResult.$($_.Name))" } |
                                        Out-String).Trim() -replace '"', ''
                                    try {
                                        $retval = $workerResult.retval
                                        $winMsg = [System.ComponentModel.Win32Exception]::new([int]$retval).Message
                                        $winMsg = ("{0:X}: {1}" -f ($retval -band 0xFFFFFFFF), $winMsg)
                                    } catch { }
                                } else {
                                    $workerOutput = "$workerResult" -replace '"', ''
                                }

                                Export-SequenceResult -RpcServerName $rpcServerName `
                                    -RpcInterface $interfaceId `
                                    -Endpoint $endpoint `
                                    -Service $service `
                                    -OpenerProcedure $openerName `
                                    -OpenerInput ($openerInput -replace '"', '') `
                                    -WorkerProcedure $workerName `
                                    -WorkerMethodDefinition $workerDef `
                                    -WorkerInput $workerInput `
                                    -WorkerOutput $workerOutput `
                                    -WorkerWindowsMessage $winMsg `
                                    -Result 'Success' `
                                    -Errormessage '' `
                                    -OutPath $OutPath

                                Export-AllowsFuzzedInput -MethodName $workerName `
                                    -RpcServerName $rpcServerName `
                                    -RpcInterface $interfaceId `
                                    -Endpoint $endpoint `
                                    -ProcedureName $workerName `
                                    -MethodDefinition $workerDef `
                                    -Service $service `
                                    -FuzzInput $workerInput `
                                    -Output $workerOutput `
                                    -windowsMessage $winMsg `
                                    -OutPath $OutPath

                            } catch {
                                $errMsg = ($_ -replace '"', '')
                                Export-SequenceResult -RpcServerName $rpcServerName `
                                    -RpcInterface $interfaceId `
                                    -Endpoint $endpoint `
                                    -Service $service `
                                    -OpenerProcedure $openerName `
                                    -OpenerInput ($openerInput -replace '"', '') `
                                    -WorkerProcedure $workerName `
                                    -WorkerMethodDefinition $workerDef `
                                    -WorkerInput $workerInput `
                                    -WorkerOutput '' `
                                    -WorkerWindowsMessage '' `
                                    -Result 'Error' `
                                    -Errormessage $errMsg `
                                    -OutPath $OutPath

                                if ($_ -match "Access is denied") {
                                    Export-AccessDeniedInput -MethodName $workerName `
                                        -RpcServerName $rpcServerName `
                                        -RpcInterface $interfaceId `
                                        -Endpoint $endpoint `
                                        -ProcedureName $workerName `
                                        -MethodDefinition $workerDef `
                                        -Service $service `
                                        -FuzzInput $workerInput `
                                        -OutPath $OutPath

                                } elseif ($_ -match "not connected" -or $_ -match "pipe is in the disconnected state") {
                                    Reset-HandlePool -Pool $HandlePool
                                    try { Disconnect-RpcClient $client } catch { }
                                    Connect-Client -client $client -stringbinding $stringbinding
                                    Invoke-HandleAcquisition -Client $client -ClassifiedMethods $classified `
                                        -HandlePool $HandlePool -Canary $Canary -Mode $Mode -remote_host $remote_host `
                                        -StringBinding $stringbinding `
                                        -RpcServer $rpcServerName -RpcServerPath $serverName -RpcInterface $interfaceId `
                                        -minStrLen $minStrLen -maxStrLen $maxStrLen `
                                        -minIntSize $minIntSize -maxIntSize $maxIntSize `
                                        -minByteArrLen $minByteArrLen -maxByteArrLen $maxByteArrLen
                                    Export-ErrorFuzzedInput -MethodName $workerName `
                                        -RpcServerName $rpcServerName `
                                        -RpcInterface $interfaceId `
                                        -Endpoint $endpoint `
                                        -ProcedureName $workerName `
                                        -MethodDefinition $workerDef `
                                        -Service $service `
                                        -FuzzInput $workerInput `
                                        -Errormessage $errMsg `
                                        -OutPath $OutPath

                                } elseif ($_ -match "stub received bad data") {
                                    if ($workerHandleIsNull) {
                                        Export-NullHandleInput -MethodName $workerName `
                                            -RpcServerName $rpcServerName `
                                            -RpcInterface $interfaceId `
                                            -Endpoint $endpoint `
                                            -ProcedureName $workerName `
                                            -MethodDefinition $workerDef `
                                            -Service $service `
                                            -FuzzInput $workerInput `
                                            -Errormessage $errMsg `
                                            -OutPath $OutPath
                                    } else {
                                        Register-HandleFailure -Pool $HandlePool -Handle $sequenceHandle
                                        Export-ErrorFuzzedInput -MethodName $workerName `
                                            -RpcServerName $rpcServerName `
                                            -RpcInterface $interfaceId `
                                            -Endpoint $endpoint `
                                            -ProcedureName $workerName `
                                            -MethodDefinition $workerDef `
                                            -Service $service `
                                            -FuzzInput $workerInput `
                                            -Errormessage $errMsg `
                                            -OutPath $OutPath
                                    }
                                } elseif ($_ -match "timed out") {
                                    Write-Host "[TIMEOUT] $workerName did not return within 5s — skipping" -ForegroundColor Yellow
                                    Disconnect-RpcClient $client
                                    Connect-Client -client $client -stringbinding $stringbinding
                                } elseif ($_ -match "C0000701" -or $_ -match "ALPC message requested is no longer available") {
                                    # ALPC crash: the service behind this RPC server was terminated
                                    $serviceName = if ($service -and $service -ne "N.a.") { $service } else { $rpcServerName }
                                    Write-Host "[CRASH] $workerName ($workerInput) > crashed service '$serviceName'" -ForegroundColor White
                                    Export-CrashInput -MethodName $workerName `
                                        -RpcServerName $rpcServerName `
                                        -RpcServerPath $serverName `
                                        -RpcInterface $interfaceId `
                                        -Endpoint $endpoint `
                                        -StringBinding $stringbinding `
                                        -ProcedureName $workerName `
                                        -MethodDefinition $workerDef `
                                        -Service $serviceName `
                                        -FuzzInput $workerInput `
                                        -Errormessage $errMsg `
                                        -OutPath $OutPath
                                } else {
                                    Export-ErrorFuzzedInput -MethodName $workerName `
                                        -RpcServerName $rpcServerName `
                                        -RpcInterface $interfaceId `
                                        -Endpoint $endpoint `
                                        -ProcedureName $workerName `
                                        -MethodDefinition $workerDef `
                                        -Service $service `
                                        -FuzzInput $workerInput `
                                        -Errormessage $errMsg `
                                        -OutPath $OutPath
                                }
                            }
                        }
                    }
                }

                try { Disconnect-RpcClient $client } catch { }
            }
        }
    }

    # Stop syscall monitoring and do a final flush to capture any buffered trailing events
    if ($MonitorSyscalls) {
        Stop-SyscallMonitor | Out-Null
        Flush-SyscallEvents -OutPath $OutPath
    }

    Write-Host "[+] Sequence fuzzing complete." -ForegroundColor Green
    Write-Host "[+] Results in: $OutPath\Sequences.json, Allowed.json, Error.json, NullHandle.json" -ForegroundColor Green
}
