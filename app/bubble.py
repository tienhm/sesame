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

    def apply_opacity(self) -> None:
        opacity = float(self._config.get("bubble_opacity") or 1.0)
        self.setWindowOpacity(max(0.2, min(1.0, opacity)))

    def set_panel(self, panel: QWidget) -> None:
        self._panel = panel

    def toggle_panel(self) -> None:
        if self._panel is None:
            return
        if self._panel.isVisible():
            self._panel.hide()
            self.show()
        else:
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
        self._btn = QPushButton("🔑", self)
        self._btn.setObjectName("BubbleButton")
        self._btn.setFixedSize(_BUBBLE_SIZE, _BUBBLE_SIZE)
        self._btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn.clicked.connect(self.toggle_panel)
        self._btn.setToolTip("Open Sesame — click to open vault")
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
        """Position the panel so it opens near the bubble, staying on screen."""
        if self._panel is None:
            return
        screen: QRect = QApplication.primaryScreen().availableGeometry()
        panel_w = self._panel.width()
        panel_h = self._panel.height()

        # Prefer opening to the left of the bubble
        bx, by = self.x(), self.y()
        px = bx - panel_w - 8
        py = by

        # Clamp to screen
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
