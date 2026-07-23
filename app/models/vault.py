"""Vault — persists entries and secrets.

Layout:
  Entry metadata  → %APPDATA%\\Sesame\\sesame_vault.json  (plain JSON, no secrets)
  Secrets + OTP   → Windows Credential Manager, TargetName "SZM:<entry.id>",
                     CredentialBlob = {"p": "<password>", "o": "<otp_secret>"}
                     (see app.utils.credential_store)

entry.id is a short, reused-gap integer (as str) assigned by Vault.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

from app.models.entry import Entry
from app.utils import credential_store

logger = logging.getLogger(__name__)


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
        entry.id = self._next_id()
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
        credential_store.delete_secret(entry_id)

    def get_secret(self, entry_id: str) -> str:
        return credential_store.get_secret(entry_id)

    def get_otp_secret(self, entry_id: str) -> str:
        return credential_store.get_otp_secret(entry_id)

    def set_otp_secret(self, entry_id: str, secret: str) -> None:
        credential_store.set_otp_secret(entry_id, secret)
        for e in self._entries:
            if e.id == entry_id:
                e.has_otp = bool(secret)
                break
        self._save_index()

    def _next_id(self) -> str:
        used = set()
        for e in self._entries:
            try:
                used.add(int(e.id))
            except (TypeError, ValueError):
                pass
        i = 0
        while i in used:
            i += 1
        return str(i)

    def rename_category(self, old_name: str, new_name: str) -> None:
        for entry in self._entries:
            if entry.category == old_name:
                entry.category = new_name
        self._save_index()

    def reorder_entries(self, ordered_ids: list[str]) -> None:
        id_map = {e.id: e for e in self._entries}
        reordered = [id_map[i] for i in ordered_ids if i in id_map]
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
            self._entries = []

    def _load_from_file(self, path: Path) -> None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            logger.exception("Failed to read sesame_vault.json — starting fresh.")
            self._entries = []
            return
        # Parse entries individually so one bad record doesn't wipe the vault
        entries, changed = [], False
        for d in data:
            try:
                before_cat  = d.get("category", "") + str(d.get("tags", []))
                entry = Entry.from_dict(d)
                if entry.category + str(entry.tags) != before_cat:
                    changed = True
                entries.append(entry)
            except Exception:
                logger.warning("Skipping malformed entry id=%s: %s",
                               d.get("id", "?"), d.get("name", "?"))
        self._entries = entries
        if changed:
            self._save_index()
        # v1.2→v1.3: move otp_secret from JSON field to Credential Manager
        self._migrate_otp_secrets_to_cred_manager()

    def _migrate_otp_secrets_to_cred_manager(self) -> None:
        """One-time: move otp_secret values stored in JSON → Credential Manager blob."""
        path = _index_path()
        try:
            raw_data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return
        changed = False
        for d, entry in zip(raw_data, self._entries):
            otp_in_json = d.get("otp_secret", "")
            if otp_in_json:
                credential_store.set_otp_secret(entry.id, otp_in_json)
                entry.has_otp = True
                changed = True
        if changed:
            self._save_index()
            logger.info("Migrated OTP secrets from JSON to Credential Manager.")

    def _save_secret(self, entry_id: str, secret: str) -> None:
        credential_store.set_secret(entry_id, secret)

    def _save_index(self) -> None:
        path = _index_path()
        try:
            path.write_text(
                json.dumps([e.to_dict() for e in self._entries],
                           ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            logger.exception("Failed to save sesame_vault.json.")
