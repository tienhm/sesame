"""Settings dialog — General, Categories, Security tabs."""

from __future__ import annotations

from PySide6.QtCore import Qt, QPoint, QRect, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

import os

from PySide6.QtGui import QColor, QPainter, QPen, QPixmap

from app.config import AppConfig
from app.models.vault import Vault
from app.utils.lock_manager import LockManager
from app.utils.startup import disable_startup, enable_startup, is_startup_enabled

from app.utils.icons import FA as _FA
_LOCK_ICON   = _FA.LOCK
_UNLOCK_ICON = _FA.UNLOCK


class SettingsDialog(QDialog):
    def __init__(
        self,
        vault: Vault,
        config: AppConfig,
        lock_manager: LockManager,
        panel: QWidget | None = None,
        bubble: QWidget | None = None,
        export_fn=None,
        import_fn=None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        try:
            from main import __version__ as _ver
            _title = f"Settings — Sesame v{_ver}"
        except Exception:
            _title = "Settings"
        self.setWindowTitle(_title)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setMinimumSize(420, 340)
        self._vault = vault
        self._config = config
        self._lock_mgr = lock_manager
        self._panel = panel
        self._bubble = bubble
        self._export_fn = export_fn
        self._import_fn = import_fn
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 12)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_general_tab(), "General")
        self._tabs.addTab(self._build_categories_tab(), "Categories")
        self._tabs.addTab(self._build_security_tab(), "Security")
        self._tabs.addTab(self._build_data_tab(), "Data")
        layout.addWidget(self._tabs)

        close_btn = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_btn.rejected.connect(self.accept)
        layout.addWidget(close_btn)

    # ── General tab ────────────────────────────────────────────────────

    def _build_general_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(12)

        self._startup_cb = QCheckBox("Start with Windows")
        self._startup_cb.setChecked(is_startup_enabled())
        self._startup_cb.toggled.connect(self._on_startup_toggled)
        layout.addWidget(self._startup_cb)

        form = QFormLayout()
        form.setSpacing(8)

        # Bubble opacity
        bubble_row = QHBoxLayout()
        self._bubble_slider = QSlider(Qt.Orientation.Horizontal)
        self._bubble_slider.setRange(20, 100)
        self._bubble_slider.setValue(int(float(self._config.get("bubble_opacity", 1.0)) * 100))
        self._bubble_lbl = QLabel(f"{self._bubble_slider.value()}%")
        self._bubble_lbl.setFixedWidth(36)
        self._bubble_slider.valueChanged.connect(self._on_bubble_opacity_changed)
        bubble_row.addWidget(self._bubble_slider)
        bubble_row.addWidget(self._bubble_lbl)
        form.addRow("Bubble opacity:", bubble_row)

        # Default category
        self._default_cat_combo = QComboBox()
        self._default_cat_combo.addItem("(none)")
        for cat in sorted(self._vault.categories()):
            self._default_cat_combo.addItem(cat)
        saved = self._config.get("default_category", "")
        idx = self._default_cat_combo.findText(saved) if saved else 0
        self._default_cat_combo.setCurrentIndex(max(0, idx))
        self._default_cat_combo.currentTextChanged.connect(self._on_default_cat_changed)
        form.addRow("Default category:", self._default_cat_combo)

        # Panel opacity
        opacity_row = QHBoxLayout()
        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(0, 100)
        self._opacity_slider.setValue(int(float(self._config.get("panel_component_opacity", 1.0)) * 100))
        has_image = bool(self._config.get("panel_bg_image", ""))
        self._opacity_slider.setEnabled(has_image)
        self._opacity_slider.setTickInterval(10)
        self._opacity_lbl = QLabel(f"{self._opacity_slider.value()}%")
        self._opacity_lbl.setFixedWidth(36)
        self._opacity_slider.valueChanged.connect(self._on_opacity_changed)
        opacity_row.addWidget(self._opacity_slider)
        opacity_row.addWidget(self._opacity_lbl)
        form.addRow("Components opacity:", opacity_row)

        layout.addLayout(form)

        # Background image
        bg_label = QLabel("Background image")
        bg_label.setStyleSheet("font-weight: 600; color: #e8eaed; margin-top: 8px;")
        layout.addWidget(bg_label)

        bg_row = QHBoxLayout()
        self._bg_path_lbl = QLabel(self._short_path(self._config.get("panel_bg_image", "")))
        self._bg_path_lbl.setStyleSheet("color: #adb5bd; font-size: 11px;")
        self._bg_path_lbl.setWordWrap(True)
        bg_browse_btn = QPushButton("Browse…")
        bg_browse_btn.setMinimumWidth(90)
        bg_browse_btn.clicked.connect(self._browse_bg_image)
        bg_clear_btn = QPushButton("Clear")
        bg_clear_btn.setMinimumWidth(70)
        bg_clear_btn.clicked.connect(self._clear_bg_image)
        bg_row.addWidget(self._bg_path_lbl, stretch=1)
        bg_row.addWidget(bg_browse_btn)
        bg_row.addWidget(bg_clear_btn)
        layout.addLayout(bg_row)

        self._crop_widget = _ImageCropWidget()
        self._crop_widget.set_image(
            self._config.get("panel_bg_image", ""),
            float(self._config.get("panel_bg_offset_x", 0.5)),
            float(self._config.get("panel_bg_offset_y", 0.5)),
        )
        self._crop_widget.offset_changed.connect(self._on_crop_offset_changed)
        layout.addWidget(self._crop_widget)

        layout.addStretch()
        return w

    def _on_startup_toggled(self, checked: bool) -> None:
        if checked:
            enable_startup()
        else:
            disable_startup()
        self._startup_cb.setChecked(is_startup_enabled())

    def _on_default_cat_changed(self, text: str) -> None:
        self._config.set("default_category", "" if text == "(none)" else text)

    def _on_bubble_opacity_changed(self, value: int) -> None:
        self._bubble_lbl.setText(f"{value}%")
        self._config.set("bubble_opacity", value / 100.0)
        if self._bubble and hasattr(self._bubble, "apply_opacity"):
            self._bubble.apply_opacity()

    def _on_opacity_changed(self, value: int) -> None:
        self._opacity_lbl.setText(f"{value}%")
        self._config.set("panel_component_opacity", value / 100.0)
        self._apply_panel_appearance()

    def _browse_bg_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Background Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if path:
            self._config.set("panel_bg_image", path)
            self._config.set("panel_bg_offset_x", 0.5)
            self._config.set("panel_bg_offset_y", 0.5)
            self._bg_path_lbl.setText(self._short_path(path))
            self._crop_widget.set_image(path, 0.5, 0.5)
            self._opacity_slider.setEnabled(True)
            self._apply_panel_appearance()

    def _clear_bg_image(self) -> None:
        self._config.set("panel_bg_image", "")
        self._bg_path_lbl.setText("(none)")
        self._crop_widget.set_image("", 0.5, 0.5)
        self._opacity_slider.setEnabled(False)
        self._apply_panel_appearance()

    def _on_crop_offset_changed(self, ox: float, oy: float) -> None:
        self._config.set("panel_bg_offset_x", ox)
        self._config.set("panel_bg_offset_y", oy)
        self._apply_panel_appearance()

    def _apply_panel_appearance(self) -> None:
        if self._panel and hasattr(self._panel, "apply_appearance"):
            self._panel.apply_appearance(self._config)

    @staticmethod
    def _short_path(path: str) -> str:
        if not path:
            return "(none)"
        return os.path.basename(path) if len(path) > 40 else path

    # ── Categories tab ─────────────────────────────────────────────────

    def _build_categories_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(8)

        self._cat_list = QListWidget()
        self._cat_list.currentRowChanged.connect(self._on_cat_row_changed)
        layout.addWidget(self._cat_list)

        btn_row = QHBoxLayout()
        self._rename_btn = QPushButton("Rename…")
        self._rename_btn.setEnabled(False)
        self._rename_btn.clicked.connect(self._rename_category)
        self._delete_cat_btn = QPushButton("Delete…")
        self._delete_cat_btn.setEnabled(False)
        self._delete_cat_btn.clicked.connect(self._delete_category)
        btn_row.addWidget(self._rename_btn)
        btn_row.addWidget(self._delete_cat_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._refresh_cat_list()
        return w

    def _refresh_cat_list(self) -> None:
        self._cat_list.clear()
        for cat in sorted(self._vault.categories()):
            self._cat_list.addItem(cat)

    def _on_cat_row_changed(self, row: int) -> None:
        enabled = row >= 0
        self._rename_btn.setEnabled(enabled)
        self._delete_cat_btn.setEnabled(enabled)

    def _rename_category(self) -> None:
        item = self._cat_list.currentItem()
        if not item:
            return
        old = item.text()
        new, ok = QInputDialog.getText(self, "Rename Category", "New name:", text=old)
        new = new.strip()
        if ok and new and new != old:
            self._vault.rename_category(old, new)
            self._lock_mgr.rename_category(old, new)
            # Update default category setting if needed
            if self._config.get("default_category") == old:
                self._config.set("default_category", new)
            self._refresh_cat_list()
            self._refresh_security_list()
            self._refresh_default_cat_combo()

    def _delete_category(self) -> None:
        item = self._cat_list.currentItem()
        if not item:
            return
        cat = item.text()
        self._vault.delete_category(cat, "General")
        self._lock_mgr.remove_locked_category(cat)
        if self._config.get("default_category") == cat:
            self._config.set("default_category", "")
        self._refresh_cat_list()
        self._refresh_security_list()
        self._refresh_default_cat_combo()

    # ── Security tab ───────────────────────────────────────────────────

    def _build_security_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(10)

        # Master password section
        pw_label = QLabel("Master password")
        pw_label.setStyleSheet("font-weight: 600; color: #e8eaed;")
        layout.addWidget(pw_label)

        pw_btn_row = QHBoxLayout()
        self._set_master_btn = QPushButton("Set / Change…")
        self._set_master_btn.clicked.connect(self._set_master_password)
        self._remove_master_btn = QPushButton("Remove…")
        self._remove_master_btn.clicked.connect(self._remove_master_password)
        self._remove_master_btn.setEnabled(self._lock_mgr.has_master_password())
        pw_btn_row.addWidget(self._set_master_btn)
        pw_btn_row.addWidget(self._remove_master_btn)
        pw_btn_row.addStretch()
        layout.addLayout(pw_btn_row)

        self._pw_status = QLabel(self._master_pw_status_text())
        self._pw_status.setStyleSheet("color: #adb5bd; font-size: 11px;")
        layout.addWidget(self._pw_status)

        # Category lock list
        cats_label = QLabel("Protected categories")
        cats_label.setStyleSheet("font-weight: 600; color: #e8eaed; margin-top: 6px;")
        layout.addWidget(cats_label)

        hint = QLabel("Copying from these categories will require the master password.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #adb5bd; font-size: 11px;")
        layout.addWidget(hint)

        self._sec_list = QListWidget()
        self._sec_list.itemChanged.connect(self._on_cat_lock_toggled)
        layout.addWidget(self._sec_list, stretch=1)

        self._refresh_security_list()
        return w

    # ── Data tab ───────────────────────────────────────────────────────

    def _build_data_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ── Export ────────────────────────────────────────────────────
        exp_lbl = QLabel("Export vault")
        exp_lbl.setStyleSheet("font-weight: 600; color: #e8eaed;")
        layout.addWidget(exp_lbl)

        exp_form = QFormLayout()
        exp_form.setSpacing(6)
        self._exp_pw = QLineEdit(); self._exp_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self._exp_pw.setPlaceholderText("Encryption password")
        self._exp_pw2 = QLineEdit(); self._exp_pw2.setEchoMode(QLineEdit.EchoMode.Password)
        self._exp_pw2.setPlaceholderText("Confirm password")
        exp_form.addRow("Password:", self._exp_pw)
        exp_form.addRow("Confirm:", self._exp_pw2)
        layout.addLayout(exp_form)

        self._exp_err = QLabel("")
        self._exp_err.setStyleSheet("color: #e74c3c; font-size: 11px;")
        layout.addWidget(self._exp_err)

        self._exp_btn = QPushButton("Export Vault…")
        self._exp_btn.clicked.connect(self._on_export)
        self._exp_pw.textChanged.connect(self._validate_export)
        self._exp_pw2.textChanged.connect(self._validate_export)
        self._validate_export()
        layout.addWidget(self._exp_btn)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        # ── Import ────────────────────────────────────────────────────
        imp_lbl = QLabel("Import vault")
        imp_lbl.setStyleSheet("font-weight: 600; color: #e8eaed;")
        layout.addWidget(imp_lbl)

        file_row = QHBoxLayout()
        self._imp_path = QLineEdit(); self._imp_path.setReadOnly(True)
        self._imp_path.setPlaceholderText("Select a .sesame file…")
        browse_btn = QPushButton("Browse…")
        browse_btn.setProperty("flat", True)
        browse_btn.setMinimumWidth(80)
        browse_btn.clicked.connect(self._browse_import_file)
        file_row.addWidget(self._imp_path, stretch=1)
        file_row.addWidget(browse_btn)
        layout.addLayout(file_row)

        imp_form = QFormLayout(); imp_form.setSpacing(6)
        self._imp_pw = QLineEdit(); self._imp_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self._imp_pw.setPlaceholderText("File password")
        imp_form.addRow("Password:", self._imp_pw)
        layout.addLayout(imp_form)

        self._imp_err = QLabel("")
        self._imp_err.setStyleSheet("color: #e74c3c; font-size: 11px;")
        layout.addWidget(self._imp_err)

        self._imp_btn = QPushButton("Import Vault…")
        self._imp_btn.setEnabled(False)
        self._imp_path.textChanged.connect(self._validate_import)
        self._imp_pw.textChanged.connect(self._validate_import)
        self._imp_btn.clicked.connect(self._on_import)
        layout.addWidget(self._imp_btn)

        layout.addStretch()
        return w

    # ── Data tab helpers ────────────────────────────────────────────────

    def _validate_export(self) -> None:
        pw, pw2 = self._exp_pw.text(), self._exp_pw2.text()
        if pw2 and pw != pw2:
            self._exp_err.setText("Passwords do not match.")
            self._exp_btn.setEnabled(False)
        else:
            self._exp_err.setText("")
            self._exp_btn.setEnabled(bool(pw) and pw == pw2)

    def _validate_import(self) -> None:
        self._imp_btn.setEnabled(
            bool(self._imp_path.text()) and bool(self._imp_pw.text())
        )

    def _browse_import_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Backup File", "", "Sesame Vault (*.sesame)"
        )
        if path:
            self._imp_path.setText(path)
            self._imp_err.setText("")

    def _on_export(self) -> None:
        from app.utils.vault_io import export_vault as _export_vault
        password = self._exp_pw.text()
        if not self._vault.entries:
            self._exp_err.setText("No entries to export.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Backup", "sesame_backup.sesame", "Sesame Vault (*.sesame)"
        )
        if not path:
            return
        try:
            data = _export_vault(self._vault.entries, self._vault.get_secret, password)
            with open(path, "wb") as f:
                f.write(data)
            self._exp_pw.clear()
            self._exp_pw2.clear()
            self._exp_err.setStyleSheet("color: #2d6a4f; font-size: 11px;")
            self._exp_err.setText(f"Exported {len(self._vault.entries)} entries.")
        except Exception as e:
            self._exp_err.setStyleSheet("color: #e74c3c; font-size: 11px;")
            self._exp_err.setText(f"Export failed: {e}")

    def _on_import(self) -> None:
        from app.utils.vault_io import import_vault as _import_vault
        from app.models.entry import Entry
        path = self._imp_path.text()
        password = self._imp_pw.text()
        try:
            file_bytes = open(path, "rb").read()
            entries_dicts, secrets = _import_vault(file_bytes, password)
            count = 0
            for ed in entries_dicts:
                entry = Entry.from_dict(ed)
                self._vault.add_entry(entry, secrets.get(entry.id, ""))
                count += 1
            if self._panel:
                self._panel.refresh()
            self._imp_pw.clear()
            self._imp_path.clear()
            self._imp_err.setStyleSheet("color: #2d6a4f; font-size: 11px;")
            self._imp_err.setText(f"Imported {count} entries.")
        except ValueError as e:
            self._imp_err.setStyleSheet("color: #e74c3c; font-size: 11px;")
            self._imp_err.setText(str(e))
        except Exception as e:
            self._imp_err.setStyleSheet("color: #e74c3c; font-size: 11px;")
            self._imp_err.setText(f"Import failed: {e}")

    def _master_pw_status_text(self) -> str:
        return "✔  Master password is set." if self._lock_mgr.has_master_password() \
               else "✘  No master password set — categories cannot be locked."

    def _set_master_password(self) -> None:
        if self._lock_mgr.has_master_password() and not self._verify_current():
            return
        dlg = _SetPasswordDialog("master password", self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._lock_mgr.set_master_password(dlg.password())
            self._update_pw_buttons()
            self._refresh_security_list()

    def _remove_master_password(self) -> None:
        dlg = _RemovePasswordDialog(self)
        while dlg.exec() == _RemovePasswordDialog.VERIFIED:
            if self._lock_mgr.verify(dlg.password()):
                self._lock_mgr.remove_master_password()
                self._update_pw_buttons()
                self._refresh_security_list()
                return
            dlg._error.setText("Wrong password.")

    def _update_pw_buttons(self) -> None:
        has_pw = self._lock_mgr.has_master_password()
        self._pw_status.setText(self._master_pw_status_text())
        self._remove_master_btn.setEnabled(has_pw)

    def _verify_current(self) -> bool:
        dlg = UnlockDialog("master password", self)
        dlg.setWindowTitle("Verify Current Password")
        while dlg.exec() == QDialog.DialogCode.Accepted:
            if self._lock_mgr.verify(dlg.password()):
                return True
            dlg.set_error("Wrong password.")
        return False

    def _refresh_security_list(self) -> None:
        self._sec_list.blockSignals(True)
        self._sec_list.clear()
        has_pw = self._lock_mgr.has_master_password()
        locked = self._lock_mgr.locked_categories()
        for cat in sorted(self._vault.categories()):
            item = QListWidgetItem(cat)
            item.setData(Qt.ItemDataRole.UserRole, cat)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if cat in locked else Qt.CheckState.Unchecked
            )
            if not has_pw:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            self._sec_list.addItem(item)
        self._sec_list.blockSignals(False)

    def _on_cat_lock_toggled(self, item: QListWidgetItem) -> None:
        cat = item.data(Qt.ItemDataRole.UserRole)
        if item.checkState() == Qt.CheckState.Checked:
            self._lock_mgr.add_locked_category(cat)
        else:
            self._lock_mgr.remove_locked_category(cat)

    # ------------------------------------------------------------------

    def _refresh_default_cat_combo(self) -> None:
        saved = self._config.get("default_category", "")
        self._default_cat_combo.blockSignals(True)
        self._default_cat_combo.clear()
        self._default_cat_combo.addItem("(none)")
        for cat in sorted(self._vault.categories()):
            self._default_cat_combo.addItem(cat)
        idx = self._default_cat_combo.findText(saved) if saved else 0
        self._default_cat_combo.setCurrentIndex(max(0, idx))
        self._default_cat_combo.blockSignals(False)


# ---------------------------------------------------------------------------
# Helper dialogs
# ---------------------------------------------------------------------------

class _SetPasswordDialog(QDialog):
    def __init__(self, category: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Set Password — {category}")
        self.setMinimumWidth(320)
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self._pw = QLineEdit()
        self._pw.setEchoMode(QLineEdit.EchoMode.Password)
        self._pw_confirm = QLineEdit()
        self._pw_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Password:", self._pw)
        form.addRow("Confirm:", self._pw_confirm)
        layout.addLayout(form)

        self._error = QLabel("")
        self._error.setStyleSheet("color: #e74c3c;")
        layout.addWidget(self._error)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._ok_btn = btns.button(QDialogButtonBox.StandardButton.Ok)
        self._ok_btn.setEnabled(False)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self._pw.textChanged.connect(self._validate)
        self._pw_confirm.textChanged.connect(self._validate)

    def _validate(self) -> None:
        pw, conf = self._pw.text(), self._pw_confirm.text()
        if conf and pw != conf:
            self._error.setText("Passwords do not match.")
            self._ok_btn.setEnabled(False)
        else:
            self._error.setText("")
            self._ok_btn.setEnabled(bool(pw) and pw == conf)

    def _on_accept(self) -> None:
        if self._pw.text() == self._pw_confirm.text() and self._pw.text():
            self.accept()

    def password(self) -> str:
        return self._pw.text()


class UnlockDialog(QDialog):
    """Shown when the user tries to copy from a locked category."""

    def __init__(self, category: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Locked Category")
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setMinimumWidth(300)
        layout = QVBoxLayout(self)

        lbl = QLabel(f'🔒  <b>{category}</b> is protected.<br>Enter the master password to continue.')
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        form = QFormLayout()
        self._pw = QLineEdit()
        self._pw.setEchoMode(QLineEdit.EchoMode.Password)
        self._pw.setPlaceholderText("Master password")
        form.addRow("Password:", self._pw)
        layout.addLayout(form)

        self._error = QLabel("")
        self._error.setStyleSheet("color: #e74c3c;")
        layout.addWidget(self._error)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._ok_btn = btns.button(QDialogButtonBox.StandardButton.Ok)
        self._ok_btn.setEnabled(False)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self._pw.textChanged.connect(lambda t: self._ok_btn.setEnabled(bool(t)))

    def set_error(self, msg: str) -> None:
        self._error.setText(msg)

    def password(self) -> str:
        return self._pw.text()


class _ImageCropWidget(QWidget):
    """Preview image with a draggable viewport (fixed 480:400 aspect ratio).

    Drag the viewport to choose which part of the image is shown in the panel.
    Emits offset_changed(ox, oy) — normalised 0.0–1.0.
    """

    offset_changed = Signal(float, float)

    _PANEL_W = 480
    _PANEL_H = 400
    _ASPECT  = 480 / 400

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pixmap: QPixmap = QPixmap()
        self._offset_x: float = 0.5
        self._offset_y: float = 0.5
        self._drag_start: QPoint | None = None
        self._drag_ox: float = 0.5
        self._drag_oy: float = 0.5
        self.setFixedHeight(160)
        self.setMinimumWidth(200)
        self.setMouseTracking(True)

    def set_image(self, path: str, ox: float = 0.5, oy: float = 0.5) -> None:
        self._pixmap = QPixmap(path) if path and os.path.exists(path) else QPixmap()
        self._offset_x, self._offset_y = ox, oy
        self.update()

    def _scale_info(self):
        """Returns (panel_scale, panel_ovx, panel_ovy, preview_scale, preview_ox, preview_oy)."""
        pw, ph = self.width(), self.height()
        if pw == 0 or ph == 0 or self._pixmap.isNull():
            return None
        iw, ih = self._pixmap.width(), self._pixmap.height()
        # Panel scale
        ps = max(self._PANEL_W / iw, self._PANEL_H / ih)
        p_ovx = iw * ps - self._PANEL_W   # overflow in scaled-for-panel image
        p_ovy = ih * ps - self._PANEL_H
        # Preview scale
        vs = max(pw / iw, ph / ih)
        v_ox = (iw * vs - pw) / 2          # offset that preview crops from scaled image
        v_oy = (ih * vs - ph) / 2
        return ps, p_ovx, p_ovy, vs, v_ox, v_oy

    def _vp_rect(self) -> QRect:
        """Compute viewport rect in preview pixels representing what the panel shows."""
        si = self._scale_info()
        if si is None:
            return QRect(0, 0, self.width(), self.height())
        ps, p_ovx, p_ovy, vs, v_ox, v_oy = si
        iw, ih = self._pixmap.width(), self._pixmap.height()

        # Top-left of visible region in original image pixels
        ix = p_ovx * self._offset_x / ps
        iy = p_ovy * self._offset_y / ps
        # Size of visible region in original image pixels
        rw = self._PANEL_W / ps
        rh = self._PANEL_H / ps

        # Convert to preview pixel coords
        px = ix * vs - v_ox
        py = iy * vs - v_oy
        pw = rw * vs
        ph = rh * vs
        return QRect(int(px), int(py), max(1, int(pw)), max(1, int(ph)))

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        w, h = self.width(), self.height()
        if self._pixmap.isNull():
            painter.fillRect(self.rect(), QColor("#1e1f26"))
            painter.setPen(QColor("#3a3b47"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No image selected")
            painter.end()
            return
        scaled = self._pixmap.scaled(w, h,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation)
        painter.drawPixmap(0, 0, scaled,
                           (scaled.width() - w) // 2,
                           (scaled.height() - h) // 2, w, h)
        vp = self._vp_rect()
        dark = QColor(0, 0, 0, 120)
        painter.fillRect(QRect(0, 0, w, vp.top()), dark)
        painter.fillRect(QRect(0, vp.bottom(), w, h - vp.bottom()), dark)
        painter.fillRect(QRect(0, vp.top(), vp.left(), vp.height()), dark)
        painter.fillRect(QRect(vp.right(), vp.top(), w - vp.right(), vp.height()), dark)
        painter.setPen(QPen(QColor("#5865f2"), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(vp)
        painter.setPen(QColor(255, 255, 255, 160))
        painter.drawText(vp, Qt.AlignmentFlag.AlignCenter, "drag")
        painter.end()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._vp_rect().contains(event.pos()):
            self._drag_start = event.pos()
            self._drag_ox, self._drag_oy = self._offset_x, self._offset_y
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_start is not None:
            si = self._scale_info()
            d = event.pos() - self._drag_start
            if si is not None:
                ps, p_ovx, p_ovy, vs, v_ox, v_oy = si
                # Convert preview pixel delta → offset delta
                # offset = (ix * ps) / p_ovx  where ix = (px + v_ox) / vs
                # d_offset = d_px * ps / (p_ovx * vs)
                if p_ovx > 0:
                    self._offset_x = max(0.0, min(1.0,
                        self._drag_ox + d.x() * ps / (p_ovx * vs)))
                if p_ovy > 0:
                    self._offset_y = max(0.0, min(1.0,
                        self._drag_oy + d.y() * ps / (p_ovy * vs)))
            self.update()
            self.offset_changed.emit(self._offset_x, self._offset_y)
        else:
            self.setCursor(Qt.CursorShape.OpenHandCursor
                           if self._vp_rect().contains(event.pos())
                           else Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_start = None
        self.setCursor(Qt.CursorShape.OpenHandCursor
                       if self._vp_rect().contains(event.pos())
                       else Qt.CursorShape.ArrowCursor)


class _RemovePasswordDialog(QDialog):
    """Remove master password — requires current password."""

    VERIFIED = 1

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Remove Master Password")
        self.setMinimumWidth(320)
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self._pw = QLineEdit()
        self._pw.setEchoMode(QLineEdit.EchoMode.Password)
        self._pw.setPlaceholderText("Current master password")
        form.addRow("Password:", self._pw)
        layout.addLayout(form)

        self._error = QLabel("")
        self._error.setStyleSheet("color: #e74c3c;")
        layout.addWidget(self._error)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._ok_btn = btns.button(QDialogButtonBox.StandardButton.Ok)
        self._ok_btn.setText("Remove")
        self._ok_btn.setEnabled(False)
        btns.accepted.connect(self._on_remove)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self._pw.textChanged.connect(lambda t: self._ok_btn.setEnabled(bool(t)))

    def _on_remove(self) -> None:
        self.done(self.VERIFIED)

    def password(self) -> str:
        return self._pw.text()
