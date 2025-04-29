@echo off
echo === BettermanAI Flask Server Only ===
echo.

echo Setting up environment...

:: Create data directory
if not exist data mkdir data

:: Set environment variables
set NODE_ENV=development
set FLASK_APP=main.py
set DATABASE_URL=sqlite:///%CD%\data\betterman.db
echo √ Environment variables set

echo.
echo Starting Flask server on http://localhost:5000
echo Press Ctrl+C to stop the server when done.
echo.

:: Run Flask directly with main.py as the entry point
python main.py

echo.
echo Flask server has stopped.
echo.
pause