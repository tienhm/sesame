"""Parse OTP URIs from Google Authenticator and standard otpauth:// format.

Supported input formats
-----------------------
1. Standard TOTP URI:
     otpauth://totp/LABEL?secret=BASE32&issuer=ISSUER

2. Google Authenticator migration URI:
     otpauth-migration://offline?data=BASE64_PROTOBUF
   (contains one or more TOTP/HOTP entries encoded as protobuf)

3. Multi-line text containing any of the above — each URI on its own line
   (useful when a QR scanner pastes multiple URIs).
"""

from __future__ import annotations

import base64
import logging
from urllib.parse import parse_qs, unquote, urlparse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_uris(text: str) -> list[dict]:
    """Return a list of dicts with keys: name, issuer, secret.

    Accepts a single URI or newline-separated URIs.
    """
    results: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("otpauth-migration://"):
            results.extend(_parse_migration_uri(line))
        elif line.startswith("otpauth://"):
            entry = _parse_otpauth_uri(line)
            if entry:
                results.append(entry)
    return results


def scan_qr_image(path: str) -> list[str] | None:
    """Decode QR code(s) from an image file.

    Returns a list of decoded URI strings, or None if pyzbar is unavailable.
    Raises on file-read errors.
    """
    try:
        from pyzbar import pyzbar          # type: ignore
        from PIL import Image
        img = Image.open(path)
        decoded = pyzbar.decode(img)
        return [d.data.decode("utf-8") for d in decoded]
    except ImportError:
        return None   # pyzbar not installed


# ---------------------------------------------------------------------------
# Standard otpauth:// URI
# ---------------------------------------------------------------------------

def _parse_otpauth_uri(uri: str) -> dict | None:
    try:
        p = urlparse(uri)
        if p.scheme != "otpauth":
            return None
        params = parse_qs(p.query)
        secret = params.get("secret", [""])[0].upper().replace(" ", "")
        if not secret:
            return None
        issuer  = params.get("issuer", [""])[0].strip()
        label   = unquote(p.path.lstrip("/")).strip()
        # label is often "Service:account@email" or just "account@email"
        if ":" in label:
            label_service, account = label.split(":", 1)
            issuer   = issuer or label_service.strip()
            account  = account.strip()
        else:
            account = label
        service_name = issuer or account
        return {"name": service_name, "account": account, "issuer": issuer, "secret": secret}
    except Exception as e:
        logger.debug("Failed to parse otpauth URI: %s", e)
        return None


# ---------------------------------------------------------------------------
# Google Authenticator migration protobuf
# ---------------------------------------------------------------------------

def _parse_migration_uri(uri: str) -> list[dict]:
    try:
        p = urlparse(uri)
        data_b64 = parse_qs(p.query).get("data", [""])[0]
        # URL-encoded '+' → space issue; re-encode
        data_b64 = data_b64.replace(" ", "+")
        raw = base64.b64decode(data_b64 + "==")
        return _decode_migration_payload(raw)
    except Exception as e:
        logger.debug("Failed to parse migration URI: %s", e)
        return []


def _read_varint(data: bytes, pos: int) -> tuple[int, int]:
    result, shift = 0, 0
    while pos < len(data):
        b = data[pos]; pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7
    return result, pos


def _decode_migration_payload(data: bytes) -> list[dict]:
    entries, pos = [], 0
    while pos < len(data):
        try:
            tag, pos = _read_varint(data, pos)
            field, wire = tag >> 3, tag & 0x7
            if wire == 2:           # length-delimited
                length, pos = _read_varint(data, pos)
                value = data[pos:pos + length]; pos += length
                if field == 1:      # OtpParameters message
                    entry = _decode_otp_parameters(value)
                    if entry:
                        entries.append(entry)
            elif wire == 0:         # varint — skip
                _, pos = _read_varint(data, pos)
            elif wire == 5:         # 32-bit — skip
                pos += 4
            elif wire == 1:         # 64-bit — skip
                pos += 8
            else:
                break
        except Exception:
            break
    return entries


def _decode_otp_parameters(data: bytes) -> dict | None:
    secret_bytes, name, issuer = None, "", ""
    pos = 0
    while pos < len(data):
        try:
            tag, pos = _read_varint(data, pos)
            field, wire = tag >> 3, tag & 0x7
            if wire == 2:
                length, pos = _read_varint(data, pos)
                value = data[pos:pos + length]; pos += length
                if field == 1:      # secret (raw bytes)
                    secret_bytes = value
                elif field == 2:    # name
                    name = value.decode("utf-8", errors="replace")
                elif field == 3:    # issuer
                    issuer = value.decode("utf-8", errors="replace")
            elif wire == 0:
                _, pos = _read_varint(data, pos)
            else:
                break
        except Exception:
            break

    if not secret_bytes:
        return None
    secret = base64.b32encode(secret_bytes).decode().rstrip("=")
    # name field from protobuf is often "Service:account" or just "account"
    account = name
    service_name = issuer
    if ":" in name:
        parts = name.split(":", 1)
        service_name = service_name or parts[0].strip()
        account = parts[1].strip()
    service_name = service_name or account
    return {"name": service_name, "account": account, "issuer": issuer, "secret": secret}
