@echo off
rem DNS checklist for Fuel App remote access (split-horizon + Cloudflare Tunnel)
rem Primary hostname: fuelapp.mteinc.net (IIS LAN + tunnel remote)
rem Legacy API-only:  fuelapp-api.mteinc.net (Vercel path — optional)
rem See REMOTE_ACCESS.TXT
setlocal
echo.
echo === Fuel App Tunnel / Split-Horizon DNS ===
echo.
echo Primary hostname: fuelapp.mteinc.net
echo   Office:  internal A -^> 10.10.20.40  (IIS)
echo   Remote:  Cloudflare proxied CNAME -^> tunnel -^> IIS
echo.
echo --- fuelapp.mteinc.net via Public DNS (8.8.8.8) ---
nslookup fuelapp.mteinc.net 8.8.8.8
echo.
echo --- fuelapp.mteinc.net via This PC default DNS ---
nslookup fuelapp.mteinc.net
echo.
echo --- fuelapp.mteinc.net via Office DNS (10.10.20.3) ---
nslookup fuelapp.mteinc.net 10.10.20.3
echo.
echo Expect:
echo   Office DNS  -^> 10.10.20.40
echo   Public DNS  -^> Cloudflare IPv4 (e.g. 104.x), not only fd10:...
echo.
echo --- Legacy API hostname (optional) ---
nslookup fuelapp-api.mteinc.net 8.8.8.8
echo.
echo Local API:     http://127.0.0.1:8000/api/health
echo Office app:    https://fuelapp.mteinc.net/api/health
echo Remote app:    https://fuelapp.mteinc.net/api/health  ^(mobile data^)
echo.
endlocal
