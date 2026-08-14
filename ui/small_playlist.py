from __future__ import annotations

import os
from typing import Any, Dict, List
from urllib.parse import unquote, urlparse

from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QShowEvent
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


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
            "QListWidget#SmallPlaylistList::item { background: rgba(10,10,18,0.32); color: #ffffff; border: 1px solid rgba(255,255,255,0.07); border-radius: 11px; padding: 6px; }"
            "QListWidget#SmallPlaylistList::item:hover { background: rgba(255,255,255,0.10); }"
            "QListWidget#SmallPlaylistList::item:selected { background: rgba(255,255,255,0.16); border: 1px solid rgba(255,255,255,0.24); }"
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

    def _make_item_widget(self, track: Dict[str, Any]) -> QWidget:
        row = QFrame()
        row.setObjectName("SmallPlaylistRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(4, 3, 6, 3)
        layout.setSpacing(9)

        art = QLabel()
        art.setFixedSize(38, 38)
        art.setAlignment(Qt.AlignmentFlag.AlignCenter)
        art_path = self._art_path(track.get("art_url") or track.get("cover_path") or track.get("album_art"))
        if art_path and os.path.exists(art_path):
            pix = QPixmap(art_path)
            if not pix.isNull():
                art.setPixmap(pix.scaled(38, 38, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
        else:
            art.setText("♫")
            art.setStyleSheet("background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.70); border-radius: 9px; border: none; font-size: 16px;")
        layout.addWidget(art)

        info = QVBoxLayout()
        info.setSpacing(0)
        title = QLabel(self._display_title(track))
        title.setStyleSheet("color: #ffffff; font-size: 10px; font-weight: 600; border: none; background: transparent;")
        artist = QLabel(self._display_artist(track))
        artist.setStyleSheet("color: rgba(255,255,255,0.58); font-size: 8px; border: none; background: transparent;")
        info.addWidget(title)
        info.addWidget(artist)
        layout.addLayout(info, 1)

        duration = self._display_duration(track)
        if duration:
            time = QLabel(duration)
            time.setStyleSheet("color: rgba(255,255,255,0.48); font-size: 8px; border: none; background: transparent;")
            layout.addWidget(time)

        play = QLabel("▶")
        play.setStyleSheet("color: rgba(255,255,255,0.72); font-size: 10px; border: none; background: transparent;")
        layout.addWidget(play)
        return row

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
                widget = self._make_item_widget(track)
                item.setSizeHint(widget.sizeHint())
                self.list_widget.addItem(item)
                self.list_widget.setItemWidget(item, widget)

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
            index = item.data(Qt.ItemDataRole.UserRole)
            item.setSelected(index == self.current_index)

    def _filter_items(self, query: str) -> None:
        query = (query or "").strip().lower()
        visible = 0
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
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

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        index = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(index, int):
            self.current_index = index
            self.play_requested.emit(index)
            self._mark_current()
