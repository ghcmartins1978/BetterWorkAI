@echo off
REM This is a mock TagUI binary for testing purposes on Windows

echo TagUI Runner (Mock)
echo Running script: %1
echo Arguments: %*

REM Check if we're in dry-run mode
echo %* | find "-n" > nul
if not errorlevel 1 (
    echo Running in dry-run mode - no actions will be taken
)

REM Read the script file
if exist %1 (
    echo Script content:
    type %1
) else (
    echo Error: Script file not found: %1
    exit /b 1
)

REM Simulate a running process
echo Processing...
timeout /t 2 > nul
echo DONE

exit /b 0