#!/bin/bash

# Exit script if any command fails
set -e

# Default tests to run (if none provided through Parameter 4)
DEFAULT_TESTS="T1003,T1059.001"
# Default webhook URL (if none provided through Parameter 5)
DEFAULT_WEBHOOK_URL="https://your-webhook-url.com"

# Jamf Pro parameters (Parameter 4 for tests, Parameter 5 for webhook URL)
TESTS_TO_RUN="${4:-$DEFAULT_TESTS}"
WEBHOOK_URL="${5:-$DEFAULT_WEBHOOK_URL}"

# Directory to store log files
LOG_DIR="/opt/art/logs"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Full path to PowerShell
if command_exists /opt/homebrew/bin/pwsh; then
    POWERSHELL_BIN="/opt/homebrew/bin/pwsh"  # For Apple Silicon Macs
elif command_exists /usr/local/bin/pwsh; then
    POWERSHELL_BIN="/usr/local/bin/pwsh"  # For Intel Macs
else
    echo "PowerShell is not installed. Exiting."
    exit 1
fi

# Ensure Atomic Red Team repo exists
if [ ! -d "/opt/atomic-red-team" ]; then
    echo "Atomic Red Team repository not found. Exiting."
    exit 1
fi

# Ensure log directory exists
if [ ! -d "$LOG_DIR" ]; then
    echo "Creating log directory at $LOG_DIR"
    mkdir -p "$LOG_DIR"
fi

# Convert comma-delimited list into array
IFS=',' read -r -a TEST_ARRAY <<< "$TESTS_TO_RUN"

# Loop through each test and execute it using Invoke-AtomicTest
for TEST in "${TEST_ARRAY[@]}"; do
    LOG_FILE="$LOG_DIR/$TEST.json"
    echo "Running Atomic Test: $TEST and logging to $LOG_FILE"
    
    # Run the test and log it to a JSON file
    $POWERSHELL_BIN -Command "& {
        Import-Module 'Invoke-AtomicRedTeam' -Force;
        Invoke-AtomicTest $TEST -PathToAtomicsFolder /opt/atomic-red-team/atomics -LoggingModule 'Attire-ExecutionLogger' -ExecutionLogPath '$LOG_FILE';
    }"

    # Check if log file exists and upload to webhook
    if [ -f "$LOG_FILE" ]; then
        echo "Uploading $LOG_FILE to webhook $WEBHOOK_URL"
        curl -X POST -H "Content-Type: application/json" -d @"$LOG_FILE" "$WEBHOOK_URL"
        
        if [ $? -eq 0 ]; then
            echo "Successfully uploaded $LOG_FILE"
        else
            echo "Failed to upload $LOG_FILE"
        fi
    else
        echo "Log file $LOG_FILE does not exist, skipping upload."
    fi

    # Run cleanup after the test
    echo "Running cleanup for Atomic Test: $TEST"
    $POWERSHELL_BIN -Command "Invoke-AtomicTest $TEST -Cleanup;"
done

echo "Atomic Red Team tests completed and logs uploaded."
