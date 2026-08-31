@echo off
echo ===================================================
echo Starting TTS WebUI Workbench Backend
echo ===================================================

cd /d "%~dp0"

if not exist backend\venv (
    echo Error: Python virtual environment not found! Please run install_backend.bat first.
    pause
    exit /b 1
)

echo Activating virtual environment...
call backend\venv\Scripts\activate.bat

cd backend
echo Launching Uvicorn Server...
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
