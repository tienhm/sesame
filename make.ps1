# Build Sesame — activate venv then run PyInstaller
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv\Scripts\Activate.ps1")) {
    Write-Error "Venv not found. Run: python -m venv .venv && .venv\Scripts\pip install -r requirements.txt"
    exit 1
}

. .\.venv\Scripts\Activate.ps1

$running = Get-Process -Name "Sesame-v*" -ErrorAction SilentlyContinue
if ($running) {
    Write-Host "Killing running Sesame process(es)..." -ForegroundColor Yellow
    $running | Stop-Process -Force
}

Write-Host "Building szm_door..." -ForegroundColor Cyan
pyinstaller native_host.spec --noconfirm
if ($LASTEXITCODE -ne 0) {
    Write-Host "szm_door build failed (exit $LASTEXITCODE)." -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host "Done: dist\szm_door.exe" -ForegroundColor Green

Write-Host "Building Sesame..." -ForegroundColor Cyan
pyinstaller sesame.spec --noconfirm

if ($LASTEXITCODE -eq 0) {
    $exe = Get-ChildItem dist\Sesame-v*.exe | Sort-Object LastWriteTime | Select-Object -Last 1
    Remove-Item -Path "dist\szm_door.exe" -Force -ErrorAction SilentlyContinue
    Write-Host "Done: $($exe.FullName)" -ForegroundColor Green
} else {
    Write-Host "Build failed (exit $LASTEXITCODE). Check build.log for details." -ForegroundColor Red
    exit $LASTEXITCODE
}
