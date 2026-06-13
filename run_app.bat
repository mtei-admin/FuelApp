@echo off
rem Development launcher — starts FastAPI + Vite dev servers
setlocal
cd /d "%~dp0"

echo Fuel Requisition System — development mode
echo.
echo Starting API (port 8000) and frontend (port 5173) in separate windows...
echo For production, see DEPLOYMENT.TXT
echo.

start "FuelApp API" cmd /k deploy\run_api.bat
start "FuelApp Frontend" cmd /k deploy\run_frontend.bat

endlocal
