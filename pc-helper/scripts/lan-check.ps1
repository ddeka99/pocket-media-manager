param(
    [int]$Port = 8765
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-PrimaryIPv4Address {
    $config = Get-NetIPConfiguration |
        Where-Object {
            $_.NetAdapter.Status -eq "Up" -and
            $_.IPv4Address -ne $null -and
            $_.IPv4DefaultGateway -ne $null
        } |
        Select-Object -First 1

    if (-not $config) {
        throw "Could not determine an active IPv4 address."
    }

    return $config.IPv4Address.IPAddress
}

$ipAddress = Get-PrimaryIPv4Address
$baseUrl = "http://$ipAddress`:$Port"

$health = Invoke-RestMethod "$baseUrl/health"
$pairing = Invoke-RestMethod "$baseUrl/pairing"

Write-Host ""
Write-Host "Pocket Media Manager LAN Check" -ForegroundColor Green
Write-Host "Wi-Fi URL: $baseUrl"
Write-Host "Token: $($pairing.api_token)"
Write-Host "Media root configured: $($health.media_root_configured)"
Write-Host "Indexed items: $($health.library_count)"
Write-Host ""
Write-Host "Next MacBook/iPhone input:" -ForegroundColor Yellow
Write-Host " - Helper URL: $baseUrl"
Write-Host " - Pairing token: $($pairing.api_token)"
Write-Host ""
Write-Host "If the iPhone cannot reach this URL on home Wi-Fi, allow Python/Uvicorn through Windows Firewall." -ForegroundColor DarkYellow
