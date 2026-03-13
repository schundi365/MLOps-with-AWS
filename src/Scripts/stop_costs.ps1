# Quick PowerShell script to stop all costly AWS resources
# Usage: .\stop_costs.ps1 [-DryRun]

param(
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$Region = if ($env:AWS_REGION) { $env:AWS_REGION } else { "us-east-1" }
$DryRunArg = if ($DryRun) { "--dry-run" } else { "" }

if ($DryRun) {
    Write-Host "Running in DRY-RUN mode..." -ForegroundColor Yellow
}

# Check if Python script exists
if (-not (Test-Path "stop_all_costly_resources.py")) {
    Write-Host "Error: stop_all_costly_resources.py not found" -ForegroundColor Red
    exit 1
}

# Run the Python script
Write-Host "Stopping costly AWS resources in region: $Region" -ForegroundColor Cyan

if ($DryRunArg) {
    python stop_all_costly_resources.py --region $Region --dry-run
} else {
    python stop_all_costly_resources.py --region $Region
}

Write-Host ""
Write-Host "Done!" -ForegroundColor Green
