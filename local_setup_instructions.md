# BettermanAI Local Automation Server Setup

This guide will help you set up the local automation server component of BettermanAI on your computer. This server allows the Replit-hosted web application to control and monitor your system for automation purposes.

## Prerequisites

1. Python 3.7+ installed on your computer
2. Basic knowledge of running Python scripts and terminal commands
3. Administrative access to install packages

## Installation Steps

### 1. Install Required Python Packages

Open a terminal/command prompt and run:

```bash
pip install flask flask-cors pynput pyautogui pygetwindow requests python-dotenv ngrok
```

### 2. Set Up Ngrok

1. Download and install ngrok from [https://ngrok.com/download](https://ngrok.com/download)
2. Sign up for a free ngrok account to get your authtoken
3. Configure ngrok with your authtoken:
   ```bash
   ngrok config add-authtoken YOUR_AUTHTOKEN
   ```

### 3. Running the Local Automation Server

1. Download the `automation_server.py` file from the Replit project
2. Open a terminal/command prompt and navigate to the folder where you saved the file
3. Run the server:
   ```bash
   python automation_server.py
   ```
4. The server will start on port 5001

### 4. Create a Tunnel with Ngrok

In a new terminal window, run:

```bash
ngrok http 5001
```

Ngrok will display a URL like `https://xxxx-xxxx-xxxx.ngrok.io`. This is your public URL that connects to your local server.

## Connecting the Replit App to Your Local Server

1. Copy the ngrok URL from the ngrok terminal
2. In the Replit project, add the ngrok URL as an environment variable:
   - Add `AUTOMATION_SERVER_URL` with the value of your ngrok URL

## Testing the Connection

1. Make sure both the local automation server and ngrok are running
2. Open the Replit BettermanAI project in your browser
3. Go to the Settings page
4. Click "Test Connection" to verify the connection to your local machine

## Using the System

Once connected, the BettermanAI web app will be able to:
- Monitor your mouse, keyboard, and window activities
- Detect patterns in your behavior
- Execute automation macros on your local machine

## Troubleshooting

### Connection Issues

- Ensure ngrok is running and the URL is current (ngrok URLs expire after a restart)
- Check that your local server is running and accessible at http://localhost:5001
- Verify that no firewall is blocking the connection

### Permission Issues

For monitoring and control functionality, your system may require:
- Accessibility permissions on macOS
- Admin rights on Windows
- X11 permissions on Linux

### Automation Not Working

- Check the logs in the local server terminal for error messages
- Ensure the automation server has the necessary permissions to control your system
- Test basic functionality by using the "Test Connection" feature in the Settings page

## Security Notes

- The ngrok URL provides remote access to your computer's input devices
- Only share the URL with trusted sources
- The local server only responds to requests from the BettermanAI web app
- Consider shutting down the server and ngrok when not in use