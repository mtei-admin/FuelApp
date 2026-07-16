@echo off
rem Run this on the PC that cannot reach the API (not on the server).
setlocal
echo.
echo === Fuel App - Client DNS Check ===
echo.
echo Your PC must resolve fuelapp.mteinc.net to the server (10.10.20.40).
echo (IIS HTTPS — not on public DNS; office DNS 10.10.20.3 required.)
echo.
echo --- Default DNS (what this PC uses) ---
nslookup fuelapp.mteinc.net
echo.
echo --- Office DNS 10.10.20.3 ---
nslookup fuelapp.mteinc.net 10.10.20.3
echo.
echo If "Default DNS" fails but 10.10.20.3 works:
echo   Set this PC's DNS to 10.10.20.3 (Network adapter - IPv4 DNS).
echo.
echo If both fail, add on internal DNS (10.10.20.3):
echo   fuelapp.mteinc.net  A  10.10.20.40
echo.
echo Quick test (Admin Notepad): add to C:\Windows\System32\drivers\etc\hosts
echo   10.10.20.40  fuelapp.mteinc.net
echo.
endlocal
