"""Movement confirmation dialog — shown when the user clicks the blinking bubble."""

from __future__ import annotations

import os
import random
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

_QUOTES = [
    "Your chair misses you already. Prove it wrong. 🦵",
    "Scientists say sitting is the new smoking.\nTime to un-smoke yourself. 🚭",
    "Even penguins waddle around sometimes.\nYour turn. 🐧",
    "Your blood is pooling.\nLike a tiny swimming pool. Get up! 🏊",
    "The couch will still be there in 2 minutes. Go walk. 🛋️",
    "Your spine is texting you: 'please move'. 📱",
    "Gravity called. It wants you to fight back. 🌍",
    "A watched screen never loads. Go stretch instead. ⏳",
    "Your future self thanks you for getting up. 🙏",
    "Sitting is just slow-motion falling. Stand up! ⬆️",
    "Your legs have been in airplane mode too long. 🛫",
    "Even robots need to reboot. Time for a walk. 🤖",
    "Your muscles are sending a strongly worded letter. 💪",
    "Plot twist: the real treasure was standing up all along. 🗺️",
    "Breaking news: Human spotted standing. Film at 11. 📺",
]


def _quotes_path() -> Path:
    appdata = os.environ.get("APPDATA") or Path.home()
    directory = Path(appdata) / "Sesame"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "fun_quotes.txt"


def _load_quotes() -> list[str]:
    """Read %APPDATA%\\Sesame\\fun_quotes.txt (one quote per line); fall back
    to _QUOTES if the file is missing, unreadable, or empty. Loaded at runtime
    like config.json/cache.json — not bundled into the build."""
    try:
        with open(_quotes_path(), encoding="utf-8") as fh:
            lines = [line.strip() for line in fh if line.strip()]
        if lines:
            return lines
    except (OSError, UnicodeDecodeError):
        pass
    return _QUOTES


class MovementConfirmDialog(QDialog):
    """Non-blocking dialog with a funny quote and two action buttons."""

    confirmed = Signal()   # "I moved!" clicked
    snoozed   = Signal()   # "Remind me in 5 min" clicked

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Time to move! 🏃")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setMinimumWidth(340)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 20)

        quote_lbl = QLabel(random.choice(_load_quotes()))
        quote_lbl.setWordWrap(True)
        quote_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        quote_lbl.setStyleSheet(
            "font-size: 14px; color: #e8eaed; line-height: 1.5;"
        )
        layout.addWidget(quote_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        snooze_btn = QPushButton("Remind me in 5 min")
        snooze_btn.setProperty("flat", True)
        snooze_btn.clicked.connect(self._on_snooze)

        confirm_btn = QPushButton("✓  I moved!")
        confirm_btn.setDefault(True)
        confirm_btn.clicked.connect(self._on_confirm)

        btn_row.addWidget(snooze_btn)
        btn_row.addWidget(confirm_btn)
        layout.addLayout(btn_row)

    def _on_confirm(self) -> None:
        self.confirmed.emit()
        self.accept()

    def _on_snooze(self) -> None:
        self.snoozed.emit()
        self.accept()
