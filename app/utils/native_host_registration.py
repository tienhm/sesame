"""Registers the Sesame Pass native-messaging host with Chrome/Edge/Firefox so
the extension can reach it via `chrome.runtime.connectNative` — no manual
pairing step.

Writes two host manifest JSONs (Chrome/Edge use `allowed_origins`;
Firefox uses `allowed_extensions`) and points each browser's
`NativeMessagingHosts` registry key at the correct one. Idempotent and
cheap — safe to call on every app startup.

The Chrome/Edge extension ID is pinned via a fixed keypair (`"key"` in
extension/manifest.json). The Firefox addon ID is pinned via
`browser_specific_settings.gecko.id` in the Firefox build of the manifest.
"""

from __future__ import annotations

import json
import logging
import os
import sys

logger = logging.getLogger(__name__)

HOST_NAME       = "com.sesame.pass"
EXTENSION_ID    = "gkfncbifphnljdllbcophdpndkpdlnpi"   # Chrome/Edge — derived from "key" in manifest.json
FIREFOX_ADDON_ID = "sesame-pass@szm"                   # Firefox — set in browser_specific_settings.gecko.id

# (hive, subkey, manifest_variant) where variant is "chrome" or "firefox"
_REGISTRY_TARGETS = [
    ("HKCU", rf"Software\Google\Chrome\NativeMessagingHosts\{HOST_NAME}",   "chrome"),
    ("HKCU", rf"Software\Microsoft\Edge\NativeMessagingHosts\{HOST_NAME}",  "chrome"),
    ("HKCU", rf"Software\Mozilla\NativeMessagingHosts\{HOST_NAME}",         "firefox"),
]


def _native_host_exe_path() -> str:
    """Return a stable path to szm_door.exe, deploying it first if needed.

    When frozen: the exe is bundled inside Sesame (binaries in sesame.spec) and
    extracted by PyInstaller to sys._MEIPASS — a temp dir that changes every run.
    We copy it to %LOCALAPPDATA%\\Sesame\\ once (or whenever it changes) so the
    browser manifests always point to a fixed, version-stable path.

    When running from source: native_host.py is used directly (dev only).
    """
    if getattr(sys, "frozen", False):
        stable_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Sesame")
        os.makedirs(stable_dir, exist_ok=True)
        stable_path = os.path.join(stable_dir, "szm_door.exe")
        bundled = os.path.join(sys._MEIPASS, "szm_door.exe")
        if os.path.exists(bundled):
            import shutil
            try:
                shutil.copy2(bundled, stable_path)
            except OSError:
                # szm_door.exe may be in use by an active browser session — skip
                # the copy; the existing stable copy is still valid.
                if not os.path.exists(stable_path):
                    logger.exception("native_host_registration: could not deploy %s", stable_path)
        elif not os.path.exists(stable_path):
            logger.warning("native_host_registration: szm_door.exe not found in bundle (%s)", bundled)
        return stable_path
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(repo_root, "native_host.py")


def _base_dir() -> str:
    d = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Sesame")
    os.makedirs(d, exist_ok=True)
    return d


def _manifest_path(variant: str) -> str:
    suffix = ".firefox" if variant == "firefox" else ""
    return os.path.join(_base_dir(), f"{HOST_NAME}{suffix}.json")


def ensure_native_host_registered() -> None:
    """Write host manifests + registry keys for Chrome, Edge, and Firefox. No-op off Windows."""
    if sys.platform != "win32":
        return
    import winreg

    exe_path = _native_host_exe_path()

    manifests = {
        "chrome": {
            "name": HOST_NAME,
            "description": "Sesame Pass native bridge",
            "path": exe_path,
            "type": "stdio",
            "allowed_origins": [f"chrome-extension://{EXTENSION_ID}/"],
        },
        "firefox": {
            "name": HOST_NAME,
            "description": "Sesame Pass native bridge",
            "path": exe_path,
            "type": "stdio",
            "allowed_extensions": [FIREFOX_ADDON_ID],
        },
    }

    written: dict[str, str] = {}  # variant -> manifest path
    for variant, manifest in manifests.items():
        path = _manifest_path(variant)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)
            written[variant] = path
        except OSError:
            logger.exception("native_host_registration: could not write manifest %s", path)

    for hive_name, subkey, variant in _REGISTRY_TARGETS:
        if variant not in written:
            continue
        hive = winreg.HKEY_CURRENT_USER if hive_name == "HKCU" else winreg.HKEY_LOCAL_MACHINE
        try:
            with winreg.CreateKey(hive, subkey) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, written[variant])
        except OSError:
            logger.exception("native_host_registration: could not write registry key %s", subkey)
