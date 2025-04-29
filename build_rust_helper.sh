#!/bin/bash
# Script to build the Rust helper for BettermanAI

set -e # Exit on any error

# Directory check
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
HELPER_DIR="$SCRIPT_DIR/rust_helper"

# Print header
echo "========================================="
echo "  Building BettermanAI Rust Helper"
echo "========================================="

# Check if Rust is installed
if ! command -v rustc &> /dev/null; then
    echo "Error: Rust is not installed."
    echo "Please install Rust from https://rustup.rs/"
    exit 1
fi

# Check if Cargo is installed
if ! command -v cargo &> /dev/null; then
    echo "Error: Cargo is not installed."
    echo "Please install Rust from https://rustup.rs/"
    exit 1
fi

# Display versions
echo "Rust version: $(rustc --version)"
echo "Cargo version: $(cargo --version)"
echo

# Check if the helper directory exists
if [ ! -d "$HELPER_DIR" ]; then
    echo "Error: Rust helper directory not found at $HELPER_DIR"
    exit 1
fi

# Navigate to the helper directory
cd "$HELPER_DIR"

# Build the helper in release mode
echo "Building the Rust helper in release mode..."
cargo build --release

# Check for successful build
if [ $? -ne 0 ]; then
    echo "Error: Failed to build the Rust helper."
    exit 1
fi

# Target directory
TARGET_DIR="$HELPER_DIR/target/release"
BINARY_NAME="betterman_helper"
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    BINARY_NAME="betterman_helper.exe"
fi

# Check if binary exists
if [ ! -f "$TARGET_DIR/$BINARY_NAME" ]; then
    echo "Error: Built binary not found at $TARGET_DIR/$BINARY_NAME"
    exit 1
fi

# Create the electron/rust_helper directory if it doesn't exist
ELECTRON_HELPER_DIR="$SCRIPT_DIR/electron/rust_helper"
mkdir -p "$ELECTRON_HELPER_DIR"

# Copy the binary to the electron/rust_helper directory
echo "Copying binary to $ELECTRON_HELPER_DIR/$BINARY_NAME"
cp "$TARGET_DIR/$BINARY_NAME" "$ELECTRON_HELPER_DIR/$BINARY_NAME"

# Make the binary executable (Unix-like systems only)
if [[ "$OSTYPE" != "msys" && "$OSTYPE" != "win32" ]]; then
    chmod +x "$ELECTRON_HELPER_DIR/$BINARY_NAME"
fi

echo
echo "Successfully built and installed the Rust helper."
echo "The helper binary is located at: $ELECTRON_HELPER_DIR/$BINARY_NAME"
echo "========================================="