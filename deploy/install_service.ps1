# Install Fuel App production API as a Windows Service (NSSM + run_production.bat)
# Run as Administrator from project root:
#   powershell -ExecutionPolicy Bypass -File deploy\install_service.ps1
#
# NSSM: place nssm.exe in C:\nssm\ or let this script download nssm-2.24 from https://nssm.cc/

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ServiceName = "FuelApp"
$NssmDir = "C:\nssm"
$NssmExe = Join-Path $NssmDir "nssm.exe"
$BatchFile = Join-Path $ProjectRoot "deploy\run_production.bat"

function Find-Nssm {
    if (Test-Path $NssmExe) { return $NssmExe }

    $paths = @(
        "C:\Program Files\nssm\nssm.exe",
        "C:\Program Files (x86)\nssm\nssm.exe"
    )
    foreach ($p in $paths) {
        if (Test-Path $p) { return $p }
    }

    $cmd = Get-Command "nssm.exe" -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    return $null
}

function Install-Nssm {
    Write-Host "NSSM not found. Downloading nssm-2.24 from nssm.cc ..." -ForegroundColor Yellow
    $zipPath = Join-Path $env:TEMP "nssm-2.24.zip"
    $extractRoot = Join-Path $env:TEMP "nssm-2.24-extract"

    Invoke-WebRequest -Uri "https://nssm.cc/release/nssm-2.24.zip" -OutFile $zipPath -UseBasicParsing
    if (Test-Path $extractRoot) {
        Remove-Item $extractRoot -Recurse -Force
    }
    Expand-Archive -Path $zipPath -DestinationPath $extractRoot -Force

    $arch = if ([Environment]::Is64BitOperatingSystem) { "win64" } else { "win32" }
    $downloaded = Get-ChildItem -Path $extractRoot -Recurse -Filter "nssm.exe" |
        Where-Object { $_.DirectoryName -like "*\$arch*" } |
        Select-Object -First 1

    if (-not $downloaded) {
        throw "Downloaded NSSM archive did not contain nssm.exe for $arch."
    }

    if (-not (Test-Path $NssmDir)) {
        New-Item -ItemType Directory -Path $NssmDir | Out-Null
    }
    Copy-Item $downloaded.FullName $NssmExe -Force
    Write-Host "Installed NSSM to $NssmExe" -ForegroundColor Green
    return $NssmExe
}

$nssmPath = Find-Nssm
if (-not $nssmPath) {
    $nssmPath = Install-Nssm
}

if (-not (Test-Path (Join-Path $ProjectRoot ".venv\Scripts\python.exe"))) {
    throw "Run deploy\install_windows.ps1 first."
}

if (-not (Test-Path $BatchFile)) {
    throw "Missing $BatchFile"
}

$DistIndex = Join-Path $ProjectRoot "frontend\dist\index.html"
if (-not (Test-Path $DistIndex)) {
    Write-Host "WARNING: frontend\dist not found. Run deploy\build_frontend.bat before using IIS." -ForegroundColor Yellow
}

$logsDir = Join-Path $ProjectRoot "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}

Write-Host "Stopping any manual API process on port 8000..." -ForegroundColor Yellow
& cmd.exe /c (Join-Path $ProjectRoot "deploy\stop_api.bat")

$existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Service '$ServiceName' already exists. Stopping and removing..." -ForegroundColor Yellow
    & $nssmPath stop $ServiceName confirm 2>$null
    & $nssmPath remove $ServiceName confirm
}

Write-Host "Installing service '$ServiceName' -> deploy\run_production.bat ..." -ForegroundColor Cyan
& $nssmPath install $ServiceName $BatchFile
& $nssmPath set $ServiceName AppDirectory $ProjectRoot
& $nssmPath set $ServiceName DisplayName "Fuel Requisition System"
& $nssmPath set $ServiceName Description "Fuel Requisition System API (deploy\run_production.bat, IIS backend)"
& $nssmPath set $ServiceName Start SERVICE_AUTO_START
& $nssmPath set $ServiceName AppStdout (Join-Path $ProjectRoot "logs\service_stdout.log")
& $nssmPath set $ServiceName AppStderr (Join-Path $ProjectRoot "logs\service_stderr.log")
& $nssmPath set $ServiceName AppRotateFiles 1
& $nssmPath set $ServiceName AppRotateBytes 1048576
& $nssmPath set $ServiceName AppKillProcessTree 1

& $nssmPath start $ServiceName
Start-Sleep -Seconds 5

$healthOk = $false
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/health" -UseBasicParsing -TimeoutSec 15
    if ($response.StatusCode -eq 200) {
        $healthOk = $true
        Write-Host "Health check: $($response.Content)" -ForegroundColor Green
    }
} catch {
    Write-Host "Health check failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "See logs\service_stderr.log for details." -ForegroundColor Yellow
}

if ($healthOk) {
    Write-Host "Service '$ServiceName' installed and running. Auto-starts on boot." -ForegroundColor Green
    Write-Host "Manage: C:\nssm\nssm.exe restart $ServiceName  |  services.msc"
} else {
    exit 1
}
