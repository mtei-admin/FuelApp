@echo off
rem Legacy Streamlit UI (deprecated — use React + FastAPI for production)
setlocal
cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found. Run deploy\install_windows.ps1 first.
    exit /b 1
)

echo [WARN] Streamlit is deprecated. Production uses React + FastAPI. See MIGRATION.TXT.
".venv\Scripts\python.exe" -m streamlit run app.py ^
    --server.address 127.0.0.1 ^
    --server.port 8501 ^
    --server.headless true ^
    --browser.gatherUsageStats false

endlocal
