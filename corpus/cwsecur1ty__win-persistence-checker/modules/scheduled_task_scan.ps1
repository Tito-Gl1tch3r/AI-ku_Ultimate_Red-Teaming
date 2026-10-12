# Scheduled Task Scanner Module
# ============================
#
# What this module does:
#   - Scans all scheduled tasks on the system (optionally including disabled tasks)
#   - Analyses task triggers, actions, and settings for suspicious patterns
#   - Flags tasks that use known malicious or unusual commands, locations, or configurations
#   - Assigns a severity level (High, Medium, Low) to each finding based on risk indicators
#   - Provides output in PowerShell objects, JSON, CSV, or HTML report formats
#
# How to use:
#   1. Dot-source this script in your PowerShell session or import it as part of a larger script:
#        . ./modules/scheduled_task_scan.ps1
#   2. Call Get-ScheduledTaskPersistence to scan for suspicious tasks:
#        $findings = Get-ScheduledTaskPersistence -CheckTriggers -CheckActions
#   3. Review the $findings array for details on each task and its risk level.
#   4. Optionally, export the results:
#        Export-ScheduledTaskFindings -Findings $findings -OutputPath 'tasks.json' -Format 'JSON'
#
# Output:
#   Each finding includes task name, path, state, last/next run, suspicious flags, severity, and more.
#   The module is safe to run and does not modify any system settings.
#
# Author: https://github.com/cwsecur1ty

function Get-ScheduledTaskPersistence {
    [CmdletBinding()]
    param(
        [switch]$Detailed,
        [switch]$IncludeDisabled,
        [string[]]$ExcludePaths = @(),
        [switch]$CheckTriggers,
        [switch]$CheckActions
    )

    $findings = @()
    $suspiciousPatterns = @(
        'powershell.*bypass',
        'cmd.*\/c',
        'wscript.*\/e',
        'mshta',
        'regsvr32.*\/s',
        'rundll32.*\/s',
        '\.(vbs|js|wsf|hta|ps1|bat|cmd)$'
    )

    # Get all scheduled tasks
    $tasks = Get-ScheduledTask | Where-Object {
        if (-not $IncludeDisabled -and $_.State -eq 'Disabled') {
            return $false
        }
        if ($ExcludePaths.Count -gt 0) {
            return -not ($ExcludePaths | Where-Object { $_.TaskPath -like $_ })
        }
        return $true
    }

    foreach ($task in $tasks) {
        $taskInfo = Get-ScheduledTaskInfo -TaskName $task.TaskName -TaskPath $task.TaskPath
        $taskDefinition = $task | Get-ScheduledTask

        # Basic task information
        $finding = @{
            TaskName = $task.TaskName
            TaskPath = $task.TaskPath
            State = $task.State
            LastRunTime = $taskInfo.LastRunTime
            LastTaskResult = $taskInfo.LastTaskResult
            NextRunTime = $taskInfo.NextRunTime
            NumberOfMissedRuns = $taskInfo.NumberOfMissedRuns
            Severity = "Low"
            SuspiciousFlags = @()
            Triggers = @()
            Actions = @()
            Settings = @{}
        }

        # Check triggers if requested
        if ($CheckTriggers) {
            foreach ($trigger in $taskDefinition.Triggers) {
                $triggerInfo = @{
                    Type = $trigger.GetType().Name
                    Enabled = $trigger.Enabled
                    StartBoundary = $trigger.StartBoundary
                    EndBoundary = $trigger.EndBoundary
                    ExecutionTimeLimit = $trigger.ExecutionTimeLimit
                }
                $finding.Triggers += $triggerInfo

                # Check for suspicious trigger patterns
                if ($trigger.GetType().Name -eq "LogonTrigger") {
                    $finding.SuspiciousFlags += "LogonTrigger"
                }
                if ($trigger.GetType().Name -eq "IdleTrigger") {
                    $finding.SuspiciousFlags += "IdleTrigger"
                }
            }
        }

        # Check actions if requested
        if ($CheckActions) {
            foreach ($action in $taskDefinition.Actions) {
                $actionInfo = @{
                    Type = $action.GetType().Name
                    Execute = $action.Execute
                    Arguments = $action.Arguments
                    WorkingDirectory = $action.WorkingDirectory
                }
                $finding.Actions += $actionInfo

                # Check for suspicious patterns in actions
                foreach ($pattern in $suspiciousPatterns) {
                    if ($action.Execute -match $pattern -or $action.Arguments -match $pattern) {
                        $finding.Severity = "High"
                        $finding.SuspiciousFlags += "SuspiciousCommand"
                    }
                }

                # Check for non-standard locations
                if ($action.Execute -notmatch '^(C:\\Windows|C:\\Program Files)') {
                    $finding.SuspiciousFlags += "NonStandardLocation"
                }
            }
        }

        # Check task settings
        $finding.Settings = @{
            AllowDemandStart = $taskDefinition.Settings.AllowDemandStart
            RestartOnFailure = $taskDefinition.Settings.RestartOnFailure
            RunOnlyIfIdle = $taskDefinition.Settings.RunOnlyIfIdle
            RunOnlyIfNetworkAvailable = $taskDefinition.Settings.RunOnlyIfNetworkAvailable
            StartWhenAvailable = $taskDefinition.Settings.StartWhenAvailable
            StopIfGoingOnBatteries = $taskDefinition.Settings.StopIfGoingOnBatteries
            WakeToRun = $taskDefinition.Settings.WakeToRun
        }

        # Check for suspicious settings
        if ($taskDefinition.Settings.RestartOnFailure) {
            $finding.SuspiciousFlags += "RestartOnFailure"
        }
        if ($taskDefinition.Settings.RunOnlyIfIdle) {
            $finding.SuspiciousFlags += "RunOnlyIfIdle"
        }
        if ($taskDefinition.Settings.StartWhenAvailable) {
            $finding.SuspiciousFlags += "StartWhenAvailable"
        }

        # Update severity based on suspicious flags
        if ($finding.SuspiciousFlags.Count -gt 2) {
            $finding.Severity = "High"
        }
        elseif ($finding.SuspiciousFlags.Count -gt 0) {
            $finding.Severity = "Medium"
        }

        $findings += $finding
    }

    return $findings
}

function Export-ScheduledTaskFindings {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]
        [array]$Findings,
        
        [Parameter(Mandatory=$true)]
        [string]$OutputPath,
        
        [ValidateSet('JSON', 'CSV', 'HTML')]
        [string]$Format = 'JSON'
    )

    switch ($Format) {
        'JSON' {
            $Findings | ConvertTo-Json -Depth 10 | Out-File $OutputPath
        }
        'CSV' {
            $Findings | Export-Csv -Path $OutputPath -NoTypeInformation
        }
        'HTML' {
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
                <h1>Scheduled Task Analysis Report</h1>
                <table>
                    <tr>
                        <th>Task Name</th>
                        <th>Path</th>
                        <th>Severity</th>
                        <th>Last Run</th>
                        <th>Next Run</th>
                        <th>Suspicious Flags</th>
                    </tr>
"@
            foreach ($finding in $Findings) {
                $severityClass = $finding.Severity.ToLower()
                $html += @"
                    <tr class="$severityClass">
                        <td>$($finding.TaskName)</td>
                        <td>$($finding.TaskPath)</td>
                        <td>$($finding.Severity)</td>
                        <td>$($finding.LastRunTime)</td>
                        <td>$($finding.NextRunTime)</td>
                        <td>$($finding.SuspiciousFlags -join ', ')</td>
                    </tr>
"@
            }
            $html += @"
                </table>
            </body>
            </html>
"@
            $html | Out-File $OutputPath
        }
    }
}
