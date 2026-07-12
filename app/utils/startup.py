"""Windows startup helper — register / unregister Sesame in HKCU Run key.

Uses the built-in `winreg` module; no admin privileges required because
HKCU is always writable by the current user.

On non-Windows platforms the functions are safe no-ops so the rest of the
app can import this module without errors during development on Linux/macOS.
"""

from __future__ import annotations

import logging
import sys

logger = logging.getLogger(__name__)

_APP_NAME = "Sesame"
_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _get_exe_path() -> str:
    """Return the path that should be registered.

    - When running as a PyInstaller bundle: path to the .exe
    - When running from source: `pythonw.exe <abs path to main.py>`
    """
    if getattr(sys, "frozen", False):
        return sys.executable  # PyInstaller .exe
    import os
    python = sys.executable.replace("python.exe", "pythonw.exe")
    main_py = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "main.py")
    )
    return f'"{python}" "{main_py}"'


def enable_startup() -> bool:
    """Write the Run registry key. Returns True on success."""
    if sys.platform != "win32":
        logger.debug("enable_startup: not on Windows, skipping.")
        return False
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _RUN_KEY,
            0,
            winreg.KEY_SET_VALUE,
        )
        winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, _get_exe_path())
        winreg.CloseKey(key)
        logger.info("Startup entry enabled.")
        return True
    except Exception:
        logger.exception("Failed to enable startup entry.")
        return False


def disable_startup() -> bool:
    """Remove the Run registry key. Returns True on success."""
    if sys.platform != "win32":
        logger.debug("disable_startup: not on Windows, skipping.")
        return False
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _RUN_KEY,
            0,
            winreg.KEY_SET_VALUE,
        )
        winreg.DeleteValue(key, _APP_NAME)
        winreg.CloseKey(key)
        logger.info("Startup entry removed.")
        return True
    except FileNotFoundError:
        return True  # already absent — that's fine
    except Exception:
        logger.exception("Failed to disable startup entry.")
        return False


def is_startup_enabled() -> bool:
    """Return True if the Run registry key exists."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _RUN_KEY,
            0,
            winreg.KEY_READ,
        )
        winreg.QueryValueEx(key, _APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        logger.exception("Could not query startup key.")
        return False


def ensure_startup_enabled() -> None:
    """Enable startup only if not already registered (call on first run)."""
    if not is_startup_enabled():
        enable_startup()
