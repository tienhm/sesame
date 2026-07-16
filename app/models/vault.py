"""Vault — persists entries and secrets.

Layout:
  Entry metadata (vault_index) → %APPDATA%\\Sesame\\vault_index.json   (plain JSON, no secrets)
  Each secret                  → Windows Credential Manager, service "Sesame", username "<entry.id>"

The vault_index is stored in a file rather than Credential Manager to avoid
the 2 560-byte per-credential limit which causes silent save failures when
the number of entries grows beyond ~10.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

import keyring

from app.models.entry import Entry

logger = logging.getLogger(__name__)

_SERVICE   = "Sesame"
_INDEX_KEY = "vault_index"   # legacy Credential Manager key (migration only)


def _index_path() -> Path:
    appdata = os.environ.get("APPDATA") or Path.home()
    directory = Path(appdata) / "Sesame"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "sesame_vault.json"


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

    def reorder_entries(self, ordered_ids: list[str]) -> None:
        """Persist a new display order for entries (drag-drop result)."""
        id_map = {e.id: e for e in self._entries}
        reordered = [id_map[i] for i in ordered_ids if i in id_map]
        # Append any entries not in ordered_ids (safety net)
        seen = set(ordered_ids)
        reordered += [e for e in self._entries if e.id not in seen]
        self._entries = reordered
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
        path = _index_path()
        if path.exists():
            self._load_from_file(path)
        else:
            self._migrate_from_credential_manager()

    def _load_from_file(self, path: Path) -> None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            before = [d.get("category", "") + str(d.get("tags", [])) for d in data]
            self._entries = [Entry.from_dict(d) for d in data]
            after = [e.category + str(e.tags) for e in self._entries]
            if before != after:
                self._save_index()   # persist any migration fixes
        except Exception:
            logger.exception("Failed to parse vault_index.json — starting fresh.")
            self._entries = []

    def _migrate_from_credential_manager(self) -> None:
        """One-time migration: move vault_index from Credential Manager to file."""
        raw = keyring.get_password(_SERVICE, _INDEX_KEY)
        if not raw:
            self._entries = []
            return
        try:
            data = json.loads(raw)
            self._entries = [Entry.from_dict(d) for d in data]
            self._save_index()   # write to file
            # Remove the old Credential Manager entry
            try:
                keyring.delete_password(_SERVICE, _INDEX_KEY)
            except Exception:
                pass
            logger.info("Migrated vault_index from Credential Manager to file.")
        except Exception:
            logger.exception("Migration failed — starting fresh.")
            self._entries = []

    def _save_index(self) -> None:
        path = _index_path()
        try:
            path.write_text(
                json.dumps([e.to_dict() for e in self._entries],
                           ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            logger.exception("Failed to save vault_index.json.")

    def _save_secret(self, entry_id: str, secret: str) -> None:
        keyring.set_password(_SERVICE, entry_id, secret)
