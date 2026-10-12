#!/bin/bash

# Exit script if any command fails
set -e

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if Homebrew is installed by looking in the common paths
if [ -x "/opt/homebrew/bin/brew" ]; then
    HOMEBREW_BIN="/opt/homebrew/bin/brew"
elif [ -x "/usr/local/bin/brew" ]; then
    HOMEBREW_BIN="/usr/local/bin/brew"
else
    echo "Homebrew is not installed. Please install Homebrew before running this script."
    exit 1
fi

echo "Homebrew is installed at $HOMEBREW_BIN"

# Install PowerShell using Homebrew if not already installed
if ! command_exists pwsh; then
    echo "Installing PowerShell..."
    $HOMEBREW_BIN install --cask powershell
else
    echo "PowerShell is already installed."
fi

# Variables
LOG_DIR="/opt/art/logs"
ART_REPO="/opt/atomic-red-team"

# Install Atomic Red Team using the official script with the specified InstallPath
echo "Installing Atomic Red Team using the official script from the repository..."
pwsh -Command "Install-Module -Name invoke-atomicredteam,powershell-yaml -Scope AllUsers; Install-AtomicRedTeam -getAtomics -InstallPath '$ART_REPO' -Force"

# Set up log directory for test outputs
if [ ! -d "$LOG_DIR" ]; then
    echo "Creating log directory at $LOG_DIR"
    sudo mkdir -p "$LOG_DIR"
    sudo chown -R $(whoami) "$LOG_DIR"
else
    echo "Log directory already exists at $LOG_DIR"
fi

echo "Atomic Red Team setup completed."