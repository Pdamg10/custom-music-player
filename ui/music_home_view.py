import datetime
import os
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import QPoint, QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from database_manager import get_database_manager
from library_manager import UNKNOWN_ALBUM, UNKNOWN_ARTIST


def get_contrast_color(hex_color: str) -> str:
    """Calcula si el texto debe ser blanco o negro según el brillo del fondo."""
    clean = hex_color.split(";")[0].strip().lstrip("#")
    if len(clean) != 6:
        return "#ffffff"
    try:
        r = int(clean[0:2], 16)
        g = int(clean[2:4], 16)
        b = int(clean[4:6], 16)
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
        return "#000000" if luminance > 0.60 else "#ffffff"
    except Exception:
        return "#ffffff"


def format_duration(seconds: int) -> str:
    if seconds <= 0:
        return "--:--"
    m = seconds // 60
    s = seconds % 60
    return f"{m}:{s:02d}"


# ═════════════════════════════════════════════════════════════════════════════
# TARJETAS DE ENTIDADES (Canción / Artista / Álbum / Playlist)
# ═════════════════════════════════════════════════════════════════════════════


class MediaCard(QFrame):
    """Tarjeta individual estándar con carátula cuadrada, título y artista/subtítulo."""

    CARD_WIDTH: int = 160
    CARD_HEIGHT: int = 215

    clicked = pyqtSignal(dict)

    def __init__(
        self,
        data: Dict[str, Any],
        title: str,
        subtitle: str,
        art_url: str = "",
        badge: str = "",
        accent_color: str = "#ff1744",
        is_circular: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.data = data
        self.accent_color = accent_color
        self.is_circular = is_circular

        self.setFixedSize(self.CARD_WIDTH, self.CARD_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        clean_accent = accent_color.split(";")[0].strip() or "#ff1744"
        qc = QColor(clean_accent)
        if not qc.isValid():
            qc = QColor("#ff1744")
        r, g, b = qc.red(), qc.green(), qc.blue()

        self.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(14, 18, 30, 0.70);
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.08);
            }}
            QFrame:hover {{
                background-color: rgba({r}, {g}, {b}, 0.22);
                border: 1.5px solid {clean_accent};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # 1. Contenedor de Portada / Avatar
        self.art_container = QLabel(self)
        self.art_container.setFixedSize(140, 140)
        self.art_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.art_container.setStyleSheet(
            "border-radius: 12px; background-color: #0b0d17;"
        )

        pixmap = self._load_pixmap(art_url, title, is_circular)
        self.art_container.setPixmap(pixmap)
        layout.addWidget(self.art_container)

        # 2. Título principal
        lbl_title = QLabel(title or "Sin título", self)
        lbl_title.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        lbl_title.setStyleSheet(
            "color: #ffffff; border: none; background: transparent;"
        )
        lbl_title.setToolTip(title)
        layout.addWidget(lbl_title)

        # 3. Subtítulo (Artista o Conteo)
        lbl_sub = QLabel(subtitle or "", self)
        lbl_sub.setFont(QFont("Sans Serif", 8))
        lbl_sub.setStyleSheet(
            "color: rgba(255, 255, 255, 0.65); border: none; background: transparent;"
        )
        lbl_sub.setToolTip(subtitle)
        layout.addWidget(lbl_sub)

        layout.addStretch(1)

    def _load_pixmap(self, art_url: str, text: str, is_circular: bool) -> QPixmap:
        """Carga y redondea la carátula o genera un placeholder estilizado."""
        size = 140
        final_pixmap = QPixmap(size, size)
        final_pixmap.fill(Qt.GlobalColor.transparent)

        source_pixmap = None
        if art_url and os.path.exists(
            art_url.replace("file://", "")
            if art_url.startswith("file://")
            else art_url
        ):
            clean_path = (
                art_url.replace("file://", "")
                if art_url.startswith("file://")
                else art_url
            )
            source_pixmap = QPixmap(clean_path)

        painter = QPainter(final_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        if is_circular:
            path.addEllipse(0, 0, size, size)
        else:
            path.addRoundedRect(QRectF(0, 0, size, size), 12.0, 12.0)

        painter.setClipPath(path)

        if source_pixmap and not source_pixmap.isNull():
            scaled = source_pixmap.scaled(
                size,
                size,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            sx = int((size - scaled.width()) / 2)
            sy = int((size - scaled.height()) / 2)
            painter.drawPixmap(sx, sy, scaled)
        else:
            # Placeholder estético degradado con iniciales o icono
            qc = QColor(self.accent_color.split(";")[0].strip() or "#ff1744")
            grad = QLinearGradient(0, 0, size, size)
            grad.setColorAt(0.0, QColor(qc.red() // 3, qc.green() // 3, qc.blue() // 3, 220))
            grad.setColorAt(1.0, QColor(16, 20, 36, 240))
            painter.fillPath(path, QBrush(grad))

            painter.setPen(QColor(255, 255, 255, 180))
            painter.setFont(QFont("Sans Serif", 24, QFont.Weight.Bold))
            initial = (text[:2] if len(text) >= 2 else text).upper() if text else "🎵"
            painter.drawText(
                QRectF(0, 0, size, size),
                Qt.AlignmentFlag.AlignCenter,
                initial,
            )

        painter.end()
        return final_pixmap

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.data)
        super().mousePressEvent(event)


class CreatePlaylistCard(QFrame):
    """Tarjeta interactiva para crear una nueva playlist (+ Crear nueva lista)."""

    create_requested = pyqtSignal()

    def __init__(
        self, accent_color: str = "#ff1744", parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.accent_color = accent_color
        self.setFixedSize(MediaCard.CARD_WIDTH, MediaCard.CARD_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        clean_accent = accent_color.split(";")[0].strip() or "#ff1744"
        qc = QColor(clean_accent)
        r, g, b = qc.red(), qc.green(), qc.blue()

        self.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(14, 18, 30, 0.40);
                border-radius: 16px;
                border: 2px dashed rgba({r}, {g}, {b}, 0.50);
            }}
            QFrame:hover {{
                background-color: rgba({r}, {g}, {b}, 0.20);
                border: 2px solid {clean_accent};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)

        lbl_icon = QLabel("+", self)
        lbl_icon.setFont(QFont("Sans Serif", 38, QFont.Weight.Light))
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setStyleSheet(
            f"color: {clean_accent}; border: none; background: transparent;"
        )
        layout.addWidget(lbl_icon)

        lbl_text = QLabel("Crear nueva\nlista", self)
        lbl_text.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_text.setStyleSheet(
            "color: #ffffff; border: none; background: transparent;"
        )
        layout.addWidget(lbl_text)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.create_requested.emit()
        super().mousePressEvent(event)


class EmptyStateWidget(QFrame):
    """Contenedor elegante para estados sin datos o vacíos."""

    def __init__(
        self,
        icon: str,
        message: str,
        submessage: str = "",
        height: int = 140,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setFixedHeight(height)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(12, 16, 28, 0.50);
                border-radius: 14px;
                border: 1px solid rgba(255, 255, 255, 0.06);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(4)

        lbl_icon = QLabel(icon, self)
        lbl_icon.setFont(QFont("Sans Serif", 22))
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(lbl_icon)

        lbl_msg = QLabel(message, self)
        lbl_msg.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        lbl_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_msg.setStyleSheet(
            "color: rgba(255, 255, 255, 0.85); border: none; background: transparent;"
        )
        layout.addWidget(lbl_msg)

        if submessage:
            lbl_sub = QLabel(submessage, self)
            lbl_sub.setFont(QFont("Sans Serif", 8))
            lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_sub.setStyleSheet(
                "color: rgba(255, 255, 255, 0.45); border: none; background: transparent;"
            )
            layout.addWidget(lbl_sub)


# ═════════════════════════════════════════════════════════════════════════════
# DIÁLOGOS (Crear Playlist / Añadir Canción)
# ═════════════════════════════════════════════════════════════════════════════


class CreatePlaylistDialog(QDialog):
    """Diálogo modal moderno para crear una playlist."""

    def __init__(
        self, accent_color: str = "#ff1744", parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.accent_color = accent_color
        self.setWindowTitle("Nueva Lista de Reproducción")
        self.setFixedSize(360, 190)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        clean_accent = accent_color.split(";")[0].strip() or "#ff1744"
        contrast = get_contrast_color(clean_accent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        frame = QFrame(self)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: #0d111d;
                border-radius: 18px;
                border: 1.5px solid {clean_accent};
            }}
        """)
        f_layout = QVBoxLayout(frame)
        f_layout.setContentsMargins(20, 18, 20, 18)
        f_layout.setSpacing(12)

        lbl_title = QLabel("Crear Lista de Reproducción", frame)
        lbl_title.setFont(QFont("Sans Serif", 11, QFont.Weight.Bold))
        lbl_title.setStyleSheet(
            "color: #ffffff; border: none; background: transparent;"
        )
        f_layout.addWidget(lbl_title)

        self.input_name = QLineEdit(frame)
        self.input_name.setPlaceholderText("Nombre de la lista...")
        self.input_name.setFixedHeight(38)
        self.input_name.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.08);
                color: #ffffff;
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 0.15);
                padding: 4px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1.5px solid #00e5ff;
            }
        """)
        f_layout.addWidget(self.input_name)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch(1)

        btn_cancel = QPushButton("Cancelar", frame)
        btn_cancel.setFixedHeight(34)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.10);
                color: #ffffff;
                border-radius: 10px;
                padding: 4px 14px;
                font-size: 12px;
                font-weight: bold;
                border: 1px solid rgba(255, 255, 255, 0.15);
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.20);
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_create = QPushButton("Crear", frame)
        btn_create.setFixedHeight(34)
        btn_create.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_create.setStyleSheet(f"""
            QPushButton {{
                background-color: {clean_accent};
                color: {contrast};
                border-radius: 10px;
                padding: 4px 16px;
                font-size: 12px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                opacity: 0.90;
            }}
        """)
        btn_create.clicked.connect(self._on_create)
        btn_layout.addWidget(btn_create)

        f_layout.addLayout(btn_layout)
        main_layout.addWidget(frame)

    def _on_create(self) -> None:
        if self.input_name.text().strip():
            self.accept()

    def get_playlist_name(self) -> str:
        return self.input_name.text().strip()


# ═════════════════════════════════════════════════════════════════════════════
# VISTA DE DETALLE DE PLAYLIST (PlaylistDetailView)
# ═════════════════════════════════════════════════════════════════════════════


class PlaylistDetailView(QWidget):
    """Vista completa del contenido de una playlist personalizada con controles de gestión."""

    back_requested = pyqtSignal()
    play_track_requested = pyqtSignal(dict)
    play_all_requested = pyqtSignal(list)
    playlist_deleted = pyqtSignal(int)
    playlist_updated = pyqtSignal()

    def __init__(
        self,
        accent_color: str = "#ff1744",
        audio_engine: Optional[Any] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.accent_color = accent_color
        self.audio_engine = audio_engine
        self.playlist_id: Optional[int] = None
        self.playlist_name: str = ""
        self.tracks: List[Dict[str, Any]] = []
        self.db = get_database_manager()

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # 1. Barra de Cabecera con Botón Volver y Acciones
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        self.btn_back = QPushButton("← Volver a Música", self)
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                color: #ffffff;
                border-radius: 12px;
                padding: 6px 14px;
                font-weight: bold;
                font-size: 12px;
                border: 1px solid rgba(255, 255, 255, 0.12);
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.18);
            }
        """)
        self.btn_back.clicked.connect(self.back_requested.emit)
        header_layout.addWidget(self.btn_back)

        header_layout.addStretch(1)

        self.btn_play_all = QPushButton("▶ Reproducir Todo", self)
        self.btn_play_all.setCursor(Qt.CursorShape.PointingHandCursor)
        clean_accent = self.accent_color.split(";")[0].strip() or "#ff1744"
        contrast = get_contrast_color(clean_accent)
        self.btn_play_all.setStyleSheet(f"""
            QPushButton {{
                background-color: {clean_accent};
                color: {contrast};
                border-radius: 12px;
                padding: 6px 16px;
                font-weight: bold;
                font-size: 12px;
                border: none;
            }}
            QPushButton:hover {{
                opacity: 0.90;
            }}
        """)
        self.btn_play_all.clicked.connect(self._on_play_all)
        header_layout.addWidget(self.btn_play_all)

        self.btn_delete_pl = QPushButton("🗑 Eliminar Lista", self)
        self.btn_delete_pl.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete_pl.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 23, 68, 0.15);
                color: #ff5252;
                border-radius: 12px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 12px;
                border: 1px solid rgba(255, 23, 68, 0.30);
            }
            QPushButton:hover {
                background-color: rgba(255, 23, 68, 0.30);
            }
        """)
        self.btn_delete_pl.clicked.connect(self._on_delete_playlist)
        header_layout.addWidget(self.btn_delete_pl)

        layout.addLayout(header_layout)

        # 2. Tarjeta Banner de la Playlist
        banner_frame = QFrame(self)
        banner_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(14, 18, 30, 0.65);
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.08);
            }
        """)
        banner_layout = QHBoxLayout(banner_frame)
        banner_layout.setContentsMargins(18, 16, 18, 16)
        banner_layout.setSpacing(16)

        lbl_icon = QLabel("📋", banner_frame)
        lbl_icon.setFont(QFont("Sans Serif", 32))
        banner_layout.addWidget(lbl_icon)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        self.lbl_pl_title = QLabel("Nombre de Lista", banner_frame)
        self.lbl_pl_title.setFont(QFont("Sans Serif", 14, QFont.Weight.Bold))
        self.lbl_pl_title.setStyleSheet("color: #ffffff;")
        info_layout.addWidget(self.lbl_pl_title)

        self.lbl_pl_stats = QLabel("0 canciones", banner_frame)
        self.lbl_pl_stats.setFont(QFont("Sans Serif", 9))
        self.lbl_pl_stats.setStyleSheet("color: rgba(255, 255, 255, 0.60);")
        info_layout.addWidget(self.lbl_pl_stats)

        banner_layout.addLayout(info_layout, stretch=1)
        layout.addWidget(banner_frame)

        # 3. Lista de Canciones con Scroll
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
        )

        self.scroll_content = QWidget()
        self.tracks_layout = QVBoxLayout(self.scroll_content)
        self.tracks_layout.setContentsMargins(0, 0, 0, 0)
        self.tracks_layout.setSpacing(6)

        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area, stretch=1)

    def update_accent_color(self, accent_color: str) -> None:
        self.accent_color = accent_color
        clean_accent = accent_color.split(";")[0].strip() or "#ff1744"
        contrast = get_contrast_color(clean_accent)
        if hasattr(self, 'btn_play_all') and self.btn_play_all:
            self.btn_play_all.setStyleSheet(f"""
                QPushButton {{
                    background-color: {clean_accent};
                    color: {contrast};
                    border-radius: 12px;
                    padding: 6px 16px;
                    font-weight: bold;
                    font-size: 12px;
                    border: none;
                }}
                QPushButton:hover {{
                    opacity: 0.90;
                }}
            """)
        if self.playlist_id is not None:
            self.load_playlist(self.playlist_id, self.playlist_name)

    def load_playlist(self, playlist_id: int, playlist_name: str) -> None:
        self.playlist_id = playlist_id
        self.playlist_name = playlist_name
        self.lbl_pl_title.setText(playlist_name)

        self.tracks = self.db.get_playlist_tracks(playlist_id)
        count = len(self.tracks)
        self.lbl_pl_stats.setText(f"{count} canciones")

        # Limpiar lista anterior
        while self.tracks_layout.count():
            child = self.tracks_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not self.tracks:
            empty = EmptyStateWidget(
                "🎵",
                "Esta lista está vacía",
                "Agrega canciones para disfrutarlas aquí",
            )
            self.tracks_layout.addWidget(empty)
            self.tracks_layout.addStretch(1)
            return

        clean_accent = self.accent_color.split(";")[0].strip() or "#ff1744"

        for idx, track in enumerate(self.tracks):
            row = QFrame(self.scroll_content)
            row.setFixedHeight(50)
            row.setCursor(Qt.CursorShape.PointingHandCursor)
            row.setStyleSheet("""
                QFrame {
                    background-color: rgba(14, 18, 30, 0.50);
                    border-radius: 10px;
                    border: 1px solid rgba(255, 255, 255, 0.05);
                }
                QFrame:hover {
                    background-color: rgba(255, 255, 255, 0.12);
                    border: 1px solid rgba(255, 255, 255, 0.20);
                }
            """)

            r_layout = QHBoxLayout(row)
            r_layout.setContentsMargins(12, 0, 12, 0)
            r_layout.setSpacing(12)

            # Número de pista
            lbl_num = QLabel(str(idx + 1), row)
            lbl_num.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
            lbl_num.setFixedWidth(24)
            lbl_num.setStyleSheet("color: rgba(255, 255, 255, 0.50);")
            r_layout.addWidget(lbl_num)

            # Título y Artista
            t_layout = QVBoxLayout()
            t_layout.setSpacing(2)
            t_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

            title_str = track.get("title") or "Sin título"
            artist_str = track.get("artist") or UNKNOWN_ARTIST

            lbl_t = QLabel(title_str, row)
            lbl_t.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
            lbl_t.setStyleSheet("color: #ffffff;")
            t_layout.addWidget(lbl_t)

            lbl_a = QLabel(artist_str, row)
            lbl_a.setFont(QFont("Sans Serif", 8))
            lbl_a.setStyleSheet("color: rgba(255, 255, 255, 0.60);")
            t_layout.addWidget(lbl_a)
            r_layout.addLayout(t_layout, stretch=1)

            # Álbum
            album_str = track.get("album") or ""
            if album_str and album_str != UNKNOWN_ALBUM:
                lbl_alb = QLabel(album_str, row)
                lbl_alb.setFont(QFont("Sans Serif", 8))
                lbl_alb.setStyleSheet("color: rgba(255, 255, 255, 0.45);")
                lbl_alb.setFixedWidth(140)
                r_layout.addWidget(lbl_alb)

            # Duración
            dur_sec = int(track.get("length_sec") or 0)
            lbl_dur = QLabel(format_duration(dur_sec), row)
            lbl_dur.setFont(QFont("Sans Serif", 8))
            lbl_dur.setStyleSheet("color: rgba(255, 255, 255, 0.50);")
            r_layout.addWidget(lbl_dur)

            # Botón Quitar de la playlist
            btn_remove = QPushButton("✕", row)
            btn_remove.setFixedSize(26, 26)
            btn_remove.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_remove.setToolTip("Quitar de la lista")
            btn_remove.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: rgba(255, 255, 255, 0.40);
                    border-radius: 13px;
                    font-size: 11px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: rgba(255, 23, 68, 0.30);
                    color: #ff5252;
                }
            """)
            track_id = track.get("track_id", "")
            btn_remove.clicked.connect(
                lambda checked, tid=track_id: self._on_remove_track(tid)
            )
            r_layout.addWidget(btn_remove)

            # Clic en fila para reproducir
            def make_click_handler(t_dict):
                def _handler(event):
                    if event.button() == Qt.MouseButton.LeftButton:
                        self.play_track_requested.emit(t_dict)

                return _handler

            row.mousePressEvent = make_click_handler(track)
            self.tracks_layout.addWidget(row)

        self.tracks_layout.addStretch(1)

    def _on_remove_track(self, track_id: str) -> None:
        if self.playlist_id is not None:
            self.db.remove_track_from_playlist(self.playlist_id, track_id)
            self.load_playlist(self.playlist_id, self.playlist_name)
            self.playlist_updated.emit()

    def _on_play_all(self) -> None:
        if self.tracks:
            self.play_all_requested.emit(self.tracks)

    def _on_delete_playlist(self) -> None:
        if self.playlist_id is None:
            return

        reply = QMessageBox.question(
            self,
            "Eliminar Lista",
            f"¿Estás seguro de eliminar la lista '{self.playlist_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            pl_id = self.playlist_id
            self.db.delete_playlist(pl_id)
            self.playlist_deleted.emit(pl_id)
            self.back_requested.emit()


# ═════════════════════════════════════════════════════════════════════════════
# GRID REUTILIZABLE DE PLAYLISTS (PlaylistsGridView)
# ═════════════════════════════════════════════════════════════════════════════


class PlaylistsGridView(QWidget):
    """Grid responsivo reutilizable de playlists con botón de crear y tarjetas de playlists."""

    playlist_clicked = pyqtSignal(dict)
    create_playlist_requested = pyqtSignal()

    def __init__(
        self,
        accent_color: str = "#ff1744",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.accent_color = accent_color
        self.db = get_database_manager()
        self._current_cols: int = 5

        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(90)
        self._resize_timer.timeout.connect(self._handle_debounced_resize)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        self.grid_layout = QGridLayout()
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(14)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addLayout(self.grid_layout)

    def set_accent_color(self, accent_color: str) -> None:
        self.accent_color = accent_color
        self.refresh()

    def _calculate_cols(self) -> int:
        card_w = MediaCard.CARD_WIDTH
        spacing = 14
        w = 0
        if self.width() > 50:
            w = self.width()
        elif self.parentWidget() and self.parentWidget().width() > 50:
            w = self.parentWidget().width() - 30
        else:
            w = 700

        return max(2, min(8, int((w + spacing) / (card_w + spacing))))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._resize_timer.start()

    def _handle_debounced_resize(self) -> None:
        new_cols = self._calculate_cols()
        if self._current_cols != new_cols:
            self._re_layout_grid(new_cols)

    def _re_layout_grid(self, cols: int) -> None:
        self._current_cols = cols
        widgets = []
        for i in range(self.grid_layout.count()):
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                widgets.append(item.widget())

        for w in widgets:
            self.grid_layout.removeWidget(w)

        for idx, w in enumerate(widgets):
            row = idx // cols
            col = idx % cols
            self.grid_layout.addWidget(w, row, col)

    def refresh(self) -> None:
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        cols = self._calculate_cols()
        self._current_cols = cols

        # 1. Tarjeta inicial para crear playlist
        create_card = CreatePlaylistCard(accent_color=self.accent_color, parent=self)
        create_card.create_requested.connect(self.create_playlist_requested.emit)
        self.grid_layout.addWidget(create_card, 0, 0)

        # 2. Playlists del usuario
        playlists = self.db.get_playlists_summary()
        for idx, pl in enumerate(playlists):
            grid_idx = idx + 1
            row = grid_idx // cols
            col = grid_idx % cols

            count = pl.get("track_count", 0)
            card = MediaCard(
                data=pl,
                title=pl.get("name", "Lista"),
                subtitle=f"{count} canciones",
                art_url="",
                accent_color=self.accent_color,
                parent=self,
            )
            card.clicked.connect(self.playlist_clicked.emit)
            self.grid_layout.addWidget(card, row, col)


# ═════════════════════════════════════════════════════════════════════════════
# VISTA DEDICADA DE LISTAS (PlaylistsPageView)
# ═════════════════════════════════════════════════════════════════════════════


class PlaylistsPageView(QWidget):
    """Vista dedicada exclusiva para la sección 'Listas' con grid y detalle de playlist."""

    play_track_requested = pyqtSignal(dict)
    play_all_requested = pyqtSignal(list)
    playlist_changed = pyqtSignal()

    def __init__(
        self,
        accent_color: str = "#ff1744",
        audio_engine: Optional[Any] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.accent_color = accent_color
        self.audio_engine = audio_engine
        self.db = get_database_manager()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget(self)
        layout.addWidget(self.stack)

        # Página 0: Scroll con Grid de Listas
        self.page_grid = QWidget()
        page_grid_layout = QVBoxLayout(self.page_grid)
        page_grid_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea(self.page_grid)
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 4, 10, 10)
        scroll_layout.setSpacing(18)

        lbl_header = QLabel("📋 Listas de Reproducción", scroll_content)
        lbl_header.setFont(QFont("Sans Serif", 14, QFont.Weight.Bold))
        lbl_header.setStyleSheet("color: #ffffff;")
        scroll_layout.addWidget(lbl_header)

        self.grid_view = PlaylistsGridView(accent_color=self.accent_color, parent=scroll_content)
        self.grid_view.playlist_clicked.connect(self._on_playlist_clicked)
        self.grid_view.create_playlist_requested.connect(self._open_create_dialog)
        scroll_layout.addWidget(self.grid_view)
        scroll_layout.addStretch(1)

        self.scroll.setWidget(scroll_content)
        page_grid_layout.addWidget(self.scroll)
        self.stack.addWidget(self.page_grid)

        # Página 1: Detalle de Playlist
        self.detail_view = PlaylistDetailView(
            accent_color=self.accent_color,
            audio_engine=self.audio_engine,
            parent=self,
        )
        self.detail_view.back_requested.connect(lambda: self.stack.setCurrentIndex(0))
        self.detail_view.play_track_requested.connect(self.play_track_requested.emit)
        self.detail_view.play_all_requested.connect(self.play_all_requested.emit)
        self.detail_view.playlist_updated.connect(self._on_detail_playlist_updated)
        self.stack.addWidget(self.detail_view)

    def set_audio_engine(self, engine: Any) -> None:
        self.audio_engine = engine
        self.detail_view.audio_engine = engine

    def set_accent_color(self, hex_color: str) -> None:
        self.accent_color = hex_color
        self.grid_view.set_accent_color(hex_color)
        self.detail_view.update_accent_color(hex_color)

    def refresh(self) -> None:
        self.stack.setCurrentIndex(0)
        self.grid_view.refresh()

    def _on_playlist_clicked(self, pl_data: dict) -> None:
        pl_id = pl_data.get("id")
        pl_name = pl_data.get("name", "Lista")
        self.detail_view.load_playlist(pl_id, pl_name)
        self.stack.setCurrentIndex(1)

    def _open_create_dialog(self) -> None:
        dialog = CreatePlaylistDialog(accent_color=self.accent_color, parent=self.window())
        if dialog.exec():
            name = dialog.get_playlist_name()
            if name:
                new_id = self.db.create_playlist(name)
                self.grid_view.refresh()
                self.playlist_changed.emit()
                if new_id:
                    self._on_playlist_clicked({"id": new_id, "name": name})

    def _on_detail_playlist_updated(self) -> None:
        self.grid_view.refresh()
        self.playlist_changed.emit()


# ═════════════════════════════════════════════════════════════════════════════
# VISTA PRINCIPAL: MÚSICA (Spotify Home Layout)
# ═════════════════════════════════════════════════════════════════════════════


class MusicHomeView(QWidget):
    """Vista principal 'Música' estilo Spotify Home con búsqueda global en tiempo real,

    sección de recién escuchados, artistas/álbumes más reproducidos y gestión de listas.
    """

    play_track_requested = pyqtSignal(dict)
    play_all_requested = pyqtSignal(list)
    playlist_changed = pyqtSignal()

    def __init__(
        self,
        accent_color: str = "#ff1744",
        audio_engine: Optional[Any] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.accent_color = accent_color
        self.audio_engine = audio_engine
        self.db = get_database_manager()
        self.active_top_tab = "artists"  # "artists" o "albums"
        self._current_playlist_cols: int = 5

        # Debounce para la búsqueda en tiempo real (80-100ms)
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(90)
        self._search_timer.timeout.connect(self._perform_search)

        self._build_ui()

    def set_audio_engine(self, audio_engine: Any) -> None:
        self.audio_engine = audio_engine
        if hasattr(self, "page_playlist_detail") and self.page_playlist_detail:
            self.page_playlist_detail.audio_engine = audio_engine

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(14)

        # 1. BARRA DE BÚSQUEDA GLOBAL (Ancho completo arriba)
        search_frame = QFrame(self)
        search_frame.setFixedHeight(44)
        search_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(14, 18, 30, 0.75);
                border-radius: 14px;
                border: 1px solid rgba(255, 255, 255, 0.10);
            }
            QFrame:focus-within {
                border: 1.5px solid #00e5ff;
                background-color: rgba(18, 24, 40, 0.90);
            }
        """)
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(14, 0, 48, 0)
        search_layout.setSpacing(10)

        lbl_search_icon = QLabel("🔍", search_frame)
        lbl_search_icon.setFont(QFont("Sans Serif", 11))
        lbl_search_icon.setStyleSheet("border: none; background: transparent;")
        search_layout.addWidget(lbl_search_icon)

        self.search_input = QLineEdit(search_frame)
        self.search_input.setPlaceholderText(
            "Buscar canciones, artistas, álbumes o listas..."
        )
        self.search_input.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #ffffff;
                font-size: 13px;
                padding: 0px;
            }
        """)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        search_layout.addWidget(self.search_input, stretch=1)

        self.btn_clear_search = QPushButton("✕", search_frame)
        self.btn_clear_search.setFixedSize(24, 24)
        self.btn_clear_search.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_search.setVisible(False)
        self.btn_clear_search.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.12);
                border-radius: 12px;
                color: rgba(255, 255, 255, 0.60);
                font-size: 10px;
                border: none;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.25);
                color: #ffffff;
            }
        """)
        self.btn_clear_search.clicked.connect(self._clear_search)
        search_layout.addWidget(self.btn_clear_search)

        main_layout.addWidget(search_frame)

        # 2. STACKED WIDGET DE CONTENIDO (Página 0: Home, Página 1: Resultados de Búsqueda, Página 2: Detalle de Playlist)
        self.content_stack = QStackedWidget(self)

        # ---------------------------------------------------------------------
        # PÁGINA 0: SPOTIFY HOME VIEW
        # ---------------------------------------------------------------------
        self.page_home = QWidget()
        page_home_layout = QVBoxLayout(self.page_home)
        page_home_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_home = QScrollArea(self.page_home)
        self.scroll_home.setWidgetResizable(True)
        self.scroll_home.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
        )

        home_content = QWidget()
        self.home_content_layout = QVBoxLayout(home_content)
        self.home_content_layout.setContentsMargins(0, 4, 10, 10)
        self.home_content_layout.setSpacing(22)

        # SECCIÓN A: RECIÉN ESCUCHADOS
        self._build_recents_section(self.home_content_layout)

        # SECCIÓN B: MÁS ESCUCHADOS (Tabs Artistas / Álbumes)
        self._build_top_played_section(self.home_content_layout)

        # SECCIÓN C: TUS LISTAS
        self._build_playlists_section(self.home_content_layout)

        self.home_content_layout.addStretch(1)
        self.scroll_home.setWidget(home_content)
        page_home_layout.addWidget(self.scroll_home)
        self.content_stack.addWidget(self.page_home)

        # ---------------------------------------------------------------------
        # PÁGINA 1: RESULTADOS DE BÚSQUEDA GLOBAL
        # ---------------------------------------------------------------------
        self.page_search = QWidget()
        page_search_layout = QVBoxLayout(self.page_search)
        page_search_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_search = QScrollArea(self.page_search)
        self.scroll_search.setWidgetResizable(True)
        self.scroll_search.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
        )

        self.search_content = QWidget()
        self.search_content_layout = QVBoxLayout(self.search_content)
        self.search_content_layout.setContentsMargins(0, 4, 10, 10)
        self.search_content_layout.setSpacing(18)

        self.scroll_search.setWidget(self.search_content)
        page_search_layout.addWidget(self.scroll_search)
        self.content_stack.addWidget(self.page_search)

        # ---------------------------------------------------------------------
        # PÁGINA 2: DETALLE DE PLAYLIST
        # ---------------------------------------------------------------------
        self.page_playlist_detail = PlaylistDetailView(
            accent_color=self.accent_color,
            audio_engine=self.audio_engine,
            parent=self,
        )
        self.page_playlist_detail.back_requested.connect(
            lambda: self.content_stack.setCurrentIndex(0)
        )
        self.page_playlist_detail.play_track_requested.connect(
            self.play_track_requested.emit
        )
        self.page_playlist_detail.play_all_requested.connect(
            self.play_all_requested.emit
        )
        self.page_playlist_detail.playlist_deleted.connect(
            lambda pl_id: self._on_playlist_deleted_or_updated()
        )
        self.page_playlist_detail.playlist_updated.connect(
            self.playlist_changed.emit
        )
        self.content_stack.addWidget(self.page_playlist_detail)

        main_layout.addWidget(self.content_stack, stretch=1)

    # ═════════════════════════════════════════════════════════════════════════
    # CONSTRUCCIÓN DE SECCIONES DEL HOME
    # ═════════════════════════════════════════════════════════════════════════

    def _build_recents_section(self, parent_layout: QVBoxLayout) -> None:
        lbl_title = QLabel("⏱️ Recién escuchados", self.page_home)
        lbl_title.setFont(QFont("Sans Serif", 11, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #ffffff;")
        parent_layout.addWidget(lbl_title)

        self.recents_scroll = QScrollArea(self.page_home)
        self.recents_scroll.setFixedHeight(225)
        self.recents_scroll.setWidgetResizable(True)
        self.recents_scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
        )

        self.recents_widget = QWidget()
        self.recents_layout = QHBoxLayout(self.recents_widget)
        self.recents_layout.setContentsMargins(0, 0, 0, 0)
        self.recents_layout.setSpacing(14)
        self.recents_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.recents_scroll.setWidget(self.recents_widget)
        parent_layout.addWidget(self.recents_scroll)

    def _build_top_played_section(self, parent_layout: QVBoxLayout) -> None:
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        lbl_title = QLabel("🔥 Más escuchados", self.page_home)
        lbl_title.setFont(QFont("Sans Serif", 11, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #ffffff;")
        header_layout.addWidget(lbl_title)

        header_layout.addSpacing(14)

        # Tabs tipo pastilla: Artistas / Álbumes
        self.btn_tab_artists = QPushButton("Artistas", self.page_home)
        self.btn_tab_artists.setFixedHeight(28)
        self.btn_tab_artists.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tab_artists.clicked.connect(
            lambda: self._set_top_tab("artists")
        )
        header_layout.addWidget(self.btn_tab_artists)

        self.btn_tab_albums = QPushButton("Álbumes", self.page_home)
        self.btn_tab_albums.setFixedHeight(28)
        self.btn_tab_albums.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tab_albums.clicked.connect(lambda: self._set_top_tab("albums"))
        header_layout.addWidget(self.btn_tab_albums)

        header_layout.addStretch(1)
        parent_layout.addLayout(header_layout)

        self.top_scroll = QScrollArea(self.page_home)
        self.top_scroll.setFixedHeight(225)
        self.top_scroll.setWidgetResizable(True)
        self.top_scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
        )

        self.top_widget = QWidget()
        self.top_layout = QHBoxLayout(self.top_widget)
        self.top_layout.setContentsMargins(0, 0, 0, 0)
        self.top_layout.setSpacing(14)
        self.top_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.top_scroll.setWidget(self.top_widget)
        parent_layout.addWidget(self.top_scroll)

    def _build_playlists_section(self, parent_layout: QVBoxLayout) -> None:
        lbl_title = QLabel("📋 Tus Listas", self.page_home)
        lbl_title.setFont(QFont("Sans Serif", 11, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #ffffff;")
        parent_layout.addWidget(lbl_title)

        self.playlists_grid_view = PlaylistsGridView(
            accent_color=self.accent_color, parent=self.page_home
        )
        self.playlists_grid_view.playlist_clicked.connect(self._open_playlist_detail)
        self.playlists_grid_view.create_playlist_requested.connect(
            self._open_create_playlist_dialog
        )
        parent_layout.addWidget(self.playlists_grid_view)

    # ═════════════════════════════════════════════════════════════════════════
    # RECARGA Y RENDERIZADO DE DATOS (Fase 1 -> UI)
    # ═════════════════════════════════════════════════════════════════════════

    def update_accent_color(self, accent_color: str) -> None:
        self.accent_color = accent_color
        self.refresh_all()

    def on_playback_recorded(self, track_meta: dict) -> None:
        """Slot reactivo en tiempo real al registrarse una reproducción válida (>10s)."""
        # Se programa en el event loop con un breve margen (120ms) para sincronizar con la DB
        QTimer.singleShot(120, self._refresh_live_stats)

    def _refresh_live_stats(self) -> None:
        """Actualiza automáticamente 'Recién escuchados' y 'Más escuchados' sin reiniciar la vista."""
        if self.isVisible() and self.content_stack.currentIndex() == 0:
            self._refresh_recents()
            self._refresh_top_played()

    def refresh_all(self) -> None:
        """Refresca todas las secciones de la vista principal."""
        self._refresh_recents()
        self._refresh_top_played()
        self._refresh_playlists()

    def _refresh_recents(self) -> None:
        while self.recents_layout.count():
            child = self.recents_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        recents = self.db.get_recently_played(limit=20)
        if not recents:
            empty = EmptyStateWidget(
                "🎧",
                "Aún no has escuchado nada",
                "Reproduce algo para verlo reflejado aquí",
                height=190,
            )
            empty.setFixedWidth(400)
            self.recents_layout.addWidget(empty)
            return

        for track in recents:
            card = MediaCard(
                data=track,
                title=track.get("title", "Sin título"),
                subtitle=track.get("artist", UNKNOWN_ARTIST),
                art_url=track.get("art_url", ""),
                accent_color=self.accent_color,
                parent=self.recents_widget,
            )
            card.clicked.connect(self.play_track_requested.emit)
            self.recents_layout.addWidget(card)

    def _set_top_tab(self, tab: str) -> None:
        self.active_top_tab = tab
        self._refresh_top_played()

    def _refresh_top_played(self) -> None:
        clean_accent = self.accent_color.split(";")[0].strip() or "#ff1744"
        contrast = get_contrast_color(clean_accent)

        # Actualizar estilos de los botones de pestaña
        if self.active_top_tab == "artists":
            self.btn_tab_artists.setStyleSheet(f"""
                QPushButton {{
                    background-color: {clean_accent};
                    color: {contrast};
                    border-radius: 14px;
                    padding: 2px 14px;
                    font-size: 11px;
                    font-weight: bold;
                    border: none;
                }}
            """)
            self.btn_tab_albums.setStyleSheet("""
                QPushButton {{
                    background-color: rgba(255, 255, 255, 0.08);
                    color: #cbd5e1;
                    border-radius: 14px;
                    padding: 2px 14px;
                    font-size: 11px;
                    font-weight: bold;
                    border: 1px solid rgba(255, 255, 255, 0.12);
                }}
                QPushButton:hover { background-color: rgba(255, 255, 255, 0.16); color: #ffffff; }
            """)
        else:
            self.btn_tab_albums.setStyleSheet(f"""
                QPushButton {{
                    background-color: {clean_accent};
                    color: {contrast};
                    border-radius: 14px;
                    padding: 2px 14px;
                    font-size: 11px;
                    font-weight: bold;
                    border: none;
                }}
            """)
            self.btn_tab_artists.setStyleSheet("""
                QPushButton {{
                    background-color: rgba(255, 255, 255, 0.08);
                    color: #cbd5e1;
                    border-radius: 14px;
                    padding: 2px 14px;
                    font-size: 11px;
                    font-weight: bold;
                    border: 1px solid rgba(255, 255, 255, 0.12);
                }}
                QPushButton:hover { background-color: rgba(255, 255, 255, 0.16); color: #ffffff; }
            """)

        while self.top_layout.count():
            child = self.top_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if self.active_top_tab == "artists":
            top_artists = self.db.get_top_artists(limit=15)
            if not top_artists:
                empty = EmptyStateWidget(
                    "👤",
                    "Sin estadísticas de artistas todavía",
                    "Escucha tus canciones para descubrir tu top",
                    height=190,
                )
                empty.setFixedWidth(400)
                self.top_layout.addWidget(empty)
                return

            for art in top_artists:
                artist_name = art.get("artist", "")
                plays = art.get("total_plays", 0)
                card = MediaCard(
                    data=art,
                    title=artist_name,
                    subtitle=f"{plays} reproducciones",
                    art_url=art.get("art_url", ""),
                    accent_color=self.accent_color,
                    is_circular=True,
                    parent=self.top_widget,
                )
                card.clicked.connect(self._on_artist_card_clicked)
                self.top_layout.addWidget(card)
        else:
            top_albums = self.db.get_top_albums(limit=15)
            if not top_albums:
                empty = EmptyStateWidget(
                    "💿",
                    "Sin estadísticas de álbumes todavía",
                    "Escucha álbumes completos para verlos aquí",
                    height=190,
                )
                empty.setFixedWidth(400)
                self.top_layout.addWidget(empty)
                return

            for alb in top_albums:
                album_name = alb.get("album", "")
                artist_name = alb.get("artist", "")
                plays = alb.get("total_plays", 0)
                card = MediaCard(
                    data=alb,
                    title=album_name,
                    subtitle=f"{artist_name} • {plays} repr.",
                    art_url=alb.get("art_url", ""),
                    accent_color=self.accent_color,
                    is_circular=False,
                    parent=self.top_widget,
                )
                card.clicked.connect(self._on_album_card_clicked)
                self.top_layout.addWidget(card)

    def _refresh_playlists(self) -> None:
        if hasattr(self, "playlists_grid_view") and self.playlists_grid_view:
            self.playlists_grid_view.refresh()

    # ═════════════════════════════════════════════════════════════════════════
    # MANEJADORES DE PLAYLISTS & NAVEGACIÓN
    # ═════════════════════════════════════════════════════════════════════════

    def _open_create_playlist_dialog(self) -> None:
        dlg = CreatePlaylistDialog(
            accent_color=self.accent_color, parent=self.window()
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name = dlg.get_playlist_name()
            if name:
                new_id = self.db.create_playlist(name)
                if new_id:
                    self._refresh_playlists()
                    self.playlist_changed.emit()

    def _open_playlist_detail(self, pl_data: dict) -> None:
        pl_id = pl_data.get("id")
        pl_name = pl_data.get("name", "Lista")
        if pl_id is not None:
            self.page_playlist_detail.load_playlist(pl_id, pl_name)
            self.content_stack.setCurrentIndex(2)

    def _on_playlist_deleted_or_updated(self) -> None:
        self._refresh_playlists()
        self.playlist_changed.emit()

    def _on_artist_card_clicked(self, artist_data: dict) -> None:
        artist_name = artist_data.get("artist", "")
        if artist_name:
            self.search_input.setText(artist_name)

    def _on_album_card_clicked(self, album_data: dict) -> None:
        album_name = album_data.get("album", "")
        if album_name:
            self.search_input.setText(album_name)

    # ═════════════════════════════════════════════════════════════════════════
    # BÚSQUEDA GLOBAL EN TIEMPO REAL
    # ═════════════════════════════════════════════════════════════════════════

    def _on_search_text_changed(self, text: str) -> None:
        self.btn_clear_search.setVisible(bool(text))
        if not text.strip():
            self._search_timer.stop()
            self.content_stack.setCurrentIndex(0)
            return

        self._search_timer.start()

    def _clear_search(self) -> None:
        self.search_input.clear()
        self.content_stack.setCurrentIndex(0)

    def _perform_search(self) -> None:
        query = self.search_input.text().strip()
        if not query:
            self.content_stack.setCurrentIndex(0)
            return

        results = self.db.search_library(query, limit=15)
        self._render_search_results(query, results)
        self.content_stack.setCurrentIndex(1)

    def _render_search_results(
        self, query: str, results: Dict[str, List[Dict[str, Any]]]
    ) -> None:
        while self.search_content_layout.count():
            child = self.search_content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        tracks = results.get("tracks", [])
        artists = results.get("artists", [])
        albums = results.get("albums", [])
        playlists = results.get("playlists", [])

        total_results = (
            len(tracks) + len(artists) + len(albums) + len(playlists)
        )
        if total_results == 0:
            empty = EmptyStateWidget(
                "🔍",
                f"No se encontraron resultados para '{query}'",
                "Intenta con otro término de búsqueda",
                height=220,
            )
            self.search_content_layout.addWidget(empty)
            self.search_content_layout.addStretch(1)
            return

        # 1. Canciones coincidentes
        if tracks:
            lbl_tr = QLabel(f"🎵 Canciones ({len(tracks)})", self.page_search)
            lbl_tr.setFont(QFont("Sans Serif", 11, QFont.Weight.Bold))
            lbl_tr.setStyleSheet("color: #ffffff;")
            self.search_content_layout.addWidget(lbl_tr)

            for t in tracks:
                row = QFrame(self.page_search)
                row.setFixedHeight(46)
                row.setCursor(Qt.CursorShape.PointingHandCursor)
                row.setStyleSheet("""
                    QFrame {
                        background-color: rgba(14, 18, 30, 0.55);
                        border-radius: 10px;
                        border: 1px solid rgba(255, 255, 255, 0.06);
                    }
                    QFrame:hover {
                        background-color: rgba(255, 255, 255, 0.14);
                        border: 1px solid rgba(255, 255, 255, 0.22);
                    }
                """)
                r_lay = QHBoxLayout(row)
                r_lay.setContentsMargins(12, 0, 12, 0)
                r_lay.setSpacing(12)

                lbl_t = QLabel(t.get("title", "Sin título"), row)
                lbl_t.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
                lbl_t.setStyleSheet("color: #ffffff;")
                r_lay.addWidget(lbl_t, stretch=2)

                lbl_a = QLabel(t.get("artist", UNKNOWN_ARTIST), row)
                lbl_a.setFont(QFont("Sans Serif", 8))
                lbl_a.setStyleSheet("color: rgba(255, 255, 255, 0.65);")
                r_lay.addWidget(lbl_a, stretch=2)

                lbl_alb = QLabel(t.get("album", ""), row)
                lbl_alb.setFont(QFont("Sans Serif", 8))
                lbl_alb.setStyleSheet("color: rgba(255, 255, 255, 0.45);")
                r_lay.addWidget(lbl_alb, stretch=2)

                def make_play_handler(t_dict):
                    def _h(event):
                        if event.button() == Qt.MouseButton.LeftButton:
                            self.play_track_requested.emit(t_dict)

                    return _h

                row.mousePressEvent = make_play_handler(t)
                self.search_content_layout.addWidget(row)

        # 2. Artistas coincidentes
        if artists:
            lbl_ar = QLabel(f"👤 Artistas ({len(artists)})", self.page_search)
            lbl_ar.setFont(QFont("Sans Serif", 11, QFont.Weight.Bold))
            lbl_ar.setStyleSheet("color: #ffffff; margin-top: 10px;")
            self.search_content_layout.addWidget(lbl_ar)

            ar_scroll = QScrollArea(self.page_search)
            ar_scroll.setFixedHeight(225)
            ar_scroll.setWidgetResizable(True)
            ar_scroll.setStyleSheet(
                "QScrollArea { border: none; background: transparent; }"
            )
            ar_w = QWidget()
            ar_lay = QHBoxLayout(ar_w)
            ar_lay.setContentsMargins(0, 0, 0, 0)
            ar_lay.setSpacing(14)
            ar_lay.setAlignment(Qt.AlignmentFlag.AlignLeft)

            for art in artists:
                card = MediaCard(
                    data=art,
                    title=art.get("artist", ""),
                    subtitle=f"{art.get('total_plays', 0)} repr.",
                    art_url=art.get("art_url", ""),
                    accent_color=self.accent_color,
                    is_circular=True,
                    parent=ar_w,
                )
                card.clicked.connect(self._on_artist_card_clicked)
                ar_lay.addWidget(card)

            ar_scroll.setWidget(ar_w)
            self.search_content_layout.addWidget(ar_scroll)

        # 3. Álbumes coincidentes
        if albums:
            lbl_al = QLabel(f"💿 Álbumes ({len(albums)})", self.page_search)
            lbl_al.setFont(QFont("Sans Serif", 11, QFont.Weight.Bold))
            lbl_al.setStyleSheet("color: #ffffff; margin-top: 10px;")
            self.search_content_layout.addWidget(lbl_al)

            al_scroll = QScrollArea(self.page_search)
            al_scroll.setFixedHeight(225)
            al_scroll.setWidgetResizable(True)
            al_scroll.setStyleSheet(
                "QScrollArea { border: none; background: transparent; }"
            )
            al_w = QWidget()
            al_lay = QHBoxLayout(al_w)
            al_lay.setContentsMargins(0, 0, 0, 0)
            al_lay.setSpacing(14)
            al_lay.setAlignment(Qt.AlignmentFlag.AlignLeft)

            for alb in albums:
                card = MediaCard(
                    data=alb,
                    title=alb.get("album", ""),
                    subtitle=alb.get("artist", ""),
                    art_url=alb.get("art_url", ""),
                    accent_color=self.accent_color,
                    is_circular=False,
                    parent=al_w,
                )
                card.clicked.connect(self._on_album_card_clicked)
                al_lay.addWidget(card)

            al_scroll.setWidget(al_w)
            self.search_content_layout.addWidget(al_scroll)

        # 4. Listas coincidentes
        if playlists:
            lbl_pl = QLabel(f"📋 Listas ({len(playlists)})", self.page_search)
            lbl_pl.setFont(QFont("Sans Serif", 11, QFont.Weight.Bold))
            lbl_pl.setStyleSheet("color: #ffffff; margin-top: 10px;")
            self.search_content_layout.addWidget(lbl_pl)

            pl_scroll = QScrollArea(self.page_search)
            pl_scroll.setFixedHeight(225)
            pl_scroll.setWidgetResizable(True)
            pl_scroll.setStyleSheet(
                "QScrollArea { border: none; background: transparent; }"
            )
            pl_w = QWidget()
            pl_lay = QHBoxLayout(pl_w)
            pl_lay.setContentsMargins(0, 0, 0, 0)
            pl_lay.setSpacing(14)
            pl_lay.setAlignment(Qt.AlignmentFlag.AlignLeft)

            for pl in playlists:
                card = MediaCard(
                    data=pl,
                    title=pl.get("name", "Lista"),
                    subtitle=f"{pl.get('track_count', 0)} canciones",
                    art_url="",
                    accent_color=self.accent_color,
                    is_circular=False,
                    parent=pl_w,
                )
                card.clicked.connect(self._open_playlist_detail)
                pl_lay.addWidget(card)

            pl_scroll.setWidget(pl_w)
            self.search_content_layout.addWidget(pl_scroll)

        self.search_content_layout.addStretch(1)
