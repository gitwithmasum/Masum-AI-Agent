$ErrorActionPreference = "Stop"

Write-Host "Masum AI Agent v5.3 - Windows + Mobile Bridge Builder" -ForegroundColor Cyan

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    Write-Host "Python launcher 'py' was not found." -ForegroundColor Red
    exit 1
}

& py -3.12 --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "Python 3.12 is required to build the Windows app." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".venv-desktop")) {
    & py -3.12 -m venv .venv-desktop
}

$python = ".\.venv-desktop\Scripts\python.exe"
& $python -m pip install --upgrade pip
& $python -m pip install -r requirements-desktop.txt

New-Item -ItemType Directory -Force -Path build | Out-Null
New-Item -ItemType Directory -Force -Path dist | Out-Null

& $python -c "from PIL import Image; Image.open('dashboard/masum-ai-agent-logo.webp').convert('RGBA').save('build/masum-ai-agent.ico', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])"

& $python -m PyInstaller --noconfirm --clean --onefile --windowed --name MasumAIAgent --icon build\masum-ai-agent.ico --collect-all faster_whisper --collect-all ctranslate2 --collect-all av --collect-all sounddevice --hidden-import pyttsx3.drivers --hidden-import pyttsx3.drivers.sapi5 desktop_companion.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller build failed." -ForegroundColor Red
    exit 1
}

$pf86 = [Environment]::GetFolderPath("ProgramFilesX86")
$iscc = Join-Path $pf86 "Inno Setup 6\ISCC.exe"

if (-not (Test-Path $iscc)) {
    Write-Host ""
    Write-Host "Inno Setup 6 was not found." -ForegroundColor Yellow
    Write-Host "Install it, then rerun this script:"
    Write-Host "winget install -e --id JRSoftware.InnoSetup"
    exit 1
}

& $iscc "installer\MasumAI.iss"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Installer build failed." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Windows installer is ready:" -ForegroundColor Green
Write-Host "installer-output\Masum-AI-Agent-Setup.exe"
