@echo off
REM Script to build the Rust helper for BettermanAI

echo =========================================
echo   Building BettermanAI Rust Helper
echo =========================================

REM Check if Rust is installed
where rustc >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: Rust is not installed.
    echo Please install Rust from https://rustup.rs/
    exit /b 1
)

REM Check if Cargo is installed
where cargo >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: Cargo is not installed.
    echo Please install Rust from https://rustup.rs/
    exit /b 1
)

REM Display versions
echo Rust version:
rustc --version
echo Cargo version:
cargo --version
echo.

REM Directory check
set SCRIPT_DIR=%~dp0
set HELPER_DIR=%SCRIPT_DIR%rust_helper

REM Check if the helper directory exists
if not exist "%HELPER_DIR%" (
    echo Error: Rust helper directory not found at %HELPER_DIR%
    exit /b 1
)

REM Navigate to the helper directory
cd "%HELPER_DIR%"

REM Build the helper in release mode
echo Building the Rust helper in release mode...
cargo build --release
if %ERRORLEVEL% neq 0 (
    echo Error: Failed to build the Rust helper.
    exit /b 1
)

REM Target directory
set TARGET_DIR=%HELPER_DIR%\target\release
set BINARY_NAME=betterman_helper.exe

REM Check if binary exists
if not exist "%TARGET_DIR%\%BINARY_NAME%" (
    echo Error: Built binary not found at %TARGET_DIR%\%BINARY_NAME%
    exit /b 1
)

REM Create the electron/rust_helper directory if it doesn't exist
set ELECTRON_HELPER_DIR=%SCRIPT_DIR%electron\rust_helper
if not exist "%ELECTRON_HELPER_DIR%" mkdir "%ELECTRON_HELPER_DIR%"

REM Copy the binary to the electron/rust_helper directory
echo Copying binary to %ELECTRON_HELPER_DIR%\%BINARY_NAME%
copy "%TARGET_DIR%\%BINARY_NAME%" "%ELECTRON_HELPER_DIR%\%BINARY_NAME%"
if %ERRORLEVEL% neq 0 (
    echo Error: Failed to copy the binary.
    exit /b 1
)

echo.
echo Successfully built and installed the Rust helper.
echo The helper binary is located at: %ELECTRON_HELPER_DIR%\%BINARY_NAME%
echo =========================================