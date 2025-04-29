@echo off
echo === BettermanAI Dependencies Installation ===
echo.

echo Installing Python dependencies...
echo This may take a few minutes...
pip install flask flask-sqlalchemy gunicorn pyyaml requests pyaudio soundfile trafilatura numpy opencv-python psutil openai email-validator psycopg2-binary pillow websocket-client
if %ERRORLEVEL% NEQ 0 (
    echo Failed to install Python dependencies. Check the error messages above.
    echo.
    echo You may need to install Microsoft Visual C++ Build Tools for some packages.
    echo Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
    echo.
    echo For PyAudio, you might need to download a pre-built wheel from:
    echo https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
    echo.
    echo For other issues, try installing the core dependencies first:
    echo pip install flask flask-sqlalchemy
    echo.
    pause
    exit /b 1
)
echo √ Python dependencies installed

echo.
echo Installing Node.js dependencies...
cd electron
npm install
if %ERRORLEVEL% NEQ 0 (
    echo Failed to install Node.js dependencies. Check the error messages above.
    pause
    exit /b 1
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