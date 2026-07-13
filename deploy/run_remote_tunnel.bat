@echo off
rem Start Cloudflare Tunnel for remote (no VPN) access to the same IIS app.
rem Requires: IIS + FuelApp API already running (LAN path unchanged).
rem See REMOTE_ACCESS.TXT
setlocal
cd /d "%~dp0\.."

set "CLOUDFLARED=C:\Program Files\cloudflared\cloudflared.exe"
if not exist "%CLOUDFLARED%" set "CLOUDFLARED=C:\Program Files (x86)\cloudflared\cloudflared.exe"

set "CF_CONFIG=%USERPROFILE%\.cloudflared\config.yml"

echo.
echo === Fuel App: Cloudflare Tunnel (remote access) ===
echo.

if not exist "%CLOUDFLARED%" (
    echo [ERROR] cloudflared not found. Install from REMOTE_ACCESS.TXT
    exit /b 1
)

if not exist "%CF_CONFIG%" (
    echo [ERROR] Missing %CF_CONFIG%
    echo Copy deploy\cloudflared.config.example.yml and edit tunnel ID + credentials.
    exit /b 1
)

echo Config:  %CF_CONFIG%
echo Origin:  IIS https://127.0.0.1:443  ^(fuelapp.mteinc.net^)
echo Public:  https://fuelapp.mteinc.net
echo Office:  internal DNS A -^> 10.10.20.40 ^(unchanged^)
echo.
echo Starting tunnel in this window. Ctrl+C to stop.
echo For auto-start: deploy\install_cloudflared_service.ps1
echo.

"%CLOUDFLARED%" tunnel --config "%CF_CONFIG%" run
endlocal
