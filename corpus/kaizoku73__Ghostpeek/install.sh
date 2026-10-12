#!/bin/bash

# GhostPeek Installation Script
# Usage: curl -sSL https://raw.githubusercontent.com/kaizoku73/Ghostpeek/main/install.sh | bash

set -euo pipefail

# Cleanup function for temp directory
cleanup() {
    if [[ -n "${TEMP_DIR:-}" ]] && [[ -d "$TEMP_DIR" ]]; then
        rm -rf "$TEMP_DIR"
    fi
}
trap cleanup EXIT

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}👻 GhostPeek Installer${NC}"
echo -e "${BLUE}=====================${NC}"

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check for required dependencies
echo "Checking system requirements..."

# Check Python 3
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed."
    echo "Please install Python 3.6+ and try again."
    echo "Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
    echo "CentOS/RHEL: sudo yum install python3 python3-pip"
    echo "Arch Linux: sudo pacman -S python python-pip"
    exit 1
fi
print_status "Python 3 found: $(python3 --version)"

# Check pip
if ! command -v pip3 &> /dev/null && ! python3 -m pip --version &> /dev/null; then
    print_error "pip is required but not installed."
    echo "Please install pip and try again."
    echo "Ubuntu/Debian: sudo apt install python3-pip"
    exit 1
fi
print_status "pip found"

# Check for virtual environment support (try multiple methods)
VENV_METHOD=""
if python3 -c "import venv" 2>/dev/null; then
    VENV_METHOD="venv"
    print_status "Built-in venv module found"
elif command -v virtualenv &> /dev/null; then
    VENV_METHOD="virtualenv"
    print_status "virtualenv found"
else
    print_warning "No virtual environment support found"
    echo "Trying to install virtualenv..."
    if command -v pip3 &> /dev/null; then
        python3 -m pip install --user virtualenv 2>/dev/null && VENV_METHOD="virtualenv" || true
    fi
    
    if [[ -z "$VENV_METHOD" ]]; then
        print_error "Virtual environment support required but not available"
        echo "Please install one of the following:"
        echo "Ubuntu/Debian: sudo apt install python3-venv"
        echo "CentOS/RHEL: sudo yum install python3-pip && pip3 install virtualenv"
        echo "Arch Linux: sudo pacman -S python-virtualenv"
        echo "macOS: pip3 install virtualenv"
        echo "Or: pip3 install --user virtualenv"
        exit 1
    else
        print_status "virtualenv installed successfully"
    fi
fi

# Check if Chrome/Chromium is available (needed for screenshots)
if ! command -v google-chrome &> /dev/null && ! command -v chromium-browser &> /dev/null && ! command -v chromium &> /dev/null; then
    print_warning "Chrome/Chromium not found. Screenshots may not work."
    echo "Install Chrome or Chromium for full functionality:"
    echo "Ubuntu/Debian: sudo apt install chromium-browser"
    echo "Arch Linux: sudo pacman -S chromium"
fi

# Determine installation directory
if [[ $EUID -eq 0 ]]; then
    # Running as root - system-wide install
    INSTALL_DIR="/usr/local/bin"
    GHOSTPEEK_DIR="/usr/local/share/ghostpeek"
    INSTALL_TYPE="system-wide"
    print_status "Installing system-wide (requires root privileges)"
else
    # User installation
    INSTALL_DIR="$HOME/.local/bin"
    GHOSTPEEK_DIR="$HOME/.local/share/ghostpeek"
    INSTALL_TYPE="user"
    print_status "Installing for current user"
fi

# Create directories
echo "Creating directories..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$GHOSTPEEK_DIR"

# Download GhostPeek
echo "Downloading GhostPeek (latest release)..."
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

if ! curl -fsSL -o ghostpeek.tar.gz https://github.com/kaizoku73/Ghostpeek/archive/refs/heads/main.tar.gz; then
    print_error "Failed to download GhostPeek"
    exit 1
fi

tar -xzf ghostpeek.tar.gz
cd Ghostpeek-main

print_status "Downloaded and extracted GhostPeek"

# Copy files to installation directory first
echo "Installing GhostPeek files..."
cp ghostpeek.py requirements.txt README.md LICENSE "$GHOSTPEEK_DIR/" 2>/dev/null || cp ghostpeek.py requirements.txt "$GHOSTPEEK_DIR/"
print_status "Files copied to $GHOSTPEEK_DIR"

# Create virtual environment in the installation directory
echo "Creating virtual environment..."
cd "$GHOSTPEEK_DIR"

# Create virtual environment using available method
if [[ "$VENV_METHOD" == "venv" ]]; then
    python3 -m venv venv
elif [[ "$VENV_METHOD" == "virtualenv" ]]; then
    python3 -m virtualenv venv 2>/dev/null || virtualenv -p python3 venv
fi

# Check if virtual environment was created successfully
if [[ ! -d "venv" ]] || [[ ! -f "venv/bin/activate" ]]; then
    print_error "Failed to create virtual environment"
    print_warning "Falling back to system-wide installation"
    VENV_FAILED=true
else
    print_status "Virtual environment created successfully"
    VENV_FAILED=false
fi

# Install dependencies (with or without virtual environment)
echo "Installing Python dependencies..."
if [[ "$VENV_FAILED" == "false" ]]; then
    # Use virtual environment
    source venv/bin/activate
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    deactivate
    print_status "Dependencies installed in virtual environment"
else
    # Fallback to user installation
    print_warning "Installing dependencies without virtual environment"
    if [[ $INSTALL_TYPE == "system-wide" ]]; then
        python3 -m pip install -r requirements.txt
    else
        python3 -m pip install -r requirements.txt --user
    fi
    print_status "Dependencies installed"
fi

# Create executable wrapper script
echo "Creating executable..."
if [[ "$VENV_FAILED" == "false" ]]; then
    # Create wrapper with virtual environment
    cat > "$INSTALL_DIR/ghostpeek" << EOF
#!/bin/bash
# GhostPeek wrapper script with virtual environment
cd "$GHOSTPEEK_DIR"
if [[ -f "venv/bin/activate" ]]; then
    exec venv/bin/python ghostpeek.py "\$@"
else
    # Fallback if venv is missing
    exec python3 ghostpeek.py "\$@"
fi
EOF
else
    # Create wrapper without virtual environment
    cat > "$INSTALL_DIR/ghostpeek" << EOF
#!/bin/bash
# GhostPeek wrapper script
cd "$GHOSTPEEK_DIR"
exec python3 ghostpeek.py "\$@"
EOF
fi

chmod +x "$INSTALL_DIR/ghostpeek"
print_status "Executable created"

# Cleanup
cd /
rm -rf "$TEMP_DIR"

echo ""
echo -e "${GREEN}GhostPeek installed successfully!${NC}"
echo ""

# Installation summary
if [[ $INSTALL_TYPE == "system-wide" ]]; then
    echo -e "${BLUE}Usage:${NC}"
    echo "   ghostpeek -d example.com"
    echo "   ghostpeek -d example.com -o /path/to/output"
    echo "   ghostpeek -d example.com -t 20"
else
    echo -e "${BLUE}Usage:${NC}"
    # Check if ~/.local/bin is in PATH
    if [[ ":$PATH:" == *":$HOME/.local/bin:"* ]]; then
        echo "   ghostpeek -d example.com"
        echo "   ghostpeek -d example.com -o /path/to/output" 
        echo "   ghostpeek -d example.com -t 20"
    else
        echo "   ~/.local/bin/ghostpeek -d example.com"
        echo ""
        print_warning "~/.local/bin is not in your PATH"
        echo "To use 'ghostpeek' from anywhere, run this command:"
        echo ""
        echo "   echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc && source ~/.bashrc"
        echo ""
        echo "Or for this session only:"
        echo "   export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi
fi

echo ""
echo -e "${BLUE} Examples:${NC}"
echo "   ghostpeek -d google.com"
echo "   ghostpeek -d target.com -o ~/my_scans"
echo "   ghostpeek -d example.com --no-threading"
echo ""
echo -e "${BLUE}Installation Details:${NC}"
echo "   Location: $GHOSTPEEK_DIR"
if [[ "$VENV_FAILED" == "false" ]]; then
    echo "   Virtual Environment: $GHOSTPEEK_DIR/venv"
else
    echo "   Virtual Environment: Not used (fallback mode)"
fi
echo "   Executable: $INSTALL_DIR/ghostpeek"
echo ""
echo ""
echo -e "${GREEN}Happy reconnaissance!${NC}"