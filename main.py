"""Sesame — main entry point.

Wires together: Vault, ClipboardManager, Bubble, VaultPanel, TrayIcon.
"""

from __future__ import annotations

__version__ = "1.1"

import ctypes
import logging
import os
import sys

# ── Make sure the project root is on sys.path when running from source ──
sys.path.insert(0, os.path.dirname(__file__))

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QSystemTrayIcon

from app.bubble import Bubble
from app.utils.icons import load as _load_fa_font
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
        self._tray.setToolTip(f"Sesame {__version__}")
        self._tray.show()

        # Connect panel signals
        self._panel.add_requested.connect(self.open_add_entry)
        self._panel.edit_requested.connect(self._on_edit_requested)
        self._panel.delete_requested.connect(self._on_delete_requested)
        self._panel.settings_requested.connect(self.open_settings)
        self._panel.sponsor_requested.connect(self.open_donate)
        self._panel.quit_requested.connect(self.quit_app)
        self._panel.restore_requested.connect(self._on_restore)

        # Bubble countdown mirror — connect once here, not inside _on_restore
        self._clipboard.countdown_tick.connect(self._on_clipboard_tick)
        self._clipboard.cleared.connect(self._on_clipboard_cleared)

        # Apply appearance and default category on startup
        self._panel.apply_appearance(self._config)
        self._apply_default_category()

    def _on_clipboard_tick(self, entry_id: str, seconds: int) -> None:
        """Mirror countdown on bubble when panel is hidden."""
        if not self._panel.isVisible() and self._bubble.isVisible():
            self._bubble.show_countdown(seconds)

    def _on_clipboard_cleared(self, entry_id: str) -> None:
        self._bubble.clear_countdown()

    def _on_restore(self, btn_center) -> None:
        half = self._bubble.width() // 2
        self._bubble.move(btn_center.x() - half, btn_center.y() - half)
        self._bubble._save_position()
        self._panel.hide()
        self._bubble.show()
        # If a countdown is already running, show it on bubble immediately
        if self._clipboard.active_entry_id and self._clipboard._remaining > 0:
            self._bubble.show_countdown(self._clipboard._remaining)

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
        dlg = AddEditEntryDialog(self._vault, parent=None)
        if dlg.exec() == AddEditEntryDialog.DialogCode.Accepted:
            entry, secret = dlg.result_entry()
            self._vault.add_entry(entry, secret)
            self._panel.refresh()


    def locate_bubble(self) -> None:
        """Flash the bubble at screen centre — same effect as a second instance."""
        self._bubble.flash_and_center()

    def open_donate(self) -> None:
        """Open the sponsor / donation page."""
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl("https://github.com/sponsors/tienhm"))

    def open_settings(self) -> None:
        dlg = SettingsDialog(self._vault, self._config, self._lock_mgr,
                             panel=self._panel, bubble=self._bubble, parent=None)
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
        dlg = ExportDialog(None)
        if dlg.exec() != ExportDialog.DialogCode.Accepted:
            return
        path, _ = QFileDialog.getSaveFileName(
            self._panel, "Save Export File", "sesame_backup.sesame",
            "Sesame Vault (*.sesame)"
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
            "Sesame Vault (*.sesame)"
        )
        if not path:
            return
        try:
            with open(path, "rb") as f:
                file_bytes = f.read()
        except Exception as e:
            QMessageBox.critical(None, "Import Failed", f"Cannot read file:\n{e}")
            return

        dlg = ImportPasswordDialog(path, None)
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
        dlg = AddEditEntryDialog(self._vault, entry=entry, parent=None)
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

    def run(self, _keep_alive=None) -> int:
        self._bubble.show()
        # Warm up DWM compositing: show panel at opacity 0, hide, restore.
        # This primes the WA_TranslucentBackground surface so the background
        # image renders correctly on the first real open.
        self._panel.setWindowOpacity(0.0)
        self._panel.show()
        QTimer.singleShot(0, self._finish_warmup)
        return self._qt_app.exec()

    def _finish_warmup(self) -> None:
        self._panel.hide()
        self._panel.setWindowOpacity(1.0)
        self._panel.apply_appearance(self._config)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

_IPC_SERVER_NAME  = "OpenSesame_IPC"
_MUTEX_NAME       = "Global\\OpenSesame_SingleInstance"
_ERROR_EXISTS     = 183   # Windows ERROR_ALREADY_EXISTS


def _acquire_mutex():
    """Create a named mutex. Returns None if another instance already holds it."""
    if sys.platform != "win32":
        return object()  # non-Windows: always allow
    handle = ctypes.windll.kernel32.CreateMutexW(None, False, _MUTEX_NAME)
    if ctypes.windll.kernel32.GetLastError() == _ERROR_EXISTS:
        return None
    return handle   # keep alive in caller


def _on_second_instance(server, controller) -> None:
    conn = server.nextPendingConnection()
    if conn:
        conn.waitForReadyRead(200)
        conn.close()
    controller._bubble.flash_and_center()


def main() -> None:
    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Sesame")
    app.setApplicationDisplayName(f"Sesame {__version__}")
    app.setApplicationVersion(__version__)
    app.setQuitOnLastWindowClosed(False)  # keep alive when panel/bubble closed

    # ── Single-instance guard ─────────────────────────────────────────
    from PySide6.QtNetwork import QLocalServer, QLocalSocket
    _mutex = _acquire_mutex()
    if _mutex is None:
        # Another instance is running — signal it and exit
        sock = QLocalSocket()
        sock.connectToServer(_IPC_SERVER_NAME)
        if sock.waitForConnected(1000):
            sock.write(b"show")
            sock.flush()
            sock.waitForBytesWritten(1000)
        sys.exit(0)

    # First instance — start IPC server (clean up any stale socket first)
    QLocalServer.removeServer(_IPC_SERVER_NAME)
    ipc_server = QLocalServer()
    ipc_server.listen(_IPC_SERVER_NAME)

    _load_stylesheet(app)
    _load_fa_font()

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "Sesame", "System tray is not available on this desktop.")
        sys.exit(1)

    controller = SesameApp(app)
    ipc_server.newConnection.connect(
        lambda: _on_second_instance(ipc_server, controller)
    )
    sys.exit(controller.run(_mutex))


if __name__ == "__main__":
    main()
