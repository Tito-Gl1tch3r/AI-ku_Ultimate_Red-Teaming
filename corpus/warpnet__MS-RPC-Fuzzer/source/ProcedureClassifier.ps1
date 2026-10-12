#  Copyright 2025 Remco van der Mei. All Rights Reserved.
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
Classifies RPC procedures by their relationship to NdrContextHandle parameters.
.DESCRIPTION
Determines whether each procedure is an Opener (produces handles), Consumer (requires handles),
Mixed (requires and produces handles), Closer (releases handles), or Independent (no handles).
This classification drives handle-pool population ordering and sequence construction.

Classes:
  Opener      — produces NdrContextHandle output, requires no handle input
  Consumer    — requires NdrContextHandle input, produces no handle output
  Mixed       — requires NdrContextHandle input AND produces a new handle output
  Closer      — requires NdrContextHandle input, name implies release (close/delete/free/...)
  Independent — no NdrContextHandle involvement
#>

function Get-MethodClass {
    <#
    .SYNOPSIS
    Returns the class string for a single MethodInfo object.
    #>
    param(
        [Parameter(Mandatory=$true)]
        [System.Reflection.MethodInfo]$Method
    )

    $handleTypeName = 'NtCoreLib.Ndr.Marshal.NdrContextHandle'

    # Does the method take a handle as input?
    $hasHandleInput = $false
    foreach ($p in $Method.GetParameters()) {
        if ($p.ParameterType.FullName -eq $handleTypeName) {
            $hasHandleInput = $true
            break
        }
    }

    # Does the method produce a handle as output (in any return-type field)?
    $hasHandleOutput = $false
    if ($Method.ReturnType -and $Method.ReturnType -ne [void]) {
        foreach ($f in $Method.ReturnType.GetFields()) {
            if ($f.FieldType.FullName -eq $handleTypeName) {
                $hasHandleOutput = $true
                break
            }
        }
    }

    $name = $Method.Name

    # Closer: consumes a handle and the name implies releasing it.
    # NOTE: Many close/delete/unregister procedures take [in,out] HANDLE* which the NDR
    # layer exposes as a handle in BOTH the input parameters AND the return struct.
    # We intentionally ignore $hasHandleOutput here so that name pattern takes priority
    # over the Mixed classification for these cases.
    $closerPattern = '\b(close|delete|destroy|free|release|remove|unregister|deregister|disconnect)\b'
    if ($hasHandleInput -and ($name -imatch $closerPattern)) {
        return 'Closer'
    }

    if ($hasHandleOutput -and -not $hasHandleInput) { return 'Opener'   }
    if ($hasHandleOutput -and     $hasHandleInput)  { return 'Mixed'    }
    if ($hasHandleInput  -and -not $hasHandleOutput){ return 'Consumer' }
    return 'Independent'
}

function Get-ClassifiedMethods {
    <#
    .SYNOPSIS
    Classifies all methods and returns an array of PSCustomObjects with Method and Class properties.
    #>
    param(
        [Parameter(Mandatory=$true)]
        [System.Reflection.MethodInfo[]]$Methods
    )

    $result = [System.Collections.Generic.List[PSCustomObject]]::new()
    foreach ($m in $Methods) {
        $result.Add([PSCustomObject]@{
            Method = $m
            Name   = $m.Name
            Class  = Get-MethodClass -Method $m
        })
    }
    return $result
}
