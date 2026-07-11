"""AppConfig — lightweight JSON config stored in %APPDATA%\\Sesame\\config.json.

Used for non-sensitive preferences (bubble position, window size, settings).
Secrets are never stored here — they live in Windows Credential Manager.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _config_path() -> Path:
    appdata = os.environ.get("APPDATA") or Path.home()
    directory = Path(appdata) / "Sesame"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "config.json"


class AppConfig:
    def __init__(self) -> None:
        self._path = _config_path()
        self._data: dict = {}
        self._load()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self._save()

    def setdefault(self, key: str, value: Any) -> Any:
        if key not in self._data:
            self.set(key, value)
        return self._data[key]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        try:
            if self._path.exists():
                self._data = json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            logger.exception("Failed to load config — using defaults.")
            self._data = {}

    def _save(self) -> None:
        try:
            self._path.write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            logger.exception("Failed to save config.")
