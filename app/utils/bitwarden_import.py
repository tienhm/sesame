"""Parse a Bitwarden JSON export (unencrypted) into Sesame's vault format.

Only login items (type=1) are imported; notes, cards, and identities are skipped.

Returns the same (entries_dicts, secrets, otp_secrets) triple as vault_io.import_vault
so the caller can reuse the same import loop.
"""

from __future__ import annotations

import json
import logging
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)

_TYPE_LOGIN = 1


def parse_bitwarden_json(
    file_bytes: bytes,
) -> tuple[list[dict], dict[str, str], dict[str, str]]:
    """Parse a Bitwarden unencrypted JSON export.

    Returns (entries_dicts, secrets_dict, otp_secrets_dict).
    Raises ValueError on encrypted export or malformed file.
    """
    try:
        data = json.loads(file_bytes.decode("utf-8-sig"))  # utf-8-sig strips BOM
    except Exception:
        raise ValueError("Not a valid JSON file.")

    if not isinstance(data, dict):
        raise ValueError("Unexpected format — root must be a JSON object.")

    if data.get("encrypted", False):
        raise ValueError(
            "This file is encrypted.\n"
            "Re-export from Bitwarden with 'No encryption' and try again."
        )

    items = data.get("items")
    if not isinstance(items, list):
        raise ValueError("Unexpected format — 'items' list not found.")

    # folder id → name
    folders: dict[str, str] = {}
    for f in (data.get("folders") or []):
        fid  = f.get("id", "")
        name = (f.get("name") or "").strip()
        if fid and name:
            folders[fid] = name

    entries_dicts: list[dict] = []
    secrets:       dict[str, str] = {}
    otp_secrets:   dict[str, str] = {}

    sid = 0
    for item in items:
        if item.get("type") != _TYPE_LOGIN:
            continue
        login = item.get("login") or {}

        name     = (item.get("name") or "").strip() or "Untitled"
        username = (login.get("username") or "").strip()
        password = login.get("password") or ""
        totp_raw = (login.get("totp") or "").strip()

        uris = login.get("uris") or []
        raw_url = (uris[0].get("uri") or "").strip() if uris else ""
        url = _strip_url_protocol(raw_url)

        category = folders.get(item.get("folderId") or "", "General") or "General"

        key = str(sid)
        sid += 1

        entries_dicts.append({
            "id":            key,
            "name":          name,
            "username":      username,
            "category":      category,
            "tags":          [],
            "url":           url,
            "auto_login_ms": 0,
            "has_otp":       bool(totp_raw),
        })
        secrets[key] = password

        if totp_raw:
            otp = _extract_otp_secret(totp_raw)
            if otp:
                otp_secrets[key] = otp

    return entries_dicts, secrets, otp_secrets


def _strip_url_protocol(url: str) -> str:
    for prefix in ("https://", "http://"):
        if url.lower().startswith(prefix):
            return url[len(prefix):]
    return url


def _extract_otp_secret(raw: str) -> str:
    """Return the bare base32 secret from an otpauth:// URI or a raw base32 string.

    Returns empty string for unrecognised URI schemes (e.g. steam://).
    """
    if raw.startswith("otpauth://"):
        try:
            params = parse_qs(urlparse(raw).query)
            return params.get("secret", [""])[0].upper().replace(" ", "")
        except Exception:
            logger.debug("Failed to parse otpauth URI: %s", raw)
            return ""
    if "://" in raw:
        # Unknown URI scheme (steam://, etc.) — not a raw base32 secret
        logger.debug("Skipping unsupported TOTP scheme: %s", raw[:30])
        return ""
    return raw.upper().replace(" ", "")
