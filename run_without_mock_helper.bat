@echo off
echo === BettermanAI Development Mode (No Mock Helper) ===
echo.

echo This script runs BettermanAI without the mock helper.
echo Only the Flask server will be started, and automation features will be disabled.
echo.

:: Create data directory
if not exist data mkdir data

:: Set environment variables
set NODE_ENV=development
set RUNNING_IN_ELECTRON=1
set DATABASE_URL=sqlite:///%CD%\data\betterman.db
set SKIP_MOCK_HELPER=1

echo Starting Flask server on http://localhost:5000
echo Press Ctrl+C to stop the server when done.
echo.

python -m flask run --host=0.0.0.0 --port=5000

echo.
echo Flask server has stopped.
echo.
pause