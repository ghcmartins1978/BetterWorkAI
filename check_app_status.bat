@echo off
echo === BettermanAI Status Check ===
echo.

echo Checking environment...
echo.

echo Python version:
python --version

echo.
echo Node.js version:
node --version

echo.
echo NPM version:
npm --version

echo.
echo Environment variables:
echo - OPENAI_API_KEY: %OPENAI_API_KEY:x=*%
if "%OPENAI_API_KEY%"=="" (
    echo   [NOT SET] You need to set this for AI features to work
    echo   Run set_openai_key.bat to set it
) else (
    echo   [SET] API key is available
)

echo.
echo Checking directories:
if exist data (
    echo - data: exists
) else (
    echo - data: missing (will be created when app runs)
)

if exist electron\node_modules (
    echo - electron\node_modules: exists
) else (
    echo - electron\node_modules: missing (run install_electron.bat)
)

echo.
echo === Checking network connectivity ===
ping -n 1 api.openai.com > nul
if %ERRORLEVEL% EQU 0 (
    echo - OpenAI API: Reachable
) else (
    echo - OpenAI API: Unreachable (check internet connection)
)

echo.
echo === Application Status Summary ===
echo.
echo If you see any issues above, please fix them before running the app.
echo.
echo To run the application, use one of these options:
echo 1. run_app_local_electron.bat - Full application with Electron
echo 2. run_flask_web.bat - Just the web interface
echo.
echo For AI features, make sure to set your OpenAI API key using set_openai_key.bat
echo.

pause