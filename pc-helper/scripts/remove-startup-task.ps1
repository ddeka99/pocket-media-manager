$ErrorActionPreference = "Stop"

$TaskName = "Pocket Media Manager PC Helper"

$CurrentIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$CurrentPrincipal = New-Object System.Security.Principal.WindowsPrincipal($CurrentIdentity)
if (-not $CurrentPrincipal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run PowerShell as Administrator to remove the boot startup task."
}

$Task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

if (-not $Task) {
    Write-Host "Scheduled task was not found: $TaskName"
    return
}

if ($Task.State -eq "Running") {
    Stop-ScheduledTask -TaskName $TaskName
}

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Host "Stopped and removed scheduled task: $TaskName"
