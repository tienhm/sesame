"""Sesame — main entry point.

Wires together: Vault, ClipboardManager, Bubble, VaultPanel, TrayIcon.
"""

from __future__ import annotations

import logging
import os
import sys

# ── Make sure the project root is on sys.path when running from source ──
sys.path.insert(0, os.path.dirname(__file__))

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QSystemTrayIcon

from app.bubble import Bubble
from app.config import AppConfig
from app.dialogs.add_entry import AddEditEntryDialog
from app.dialogs.export_import import ExportDialog, ImportPasswordDialog
from app.dialogs.settings import SettingsDialog
from app.models.entry import Entry
from app.models.vault import Vault
from app.tray import TrayIcon
from app.utils.clipboard import ClipboardManager
from app.utils.lock_manager import LockManager
from app.utils.startup import ensure_startup_enabled
from app.utils.vault_io import export_vault, import_vault
from app.vault_panel import VaultPanel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_stylesheet(app: QApplication) -> None:
    qss_path = os.path.join(os.path.dirname(__file__), "resources", "style.qss")
    if os.path.exists(qss_path):
        with open(qss_path, encoding="utf-8") as fh:
            app.setStyleSheet(fh.read())


def _make_icon() -> QIcon:
    """Generate a simple fallback icon if no icon.png is found."""
    icon_path = os.path.join(os.path.dirname(__file__), "resources", "icon.png")
    if os.path.exists(icon_path):
        return QIcon(icon_path)
    # Draw a simple coloured square as fallback
    px = QPixmap(32, 32)
    px.fill(QColor("#5865f2"))
    painter = QPainter(px)
    painter.setPen(QColor("white"))
    painter.setFont(painter.font())
    painter.drawText(px.rect(), Qt.AlignmentFlag.AlignCenter, "S")
    painter.end()
    return QIcon(px)


# ---------------------------------------------------------------------------
# Application controller
# ---------------------------------------------------------------------------

class SesameApp:
    """Owns all top-level widgets and wires their signals together."""

    def __init__(self, qt_app: QApplication) -> None:
        self._qt_app = qt_app
        self._config = AppConfig()
        self._vault = Vault()
        self._clipboard = ClipboardManager()
        self._lock_mgr = LockManager(self._config)
        self._icon = _make_icon()

        self._panel = VaultPanel(self._vault, self._clipboard, self._lock_mgr)
        self._bubble = Bubble(self._config)
        self._bubble.set_panel(self._panel)

        self._tray = TrayIcon(self._icon, self)
        self._tray.setToolTip("Open Sesame")
        self._tray.show()

        # Connect panel signals
        self._panel.add_requested.connect(self.open_add_entry)
        self._panel.edit_requested.connect(self._on_edit_requested)
        self._panel.delete_requested.connect(self._on_delete_requested)
        self._panel.settings_requested.connect(self.open_settings)
        self._panel.quit_requested.connect(self.quit_app)
        self._panel.restore_requested.connect(self._on_restore)

    def _on_restore(self) -> None:
        self._panel.hide()
        self._bubble.show()

        # Apply appearance (opacity + background image) on startup
        self._panel.apply_appearance(self._config)
        self._apply_default_category()

        # Enable startup on first run (default ON)
        ensure_startup_enabled()

    # ------------------------------------------------------------------
    # Public interface used by TrayIcon
    # ------------------------------------------------------------------

    def toggle_bubble(self) -> None:
        if self._bubble.isVisible():
            self._bubble.hide()
            self._panel.hide()
        else:
            self._bubble.show()

    def open_add_entry(self) -> None:
        dlg = AddEditEntryDialog(self._vault, parent=self._panel)
        if dlg.exec() == AddEditEntryDialog.DialogCode.Accepted:
            entry, secret = dlg.result_entry()
            self._vault.add_entry(entry, secret)
            self._panel.refresh()


    def open_settings(self) -> None:
        dlg = SettingsDialog(self._vault, self._config, self._lock_mgr,
                             panel=self._panel, parent=None)
        dlg.exec()
        self._panel.refresh()
        self._panel.apply_appearance(self._config)

    def _apply_default_category(self) -> None:
        cat = self._config.get("default_category", "")
        if cat:
            self._panel.select_category(cat)

    def export_vault(self) -> None:
        if not self._vault.entries:
            QMessageBox.information(None, "Export Vault", "No entries to export.")
            return
        dlg = ExportDialog(self._panel)
        if dlg.exec() != ExportDialog.DialogCode.Accepted:
            return
        path, _ = QFileDialog.getSaveFileName(
            self._panel, "Save Export File", "sesame_backup.sesame",
            "Open Sesame Vault (*.sesame)"
        )
        if not path:
            return
        try:
            data = export_vault(self._vault.entries, self._vault.get_secret, dlg.password())
            with open(path, "wb") as f:
                f.write(data)
            QMessageBox.information(
                None, "Export Vault",
                f"Exported {len(self._vault.entries)} entries to:\n{path}"
            )
        except Exception as e:
            QMessageBox.critical(None, "Export Failed", str(e))

    def import_vault(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self._panel, "Open Export File", "",
            "Open Sesame Vault (*.sesame)"
        )
        if not path:
            return
        try:
            file_bytes = open(path, "rb").read()
        except Exception as e:
            QMessageBox.critical(None, "Import Failed", f"Cannot read file:\n{e}")
            return

        dlg = ImportPasswordDialog(path, self._panel)
        while dlg.exec() == ImportPasswordDialog.DialogCode.Accepted:
            try:
                entries_dicts, secrets = import_vault(file_bytes, dlg.password())
                count = 0
                for ed in entries_dicts:
                    entry = Entry.from_dict(ed)
                    secret = secrets.get(entry.id, "")
                    self._vault.add_entry(entry, secret)
                    count += 1
                self._panel.refresh()
                QMessageBox.information(
                    None, "Import Vault",
                    f"Successfully imported {count} entries."
                )
                return
            except ValueError as e:
                dlg.set_error(str(e))

    def quit_app(self) -> None:
        self._panel.close()
        self._bubble.close()
        self._tray.hide()
        self._qt_app.quit()

    # ------------------------------------------------------------------
    # Private slots
    # ------------------------------------------------------------------

    def _on_edit_requested(self, entry_id: str) -> None:
        entry = next((e for e in self._vault.entries if e.id == entry_id), None)
        if entry is None:
            return
        dlg = AddEditEntryDialog(self._vault, entry=entry, parent=self._panel)
        if dlg.exec() == AddEditEntryDialog.DialogCode.Accepted:
            updated_entry, secret = dlg.result_entry()
            self._vault.update_entry(updated_entry, secret or None)
            self._panel.refresh()

    def _on_delete_requested(self, entry_id: str) -> None:
        entry = next((e for e in self._vault.entries if e.id == entry_id), None)
        if entry is None:
            return
        reply = QMessageBox.question(
            self._panel,
            "Delete Entry",
            f'Delete "{entry.name}"? This cannot be undone.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._vault.delete_entry(entry_id)
            self._panel.refresh()

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def run(self) -> int:
        self._bubble.show()
        return self._qt_app.exec()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Open Sesame")
    app.setApplicationDisplayName("Open Sesame")
    app.setQuitOnLastWindowClosed(False)  # keep alive when panel/bubble closed

    _load_stylesheet(app)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "Open Sesame", "System tray is not available on this desktop.")
        sys.exit(1)

    controller = SesameApp(app)
    sys.exit(controller.run())


if __name__ == "__main__":
    main()
