# IIS + HTTPS setup for Fuel Requisition System
# Run as Administrator from project root:
#   powershell -ExecutionPolicy Bypass -File deploy\setup_iis.ps1 -HostName "fuel.mteinc.local" -CreateSelfSignedCert

param(
    [Parameter(Mandatory = $true)]
    [string]$HostName,

    [string]$SiteName = "FuelApp",
    [int]$HttpsPort = 443,
    [switch]$CreateSelfSignedCert
)

$ErrorActionPreference = "Stop"

# Require Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
if (-not $isAdmin) {
    Write-Host "ERROR: Run this script as Administrator." -ForegroundColor Red
    exit 1
}

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$WebConfigPath = Join-Path $ProjectRoot "web.config"

Write-Host "=== Fuel App IIS Setup ===" -ForegroundColor Cyan
Write-Host "Project root: $ProjectRoot"
Write-Host "Hostname:     $HostName"

# Install IIS features
$webServer = Get-WindowsFeature -Name Web-Server
if ($webServer.InstallState -ne "Installed") {
    Write-Host "Installing IIS..." -ForegroundColor Yellow
    Install-WindowsFeature -Name Web-Server -IncludeManagementTools | Out-Null
} else {
    Write-Host "IIS already installed."
}

$webSockets = Get-WindowsFeature -Name Web-WebSockets -ErrorAction SilentlyContinue
if ($webSockets -and $webSockets.InstallState -ne "Installed") {
    Write-Host "Installing WebSockets..." -ForegroundColor Yellow
    Install-WindowsFeature -Name Web-WebSockets | Out-Null
}

if (-not (Test-Path $WebConfigPath)) {
    throw "web.config not found at $WebConfigPath"
}

Import-Module WebAdministration

# Application pool
$poolName = $SiteName
if (-not (Test-Path "IIS:\AppPools\$poolName")) {
    Write-Host "Creating application pool '$poolName'..." -ForegroundColor Yellow
    New-WebAppPool -Name $poolName | Out-Null
    Set-ItemProperty "IIS:\AppPools\$poolName" -Name managedRuntimeVersion -Value ""
}

# SSL certificate
$certThumbprint = $null
if ($CreateSelfSignedCert) {
    Write-Host "Creating self-signed certificate for $HostName ..." -ForegroundColor Yellow
    $cert = New-SelfSignedCertificate `
        -DnsName $HostName `
        -CertStoreLocation "cert:\LocalMachine\My" `
        -KeyExportPolicy Exportable `
        -NotAfter (Get-Date).AddYears(5)
    $certThumbprint = $cert.Thumbprint
    Write-Host "Certificate thumbprint: $certThumbprint"
    Write-Host "NOTE: Clients will see a certificate warning unless you trust this cert." -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "No certificate created. Bind HTTPS manually in IIS Manager with your SSL cert."
    Write-Host "Or re-run with -CreateSelfSignedCert for testing."
}

# IIS site
if (Test-Path "IIS:\Sites\$SiteName") {
    Write-Host "Removing existing site '$SiteName'..." -ForegroundColor Yellow
    Remove-Website -Name $SiteName
}

Write-Host "Creating website '$SiteName'..." -ForegroundColor Yellow
New-Website -Name $SiteName `
    -PhysicalPath $ProjectRoot `
    -ApplicationPool $poolName `
    -Port 80 `
    -HostHeader $HostName | Out-Null

if ($certThumbprint) {
    New-WebBinding -Name $SiteName -Protocol "https" -Port $HttpsPort -HostHeader $HostName -SslFlags 1
    $binding = Get-WebBinding -Name $SiteName -Protocol "https" -HostHeader $HostName
    $binding.AddSslCertificate($certThumbprint, "my")
    Write-Host "HTTPS binding created on port $HttpsPort"
}

# Allow reverse-proxy server variables (best-effort)
try {
    Add-WebConfigurationProperty -PSPath "MACHINE/WEBROOT/APPHOST" `
        -Filter "system.webServer/rewrite/allowedServerVariables" `
        -Name "." -Value @{name = "HTTP_X_FORWARDED_PROTO"} -ErrorAction SilentlyContinue
    Add-WebConfigurationProperty -PSPath "MACHINE/WEBROOT/APPHOST" `
        -Filter "system.webServer/rewrite/allowedServerVariables" `
        -Name "." -Value @{name = "HTTP_X_FORWARDED_HOST"} -ErrorAction SilentlyContinue
    Add-WebConfigurationProperty -PSPath "MACHINE/WEBROOT/APPHOST" `
        -Filter "system.webServer/rewrite/allowedServerVariables" `
        -Name "." -Value @{name = "HTTP_X_FORWARDED_FOR"} -ErrorAction SilentlyContinue
    Write-Host "Server variables registered for reverse proxy."
} catch {
    Write-Host "Could not auto-register server variables. Add them manually in IIS URL Rewrite." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== IIS site created ===" -ForegroundColor Green
Write-Host ""
Write-Host "REMAINING MANUAL STEPS:"
Write-Host "  1. Install URL Rewrite: https://www.iis.net/downloads/microsoft/url-rewrite"
Write-Host "  2. Install ARR:         https://www.iis.net/downloads/microsoft/application-request-routing"
Write-Host "  3. IIS Manager -> Server -> Application Request Routing Cache -> Enable proxy"
Write-Host "  4. Build frontend:    deploy\build_frontend.bat"
Write-Host "  5. Start API:         deploy\run_production.bat  (or install_service.ps1)"
Write-Host "  6. Edit .env:           APP_BASE_URL=https://$HostName"
Write-Host "  7. Test:                https://$HostName"
Write-Host ""
Write-Host "Full guide: deploy\IIS_SETUP.txt"
