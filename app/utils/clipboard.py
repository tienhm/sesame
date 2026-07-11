"""Clipboard utility — copy a secret and auto-clear after a timeout."""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication

_CLEAR_AFTER_MS = 30_000  # 30 seconds


class ClipboardManager(QObject):
    """Copies text to the system clipboard and clears it after a timeout.

    Signals:
        countdown_tick(entry_id, seconds_remaining)  — fires every second
        cleared(entry_id)                             — fires when clipboard is cleared
    """

    countdown_tick = Signal(str, int)
    cleared = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setInterval(1_000)
        self._timer.timeout.connect(self._on_tick)
        self._entry_id: str = ""
        self._remaining: int = 0

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def copy(self, entry_id: str, secret: str) -> None:
        """Copy *secret* to clipboard, start countdown for *entry_id*."""
        if self._entry_id and self._entry_id != entry_id:
            old_id = self._entry_id
            self._timer.stop()
            self._entry_id = ""
            self._remaining = 0
            self.cleared.emit(old_id)

        QApplication.clipboard().setText(secret)
        self._entry_id = entry_id
        self._remaining = _CLEAR_AFTER_MS // 1_000
        self._timer.start()
        self.countdown_tick.emit(self._entry_id, self._remaining)

    def copy_plain(self, text: str) -> None:
        """Copy *text* to clipboard without auto-clear or countdown."""
        self._timer.stop()
        if self._entry_id:
            eid = self._entry_id
            self._entry_id = ""
            self._remaining = 0
            self.cleared.emit(eid)
        QApplication.clipboard().setText(text)

    def cancel(self) -> None:
        """Stop any pending clear without wiping the clipboard."""
        self._timer.stop()
        self._entry_id = ""
        self._remaining = 0

    @property
    def active_entry_id(self) -> str:
        return self._entry_id

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _on_tick(self) -> None:
        self._remaining -= 1
        if self._remaining <= 0:
            self._timer.stop()
            QApplication.clipboard().clear()
            eid = self._entry_id
            self._entry_id = ""
            self.cleared.emit(eid)
        else:
            self.countdown_tick.emit(self._entry_id, self._remaining)
