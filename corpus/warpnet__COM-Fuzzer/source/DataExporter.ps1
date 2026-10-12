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
Exports Allowed fuzzed input to a json file
.DESCRIPTION
This function exports Allowed fuzzed input to a json file
#>
function Export-AllowsFuzzedInput {
    param (
        [string]$ComServerName,
        [string]$ComCLSID, 
        [string]$ComInterface,
        [string]$ProcedureName, 
        [string]$ProcedureDefinition,
        [string]$Service,
        [string]$FuzzInput, 
        [string]$Output,
        [string]$windowsMessage,
        [string]$OutPath
    )

    $jsonFile = Join-Path $OutPath "Allowed.json"

    # Create new procedure object
    $newEntry = [PSCustomObject]@{
        ProcedureName       = $ProcedureName
        ProcedureDefinition = $ProcedureDefinition
        FuzzInput           = $FuzzInput
        Output              = $Output
        WindowsMessage      = $windowsMessage
        Service             = $Service
    }

    # Load or initialize the base object
    if (Test-Path $jsonFile) {
        $jsonRaw = Get-Content $jsonFile -Raw
        $jsonData = $jsonRaw | ConvertFrom-Json
    } else {
        $jsonData = @{}
    }

    # Convert to hashtable if needed
    if ($jsonData -isnot [hashtable]) {
        $ht = @{}
        foreach ($prop in $jsonData.PSObject.Properties) {
            $interfaceMap = @{}
            foreach ($iface in $prop.Value.PSObject.Properties) {
                $interfaceMap[$iface.Name] = @($iface.Value | ForEach-Object { $_ })
            }
            $ht[$prop.Name] = $interfaceMap
        }
        $jsonData = $ht
    }

    # Ensure the CLSID exists
    if (-not $jsonData.ContainsKey($ComCLSID)) {
        $jsonData[$ComCLSID] = @{}
    }

    # Ensure the interface exists
    if (-not $jsonData[$ComCLSID].ContainsKey($ComInterface)) {
        $jsonData[$ComCLSID][$ComInterface] = @()
    }

    # Append new procedure to the interface
    $jsonData[$ComCLSID][$ComInterface] += $newEntry

    # Save JSON with full depth
    $jsonData | ConvertTo-Json -Depth 10 | Set-Content -Path $jsonFile -Encoding UTF8
}

<#
.SYNOPSIS
Exports Access Denied fuzzed input to a json file
.DESCRIPTION
This function exports Access Denied fuzzed input to a json file
#>
function Export-AccessDeniedInput {
    param (
        [string]$ComServerName,
        [string]$ComCLSID, 
        [string]$ComInterface,
        [string]$ProcedureName, 
        [string]$ProcedureDefinition,
        [string]$Service,
        [string]$FuzzInput, 
        [string]$Output,
        [string]$windowsMessage,
        [string]$OutPath
    )

    $jsonFile = Join-Path $OutPath "Denied.json"

    # Create new procedure object
    $newEntry = [PSCustomObject]@{
        ProcedureName       = $ProcedureName
        ProcedureDefinition = $ProcedureDefinition
        FuzzInput           = $FuzzInput
        Output              = $Output
        WindowsMessage      = $windowsMessage
        Service             = $Service
    }

    # Load or initialize the base object
    if (Test-Path $jsonFile) {
        $jsonRaw = Get-Content $jsonFile -Raw
        $jsonData = $jsonRaw | ConvertFrom-Json
    } else {
        $jsonData = @{}
    }

    # Convert to hashtable if needed
    if ($jsonData -isnot [hashtable]) {
        $ht = @{}
        foreach ($prop in $jsonData.PSObject.Properties) {
            $interfaceMap = @{}
            foreach ($iface in $prop.Value.PSObject.Properties) {
                $interfaceMap[$iface.Name] = @($iface.Value | ForEach-Object { $_ })
            }
            $ht[$prop.Name] = $interfaceMap
        }
        $jsonData = $ht
    }

    # Ensure the CLSID exists
    if (-not $jsonData.ContainsKey($ComCLSID)) {
        $jsonData[$ComCLSID] = @{}
    }

    # Ensure the interface exists
    if (-not $jsonData[$ComCLSID].ContainsKey($ComInterface)) {
        $jsonData[$ComCLSID][$ComInterface] = @()
    }

    # Append new procedure to the interface
    $jsonData[$ComCLSID][$ComInterface] += $newEntry

    # Save JSON with full depth
    $jsonData | ConvertTo-Json -Depth 10 | Set-Content -Path $jsonFile -Encoding UTF8
}

<#
.SYNOPSIS
Exports Error fuzzed input to a json file
.DESCRIPTION
This function exports Error fuzzed input to a json file
#>
function Export-ErrorFuzzedInput {
    param (
        [string]$MethodName, 
        [string]$ComCLSID,
        [string]$ComInterface,
        [string]$Endpoint, 
        [string]$ProcedureName, 
        [string]$Service,
        [string]$MethodDefinition, 
        [string]$FuzzInput,
        [string]$Errormessage,
        [string]$OutPath
    )
    begin {
        $methodEntry = [ordered]@{
            MethodName       = $MethodName
            Endpoint         = $Endpoint
            ProcedureName    = $ProcedureName
            MethodDefinition = $MethodDefinition
            Service          = $Service
            FuzzInput        = $FuzzInput
            Errormessage     = $Errormessage
        }

        # Specify target output file
        $jsonFile = "$OutPath\Error.json"

        # Check if the directory exists, if not, create it
        $directoryPath = Split-Path -Path $jsonFile
        if (-not (Test-Path $directoryPath)) {
            New-Item -Path $directoryPath -ItemType Directory | Out-Null
        }
    }
    process {
        # Read existing JSON or initialize a new hashtable
        if (Test-Path $jsonFile) {
            $jsonContent = Get-Content -Path $jsonFile -Raw
            $existingData = $jsonContent | ConvertFrom-Json -AsHashtable
        } else {
            $existingData = @{}
        }

        # Ensure the ComCLSID exists in the data
        if (-not $existingData.ContainsKey($ComCLSID)) {
            $existingData[$ComCLSID] = @{}
        }

        # Get the server's interface data
        $serverData = $existingData[$ComCLSID]

        # Ensure the ComInterface exists in the server's data
        if (-not $serverData.ContainsKey($ComInterface)) {
            $serverData[$ComInterface] = @()
        }

        # Add the method entry to the interface's array
        $serverData[$ComInterface] += $methodEntry

        # Update the server data in the existing data
        $existingData[$ComCLSID] = $serverData
    }
    end {
        # Convert the data to JSON and save
        $existingData | ConvertTo-Json -Depth 10 | Set-Content -Path $jsonFile -Encoding utf8
    }
}