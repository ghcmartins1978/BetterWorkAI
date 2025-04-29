#!/bin/bash
# BettermanAI Quick Start (With Real Rust Helper)

echo "=== BettermanAI Quick Start (With Real Rust Helper) ==="
echo

# Set up environment
echo "Setting up environment..."

# Create data directory
mkdir -p data

# Clean up any existing processes
echo "Cleaning up any existing processes..."
pkill -f "Flask Server" || true
pkill -f "Python Rust Helper" || true
pkill -f "python rust_helper.py" || true

# Set environment variables
export NODE_ENV=development
export RUNNING_IN_ELECTRON=1
export DATABASE_URL=sqlite:///${PWD}/data/betterman.db
export AUTOMATION_SERVER_URL=http://127.0.0.1:17400
export FLASK_APP=main.py
echo "✓ Environment variables set"

echo
echo "=== Starting BettermanAI ==="
echo
echo "If this is your first time running the app:"
echo "  1. Make sure you've installed dependencies"
echo "  2. Install Electron if needed"
echo
echo "Press Ctrl+C to stop the application when done"
echo

# Check if Python Rust helper implementation exists
if [ ! -f "rust_helper.py" ]; then
    echo "ERROR: Python Rust helper implementation not found at rust_helper.py"
    exit 1
fi

# Start the Flask server in the background
echo "Starting Flask server..."
python -m flask run --host=0.0.0.0 --port=5000 > /tmp/flask_server.log 2>&1 &
FLASK_PID=$!

# Wait for Flask to start
echo "Waiting for Flask server to start..."
sleep 3

# Start the Python Rust helper in the background
echo "Starting Python Rust helper..."
python rust_helper.py > /tmp/rust_helper.log 2>&1 &
RUST_HELPER_PID=$!

# Wait for the Python Rust helper to start
echo "Waiting for Rust helper to start..."
sleep 2

# Start Electron pointing to the Flask app
echo "Starting Electron..."
cd electron
./node_modules/.bin/electron . || ../node_modules/.bin/electron .
cd ..

echo
echo "BettermanAI has closed."
echo "Terminating Flask server and Rust helper..."

# Kill the Flask and Rust helper processes
kill $FLASK_PID $RUST_HELPER_PID 2>/dev/null || true
pkill -f "Flask Server" || true
pkill -f "Python Rust Helper" || true
pkill -f "python rust_helper.py" || true

echo
echo "Press Enter to exit..."
read