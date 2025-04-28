# BettermanAI Rust Helper Setup Guide

This document provides step-by-step instructions for setting up the BettermanAI Rust Helper on your local machine. The Rust Helper is a critical component that enables system-level monitoring and automation execution.

## Why Do I Need the Rust Helper?

**BettermanAI is a hybrid application** split between:
- The web interface (running on Replit's servers in the cloud)
- The automation capabilities (which must run locally on your computer)

For privacy and security reasons, all automation code that monitors and controls your desktop runs locally on your machine, not in the cloud. The Rust Helper provides this critical local functionality.

**Without the Rust Helper connected, you will not be able to:**
- Record or run automation macros
- Capture screenshots or monitor system events
- Receive automation suggestions

## What is the Rust Helper?

The Rust Helper is a local application written in Rust that provides:

1. System-level event monitoring (mouse, keyboard, window changes)
2. Macro execution through TagUI integration
3. Screenshot capture and analysis
4. REST API for the web interface to communicate with
5. Security layer to ensure your data stays private

## Prerequisites

- Windows 10/11, macOS, or Linux
- Administrator/sudo privileges for installation
- Internet connection for downloading the helper

## Installation Steps

### Step 1: Download the Rust Helper

Download the appropriate version for your operating system from the [releases page](https://github.com/betterman-ai/rust-helper/releases/latest).

- Windows: `betterman_helper-windows-x64.zip`
- macOS: `betterman_helper-macos.dmg`
- Linux: `betterman_helper-linux-x64.tar.gz`

### Step 2: Install the Helper

#### Windows
1. Extract the ZIP file to a folder of your choice
2. Right-click on `betterman_helper.exe` and select "Run as Administrator" for the first run
3. If prompted by Windows Defender or antivirus, allow the application to run

#### macOS
1. Open the DMG file
2. Drag the BettermanHelper app to your Applications folder
3. When first launching, right-click the app and select "Open" to bypass Gatekeeper
4. In System Preferences > Security & Privacy, allow the app under Accessibility and Input Monitoring

#### Linux
1. Extract the tar.gz file: `tar -xzf betterman_helper-linux-x64.tar.gz`
2. Make the binary executable: `chmod +x betterman_helper`
3. Install required dependencies: `sudo apt install libxtst-dev libxdo-dev` (for Debian/Ubuntu)

### Step 3: Configure the Helper

1. The first time you run the helper, it will create a configuration file in:
   - Windows: `%APPDATA%\BettermanAI\config.toml`
   - macOS: `~/Library/Application Support/BettermanAI/config.toml`
   - Linux: `~/.config/bettermanai/config.toml`

2. The default configuration should work in most cases, but you can customize settings like:
   - Port number (default: 17400)
   - Logging level
   - TagUI installation path

### Step 4: Connect the Web Interface

1. Launch the helper application if it's not already running
2. On the BettermanAI web interface, you'll see a connection status alert at the top of your dashboard
3. Click the "Setup Helper" button to open the connection modal
4. Make sure the URL in the connection settings shows: `http://127.0.0.1:17400`
5. Click "Test & Save Connection" to verify
6. If successful, you'll see a green success message and the dashboard will update to show connected status

> **Note:** The website automatically checks for connection on every page load. If you see the helper is connected (green status), you don't need to do anything else!

## Troubleshooting

### Connection Issues
- Ensure the helper is running (look for the icon in system tray)
- Check if the port 17400 is not blocked by firewall
- Verify the URL is exactly `http://127.0.0.1:17400` (no trailing slash)

### Permission Issues
- On Windows and macOS, the helper needs elevated permissions for monitoring
- On Linux, ensure the helper has access to X11 events: `xhost +local:` may help

### TagUI Integration
- The helper will attempt to find TagUI automatically
- If it can't find TagUI, set the path manually in the config file

## API Reference

The Rust Helper exposes the following REST API endpoints:

- `GET /api/status` - Get current status and system information
- `POST /api/monitoring` - Enable/disable monitoring
- `GET /api/events` - Get recent system events
- `POST /api/execute` - Execute a macro

For developers, full API documentation is available at [http://127.0.0.1:17400/docs](http://127.0.0.1:17400/docs) when the helper is running.

## Support

If you encounter any issues with the Rust Helper, please:

1. Check the logs at:
   - Windows: `%APPDATA%\BettermanAI\logs\`
   - macOS: `~/Library/Logs/BettermanAI/`
   - Linux: `~/.local/share/bettermanai/logs/`

2. Report issues on the [GitHub repository](https://github.com/betterman-ai/rust-helper/issues) with:
   - Your operating system and version
   - Helper version
   - Steps to reproduce
   - Log files if possible