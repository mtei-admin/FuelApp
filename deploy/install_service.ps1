# Install Fuel App as a Windows Service using NSSM (https://nssm.cc/)
# Run as Administrator from project root:
#   powershell -ExecutionPolicy Bypass -File deploy\install_service.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ServiceName = "FuelApp"
$Nssm = "nssm.exe"

function Find-Nssm {
    $paths = @(
        "C:\nssm\nssm.exe",
        "C:\Program Files\nssm\nssm.exe",
        "C:\Program Files (x86)\nssm\nssm.exe"
    )
    foreach ($p in $paths) {
        if (Test-Path $p) { return $p }
    }
    $cmd = Get-Command $Nssm -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

$nssmPath = Find-Nssm
if (-not $nssmPath) {
    Write-Host "NSSM not found." -ForegroundColor Red
    Write-Host "Download from https://nssm.cc/download and place nssm.exe in C:\nssm\"
    Write-Host "Then re-run this script."
    exit 1
}

$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    throw "Run deploy\install_windows.ps1 first."
}

$DistIndex = Join-Path $ProjectRoot "frontend\dist\index.html"
if (-not (Test-Path $DistIndex)) {
    Write-Host "WARNING: frontend\dist not found. Run deploy\build_frontend.bat before using IIS." -ForegroundColor Yellow
}

$AppParams = "-m uvicorn api.main:app --host 127.0.0.1 --port 8000"

$existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Service '$ServiceName' already exists. Stopping and removing..." -ForegroundColor Yellow
    & $nssmPath stop $ServiceName confirm
    & $nssmPath remove $ServiceName confirm
}

Write-Host "Installing service '$ServiceName'..." -ForegroundColor Cyan
& $nssmPath install $ServiceName $PythonExe $AppParams
& $nssmPath set $ServiceName AppDirectory $ProjectRoot
& $nssmPath set $ServiceName AppEnvironmentExtra "SERVE_FRONTEND=false"
& $nssmPath set $ServiceName DisplayName "Fuel Requisition System"
& $nssmPath set $ServiceName Description "Fuel Requisition System API (FastAPI, production)"
& $nssmPath set $ServiceName Start SERVICE_AUTO_START
& $nssmPath set $ServiceName AppStdout (Join-Path $ProjectRoot "logs\service_stdout.log")
& $nssmPath set $ServiceName AppStderr (Join-Path $ProjectRoot "logs\service_stderr.log")

$logsDir = Join-Path $ProjectRoot "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}

& $nssmPath start $ServiceName
Write-Host "Service '$ServiceName' started. API listens on http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "IIS serves frontend\dist and proxies /api/* to that address."
