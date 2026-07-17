"""Floating bubble — a small always-on-top draggable button.

Click  → toggle the VaultPanel open/closed
Drag   → reposition the bubble anywhere on screen
Position is persisted in config.json between sessions.
"""

from __future__ import annotations

from PySide6.QtCore import (
    QEvent,
    QPoint,
    QPropertyAnimation,
    QRect,
    Qt,
    QEasingCurve,
    QTimer,
)
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QApplication,
    QPushButton,
    QWidget,
)

from app.config import AppConfig

_BUBBLE_SIZE = 48       # px — diameter
_DRAG_THRESHOLD = 5    # px manhattan distance before treating move as drag


class Bubble(QWidget):
    """Frameless, always-on-top circular button."""

    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self._drag_press_pos: QPoint | None = None   # global cursor pos at press
        self._drag_offset: QPoint | None = None       # cursor offset within window
        self._drag_active = False
        self._panel: QWidget | None = None  # set by main after panel is created

        self._setup_window()
        self._setup_button()
        self._restore_position()
        self.apply_opacity()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def show_countdown(self, seconds: int) -> None:
        """Show countdown on bubble when panel is hidden."""
        self._btn.setText(f"{seconds}s")
        self._btn.setStyleSheet(
            "QPushButton { background-color: #2d6a4f; border-radius: 24px; "
            "border: 2px solid #1a4a35; font-size: 13px; color: #d8f3dc; "
            "font-family: 'Segoe UI'; font-weight: 600; }"
        )

    def clear_countdown(self) -> None:
        """Restore bubble to normal icon."""
        from app.utils.icons import FA
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
        self.move(
            (screen.width() - _BUBBLE_SIZE) // 2,
            (screen.height() - _BUBBLE_SIZE) // 2,
        )
        self.show()
        self._save_position()
        self.apply_opacity()

        self._blink_count = 0
        if not hasattr(self, "_blink_timer"):
            self._blink_timer = QTimer(self)
            self._blink_timer.setInterval(250)
            self._blink_timer.timeout.connect(self._do_blink)
        self._blink_timer.start()

    def _do_blink(self) -> None:
        self._blink_count += 1
        if self._blink_count > 12:
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

    def set_panel(self, panel: QWidget) -> None:
        self._panel = panel

    def toggle_panel(self) -> None:
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
        self.setFixedSize(_BUBBLE_SIZE, _BUBBLE_SIZE)

    def _setup_button(self) -> None:
        from app.utils.icons import FA
        self._btn = QPushButton(FA.KEY, self)
        self._btn.setObjectName("BubbleButton")
        self._btn.setFixedSize(_BUBBLE_SIZE, _BUBBLE_SIZE)
        self._btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn.clicked.connect(self.toggle_panel)
        self._btn.setToolTip("Sesame — click to open vault")
        self._btn.installEventFilter(self)

    # ------------------------------------------------------------------
    # Position persistence
    # ------------------------------------------------------------------

    def _restore_position(self) -> None:
        screen = QApplication.primaryScreen().availableGeometry()
        saved = self._config.get("bubble_pos")
        if saved:
            x = max(0, min(saved["x"], screen.width() - _BUBBLE_SIZE))
            y = max(0, min(saved["y"], screen.height() - _BUBBLE_SIZE))
            self.move(x, y)
        else:
            # Default: bottom-right corner with a small margin
            self.move(
                screen.width() - _BUBBLE_SIZE - 20,
                screen.height() - _BUBBLE_SIZE - 60,
            )

    def _save_position(self) -> None:
        self._config.set("bubble_pos", {"x": self.x(), "y": self.y()})

    def _reposition_panel(self) -> None:
        """Position the panel so the ⊙ restore button aligns with the bubble center."""
        if self._panel is None:
            return
        screen: QRect = QApplication.primaryScreen().availableGeometry()
        panel_w = self._panel.width()
        panel_h = self._panel.height()
        bubble_cx = self.x() + _BUBBLE_SIZE // 2
        bubble_cy = self.y() + _BUBBLE_SIZE // 2

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
            px = bx + _BUBBLE_SIZE + 8
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
                if moved > _DRAG_THRESHOLD:
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
