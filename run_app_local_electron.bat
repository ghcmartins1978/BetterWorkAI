@echo off
echo === BettermanAI Quick Start (Local Electron) ===
echo.

echo Setting up environment...

:: Create data directory
if not exist data mkdir data

:: Clean up any existing processes
echo Cleaning up any existing processes...
taskkill /f /fi "WINDOWTITLE eq Flask Server*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq Mock Rust Helper*" > nul 2>&1
:: Also try to kill by process name
taskkill /f /im "node.exe" /fi "WINDOWTITLE eq Mock*" > nul 2>&1

:: Set environment variables
set NODE_ENV=development
set RUNNING_IN_ELECTRON=1
set DATABASE_URL=sqlite:///%CD%\data\betterman.db
set AUTOMATION_SERVER_URL=http://127.0.0.1:17400
set FLASK_APP=main.py
echo √ Environment variables set

echo.
echo === Starting BettermanAI ===
echo.
echo If this is your first time running the app:
echo   1. Make sure you've installed dependencies using: install_dependencies.bat
echo   2. Install Electron locally using: install_electron.bat
echo.
echo Press Ctrl+C to stop the application when done
echo.

:: Start the Flask server in a new command window
start cmd /c "title Flask Server && python -m flask run --host=0.0.0.0 --port=5000"

:: Wait for Flask to start
echo Waiting for Flask server to start...
timeout /t 3 > nul

:: Start the mock server in another window
cd electron
start cmd /c "title Mock Rust Helper && node mock_helper.js"

:: Wait for the mock server to start
echo Waiting for mock helper to start...
timeout /t 2 > nul

:: Start Electron pointing to the Flask app
echo Starting Electron...
node_modules\.bin\electron .

echo.
echo BettermanAI has closed.
echo Terminating Flask server and mock helper...
:: Find and kill the Flask and mock helper processes
taskkill /f /fi "WINDOWTITLE eq Flask Server*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq Mock Rust Helper*" > nul 2>&1
:: Also try to kill by process name
taskkill /f /im "node.exe" /fi "WINDOWTITLE eq Mock*" > nul 2>&1
taskkill /f /im "python.exe" /fi "WINDOWTITLE eq Flask*" > nul 2>&1

echo.
echo Press any key to exit...
pause > nul