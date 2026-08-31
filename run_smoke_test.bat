@echo off
echo ===================================================
echo Running TTS WebUI Workbench Backend Smoke Test
echo ===================================================

cd /d "%~dp0"

if not exist backend\venv (
    echo Error: Python virtual environment not found! Please run install_backend.bat first.
    pause
    exit /b 1
)

echo Activating virtual environment...
call backend\venv\Scripts\activate.bat

echo Running smoke test script...
set SMOKE_DATA_DIR=%TEMP%\tts-webui-workbench-smoke-%RANDOM%%RANDOM%
python backend/tests/smoke_test.py --data-dir "%SMOKE_DATA_DIR%"
set TEST_EXIT=%ERRORLEVEL%
rmdir /S /Q "%SMOKE_DATA_DIR%" >nul 2>&1
if not "%TEST_EXIT%"=="0" exit /b %TEST_EXIT%

echo.
echo Smoke test completed!
echo ===================================================
pause
