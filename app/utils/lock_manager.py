"""Single master-password lock manager.

One shared password protects all locked categories.
Session unlock clears the lock for the entire app session.
"""

from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.config import AppConfig

_ITERATIONS = 100_000
_MASTER_KEY  = "master_lock"
_CATS_KEY    = "locked_categories"


class LockManager:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._session_unlocked = False

    # ------------------------------------------------------------------
    # Master password
    # ------------------------------------------------------------------

    def has_master_password(self) -> bool:
        return bool(self._config.get(_MASTER_KEY))

    def set_master_password(self, password: str) -> None:
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=_ITERATIONS)
        key = kdf.derive(password.encode("utf-8"))
        self._config.set(_MASTER_KEY, {
            "hash": base64.b64encode(key).decode(),
            "salt": base64.b64encode(salt).decode(),
        })
        self._session_unlocked = False

    def remove_master_password(self) -> None:
        self._config.set(_MASTER_KEY, None)
        self._config.set(_CATS_KEY, [])
        self._session_unlocked = False

    def verify(self, password: str) -> bool:
        lock = self._config.get(_MASTER_KEY)
        if not lock:
            return True
        salt = base64.b64decode(lock["salt"])
        stored = base64.b64decode(lock["hash"])
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=_ITERATIONS)
        try:
            kdf.verify(password.encode("utf-8"), stored)
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Session
    # ------------------------------------------------------------------

    def unlock_session(self, password: str) -> bool:
        if self.verify(password):
            self._session_unlocked = True
            return True
        return False

    def lock_session(self) -> None:
        self._session_unlocked = False

    # ------------------------------------------------------------------
    # Per-category lock toggle
    # ------------------------------------------------------------------

    def locked_categories(self) -> set[str]:
        return set(self._config.get(_CATS_KEY) or [])

    def add_locked_category(self, category: str) -> None:
        cats = self.locked_categories()
        cats.add(category)
        self._config.set(_CATS_KEY, sorted(cats))

    def remove_locked_category(self, category: str) -> None:
        cats = self.locked_categories()
        cats.discard(category)
        self._config.set(_CATS_KEY, sorted(cats))

    def is_locked(self, category: str) -> bool:
        if self._session_unlocked or not self.has_master_password():
            return False
        return category in self.locked_categories()

    def rename_category(self, old: str, new: str) -> None:
        cats = self.locked_categories()
        if old in cats:
            cats.discard(old)
            cats.add(new)
            self._config.set(_CATS_KEY, sorted(cats))
