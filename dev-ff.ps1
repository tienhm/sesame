# Prepare an unpacked Firefox dev build at dist\ext\firefox-dev\
# Load that folder in about:debugging (any file inside will do).
Set-Location $PSScriptRoot

$ffDev = "dist\ext\firefox-dev"
Remove-Item -Recurse -Force $ffDev -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $ffDev | Out-Null

Copy-Item "extension\*" $ffDev -Recurse
Copy-Item "$ffDev\manifest-ff.json" "$ffDev\manifest.json" -Force
Remove-Item "$ffDev\manifest-ff.json"

Write-Host "Ready: $PSScriptRoot\$ffDev" -ForegroundColor Green
Write-Host "Load in Firefox: about:debugging -> This Firefox -> Load Temporary Add-on -> pick any file in that folder" -ForegroundColor Cyan
