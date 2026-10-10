$ErrorActionPreference = "Stop"

Write-Host "Masum AI Agent v4.1 - Local Whisper setup" -ForegroundColor Cyan
Write-Host ""

Write-Host "Checking Python 3.12..."
& py -3.12 --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Python 3.12 was not found on this PC." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Install it with:" -ForegroundColor Cyan
    Write-Host "winget install -e --id Python.Python.3.12"
    Write-Host ""
    Write-Host "After installation, close and reopen the VS Code terminal."
    Write-Host "Then verify:"
    Write-Host "py -0p"
    Write-Host ""
    Write-Host "Finally run this setup again:"
    Write-Host ".\setup_local_stt.ps1"
    exit 1
}

Write-Host "Python 3.12 detected." -ForegroundColor Green

if (-not (Test-Path ".venv-stt")) {
    Write-Host "Creating .venv-stt with Python 3.12..."
    & py -3.12 -m venv .venv-stt

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to create .venv-stt." -ForegroundColor Red
        exit 1
    }
}

$python = ".\.venv-stt\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Host "The STT virtual environment is incomplete." -ForegroundColor Red
    Write-Host "Delete .venv-stt and run this setup again:"
    Write-Host "Remove-Item -Recurse -Force .venv-stt"
    Write-Host ".\setup_local_stt.ps1"
    exit 1
}

Write-Host "Updating pip..."
& $python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    Write-Host "pip upgrade failed." -ForegroundColor Red
    exit 1
}

Write-Host "Installing local STT dependencies..."
& $python -m pip install -r requirements-stt.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "STT dependency installation failed." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Local Whisper environment is ready." -ForegroundColor Green
Write-Host "Start it with:"
Write-Host ".\.venv-stt\Scripts\python.exe local_stt_server.py"
