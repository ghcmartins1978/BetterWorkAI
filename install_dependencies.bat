@echo off
echo === BettermanAI Dependencies Installation ===
echo.

echo Installing Python dependencies...
echo This may take a few minutes...

:: Install core dependencies first
echo Step 1/5: Installing core dependencies (Flask, SQLAlchemy)...
pip install flask flask-sqlalchemy
if %ERRORLEVEL% NEQ 0 (
    echo Failed to install core Python dependencies. Please check your Python installation.
    pause
    exit /b 1
)
echo √ Core dependencies installed

:: Install web and utility dependencies
echo Step 2/5: Installing web and utility dependencies...
pip install gunicorn pyyaml requests websocket-client email-validator
if %ERRORLEVEL% NEQ 0 (
    echo Warning: Some utility dependencies failed to install.
    echo Continuing with other dependencies...
)
echo √ Web and utility dependencies installed

:: Install database dependencies
echo Step 3/5: Installing database dependencies...
pip install psycopg2-binary
if %ERRORLEVEL% NEQ 0 (
    echo Warning: Database driver failed to install. SQLite will work, but PostgreSQL might not.
    echo Continuing with other dependencies...
)
echo √ Database dependencies installed

:: Install AI and data science dependencies
echo Step 4/5: Installing AI and data science dependencies...
pip install numpy pillow openai trafilatura psutil
if %ERRORLEVEL% NEQ 0 (
    echo Warning: Some AI dependencies failed to install.
    echo Continuing with other dependencies...
)
echo √ AI dependencies installed

:: Install media dependencies (most likely to fail)
echo Step 5/5: Installing media dependencies (may require system libraries)...
pip install pyaudio soundfile opencv-python
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo -----------------------------------
    echo Some media dependencies failed to install. This is common on Windows.
    echo.
    echo For PyAudio:
    echo   Download a pre-built wheel from: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
    echo   Then install with: pip install C:\path\to\downloaded\PyAudio‑0.2.11‑cp39‑cp39‑win_amd64.whl
    echo.
    echo For OpenCV:
    echo   Try: pip install opencv-python-headless
    echo.
    echo For other issues:
    echo   Install Microsoft Visual C++ Build Tools from:
    echo   https://visualstudio.microsoft.com/visual-cpp-build-tools/
    echo -----------------------------------
    echo.
    echo The application should still work with limited functionality.
)
echo.
echo √ Python dependencies installation completed with necessary components

echo.
echo Installing Express and CORS globally for mock helper...
npm install -g express cors
if %ERRORLEVEL% NEQ 0 (
    echo Warning: Failed to install Express and CORS globally.
    echo Attempting to continue with local installation...
)

echo.
echo Installing Node.js dependencies...
cd electron
npm install
if %ERRORLEVEL% NEQ 0 (
    echo Failed to install Node.js dependencies. Check the error messages above.
    pause
    exit /b 1
)

echo.
echo Installing Express and CORS locally in electron folder...
npm install express cors
if %ERRORLEVEL% NEQ 0 (
    echo Warning: Failed to install Express and CORS locally.
    echo The mock helper may not work properly.
)
echo √ Node.js dependencies installed

echo.
echo === All Dependencies Successfully Installed ===
echo.
echo You can now run the application using:
echo   - setup_dev_windows.bat (for development)
echo   - cd electron && npm run win-dev (manual start)
echo.
pause