"""Detect installed browsers via the Windows registry.

Used by Settings → Extensions to show which browsers Sesame Pass can be
installed into. No-op (returns none) on non-Windows platforms.
"""

from __future__ import annotations

import sys

# (key, hive, subkey) — presence of the subkey means the browser is installed.
_REGISTRY_KEYS = [
    ("chrome",  "HKCU", r"Software\Google\Chrome"),
    ("edge",    "HKLM", r"SOFTWARE\Microsoft\Edge"),
    ("firefox", "HKCU", r"Software\Mozilla\Firefox"),
    ("brave",   "HKCU", r"Software\BraveSoftware\Brave-Browser"),
    ("opera",   "HKCU", r"Software\Opera Software"),
]

DISPLAY_NAMES = {
    "chrome":  "Chrome",
    "edge":    "Edge",
    "firefox": "Firefox",
    "brave":   "Brave",
    "opera":   "Opera",
}


def detect_installed_browsers() -> list[str]:
    """Return the keys (from _REGISTRY_KEYS) of browsers found installed,
    in the order listed above."""
    if sys.platform != "win32":
        return []
    import winreg
    hives = {"HKCU": winreg.HKEY_CURRENT_USER, "HKLM": winreg.HKEY_LOCAL_MACHINE}
    found = []
    for name, hive_name, subkey in _REGISTRY_KEYS:
        try:
            with winreg.OpenKey(hives[hive_name], subkey):
                found.append(name)
        except OSError:
            pass
    return found
