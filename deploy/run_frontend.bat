@echo off
rem Start React frontend dev server (proxies /api to localhost:8000)
setlocal
cd /d "%~dp0\..\frontend"

where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm not found. Install Node.js from https://nodejs.org/
    exit /b 1
)

if not exist "node_modules" (
    echo Installing frontend dependencies...
    call npm install
)

call npm run dev
endlocal
