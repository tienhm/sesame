"""Add / Edit Entry dialog + inline Password Generator."""

from __future__ import annotations

import secrets
import string

from PySide6.QtCore import Qt
from app.utils.icons import FA
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.models.entry import Entry
from app.models.vault import Vault

_EYE_SHOW = FA.EYE
_EYE_HIDE = FA.EYE_SLASH
_GENERATE  = FA.DICE


class AddEditEntryDialog(QDialog):
    def __init__(
        self,
        vault: Vault,
        entry: Entry | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._vault = vault
        self._existing_entry = entry
        self._is_edit = entry is not None

        self.setWindowTitle("Edit Entry" if self._is_edit else "Add Entry")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setMinimumWidth(380)
        self._build_ui()
        if self._is_edit:
            self._populate(entry)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 16)

        title = QLabel("Edit Entry" if self._is_edit else "New Entry")
        title.setStyleSheet("font-size: 15px; font-weight: 700; color: #e8eaed;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Name
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. GitHub Token")
        form.addRow("Name *", self._name_edit)

        # Username
        self._user_edit = QLineEdit()
        self._user_edit.setPlaceholderText("e.g. john.doe@company.com")
        form.addRow("Username", self._user_edit)

        # Secret row: field + 👁 + 🎲
        self._secret_edit = QLineEdit()
        self._secret_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._secret_edit.setPlaceholderText(
            "Leave blank to keep existing" if self._is_edit
            else "Password / token / secret"
        )

        self._show_btn = QPushButton(_EYE_SHOW)
        self._show_btn.setObjectName("DialogIcon")
        self._show_btn.setFixedSize(32, 32)
        self._show_btn.setCheckable(True)
        self._show_btn.setToolTip("Show / hide secret")
        self._show_btn.toggled.connect(self._toggle_visibility)

        self._gen_btn = QPushButton(_GENERATE)
        self._gen_btn.setObjectName("DialogIcon")
        self._gen_btn.setFixedSize(32, 32)
        self._gen_btn.setToolTip("Generate password…")
        self._gen_btn.clicked.connect(self._open_generator)

        secret_row = QHBoxLayout()
        secret_row.setSpacing(4)
        secret_row.addWidget(self._secret_edit, stretch=1)
        secret_row.addWidget(self._show_btn)
        secret_row.addWidget(self._gen_btn)
        form.addRow("Secret *" if not self._is_edit else "Secret", secret_row)

        # URL
        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText("e.g. https://github.com")
        form.addRow("URL", self._url_edit)

        # Tags
        self._tags_edit = QLineEdit()
        self._tags_edit.setPlaceholderText("e.g. work, 2fa, vpn")
        form.addRow("Tags", self._tags_edit)

        layout.addLayout(form)

        # Category
        cat_label = QLabel("Category")
        cat_label.setStyleSheet("color: #adb5bd; font-size: 12px;")
        layout.addWidget(cat_label)

        self._cat_combo = QComboBox()
        self._cat_combo.setEditable(True)
        self._cat_combo.lineEdit().setPlaceholderText("Select or type a new category")
        self._cat_combo.lineEdit().textEdited.connect(self._sanitize_category)
        self._populate_categories()
        layout.addWidget(self._cat_combo)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setProperty("flat", True)
        self._cancel_btn.clicked.connect(self.reject)

        self._save_btn = QPushButton("Save")
        self._save_btn.setDefault(True)
        self._save_btn.clicked.connect(self._on_save)

        btn_row.addWidget(self._cancel_btn)
        btn_row.addWidget(self._save_btn)
        layout.addLayout(btn_row)

        self._error_lbl = QLabel("")
        self._error_lbl.setStyleSheet("color: #e74c3c; font-size: 11px;")
        self._error_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._error_lbl)

    def _populate(self, entry: Entry) -> None:
        self._name_edit.setText(entry.name)
        self._user_edit.setText(entry.username)
        self._url_edit.setText(entry.url)
        self._tags_edit.setText(", ".join(entry.tags))
        # Load existing secret so show/hide works immediately
        existing_secret = self._vault.get_secret(entry.id)
        if existing_secret:
            self._secret_edit.setText(existing_secret)
        idx = self._cat_combo.findText(entry.category)
        if idx >= 0:
            self._cat_combo.setCurrentIndex(idx)
        else:
            self._cat_combo.setCurrentText(entry.category)

    def _sanitize_category(self, text: str) -> None:
        if "," in text:
            cursor = self._cat_combo.lineEdit().cursorPosition()
            self._cat_combo.lineEdit().setText(text.replace(",", ""))
            self._cat_combo.lineEdit().setCursorPosition(max(0, cursor - 1))

    def _populate_categories(self) -> None:
        cats = self._vault.categories()
        for cat in cats:
            self._cat_combo.addItem(cat)
        if not cats:
            self._cat_combo.addItem("General")

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _toggle_visibility(self, checked: bool) -> None:
        self._secret_edit.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )
        self._show_btn.setText(_EYE_HIDE if checked else _EYE_SHOW)

    def _open_generator(self) -> None:
        dlg = PasswordGeneratorDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._secret_edit.setText(dlg.password())
            # Show the generated password
            self._show_btn.setChecked(True)

    def _on_save(self) -> None:
        name     = self._name_edit.text().strip()
        username = self._user_edit.text().strip()
        secret   = self._secret_edit.text()
        url      = self._url_edit.text().strip()
        category = self._cat_combo.currentText().strip() or "General"
        tags     = Entry.parse_tags(self._tags_edit.text())

        if not name:
            self._error_lbl.setText("Name is required.")
            return
        if not self._is_edit and not secret:
            self._error_lbl.setText("Secret is required.")
            return

        self._result_name     = name
        self._result_username = username
        self._result_secret   = secret
        self._result_url      = url
        self._result_category = category
        self._result_tags     = tags
        self.accept()

    # ------------------------------------------------------------------
    # Result
    # ------------------------------------------------------------------

    def result_entry(self) -> tuple[Entry, str]:
        kwargs = dict(
            name=self._result_name,
            username=self._result_username,
            category=self._result_category,
            tags=self._result_tags,
            url=self._result_url,
        )
        if self._is_edit:
            kwargs["id"] = self._existing_entry.id
        return Entry(**kwargs), self._result_secret


# ---------------------------------------------------------------------------
# Password Generator Dialog
# ---------------------------------------------------------------------------

class PasswordGeneratorDialog(QDialog):
    """Generate a random password with configurable options."""

    # Remembered across instances
    _last_length:  int  = 16
    _last_letters: bool = True
    _last_digits:  bool = True
    _last_special: bool = False

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Generate Password")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setMinimumWidth(340)
        self._build_ui()
        # Restore last-used options
        self._len_slider.setValue(PasswordGeneratorDialog._last_length)
        self._cb_letters.setChecked(PasswordGeneratorDialog._last_letters)
        self._cb_digits.setChecked(PasswordGeneratorDialog._last_digits)
        self._cb_special.setChecked(PasswordGeneratorDialog._last_special)
        self._regenerate()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 16)

        title = QLabel("Generate Password")
        title.setStyleSheet("font-size: 14px; font-weight: 700; color: #e8eaed;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        # Length
        len_row = QHBoxLayout()
        self._len_slider = QSlider(Qt.Orientation.Horizontal)
        self._len_slider.setRange(4, 64)
        self._len_slider.setValue(16)
        self._len_spin = QSpinBox()
        self._len_spin.setRange(4, 64)
        self._len_spin.setValue(16)
        self._len_spin.setFixedWidth(56)
        self._len_slider.valueChanged.connect(self._len_spin.setValue)
        self._len_spin.valueChanged.connect(self._len_slider.setValue)
        self._len_slider.valueChanged.connect(self._regenerate)
        len_row.addWidget(self._len_slider, stretch=1)
        len_row.addWidget(self._len_spin)
        form.addRow("Length:", len_row)

        # Options
        self._cb_letters = QCheckBox("Letters  (Aa–Zz)")
        self._cb_digits  = QCheckBox("Digits  (0–9)")
        self._cb_special = QCheckBox("Special  (!@#$…)")
        self._cb_letters.setChecked(True)
        self._cb_digits.setChecked(True)
        self._cb_special.setChecked(False)
        for cb in (self._cb_letters, self._cb_digits, self._cb_special):
            cb.toggled.connect(self._regenerate)
            form.addRow("", cb)

        layout.addLayout(form)

        # Preview
        preview_label = QLabel("Generated:")
        preview_label.setStyleSheet("color: #adb5bd; font-size: 12px;")
        layout.addWidget(preview_label)

        preview_row = QHBoxLayout()
        self._preview = QLineEdit()
        self._preview.setReadOnly(True)
        self._preview.setStyleSheet("font-family: monospace; font-size: 13px;")

        reroll_btn = QPushButton(FA.ROTATE)
        reroll_btn.setObjectName("DialogIcon")
        reroll_btn.setFixedSize(32, 32)
        reroll_btn.setToolTip("Regenerate")
        reroll_btn.clicked.connect(self._regenerate)

        preview_row.addWidget(self._preview, stretch=1)
        preview_row.addWidget(reroll_btn)
        layout.addLayout(preview_row)

        # Buttons
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        btns.button(QDialogButtonBox.StandardButton.Ok).setText("Use this password")
        btns.button(QDialogButtonBox.StandardButton.Cancel).setProperty("flat", True)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    # ------------------------------------------------------------------

    def _regenerate(self) -> None:
        length  = self._len_slider.value()
        letters = self._cb_letters.isChecked()
        digits  = self._cb_digits.isChecked()
        special = self._cb_special.isChecked()

        # Persist options for next open
        PasswordGeneratorDialog._last_length  = length
        PasswordGeneratorDialog._last_letters = letters
        PasswordGeneratorDialog._last_digits  = digits
        PasswordGeneratorDialog._last_special = special

        chars = ""
        if letters: chars += string.ascii_letters
        if digits:  chars += string.digits
        if special: chars += "!@#$%^&*()-_=+[]{}|;:,.<>?"
        if not chars:
            chars = string.ascii_lowercase
        self._preview.setText("".join(secrets.choice(chars) for _ in range(length)))

    def password(self) -> str:
        return self._preview.text()


