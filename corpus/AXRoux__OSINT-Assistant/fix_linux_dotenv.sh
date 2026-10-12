#!/bin/bash

echo "===== OSINT Assistant Python Environment Diagnostic ====="
echo

# Show Python environment information
echo "PYTHON ENVIRONMENT INFORMATION:"
echo "------------------------------"
which python3
python3 --version
echo
echo "Python executable path:"
python3 -c "import sys; print(sys.executable)"
echo
echo "Python site-packages location:"
python3 -c "import site; print(site.getsitepackages()[0])"
echo

# Try different pip installation methods
echo "ATTEMPTING MULTIPLE INSTALLATION METHODS:"
echo "------------------------------"
echo "Method 1: Standard pip install"
pip install python-dotenv
echo

echo "Method 2: Specific Python executable"
python3 -m pip install python-dotenv
echo

echo "Method 3: Using pip directly with --user flag"
pip install --user python-dotenv
echo

echo "Method 4: Force reinstallation"
pip install --force-reinstall python-dotenv
echo

# Verify installation
echo "VERIFYING INSTALLATION:"
echo "------------------------------"
echo "Checking if dotenv is now installed:"
python3 -c "import importlib.util; print('python-dotenv is INSTALLED' if importlib.util.find_spec('dotenv') else 'python-dotenv is NOT installed')"
echo

# Run the actual application with error handling
echo "TESTING OSINT ASSISTANT:"
echo "------------------------------"
echo "Trying to import dotenv module..."
python3 -c "try: import dotenv; print('Successfully imported dotenv module. Now checking for dotenv_values function...'); print('dotenv_values function exists' if hasattr(dotenv, 'dotenv_values') else 'dotenv_values function MISSING'); except ImportError as e: print(f'Error: {e}. Module still not installed correctly.')"
echo

echo "==== TROUBLESHOOTING RECOMMENDATIONS ===="
echo
echo "If the module is still not found:"
echo "1. Try using pip3 instead of pip:"
echo "   pip3 install python-dotenv"
echo
echo "2. Try installing with sudo (if you have admin privileges):"
echo "   sudo pip install python-dotenv"
echo
echo "3. If you're using a virtual environment, make sure it's activated"
echo
echo "4. Manually add the site-packages path to PYTHONPATH:"
echo "   export PYTHONPATH=\$PYTHONPATH:[site-packages-path-shown-above]"
echo
echo "5. We've included a standalone dotenv.py module in the project directory"
echo "   This should work even without installing python-dotenv"
echo

# Make the script executable
chmod +x run.sh 