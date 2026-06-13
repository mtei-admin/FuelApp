# Backup SQLite database. Schedule via Task Scheduler (daily recommended).
#   powershell -ExecutionPolicy Bypass -File deploy\backup_database.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DbPath = Join-Path $ProjectRoot "data\fuel_system.db"
$BackupDir = Join-Path $ProjectRoot "data\backups"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupPath = Join-Path $BackupDir "fuel_system_$Timestamp.db"

if (-not (Test-Path $DbPath)) {
    Write-Host "Database not found: $DbPath"
    exit 1
}

if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
}

Copy-Item $DbPath $BackupPath
Write-Host "Backup saved: $BackupPath"

# Keep last 30 backups
Get-ChildItem $BackupDir -Filter "fuel_system_*.db" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -Skip 30 |
    Remove-Item -Force
