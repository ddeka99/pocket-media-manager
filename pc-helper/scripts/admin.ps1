param(
    [switch]$Rescan
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$baseUrl = "http://127.0.0.1:8765"

function Get-HelperToken {
    return (Invoke-RestMethod "$baseUrl/pairing").api_token
}

function Get-AuthHeaders {
    param([string]$Token)
    return @{ Authorization = "Bearer $Token" }
}

$token = Get-HelperToken
$headers = Get-AuthHeaders -Token $token

if ($Rescan) {
    Write-Host "Rescanning library..." -ForegroundColor Cyan
    Invoke-RestMethod -Method Post -Uri "$baseUrl/library/rescan" -Headers $headers | Out-Null
}

$config = Invoke-RestMethod -Uri "$baseUrl/config" -Headers $headers
$summary = Invoke-RestMethod -Uri "$baseUrl/library/summary" -Headers $headers

Write-Host ""
Write-Host "Pocket Media Manager Helper" -ForegroundColor Green
Write-Host "Base URL: $baseUrl"
Write-Host "Media root: $($config.media_root)"
Write-Host "Items indexed: $($summary.total_items)"
Write-Host "Direct-play items: $($summary.direct_play_items)"
Write-Host "Incompatible items: $($summary.incompatible_items)"

if ($summary.latest_scan) {
    Write-Host "Last scan: $($summary.latest_scan.completed_at)"
}

if ($summary.top_folders.Count -gt 0) {
    Write-Host ""
    Write-Host "Top folders:" -ForegroundColor Yellow
    foreach ($folder in $summary.top_folders) {
        Write-Host " - $($folder.folder): $($folder.item_count)"
    }
}
