"""System tray icon and context menu."""

from __future__ import annotations

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QWidget



class TrayIcon(QSystemTrayIcon):
    def __init__(self, icon: QIcon, app_controller, parent: QWidget | None = None) -> None:
        super().__init__(icon, parent)
        self._ctrl = app_controller  # reference to SesameApp
        self._build_menu()
        self.activated.connect(self._on_activated)

    # ------------------------------------------------------------------

    def _build_menu(self) -> None:
        menu = QMenu()
        menu.aboutToShow.connect(self._update_show_action)

        self._show_action = QAction("Show Bubble", menu)
        self._show_action.triggered.connect(self._ctrl.toggle_bubble)
        menu.addAction(self._show_action)

        self._locate_action = QAction("Locate Sesame", menu)
        self._locate_action.triggered.connect(self._ctrl.locate_bubble)
        menu.addAction(self._locate_action)

        menu.addSeparator()

        self._support_action = QAction("❤  Support Sesame", menu)
        self._support_action.triggered.connect(self._ctrl.open_donate)
        menu.addAction(self._support_action)

        menu.addSeparator()

        quit_action = QAction("Exit Sesame", menu)
        quit_action.triggered.connect(self._ctrl.quit_app)
        menu.addAction(quit_action)

        self.setContextMenu(menu)

    # ------------------------------------------------------------------

    def _update_show_action(self) -> None:
        bubble = getattr(self._ctrl, '_bubble', None)
        panel  = getattr(self._ctrl, '_panel',  None)
        panel_visible = panel is not None and panel.isVisible()
        if bubble is not None and bubble.isVisible():
            self._show_action.setText("Hide Bubble")
        else:
            self._show_action.setText("Show Bubble")
        self._show_action.setEnabled(not panel_visible)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._ctrl.toggle_bubble()
