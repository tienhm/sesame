"""System tray icon and context menu."""

from __future__ import annotations

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QWidget

from app.utils.startup import disable_startup, enable_startup, is_startup_enabled


class TrayIcon(QSystemTrayIcon):
    def __init__(self, icon: QIcon, app_controller, parent: QWidget | None = None) -> None:
        super().__init__(icon, parent)
        self._ctrl = app_controller  # reference to SesameApp
        self._build_menu()
        self.activated.connect(self._on_activated)

    # ------------------------------------------------------------------

    def _build_menu(self) -> None:
        menu = QMenu()

        self._show_action = QAction("Show / Hide Bubble", menu)
        self._show_action.triggered.connect(self._ctrl.toggle_bubble)
        menu.addAction(self._show_action)

        menu.addSeparator()

        self._add_action = QAction("Add New Entry…", menu)
        self._add_action.triggered.connect(self._ctrl.open_add_entry)
        menu.addAction(self._add_action)

        self._settings_action = QAction("Settings…", menu)
        self._settings_action.triggered.connect(self._ctrl.open_settings)
        menu.addAction(self._settings_action)

        menu.addSeparator()

        self._export_action = QAction("Export Vault…", menu)
        self._export_action.triggered.connect(self._ctrl.export_vault)
        menu.addAction(self._export_action)

        self._import_action = QAction("Import Vault…", menu)
        self._import_action.triggered.connect(self._ctrl.import_vault)
        menu.addAction(self._import_action)

        menu.addSeparator()

        self._startup_action = QAction("Start with Windows", menu)
        self._startup_action.setCheckable(True)
        self._startup_action.setChecked(is_startup_enabled())
        self._startup_action.triggered.connect(self._on_toggle_startup)
        menu.addAction(self._startup_action)

        menu.addSeparator()

        quit_action = QAction("Exit Open Sesame", menu)
        quit_action.triggered.connect(self._ctrl.quit_app)
        menu.addAction(quit_action)

        self.setContextMenu(menu)

    # ------------------------------------------------------------------

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._ctrl.toggle_bubble()

    def _on_toggle_startup(self, checked: bool) -> None:
        if checked:
            enable_startup()
        else:
            disable_startup()
        self._startup_action.setChecked(is_startup_enabled())
