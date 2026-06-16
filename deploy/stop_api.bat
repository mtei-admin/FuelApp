@echo off
rem Stop all Fuel App API processes listening on port 8000
setlocal

echo Stopping processes on port 8000...

powershell -NoProfile -Command ^
  "$conns = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue; " ^
  "if (-not $conns) { Write-Host 'No process found on port 8000.'; exit 0 }; " ^
  "$procIds = $conns.OwningProcess | Sort-Object -Unique; " ^
  "foreach ($procId in $procIds) { " ^
  "  $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue; " ^
  "  if ($proc) { Write-Host ('Stopping PID ' + $procId + ' (' + $proc.ProcessName + ')'); Stop-Process -Id $procId -Force } " ^
  "}; " ^
  "Write-Host 'Done.'"

endlocal
