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
Formats parameter types and calls input generator for values
.DESCRIPTION
This function formats the parameter type and calls the input generator for values
#>
Function Format-ParameterType {
    param (
        [Parameter(Mandatory = $true)]
        [System.Type]$Type,
        $UNC,
        $Canary,
        $StringInput,
        $IntInput,
        $GuidInput,
        $minStrLen,
        $maxStrLen,
        $minIntSize,
        $maxIntSize,
        $minByteArrLen,
        $maxByteArrLen
    )

    process {
        if ($Type -eq [System.Byte[]]) {
            return ,(CallInputGenerator -param $Type -canary $Canary -minByteArrLen $minByteArrLen -maxByteArrLen $maxByteArrLen)

        } elseif ($Type.IsArray) {
            $elementType = $Type.GetElementType()

            # Clone and filter splatting params to only known parameters of Format-ParameterType
            $newParams = @{}
            $validParams = (Get-Command Format-ParameterType).Parameters.Keys
            foreach ($key in $PSBoundParameters.Keys) {
                if ($validParams -contains $key -and $key -ne "Type") {
                    $newParams[$key] = $PSBoundParameters[$key]
                }
            }
            return ,@(Format-ParameterType -Type $elementType @newParams)

        } elseif ($Type -eq [System.String]) {
            if ($StringInput) {
                return $StringInput
            } elseif ($UNC) {
                $randomString = CallInputGenerator -param $Type -canary $Canary -minStrLen $minStrLen -maxStrLen $maxStrLen
                return "\\" + $UNC + "\test\" + $randomString
            } else {
                return (CallInputGenerator -param $Type -canary $Canary -minStrLen $minStrLen -maxStrLen $maxStrLen)
            }

        } elseif ($Type -eq [System.Int32]) {
            if ($IntInput) {
                return [int32]$IntInput
            } else {
                $randomInt = CallInputGenerator -param $Type -canary $Canary -minIntSize $minIntSize -maxIntSize $maxIntSize
                return [int32]$randomInt
            }

        } elseif ($Type -eq [System.Byte]) {
            return [byte]0x41

        } elseif ($Type -eq [System.Guid] -and $GuidInput) {
            return [System.Guid]$GuidInput

        } elseif ($Type -eq [NtApiDotNet.Ndr.Marshal.INdrComObject]) {
            return

        } else {
            # Default fallback for other types
            return [System.Activator]::CreateInstance($Type)
        }
    }
}

<#
.SYNOPSIS
Process each parameter and format it
.DESCRIPTION
This function takes a Method as input and processes each parameter with a value
#>
Function Format-DefaultParameters {
    param (
        [Parameter(Mandatory = $true)]
        $ComMethod,
        $UNC,
        [string]$Canary = "incendiumrocks",
        $StringInput,
        $IntInput,
        $GuidInput,
        $minStrLen = 5,
        $maxStrLen = 20,
        $minIntSize = -2147483648,
        $maxIntSize = 2147483647,
        $minByteArrLen,
        $maxByteArrLen
    )

    process {
        $definition = $ComMethod

        # Extract the parameter list from within the parentheses
        if ($definition -match '\((.*)\)') {
            $paramList = $matches[1]

            # Trim and handle empty param list
            if ([string]::IsNullOrWhiteSpace($paramList)) {
                return @()  # No parameters
            }

            # Define known mappings from strings to .NET types
            $typeMap = @{
                'int'      = [System.Int32]
                'int32'    = [System.Int32]
                'string'   = [System.String]
                'byte'     = [System.Byte]
                'byte[]'   = [System.Byte[]]
                'guid'     = [System.Guid]
                'bool'     = [System.Boolean]
            }

            $paramValues = @()

            # Split parameters and resolve their types
            $paramList -split ',' | ForEach-Object {
                $param = $_.Trim()
                if ($param -match '^\s*(\S+)\s+\S+$') {
                    $paramTypeName = $matches[1].ToLower()

                    if ($typeMap.ContainsKey($paramTypeName)) {
                        $resolvedType = $typeMap[$paramTypeName]
                    } else {
                        $resolvedType = $paramTypeName
                    }
                    
                    $value = Format-ParameterType -Type $resolvedType `
                        -UNC $UNC `
                        -canary $Canary `
                        -StringInput $StringInput `
                        -IntInput $IntInput `
                        -GuidInput $GuidInput `
                        -minStrLen $minStrLen `
                        -maxStrLen $maxStrLen `
                        -minIntSize $minIntSize `
                        -maxIntSize $maxIntSize `
                        -minByteArrLen $minByteArrLen `
                        -maxByteArrLen $maxByteArrLen

                    $paramValues += ,$value
                } else {
                    Write-Verbose "Could not parse parameter segment: '$_'"
                }
            }

            return ,$paramValues
        } else {
            throw "Unable to parse parameter list from method definition: $definition"
        }
    }
}

<#
.SYNOPSIS
Takes a parameter and calls the input generator
.DESCRIPTION
This function calls the input generator for a parameter value
#>
function CallInputGenerator {
    Param (
        $param,
        [string]$Canary = "incendiumrocks",
        $minStrLen,
        $maxStrLen,
        $minIntSize = -2147483648,
        $maxIntSize = 2147483647,
        $minByteArrLen,
        $maxByteArrLen        
    ) 
    # $iterations is a global variable from Invoke-Fuzzer scope, so it should be accessible here
    $value = GenerateInput -paramType $param -count $iterations -canary $Canary -minStrLen $minStrLen -maxStrLen $maxStrLen -minIntSize $minIntSize -maxIntSize $maxIntSize -minByteArrLen $minByteArrLen -maxByteArrLen $maxByteArrLen
    return $value
}

<#
.SYNOPSIS
Generates fuzz input for a parameter
.DESCRIPTION
This function generates fuzz input for a parameter
#>
function GenerateInput {
    param (
        [string]$paramType,
        [string]$Canary = "incendiumrocks",
        $minStrLen = 5,
        $maxStrLen = 20,
        $minIntSize = -2147483648,
        $maxIntSize = 2147483647,
        $minByteArrLen = 100,
        $maxByteArrLen = 1000
    )
    
    # Convert PSCustomObject to Hashtable (if needed)
    if ($existingData -isnot [hashtable]) {
        $hashTable = @{}
        foreach ($property in $existingData.PSObject.Properties) {
            $hashTable[$property.Name] = $property.Value
        }
        $existingData = $hashTable
    }

    # Initialize new data array
    $newData = @()
    # Create a function for this that takes parameters for minimum/maximum length of String
    if ($paramType -eq "string") {
        if ($NoSpecialChars) {
            $characters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        } else {
            $characters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()~-=+?><,;][{}_|"
        }
        $stringLength = Get-Random -Minimum $minStrLen -Maximum $maxStrLen
        $randomString = -join (Get-Random -InputObject $characters.ToCharArray() -Count $stringLength)
        $newData += ($Canary + "_$randomString")
        return $newData
    }   

    # Generate random 32-bit Integer
    if ($paramType -eq "int") {
        for ($i = 0; $i -lt $iterations; $i++) { 
            $newData = Get-Random -Minimum $minIntSize -Maximum $maxIntSize
            return $newData
        }
    }

    if ($paramType -eq "byte") {
        for ($i = 0; $i -lt $iterations; $i++) {
            $characters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()~-=+?><,.;][{}_|"
            $stringLength = Get-Random -Minimum $minByteArrLen -Maximum $maxByteArrLen
            $randomString = -join (Get-Random -InputObject $characters.ToCharArray() -Count $stringLength)
            $newData += ($Canary + "_$randomString")          
            $byteArrStr = ,([System.Text.Encoding]::UTF8.GetBytes($newData))
            return ,$byteArrStr
        }
    }
}