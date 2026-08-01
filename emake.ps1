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

    # Patch version in manifest
    $mf = Get-Content "$tmp\manifest.json" -Raw | ConvertFrom-Json
    $mf.version = $semver

    if ($browser -eq "firefox") {
        # Remove Chrome-specific "key" field (causes Firefox validation warning)
        $mf.PSObject.Properties.Remove("key")

        # Add gecko addon ID so the ID is stable across installs
        $gecko = [PSCustomObject]@{ id = "sesame-pass@szm" }
        $bss   = [PSCustomObject]@{ gecko = $gecko }
        $mf | Add-Member -NotePropertyName "browser_specific_settings" -NotePropertyValue $bss -Force
    }

    $mf | ConvertTo-Json -Depth 10 | Set-Content "$tmp\manifest.json" -Encoding utf8

    # Zip into output file
    $fullOut = "$outDir\$outFile"
    Remove-Item $fullOut -ErrorAction SilentlyContinue
    Compress-Archive -Path "$tmp\*" -DestinationPath $fullOut
    Write-Host "  $fullOut" -ForegroundColor Green
}

Make-Package "chrome"  "sesame-pass-chrome-v$version.zip"
Make-Package "edge"    "sesame-pass-edge-v$version.zip"
Make-Package "firefox" "sesame-pass-firefox-v$version.xpi"

Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
Write-Host "Done." -ForegroundColor Green
