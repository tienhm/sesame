"""Vault — persists entries and secrets using Windows Credential Manager via keyring.

Layout in Credential Manager:
  Service: "Sesame"
  Username "vault_index"  → JSON list of Entry dicts (no secrets)
  Username "<entry.id>"   → the raw secret string for that entry
"""

from __future__ import annotations

import json
import logging
from typing import Optional

import keyring

from app.models.entry import Entry

logger = logging.getLogger(__name__)

_SERVICE = "Sesame"
_INDEX_KEY = "vault_index"


class Vault:
    def __init__(self) -> None:
        self._entries: list[Entry] = []
        self._load_index()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def entries(self) -> list[Entry]:
        return list(self._entries)

    def categories(self) -> list[str]:
        cats = sorted({e.category for e in self._entries})
        return cats if cats else ["General"]

    def add_entry(self, entry: Entry, secret: str) -> None:
        self._entries.append(entry)
        self._save_index()
        self._save_secret(entry.id, secret)

    def update_entry(self, entry: Entry, secret: Optional[str] = None) -> None:
        for i, e in enumerate(self._entries):
            if e.id == entry.id:
                self._entries[i] = entry
                break
        self._save_index()
        if secret is not None:
            self._save_secret(entry.id, secret)

    def delete_entry(self, entry_id: str) -> None:
        self._entries = [e for e in self._entries if e.id != entry_id]
        self._save_index()
        try:
            keyring.delete_password(_SERVICE, entry_id)
        except keyring.errors.PasswordDeleteError:
            pass

    def get_secret(self, entry_id: str) -> str:
        return keyring.get_password(_SERVICE, entry_id) or ""

    def rename_category(self, old_name: str, new_name: str) -> None:
        for entry in self._entries:
            if entry.category == old_name:
                entry.category = new_name
        self._save_index()

    def delete_category(self, name: str, move_to: str = "General") -> None:
        for entry in self._entries:
            if entry.category == name:
                entry.category = move_to
        self._save_index()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_index(self) -> None:
        raw = keyring.get_password(_SERVICE, _INDEX_KEY)
        if not raw:
            self._entries = []
            return
        try:
            data = json.loads(raw)
            before = [d.get("category", "") + str(d.get("tags", [])) for d in data]
            self._entries = [Entry.from_dict(d) for d in data]
            after = [e.category + str(e.tags) for e in self._entries]
            if before != after:
                self._save_index()  # persist migration
        except Exception:
            logger.exception("Failed to parse vault index — starting fresh.")
            self._entries = []

    def _save_index(self) -> None:
        payload = json.dumps([e.to_dict() for e in self._entries])
        keyring.set_password(_SERVICE, _INDEX_KEY, payload)

    def _save_secret(self, entry_id: str, secret: str) -> None:
        keyring.set_password(_SERVICE, entry_id, secret)
