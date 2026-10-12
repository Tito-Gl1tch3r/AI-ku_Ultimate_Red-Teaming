#!/bin/bash

# Exit on any error
set -e

# Function to check if a command is available
command_exists() {
    command -v "$1" &>/dev/null
}

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Update package lists
log "Updating package lists..."
apt-get update -y

# Install prerequisites
log "Installing prerequisites..."
apt-get install -y \
    curl \
    build-essential \
    python3 \
    python3-pip \
    python3-venv \
    make \
    g++ \
    libbluetooth-dev \
    libudev-dev \
    libusb-1.0-0-dev \
    bluez

# Verify Python3 installation
log "Verifying Python installation..."
if ! command_exists python3; then
    log "Python3 not found. Installing..."
    apt-get install -y python3
fi
python3 --version

# Update pip to the latest version
log "Updating pip..."
pip3 install --upgrade pip --root-user-action=ignore

# Remove existing Node.js version
log "Removing existing Node.js version..."
apt-get remove -y nodejs libnode-dev nodejs-doc || true
apt-get autoremove -y
apt-get purge -y nodejs libnode-dev nodejs-doc || true
rm -rf /usr/local/lib/node_modules /usr/local/bin/node /usr/local/bin/npm /root/.npm /root/.node-gyp /home/*/.npm /home/*/.node-gyp

# Install Node.js 16
log "Installing Node.js 16..."
curl -fsSL https://deb.nodesource.com/setup_16.x | bash - || {
    log "Failed to add NodeSource repository. Trying alternative method..."
    curl -fsSL https://deb.nodesource.com/setup_16.x | bash -
}
apt-get install -y nodejs

# Verify Node.js and npm installation
log "Verifying Node.js and npm installation..."
if ! command_exists node; then
    log "Node.js not found. Exiting..."
    exit 1
fi
if ! command_exists npm; then
    log "npm not found. Exiting..."
    exit 1
fi
node_version=$(node --version)
npm_version=$(npm --version)
log "Node.js version: $node_version"
log "npm version: $npm_version"

# Ensure npm version is compatible (8.x for Node.js 16)
if [[ ! $npm_version =~ ^8\..* ]]; then
    log "Installing npm 8.x for compatibility with Node.js 16..."
    npm install -g npm@8.19.4
fi

# Install node-gyp globally
log "Installing node-gyp globally..."
npm install -g node-gyp@9.4.1

# Verify node-gyp installation
if ! command_exists node-gyp; then
    log "node-gyp not found. Exiting..."
    exit 1
fi

# Clone or navigate to gattacker directory
gattacker_dir="/home/$SUDO_USER/tools/gattacker"
if [ ! -d "$gattacker_dir" ]; then
    log "Cloning gattacker repository..."
    mkdir -p "$(dirname "$gattacker_dir")"
    git clone https://github.com/xen0bit/gattacker "$gattacker_dir"
fi
log "Navigating to gattacker directory..."
cd "$gattacker_dir"

# Clean npm cache
log "Cleaning npm cache..."
npm cache clean --force

# Remove node_modules and package-lock.json
log "Removing node_modules and package-lock.json..."
rm -rf node_modules package-lock.json

# Run npm install with verbose output
log "Running npm install..."
npm install --verbose

# Fix ownership for non-root user
if [ -n "$SUDO_USER" ]; then
    log "Fixing ownership for $SUDO_USER..."
    chown -R "$SUDO_USER:$SUDO_USER" "$gattacker_dir"
fi

log "Installation completed successfully!"
log "To test gattacker, run: cd $gattacker_dir && node ws-client.js"
