# Install IIS URL Rewrite 2.1 and Application Request Routing 3.0 (x64).
# Run as Administrator:
#   powershell -ExecutionPolicy Bypass -File deploy\install_iis_rewrite_arr.ps1

$ErrorActionPreference = "Stop"

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
if (-not $isAdmin) {
    Write-Host "ERROR: Run PowerShell as Administrator." -ForegroundColor Red
    exit 1
}

$downloads = Join-Path $env:TEMP "fuelapp-iis-modules"
New-Item -ItemType Directory -Force -Path $downloads | Out-Null

$packages = @(
    @{
        Name = "URL Rewrite 2.1"
        Url  = "https://download.microsoft.com/download/1/2/8/128E2E22-C1B9-44A4-BE2A-5859ED1D4592/rewrite_amd64_en-US.msi"
        File = "rewrite_amd64_en-US.msi"
        Test = { Test-Path "C:\Program Files\IIS\Microsoft URL Rewrite Module\rewrite.dll" }
    },
    @{
        Name = "Application Request Routing 3.0"
        Url  = "https://download.microsoft.com/download/E/9/8/E9849D6A-020E-47E4-9FD0-A023E99B54EB/requestRouter_amd64.msi"
        File = "requestRouter_amd64.msi"
        Test = { Get-WebGlobalModule -ErrorAction SilentlyContinue | Where-Object { $_.Name -eq "ApplicationRequestRouting" } }
    }
)

function Install-MsiPackage {
    param(
        [string]$Label,
        [string]$MsiPath
    )
    Write-Host "Installing $Label ..." -ForegroundColor Yellow
    $args = "/i `"$MsiPath`" /quiet /norestart"
    $proc = Start-Process -FilePath "msiexec.exe" -ArgumentList $args -Wait -PassThru -NoNewWindow
    if ($proc.ExitCode -notin 0, 3010) {
        throw "msiexec exit code $($proc.ExitCode) for $Label"
    }
    Write-Host "$Label installed." -ForegroundColor Green
}

Write-Host "=== Install URL Rewrite + ARR ===" -ForegroundColor Cyan

foreach ($pkg in $packages) {
    if (& $pkg.Test) {
        Write-Host "$($pkg.Name) already installed - skipping." -ForegroundColor Gray
        continue
    }
    $dest = Join-Path $downloads $pkg.File
    if (-not (Test-Path $dest)) {
        Write-Host "Downloading $($pkg.Name) ..." -ForegroundColor Yellow
        Invoke-WebRequest -Uri $pkg.Url -OutFile $dest -UseBasicParsing
    }
    Install-MsiPackage -Label $pkg.Name -MsiPath $dest
}

Write-Host "Enabling ARR reverse proxy ..." -ForegroundColor Yellow
Import-Module WebAdministration -ErrorAction Stop
Set-WebConfigurationProperty -PSPath "MACHINE/WEBROOT/APPHOST" -Filter "system.webServer/proxy" -Name "enabled" -Value "True"

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
    Write-Host "Proxy server variables registered." -ForegroundColor Green
} catch {
    Write-Host "Could not auto-register server variables (add manually in IIS if needed)." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Green
Write-Host "Next: powershell -ExecutionPolicy Bypass -File deploy\setup_iis.ps1 -HostName fuelapp-api.mteinc.net -CreateSelfSignedCert"
