@echo off
echo === BettermanAI OpenAI API Key Setup ===
echo.

echo This script will help you set up your OpenAI API key for BettermanAI.
echo Your API key will be stored as an environment variable.
echo.

set /p OPENAI_KEY="Enter your OpenAI API key: "

echo.
if "%OPENAI_KEY%"=="" (
    echo No API key provided. Operation cancelled.
    exit /b 1
)

echo Setting OpenAI API key...
setx OPENAI_API_KEY "%OPENAI_KEY%"

echo.
echo API key has been set as an environment variable.
echo You will need to RESTART your command prompt or terminal for the change to take effect.
echo.
echo Press any key to exit...
pause > nul