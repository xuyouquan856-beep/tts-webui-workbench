@echo off
echo ===================================================
echo Building Backend Executable with PyInstaller
echo ===================================================

set "PYTHON_EXE=python"
if exist ".\backend\venv\Scripts\python.exe" set "PYTHON_EXE=.\backend\venv\Scripts\python.exe"

"%PYTHON_EXE%" -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PyInstaller is unavailable. Run: python -m pip install pyinstaller
    exit /b 1
)

:: Run PyInstaller in onefile mode
"%PYTHON_EXE%" -m PyInstaller --noconfirm --onefile ^
    --distpath .\desktop-sidecar ^
    --name backend_sidecar ^
    --paths .\backend ^
    --hidden-import uvicorn.logging ^
    --hidden-import uvicorn.loops ^
    --hidden-import uvicorn.loops.auto ^
    --hidden-import uvicorn.protocols ^
    --hidden-import uvicorn.protocols.http ^
    --hidden-import uvicorn.protocols.http.auto ^
    --hidden-import uvicorn.protocols.websockets ^
    --hidden-import uvicorn.protocols.websockets.auto ^
    --hidden-import uvicorn.lifespan ^
    --hidden-import uvicorn.lifespan.on ^
    --hidden-import sqlalchemy.ext.declarative ^
    --hidden-import python_multipart ^
    .\backend\desktop_entry.py

if %ERRORLEVEL% neq 0 (
    echo [ERROR] PyInstaller compilation failed!
    exit /b %ERRORLEVEL%
)

:: Copy and rename sidecar binary for Tauri target
echo Copying sidecar binary to src-tauri\binaries...
if not exist ".\src-tauri\binaries" (
    mkdir ".\src-tauri\binaries"
)
if exist ".\desktop-sidecar\backend_sidecar.exe" (
    copy /Y ".\desktop-sidecar\backend_sidecar.exe" ".\src-tauri\binaries\backend_sidecar-x86_64-pc-windows-msvc.exe"
    copy /Y ".\desktop-sidecar\backend_sidecar.exe" ".\src-tauri\binaries\backend_sidecar.exe"
    echo [SUCCESS] Copied and renamed sidecar executable successfully.
) else (
    echo [ERROR] Compiled binary not found!
    exit /b 1
)

echo [SUCCESS] Backend sidecar executable successfully built and copied to .\src-tauri\binaries\
