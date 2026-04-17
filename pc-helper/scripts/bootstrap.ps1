Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Action,
        [Parameter(Mandatory = $true)]
        [string]$Description
    )

    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "Failed during: $Description"
    }
}

function Find-RealPython {
    $candidates = New-Object System.Collections.Generic.List[string]

    foreach ($name in @("python.exe", "py.exe")) {
        try {
            $command = Get-Command $name -ErrorAction Stop
            if ($command.Source -and $command.Source -notlike "*WindowsApps*") {
                $candidates.Add($command.Source)
            }
        } catch {
        }
    }

    $patterns = @(
        "$env:LOCALAPPDATA\Programs\Python\Python*\python.exe",
        "$env:LOCALAPPDATA\Python\bin\python*.exe",
        "$env:ProgramFiles\Python*\python.exe",
        "$env:ProgramFiles\Python*\*\python.exe"
    )

    foreach ($pattern in $patterns) {
        foreach ($match in Get-ChildItem $pattern -ErrorAction SilentlyContinue) {
            if ($match.Name -notlike "pythonw*") {
                $candidates.Add($match.FullName)
            }
        }
    }

    return $candidates | Select-Object -Unique | Select-Object -First 1
}

$python = Find-RealPython
if (-not $python) {
    Write-Host "Could not find a real Python interpreter." -ForegroundColor Red
    Write-Host "This shell is likely still resolving python/py to Windows Store aliases." -ForegroundColor Yellow
    Write-Host "Disable App Execution Aliases for python.exe/py.exe or restart your terminal after install." -ForegroundColor Yellow
    exit 1
}

Write-Host "Using Python at $python" -ForegroundColor Cyan

$venvPath = Join-Path $PSScriptRoot "..\.venv"
Invoke-Step -Description "creating virtual environment" -Action {
    & $python -m venv $venvPath
}

$venvPython = Join-Path $venvPath "Scripts\python.exe"
Invoke-Step -Description "upgrading pip" -Action {
    & $venvPython -m pip install --upgrade pip
}

$requirementsPath = Join-Path $PSScriptRoot "..\requirements.txt"
Invoke-Step -Description "installing dependencies" -Action {
    & $venvPython -m pip install -r $requirementsPath
}

Write-Host ""
Write-Host "Bootstrap complete." -ForegroundColor Green
Write-Host "Run .\scripts\run-dev.ps1 from pc-helper to start the API."
