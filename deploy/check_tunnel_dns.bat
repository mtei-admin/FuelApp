@echo off
rem DNS checklist for fuelapp-api.mteinc.net Cloudflare tunnel
setlocal
echo.
echo === Fuel App Tunnel DNS ===
echo.
echo Tunnel ID: cbba9bda-5122-41b9-96a6-94c2b5594683
echo Hostname:  fuelapp-api.mteinc.net
echo CNAME to:  cbba9bda-5122-41b9-96a6-94c2b5594683.cfargotunnel.com
echo.
echo 1. Add this CNAME at whoever hosts mteinc.net DNS:
echo      Name:   fuelapp-api
echo      Target: cbba9bda-5122-41b9-96a6-94c2b5594683.cfargotunnel.com
echo.
echo 2. If mteinc.net is on Cloudflare, run instead:
echo      cloudflared tunnel route dns fuelapp-api fuelapp-api.mteinc.net
echo.
echo 3. Restart tunnel after config change:
echo      cloudflared tunnel run fuelapp-api
echo.
echo 4. Test (after DNS propagates):
echo      https://fuelapp-api.mteinc.net/api/health
echo.
echo Checking DNS now...
nslookup fuelapp-api.mteinc.net 8.8.8.8
echo.
endlocal
