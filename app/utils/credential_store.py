"""Direct Windows Credential Manager access for entry secrets.

Layout (single credential per entry):
  TargetName     = "SZM:<entry.id>"
  UserName       = ""  (unused — kept empty)
  CredentialBlob = JSON: {"p": "<password>", "o": "<otp_secret>"}
                   Legacy plain-text blob is auto-migrated on first read.

Storing both fields in one blob halves the number of Credential Manager
entries compared to keeping separate SZM:<id> and SZM:<id>:otp entries.

On non-Windows platforms falls back to an in-memory dict.
"""

from __future__ import annotations

import json
import logging
import sys

logger = logging.getLogger(__name__)

_TARGET_PREFIX = "SZM"
_dev_store: dict[str, dict] = {}   # {entry_id: {"p": str, "o": str}}


def _target_name(entry_id: str) -> str:
    return f"{_TARGET_PREFIX}:{entry_id}"


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _decode_blob(raw) -> dict:
    """Decode CredentialBlob → {"p": password, "o": otp}.

    Handles three cases:
      1. New format  : JSON bytes  → {"p": "...", "o": "..."}
      2. Legacy JSON : plain-text JSON string
      3. Legacy plain: raw password string (no JSON)
    """
    if not raw:
        return {"p": "", "o": ""}
    text = raw.decode("utf-16-le") if isinstance(raw, (bytes, bytearray)) else str(raw)
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return {"p": data.get("p", ""), "o": data.get("o", "")}
    except (json.JSONDecodeError, ValueError):
        pass
    # Legacy plain-text password
    return {"p": text, "o": ""}


def _encode_blob(password: str, otp: str) -> str:
    return json.dumps({"p": password, "o": otp}, ensure_ascii=False)


def _read_raw(entry_id: str) -> dict:
    if sys.platform != "win32":
        return _dev_store.get(entry_id, {"p": "", "o": ""})
    import pywintypes, win32cred
    try:
        cred = win32cred.CredRead(_target_name(entry_id), win32cred.CRED_TYPE_GENERIC, 0)
        return _decode_blob(cred["CredentialBlob"])
    except pywintypes.error:
        return {"p": "", "o": ""}


def _write_raw(entry_id: str, password: str, otp: str) -> None:
    if sys.platform != "win32":
        _dev_store[entry_id] = {"p": password, "o": otp}
        return
    import win32cred
    win32cred.CredWrite({
        "Type":           win32cred.CRED_TYPE_GENERIC,
        "TargetName":     _target_name(entry_id),
        "UserName":       "",
        "CredentialBlob": _encode_blob(password, otp),
        "Comment":        "Sesame",
        "Persist":        win32cred.CRED_PERSIST_LOCAL_MACHINE,
    }, 0)


# ---------------------------------------------------------------------------
# Public API — password
# ---------------------------------------------------------------------------

def set_secret(entry_id: str, secret: str) -> None:
    data = _read_raw(entry_id)
    _write_raw(entry_id, secret, data["o"])


def get_secret(entry_id: str) -> str:
    return _read_raw(entry_id)["p"]


def delete_secret(entry_id: str) -> None:
    """Remove the entire credential (password + OTP) from Credential Manager."""
    if sys.platform != "win32":
        _dev_store.pop(entry_id, None)
        return
    import pywintypes, win32cred
    for target in (_target_name(entry_id),
                   f"{_TARGET_PREFIX}:{entry_id}:otp"):   # legacy
        try:
            win32cred.CredDelete(target, win32cred.CRED_TYPE_GENERIC, 0)
        except pywintypes.error:
            pass


# ---------------------------------------------------------------------------
# Public API — OTP secret
# ---------------------------------------------------------------------------

def set_otp_secret(entry_id: str, otp: str) -> None:
    data = _read_raw(entry_id)
    _write_raw(entry_id, data["p"], otp)


def get_otp_secret(entry_id: str) -> str:
    otp = _read_raw(entry_id)["o"]
    if otp:
        return otp
    # Legacy fallback: separate SZM:<id>:otp credential
    if sys.platform != "win32":
        return ""
    import pywintypes, win32cred
    try:
        cred = win32cred.CredRead(f"{_TARGET_PREFIX}:{entry_id}:otp",
                                  win32cred.CRED_TYPE_GENERIC, 0)
        blob = cred["CredentialBlob"]
        legacy = (blob.decode("utf-16-le") if isinstance(blob, (bytes, bytearray))
                  else str(blob)) if blob else ""
        if legacy:
            set_otp_secret(entry_id, legacy)   # migrate into main entry
            try:
                win32cred.CredDelete(f"{_TARGET_PREFIX}:{entry_id}:otp",
                                     win32cred.CRED_TYPE_GENERIC, 0)
            except pywintypes.error:
                pass
        return legacy
    except pywintypes.error:
        return ""


def delete_otp_secret(entry_id: str) -> None:
    data = _read_raw(entry_id)
    _write_raw(entry_id, data["p"], "")
    # Clean up legacy separate OTP entry
    if sys.platform != "win32":
        return
    import pywintypes, win32cred
    try:
        win32cred.CredDelete(f"{_TARGET_PREFIX}:{entry_id}:otp",
                             win32cred.CRED_TYPE_GENERIC, 0)
    except pywintypes.error:
        pass
