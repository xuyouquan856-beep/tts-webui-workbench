@echo off
echo ===================================================
echo Launching TTS WebUI Workbench Backend and Frontend
echo ===================================================

cd /d "%~dp0"

echo Launching Backend server in new window...
start "TTS Workbench Backend" cmd /c start_backend.bat

echo Launching Frontend server in new window...
start "TTS Workbench Frontend" cmd /c start_frontend.bat

echo.
echo Both servers have been launched.
echo - Backend: http://127.0.0.1:8000
echo - Frontend: http://localhost:5173
echo.
echo Press any key to exit this script (servers will continue running in their own windows).
pause
