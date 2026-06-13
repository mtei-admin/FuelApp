@echo off
rem Build React frontend for production (output: frontend\dist)
setlocal
cd /d "%~dp0\.."

where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js/npm not found. Install Node.js LTS from https://nodejs.org/
    exit /b 1
)

if not exist "frontend\package.json" (
    echo [ERROR] frontend\package.json not found.
    exit /b 1
)

cd frontend
call npm install
if errorlevel 1 exit /b 1
call npm run build
if errorlevel 1 exit /b 1

echo [OK] Built frontend\dist — ready for IIS or deploy\run_lan.bat
endlocal
