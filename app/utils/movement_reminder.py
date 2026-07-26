"""Periodic movement reminder — fires a signal after a configurable idle interval.

States:
  idle    → timer running, waiting for interval to elapse
  waiting → interval elapsed, bubble is blinking; waiting for user to click
  paused  → system suspended (hibernate); timer stopped
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal

from app.config import AppConfig


class MovementReminder(QObject):
    """Emits reminder_triggered when it's time to move.

    After the signal fires the caller is expected to start the bubble blink.
    The reminder enters "waiting" state until reset() or snooze() is called.
    """

    reminder_triggered = Signal()

    def __init__(self, config: AppConfig, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._config   = config
        self._enabled  = bool(config.get("movement_reminder_enabled", True))
        default_minutes = int(config.get("movement_reminder_default_minutes", 20))
        self._minutes  = int(config.get("movement_reminder_interval_minutes",
                                        default_minutes))
        self._waiting  = False

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timer)

        if self._enabled:
            self._timer.start(self._ms())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def waiting(self) -> bool:
        """True while the bubble is blinking, waiting for the user to click."""
        return self._waiting

    @property
    def enabled(self) -> bool:
        return self._enabled

    def remaining_seconds(self) -> int:
        """Seconds left until the reminder fires; 0 if disabled/waiting/stopped."""
        if not self._enabled or self._waiting or not self._timer.isActive():
            return 0
        return max(0, self._timer.remainingTime() // 1000)

    def reset(self) -> None:
        """Restart countdown from zero (called after user confirms movement)."""
        self._waiting = False
        if self._enabled:
            self._timer.start(self._ms())

    def snooze(self) -> None:
        """Postpone reminder by snooze minutes (user not ready yet)."""
        self._waiting = False
        if self._enabled:
            snooze_minutes = int(self._config.get("movement_reminder_snooze_minutes", 5))
            self._timer.start(snooze_minutes * 60 * 1000)

    def pause(self) -> None:
        """Suspend timer on system hibernate."""
        self._timer.stop()
        self._waiting = False

    def resume(self) -> None:
        """Resume after hibernate — reset to full interval (user wasn't moving)."""
        self.reset()

    def stop(self) -> None:
        """Fully disable the reminder."""
        self._timer.stop()
        self._waiting = False
        self._enabled = False

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        self._config.set("movement_reminder_enabled", enabled)
        if enabled:
            self._waiting = False
            self._timer.start(self._ms())
        else:
            self._timer.stop()
            self._waiting = False

    def set_interval(self, minutes: int) -> None:
        self._minutes = minutes
        self._config.set("movement_reminder_interval_minutes", minutes)
        if self._enabled and not self._waiting:
            self._timer.start(self._ms())

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _ms(self) -> int:
        return self._minutes * 60 * 1000

    def _on_timer(self) -> None:
        if not self._enabled:
            return
        self._waiting = True
        self.reminder_triggered.emit()
