#!/bin/bash

# Exit script if any command fails
set -e

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if Git is installed, if not, install it
if ! command_exists git; then
    echo "Git not found. Installing Git..."
    sudo apt-get update && sudo apt-get install -y git
else
    echo "Git is already installed."
fi

# Check if Curl is installed, if not, install it
if ! command_exists curl; then
    echo "Curl not found. Installing Curl..."
    sudo apt-get install -y curl
else
    echo "Curl is already installed."
fi

# Check if PowerShell is installed, if not, install it
if ! command_exists pwsh; then
    echo "PowerShell not found. Installing PowerShell..."
    sudo apt-get update
    sudo apt-get install -y wget apt-transport-https software-properties-common
    wget -q "https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/packages-microsoft-prod.deb"
    sudo dpkg -i packages-microsoft-prod.deb
    sudo apt-get update
    sudo apt-get install -y powershell
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
