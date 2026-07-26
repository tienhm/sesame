"""Floating bubble — a small always-on-top draggable button.

Click  → toggle the VaultPanel open/closed
Drag   → reposition the bubble anywhere on screen
Position is persisted in cache.json between sessions.
"""

from __future__ import annotations

import math
import random as _random

from PySide6.QtCore import (
    QEvent,
    QPoint,
    QPropertyAnimation,
    QRect,
    Qt,
    QEasingCurve,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QCursor, QFont, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QPushButton,
    QWidget,
)

from app.config import AppConfig


class _CurvedText(QWidget):
    """Transparent overlay that paints text curved along the bubble's
    circular edge — each character rotated to follow the arc's tangent."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._text = ""

    def set_text(self, text: str) -> None:
        if text != self._text:
            self._text = text
            self.update()

    def paintEvent(self, event) -> None:
        if not self._text:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        font = QFont("Segoe UI", 7, QFont.Weight.ExtraBold)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#ffffff"))
        metrics = painter.fontMetrics()

        cx = self.width() / 2
        cy = self.height() / 2
        radius = min(cx, cy) - 7   # nested closer to the bubble's center

        widths = [metrics.horizontalAdvance(ch) for ch in self._text]
        angles = [w / radius for w in widths]   # arc length -> radians
        total_angle = sum(angles)
        current_angle = -total_angle / 2

        for ch, w, ang in zip(self._text, widths, angles):
            theta = -math.pi / 2 + current_angle + ang / 2   # top-centered
            x = cx + radius * math.cos(theta)
            y = cy + radius * math.sin(theta)
            painter.save()
            painter.translate(x, y)
            painter.rotate(math.degrees(theta) + 90)
            from PySide6.QtCore import QRectF
            painter.drawText(
                QRectF(-w / 2, -metrics.height() / 2, w, metrics.height()),
                Qt.AlignmentFlag.AlignCenter,
                ch,
            )
            painter.restore()
            current_angle += ang


class Bubble(QWidget):
    """Frameless, always-on-top circular button."""

    movement_click = Signal()   # emitted when bubble clicked during movement reminder

    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self._bubble_size = int(self._config.get("bubble_size", 48))
        self._drag_threshold = int(self._config.get("bubble_drag_threshold", 5))
        self._drag_press_pos: QPoint | None = None   # global cursor pos at press
        self._drag_offset: QPoint | None = None       # cursor offset within window
        self._drag_active = False
        self._panel: QWidget | None = None  # set by main after panel is created
        self._movement_reminder = None      # set via set_movement_reminder()
        self._clipboard_active = False      # True while a password countdown is showing

        self._setup_window()
        self._setup_button()
        self._setup_movement_overlay()
        self._restore_position()
        self.apply_opacity()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def show_countdown(self, seconds: int) -> None:
        """Show countdown on bubble when panel is hidden."""
        self._clipboard_active = True
        self._movement_overlay.set_text("")   # avoid clutter with the password countdown
        self._btn.setText(f"{seconds}s")
        self._btn.setStyleSheet(
            "QPushButton { background-color: #2d6a4f; border-radius: 24px; "
            "border: 2px solid #1a4a35; font-size: 13px; color: #d8f3dc; "
            "font-family: 'Segoe UI'; font-weight: 600; }"
        )

    def clear_countdown(self) -> None:
        """Restore bubble to normal icon."""
        from app.utils.icons import FA
        self._clipboard_active = False
        self._btn.setText(FA.KEY)
        self._btn.setStyleSheet("")

    def apply_opacity(self) -> None:
        opacity = float(self._config.get("bubble_opacity", 1.0))
        self.setWindowOpacity(max(0.2, min(1.0, opacity)))

    def flash_and_center(self) -> None:
        """Move to screen center and blink for 3 seconds.
        Ensures bubble is visible and panel is hidden before flashing.
        """
        # Hide panel if open
        if self._panel and self._panel.isVisible():
            self._panel.hide()

        screen = QApplication.primaryScreen().availableGeometry()
        bubble_size = int(self._config.get("bubble_size", 48))
        self.move(
            (screen.width() - bubble_size) // 2,
            (screen.height() - bubble_size) // 2,
        )
        self.show()
        self._save_position()
        self.apply_opacity()

        self._blink_count = 0
        flash_interval = int(self._config.get("bubble_locate_flash_interval_ms", 250))
        if not hasattr(self, "_blink_timer"):
            self._blink_timer = QTimer(self)
            self._blink_timer.timeout.connect(self._do_blink)
        self._blink_timer.setInterval(flash_interval)
        self._blink_timer.start()

    def _do_blink(self) -> None:
        self._blink_count += 1
        flash_count = int(self._config.get("bubble_locate_flash_count", 12))
        if self._blink_count > flash_count:
            self._blink_timer.stop()
            self._blink_count = 0
            self._btn.setStyleSheet("")
            return
        if self._blink_count % 2 == 1:
            self._btn.setStyleSheet(
                "QPushButton { background-color: #ff8800; border-radius: 24px; "
                "border: 2px solid #ff6600; font-family: 'Font Awesome 6 Free Solid'; }"
            )
        else:
            self._btn.setStyleSheet("")

    def set_movement_reminder(self, reminder) -> None:
        self._movement_reminder = reminder
        self._movement_timer.start()
        self._update_movement_text()

    def start_waiting_blink(self) -> None:
        """Continuous gentle blink until user clicks — movement reminder."""
        wait_interval = int(self._config.get("bubble_wait_blink_interval_ms", 800))
        self._movement_overlay.set_text("")
        if not hasattr(self, "_wait_blink_timer"):
            self._wait_blink_timer = QTimer(self)
            self._wait_blink_timer.timeout.connect(self._do_wait_blink)
        self._wait_blink_timer.setInterval(wait_interval)
        self._wait_blink_phase = 0
        self._wait_blink_timer.start()
        # After roam delay of no user action, start roaming
        self._start_roam_delay()

    def stop_waiting_blink(self) -> None:
        """Stop continuous blink, roaming, and restore normal button style."""
        if hasattr(self, "_wait_blink_timer"):
            self._wait_blink_timer.stop()
        self._stop_roaming()
        self._btn.setStyleSheet("")

    def _do_wait_blink(self) -> None:
        self._wait_blink_phase ^= 1
        if self._wait_blink_phase:
            self._btn.setStyleSheet(
                "QPushButton { background-color: #ff8800; border-radius: 24px; "
                "border: 3px solid #ff6600; font-family: 'Font Awesome 6 Free Solid'; }"
            )
        else:
            self._btn.setStyleSheet("")

    # ------------------------------------------------------------------
    # Roaming — move bubble around to grab attention
    # ------------------------------------------------------------------

    def _start_roam_delay(self) -> None:
        """Start a one-shot timer; if user doesn't act within roam delay, begin roaming."""
        if not hasattr(self, "_roam_delay_timer"):
            self._roam_delay_timer = QTimer(self)
            self._roam_delay_timer.setSingleShot(True)
            self._roam_delay_timer.timeout.connect(self._begin_roaming)
        delay = int(self._config.get("roam_delay_ms", 3_000))
        self._roam_delay_timer.start(delay)

    def _begin_roaming(self) -> None:
        """Start periodic roaming moves."""
        screens = QApplication.screens()
        self._roam_screen_index = 0
        self._roam_screen_count = len(screens)
        interval = int(self._config.get("roam_interval_ms", 5_000))
        # Do the first move immediately, then repeat every interval ms
        self._roam_move()
        if not hasattr(self, "_roam_timer"):
            self._roam_timer = QTimer(self)
            self._roam_timer.timeout.connect(self._roam_move)
        self._roam_timer.setInterval(interval)
        self._roam_timer.start()

    def _stop_roaming(self) -> None:
        """Stop all roaming timers and restore saved position."""
        if hasattr(self, "_roam_delay_timer"):
            self._roam_delay_timer.stop()
        if hasattr(self, "_roam_timer"):
            self._roam_timer.stop()
        # Restore bubble to its saved position
        self._restore_position()

    def _roam_move(self) -> None:
        """Move the bubble to the next roaming position.

        Single screen  → random position within the available area.
        Multiple screens → cycle through the centre of each screen.
        """
        screens = QApplication.screens()
        if len(screens) <= 1:
            # Single screen: random position
            geo = QApplication.primaryScreen().availableGeometry()
            margin = self._bubble_size + 20
            x = _random.randint(geo.left() + margin, max(geo.left() + margin, geo.right() - margin))
            y = _random.randint(geo.top() + margin, max(geo.top() + margin, geo.bottom() - margin))
            self.move(x, y)
        else:
            # Multiple screens: cycle through screen centres
            idx = self._roam_screen_index % len(screens)
            geo = screens[idx].availableGeometry()
            cx = geo.left() + (geo.width() - self._bubble_size) // 2
            cy = geo.top() + (geo.height() - self._bubble_size) // 2
            self.move(cx, cy)
            self._roam_screen_index = idx + 1

    def set_panel(self, panel: QWidget) -> None:
        self._panel = panel

    def toggle_panel(self) -> None:
        # Movement reminder takes priority — show confirm dialog instead of panel
        if self._movement_reminder and self._movement_reminder.waiting:
            self.movement_click.emit()
            return
        if self._panel is None:
            return
        if self._panel.isVisible():
            self._panel.hide()
            self.show()
        else:
            self.clear_countdown()   # restore key icon before hiding
            self._reposition_panel()
            self._panel.show()
            self._panel.raise_()
            self._panel.activateWindow()
            self.hide()

    # ------------------------------------------------------------------
    # Window setup
    # ------------------------------------------------------------------

    def _setup_window(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # keeps it out of taskbar
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(self._bubble_size, self._bubble_size)

    def _setup_button(self) -> None:
        from app.utils.icons import FA
        self._btn = QPushButton(FA.KEY, self)
        self._btn.setObjectName("BubbleButton")
        self._btn.setFixedSize(self._bubble_size, self._bubble_size)
        self._btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn.clicked.connect(self.toggle_panel)
        self._btn.setToolTip("Sesame — click to open vault")
        self._btn.installEventFilter(self)

    def _setup_movement_overlay(self) -> None:
        """Transparent overlay drawing 'm:ss' curved along the bubble's top
        arc — live countdown to the next movement reminder."""
        self._movement_overlay = _CurvedText(self)
        self._movement_overlay.setFixedSize(self._bubble_size, self._bubble_size)
        self._movement_overlay.move(0, 0)
        self._movement_overlay.raise_()

        self._movement_timer = QTimer(self)
        text_interval = int(self._config.get("bubble_movement_text_interval_ms", 1_000))
        self._movement_timer.setInterval(text_interval)
        self._movement_timer.timeout.connect(self._update_movement_text)

    def _update_movement_text(self) -> None:
        reminder = self._movement_reminder
        if self._clipboard_active:
            self._movement_overlay.set_text("")
            self.update()
            return
        if reminder is None or not reminder.enabled or reminder.waiting:
            self._movement_overlay.set_text("")
            self.update()
            return
        remaining = reminder.remaining_seconds()
        if remaining <= 0:
            self._movement_overlay.set_text("")
            self.update()
            return
        minutes, seconds = divmod(remaining, 60)
        self._movement_overlay.set_text(f"{minutes}:{seconds:02d}")
        self._movement_overlay.raise_()
        self.update()

    # ------------------------------------------------------------------
    # Position persistence
    # ------------------------------------------------------------------

    def _restore_position(self) -> None:
        screen = QApplication.primaryScreen().availableGeometry()
        saved = self._config.cache.get("bubble_pos")
        if saved:
            x = max(0, min(saved["x"], screen.width() - self._bubble_size))
            y = max(0, min(saved["y"], screen.height() - self._bubble_size))
            self.move(x, y)
        else:
            # Default: bottom-right corner with a small margin
            self.move(
                screen.width() - self._bubble_size - 20,
                screen.height() - self._bubble_size - 60,
            )

    def _save_position(self) -> None:
        self._config.cache.set("bubble_pos", {"x": self.x(), "y": self.y()})

    def _reposition_panel(self) -> None:
        """Position the panel so the ⊙ restore button aligns with the bubble center."""
        if self._panel is None:
            return
        screen: QRect = QApplication.primaryScreen().availableGeometry()
        panel_w = self._panel.width()
        panel_h = self._panel.height()
        bubble_cx = self.x() + self._bubble_size // 2
        bubble_cy = self.y() + self._bubble_size // 2

        # Try to align ⊙ center with bubble center
        restore_btn = getattr(self._panel, '_restore_btn', None)
        if restore_btn:
            btn_local = restore_btn.mapTo(self._panel, restore_btn.rect().center())
            if btn_local.x() > 0 or btn_local.y() > 0:
                px = bubble_cx - btn_local.x()
                py = bubble_cy - btn_local.y()
                if (screen.left() <= px
                        and px + panel_w <= screen.right()
                        and screen.top() <= py
                        and py + panel_h <= screen.bottom()):
                    self._panel.move(px, py)
                    return

        # Fallback: open to the left of the bubble, clamp to screen
        bx, by = self.x(), self.y()
        px = bx - panel_w - 8
        py = by
        if px < screen.left():
            px = bx + self._bubble_size + 8
        if py + panel_h > screen.bottom():
            py = screen.bottom() - panel_h
        self._panel.move(px, py)

    # ------------------------------------------------------------------
    # Drag support — event filter on _btn (button covers full widget area)
    # ------------------------------------------------------------------

    def eventFilter(self, obj, event) -> bool:
        if obj is not self._btn:
            return super().eventFilter(obj, event)

        t = event.type()

        if t == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            self._drag_press_pos = event.globalPosition().toPoint()
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._drag_active = False
            return False  # let button track the press normally

        if t == QEvent.Type.MouseMove and event.buttons() & Qt.MouseButton.LeftButton:
            if self._drag_press_pos is not None:
                moved = (event.globalPosition().toPoint() - self._drag_press_pos).manhattanLength()
                if moved > self._drag_threshold:
                    self._drag_active = True
                if self._drag_active:
                    self.move(event.globalPosition().toPoint() - self._drag_offset)
                    self._btn.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
                    if self._panel and self._panel.isVisible():
                        self._reposition_panel()
                    return True  # consume — suppress button hover effects

        if t == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
            if self._drag_active:
                self._drag_active = False
                self._drag_press_pos = None
                self._save_position()
                self._btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                return True  # swallow release so clicked signal doesn't fire
            self._drag_press_pos = None

        return False

    # ------------------------------------------------------------------
    # Close: persist position
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        self._save_position()
        super().closeEvent(event)
