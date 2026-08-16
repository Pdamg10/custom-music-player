from __future__ import annotations

import os
from typing import Any, Dict, List
from urllib.parse import unquote, urlparse

from PyQt6.QtCore import QModelIndex, QRect, QRectF, QSize, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QShowEvent,
)
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStyle,
    QStyleOptionViewItem,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
)


class SmallPlaylistDelegate(QStyledItemDelegate):
    """Delegado C++ ultraligero y libre de fugas para renderizar canciones en modo Pequeño."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        return QSize(option.rect.width(), 46)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        rect = option.rect
        is_selected = bool(option.state & QStyle.StateFlag.State_Selected)
        is_hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)

        bg_rect = rect.adjusted(1, 2, -1, -2)
        if is_selected:
            painter.setPen(QPen(QColor(255, 255, 255, 60), 1))
            painter.setBrush(QColor(255, 255, 255, 45))
        elif is_hovered:
            painter.setPen(QPen(QColor(255, 255, 255, 30), 1))
            painter.setBrush(QColor(255, 255, 255, 25))
        else:
            painter.setPen(QPen(QColor(255, 255, 255, 18), 1))
            painter.setBrush(QColor(10, 10, 18, 80))
        painter.drawRoundedRect(bg_rect, 10, 10)

        art_rect = QRect(bg_rect.left() + 6, bg_rect.top() + (bg_rect.height() - 34) // 2, 34, 34)
        art_path = index.data(Qt.ItemDataRole.UserRole + 3)
        pix: QPixmap | None = None
        if art_path and os.path.exists(art_path):
            from ui.expanded_view import get_cached_pixmap
            pix = get_cached_pixmap(art_path, 34, 34)

        if pix and not pix.isNull():
            path = QPainterPath()
            path.addRoundedRect(QRectF(art_rect), 7, 7)
            painter.save()
            painter.setClipPath(path)
            painter.drawPixmap(art_rect, pix)
            painter.restore()
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, 20))
            painter.drawRoundedRect(art_rect, 7, 7)
            painter.setPen(QColor(255, 255, 255, 180))
            painter.setFont(QFont("Sans Serif", 12))
            painter.drawText(art_rect, Qt.AlignmentFlag.AlignCenter, "♫")

        right_margin = bg_rect.right() - 8
        dur_str = index.data(Qt.ItemDataRole.UserRole + 2) or ""
        if dur_str:
            painter.setFont(QFont("Sans Serif", 8))
            painter.setPen(QColor(255, 255, 255, 130))
            metrics = QFontMetrics(painter.font())
            dur_width = metrics.horizontalAdvance(dur_str)
            dur_rect = QRect(right_margin - dur_width, bg_rect.top(), dur_width, bg_rect.height())
            painter.drawText(dur_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, dur_str)
            right_margin -= (dur_width + 8)

        if is_selected:
            painter.setFont(QFont("Sans Serif", 9))
            painter.setPen(QColor(255, 255, 255, 230))
            play_rect = QRect(right_margin - 12, bg_rect.top(), 12, bg_rect.height())
            painter.drawText(play_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter, "▶")
            right_margin -= 18

        text_left = art_rect.right() + 10
        text_width = max(10, right_margin - text_left)

        title_str = index.data(Qt.ItemDataRole.DisplayRole) or "Sin título"
        artist_str = index.data(Qt.ItemDataRole.UserRole + 1) or "Artista desconocido"

        painter.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold if is_selected else QFont.Weight.Normal))
        painter.setPen(QColor("#ffffff") if is_selected else QColor(255, 255, 255, 230))
        title_metrics = QFontMetrics(painter.font())
        elided_title = title_metrics.elidedText(title_str, Qt.TextElideMode.ElideRight, text_width)
        painter.drawText(text_left, bg_rect.top() + 16, elided_title)

        painter.setFont(QFont("Sans Serif", 8))
        painter.setPen(QColor(255, 255, 255, 150))
        artist_metrics = QFontMetrics(painter.font())
        elided_artist = artist_metrics.elidedText(artist_str, Qt.TextElideMode.ElideRight, text_width)
        painter.drawText(text_left, bg_rect.top() + 30, elided_artist)

        painter.restore()


class SmallPlaylistPage(QWidget):
    """Vista compacta de canciones exclusiva del modo Pequeño."""

    play_requested = pyqtSignal(int)
    close_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.playlist: List[Dict[str, Any]] = []
        self.current_index = -1
        self._dirty: bool = False
        self._rebuilding: bool = False

        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(80)
        self._debounce_timer.timeout.connect(self._on_debounce_timeout)

        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(8)

        title = QLabel("Canciones")
        title.setObjectName("SmallPlaylistTitle")
        title.setFont(QFont("Sans Serif", 12, QFont.Weight.Bold))
        header.addWidget(title)
        header.addStretch()

        self.count_label = QLabel("0")
        self.count_label.setObjectName("SmallPlaylistCount")
        header.addWidget(self.count_label)

        self.close_button = QPushButton("×")
        self.close_button.setObjectName("SmallPlaylistClose")
        self.close_button.setFixedSize(28, 28)
        self.close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_button.setToolTip("Volver al reproductor")
        self.close_button.clicked.connect(self.close_requested.emit)
        header.addWidget(self.close_button)
        root.addLayout(header)

        self.search = QLineEdit()
        self.search.setObjectName("SmallPlaylistSearch")
        self.search.setPlaceholderText("Buscar canción o artista…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter_items)
        root.addWidget(self.search)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("SmallPlaylistList")
        self.list_widget.setItemDelegate(SmallPlaylistDelegate(self.list_widget))
        self.list_widget.setSpacing(4)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        root.addWidget(self.list_widget, 1)

        self.empty_label = QLabel("No hay canciones para mostrar")
        self.empty_label.setObjectName("SmallPlaylistEmpty")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.hide()
        root.addWidget(self.empty_label)

        self.setStyleSheet(
            "QLabel#SmallPlaylistTitle { color: #ffffff; }"
            "QLabel#SmallPlaylistCount { color: rgba(255,255,255,0.62); font-size: 10px; }"
            "QPushButton#SmallPlaylistClose { background: rgba(25,28,44,0.70); color: #ffffff; border: 1px solid rgba(255,255,255,0.18); border-radius: 14px; font-size: 18px; padding: 0px; }"
            "QPushButton#SmallPlaylistClose:hover { background: rgba(255,255,255,0.18); }"
            "QLineEdit#SmallPlaylistSearch { background: rgba(8,8,14,0.48); color: #ffffff; border: 1px solid rgba(255,255,255,0.16); border-radius: 12px; padding: 6px 10px; selection-background-color: rgba(255,255,255,0.22); }"
            "QListWidget#SmallPlaylistList { background: transparent; border: none; outline: none; }"
            "QLabel#SmallPlaylistEmpty { color: rgba(255,255,255,0.60); }"
        )

    def set_playlist(self, playlist: list, current_index: int = -1) -> None:
        self.playlist = list(playlist or [])
        if current_index != -1 or self.current_index == -1:
            self.current_index = current_index
        self._dirty = True
        if self.isVisible():
            self._debounce_timer.start(80)

    def _on_debounce_timeout(self) -> None:
        if self.isVisible() and self._dirty:
            self._rebuild_items()

    def showEvent(self, event: QShowEvent | None) -> None:
        super().showEvent(event)
        if self._dirty:
            if self._debounce_timer.isActive():
                self._debounce_timer.stop()
            self._rebuild_items()

    def set_current_index(self, index: int) -> None:
        self.current_index = index
        if self.isVisible() and not self._dirty:
            self._mark_current()

    def _display_title(self, track: Dict[str, Any]) -> str:
        file_path = track.get("file_path", "")
        fallback = os.path.splitext(os.path.basename(file_path))[0] if file_path else "Sin título"
        return str(track.get("title") or track.get("name") or fallback)

    def _display_artist(self, track: Dict[str, Any]) -> str:
        return str(track.get("artist") or "Artista desconocido")

    def _display_duration(self, track: Dict[str, Any]) -> str:
        duration = track.get("length_sec", track.get("duration", track.get("duration_sec", 0)))
        try:
            seconds = int(float(duration or 0))
            if seconds > 10000:
                seconds //= 1000
            return f"{seconds // 60}:{seconds % 60:02d}" if seconds else ""
        except (TypeError, ValueError):
            return ""

    @staticmethod
    def _art_path(value: Any) -> str:
        if not isinstance(value, str) or not value:
            return ""
        if value.startswith("file://"):
            parsed = urlparse(value)
            return unquote(parsed.path)
        return value

    def _rebuild_items(self) -> None:
        if self._rebuilding:
            self._dirty = True
            return

        self._rebuilding = True
        self.list_widget.setUpdatesEnabled(False)
        try:
            self.list_widget.clear()
            for index, track in enumerate(self.playlist):
                item = QListWidgetItem()
                item.setData(Qt.ItemDataRole.UserRole, index)
                item.setData(Qt.ItemDataRole.DisplayRole, self._display_title(track))
                item.setData(Qt.ItemDataRole.UserRole + 1, self._display_artist(track))
                item.setData(Qt.ItemDataRole.UserRole + 2, self._display_duration(track))
                art_path = self._art_path(track.get("art_url") or track.get("cover_path") or track.get("album_art"))
                item.setData(Qt.ItemDataRole.UserRole + 3, art_path)
                item.setSizeHint(QSize(0, 46))
                self.list_widget.addItem(item)

            self.count_label.setText(str(len(self.playlist)))
            self.empty_label.setVisible(not bool(self.playlist))
            self.list_widget.setVisible(bool(self.playlist))
            self._dirty = False
            self._mark_current()
            self._filter_items(self.search.text())
        finally:
            self.list_widget.setUpdatesEnabled(True)
            self._rebuilding = False

    def _mark_current(self) -> None:
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            if item is None:
                continue
            index = item.data(Qt.ItemDataRole.UserRole)
            item.setSelected(index == self.current_index)
        self.list_widget.viewport().update()

    def _filter_items(self, query: str) -> None:
        query = (query or "").strip().lower()
        visible = 0
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            if item is None:
                continue
            index = item.data(Qt.ItemDataRole.UserRole)
            if not isinstance(index, int) or not 0 <= index < len(self.playlist):
                item.setHidden(True)
                continue
            track = self.playlist[index]
            haystack = f"{self._display_title(track)} {self._display_artist(track)}".lower()
            hidden = bool(query and query not in haystack)
            item.setHidden(hidden)
            if not hidden:
                visible += 1

        self.empty_label.setText("No se encontraron canciones" if query and not visible else "No hay canciones para mostrar")
        self.empty_label.setVisible(visible == 0)
        self.list_widget.setVisible(visible > 0)

    def _on_item_clicked(self, item: QListWidgetItem | None) -> None:
        if item is None:
            return
        index = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(index, int):
            self.current_index = index
            self.play_requested.emit(index)
            self._mark_current()
