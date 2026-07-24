"""VaultPanel — the main expanded panel that opens from the bubble.

Layout:
  ┌──────────────────────────────────────┐
  │  🔍 Search...                         │
  ├───────────────┬──────────────────────┤
  │ Tag list      │ Entry list           │
  │  All          │  [Name]  [Username]  │
  │  #tag1        │  [👤] [🔑]           │
  │  #tag2        │                      │
  ├───────────────┴──────────────────────┤
  │  [+ Add]  [✎ Edit]  [🗑 Delete]      │
  └──────────────────────────────────────┘

Tag filter: click one tag → filter entries containing it.
Click multiple tags (Ctrl/Shift or just click more) → AND filter.
Click "All" → clear filter.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

from PySide6.QtCore import Qt, QPoint, QRectF, QTimer, QUrl, Signal
from PySide6.QtGui import (
    QColor, QCursor, QDesktopServices, QPainter, QPainterPath, QPixmap,
)
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.config import AppConfig
from app.dialogs.settings import UnlockDialog
from app.models.entry import Entry
from app.models.vault import Vault
from app.utils import auto_login
from app.utils.clipboard import ClipboardManager
from app.utils.lock_manager import LockManager

from app.utils.icons import FA

_COPY_USER = FA.USER
_EDIT      = FA.PEN
_COPY_PASS = FA.KEY

_PANEL_WIDTH = 480
_PANEL_HEIGHT = 430
_ALL_CATEGORIES = "All categories"


class EntryRowWidget(QWidget):
    """Custom widget rendered inside each QListWidgetItem."""

    copy_user_requested   = Signal(str)  # entry_id
    edit_row_requested    = Signal(str)  # entry_id
    copy_secret_requested = Signal(str)  # entry_id
    copy_otp_requested    = Signal(str)  # entry_id
    url_open_requested    = Signal(str)  # entry_id

    def __init__(self, entry: Entry, countdown: int | None = None, parent=None) -> None:
        super().__init__(parent)
        self.entry_id = entry.id
        self._has_username = bool(entry.username)
        self.setObjectName("EntryRow")
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAutoFillBackground(False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        # Text block: name + optional URL + tags
        text_block = QVBoxLayout()
        text_block.setSpacing(1)

        # Name row: name label + optional link icon inline
        name_row = QHBoxLayout()
        name_row.setSpacing(4)
        name_row.setContentsMargins(0, 0, 0, 0)

        name_lbl = QLabel(entry.name)
        name_lbl.setObjectName("EntryName")
        name_row.addWidget(name_lbl)

        if entry.url:
            link_btn = QPushButton(FA.LINK)
            link_btn.setObjectName("LinkButton")
            link_btn.setFixedSize(16, 16)
            link_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            link_btn.setToolTip(entry.url)
            link_btn.clicked.connect(lambda: self.url_open_requested.emit(self.entry_id))
            name_row.addWidget(link_btn)

        name_row.addStretch()
        text_block.addLayout(name_row)

        # OTP code display label (updated live by VaultPanel timer)
        self._otp_lbl = None
        if entry.has_otp:
            self._otp_lbl = QLabel("● ● ●")
            self._otp_lbl.setObjectName("OtpLabel")
            text_block.addWidget(self._otp_lbl)

        layout.addLayout(text_block, stretch=1)

        # Copy username button (only when username is set)
        if self._has_username:
            self._copy_user_btn = QPushButton(_COPY_USER)
            self._copy_user_btn.setObjectName("CopyButton")
            self._copy_user_btn.setFixedSize(26, 26)
            self._copy_user_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self._copy_user_btn.setToolTip("Copy username")
            self._copy_user_btn.clicked.connect(self._on_copy_user_clicked)

        # Copy secret button
        self._copy_btn = QPushButton(_COPY_PASS)
        self._copy_btn.setObjectName("CopyButton")
        self._copy_btn.setFixedSize(26, 26)
        self._copy_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._copy_btn.setToolTip("Copy password / secret")
        self._copy_btn.clicked.connect(lambda: self.copy_secret_requested.emit(self.entry_id))

        # OTP button (clock icon — click to copy)
        self._otp_btn = None
        if entry.has_otp:
            self._otp_btn = QPushButton(FA.CLOCK)
            self._otp_btn.setObjectName("CopyButton")
            self._otp_btn.setFixedSize(26, 26)
            self._otp_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self._otp_btn.setToolTip("Copy OTP code")
            self._otp_btn.clicked.connect(lambda: self.copy_otp_requested.emit(self.entry_id))

        # Edit button
        self._edit_btn = QPushButton(_EDIT)
        self._edit_btn.setObjectName("CopyButton")
        self._edit_btn.setFixedSize(26, 26)
        self._edit_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._edit_btn.setToolTip("Edit entry")
        self._edit_btn.clicked.connect(lambda: self.edit_row_requested.emit(self.entry_id))

        if countdown is not None:
            self._set_countdown(countdown)

        # Order: 🕐 OTP | 👤 user | 🔑 pass | ✏ edit
        if self._otp_btn:
            layout.addWidget(self._otp_btn)
        if self._has_username:
            layout.addWidget(self._copy_user_btn)
        layout.addWidget(self._copy_btn)
        layout.addWidget(self._edit_btn)

    def _on_copy_user_clicked(self) -> None:
        self.copy_user_requested.emit(self.entry_id)
        self._copy_user_btn.setText("✓")
        self._copy_user_btn.setProperty("copied", True)
        self._copy_user_btn.style().unpolish(self._copy_user_btn)
        self._copy_user_btn.style().polish(self._copy_user_btn)
        # Use a weak check so the timer doesn't resurrect an orphaned widget
        QTimer.singleShot(1500, lambda: self._reset_copy_user_btn() if self._copy_user_btn else None)

    def _reset_copy_user_btn(self) -> None:
        self._copy_user_btn.setText(_COPY_USER)
        self._copy_user_btn.setProperty("copied", False)
        self._copy_user_btn.style().unpolish(self._copy_user_btn)
        self._copy_user_btn.style().polish(self._copy_user_btn)

    def update_countdown(self, seconds: int) -> None:
        self._set_countdown(seconds)

    def reset_copy_button(self) -> None:
        self._copy_btn.setText(_COPY_PASS)
        self._copy_btn.setProperty("copied", False)
        self._copy_btn.style().unpolish(self._copy_btn)
        self._copy_btn.style().polish(self._copy_btn)

    # ------------------------------------------------------------------

    def _set_countdown(self, seconds: int) -> None:
        self._copy_btn.setText(f"{seconds}s")
        self._copy_btn.setProperty("copied", True)
        self._copy_btn.style().unpolish(self._copy_btn)
        self._copy_btn.style().polish(self._copy_btn)


class VaultPanel(QWidget):
    """Always-on-top frameless panel, anchored near the bubble."""

    # Signals that tray/main can connect to
    add_requested      = Signal()
    edit_requested     = Signal(str)   # entry_id
    delete_requested   = Signal(str)   # entry_id
    settings_requested = Signal()
    sponsor_requested  = Signal()
    quit_requested     = Signal()
    restore_requested  = Signal(QPoint)   # global center of the restore button

    def __init__(
        self,
        vault: Vault,
        clipboard: ClipboardManager,
        lock_manager: LockManager,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._vault = vault
        self._clipboard = clipboard
        self._lock_mgr = lock_manager
        self._selected_category: str = ""        # empty = All categories
        self._selected_tags: set[str] = set()    # empty = no tag filter
        self._row_widgets: dict[str, EntryRowWidget] = {}  # entry_id → widget
        self._drag_pos: QPoint | None = None
        self._caption_height: int = 34            # px — drag active only in this band

        self._bg_pixmap: QPixmap = QPixmap()
        self._bg_offset_x: float = 0.5
        self._bg_offset_y: float = 0.5

        self._setup_window()
        self._build_ui()
        self._connect_signals()
        self.refresh()

        # Timer to refresh OTP codes every 5 s
        self._otp_timer = QTimer(self)
        self._otp_timer.setInterval(1_000)
        self._otp_timer.timeout.connect(self._update_otp_buttons)
        self._otp_timer.start()

    # ------------------------------------------------------------------
    # Window setup
    # ------------------------------------------------------------------

    def _setup_window(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setObjectName("VaultPanel")
        self.setFixedSize(_PANEL_WIDTH, _PANEL_HEIGHT)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 10)
        root.setSpacing(8)

        # ── Caption bar ───────────────────────────────────────────────
        caption = QHBoxLayout()
        caption.setContentsMargins(2, 0, 0, 0)
        caption.setSpacing(4)

        try:
            from main import __version__ as _ver
            _caption = f"Sesame v{_ver}"
        except Exception:
            _caption = "Sesame"
        title_lbl = QLabel(_caption)
        title_lbl.setObjectName("CaptionTitle")
        caption.addWidget(title_lbl, stretch=1)

        self._restore_btn = QPushButton(FA.CIRCLE_DOT)
        self._restore_btn.setObjectName("ToolbarIcon")
        self._restore_btn.setFixedSize(24, 24)
        self._restore_btn.setToolTip("Back to bubble")
        caption.addWidget(self._restore_btn)

        root.addLayout(caption)

        # ── Body: left column (combo + tags) | right column (search + entries)
        body = QHBoxLayout()
        body.setSpacing(8)

        # Left column: category combo + tag list
        left = QVBoxLayout()
        left.setSpacing(4)
        left.setContentsMargins(0, 0, 0, 0)

        self._cat_combo = QComboBox()
        self._cat_combo.setObjectName("CategoryCombo")
        self._cat_combo.setFixedWidth(110)
        left.addWidget(self._cat_combo)

        self._tag_list = QListWidget()
        self._tag_list.setObjectName("TagList")
        self._tag_list.setFixedWidth(110)
        self._tag_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._tag_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        left.addWidget(self._tag_list, stretch=1)

        body.addLayout(left)

        # Right column: search bar (same row as combo) + entry list below
        right = QVBoxLayout()
        right.setSpacing(4)
        right.setContentsMargins(0, 0, 0, 0)

        self._search = QLineEdit()
        self._search.setObjectName("SearchBar")
        self._search.setPlaceholderText("Search secrets…")
        self._search.setClearButtonEnabled(True)
        right.addWidget(self._search)

        self._entry_list = QListWidget()
        self._entry_list.setObjectName("EntryList")
        self._entry_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._entry_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self._entry_list.setSpacing(2)
        self._entry_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self._entry_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        right.addWidget(self._entry_list, stretch=1)

        body.addLayout(right, stretch=1)

        root.addLayout(body, stretch=1)

        # ── Separator ─────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep)

        # ── Toolbar ───────────────────────────────────────────────────
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        self._add_btn = QPushButton("+ Add")
        self._add_btn.setObjectName("ToolbarButton")
        self._add_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self._del_btn = QPushButton("Delete")
        self._del_btn.setObjectName("DeleteButton")
        self._del_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._del_btn.setEnabled(False)

        self._sponsor_btn = QPushButton(FA.HEART)
        self._sponsor_btn.setObjectName("SponsorBtn")
        self._sponsor_btn.setFixedSize(28, 28)
        self._sponsor_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._sponsor_btn.setToolTip("Support Sesame")

        self._settings_btn = QPushButton(FA.GEAR)
        self._settings_btn.setObjectName("ToolbarIcon")
        self._settings_btn.setFixedSize(28, 28)
        self._settings_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._settings_btn.setToolTip("Settings")

        self._close_btn = QPushButton(FA.XMARK)
        self._close_btn.setObjectName("ToolbarIcon")
        self._close_btn.setFixedSize(28, 28)
        self._close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._close_btn.setToolTip("Close panel")

        toolbar.addWidget(self._add_btn)
        toolbar.addWidget(self._del_btn)
        toolbar.addStretch()
        toolbar.addWidget(self._sponsor_btn)
        toolbar.addWidget(self._settings_btn)
        toolbar.addWidget(self._close_btn)

        root.addLayout(toolbar)
        # Force layout to compute widget positions so mapTo() works before first show
        root.activate()

    def _connect_signals(self) -> None:
        self._search.textChanged.connect(self._apply_filter)
        self._cat_combo.currentIndexChanged.connect(self._on_category_changed)
        self._tag_list.itemClicked.connect(self._on_tag_clicked)
        self._entry_list.currentRowChanged.connect(self._on_entry_selection_changed)
        self._add_btn.clicked.connect(self.add_requested)
        self._del_btn.clicked.connect(self._on_delete_clicked)
        self._entry_list.model().rowsMoved.connect(self._on_rows_moved)
        self._sponsor_btn.clicked.connect(self.sponsor_requested)
        self._settings_btn.clicked.connect(self.settings_requested)
        self._restore_btn.clicked.connect(self._on_restore_clicked)
        self._close_btn.clicked.connect(self.hide)

        self._clipboard.countdown_tick.connect(self._on_countdown_tick)
        self._clipboard.cleared.connect(self._on_clipboard_cleared)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Reload all data from the vault and redraw."""
        self._rebuild_category_combo()
        self._rebuild_tags()
        self._rebuild_entries()

    def select_category(self, category: str) -> None:
        idx = self._cat_combo.findText(category)
        if idx >= 0:
            self._cat_combo.setCurrentIndex(idx)

    def _apply_component_opacity(self, opacity: float) -> None:
        a  = int(max(0.0, min(1.0, opacity)) * 255)
        # Selected items are 30% more opaque for clear visual feedback
        a2 = min(255, a + 76)
        if opacity >= 0.99:
            self.setStyleSheet("")
            vp_style = ""
        else:
            self.setStyleSheet(f"""
                QWidget        {{ background-color: transparent; }}
                #SearchBar     {{ background-color: rgba(46,47,58,{a}); }}
                #EntryList     {{ background-color: rgba(30,31,38,{a}); }}
                #TagList       {{ background-color: rgba(30,31,38,{a}); }}
                #TagList::item:selected  {{ background-color: rgba(61,62,79,{a2}); color: #5865f2; }}
                #EntryList::item:selected {{ background-color: rgba(61,62,79,{a2}); }}
                #CategoryCombo {{ background-color: rgba(46,47,58,{a}); }}
                #ToolbarButton {{ background-color: rgba(46,47,58,{a}); }}
                #DeleteButton  {{ background-color: rgba(46,47,58,{a}); }}
                #ToolbarIcon   {{ background-color: rgba(46,47,58,{a}); }}
                #CopyButton    {{ background-color: rgba(46,47,58,{a}); }}
            """)
            vp_style = f"background-color: rgba(30,31,38,{a});"

        for lw in self.findChildren(QListWidget):
            lw.viewport().setStyleSheet(vp_style)

    # ------------------------------------------------------------------
    # Caption drag
    # ------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        if (event.button() == Qt.MouseButton.LeftButton
                and event.position().y() < self._caption_height):
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_pos = None

    # ------------------------------------------------------------------

    def apply_appearance(self, config: AppConfig) -> None:
        bg_path = config.get("panel_bg_image", "")
        self._bg_pixmap = QPixmap(bg_path) if bg_path and os.path.exists(bg_path) else QPixmap()
        self._bg_offset_x = float(config.get("panel_bg_offset_x", 0.5))
        self._bg_offset_y = float(config.get("panel_bg_offset_y", 0.5))
        comp_opacity = float(config.get("panel_component_opacity", 1.0))
        self._apply_component_opacity(comp_opacity)
        self.repaint()

    # ------------------------------------------------------------------
    # Background rendering
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect())
        radius = 12.0

        clip = QPainterPath()
        clip.addRoundedRect(rect, radius, radius)
        painter.setClipPath(clip)

        if not self._bg_pixmap.isNull():
            scaled = self._bg_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = int((scaled.width()  - self.width())  * self._bg_offset_x)
            y = int((scaled.height() - self.height()) * self._bg_offset_y)
            painter.drawPixmap(0, 0, scaled, x, y, self.width(), self.height())
            painter.fillPath(clip, QColor(30, 31, 38, 160))
        else:
            painter.fillPath(clip, QColor("#25262f"))

        painter.setClipping(False)
        pen = painter.pen()
        pen.setColor(QColor("#3a3b47"))
        pen.setWidthF(1.0)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)
        painter.end()

    # ------------------------------------------------------------------
    # Category combo + tag list helpers
    # ------------------------------------------------------------------

    def _rebuild_category_combo(self) -> None:
        cats = sorted({e.category for e in self._vault.entries if e.category})
        self._cat_combo.blockSignals(True)
        self._cat_combo.clear()
        self._cat_combo.addItem(_ALL_CATEGORIES)
        for cat in cats:
            self._cat_combo.addItem(cat)
        idx = self._cat_combo.findText(self._selected_category or _ALL_CATEGORIES)
        self._cat_combo.setCurrentIndex(max(0, idx))
        self._cat_combo.blockSignals(False)

    def _on_category_changed(self, index: int) -> None:
        text = self._cat_combo.itemText(index)
        self._selected_category = "" if text == _ALL_CATEGORIES else text
        self._selected_tags = set()
        self._rebuild_tags()
        self._rebuild_entries()

    def _rebuild_tags(self) -> None:
        if self._selected_category:
            relevant = [e for e in self._vault.entries if e.category == self._selected_category]
        else:
            relevant = self._vault.entries
        all_tags = sorted({t for e in relevant for t in e.tags})

        self._tag_list.blockSignals(True)
        self._tag_list.clear()
        for tag in all_tags:
            self._tag_list.addItem(QListWidgetItem(tag))

        # Restore valid selected tags
        still_valid = set()
        for i in range(self._tag_list.count()):
            item = self._tag_list.item(i)
            if item.text() in self._selected_tags:
                item.setSelected(True)
                still_valid.add(item.text())
        self._selected_tags = still_valid
        self._tag_list.blockSignals(False)

    def _on_tag_clicked(self, item: QListWidgetItem) -> None:
        tag = item.text()
        if self._selected_tags == {tag}:
            # Clicking the already-selected tag → deselect → show all
            self._tag_list.clearSelection()
            self._selected_tags = set()
        else:
            self._selected_tags = {tag}
        self._rebuild_entries()

    # ------------------------------------------------------------------
    # Entry helpers
    # ------------------------------------------------------------------

    def _rebuild_entries(self) -> None:
        query = self._search.text().strip().lower()
        self._entry_list.clear()
        self._row_widgets.clear()

        active_id = self._clipboard.active_entry_id

        for entry in self._vault.entries:
            # Category filter
            if self._selected_category and entry.category != self._selected_category:
                continue
            # Tag AND filter: entry must contain ALL selected tags
            if self._selected_tags and not self._selected_tags.issubset(set(entry.tags)):
                continue
            if query and (
                query not in entry.name.lower()
                and query not in entry.username.lower()
                and not any(query in t.lower() for t in entry.tags)
            ):
                continue

            countdown = None
            if active_id == entry.id:
                countdown = (self._clipboard._remaining
                             if self._clipboard._remaining > 0 else None)

            row_widget = EntryRowWidget(entry, countdown)
            row_widget.copy_user_requested.connect(self._on_copy_user_requested)
            row_widget.edit_row_requested.connect(self.edit_requested)
            row_widget.copy_secret_requested.connect(self._on_copy_requested)
            row_widget.copy_otp_requested.connect(self._on_copy_otp_requested)
            row_widget.url_open_requested.connect(self._on_url_open_requested)
            self._row_widgets[entry.id] = row_widget

            item = QListWidgetItem(self._entry_list)
            item.setData(Qt.ItemDataRole.UserRole, entry.id)
            item.setSizeHint(row_widget.sizeHint())
            self._entry_list.addItem(item)
            self._entry_list.setItemWidget(item, row_widget)

        self._on_entry_selection_changed(self._entry_list.currentRow())
        self._update_otp_buttons()

    def _apply_filter(self) -> None:
        self._rebuild_entries()

    def _on_entry_selection_changed(self, row: int) -> None:
        self._del_btn.setEnabled(row >= 0)

    def _selected_entry_id(self) -> str | None:
        item = self._entry_list.currentItem()
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None

    # ------------------------------------------------------------------
    # Toolbar actions
    # ------------------------------------------------------------------

    def _on_restore_clicked(self) -> None:
        center = self._restore_btn.mapToGlobal(self._restore_btn.rect().center())
        self.restore_requested.emit(center)

    def _on_rows_moved(self) -> None:
        """Persist entry order after drag-drop reorder."""
        ordered_ids = [
            self._entry_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self._entry_list.count())
        ]
        self._vault.reorder_entries(ordered_ids)

    def _on_delete_clicked(self) -> None:
        eid = self._selected_entry_id()
        if eid:
            self.delete_requested.emit(eid)

    def _on_copy_user_requested(self, entry_id: str) -> None:
        entry = next((e for e in self._vault.entries if e.id == entry_id), None)
        if not entry or not entry.username:
            return
        if not self._ensure_unlocked(entry):
            return
        self._clipboard.copy_plain(entry.username)

    def _on_copy_requested(self, entry_id: str) -> None:
        entry = next((e for e in self._vault.entries if e.id == entry_id), None)
        if not entry:
            return
        if not self._ensure_unlocked(entry):
            return
        secret = self._vault.get_secret(entry_id) or ""
        self._clipboard.copy(entry_id, secret)

    def _on_copy_otp_requested(self, entry_id: str) -> None:
        entry = next((e for e in self._vault.entries if e.id == entry_id), None)
        if not entry or not entry.has_otp:
            return
        if not self._ensure_unlocked(entry):
            return
        try:
            import pyotp
            otp_secret = self._vault.get_otp_secret(entry_id)
            if not otp_secret:
                return
            totp = pyotp.TOTP(otp_secret)
            code = totp.now()
            self._clipboard.copy_plain(code)
            # Show ✓ briefly then restore clock icon
            widget = self._row_widgets.get(entry_id)
            if widget and widget._otp_btn:
                widget._otp_btn.setText("✓")
                widget._otp_btn.setProperty("copied", True)
                widget._otp_btn.style().unpolish(widget._otp_btn)
                widget._otp_btn.style().polish(widget._otp_btn)
                QTimer.singleShot(1500, lambda eid=entry_id: self._reset_otp_btn(eid))
        except Exception as e:
            logger.error("OTP generation failed: %s", e)

    def _reset_otp_btn(self, entry_id: str) -> None:
        widget = self._row_widgets.get(entry_id)
        if widget and widget._otp_btn:
            widget._otp_btn.setText(FA.CLOCK)
            widget._otp_btn.setProperty("copied", False)
            widget._otp_btn.style().unpolish(widget._otp_btn)
            widget._otp_btn.style().polish(widget._otp_btn)

    def _update_otp_buttons(self) -> None:
        """Refresh all visible OTP labels with current codes."""
        for entry_id, widget in self._row_widgets.items():
            if widget._otp_lbl:
                self._refresh_otp_code(entry_id, widget)

    def _refresh_otp_code(self, entry_id: str, widget) -> None:
        if not widget._otp_lbl:
            return
        try:
            import pyotp, time
            secret = self._vault.get_otp_secret(entry_id)
            if not secret:
                return
            totp = pyotp.TOTP(secret)
            code = totp.now()
            remaining = int(totp.interval - time.time() % totp.interval)
            # Display as "123 456  (28s)" — spaced for readability
            spaced = f"{code[:3]} {code[3:]}"
            widget._otp_lbl.setText(f"{spaced}  {remaining}s")
            if widget._otp_btn:
                widget._otp_btn.setToolTip(f"OTP: {code} — {remaining}s remaining\nClick to copy")
        except Exception:
            pass

    def _on_url_open_requested(self, entry_id: str) -> None:
        entry = next((e for e in self._vault.entries if e.id == entry_id), None)
        if not entry or not entry.url:
            return
        QDesktopServices.openUrl(QUrl(entry.url))
        if entry.auto_login_ms > 0:
            QTimer.singleShot(entry.auto_login_ms, lambda: self._do_auto_login(entry_id))

    def _do_auto_login(self, entry_id: str) -> None:
        entry = next((e for e in self._vault.entries if e.id == entry_id), None)
        if not entry:
            return
        if not self._ensure_unlocked(entry):
            return
        secret = self._vault.get_secret(entry_id) or ""
        auto_login.send_credentials(entry.username, secret)

    def _ensure_unlocked(self, entry: Entry) -> bool:
        if not self._lock_mgr.is_locked(entry.category):
            return True
        dlg = UnlockDialog(entry.category, self)
        while dlg.exec() == UnlockDialog.DialogCode.Accepted:
            if self._lock_mgr.unlock_session(dlg.password()):
                return True
            dlg.set_error("Wrong password.")
        return False

    # ------------------------------------------------------------------
    # Clipboard feedback
    # ------------------------------------------------------------------

    def _on_countdown_tick(self, entry_id: str, seconds: int) -> None:
        widget = self._row_widgets.get(entry_id)
        if widget:
            widget.update_countdown(seconds)

    def _on_clipboard_cleared(self, entry_id: str) -> None:
        widget = self._row_widgets.get(entry_id)
        if widget:
            widget.reset_copy_button()
