# Install cloudflared as a Windows service for Fuel App remote access.
# Run as Administrator from project root:
#   powershell -ExecutionPolicy Bypass -File deploy\install_cloudflared_service.ps1
#
# Prerequisites: cloudflared installed; %USERPROFILE%\.cloudflared\config.yml
# configured per REMOTE_ACCESS.TXT (ingress → IIS, hostname fuelapp.mteinc.net).
#
# Does not replace the FuelApp API service — run both.

$ErrorActionPreference = "Stop"

function Find-Cloudflared {
    $paths = @(
        "C:\Program Files\cloudflared\cloudflared.exe",
        "C:\Program Files (x86)\cloudflared\cloudflared.exe"
    )
    foreach ($p in $paths) {
        if (Test-Path $p) { return $p }
    }
    $cmd = Get-Command "cloudflared.exe" -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

$cloudflared = Find-Cloudflared
if (-not $cloudflared) {
    throw "cloudflared.exe not found. Install from REMOTE_ACCESS.TXT first."
}

$configPath = Join-Path $env:USERPROFILE ".cloudflared\config.yml"
if (-not (Test-Path $configPath)) {
    $example = Join-Path $PSScriptRoot "cloudflared.config.example.yml"
    throw @"
Missing tunnel config: $configPath

Copy $example to $configPath, set tunnel ID and credentials-file, then re-run.
"@
}

Write-Host "Using cloudflared: $cloudflared" -ForegroundColor Cyan
Write-Host "Using config:      $configPath" -ForegroundColor Cyan

# Prefer native cloudflared Windows service (uses config next to credentials).
# Install from the profile that owns .cloudflared credentials.
$existing = Get-Service -Name "cloudflared" -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Service 'cloudflared' already exists (Status=$($existing.Status))." -ForegroundColor Yellow
    Write-Host "To reinstall: cloudflared service uninstall  (as Admin), then re-run this script."
    if ($existing.Status -ne "Running") {
        Start-Service cloudflared
        Write-Host "Started cloudflared service." -ForegroundColor Green
    }
    exit 0
}

Write-Host "Installing cloudflared Windows service..." -ForegroundColor Cyan
& $cloudflared service install
if ($LASTEXITCODE -ne 0) {
    throw "cloudflared service install failed (exit $LASTEXITCODE). Run as Administrator."
}

# Ensure service uses our config: copy config into the system profile location
# that cloudflared service typically reads, if different from current user.
$systemCfDir = "C:\Windows\System32\config\systemprofile\.cloudflared"
$userCfDir = Join-Path $env:USERPROFILE ".cloudflared"
if (-not (Test-Path $systemCfDir)) {
    New-Item -ItemType Directory -Path $systemCfDir -Force | Out-Null
}
Copy-Item (Join-Path $userCfDir "config.yml") (Join-Path $systemCfDir "config.yml") -Force
Get-ChildItem $userCfDir -Filter "*.json" | ForEach-Object {
    Copy-Item $_.FullName (Join-Path $systemCfDir $_.Name) -Force
}

# Fix credentials-file path inside system config if it still points at user profile.
$sysConfig = Join-Path $systemCfDir "config.yml"
$raw = Get-Content $sysConfig -Raw
$credNameMatch = [regex]::Match($raw, 'credentials-file:\s*.*?([^\\/]+\.json)')
if ($credNameMatch.Success) {
    $credFile = $credNameMatch.Groups[1].Value
    $sysCred = Join-Path $systemCfDir $credFile
    $raw2 = $raw -replace 'credentials-file:\s*.+', "credentials-file: $sysCred"
    Set-Content -Path $sysConfig -Value $raw2 -Encoding UTF8
}

Start-Service cloudflared
Write-Host "cloudflared service installed and started." -ForegroundColor Green
Write-Host "Verify from mobile data: https://fuelapp.mteinc.net/api/health"
Write-Host "Office LAN should still use internal DNS A -> 10.10.20.40 (see REMOTE_ACCESS.TXT)."
