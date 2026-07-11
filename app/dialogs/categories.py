"""Manage Categories dialog — rename and delete categories."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.models.vault import Vault


class CategoriesDialog(QDialog):
    def __init__(self, vault: Vault, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._vault = vault
        self.setWindowTitle("Manage Categories")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.MSWindowsFixedSizeDialogHint
        )
        self.setMinimumWidth(320)
        self._build_ui()
        self._refresh()

    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Manage Categories")
        title.setStyleSheet("font-size: 15px; font-weight: 700; color: #e8eaed;")
        layout.addWidget(title)

        self._list = QListWidget()
        self._list.setObjectName("CategoryList")
        layout.addWidget(self._list)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self._rename_btn = QPushButton("Rename")
        self._rename_btn.setObjectName("ToolbarButton")
        self._rename_btn.setEnabled(False)

        self._delete_btn = QPushButton("Delete")
        self._delete_btn.setObjectName("DeleteButton")
        self._delete_btn.setEnabled(False)

        close_btn = QPushButton("Close")
        close_btn.setProperty("flat", True)

        btn_row.addWidget(self._rename_btn)
        btn_row.addWidget(self._delete_btn)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        self._list.currentRowChanged.connect(self._on_selection_changed)
        self._rename_btn.clicked.connect(self._on_rename)
        self._delete_btn.clicked.connect(self._on_delete)
        close_btn.clicked.connect(self.accept)

    def _refresh(self) -> None:
        self._list.clear()
        for cat in self._vault.categories():
            self._list.addItem(QListWidgetItem(cat))

    def _on_selection_changed(self, row: int) -> None:
        enabled = row >= 0
        self._rename_btn.setEnabled(enabled)
        self._delete_btn.setEnabled(enabled)

    def _selected_category(self) -> str | None:
        item = self._list.currentItem()
        return item.text() if item else None

    def _on_rename(self) -> None:
        cat = self._selected_category()
        if not cat:
            return
        new_name, ok = QInputDialog.getText(
            self, "Rename Category", "New name:", text=cat
        )
        if ok and new_name.strip() and new_name.strip() != cat:
            self._vault.rename_category(cat, new_name.strip())
            self._refresh()

    def _on_delete(self) -> None:
        cat = self._selected_category()
        if not cat:
            return
        reply = QMessageBox.question(
            self,
            "Delete Category",
            f'Delete category "{cat}"?\n\nAll entries in this category will be moved to "General".',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._vault.delete_category(cat)
            self._refresh()
