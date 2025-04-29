@echo off
echo === BettermanAI Process Cleanup ===
echo.

echo This script will kill all processes related to BettermanAI.
echo This is useful if you need to restart from a clean state.
echo.

echo Press any key to continue or Ctrl+C to cancel...
pause > nul

echo.
echo Cleaning up processes...

:: Try to kill by window title
echo - Searching for processes by window title...
taskkill /f /fi "WINDOWTITLE eq Flask Server*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq Mock Rust Helper*" > nul 2>&1

:: Try to kill specific Python and Node processes that might be related
echo - Searching for Python processes running Flask...
taskkill /f /im "python.exe" /fi "WINDOWTITLE eq Flask*" > nul 2>&1
taskkill /f /im "python.exe" /fi "COMMANDLINE eq *flask*" > nul 2>&1
taskkill /f /im "python.exe" /fi "COMMANDLINE eq *gunicorn*" > nul 2>&1

echo - Searching for Node.js processes running mock helper...
taskkill /f /im "node.exe" /fi "WINDOWTITLE eq Mock*" > nul 2>&1
taskkill /f /im "node.exe" /fi "COMMANDLINE eq *mock_helper*" > nul 2>&1

echo - Searching for Electron processes...
taskkill /f /im "electron.exe" > nul 2>&1

echo.
echo Process cleanup completed.
echo You can now restart the application with a clean state.
echo.

pause