"""Registers the Sesame Pass native-messaging host with Chrome/Edge so the
extension can reach it via `chrome.runtime.connectNative` — no manual
pairing step (unlike the old HTTP-loopback + pairing-code architecture).

Writes the host manifest JSON and points each browser's
`NativeMessagingHosts` registry key at it. Idempotent and cheap — safe to
call on every app startup, which is how it stays correct if Sesame gets
moved/reinstalled to a new path.

The extension's ID is pinned via a fixed keypair (`"key"` in
extension/manifest.json) specifically so `allowed_origins` below never has
to change between installs/updates — see Plan.md F011 mục F for how this ID
was generated.
"""

from __future__ import annotations

import json
import logging
import os
import sys

logger = logging.getLogger(__name__)

HOST_NAME = "com.sesame.pass"
EXTENSION_ID = "gkfncbifphnljdllbcophdpndkpdlnpi"

# (hive, subkey) — default value of each key is set to the manifest JSON path.
_REGISTRY_TARGETS = [
    ("HKCU", rf"Software\Google\Chrome\NativeMessagingHosts\{HOST_NAME}"),
    ("HKCU", rf"Software\Microsoft\Edge\NativeMessagingHosts\{HOST_NAME}"),
]


def _native_host_exe_path() -> str:
    """Path to the native host exe/script — sits next to the main Sesame exe
    when frozen (PyInstaller), or is native_host.py when running from source."""
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
        return os.path.join(base_dir, "sesame_native_host.exe")
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(repo_root, "native_host.py")


def _manifest_path() -> str:
    base_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Sesame")
    os.makedirs(base_dir, exist_ok=True)
    return os.path.join(base_dir, f"{HOST_NAME}.json")


def ensure_native_host_registered() -> None:
    """Write the host manifest + registry keys. No-op off Windows."""
    if sys.platform != "win32":
        return
    import winreg

    manifest = {
        "name": HOST_NAME,
        "description": "Sesame Pass native bridge",
        "path": _native_host_exe_path(),
        "type": "stdio",
        "allowed_origins": [f"chrome-extension://{EXTENSION_ID}/"],
    }
    manifest_path = _manifest_path()
    try:
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
    except OSError:
        logger.exception("native_host_registration: could not write manifest %s", manifest_path)
        return

    for hive_name, subkey in _REGISTRY_TARGETS:
        hive = winreg.HKEY_CURRENT_USER if hive_name == "HKCU" else winreg.HKEY_LOCAL_MACHINE
        try:
            with winreg.CreateKey(hive, subkey) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, manifest_path)
        except OSError:
            logger.exception("native_host_registration: could not write registry key %s", subkey)
