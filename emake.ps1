# Package Sesame Pass extension for Chrome, Edge, and Firefox.
# Output: dist\ext\sesame-pass-chrome-vX.Y.zip
#         dist\ext\sesame-pass-edge-vX.Y.zip
#         dist\ext\sesame-pass-firefox-vX.Y.xpi
#         dist\ext\firefox-dev\  (unpacked, for about:debugging)
Set-Location $PSScriptRoot
Add-Type -Assembly "System.IO.Compression"
Add-Type -Assembly "System.IO.Compression.FileSystem"

function Compress-WithForwardSlashes($sourceDir, $destFile) {
    $sourceDir = (Resolve-Path $sourceDir).Path
    # .NET resolves relative paths against Environment.CurrentDirectory, not PS $PWD.
    # Convert to absolute so ZipFile::Open finds the right location.
    $destFile  = [System.IO.Path]::GetFullPath([System.IO.Path]::Combine($PWD.Path, $destFile))
    $zip = [System.IO.Compression.ZipFile]::Open($destFile, [System.IO.Compression.ZipArchiveMode]::Create)
    Get-ChildItem $sourceDir -Recurse -File | ForEach-Object {
        $entry = $_.FullName.Substring($sourceDir.Length + 1).Replace('\', '/')
        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $_.FullName, $entry) | Out-Null
    }
    $zip.Dispose()
}

$verLine = Select-String -Path main.py -Pattern '__version__\s*=\s*"([^"]+)"'
$version = $verLine.Matches[0].Groups[1].Value   # e.g. "1.6"
$semver  = "$version.0"                           # "1.6.0" for manifest

Write-Host "Packaging Sesame Pass extension v$version" -ForegroundColor Cyan

$outDir = "dist\ext"
$src    = "extension"
$tmp    = "$outDir\_tmp"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

# Builds one package. $outName is a file (zip/xpi) or a directory name (unpack).
function Make-Package($browser, $outName, $unpack = $false) {
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Force -Path $tmp | Out-Null
    Copy-Item "$src\*" $tmp -Recurse

    if ($browser -eq "firefox") { $baseMf = "$src\manifest-ff.json" }
    else                         { $baseMf = "$tmp\manifest.json" }

    $mf = Get-Content $baseMf -Raw | ConvertFrom-Json
    $mf.version = $semver
    $mf.PSObject.Properties.Remove("key")   # not allowed by Chrome/Edge Web Store
    $mf | ConvertTo-Json -Depth 10 | Set-Content "$tmp\manifest.json" -Encoding utf8
    Remove-Item "$tmp\manifest-ff.json" -ErrorAction SilentlyContinue

    $dest = "$outDir\$outName"
    Remove-Item -Recurse -Force $dest -ErrorAction SilentlyContinue

    if ($unpack) {
        Move-Item $tmp $dest
    } else {
        # Use .NET ZipFile to ensure forward-slash paths (Firefox rejects backslashes)
        $zipTmp = "$outDir\_pkg.zip"
        Remove-Item $zipTmp -ErrorAction SilentlyContinue
        Compress-WithForwardSlashes $tmp $zipTmp
        Rename-Item $zipTmp $outName
        Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
    }
    Write-Host "  $dest" -ForegroundColor Green
}

Make-Package "chrome"  "sesame-pass-chrome-v$version.zip"
Make-Package "edge"    "sesame-pass-edge-v$version.zip"
Make-Package "firefox" "sesame-pass-firefox-v$version.xpi"
Make-Package "firefox" "firefox-dev" -unpack $true   # load this folder in about:debugging

Write-Host "Done." -ForegroundColor Green
