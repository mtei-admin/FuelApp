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
rem Cloudflare Zero Trust still routes fuelapp.mteinc.net to :8000 (overrides local
rem config.yml). Serve the React build so remote users get the login page, not JSON.
set SERVE_FRONTEND=true
".venv\Scripts\python.exe" -m uvicorn api.main:app --host 127.0.0.1 --port 8000

endlocal
