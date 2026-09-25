$ErrorActionPreference = "Stop"

Write-Host "GreenPulse pre-operational installer"

if (!(Test-Path ".\.venv")) {
    Write-Host "Creating local virtual environment..."
    python -m venv .venv
}

$python = ".\.venv\Scripts\python.exe"

if (!(Test-Path $python)) {
    throw "Virtual environment Python not found."
}

if (Test-Path ".\requirements.txt") {
    & $python -m pip install -r requirements.txt

    if ($LASTEXITCODE -ne 0) {
        throw "Dependency installation failed."
    }

    Write-Host "Dependencies installed from requirements.txt."
}
else {
    Write-Warning "Final dependency lock file requirements.txt is not frozen yet."
    Write-Warning "Installation cannot be claimed reproducible until final release."
}

Write-Host "Install script completed in PRE-OPERATIONAL mode."
