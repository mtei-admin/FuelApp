@echo off
rem LEGACY: API-only tunnel for Vercel (separate API hostname).
rem Preferred remote access for staff: REMOTE_ACCESS.TXT + deploy\run_remote_tunnel.bat
rem (same hostname fuelapp.mteinc.net through IIS).
setlocal
cd /d "%~dp0\.."

set "CLOUDFLARED=C:\Program Files (x86)\cloudflared\cloudflared.exe"
if not exist "%CLOUDFLARED%" set "CLOUDFLARED=C:\Program Files\cloudflared\cloudflared.exe"

echo.
echo === Fuel App: API + Tunnel (LEGACY Vercel path) ===
echo Prefer REMOTE_ACCESS.TXT for office+remote on https://fuelapp.mteinc.net
echo.

call "%~dp0stop_api.bat"

echo Starting API in a new window...
start "Fuel API" cmd /k "%~dp0run_production.bat"

timeout /t 3 /nobreak >nul

if not exist "%CLOUDFLARED%" (
    echo [ERROR] cloudflared not found. Install from REMOTE_ACCESS.TXT / TUNNEL_SETUP.TXT
    exit /b 1
)

echo Starting Cloudflare tunnel in a new window...
start "Cloudflare Tunnel" cmd /k ""%CLOUDFLARED%" tunnel run fuelapp-api"

echo.
echo API:    http://127.0.0.1:8000/api/health
echo Public: https://fuelapp-api.mteinc.net/api/health
echo.
echo If login fails from office PCs, add this CNAME on internal DNS ^(10.10.20.3^):
echo   fuelapp-api.mteinc.net -^> cbba9bda-5122-41b9-96a6-94c2b5594683.cfargotunnel.com
echo.
endlocal
