# Fuel Requisition System — Windows Server install script
# Run from project root: powershell -ExecutionPolicy Bypass -File deploy\install_windows.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "=== Fuel App — Windows install ===" -ForegroundColor Cyan
Write-Host "Project root: $ProjectRoot"

# Prefer Python 3.11/3.12 if available; fall back to default launcher
$PythonCmd = $null
foreach ($candidate in @("py -3.12", "py -3.11", "py")) {
    try {
        $version = Invoke-Expression "$candidate --version 2>&1"
        if ($LASTEXITCODE -eq 0) {
            $PythonCmd = $candidate
            Write-Host "Using: $version"
            break
        }
    } catch {
        continue
    }
}
if (-not $PythonCmd) {
    throw "Python not found. Install Python 3.11+ from https://www.python.org/downloads/"
}

# Virtual environment
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    Invoke-Expression "$PythonCmd -m venv .venv"
} else {
    Write-Host "Virtual environment already exists."
}

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    throw "Virtual environment creation failed: $VenvPython not found"
}

Write-Host "Installing dependencies..." -ForegroundColor Yellow
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r REQUIREMENTS.TXT
& $VenvPython -m pip install -r api\requirements.txt

# Ensure data directory exists
$dataDir = Join-Path $ProjectRoot "data"
if (-not (Test-Path $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir | Out-Null
}

# Initialize database schema
Write-Host "Initializing database..." -ForegroundColor Yellow
& $VenvPython -c "from pathlib import Path; from src.database import init_database; init_database(str(Path('data') / 'fuel_system.db'))"

# .env template
if (-not (Test-Path ".env")) {
    Copy-Item "env.example" ".env"
    Write-Host "Created .env from env.example — edit APP_BASE_URL and SMTP before production use." -ForegroundColor Yellow
} else {
    Write-Host ".env already exists (not overwritten)."
}

Write-Host ""
Write-Host "=== Install complete ===" -ForegroundColor Green
Write-Host "Next steps:"
Write-Host "  1. Edit .env (APP_BASE_URL, SMTP settings)"
Write-Host "  2. Seed admin:  .\.venv\Scripts\python.exe init_admin.py"
Write-Host "  3. Build UI:    deploy\build_frontend.bat  (requires Node.js)"
Write-Host "  4. Test API:    deploy\run_production.bat  (http://127.0.0.1:8000/api/health)"
Write-Host "  5. IIS + HTTPS: see DEPLOYMENT.TXT"
Write-Host "  6. Auto-start:  powershell -ExecutionPolicy Bypass -File deploy\install_service.ps1"
