# Build Sesame native messaging host
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv\Scripts\Activate.ps1")) {
    Write-Error "Venv not found. Run: python -m venv .venv && .venv\Scripts\pip install -r requirements.txt"
    exit 1
}

. .\.venv\Scripts\Activate.ps1

Write-Host "Building szm_door..." -ForegroundColor Cyan
pyinstaller native_host.spec --noconfirm

if ($LASTEXITCODE -eq 0) {
    Write-Host "Done: $PSScriptRoot\dist\szm_door.exe" -ForegroundColor Green
} else {
    Write-Host "Build failed (exit $LASTEXITCODE)." -ForegroundColor Red
    exit $LASTEXITCODE
}
