$ErrorActionPreference = "Stop"

$python = ".\.venv\Scripts\python.exe"

if (!(Test-Path $python)) {
    throw "GreenPulse virtual environment not found. Run release/install.ps1 first."
}

if (!(Test-Path ".\src\api.py")) {
    throw "src/api.py not found."
}

& $python -c "import fastapi, uvicorn"

if ($LASTEXITCODE -ne 0) {
    throw "FastAPI/Uvicorn runtime dependencies are unavailable."
}

Write-Host "Starting GreenPulse API..."
& $python -m uvicorn src.api:app --host 0.0.0.0 --port 8000
