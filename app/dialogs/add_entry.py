"""Add / Edit Entry dialog."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.models.entry import Entry
from app.models.vault import Vault


class AddEditEntryDialog(QDialog):
    """Modal dialog to create or edit a vault entry.

    Usage:
        dlg = AddEditEntryDialog(vault, parent=panel)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            entry, secret = dlg.result_entry()
    """

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
            | Qt.WindowType.MSWindowsFixedSizeDialogHint
        )
        self.setMinimumWidth(360)
        self._build_ui()
        if self._is_edit:
            self._populate(entry)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

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

        # Secret + show/hide toggle in one row
        self._secret_edit = QLineEdit()
        self._secret_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._secret_edit.setPlaceholderText(
            "Leave blank to keep existing" if self._is_edit else "Password / token / secret"
        )

        self._show_btn = QPushButton("Show")
        self._show_btn.setProperty("flat", True)
        self._show_btn.setFixedWidth(60)
        self._show_btn.setCheckable(True)
        self._show_btn.toggled.connect(self._toggle_secret_visibility)

        secret_row = QHBoxLayout()
        secret_row.setSpacing(6)
        secret_row.addWidget(self._secret_edit, stretch=1)
        secret_row.addWidget(self._show_btn)
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

        cat_row = QHBoxLayout()
        cat_row.setSpacing(6)

        self._cat_combo = QComboBox()
        self._cat_combo.setEditable(True)
        self._cat_combo.lineEdit().setPlaceholderText("Select or type a new category")
        self._cat_combo.lineEdit().textEdited.connect(self._sanitize_category)
        self._populate_categories()
        cat_row.addWidget(self._cat_combo, stretch=1)
        layout.addLayout(cat_row)

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
        idx = self._cat_combo.findText(entry.category)
        if idx >= 0:
            self._cat_combo.setCurrentIndex(idx)
        else:
            self._cat_combo.setCurrentText(entry.category)

    def _sanitize_category(self, text: str) -> None:
        if "," in text:
            cursor = self._cat_combo.lineEdit().cursorPosition()
            cleaned = text.replace(",", "")
            self._cat_combo.lineEdit().setText(cleaned)
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

    def _toggle_secret_visibility(self, checked: bool) -> None:
        mode = QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        self._secret_edit.setEchoMode(mode)
        self._show_btn.setText("Hide" if checked else "Show")

    def _on_save(self) -> None:
        name = self._name_edit.text().strip()
        username = self._user_edit.text().strip()
        secret = self._secret_edit.text()
        url = self._url_edit.text().strip()
        category = self._cat_combo.currentText().strip() or "General"
        tags = Entry.parse_tags(self._tags_edit.text())

        if not name:
            self._error_lbl.setText("Name is required.")
            return
        if not self._is_edit and not secret:
            self._error_lbl.setText("Secret is required.")
            return

        self._result_name = name
        self._result_username = username
        self._result_secret = secret
        self._result_url = url
        self._result_category = category
        self._result_tags = tags
        self.accept()

    # ------------------------------------------------------------------
    # Result
    # ------------------------------------------------------------------

    def result_entry(self) -> tuple[Entry, str]:
        """Call after exec() == Accepted.  Returns (Entry, secret_str)."""
        if self._is_edit:
            entry = Entry(
                id=self._existing_entry.id,
                name=self._result_name,
                username=self._result_username,
                category=self._result_category,
                tags=self._result_tags,
                url=self._result_url,
            )
        else:
            entry = Entry(
                name=self._result_name,
                username=self._result_username,
                category=self._result_category,
                tags=self._result_tags,
                url=self._result_url,
            )
        return entry, self._result_secret
