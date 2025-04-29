# BettermanAI Development Guide

This document outlines the development setup and processes for the BettermanAI application.

## Architecture Overview

BettermanAI uses a hybrid architecture:

- **Web UI**: Flask-based web interface
- **System Automation**: Rust helper application running locally
- **Desktop Integration**: Electron wrapper for packaging

The application is designed to work in two modes:

1. **Development Mode**: Mock Rust helper, SQLite database
2. **Production Mode**: Real Rust helper, PostgreSQL database

## Development Setup

### Prerequisites

- Node.js 18+ and npm
- Python 3.8+
- (Optional) Rust toolchain for building the helper

### Setting Up the Development Environment

1. Clone the repository

```bash
git clone https://github.com/yourusername/bettermanai.git
cd bettermanai
```

2. Install Python dependencies

```bash
pip install -r requirements.txt
```

3. Install Electron dependencies

```bash
cd electron
npm install
cd ..
```

4. Run the application in development mode

```bash
# Option 1: Using the convenience script
./run_electron_app.sh

# Option 2: Manually
cd electron
npm run dev  # On macOS/Linux
npm run win-dev  # On Windows
```

## Development Mode Features

In development mode, the application uses:

- Mock JavaScript version of the Rust helper API (runs on port 17400)
- SQLite database in the `data` directory
- Automatic creation of required directories
- Mock responses for automation functions

## Mock Rust Helper

The mock Rust helper (`electron/mock_helper.js`) provides a simple Express server that mimics the real Rust helper's API. It responds to the same endpoints but provides mock data instead of actually controlling the system.

If you need to add new endpoints to the mock helper, update both the mock helper and the `automation_client.py` file.

## Database

The application uses SQLAlchemy with a database URL specified in the `DATABASE_URL` environment variable. In development mode, it defaults to a SQLite database in the `data` directory.

Database schema updates are handled in `database.py` through the `check_and_update_schema()` function.

## Building for Production

To build the application for production:

```bash
cd electron
npm run build
```

This will create platform-specific packages in the `electron/dist` directory.

## Rust Helper Development

The Rust helper source code is located in the `rust_helper` directory. To build it:

1. Install Rust (https://rustup.rs/)
2. Build the helper:

```bash
cd rust_helper
cargo build --release
```

The built binary will be placed in `rust_helper/target/release/`.

## Troubleshooting

### Connection Issues

If you see connection errors to the Rust helper in development mode, ensure:

1. The mock helper is running (check logs in Electron's console)
2. No other application is using port 17400
3. The `AUTOMATION_SERVER_URL` environment variable is set to `http://127.0.0.1:17400`

### Database Issues

If you encounter database errors:

1. Check if the `data` directory exists and is writable
2. Delete the SQLite database file to start fresh: `rm data/betterman.db`
3. Check the database URL in environment variables

### Electron Packaging Issues

If Electron packaging fails:

1. Clear the `dist` directory: `rm -rf electron/dist`
2. Clear npm cache: `npm cache clean --force`
3. Reinstall dependencies: `cd electron && npm install`