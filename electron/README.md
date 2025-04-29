# BettermanAI Electron Application

This directory contains the Electron wrapper for BettermanAI, which packages the Flask web application and the Rust helper into a single desktop application.

## Development Setup

### Prerequisites

- Node.js 18+ and npm
- Python 3.8+ with pip
- Rust toolchain (for building the helper)

### Install Dependencies

```bash
# Install Node.js dependencies
npm install

# Install Python dependencies (from repo root)
cd ..
pip install -r requirements.txt
```

### Development Mode

```bash
# Start the Electron app in development mode
npm run dev

# On Windows
npm run win-dev
```

This will:
1. Start the Flask server as a child process
2. Start the Rust helper as a child process
3. Launch the Electron app pointing to the Flask server

### Building the Application

```bash
# Build for all platforms
npm run build

# Build for specific platforms
npm run build:mac
npm run build:win
npm run build:linux
```

The built applications will be in the `dist` directory.

## Project Structure

- `main.js`: Main Electron process
- `preload.js`: Secure bridge between Electron and web content
- `package.json`: Application configuration
- `rust_helper/`: Directory containing Rust helper binaries

## Packaging Notes

The application packages:

1. The entire Flask application code
2. A Python interpreter (using electron-builder)
3. The Rust helper binaries
4. All required dependencies

## Deployment Considerations

- Windows: The installer will need admin privileges to set up the Rust helper
- macOS: The app will need accessibility permissions for automation features
- Linux: Depending on the distribution, X11 or Wayland permissions may be needed

## Auto-Updates

The application is configured for auto-updates using electron-builder's built-in functionality. Updates will be checked when the application starts.