@echo off
rem Start FastAPI backend (development)
setlocal
cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found. Run deploy\install_windows.ps1 first.
    exit /b 1
)

".venv\Scripts\python.exe" -m pip install -q -r api\requirements.txt
".venv\Scripts\python.exe" -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000

endlocal
