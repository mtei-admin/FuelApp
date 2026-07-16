# Install IIS (Web Server role) for Fuel App — run as Administrator:
#   powershell -ExecutionPolicy Bypass -File deploy\install_iis.ps1

$ErrorActionPreference = "Stop"

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
if (-not $isAdmin) {
    Write-Host "ERROR: Run PowerShell as Administrator." -ForegroundColor Red
    exit 1
}

Write-Host "=== Installing IIS ===" -ForegroundColor Cyan

$webServer = Get-WindowsFeature -Name Web-Server
if ($webServer.InstallState -ne "Installed") {
    Write-Host "Installing Web-Server + management tools..." -ForegroundColor Yellow
    $result = Install-WindowsFeature -Name Web-Server -IncludeManagementTools
    if ($result.RestartNeeded -eq "Yes") {
        Write-Host "REBOOT REQUIRED before continuing IIS setup." -ForegroundColor Yellow
    }
} else {
    Write-Host "Web-Server already installed."
}

$webSockets = Get-WindowsFeature -Name Web-WebSockets -ErrorAction SilentlyContinue
if ($webSockets -and $webSockets.InstallState -ne "Installed") {
    Write-Host "Installing Web-WebSockets..." -ForegroundColor Yellow
    Install-WindowsFeature -Name Web-WebSockets | Out-Null
}

Get-WindowsFeature Web-Server, Web-WebSockets | Format-Table Name, InstallState -AutoSize

Write-Host ""
Write-Host "Next: install URL Rewrite + ARR, then run:" -ForegroundColor Green
Write-Host "  powershell -ExecutionPolicy Bypass -File deploy\setup_iis.ps1 -HostName fuelapp-api.mteinc.net -CreateSelfSignedCert"
Write-Host "See deploy\IIS_SETUP.txt"
