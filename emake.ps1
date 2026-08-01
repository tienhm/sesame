# Package Sesame Pass extension for Chrome, Edge, and Firefox.
# Output: dist\ext\sesame-pass-chrome-vX.Y.zip
#         dist\ext\sesame-pass-edge-vX.Y.zip
#         dist\ext\sesame-pass-firefox-vX.Y.xpi
Set-Location $PSScriptRoot

# --- Read version from main.py ---
$verLine = Select-String -Path main.py -Pattern '__version__\s*=\s*"([^"]+)"'
$version = $verLine.Matches[0].Groups[1].Value          # e.g. "1.6"
$semver  = "$version.0"                                  # "1.6.0" for manifest

Write-Host "Packaging Sesame Pass extension v$version" -ForegroundColor Cyan

$outDir = "dist\ext"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$src = "extension"
$tmp = "$outDir\_tmp"

function Make-Package($browser, $outFile) {
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Force -Path $tmp | Out-Null

    # Copy all extension files
    Copy-Item "$src\*" $tmp -Recurse

    # Firefox uses its own manifest; Chrome/Edge use the main one.
    if ($browser -eq "firefox") { $baseMf = "$src\manifest-ff.json" }
    else                         { $baseMf = "$tmp\manifest.json" }
    $mf = Get-Content $baseMf -Raw | ConvertFrom-Json
    $mf.version = $semver
    $mf | ConvertTo-Json -Depth 10 | Set-Content "$tmp\manifest.json" -Encoding utf8

    # manifest-ff.json must not ship inside the Firefox package itself
    Remove-Item "$tmp\manifest-ff.json" -ErrorAction SilentlyContinue

    # Zip into output file (.xpi is a renamed .zip — create as .zip then rename)
    $fullOut = "$outDir\$outFile"
    $tmpZip  = "$outDir\_pkg.zip"
    Remove-Item $fullOut -ErrorAction SilentlyContinue
    Remove-Item $tmpZip  -ErrorAction SilentlyContinue
    Compress-Archive -Path "$tmp\*" -DestinationPath $tmpZip
    Rename-Item $tmpZip $outFile
    Write-Host "  $fullOut" -ForegroundColor Green
}

Make-Package "chrome"  "sesame-pass-chrome-v$version.zip"
Make-Package "edge"    "sesame-pass-edge-v$version.zip"
Make-Package "firefox" "sesame-pass-firefox-v$version.xpi"

# Also keep an unpacked Firefox dev build so about:debugging can load it directly
# (Firefox always reads manifest.json from the directory, not the selected file).
$ffDev = "$outDir\firefox-dev"
Remove-Item -Recurse -Force $ffDev -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $ffDev | Out-Null
Copy-Item "$src\*" $ffDev -Recurse
$mf = Get-Content "$src\manifest-ff.json" -Raw | ConvertFrom-Json
$mf.version = $semver
$mf | ConvertTo-Json -Depth 10 | Set-Content "$ffDev\manifest.json" -Encoding utf8
Remove-Item "$ffDev\manifest-ff.json" -ErrorAction SilentlyContinue
Write-Host "  $ffDev\ (load this folder in about:debugging)" -ForegroundColor Green

Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
Write-Host "Done." -ForegroundColor Green
