# Rust Helper Setup Guide

BettermanAI uses a local Rust helper application to execute automation tasks on your computer. This guide explains how to set up and connect to the Rust helper.

## Architecture Overview

The BettermanAI application consists of two main components:

1. **Web Application (Replit-hosted)**: The main interface where you manage automations, view patterns, and access metrics.

2. **Rust Helper (Local)**: A lightweight Rust application running on your local machine that:
   - Controls mouse and keyboard actions
   - Manages window focus
   - Executes TagUI automation scripts
   - Captures screenshots
   - Monitors system events

## Setting Up the Rust Helper

### Prerequisites
- Rust installed on your system (rust 1.76.0 or later recommended)
- TagUI installed for automation script execution

### Installation Steps

1. Clone the Rust helper repository:
   ```
   git clone https://github.com/bettermanai/automation-helper
   cd automation-helper
   ```

2. Build the helper application:
   ```
   cargo build --release
   ```

3. Run the helper application:
   ```
   ./target/release/automation-helper
   ```

The helper will start an Actix-Web server on `http://127.0.0.1:17400`.

## Connecting BettermanAI to the Rust Helper

1. In the BettermanAI web interface, click the **Helper API** button in the top navigation bar.

2. Enter the URL of your local Rust helper: `http://127.0.0.1:17400`

3. Click **Test & Save Connection**.

4. If the connection is successful, you'll see a green confirmation message, and the application will reload.

## Troubleshooting

If the connection test fails:

1. **Check if the helper is running**: Make sure the Rust helper is running on your local machine.

2. **Verify the URL**: The default URL is `http://127.0.0.1:17400`. Make sure you entered it correctly.

3. **Check for firewall issues**: Your firewall may be blocking the connection. Check your firewall settings and allow the helper application.

4. **Check the logs**: Look at the terminal where the Rust helper is running for any error messages.

## Additional Information

- The Rust helper's REST API provides endpoints for controlling mouse, keyboard, and window actions.
- All automation commands sent from the web interface are executed locally by the Rust helper.
- The web interface and Rust helper communicate over HTTP, so they can be run on different machines if needed.

For more detailed information, see the [Rust Helper API Documentation](https://github.com/bettermanai/automation-helper/docs/api.md).