# Exit script if any command fails
$ErrorActionPreference = "Stop"

# Parameters
param (
    [string]$TestsToRun = "T1003,T1059.001",
    [string]$WebhookURL = "https://your-webhook-url.com"
)

# Variables
$LOG_DIR = "C:\AtomicRedTeam\Logs"
$ART_MODULE_PATH = "C:\AtomicRedTeam\Invoke-AtomicRedTeam"

# Ensure the Invoke-AtomicRedTeam PowerShell module is installed
if (-not (Get-Module -ListAvailable -Name Invoke-AtomicRedTeam)) {
    Write-Output "Invoke-AtomicRedTeam PowerShell module is not installed. Please install it before running this script."
    exit 1
}

# Ensure log directory exists
if (-not (Test-Path $LOG_DIR)) {
    New-Item -ItemType Directory -Path $LOG_DIR | Out-Null
}

# Convert comma-delimited list into array
$TestsArray = $TestsToRun -split ','

# Function to upload logs to webhook
function Upload-LogToWebhook {
    param (
        [string]$LogFile,
        [string]$WebhookURL
    )

    if (Test-Path $LogFile) {
        $jsonContent = Get-Content -Path $LogFile -Raw
        $response = Invoke-RestMethod -Uri $WebhookURL -Method Post -Body $jsonContent -ContentType "application/json"
        if ($response.StatusCode -eq 200) {
            Write-Output "Successfully uploaded $LogFile to $WebhookURL"
        } else {
            Write-Output "Failed to upload $LogFile to webhook."
        }
    } else {
        Write-Output "Log file $LogFile does not exist, skipping upload."
    }
}

# Run each test and log output
foreach ($test in $TestsArray) {
    $log_file = "$LOG_DIR\$test.json"
    Write-Output "Running Atomic Test: $test and logging to $log_file"
    
    # Execute the test and log the output
    Invoke-AtomicTest $test -LoggingModule 'Invoke-AtomicLogger' -ExecutionLogPath $log_file

    # Upload log to webhook if available
    if ($WebhookURL) {
        Upload-LogToWebhook -LogFile $log_file -WebhookURL $WebhookURL
    }

    # Cleanup after the test
    Write-Output "Running cleanup for Atomic Test: $test"
    Invoke-AtomicTest $test -Cleanup
}

# Check Windows Defender logs for any alerts
Write-Output "Checking Windows Defender logs for any detections..."

# Search Windows Defender event logs for detections
$defender_logs = Get-WinEvent -LogName "Microsoft-Windows-Windows Defender/Operational" | 
    Where-Object { $_.Message -match "threat" -or $_.Message -match "detected" }

# Display Defender log detections
if ($defender_logs) {
    Write-Output "Windows Defender detected the following threats:"
    foreach ($log in $defender_logs) {
        Write-Output $log.Message
    }
} else {
    Write-Output "No threats detected by Windows Defender."
}

Write-Output "Atomic Red Team tests completed."
