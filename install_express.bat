@echo off
echo === Installing Express for BettermanAI Mock Helper ===
echo.

echo Attempting to install Express and CORS modules...

:: First try global installation
echo Installing Express and CORS globally...
npm install -g express cors
if %ERRORLEVEL% NEQ 0 (
    echo Warning: Failed to install Express and CORS globally.
    echo Attempting local installation instead...
) else (
    echo √ Express and CORS installed globally
)

:: Then try installation in the project root
echo.
echo Installing Express and CORS in project root...
npm init -y
npm install express cors
if %ERRORLEVEL% NEQ 0 (
    echo Warning: Failed to install Express and CORS in project root.
    echo Attempting installation in electron folder...
) else (
    echo √ Express and CORS installed in project root
)

:: Then try installation in the electron directory
cd electron
echo.
echo Installing Express and CORS in electron directory...
npm install express cors
if %ERRORLEVEL% NEQ 0 (
    echo Warning: Failed to install Express and CORS in electron directory.
    echo.
    echo !!! Express modules could not be installed !!!
    echo The mock helper will not work without these modules.
    echo.
    echo Possible solutions:
    echo 1. Run this script as administrator
    echo 2. Check your internet connection
    echo 3. Try manual installation: npm install express cors
    pause
    exit /b 1
) else (
    echo √ Express and CORS installed in electron directory
)

echo.
echo === Express Modules Successfully Installed ===
echo.
echo You can now run the application using:
echo   - run_app.bat
echo   - cd electron && npm run win-dev
echo.
pause