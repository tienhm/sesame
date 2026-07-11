"""Dialogs for Export and Import vault operations."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class _PasswordLineEdit(QLineEdit):
    """Password field with a show/hide toggle button."""

    def __init__(self, placeholder: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setEchoMode(QLineEdit.EchoMode.Password)
        self.setPlaceholderText(placeholder)
        self._toggle = QPushButton("👁", self)
        self._toggle.setFixedSize(28, 28)
        self._toggle.setFlat(True)
        self._toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle.setToolTip("Show / hide")
        self._toggle.clicked.connect(self._on_toggle)
        self.setTextMargins(0, 0, 32, 0)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._toggle.move(self.width() - 32, (self.height() - 28) // 2)

    def _on_toggle(self) -> None:
        if self.echoMode() == QLineEdit.EchoMode.Password:
            self.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.setEchoMode(QLineEdit.EchoMode.Password)


class ExportDialog(QDialog):
    """Ask the user for an export password (with confirmation)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Export Vault")
        self.setMinimumWidth(360)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        info = QLabel(
            "Choose a password to protect the export file.\n"
            "You will need it to import on another machine."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QFormLayout()
        self._pw = _PasswordLineEdit("Enter password")
        self._pw_confirm = _PasswordLineEdit("Confirm password")
        form.addRow("Password:", self._pw)
        form.addRow("Confirm:", self._pw_confirm)
        layout.addLayout(form)

        self._error = QLabel("")
        self._error.setStyleSheet("color: #e74c3c;")
        layout.addWidget(self._error)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self._ok_btn.setText("Export…")
        self._ok_btn.setEnabled(False)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._pw.textChanged.connect(self._validate)
        self._pw_confirm.textChanged.connect(self._validate)

    def _validate(self) -> None:
        pw = self._pw.text()
        confirm = self._pw_confirm.text()
        if not pw:
            self._error.setText("")
            self._ok_btn.setEnabled(False)
        elif confirm and pw != confirm:
            self._error.setText("Passwords do not match.")
            self._ok_btn.setEnabled(False)
        else:
            self._error.setText("")
            self._ok_btn.setEnabled(bool(pw) and pw == confirm)

    def _on_accept(self) -> None:
        if self._pw.text() == self._pw_confirm.text() and self._pw.text():
            self.accept()

    def password(self) -> str:
        return self._pw.text()


class ImportPasswordDialog(QDialog):
    """Ask for the password to decrypt an import file."""

    def __init__(self, file_path: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Import Vault")
        self.setMinimumWidth(360)
        self._build_ui(file_path)

    def _build_ui(self, file_path: str) -> None:
        layout = QVBoxLayout(self)

        info = QLabel(f"Enter the password for:\n<b>{file_path}</b>")
        info.setTextFormat(Qt.TextFormat.RichText)
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QFormLayout()
        self._pw = _PasswordLineEdit("Password")
        form.addRow("Password:", self._pw)
        layout.addLayout(form)

        self._error = QLabel("")
        self._error.setStyleSheet("color: #e74c3c;")
        layout.addWidget(self._error)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self._ok_btn.setText("Import")
        self._ok_btn.setEnabled(False)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._pw.textChanged.connect(lambda t: self._ok_btn.setEnabled(bool(t)))

    def set_error(self, msg: str) -> None:
        self._error.setText(msg)

    def password(self) -> str:
        return self._pw.text()
