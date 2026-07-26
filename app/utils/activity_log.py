"""Persistent activity log — screen-on timestamps and daily 'moved' confirm counts.

Stored at %APPDATA%\\Sesame\\activity_log.json, separate from config.json.
Screen-on events that immediately follow a hibernate/sleep resume are NOT
logged here (that case is filtered out by the caller) — only genuine
unlock/screen-on events matter for this log.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _log_path() -> Path:
    appdata = os.environ.get("APPDATA") or Path.home()
    directory = Path(appdata) / "Sesame"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "activity_log.json"


class ActivityLogger:
    """Tracks screen-on events and per-day movement-confirm counts."""

    def __init__(self) -> None:
        self._path = _log_path()
        self._data: dict[str, Any] = {"screen_on_events": [], "move_confirms": {}}
        self._load()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def log_screen_on(self) -> None:
        """Record a timestamp for a genuine screen-on / unlock event."""
        self._data.setdefault("screen_on_events", []).append(
            datetime.now().isoformat(timespec="seconds")
        )
        self._save()

    def log_move_confirmed(self) -> None:
        """Increment today's movement-confirmed counter."""
        today = date.today().isoformat()
        counts = self._data.setdefault("move_confirms", {})
        counts[today] = counts.get(today, 0) + 1
        self._save()

    def screen_on_events(self) -> list[str]:
        return list(self._data.get("screen_on_events", []))

    def move_confirms(self) -> dict[str, int]:
        return dict(self._data.get("move_confirms", {}))

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        try:
            if self._path.exists():
                self._data = json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            logger.exception("Failed to load activity log — starting fresh.")

    def _save(self) -> None:
        try:
            self._path.write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            logger.exception("Failed to save activity log.")
