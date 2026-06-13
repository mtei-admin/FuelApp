@echo off
rem Production launcher — FastAPI on localhost (IIS serves React from frontend\dist)
setlocal
cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found. Run deploy\install_windows.ps1 first.
    exit /b 1
)

if not exist "frontend\dist\index.html" (
    echo [WARN] frontend\dist not found. Run deploy\build_frontend.bat before using IIS.
)

".venv\Scripts\python.exe" -m pip install -q -r api\requirements.txt
set SERVE_FRONTEND=false
".venv\Scripts\python.exe" -m uvicorn api.main:app --host 127.0.0.1 --port 8000

endlocal
