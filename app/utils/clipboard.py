"""Clipboard utility — copy a secret and auto-clear after a timeout.

On Windows, secrets are copied with the
``ExcludeClipboardContentFromMonitorProcessing`` flag so that Windows
Clipboard History (Win+V) never stores them.
"""

from __future__ import annotations

import ctypes
import sys

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication

_CLEAR_AFTER_MS = 30_000  # 30 seconds

# Windows clipboard format that tells clipboard managers to skip this content
_CF_EXCLUDE_FORMAT = "ExcludeClipboardContentFromMonitorProcessing"
_cf_exclude_id: int = 0


def _set_clipboard_secret(text: str) -> None:
    """Set clipboard text, excluding it from Windows Clipboard History."""
    if sys.platform != "win32":
        QApplication.clipboard().setText(text)
        return

    global _cf_exclude_id

    try:
        user32   = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        # Declare return/arg types so 64-bit handles are not truncated
        kernel32.GlobalAlloc.restype  = ctypes.c_void_p
        kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
        kernel32.GlobalLock.restype   = ctypes.c_void_p
        kernel32.GlobalLock.argtypes  = [ctypes.c_void_p]
        kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
        kernel32.GlobalFree.argtypes  = [ctypes.c_void_p]
        user32.OpenClipboard.restype  = ctypes.c_bool
        user32.EmptyClipboard.restype = ctypes.c_bool
        user32.SetClipboardData.restype  = ctypes.c_void_p
        user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
        user32.CloseClipboard.restype = ctypes.c_bool
        user32.RegisterClipboardFormatW.restype  = ctypes.c_uint
        user32.RegisterClipboardFormatW.argtypes = [ctypes.c_wchar_p]

        if not _cf_exclude_id:
            _cf_exclude_id = user32.RegisterClipboardFormatW(_CF_EXCLUDE_FORMAT)

        CF_UNICODETEXT = 13
        GMEM_MOVEABLE  = 0x0002

        encoded = (text + "\0").encode("utf-16-le")
        hMem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(encoded))
        if not hMem:
            raise RuntimeError("GlobalAlloc failed")

        ptr = kernel32.GlobalLock(hMem)
        if not ptr:
            kernel32.GlobalFree(hMem)
            raise RuntimeError("GlobalLock failed")
        ctypes.memmove(ptr, encoded, len(encoded))
        kernel32.GlobalUnlock(hMem)

        if not user32.OpenClipboard(None):
            kernel32.GlobalFree(hMem)
            raise RuntimeError("OpenClipboard failed")

        user32.EmptyClipboard()
        user32.SetClipboardData(CF_UNICODETEXT, hMem)
        # hMem ownership transferred to clipboard — do NOT free
        if _cf_exclude_id:
            user32.SetClipboardData(_cf_exclude_id, None)
        user32.CloseClipboard()

    except Exception:
        # Fall back to Qt clipboard on any Win32 error
        QApplication.clipboard().setText(text)


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

        _set_clipboard_secret(secret)
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
        _set_clipboard_secret(text)

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
