@echo off
echo ===================================================
echo Installing TTS WebUI Workbench Backend Dependencies
echo ===================================================

cd /d "%~dp0"

:: Recommended Python Version: 3.11.x
echo Note: Python 3.11 is the recommended version for this project.
echo Python 3.14 may run the WebUI backend, but local AI/TTS models
echo should usually run in separate, isolated Python 3.10/3.11 environments.
echo.

:: Check python availability
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python executable not found in PATH!
    echo Please install Python 3.11 from python.org and add it to your PATH.
    pause
    exit /b 1
)

:: Create python virtual environment
if not exist backend\venv (
    echo Creating python virtual environment...
    python -m venv backend\venv
) else (
    echo Python virtual environment already exists.
)

:: Activate virtual environment and install requirements
echo Activating virtual environment...
call backend\venv\Scripts\activate.bat

echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r backend\requirements.txt

:: Copy env file if not exists
if not exist .env (
    echo Creating default .env file from .env.example...
    copy .env.example .env
)

echo.
echo Backend installation completed successfully!
echo ===================================================
pause
