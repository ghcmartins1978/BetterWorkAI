#!/bin/bash
# BettermanAI Quick Start (Local Electron with Rust Helper)

echo "=== BettermanAI Quick Start (Local Electron with Rust Helper) ==="
echo

# Set up environment
echo "Setting up environment..."

# Create data directory
mkdir -p data

# Clean up any existing processes
echo "Cleaning up any existing processes..."
pkill -f "Flask Server" || true
pkill -f "Rust Helper" || true
pkill -f "betterman_helper" || true

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
echo "  2. Build the Rust helper using: ./build_rust_helper.sh"
echo
echo "Press Ctrl+C to stop the application when done"
echo

# Check if Rust helper binary exists
RUST_HELPER_PATH="${PWD}/electron/rust_helper/betterman_helper"
if [ ! -f "$RUST_HELPER_PATH" ]; then
    echo "ERROR: Rust helper binary not found at $RUST_HELPER_PATH"
    echo "Please build the Rust helper first using ./build_rust_helper.sh"
    exit 1
fi

# Make sure the helper is executable
chmod +x "$RUST_HELPER_PATH"

# Start the Flask server in the background
echo "Starting Flask server..."
python -m flask run --host=0.0.0.0 --port=5000 > /tmp/flask_server.log 2>&1 &
FLASK_PID=$!

# Wait for Flask to start
echo "Waiting for Flask server to start..."
sleep 3

# Start the Rust helper in the background
echo "Starting Rust helper..."
"$RUST_HELPER_PATH" > /tmp/rust_helper.log 2>&1 &
RUST_HELPER_PID=$!

# Wait for the Rust helper to start
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
pkill -f "Rust Helper" || true
pkill -f "betterman_helper" || true

echo
echo "Press Enter to exit..."
read