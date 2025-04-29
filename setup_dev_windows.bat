@echo off
echo === BettermanAI Development Setup ===
echo.

echo Checking prerequisites...

:: Check Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo X Python not found. Please install Python 3.8 or higher: https://www.python.org/
    exit /b 1
) else (
    python -c "import sys; print('Python', sys.version.split()[0])"
    echo √ Python found and working
)

:: Check pip
pip --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo X pip not found. Please install pip: https://pip.pypa.io/en/stable/installation/
    exit /b 1
) else (
    echo √ pip found and working
)

:: Check Node.js
node --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo X Node.js not found. Please install Node.js 18 or higher: https://nodejs.org/
    exit /b 1
) else (
    echo √ Node.js found and working
)

:: Check npm
npm --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo X npm not found. Please install Node.js which includes npm: https://nodejs.org/
    exit /b 1
) else (
    echo √ npm found and working
)

echo.
echo Setting up environment...

:: Install Python dependencies
echo.
echo Installing Python dependencies...
pip install flask flask-sqlalchemy gunicorn pyyaml requests pyaudio soundfile trafilatura numpy opencv-python psutil openai email-validator psycopg2-binary pillow websocket-client
if %ERRORLEVEL% NEQ 0 (
    echo Failed to install Python dependencies. Check the error messages above.
    echo You may need to install Visual C++ Build Tools for some packages.
    echo Try installing dependencies manually:
    echo pip install flask flask-sqlalchemy
    exit /b 1
)
echo √ Python dependencies installed

:: Install Node.js dependencies
echo.
echo Installing Node.js dependencies...
cd electron
npm install
if %ERRORLEVEL% NEQ 0 (
    echo Failed to install Node.js dependencies. Check the error messages above.
    exit /b 1
)
echo √ Node.js dependencies installed

:: Create data directory
echo.
echo Setting up data directory...
cd ..
if not exist data mkdir data
echo √ Data directory created

:: Set environment variables
echo.
echo Setting up environment variables...
set NODE_ENV=development
set RUNNING_IN_ELECTRON=1
set DATABASE_URL=sqlite:///%CD%\data\betterman.db
set AUTOMATION_SERVER_URL=http://127.0.0.1:17400
echo √ Environment variables set

echo.
echo === Setup Complete ===
echo.
echo To run the application:
echo cd electron
echo npm run win-dev
echo.
echo Press any key to start BettermanAI...
pause >nul

:: Start the application
cd electron
npm run win-dev