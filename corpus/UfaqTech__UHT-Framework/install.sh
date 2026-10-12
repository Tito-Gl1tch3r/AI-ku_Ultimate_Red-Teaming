#!/bin/bash

# --- UTH Framework Installation Script ---
# This script sets up a Python virtual environment and installs dependencies.

# Check if the script is run in a writable directory
if [ ! -w . ]; then
    echo "Error: Cannot write to the current directory."
    echo "Please run this script in a directory where you have write permissions."
    exit 1
fi

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed."
    echo "Please install Python 3 and try again."
    exit 1
fi

echo "--- Uth-framework Setup ---"
echo "This script will create a virtual environment and install dependencies."

# Create a virtual environment named 'venv'
echo "Creating Python virtual environment..."
python3 -m venv venv

if [ $? -ne 0 ]; then
    echo "Error: Failed to create virtual environment."
    echo "Please ensure you have the 'venv' module installed (e.g., 'sudo apt-get install python3-venv')."
    exit 1
fi

# Activate the virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if activation was successful
if [ $? -ne 0 ]; then
    echo "Error: Failed to activate virtual environment."
    echo "Please check your environment setup."
    exit 1
fi

# Install required Python libraries
echo "Installing required Python libraries (rich and requests)..."
pip install rich requests

if [ $? -ne 0 ]; then
    echo "Error: Failed to install required libraries."
    echo "Please check your network connection or try running 'pip install rich requests' manually."
    deactivate
    exit 1
fi

# Deactivate the virtual environment to prevent the user from continuing in it by mistake
deactivate

echo "--- Setup Complete ---"
echo "The Uth-framework has been successfully set up in a 'venv' directory."
echo "To run the tool, use the following commands:"
echo ""
echo "    1. Activate the virtual environment:"
echo "       source venv/bin/activate"
echo ""
echo "    2. Run the tool:"
echo "       python3 uth.py"
echo ""
echo "    3. To exit the virtual environment when you are done:"
echo "       deactivate"
echo ""
