"""Font Awesome 6 Free Solid icon helper."""

from __future__ import annotations

import os
import sys

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QPushButton

_FA_FAMILY: str | None = None


def _font_path() -> str:
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "resources", "fa-solid-900.ttf")
    return os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "resources", "fa-solid-900.ttf")
    )


def load() -> None:
    global _FA_FAMILY
    fid = QFontDatabase.addApplicationFont(_font_path())
    if fid >= 0:
        families = QFontDatabase.applicationFontFamilies(fid)
        if families:
            _FA_FAMILY = families[0]


def fa_font(size: int = 14) -> QFont:
    f = QFont(_FA_FAMILY or "")
    f.setPointSize(size)
    return f


def apply_fa(btn: QPushButton, icon: str, size: int = 14) -> None:
    btn.setText(icon)
    btn.setFont(fa_font(size))


# ---------------------------------------------------------------------------
# Font Awesome 6 Free Solid codepoints (Private Use Area U+F000+)
# ---------------------------------------------------------------------------

class FA:
    KEY        = chr(0xf084)  # fa-key
    USER       = chr(0xf007)  # fa-user
    PEN        = chr(0xf304)  # fa-pen
    EYE        = chr(0xf06e)  # fa-eye
    EYE_SLASH  = chr(0xf070)  # fa-eye-slash
    DICE       = chr(0xf522)  # fa-dice
    ROTATE     = chr(0xf021)  # fa-arrows-rotate
    HEART      = chr(0xf004)  # fa-heart
    GEAR       = chr(0xf013)  # fa-gear
    XMARK      = chr(0xf00d)  # fa-xmark
    CIRCLE_DOT = chr(0xf192)  # fa-circle-dot
    COPY       = chr(0xf0c5)  # fa-copy
    LOCK       = chr(0xf023)  # fa-lock
    UNLOCK     = chr(0xf09c)  # fa-unlock
