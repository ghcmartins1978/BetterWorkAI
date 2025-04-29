@echo off
echo === Installing Electron for BettermanAI ===
echo.

cd electron

echo Creating package.json if it doesn't exist...
if not exist package.json (
  echo {
  echo   "name": "betterman-ai-electron",
  echo   "version": "1.0.0",
  echo   "description": "BettermanAI Electron App",
  echo   "main": "main.js",
  echo   "scripts": {
  echo     "start": "electron .",
  echo     "dev": "cross-env NODE_ENV=development electron .",
  echo     "win-dev": "set NODE_ENV=development && .\\node_modules\\.bin\\electron ."
  echo   }
  echo } > package.json
  echo Created package.json
)

echo Installing Electron and required dependencies...
npm install --save electron electron-updater electron-builder electron-log cross-env
if %ERRORLEVEL% NEQ 0 (
  echo Failed to install Electron. Please make sure npm is installed and working.
  pause
  exit /b 1
)

echo Installing Express and CORS for mock helper...
npm install --save express cors
if %ERRORLEVEL% NEQ 0 (
  echo Warning: Failed to install Express and CORS.
  echo The mock helper may not work correctly.
)

echo.
echo === Electron Installation Complete ===
echo.
echo You can now run the application using:
echo - run_app_local_electron.bat
echo.
pause