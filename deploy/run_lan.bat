@echo off
rem LAN / VPN launcher — FastAPI + React SPA on port 8000 (no IIS, no HTTPS)
setlocal
cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found. Run deploy\install_windows.ps1 first.
    exit /b 1
)

if not exist "frontend\dist\index.html" (
    echo [ERROR] frontend\dist not found. Run deploy\build_frontend.bat first.
    exit /b 1
)

echo [INFO] Serving on http://0.0.0.0:8000 — ensure Windows Firewall allows inbound TCP 8000.
".venv\Scripts\python.exe" -m pip install -q -r api\requirements.txt
set SERVE_FRONTEND=true
".venv\Scripts\python.exe" -m uvicorn api.main:app --host 0.0.0.0 --port 8000

endlocal
