@echo off
echo ===================================================
echo Starting TTS WebUI Workbench Frontend
echo ===================================================

cd /d "%~dp0\frontend"

if not exist node_modules (
    echo Error: node_modules directory not found! Please run install_frontend.bat first.
    pause
    exit /b 1
)

echo Starting Vite Dev Server...
call npm run dev
