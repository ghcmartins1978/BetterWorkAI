@echo off
echo === BettermanAI Quick Start (Local Electron with Rust Helper) ===
echo.

echo Setting up environment...

:: Create data directory
if not exist data mkdir data

:: Clean up any existing processes
echo Cleaning up any existing processes...
taskkill /f /fi "WINDOWTITLE eq Flask Server*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq Rust Helper*" > nul 2>&1
:: Also try to kill by process name
taskkill /f /im "betterman_helper.exe" > nul 2>&1

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
echo   3. Build the Rust helper using: build_rust_helper.bat
echo.
echo Press Ctrl+C to stop the application when done
echo.

:: Check if Rust helper binary exists
set RUST_HELPER_PATH=%CD%\electron\rust_helper\betterman_helper.exe
if not exist "%RUST_HELPER_PATH%" (
    echo ERROR: Rust helper binary not found at %RUST_HELPER_PATH%
    echo Please build the Rust helper first using build_rust_helper.bat
    goto :end
)

:: Start the Flask server in a new command window
start cmd /c "title Flask Server && python -m flask run --host=0.0.0.0 --port=5000"

:: Wait for Flask to start
echo Waiting for Flask server to start...
timeout /t 3 > nul

:: Start the Rust helper in another window
cd electron\rust_helper
start cmd /c "title Rust Helper && betterman_helper.exe"
cd ..\..

:: Wait for the Rust helper to start
echo Waiting for Rust helper to start...
timeout /t 2 > nul

:: Start Electron pointing to the Flask app
echo Starting Electron...
cd electron
node_modules\.bin\electron .
cd ..

echo.
echo BettermanAI has closed.
echo Terminating Flask server and Rust helper...
:: Find and kill the Flask and Rust helper processes
taskkill /f /fi "WINDOWTITLE eq Flask Server*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq Rust Helper*" > nul 2>&1
:: Also try to kill by process name
taskkill /f /im "betterman_helper.exe" > nul 2>&1
taskkill /f /im "python.exe" /fi "WINDOWTITLE eq Flask*" > nul 2>&1

:end
echo.
echo Press any key to exit...
pause > nul