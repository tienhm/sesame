"""Generate extension/icons/ from resources/icon.png.

resources/icon.png is the single source of truth for Sesame's logo — this
regenerates the browser extension's toolbar icon set from it instead of
maintaining a second, separately-exported icon set that can drift out of
sync. Also generates a dimmed/desaturated "gray" variant per size, used by
background.js to show a disconnected state (see extension/background.js).

Output is gitignored — run this instead of committing icons. Called
automatically by emake.ps1 and dev-ff.ps1 before they package/stage the
extension; run it manually first if you just want to "Load unpacked" the
extension/ folder directly for local testing.
"""

from __future__ import annotations

import os

from PIL import Image

_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
_SOURCE = os.path.join(_REPO_ROOT, "resources", "icon.png")
_OUT_DIR = os.path.join(_REPO_ROOT, "extension", "icons")
_GRAY_DIR = os.path.join(_OUT_DIR, "gray")
_SIZES = (16, 32, 48, 64, 128)
_GRAY_ALPHA_FACTOR = 0.55  # dim the gray variant's opacity, not just desaturate


def _gray_variant(img: Image.Image) -> Image.Image:
    r, g, b, a = img.convert("RGBA").split()
    gray = Image.merge("RGB", (r, g, b)).convert("L")
    gray_rgba = Image.merge("RGBA", (gray, gray, gray, a))
    gray_rgba.putalpha(a.point(lambda p: int(p * _GRAY_ALPHA_FACTOR)))
    return gray_rgba


def main() -> None:
    source = Image.open(_SOURCE).convert("RGBA")
    os.makedirs(_OUT_DIR, exist_ok=True)
    os.makedirs(_GRAY_DIR, exist_ok=True)

    for size in _SIZES:
        resized = source.resize((size, size), Image.LANCZOS)
        name = f"icon{size}.png"
        resized.save(os.path.join(_OUT_DIR, name))
        _gray_variant(resized).save(os.path.join(_GRAY_DIR, name))
        print(f"{name}: {size}x{size}")


if __name__ == "__main__":
    main()
