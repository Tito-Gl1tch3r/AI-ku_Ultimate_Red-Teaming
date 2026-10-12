#!/bin/bash

# PrimusRedir Automated Setup Script
# This script installs the required system dependencies and Python packages
# Supports Debian-based systems (Ubuntu, Kali Linux, etc.)

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install system dependencies
install_system_deps() {
    print_status "Installing system dependencies on Debian-based system..."
    sudo apt update
    sudo apt install -y wireguard wireguard-tools curl wget git python3 python3-pip unzip jq
    print_success "System dependencies installed"
}

# Function to install Terraform
install_terraform() {
    if command_exists terraform; then
        print_success "Terraform is already installed"
        return
    fi
    
    print_status "Installing Terraform..."
    
    # Get latest Terraform version
    TF_VERSION=$(curl -s https://checkpoint-api.hashicorp.com/v1/check/terraform | jq -r '.current_version')
    
    # Download and install Terraform
    curl -LO "https://releases.hashicorp.com/terraform/${TF_VERSION}/terraform_${TF_VERSION}_linux_amd64.zip"
    unzip "terraform_${TF_VERSION}_linux_amd64.zip"
    sudo mv terraform /usr/local/bin/
    rm "terraform_${TF_VERSION}_linux_amd64.zip"
    
    print_success "Terraform ${TF_VERSION} installed successfully"
}

# Function to install Python dependencies
install_python_deps() {
    print_status "Installing Python dependencies..."
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        print_status "Creating virtual environment..."
        python3 -m venv venv
        print_success "Virtual environment created"
    else
        print_success "Virtual environment already exists"
    fi
    
    # Activate virtual environment and install dependencies
    print_status "Installing Python packages in virtual environment..."
    source venv/bin/activate
    pip install -r requirements.txt
    deactivate
    
    print_success "Python dependencies installed in virtual environment"
}

# Function to check Python version
check_python_version() {
    local python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    local required_version="3.7"
    
    if python3 -c "import sys; exit(0 if sys.version_info >= (3, 7) else 1)"; then
        print_success "Python $python_version is compatible"
    else
        print_error "Python $python_version is too old. Required: $required_version+"
        exit 1
    fi
}

# Function to verify installation
verify_installation() {
    print_status "Verifying installation..."
    
    local all_good=true
    
    # Check Python
    if command_exists python3; then
        print_success "Python3 found"
        check_python_version
    else
        print_error "Python3 not found"
        all_good=false
    fi
    
    # Check Terraform
    if command_exists terraform; then
        print_success "Terraform found"
    else
        print_error "Terraform not found"
        all_good=false
    fi
    
    # Check WireGuard
    if command_exists wg; then
        print_success "WireGuard tools found"
    else
        print_error "WireGuard tools not found"
        all_good=false
    fi
    
    # Check virtual environment and Python dependencies
    if [ -d "venv" ]; then
        print_success "Virtual environment found"
        if source venv/bin/activate && python -c "import halo, rich" 2>/dev/null; then
            print_success "Python dependencies installed in virtual environment"
            deactivate
        else
            print_error "Python dependencies missing in virtual environment"
            all_good=false
            deactivate 2>/dev/null || true
        fi
    else
        print_error "Virtual environment not found"
        all_good=false
    fi
    
    if [ "$all_good" = true ]; then
        print_success "All checks passed! PrimusRedir is ready to use."
    else
        print_error "Some checks failed. Please run the setup script again."
        exit 1
    fi
}

# Main setup function
main() {
    echo "PrimusRedir Setup Script"
    echo "========================"
    echo ""
    
    print_status "Starting PrimusRedir setup..."
    
    # Check system dependencies
    print_status "Installing system dependencies..."
    install_system_deps
    install_terraform
    
    # Check Python and install dependencies
    print_status "Setting up Python environment..."
    check_python_version
    install_python_deps
    
    # Verify everything is working
    verify_installation
    
    print_success "Setup complete! PrimusRedir is ready to use."
    echo ""
    echo "Next steps:"
    echo "1. Activate virtual environment: source venv/bin/activate"
    echo "2. Configure API keys: python3 Primus_redir.py --config"
    echo "3. Provision redirector: python3 Primus_redir.py -d your-subdomain.yourdomain.com"
    echo ""
    echo "Note: Always activate the virtual environment before running PrimusRedir:"
    echo "  source venv/bin/activate"
}

# Run main function
main "$@" 