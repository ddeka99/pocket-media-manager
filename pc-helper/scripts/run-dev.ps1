param(
    [string]$Host = "0.0.0.0",
    [int]$Port = 8765
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$venvPython = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Virtual environment not found. Run .\scripts\bootstrap.ps1 first." -ForegroundColor Red
    exit 1
}

& $venvPython -m uvicorn app.main:app --reload --host $Host --port $Port
