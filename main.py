"""Sesame — main entry point.

Wires together: Vault, ClipboardManager, Bubble, VaultPanel, TrayIcon.
"""

from __future__ import annotations

__version__ = "1.4"

import ctypes
import logging
import os
import sys
import time

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
from app.utils.activity_log import ActivityLogger
from app.utils.clipboard import ClipboardManager
from app.utils.lock_manager import LockManager
from app.utils.movement_reminder import MovementReminder
from app.utils.startup import ensure_startup_enabled
from app.utils.vault_io import export_vault, import_vault
from app.vault_panel import VaultPanel
from app.dialogs.movement_confirm import MovementConfirmDialog

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
        self._clipboard = ClipboardManager(self._config)
        self._lock_mgr = LockManager(self._config)
        self._icon = _make_icon()

        self._panel = VaultPanel(self._vault, self._clipboard, self._lock_mgr, self._config)
        self._bubble = Bubble(self._config)
        self._bubble.set_panel(self._panel)

        self._tray = TrayIcon(self._icon, self)
        self._tray.setToolTip(f"Sesame v{__version__}")
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

        # Movement reminder
        self._movement_reminder = MovementReminder(self._config)
        self._bubble.set_movement_reminder(self._movement_reminder)
        self._panel.set_movement_reminder(self._movement_reminder)
        self._bubble.movement_click.connect(self._on_movement_click)
        self._panel.movement_badge_clicked.connect(self._on_movement_badge_click)
        self._movement_reminder.reminder_triggered.connect(self._on_movement_triggered)
        self._panel.panel_closed.connect(self._on_panel_closed)
        self._movement_pending = False

        # Activity log — screen-on timestamps + daily movement-confirm counts
        self._activity_log = ActivityLogger()
        self._last_resume_ts = 0.0

        # System power events (hibernate/resume) pause/reset the reminder
        self._power_watcher = _PowerWatcher()
        self._power_watcher.setFixedSize(0, 0)
        self._power_watcher.show()
        self._power_watcher.register_session_notifications()
        self._power_watcher.suspend_detected.connect(self._movement_reminder.pause)
        self._power_watcher.resume_detected.connect(self._on_system_resume)
        self._power_watcher.session_unlocked.connect(self._on_screen_on)

        # Apply appearance and default category on startup
        self._panel.apply_appearance(self._config)
        self._apply_default_category()

    def _on_clipboard_tick(self, entry_id: str, seconds: int) -> None:
        """Mirror countdown on bubble when panel is hidden."""
        if not self._panel.isVisible() and self._bubble.isVisible():
            self._bubble.show_countdown(seconds)

    def _on_clipboard_cleared(self, entry_id: str) -> None:
        self._bubble.clear_countdown()

    def _on_movement_triggered(self) -> None:
        """Interval elapsed — start blinking the bubble (and badge auto-detects via timer)."""
        if self._panel.isVisible():
            self._movement_pending = True
            return
        self._start_movement_blink()

    def _on_panel_closed(self) -> None:
        """Panel just closed — fire any movement reminder that was deferred while it was open."""
        if self._movement_pending and self._movement_reminder.waiting:
            self._movement_pending = False
            self._start_movement_blink()

    def _start_movement_blink(self) -> None:
        if not self._bubble.isVisible():
            self._bubble.show()
        self._bubble.start_waiting_blink()

    def _on_movement_click(self) -> None:
        """User clicked the blinking bubble — show the confirm dialog, keep blinking."""
        self._show_movement_confirm()

    def _on_movement_badge_click(self) -> None:
        """User clicked the movement badge on the panel — show the confirm dialog, keep blinking."""
        self._show_movement_confirm()

    def _show_movement_confirm(self) -> None:
        """Show the movement confirmation dialog (shared by bubble click and badge click)."""
        dlg = MovementConfirmDialog(parent=None)
        dlg.confirmed.connect(self._on_movement_confirmed)
        dlg.snoozed.connect(self._on_movement_snoozed)
        dlg.show()
        self._movement_dlg = dlg  # keep a reference alive

    def _on_movement_confirmed(self) -> None:
        """Unified handler: user confirmed they moved (bubble or vault badge)."""
        self._movement_pending = False
        self._bubble.stop_waiting_blink()
        self._panel.stop_badge_blink()
        self._movement_reminder.reset()
        self._activity_log.log_move_confirmed()

    def _on_movement_snoozed(self) -> None:
        """Unified handler: user chose snooze (bubble or vault badge)."""
        self._movement_pending = False
        self._bubble.stop_waiting_blink()
        self._panel.stop_badge_blink()
        self._movement_reminder.snooze()

    def _on_system_resume(self) -> None:
        """System resumed from hibernate/sleep — reset the reminder and remember
        the timestamp so the following session-unlock isn't logged as screen-on."""
        self._last_resume_ts = time.monotonic()
        self._movement_reminder.resume()

    def _on_screen_on(self) -> None:
        """Session unlocked (genuine screen-on) — log it and reset the movement
        reminder, unless it immediately follows a hibernate/sleep resume
        (already accounted for separately by _on_system_resume)."""
        if time.monotonic() - self._last_resume_ts < 10:
            return
        self._activity_log.log_screen_on()
        self._movement_reminder.resume()

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
            if dlg._result_otp_secret:
                self._vault.set_otp_secret(entry.id, dlg._result_otp_secret)
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
                             panel=self._panel, bubble=self._bubble,
                             export_fn=self.export_vault,
                             import_fn=self.import_vault,
                             reminder=self._movement_reminder,
                             parent=None)
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
            data = export_vault(self._vault.entries, self._vault.get_secret, dlg.password(),
                               get_otp_secret_fn=self._vault.get_otp_secret)
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
                entries_dicts, secrets, otp_secrets = import_vault(file_bytes, dlg.password())
                count = 0
                for ed in entries_dicts:
                    entry = Entry.from_dict(ed)
                    secret = secrets.get(entry.id, "")
                    self._vault.add_entry(entry, secret)
                    otp = otp_secrets.get(ed.get("id", ""), "")
                    if otp:
                        self._vault.set_otp_secret(entry.id, otp)
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
            otp = dlg._result_otp_secret
            if otp is not None:  # empty string intentionally clears OTP
                self._vault.set_otp_secret(updated_entry.id, otp)
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
# Power event watcher — pauses/resumes the movement reminder on hibernate,
# and detects genuine screen-on (session unlock) events for the activity log
# ---------------------------------------------------------------------------

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget as _QWidget

_WM_POWERBROADCAST      = 0x0218
_PBT_APMSUSPEND         = 4
_PBT_APMRESUMEAUTOMATIC = 18

_WM_WTSSESSION_CHANGE   = 0x02B1
_WTS_SESSION_UNLOCK     = 0x8
_NOTIFY_FOR_THIS_SESSION = 0


class _PowerWatcher(_QWidget):
    """Hidden widget that listens for Windows power (suspend/resume) events
    and session unlock (screen-on) events."""

    suspend_detected = Signal()
    resume_detected  = Signal()
    session_unlocked = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._wts_registered = False

    def register_session_notifications(self) -> None:
        """Call after show() so winId() is valid — enables WM_WTSSESSION_CHANGE."""
        if sys.platform != "win32":
            return
        try:
            hwnd = int(self.winId())
            wtsapi = ctypes.WinDLL("wtsapi32.dll")
            if wtsapi.WTSRegisterSessionNotification(hwnd, _NOTIFY_FOR_THIS_SESSION):
                self._wts_registered = True
        except Exception:
            pass

    def nativeEvent(self, eventType, message):
        if sys.platform == "win32":
            try:
                import ctypes.wintypes
                msg = ctypes.wintypes.MSG.from_address(int(message))
                if msg.message == _WM_POWERBROADCAST:
                    if msg.wParam == _PBT_APMSUSPEND:
                        self.suspend_detected.emit()
                    elif msg.wParam == _PBT_APMRESUMEAUTOMATIC:
                        self.resume_detected.emit()
                elif msg.message == _WM_WTSSESSION_CHANGE:
                    if msg.wParam == _WTS_SESSION_UNLOCK:
                        self.session_unlocked.emit()
            except Exception:
                pass
        return False, 0

    def closeEvent(self, event) -> None:
        if self._wts_registered:
            try:
                hwnd = int(self.winId())
                ctypes.WinDLL("wtsapi32.dll").WTSUnRegisterSessionNotification(hwnd)
            except Exception:
                pass
        super().closeEvent(event)


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
    app.setApplicationDisplayName(f"Sesame v{__version__}")
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
