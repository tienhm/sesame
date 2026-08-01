# Prepare an unpacked Firefox dev build at dist\ext\firefox-dev\
# Load that folder in about:debugging (any file inside will do).
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv\Scripts\Activate.ps1")) {
    Write-Error "Venv not found. Run: python -m venv .venv && .venv\Scripts\pip install -r requirements.txt"
    exit 1
}
. .\.venv\Scripts\Activate.ps1
python gen_extension_icons.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Icon generation failed (exit $LASTEXITCODE)." -ForegroundColor Red
    exit $LASTEXITCODE
}

$ffDev = "dist\ext\firefox-dev"
Remove-Item -Recurse -Force $ffDev -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $ffDev | Out-Null

Copy-Item "extension\*" $ffDev -Recurse
Copy-Item "$ffDev\manifest-ff.json" "$ffDev\manifest.json" -Force
Remove-Item "$ffDev\manifest-ff.json"

Write-Host "Ready: $PSScriptRoot\$ffDev" -ForegroundColor Green
Write-Host "Load in Firefox: about:debugging -> This Firefox -> Load Temporary Add-on -> pick any file in that folder" -ForegroundColor Cyan
