$ErrorActionPreference = "Stop"

Write-Host "Masum AI Agent v4.1 - Local Whisper setup" -ForegroundColor Cyan

try {
    py -3.12 --version
} catch {
    Write-Host ""
    Write-Host "Python 3.12 was not found." -ForegroundColor Yellow
    Write-Host "Install it first, then run this script again:"
    Write-Host "winget install -e --id Python.Python.3.12"
    exit 1
}

if (-not (Test-Path ".venv-stt")) {
    Write-Host "Creating .venv-stt with Python 3.12..."
    py -3.12 -m venv .venv-stt
}

$python = ".\.venv-stt\Scripts\python.exe"

Write-Host "Updating pip..."
& $python -m pip install --upgrade pip

Write-Host "Installing local STT dependencies..."
& $python -m pip install -r requirements-stt.txt

Write-Host ""
Write-Host "Local Whisper environment is ready." -ForegroundColor Green
Write-Host "Start it with:"
Write-Host ".\.venv-stt\Scripts\python.exe local_stt_server.py"
