$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    python -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt -r requirements-dev.txt
& ".\.venv\Scripts\python.exe" scripts\check_windows_runtime.py --skip-browser
& ".\.venv\Scripts\pyinstaller.exe" --clean --noconfirm packaging\digikey_price_scraper.spec

Write-Host "Built dist\DigiKeyPriceScraper\DigiKeyPriceScraper.exe"
