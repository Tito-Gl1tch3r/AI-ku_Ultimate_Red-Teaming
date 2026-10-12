#!/bin/bash

# Check if Python is installed
if ! command -v python &> /dev/null; then
    echo "Python is required but not installed. Please install Python 3.8+ and try again."
    exit 1
fi

# Check if Flask is installed
python -c "import flask" &> /dev/null
if [ $? -ne 0 ]; then
    echo "Flask is not installed. Installing dependencies..."
    pip install -r requirements.txt
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Creating .env file from example..."
    cp .env.example .env
    echo "Please edit the .env file and add your API key."
fi

# Check if React app is built
if [ ! -d "client/build" ]; then
    echo "React app is not built. Building now..."
    
    # Check if Node.js is installed
    if ! command -v npm &> /dev/null; then
        echo "Node.js and npm are required to build the frontend. Please install them and try again."
        echo "Running with backend only..."
    else
        cd client
        npm install
        npm run build
        cd ..
    fi
fi

# Start the Flask server
echo "Starting OSINT Assistant Web App..."
python osint_web_app.py 