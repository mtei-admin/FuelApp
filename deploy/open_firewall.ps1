# Open Windows Firewall for LAN mode (port 8000). Run as Administrator.

$ErrorActionPreference = "Stop"
$RuleName = "Fuel App API 8000"

$existing = Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Firewall rule '$RuleName' already exists."
    exit 0
}

New-NetFirewallRule `
    -DisplayName $RuleName `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 8000 `
    -Action Allow `
    -Profile Domain, Private | Out-Null

Write-Host "Firewall rule created: inbound TCP 8000 allowed (Domain, Private profiles)."
