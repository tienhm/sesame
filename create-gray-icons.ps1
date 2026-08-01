Add-Type -Assembly "System.Drawing"

$srcDir = "extension\icons"
$dstDir = "extension\icons\gray"
New-Item -ItemType Directory -Force -Path $dstDir | Out-Null

Get-ChildItem "$srcDir\*.png" | ForEach-Object {
    $src = $_.FullName
    $dst = "$dstDir\$($_.Name)"

    $orig = [System.Drawing.Bitmap]::new($src)
    $gray = [System.Drawing.Bitmap]::new($orig.Width, $orig.Height)

    for ($x = 0; $x -lt $orig.Width; $x++) {
        for ($y = 0; $y -lt $orig.Height; $y++) {
            $p = $orig.GetPixel($x, $y)
            $g = [int](0.299 * $p.R + 0.587 * $p.G + 0.114 * $p.B)
            $gray.SetPixel($x, $y, [System.Drawing.Color]::FromArgb($p.A, $g, $g, $g))
        }
    }

    $gray.Save($dst, [System.Drawing.Imaging.ImageFormat]::Png)
    $orig.Dispose()
    $gray.Dispose()
    Write-Host "  $dst" -ForegroundColor Green
}
Write-Host "Done." -ForegroundColor Green
