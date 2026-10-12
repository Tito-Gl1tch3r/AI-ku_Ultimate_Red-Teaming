# Windows Persistence Checker
# ==========================
# What this script does:
#   - Scans a wide range of registry locations for autorun entries (Run, RunOnce, Winlogon, IFEO, etc.)
#   - Optionally scans all scheduled tasks for suspicious or malicious configurations
#   - Checks referenced files for existence, digital signature, and calculates SHA256 hashes
#   - Assigns a severity level (High, Medium, Low) to each finding based on risk indicators
#   - Outputs results to the console, and can export to JSON or HTML for reporting/sharing
#
# How to use:
#   1. Open PowerShell as Administrator (required for full access)
#   2. Place this script and the 'modules' folder in the same directory
#   3. Run the script with your desired options, for example:
#        .\persistcheck.ps1 -IncludeScheduledTasks -ExportHtml
#   4. Review the output in your console and/or the generated report files
#
# Output:
#   - Console: Color-coded summary and details of all findings
#   - JSON: Machine-readable export for further analysis
#   - HTML: Easy-to-read report for sharing or archiving
#
# The script is read-only and does not change any system settings.
#
# Author: https://github.com/cwsecur1ty

[CmdletBinding()]
param(
    [switch]$ExportJson,
    [string]$OutputPath = "persistence_findings_$(Get-Date -Format 'yyyyMMdd_HHmmss').json",
    [switch]$VerboseOutput,
    [switch]$ExportHtml,
    [string]$HtmlOutputPath = "persistence_report_$(Get-Date -Format 'yyyyMMdd_HHmmss').html",
    [switch]$IncludeScheduledTasks,
    [switch]$DetailedTaskAnalysis
)

# Import the scheduled task scanning module
$modulePath = Join-Path $PSScriptRoot "modules\scheduled_task_scan.ps1"
if (Test-Path $modulePath) {
    . $modulePath
}
else {
    Write-Warning "Scheduled task scanning module not found at: $modulePath"
}

# Function to calculate SHA256 hash of a file
function Get-FileHash {
    param([string]$FilePath)
    
    try {
        if ($FilePath -and (Test-Path $FilePath)) {
            $hash = Get-FileHash -Path $FilePath -Algorithm SHA256
            return $hash.Hash
        }
    }
    catch {
        Write-Warning "Error calculating hash for $FilePath : $_"
    }
    return $null
}

# Function to extract file path from command
function Get-FilePathFromCommand {
    param([string]$Command)
    
    # Remove quotes if present
    $Command = $Command.Trim('"', "'")
    
    # Try to extract the first part of the command (usually the executable)
    if ($Command -match '^([a-zA-Z]:\\[^"\s]+)') {
        return $matches[1]
    }
    elseif ($Command -match '^([^"\s]+)') {
        return $matches[1]
    }
    
    return $null
}

# Function to validate file paths
function Test-FilePath {
    param([string]$Path)
    
    if ($Path -match '^[a-zA-Z]:\\') {
        return Test-Path $Path
    }
    return $false
}

# Function to determine severity level
function Get-SeverityLevel {
    param(
        [string]$Location,
        [string]$Value
    )
    
    # High severity indicators
    $highSeverityPatterns = @(
        'powershell.*bypass',
        'cmd.*\/c',
        'wscript.*\/e',
        'mshta',
        'regsvr32.*\/s',
        'rundll32.*\/s'
    )
    
    # Check for high severity patterns
    foreach ($pattern in $highSeverityPatterns) {
        if ($Value -match $pattern) {
            return "High"
        }
    }
    
    # Medium severity for non-standard locations
    if ($Location -match "RunOnce" -or $Location -match "Image File Execution Options") {
        return "Medium"
    }
    
    return "Low"
}

# Function to resolve file path (handles just the executable name by searching PATH)
function Resolve-FilePath {
    param([string]$FileName)
    if ([System.IO.Path]::IsPathRooted($FileName) -and (Test-Path $FileName)) {
        return $FileName
    }
    # If quoted, remove quotes
    $FileName = $FileName.Trim('"', "'")
    # Try to resolve via PATH and return the first match
    foreach ($dir in $env:PATH.Split(';')) {
        $candidate = Join-Path $dir $FileName
        if (Test-Path $candidate) { return $candidate }
    }
    return $FileName # fallback to original
}

# Function to check digital signature
function Get-DigitalSignatureInfo {
    param([string]$FilePath)
    $result = @{ IsSigned = $false; Signer = $null }
    try {
        if (Test-Path $FilePath) {
            $sig = Get-AuthenticodeSignature -FilePath $FilePath
            if ($sig.Status -eq 'Valid') {
                $result.IsSigned = $true
                $result.Signer = $sig.SignerCertificate.Subject
            }
            elseif ($sig.Status -ne 'NotSigned') {
                $result.IsSigned = $false
                $result.Signer = $sig.Status
            }
        }
    }
    catch { }
    return $result
}

# Function for heuristic checks
function Get-HeuristicFlags {
    param([string]$FilePath)
    $flags = @()
    if ($FilePath) {
        # Suspicious if not in Windows or Program Files
        if ($FilePath -notmatch '^(C:\\Windows|C:\\Program Files)') {
            $flags += 'UnusualLocation'
        }
        # Suspicious if writable by non-admins
        try {
            $acl = Get-Acl $FilePath -ErrorAction Stop
            foreach ($ace in $acl.Access) {
                if ($ace.FileSystemRights -match 'Write' -and $ace.IdentityReference -notmatch 'BUILTIN\\Administrators') {
                    $flags += 'WritableByNonAdmin'
                    break
                }
            }
        }
        catch {}
        # Suspicious if double extension or typosquatting
        if ($FilePath -match '\\[^\\]+\.(exe|bat|cmd|vbs)\.(exe|bat|cmd|vbs)$') {
            $flags += 'DoubleExtension'
        }
        if ($FilePath -match 'svchost|explorer|lsass|csrss|winlogon' -and $FilePath -notmatch 'C:\\Windows') {
            $flags += 'TyposquatName'
        }
    }
    return $flags -join ','
}

# Function to check registry keys and return findings
function Get-RegistryPersistence {
    [CmdletBinding()]
    param()
    
    $findings = @()
    
    # Common registry locations to check
    $registryPaths = @(
        @{
            Path        = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
            Description = "Local Machine Run"
        },
        @{
            Path        = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce"
            Description = "Local Machine RunOnce"
        },
        @{
            Path        = "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
            Description = "Current User Run"
        },
        @{
            Path        = "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce"
            Description = "Current User RunOnce"
        },
        @{
            Path        = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"
            Description = "Winlogon"
        },
        @{
            Path        = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options"
            Description = "Image File Execution Options"
        },
        @{
            Path        = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer\Run"
            Description = "Local Machine Policies Run"
        },
        @{
            Path        = "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer\Run"
            Description = "Current User Policies Run"
        },
        @{
            Path        = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\ShellExecuteHooks"
            Description = "Shell Execute Hooks"
        },
        @{
            Path        = "HKLM:\SOFTWARE\Microsoft\Active Setup\Installed Components"
            Description = "Active Setup"
        }
    )

    foreach ($regPath in $registryPaths) {
        Write-Host "[+] Scanning registry: $($regPath.Description) ($($regPath.Path))" -ForegroundColor Cyan
        try {
            if (Test-Path $regPath.Path) {
                $keys = Get-ItemProperty -Path $regPath.Path -ErrorAction Stop
                if ($keys) {
                    foreach ($key in $keys.PSObject.Properties) {
                        if ($key.Name -notin @('PSPath', 'PSParentPath', 'PSChildName', 'PSProvider', 'PSDrive')) {
                            $value = $key.Value
                            $filePathRaw = Get-FilePathFromCommand -Command $value
                            $filePath = Resolve-FilePath -FileName $filePathRaw
                            $fileExists = ($filePath -and (Test-Path $filePath) -and -not (Test-Path $filePath -PathType Container))
                            $fileHash = if ($fileExists) { Get-FileHash -FilePath $filePath } else { $null }
                            $sigInfo = if ($fileExists) { Get-DigitalSignatureInfo -FilePath $filePath } else { @{ IsSigned = $null; Signer = $null } }
                            $heuristics = if ($fileExists) { Get-HeuristicFlags -FilePath $filePath } else { $null }
                            $severity = Get-SeverityLevel -Location $regPath.Description -Value $value
                            
                            $findings += [PSCustomObject]@{
                                Location       = $regPath.Description
                                RegistryPath   = $regPath.Path
                                Key            = $key.Name
                                Value          = $value
                                Severity       = $severity
                                FileExists     = $fileExists
                                FilePath       = $filePath
                                FileHash       = $fileHash
                                IsSigned       = $sigInfo.IsSigned
                                Signer         = $sigInfo.Signer
                                HeuristicFlags = $heuristics
                                LastWriteTime  = (Get-ItemProperty -Path $regPath.Path).PSLastWriteTime
                                CheckTime      = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
                            }
                        }
                    }
                }
            }
        }
        catch {
            Write-Warning "Error checking $($regPath.Path): $_"
        }
    }

    return $findings
}

# Main execution block
$allFindings = @()

Write-Host "[+] Starting Windows persistence scan..." -ForegroundColor Green

# Get registry persistence findings
$registryFindings = Get-RegistryPersistence
$allFindings += $registryFindings

# Get scheduled task findings if requested
if ($IncludeScheduledTasks) {
    Write-Host "[+] Scanning scheduled tasks..." -ForegroundColor Cyan
    $taskFindings = Get-ScheduledTaskPersistence -Detailed:$DetailedTaskAnalysis -CheckTriggers -CheckActions
    $allFindings += $taskFindings
}

# Export findings based on parameters
if ($ExportJson) {
    $allFindings | ConvertTo-Json -Depth 10 | Out-File $OutputPath
    Write-Host "Findings exported to: $OutputPath"
}

if ($ExportHtml) {
    $html = @"
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
            .high { background-color: #ffcccc; }
            .medium { background-color: #fff2cc; }
            .low { background-color: #ccffcc; }
        </style>
    </head>
    <body>
        <h1>Windows Persistence Analysis Report</h1>
        <table>
            <tr>
                <th>Type</th>
                <th>Name/Path</th>
                <th>Severity</th>
                <th>Details</th>
                <th>Suspicious Flags</th>
            </tr>
"@

    foreach ($finding in $allFindings) {
        $severityClass = $finding.Severity.ToLower()
        $type = if ($finding.TaskName) { "Scheduled Task" } else { "Registry" }
        $name = if ($finding.TaskName) { $finding.TaskName } else { $finding.Key }
        $details = if ($finding.TaskName) { 
            "Last Run: $($finding.LastRunTime)`nNext Run: $($finding.NextRunTime)"
        } else {
            "Value: $($finding.Value)"
        }
        
        $html += @"
            <tr class="$severityClass">
                <td>$type</td>
                <td>$name</td>
                <td>$($finding.Severity)</td>
                <td>$details</td>
                <td>$($finding.SuspiciousFlags -join ', ')</td>
            </tr>
"@
    }

    $html += @"
        </table>
    </body>
    </html>
"@
    $html | Out-File $HtmlOutputPath
    Write-Host "HTML report generated at: $HtmlOutputPath"
}

# Display summary
$highSeverity = ($allFindings | Where-Object { $_.Severity -eq "High" }).Count
$mediumSeverity = ($allFindings | Where-Object { $_.Severity -eq "Medium" }).Count
$lowSeverity = ($allFindings | Where-Object { $_.Severity -eq "Low" }).Count

Write-Host "`nScan Summary:"
Write-Host "------------"
Write-Host "High Severity Findings: $highSeverity"
Write-Host "Medium Severity Findings: $mediumSeverity"
Write-Host "Low Severity Findings: $lowSeverity"
Write-Host "Total Findings: $($allFindings.Count)" 