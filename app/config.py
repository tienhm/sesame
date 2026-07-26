"""AppConfig — lightweight JSON config stored in %APPDATA%\\Sesame\\config.json.

Used for non-sensitive preferences and settings.
Transient UI coordinates (e.g. bubble position, background crop offset) live
in cache.json. Secrets are never stored here — they live in Windows Credential
Manager.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Protected defaults — these keys are read-only from config.json.
# The app only reads them (one-way JSON → app). They are never written
# back by the app; users can override them by editing config.json manually.
_PROTECTED_CONFIG = {
    # Bubble
    "bubble_size": 48,
    "bubble_drag_threshold": 5,
    "bubble_locate_flash_interval_ms": 250,
    "bubble_locate_flash_count": 12,
    "bubble_wait_blink_interval_ms": 800,
    "bubble_movement_text_interval_ms": 1_000,

    # Vault panel
    "panel_width": 480,
    "panel_height": 430,
    "panel_caption_height": 34,

    # Movement badge inside panel
    "movement_badge_width": 60,
    "movement_badge_height": 24,
    "movement_badge_timer_interval_ms": 1_000,
    "movement_badge_blink_interval_ms": 800,

    # OTP refresh timer
    "otp_refresh_interval_ms": 1_000,

    # Clipboard auto-clear
    "clipboard_clear_after_ms": 30_000,
    "clipboard_countdown_interval_ms": 1_000,

    # Movement reminder
    "movement_reminder_default_minutes": 20,
    "movement_reminder_snooze_minutes": 5,

    # Roaming bubble
    "roam_delay_ms": 3_000,
    "roam_interval_ms": 5_000,

    # Auto-login keystroke delay
    "auto_login_inter_key_delay_s": 0.012,
}


def _config_path() -> Path:
    appdata = os.environ.get("APPDATA") or Path.home()
    directory = Path(appdata) / "Sesame"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "config.json"


def _cache_path() -> Path:
    appdata = os.environ.get("APPDATA") or Path.home()
    directory = Path(appdata) / "Sesame"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "cache.json"


class Cache:
    """Transient UI state stored in %APPDATA%\\Sesame\\cache.json.

    Unlike config.json, this file is rewritten automatically whenever
    runtime state (e.g. bubble position) changes. It is safe to update
    frequently because it only contains auto-generated UI state.
    """

    def __init__(self) -> None:
        self._path = _cache_path()
        self._data: dict = {}
        self._load()

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self._save()

    def setdefault(self, key: str, value: Any) -> Any:
        if key not in self._data:
            self.set(key, value)
        return self._data[key]

    def _load(self) -> None:
        try:
            if self._path.exists():
                self._data = json.loads(self._path.read_text(encoding="utf-8"))
            else:
                self._data = {}
        except Exception:
            logger.exception("Failed to load cache — starting fresh.")
            self._data = {}

    def _save(self) -> None:
        try:
            self._path.write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            logger.exception("Failed to save cache.")


class AppConfig:
    def __init__(self) -> None:
        self._path = _config_path()
        self._data: dict = {}
        self._dirty: set[str] = set()
        self._load()
        self.cache = Cache()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        if key in self._data:
            return self._data[key]
        if key in _PROTECTED_CONFIG:
            return _PROTECTED_CONFIG[key]
        return default

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self._dirty.add(key)
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
            else:
                self._data = {}
        except Exception:
            logger.exception("Failed to load config — starting fresh.")
            self._data = {}
        self._dirty = set()

    def _save(self) -> None:
        """Persist only settings-configurable keys that changed this session.

        Protected/read-only parameters (bubble sizes, intervals, protected
        defaults) are never written by the app — they are read one-way from
        config.json, falling back to the built-in defaults when missing.
        """
        if not self._dirty:
            return
        try:
            stored: dict[str, Any] = {}
            if self._path.exists():
                try:
                    stored = json.loads(self._path.read_text(encoding="utf-8"))
                except Exception:
                    logger.exception("Failed to read existing config for merge.")
            # Write only settings-configurable keys that changed.
            # Protected keys remain read-only from the JSON file.
            for key in self._dirty:
                if key not in _PROTECTED_CONFIG:
                    stored[key] = self._data[key]
            self._path.write_text(
                json.dumps(stored, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            self._data = stored
            self._dirty.clear()
        except Exception:
            logger.exception("Failed to save config.")
