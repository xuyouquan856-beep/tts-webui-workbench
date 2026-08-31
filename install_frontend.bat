@echo off
echo ====================================================
echo Installing TTS WebUI Workbench Frontend Dependencies
echo ====================================================

cd /d "%~dp0\frontend"

if not exist package.json (
    echo Error: package.json not found in frontend directory!
    pause
    exit /b 1
)

echo Installing npm packages...
call npm install

echo.
echo Frontend installation completed successfully!
echo ====================================================
pause
