"""Direct Windows Credential Manager access for entry secrets.

Bypasses `keyring`'s own TargetName/UserName conventions so the layout is
fully explicit and compact:

  TargetName     = "SZM:<entry.id>"   (entry.id is a short, reused-gap int)
  UserName       = ""                 (the real username lives in vault_index.json)
  CredentialBlob = the secret, UTF-16LE

On non-Windows platforms (dev/test), falls back to an in-memory dict so the
app can run without pywin32 installed.
"""

from __future__ import annotations

import logging
import sys

logger = logging.getLogger(__name__)

_TARGET_PREFIX = "SZM"

_dev_store: dict[str, str] = {}  # non-Windows fallback only, not persisted


def _target_name(entry_id: str) -> str:
    return f"{_TARGET_PREFIX}:{entry_id}"


def set_secret(entry_id: str, secret: str) -> None:
    if sys.platform != "win32":
        _dev_store[entry_id] = secret
        return

    import win32cred

    credential = {
        "Type": win32cred.CRED_TYPE_GENERIC,
        "TargetName": _target_name(entry_id),
        "UserName": "",
        "CredentialBlob": secret.encode("utf-16-le"),
        "Comment": "Sesame secret",
        "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE,
    }
    win32cred.CredWrite(credential, 0)


def get_secret(entry_id: str) -> str:
    if sys.platform != "win32":
        return _dev_store.get(entry_id, "")

    import pywintypes
    import win32cred

    try:
        cred = win32cred.CredRead(_target_name(entry_id), win32cred.CRED_TYPE_GENERIC, 0)
    except pywintypes.error:
        return ""
    return cred["CredentialBlob"].decode("utf-16-le")


def delete_secret(entry_id: str) -> None:
    if sys.platform != "win32":
        _dev_store.pop(entry_id, None)
        return

    import pywintypes
    import win32cred

    try:
        win32cred.CredDelete(_target_name(entry_id), win32cred.CRED_TYPE_GENERIC, 0)
    except pywintypes.error:
        pass
