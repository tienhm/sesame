"""Auto-login — blind keystroke injection after an entry's URL is opened.

There is no way to inspect the page DOM from a separate desktop process, so
this cannot target "the correct field": it just re-asserts the foreground
window (best-effort auto-locate — normally already the browser, since
opening a URL focuses whatever handles it) and types:

    <username> TAB <secret>

with no trailing Enter, so the user can check focus landed correctly before
submitting. Timing (how long to wait after opening the URL) is caller-
controlled via Entry.auto_login_ms — this module does not try to detect
"page loaded".

No-op on non-Windows platforms.
"""

from __future__ import annotations

import ctypes
import logging
import sys
import time

logger = logging.getLogger(__name__)

_VK_TAB = 0x09
_INPUT_KEYBOARD = 1
_KEYEVENTF_UNICODE = 0x0004
_KEYEVENTF_KEYUP = 0x0002
_INTER_KEY_DELAY_S = 0.012  # small gap so JS-heavy forms register each keystroke

# ctypes Structure/Union definitions are plain Python — safe to build on any
# platform. Only calling into ctypes.windll (below) is Windows-only.
_PUL = ctypes.POINTER(ctypes.c_ulong)


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", _PUL),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", _KEYBDINPUT)]


class _INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("ii", _INPUT_UNION)]


def _send_input(events: list[_INPUT]) -> None:
    n = len(events)
    arr = (_INPUT * n)(*events)
    ctypes.windll.user32.SendInput(n, arr, ctypes.sizeof(_INPUT))


def _key_event(vk: int = 0, scan: int = 0, flags: int = 0) -> _INPUT:
    extra = ctypes.pointer(ctypes.c_ulong(0))
    return _INPUT(type=_INPUT_KEYBOARD, ii=_INPUT_UNION(ki=_KEYBDINPUT(vk, scan, flags, 0, extra)))


def _send_tab() -> None:
    _send_input([_key_event(vk=_VK_TAB), _key_event(vk=_VK_TAB, flags=_KEYEVENTF_KEYUP)])
    time.sleep(_INTER_KEY_DELAY_S)


def _type_text(text: str) -> None:
    for ch in text:
        code = ord(ch)
        _send_input([
            _key_event(scan=code, flags=_KEYEVENTF_UNICODE),
            _key_event(scan=code, flags=_KEYEVENTF_UNICODE | _KEYEVENTF_KEYUP),
        ])
        time.sleep(_INTER_KEY_DELAY_S)


def _ensure_foreground() -> None:
    """Best-effort auto-locate: re-assert whatever window is currently in the
    foreground. Opening a URL normally already focuses the browser, so in
    practice this is just a safety net — no window hunting by title/class."""
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    if hwnd:
        ctypes.windll.user32.SetForegroundWindow(hwnd)


def send_credentials(username: str, secret: str) -> None:
    if sys.platform != "win32":
        logger.debug("send_credentials: not on Windows, skipping.")
        return

    _ensure_foreground()
    if username:
        _type_text(username)
        _send_tab()
    if secret:
        _type_text(secret)
