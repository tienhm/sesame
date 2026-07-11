"""Export/import vault data to/from an encrypted .sesame file.

File format (JSON wrapper):
  {
    "version": 1,
    "salt": "<base64 16 bytes>",
    "nonce": "<base64 12 bytes>",
    "ciphertext": "<base64 AES-256-GCM ciphertext + tag>"
  }

Plaintext (before encryption):
  {
    "entries": [<Entry.to_dict()>, ...],
    "secrets": {"<entry_id>": "<secret>", ...}
  }
"""

from __future__ import annotations

import base64
import json
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

_ITERATIONS = 600_000
_FILE_VERSION = 1


def export_vault(entries, get_secret_fn, password: str) -> bytes:
    """Return encrypted .sesame file bytes."""
    salt = os.urandom(16)
    nonce = os.urandom(12)
    key = _derive_key(password.encode("utf-8"), salt)

    payload = {
        "entries": [e.to_dict() for e in entries],
        "secrets": {e.id: get_secret_fn(e.id) for e in entries},
    }
    plaintext = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)

    file_data = {
        "version": _FILE_VERSION,
        "salt": base64.b64encode(salt).decode(),
        "nonce": base64.b64encode(nonce).decode(),
        "ciphertext": base64.b64encode(ciphertext).decode(),
    }
    return json.dumps(file_data, indent=2).encode("utf-8")


def import_vault(file_bytes: bytes, password: str) -> tuple[list[dict], dict[str, str]]:
    """Decrypt .sesame file bytes.

    Returns (entries_dicts, secrets_dict).
    Raises ValueError on wrong password or corrupted file.
    """
    try:
        file_data = json.loads(file_bytes.decode("utf-8"))
    except Exception:
        raise ValueError("Not a valid .sesame file.")

    if file_data.get("version") != _FILE_VERSION:
        raise ValueError(f"Unsupported file version: {file_data.get('version')}")

    salt = base64.b64decode(file_data["salt"])
    nonce = base64.b64decode(file_data["nonce"])
    ciphertext = base64.b64decode(file_data["ciphertext"])

    key = _derive_key(password.encode("utf-8"), salt)

    try:
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, None)
    except Exception:
        raise ValueError("Wrong password or corrupted file.")

    payload = json.loads(plaintext.decode("utf-8"))
    return payload["entries"], payload["secrets"]


def _derive_key(password: bytes, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=_ITERATIONS,
    )
    return kdf.derive(password)
