@echo off
echo === BettermanAI Quick Start ===
echo.

echo Setting up environment...

:: Create data directory
if not exist data mkdir data

:: Set environment variables
set NODE_ENV=development
set RUNNING_IN_ELECTRON=1
set DATABASE_URL=sqlite:///%CD%\data\betterman.db
set AUTOMATION_SERVER_URL=http://127.0.0.1:17400
echo √ Environment variables set

echo.
echo === Starting BettermanAI ===
echo.
echo If this is your first time running the app, make sure you've installed dependencies using:
echo   - install_dependencies.bat
echo.
echo Press Ctrl+C to stop the application when done
echo.

:: Start the application
cd electron
npm run win-dev

echo.
echo BettermanAI has closed. Press any key to exit...
pause >nul