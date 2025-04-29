@echo off
echo === BettermanAI Web Interface (Flask Only) ===
echo.

echo Setting up environment...

:: Create data directory
if not exist data mkdir data

:: Set environment variables
set FLASK_APP=main.py
set DATABASE_URL=sqlite:///%CD%\data\betterman.db
set AUTOMATION_SERVER_URL=http://127.0.0.1:17400
echo √ Environment variables set

echo.
echo Starting Flask web server on http://localhost:5000
echo.
echo IMPORTANT: This runs just the web interface without Electron or the mock helper.
echo Some automation features will be disabled.
echo.
echo Press Ctrl+C to stop the server when done.
echo.

:: Start the Flask server
python -m gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app

echo.
echo Flask server has stopped.
echo.
pause