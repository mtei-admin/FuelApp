@echo off
rem One-shot API setup: deps, database, frontend build, then start LAN server
setlocal
cd /d "%~dp0\.."

echo === Fuel App API Setup ===
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [1/5] Creating virtual environment...
    powershell -ExecutionPolicy Bypass -File deploy\install_windows.ps1
    if errorlevel 1 exit /b 1
) else (
    echo [1/5] Virtual environment found.
)

echo [2/5] Installing API dependencies...
".venv\Scripts\python.exe" -m pip install -q -r api\requirements.txt
if errorlevel 1 exit /b 1

echo [3/5] Initializing database...
".venv\Scripts\python.exe" -c "from pathlib import Path; from src.database import init_database; init_database(str(Path('data')/'fuel_system.db'))"
if errorlevel 1 exit /b 1

echo [4/5] Building React frontend...
call deploy\build_frontend.bat
if errorlevel 1 exit /b 1

echo.
echo [5/5] Setup complete.
echo.
echo NEXT STEPS:
echo   1. Create admin user (first time only):
echo        .\.venv\Scripts\python.exe init_admin.py
echo.
echo   2. Open firewall (Administrator PowerShell):
echo        powershell -ExecutionPolicy Bypass -File deploy\open_firewall.ps1
echo.
echo   3. Start the app (React + API on port 8000):
echo        deploy\run_lan.bat
echo.
echo   4. Open in browser:
echo        http://10.10.20.40:8000
echo        (or http://YOUR-SERVER-IP:8000)
echo.
echo   For IIS + HTTPS or Windows Service, see DEPLOYMENT.TXT
echo.
endlocal
