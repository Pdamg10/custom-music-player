import os
import random
import urllib.parse
from typing import Optional, Dict, Any, List
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPoint, QPointF, QRect, QRectF, QTimer, QEvent, QObject, QModelIndex
from PyQt6.QtGui import (
    QFont, QFontMetrics, QPixmap, QColor, QPainter, QPainterPath, QPen, QBrush, QIcon, QAction,
    QLinearGradient, QRadialGradient, QConicalGradient, QImage, QImageReader, QShowEvent
)
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QLineEdit, QScrollArea, QFrame, QStackedWidget, QSlider,
    QGridLayout, QSizePolicy, QListWidget, QListWidgetItem,
    QInputDialog, QMenu, QMessageBox, QApplication, QDialog,
    QStyledItemDelegate, QStyleOptionViewItem, QStyle
)

from ui.marquee_label import MarqueeLabel
from ui.equalizer_widget import EqualizerWidget
from ui.y2k_volume_slider import Y2KVolumeSlider
from ui.color_extractor import get_contrasting_text_color
from ui.styles import MAIN_STYLE, _build_qlineargradient, build_button_style, build_mode_pill_style
from ui.music_home_view import MusicHomeView, PlaylistsPageView, CreatePlaylistDialog
from ui.lyrics_view_widget import LyricsDisplayWidget

_PIXMAP_CACHE: Dict[tuple, Optional[QPixmap]] = {}
_PLACEHOLDER_CACHE: Dict[tuple, QPixmap] = {}

def get_cached_pixmap(path_or_url: str, width: int = 129, height: int = 110) -> Optional[QPixmap]:
    if not path_or_url:
        return None
    
    clean_path = str(path_or_url).strip()
    if clean_path.startswith("file://"):
        clean_path = urllib.parse.unquote(clean_path[7:])
    elif clean_path.startswith("file:"):
        clean_path = urllib.parse.unquote(clean_path[5:])
    else:
        clean_path = urllib.parse.unquote(clean_path)
    
    clean_path = os.path.expanduser(clean_path.strip("'\""))
    
    cache_key = (clean_path, width, height)
    if cache_key in _PIXMAP_CACHE:
        return _PIXMAP_CACHE[cache_key]

    base_key = (clean_path, 0, 0)
    if base_key in _PIXMAP_CACHE and _PIXMAP_CACHE[base_key] is not None:
        base_pix = _PIXMAP_CACHE[base_key]
        if width > 0 and height > 0:
            scaled = base_pix.scaled(
                width, height,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            _PIXMAP_CACHE[cache_key] = scaled
            return scaled
        return base_pix

    if not os.path.exists(clean_path) or not os.path.isfile(clean_path):
        _PIXMAP_CACHE[cache_key] = None
        return None

    pixmap: Optional[QPixmap] = None

    # Método 1: QPixmap Directo Nativo en C++ (Ultrarrápido, ~1ms por imagen)
    try:
        pix = QPixmap(clean_path)
        if pix and not pix.isNull() and pix.width() > 0:
            pixmap = pix
            _PIXMAP_CACHE[base_key] = pixmap
    except Exception:
        pixmap = None

    # Método 2: QImageReader (Con auto-transformación EXIF)
    if pixmap is None or pixmap.isNull():
        try:
            reader = QImageReader(clean_path)
            reader.setAutoTransform(True)
            qimg = reader.read()
            if not qimg.isNull():
                pixmap = QPixmap.fromImage(qimg)
                _PIXMAP_CACHE[base_key] = pixmap
        except Exception:
            pixmap = None

    # Método 3: PIL / Pillow Fallback (Para formatos complejos o raros)
    if pixmap is None or pixmap.isNull():
        try:
            from PIL import Image, ImageOps
            import io
            with Image.open(clean_path) as pil_img:
                pil_img = ImageOps.exif_transpose(pil_img)
                if width > 0 and height > 0:
                    pil_img.thumbnail((max(width * 2, 400), max(height * 2, 400)))
                buf = io.BytesIO()
                pil_img.save(buf, format="PNG")
                pix = QPixmap()
                if pix.loadFromData(buf.getvalue()):
                    pixmap = pix
                    _PIXMAP_CACHE[base_key] = pixmap
        except Exception:
            pixmap = None

    if pixmap and not pixmap.isNull():
        if width > 0 and height > 0:
            scaled = pixmap.scaled(
                width, height,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            _PIXMAP_CACHE[cache_key] = scaled
            return scaled
        else:
            _PIXMAP_CACHE[cache_key] = pixmap
            return pixmap

    _PIXMAP_CACHE[cache_key] = None
    return None

def _get_placeholder_pixmap(width: int = 140, height: int = 140, is_playing: bool = False, accent_color: str = "#ff1744") -> QPixmap:
    key = (width, height, is_playing, accent_color)
    if key in _PLACEHOLDER_CACHE:
        return _PLACEHOLDER_CACHE[key]

    pm = QPixmap(max(1, width), max(1, height))
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, width, height), 14, 14)
    p.setClipPath(path)

    qc = QColor(accent_color.split(';')[0].strip() if accent_color else "#ff1744")
    if not qc.isValid():
        qc = QColor("#ff1744")
    r, g, b = qc.red(), qc.green(), qc.blue()

    # Fondo sutil y traslúcido armonizado con el color de acento
    grad = QLinearGradient(0, 0, width, height)
    grad.setColorAt(0.0, QColor(r, g, b, 45))
    grad.setColorAt(1.0, QColor(8, 11, 20, 140))
    p.fillRect(0, 0, width, height, grad)

    p.setPen(QPen(QColor(255, 255, 255, 24), 1.0))
    p.drawRoundedRect(QRectF(0.5, 0.5, width - 1.0, height - 1.0), 14, 14)

    # Ícono discreto y sutil
    p.setPen(QPen(QColor(255, 255, 255, 110)))
    p.setFont(QFont("Sans Serif", max(13, min(width // 5, 22)), QFont.Weight.Medium))
    symbol = "▶" if is_playing else "🎧"
    p.drawText(QRectF(0, 0, width, height), Qt.AlignmentFlag.AlignCenter, symbol)
    p.end()

    _PLACEHOLDER_CACHE[key] = pm
    return pm

def create_heart_path(rect: QRectF) -> QPainterPath:
    """Genera una trayectoria vectorial QPainterPath en forma de corazón simétrico suave."""
    x = rect.x()
    y = rect.y()
    w = rect.width()
    h = rect.height()

    top_notch_y = y + h * 0.24
    bottom_tip_y = y + h * 0.96
    cx = x + w * 0.50

    path = QPainterPath()
    path.moveTo(cx, top_notch_y)

    # Lóbulo izquierdo
    path.cubicTo(
        cx - w * 0.14, y,
        x, y + h * 0.04,
        x, y + h * 0.36
    )
    path.cubicTo(
        x, y + h * 0.62,
        cx - w * 0.28, y + h * 0.80,
        cx, bottom_tip_y
    )

    # Lóbulo derecho
    path.cubicTo(
        cx + w * 0.28, y + h * 0.80,
        x + w, y + h * 0.62,
        x + w, y + h * 0.36
    )
    path.cubicTo(
        x + w, y + h * 0.04,
        cx + w * 0.14, y,
        cx, top_notch_y
    )
    path.closeSubpath()
    return path

class VinylTurntableWidget(QWidget):
    """Widget de Tocadiscos de Vinilo con Brazo Dinámico y Carátula Giratoria."""
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.album_art: Optional[QPixmap] = None
        self.accent_color: str = "#ff1744"
        self.cover_shape: str = "circle"
        self.is_playing: bool = False

        self.setMinimumSize(260, 260)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._rotation_angle: float = 0.0
        self._arm_angle: float = -26.0  # -26° = reposo/pausado, 0° = sobre el vinilo
        self._target_arm_angle: float = -26.0

        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(30)
        self.anim_timer.timeout.connect(self._update_animation)
        self._cached_scaled_art: Optional[QPixmap] = None
        self._cached_art_size: tuple[int, int] = (0, 0)
        self._cached_source_pixmap: Optional[QPixmap] = None

    def sizeHint(self) -> QSize:
        return QSize(360, 360)

    def set_playing(self, is_playing: bool) -> None:
        self.is_playing = bool(is_playing)
        self._target_arm_angle = 0.0 if self.is_playing else -26.0
        if not self.anim_timer.isActive():
            self.anim_timer.start()

    def start(self) -> None:
        self.set_playing(True)

    def resume(self) -> None:
        self.set_playing(True)

    def stop(self) -> None:
        self.set_playing(False)

    def pause(self) -> None:
        self.set_playing(False)

    def set_active(self, is_active: bool) -> None:
        self.set_playing(is_active)

    def set_album_art(self, pixmap: Optional[QPixmap]) -> None:
        self.album_art = pixmap if (pixmap and not pixmap.isNull()) else None
        self._cached_scaled_art = None
        self.update()

    def set_accent_color(self, hex_color: str) -> None:
        if hex_color:
            self.accent_color = hex_color
        self.update()

    def set_cover_shape(self, shape: str) -> None:
        self.cover_shape = shape if shape in ("circle", "rounded", "heart") else "rounded"
        self._cached_scaled_art = None
        self.update()

    def _update_animation(self) -> None:
        if not self.isVisible():
            return

        # Animación suave de descenso / ascenso del brazo
        arm_diff = self._target_arm_angle - self._arm_angle
        if abs(arm_diff) > 0.4:
            self._arm_angle += arm_diff * 0.16
        else:
            self._arm_angle = self._target_arm_angle

        # Rotación continua del disco de vinilo cuando está en reproducción
        if self.is_playing:
            self._rotation_angle = (self._rotation_angle + 0.6) % 360.0
            self.update()
        else:
            if abs(arm_diff) > 0.4:
                self.update()
            elif self.anim_timer.isActive():
                self.anim_timer.stop()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w = float(self.width())
        h = float(self.height())
        disc_size = max(160.0, min(w * 0.84, h * 0.80, 320.0))
        cx = w / 2.0
        cy = h * 0.54

        # 1. Resplandor / Sombra exterior del tocadiscos
        glow_grad = QRadialGradient(cx, cy, disc_size * 0.60)
        glow_grad.setColorAt(0.0, QColor(0, 0, 0, 180))
        glow_grad.setColorAt(0.85, QColor(0, 0, 0, 95))
        glow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(glow_grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(cx - disc_size * 0.56, cy - disc_size * 0.56, disc_size * 1.12, disc_size * 1.12))

        # 2. Marco exterior del plato de vinilo (Chassis / Bezel)
        p.setBrush(QBrush(QColor(26, 28, 33)))
        p.setPen(QPen(QColor(50, 54, 62), 2.0))
        p.drawEllipse(QRectF(cx - disc_size * 0.505, cy - disc_size * 0.505, disc_size * 1.01, disc_size * 1.01))

        # 3. Disco de Vinilo (Gira con la rotación activa)
        p.save()
        p.translate(cx, cy)
        p.rotate(self._rotation_angle)

        disc_r = disc_size * 0.485
        disc_rect = QRectF(-disc_r, -disc_r, disc_r * 2, disc_r * 2)

        # Superficie de vinilo negro
        p.setBrush(QBrush(QColor(11, 12, 15)))
        p.setPen(QPen(QColor(22, 24, 28), 1.0))
        p.drawEllipse(disc_rect)

        # Reflejos cónicos de luz satinada
        conic = QConicalGradient(0, 0, 45)
        conic.setColorAt(0.0, QColor(255, 255, 255, 34))
        conic.setColorAt(0.12, QColor(255, 255, 255, 6))
        conic.setColorAt(0.25, QColor(255, 255, 255, 28))
        conic.setColorAt(0.37, QColor(255, 255, 255, 6))
        conic.setColorAt(0.50, QColor(255, 255, 255, 34))
        conic.setColorAt(0.62, QColor(255, 255, 255, 6))
        conic.setColorAt(0.75, QColor(255, 255, 255, 28))
        conic.setColorAt(0.87, QColor(255, 255, 255, 6))
        conic.setColorAt(1.0, QColor(255, 255, 255, 34))
        p.setBrush(QBrush(conic))
        p.drawEllipse(disc_rect)

        # Surcos concéntricos micro-texturizados del vinilo
        p.setBrush(Qt.BrushStyle.NoBrush)
        for r_factor in [0.93, 0.88, 0.83, 0.77, 0.71, 0.65, 0.59]:
            gr = disc_r * r_factor
            p.setPen(QPen(QColor(255, 255, 255, 14), 0.8))
            p.drawEllipse(QRectF(-gr, -gr, gr * 2, gr * 2))

        # 4. Etiqueta Central con Carátula del Álbum
        art_r = disc_r * 0.52
        art_rect = QRectF(-art_r, -art_r, art_r * 2, art_r * 2)

        if self.cover_shape == "heart":
            art_clip = create_heart_path(art_rect)
        elif self.cover_shape == "rounded":
            art_clip = QPainterPath()
            art_clip.addRoundedRect(art_rect, 16.0, 16.0)
        else:
            art_clip = QPainterPath()
            art_clip.addEllipse(art_rect)

        p.save()
        p.setClipPath(art_clip)

        target_size = (int(art_r * 2), int(art_r * 2))
        if self.album_art and not self.album_art.isNull():
            if (
                self._cached_scaled_art is None
                or self._cached_art_size != target_size
                or self._cached_source_pixmap is not self.album_art
            ):
                self._cached_scaled_art = self.album_art.scaled(
                    target_size[0], target_size[1],
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation
                )
                self._cached_art_size = target_size
                self._cached_source_pixmap = self.album_art

            scaled = self._cached_scaled_art
            sx = int(-scaled.width() / 2.0)
            sy = int(-scaled.height() / 2.0)
            p.drawPixmap(sx, sy, scaled)
        else:
            ph = _get_placeholder_pixmap(target_size[0], target_size[1], is_playing=self.is_playing, accent_color=self.accent_color)
            p.drawPixmap(int(-art_r), int(-art_r), ph)

        p.restore()

        # Borde iluminado de la etiqueta central y orificio central
        qc = QColor(self.accent_color.split(';')[0].strip() if self.accent_color else "#ff1744")
        if not qc.isValid():
            qc = QColor("#ff1744")
        p.setPen(QPen(QColor(qc.red(), qc.green(), qc.blue(), 180), 2.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(art_clip)

        p.setBrush(QBrush(QColor(6, 7, 10)))
        p.setPen(QPen(QColor(170, 175, 185), 1.5))
        p.drawEllipse(QRectF(-7, -7, 14, 14))

        p.restore()

        # 5. Brazo de Tocadiscos (Tonearm) estilo Hi-Fi / NetEase
        pivot_x = cx
        pivot_y = cy - disc_size * 0.50

        p.save()
        p.translate(pivot_x, pivot_y)
        p.rotate(self._arm_angle)

        # Base metálica del pivote
        base_grad = QRadialGradient(0, 0, 13)
        base_grad.setColorAt(0.0, QColor(250, 252, 255))
        base_grad.setColorAt(0.7, QColor(170, 175, 185))
        base_grad.setColorAt(1.0, QColor(80, 85, 95))
        p.setBrush(QBrush(base_grad))
        p.setPen(QPen(QColor(40, 45, 55), 1.0))
        p.drawEllipse(QRectF(-12, -12, 24, 24))

        # Tapa central del pivote
        p.setBrush(QBrush(QColor(255, 255, 255, 220)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(-4, -4, 8, 8))

        # Varilla curva del brazo
        arm_path = QPainterPath()
        arm_path.moveTo(0, 8)
        arm_path.cubicTo(-disc_size * 0.03, disc_size * 0.12, -disc_size * 0.01, disc_size * 0.22, disc_size * 0.10, disc_size * 0.40)

        # Sombra del brazo
        p.setPen(QPen(QColor(0, 0, 0, 90), 4.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawPath(arm_path)

        # Varilla plateada/blanca del brazo
        p.setPen(QPen(QColor(235, 240, 245), 3.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawPath(arm_path)

        # Cápsula fonocaptora y aguja
        end_pt = arm_path.currentPosition()
        p.save()
        p.translate(end_pt.x(), end_pt.y())
        p.rotate(24)

        # Cuerpo de la cápsula
        p.setBrush(QBrush(QColor(32, 34, 40)))
        p.setPen(QPen(QColor(180, 185, 195), 1.0))
        p.drawRoundedRect(QRectF(-4.5, -2, 9, 16), 2.0, 2.0)

        # Punta de la aguja
        p.setBrush(QBrush(QColor(255, 255, 255)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(-1.5, 12, 3, 3.5))
        p.restore()

        p.restore()
        p.end()

ArtworkEKGDisplayWidget = VinylTurntableWidget

class SongCardWidget(QFrame):
    """Tarjeta individual unificada para canciones en Escuchados recientemente y Todas tus canciones."""
    card_clicked = pyqtSignal(int)

    def __init__(self, track_index: int, title: str, artist: str, art_url: str, duration_sec: int = 0, accent_color: str = "#ff1744", is_playing: bool = False, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.track_index = track_index
        self.accent_color = accent_color
        self.setObjectName("SongCardWidget")
        self.setFixedSize(168, 232)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        clean_accent = accent_color.split(';')[0].strip() if accent_color else "#ff1744"
        qc = QColor(clean_accent)
        if not qc.isValid():
            qc = QColor("#ff1744")
        r, g, b = qc.red(), qc.green(), qc.blue()

        if is_playing:
            self.setStyleSheet(f"""
                QFrame#SongCardWidget {{
                    background-color: rgba({r}, {g}, {b}, 0.28);
                    border-radius: 18px;
                    border: 2px solid {clean_accent};
                }}
                QFrame#SongCardWidget:hover {{
                    background-color: rgba({r}, {g}, {b}, 0.38);
                    border: 2px solid {clean_accent};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame#SongCardWidget {{
                    background-color: rgba(14, 18, 30, 0.48);
                    border-radius: 18px;
                    border: 1px solid rgba(255, 255, 255, 0.09);
                }}
                QFrame#SongCardWidget:hover {{
                    background-color: rgba({r}, {g}, {b}, 0.20);
                    border: 1.5px solid {clean_accent};
                }}
            """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 12)
        layout.setSpacing(8)

        # Contenedor de Carátula 1:1 cuadrada con esquinas redondeadas elegantes y fondo traslúcido
        self.art_label = QLabel(self)
        self.art_label.setFixedSize(148, 148)
        self.art_label.setStyleSheet("border-radius: 14px; background-color: rgba(10, 14, 24, 0.50); border: 1px solid rgba(255, 255, 255, 0.08);")
        self.art_label.setScaledContents(True)
        self.art_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        effective_art = art_url
        custom_art_path = getattr(parent, 'custom_inner_image', '') or ''
        inner_mode = getattr(parent, 'inner_art_mode', 'auto') or 'auto'
        if inner_mode == "custom_always" and custom_art_path and os.path.exists(custom_art_path):
            effective_art = custom_art_path

        pix = get_cached_pixmap(effective_art, 148, 148)
        if pix and not pix.isNull():
            self.art_label.setPixmap(pix)
        else:
            self.art_label.setPixmap(_get_placeholder_pixmap(148, 148, is_playing, accent_color=clean_accent))

        layout.addWidget(self.art_label)

        # Título (Texto blanco nítido con jerarquía)
        display_title = f"▶ {title}" if is_playing else (title or "Sin título")
        lbl_title = QLabel(display_title, self)
        lbl_title.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #ffffff; border: none; background: transparent;")
        lbl_title.setToolTip(title)
        layout.addWidget(lbl_title)

        # Artista (Texto gris plateado claro y legible)
        lbl_artist = QLabel(artist or "Artista desconocido", self)
        lbl_artist.setFont(QFont("Sans Serif", 8))
        lbl_artist.setStyleSheet("color: rgba(255, 255, 255, 0.65); border: none; background: transparent;")
        lbl_artist.setToolTip(artist)
        layout.addWidget(lbl_artist)
        layout.addStretch(1)


class QueueTrackDelegate(QStyledItemDelegate):
    """Delegado moderno y elegante para los elementos de la lista en curso."""

    def __init__(self, accent_color: str = "#ff1744", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.accent_color = accent_color

    def set_accent_color(self, hex_color: str) -> None:
        self.accent_color = hex_color

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        return QSize(option.rect.width(), 50)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        rect = option.rect
        is_playing = bool(index.data(Qt.ItemDataRole.UserRole + 4))
        is_selected = bool(option.state & QStyle.StateFlag.State_Selected)
        is_hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)

        bg_rect = rect.adjusted(2, 2, -2, -2)
        clean_accent = self.accent_color.split(';')[0].strip() or "#ff1744"

        if is_playing:
            painter.setPen(QPen(QColor(clean_accent), 1.5))
            c = QColor(clean_accent)
            c.setAlpha(45)
            painter.setBrush(c)
        elif is_selected:
            painter.setPen(QPen(QColor(255, 255, 255, 50), 1))
            painter.setBrush(QColor(255, 255, 255, 35))
        elif is_hovered:
            painter.setPen(QPen(QColor(255, 255, 255, 25), 1))
            painter.setBrush(QColor(255, 255, 255, 20))
        else:
            painter.setPen(QPen(QColor(255, 255, 255, 10), 1))
            painter.setBrush(QColor(16, 20, 32, 90))

        painter.drawRoundedRect(bg_rect, 10, 10)

        # Thumbnail / Portada
        art_rect = QRect(bg_rect.left() + 8, bg_rect.top() + (bg_rect.height() - 34) // 2, 34, 34)
        art_path = index.data(Qt.ItemDataRole.UserRole + 3)
        pix = None
        if art_path:
            pix = get_cached_pixmap(art_path, 34, 34)

        if pix and not pix.isNull():
            path = QPainterPath()
            path.addRoundedRect(QRectF(art_rect), 6, 6)
            painter.save()
            painter.setClipPath(path)
            painter.drawPixmap(art_rect, pix)
            painter.restore()
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, 20))
            painter.drawRoundedRect(art_rect, 6, 6)
            painter.setPen(QColor(255, 255, 255, 180))
            painter.setFont(QFont("Sans Serif", 11))
            painter.drawText(art_rect, Qt.AlignmentFlag.AlignCenter, "♫")

        right_margin = bg_rect.right() - 12
        dur_str = index.data(Qt.ItemDataRole.UserRole + 2) or ""
        if dur_str:
            painter.setFont(QFont("Sans Serif", 9))
            painter.setPen(QColor(255, 255, 255, 140))
            metrics = QFontMetrics(painter.font())
            dur_width = metrics.horizontalAdvance(dur_str)
            dur_rect = QRect(right_margin - dur_width, bg_rect.top(), dur_width, bg_rect.height())
            painter.drawText(dur_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, dur_str)
            right_margin -= (dur_width + 10)

        if is_playing:
            painter.setFont(QFont("Sans Serif", 10, QFont.Weight.Bold))
            painter.setPen(QColor(clean_accent))
            play_rect = QRect(right_margin - 14, bg_rect.top(), 14, bg_rect.height())
            painter.drawText(play_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter, "▶")
            right_margin -= 18

        text_left = art_rect.right() + 10
        text_width = max(10, right_margin - text_left)

        title_str = index.data(Qt.ItemDataRole.DisplayRole) or "Sin título"
        artist_str = index.data(Qt.ItemDataRole.UserRole + 1) or "Artista desconocido"

        painter.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold if (is_playing or is_selected) else QFont.Weight.Normal))
        painter.setPen(QColor(clean_accent) if is_playing else QColor("#ffffff"))
        title_metrics = QFontMetrics(painter.font())
        elided_title = title_metrics.elidedText(title_str, Qt.TextElideMode.ElideRight, text_width)
        painter.drawText(text_left, bg_rect.top() + 18, elided_title)

        painter.setFont(QFont("Sans Serif", 8))
        painter.setPen(QColor(255, 255, 255, 160))
        artist_metrics = QFontMetrics(painter.font())
        elided_artist = artist_metrics.elidedText(artist_str, Qt.TextElideMode.ElideRight, text_width)
        painter.drawText(text_left, bg_rect.top() + 34, elided_artist)

        painter.restore()


class CurrentQueueDialog(QDialog):
    """Diálogo modal moderno y elegante para ver y buscar en la lista de reproducción en curso."""

    play_requested = pyqtSignal(int)

    def __init__(
        self,
        playlist: List[Dict[str, Any]],
        current_index: int = -1,
        accent_color: str = "#ff1744",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.playlist = list(playlist or [])
        self.current_index = current_index
        self.accent_color = accent_color

        self.setWindowTitle("Lista en Curso")
        self.setFixedSize(480, 560)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._build_ui()
        self._populate_list()

    def _build_ui(self) -> None:
        clean_accent = self.accent_color.split(";")[0].strip() or "#ff1744"

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        frame = QFrame(self)
        frame.setObjectName("QueueMainCard")
        frame.setStyleSheet(f"""
            QFrame#QueueMainCard {{
                background-color: rgba(13, 17, 29, 0.96);
                border: 1.5px solid {clean_accent};
                border-radius: 20px;
            }}
        """)
        f_layout = QVBoxLayout(frame)
        f_layout.setContentsMargins(18, 16, 18, 16)
        f_layout.setSpacing(12)

        # Cabecera
        header = QHBoxLayout()
        header.setSpacing(10)

        lbl_icon = QLabel("🎧", frame)
        lbl_icon.setFont(QFont("Sans Serif", 14))
        lbl_icon.setStyleSheet("border: none; background: transparent;")
        header.addWidget(lbl_icon)

        lbl_title = QLabel("Lista en Curso", frame)
        lbl_title.setFont(QFont("Sans Serif", 13, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #ffffff; border: none; background: transparent;")
        header.addWidget(lbl_title)

        self.lbl_count = QLabel(f"{len(self.playlist)} canciones", frame)
        self.lbl_count.setFont(QFont("Sans Serif", 9))
        self.lbl_count.setStyleSheet("""
            color: rgba(255, 255, 255, 0.70);
            background-color: rgba(255, 255, 255, 0.08);
            border-radius: 10px;
            padding: 2px 8px;
            border: 1px solid rgba(255, 255, 255, 0.12);
        """)
        header.addWidget(self.lbl_count)

        header.addStretch(1)

        btn_close = QPushButton("✕", frame)
        btn_close.setFixedSize(30, 30)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 15px;
                font-size: 15px;
                font-weight: bold;
                padding: 0px;
                text-align: center;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.22);
                color: #ffffff;
            }
        """)
        btn_close.clicked.connect(self.reject)
        header.addWidget(btn_close)
        f_layout.addLayout(header)

        # Buscador elegante
        self.search_input = QLineEdit(frame)
        self.search_input.setPlaceholderText("🔍 Buscar canción, artista o álbum...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setFixedHeight(38)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: rgba(255, 255, 255, 0.07);
                color: #ffffff;
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.16);
                padding: 4px 12px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border: 1.5px solid {clean_accent};
            }}
        """)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        f_layout.addWidget(self.search_input)

        # Lista de canciones
        self.list_widget = QListWidget(frame)
        self.delegate = QueueTrackDelegate(accent_color=self.accent_color, parent=self.list_widget)
        self.list_widget.setItemDelegate(self.delegate)
        self.list_widget.setSpacing(3)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.list_widget.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
            }
        """)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        f_layout.addWidget(self.list_widget, stretch=1)

        # Empty state label
        self.lbl_empty = QLabel("No se encontraron canciones", frame)
        self.lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_empty.setFont(QFont("Sans Serif", 11))
        self.lbl_empty.setStyleSheet("color: rgba(255, 255, 255, 0.50); border: none; background: transparent;")
        self.lbl_empty.hide()
        f_layout.addWidget(self.lbl_empty)

        main_layout.addWidget(frame)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, "_drag_pos"):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def _display_title(self, track: Dict[str, Any]) -> str:
        file_path = track.get("file_path") or track.get("path") or ""
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

    def _populate_list(self) -> None:
        self.list_widget.clear()
        target_item = None

        for idx, track in enumerate(self.playlist):
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, idx)
            item.setData(Qt.ItemDataRole.DisplayRole, self._display_title(track))
            item.setData(Qt.ItemDataRole.UserRole + 1, self._display_artist(track))
            item.setData(Qt.ItemDataRole.UserRole + 2, self._display_duration(track))
            art = track.get("art_url") or track.get("cover_path") or track.get("album_art") or ""
            item.setData(Qt.ItemDataRole.UserRole + 3, art)
            is_cur = (idx == self.current_index)
            item.setData(Qt.ItemDataRole.UserRole + 4, is_cur)
            item.setSizeHint(QSize(0, 50))
            self.list_widget.addItem(item)
            if is_cur:
                target_item = item
                item.setSelected(True)

        if target_item:
            self.list_widget.scrollToItem(target_item, QListWidget.ScrollHint.PositionAtCenter)

        if not self.playlist:
            self.lbl_empty.setText("La lista en curso está vacía")
            self.lbl_empty.show()
            self.list_widget.hide()

    def _on_search_text_changed(self, text: str) -> None:
        query = (text or "").strip().lower()
        visible_count = 0
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if not item:
                continue
            idx = item.data(Qt.ItemDataRole.UserRole)
            if idx is None or not (0 <= idx < len(self.playlist)):
                item.setHidden(True)
                continue
            track = self.playlist[idx]
            title = self._display_title(track).lower()
            artist = self._display_artist(track).lower()
            album = str(track.get("album") or "").lower()
            match = not query or (query in title or query in artist or query in album)
            item.setHidden(not match)
            if match:
                visible_count += 1

        self.lbl_count.setText(f"{visible_count} canciones" if query else f"{len(self.playlist)} canciones")
        self.lbl_empty.setText("No se encontraron canciones" if query else "La lista en curso está vacía")
        self.lbl_empty.setVisible(visible_count == 0)
        self.list_widget.setVisible(visible_count > 0)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        if not item:
            return
        idx = item.data(Qt.ItemDataRole.UserRole)
        if idx is not None and isinstance(idx, int):
            self.current_index = idx
            for i in range(self.list_widget.count()):
                it = self.list_widget.item(i)
                if it:
                    it_idx = it.data(Qt.ItemDataRole.UserRole)
                    it.setData(Qt.ItemDataRole.UserRole + 4, (it_idx == idx))
            self.list_widget.viewport().update()
            self.play_requested.emit(idx)


class ExpandedPageView(QWidget):
    """Vista Principal Expandida Dashboard (Pestañas de Navegación, Buscador, Favoritos y Biblioteca)."""
    play_track_requested = pyqtSignal(int)
    open_personalization_requested = pyqtSignal()
    view_mode_requested = pyqtSignal(str)
    toggle_compact_mode_requested = pyqtSignal()
    toggle_normal_mode_requested = pyqtSignal()
    choose_music_folder_requested = pyqtSignal()

    play_pause_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    next_requested = pyqtSignal()
    prev_requested = pyqtSignal()
    seek_requested = pyqtSignal(int)
    volume_changed = pyqtSignal(float)
    toggle_fav_requested = pyqtSignal()
    loop_requested = pyqtSignal()
    shuffle_requested = pyqtSignal()
    change_background_requested = pyqtSignal()
    toggle_art_mode_requested = pyqtSignal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        audio_engine: Optional[Any] = None,
        config: Optional[Any] = None,
    ) -> None:
        super().__init__(parent)
        self.audio_engine = audio_engine
        self.config = config
        self.accent_color: str = "#ff1744"
        self.brand_name: str = "RED WORLD"
        self.inner_art_mode: str = "auto"
        self.custom_inner_image: str = ""
        self.playlist: List[Dict[str, Any]] = []
        self.current_index: int = -1
        self.current_view_mode: str = "expanded"
        self.active_filter_mode: str = "all"
        self.selected_playlist_name: Optional[str] = None
        self.user_playlists: Dict[str, List[int]] = {"Lista 1": [], "Lista 2": []}
        self._dirty: bool = False
        self._rebuilding: bool = False
        self._current_library_cols: int = 4

        self.init_ui()

    def set_audio_engine(self, engine: Any) -> None:
        self.audio_engine = engine
        if hasattr(self, "music_home_view") and self.music_home_view:
            self.music_home_view.set_audio_engine(engine)
        if hasattr(self, "playlists_page_view") and self.playlists_page_view:
            self.playlists_page_view.set_audio_engine(engine)

    def set_config(self, config: Any) -> None:
        self.config = config

    def set_brand_name(self, name: str) -> None:
        self.brand_name = name or "RED WORLD"
        if hasattr(self, 'sub_brand') and self.sub_brand:
            self.sub_brand.setText(f"{self.brand_name} Edition")
        if hasattr(self, 'lbl_sidebar_brand') and self.lbl_sidebar_brand:
            self.lbl_sidebar_brand.setText("🎧" if getattr(self, 'is_sidebar_collapsed', False) else f"🎧 {self.brand_name.upper()}")

    def init_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # ----------------------------------------------------
        # 1. PANEL LATERAL IZQUIERDO (SIDEBAR DASHBOARD ELEGANTE)
        # ----------------------------------------------------
        self.sidebar_expanded_width = 220
        self.sidebar_collapsed_width = 72
        self.is_sidebar_collapsed = False

        self.sidebar = QFrame(self)
        self.sidebar.setObjectName("ExpandedSidebar")
        self.sidebar.setFixedWidth(self.sidebar_expanded_width)
        self.sidebar.setStyleSheet(
            "QFrame#ExpandedSidebar { background-color: rgba(10, 14, 24, 0.65); border-radius: 20px; border: 1.5px solid rgba(255, 255, 255, 0.14); }"
        )

        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(10, 14, 10, 14)
        self.sidebar_layout.setSpacing(8)

        # A. HEADER: Logo / Nombre de la app + Botón de colapsar (<)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(4, 0, 4, 0)
        header_layout.setSpacing(6)

        self.lbl_sidebar_brand = QLabel(f"🎧 {self.brand_name.upper()}", self.sidebar)
        self.lbl_sidebar_brand.setFont(QFont("Sans Serif", 11, QFont.Weight.Bold))
        self.lbl_sidebar_brand.setStyleSheet("color: #ffffff; border: none; background: transparent;")
        header_layout.addWidget(self.lbl_sidebar_brand, stretch=1)

        self.btn_sidebar_toggle = QPushButton("<", self.sidebar)
        self.btn_sidebar_toggle.setFixedSize(26, 26)
        self.btn_sidebar_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sidebar_toggle.setToolTip("Colapsar barra lateral")
        self.btn_sidebar_toggle.setStyleSheet("""
            QPushButton {
                font-size: 13px;
                font-weight: bold;
                border-radius: 13px;
                background-color: rgba(255, 255, 255, 0.08);
                color: #cbd5e1;
                border: 1px solid rgba(255, 255, 255, 0.14);
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.20);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.30);
            }
        """)
        self.btn_sidebar_toggle.clicked.connect(self.toggle_sidebar)
        header_layout.addWidget(self.btn_sidebar_toggle)
        self.sidebar_layout.addLayout(header_layout)

        self.sidebar_layout.addSpacing(2)

        # B. SECCIÓN "MENU"
        self.lbl_menu_header = QLabel("MENÚ", self.sidebar)
        self.lbl_menu_header.setFont(QFont("Sans Serif", 8, QFont.Weight.Bold))
        self.lbl_menu_header.setStyleSheet("color: #94a3b8; letter-spacing: 1px; border: none; background: transparent; padding-left: 4px;")
        self.sidebar_layout.addWidget(self.lbl_menu_header)

        # 5 Botones de Navegación
        self.btn_nav_music = QPushButton("  🎵   Música", self.sidebar)
        self.btn_nav_music.setToolTip("Música (Inicio Spotify)")

        self.btn_nav_playing = QPushButton("  💿   En Reproducción", self.sidebar)
        self.btn_nav_playing.setToolTip("En Reproducción")

        self.btn_nav_favs = QPushButton("  ♥   Favoritos", self.sidebar)
        self.btn_nav_favs.setToolTip("Favoritos")

        self.btn_nav_albums = QPushButton("  📚   Biblioteca", self.sidebar)
        self.btn_nav_albums.setToolTip("Biblioteca Completa")

        self.btn_nav_playlists = QPushButton("  📋   Listas", self.sidebar)
        self.btn_nav_playlists.setToolTip("Listas de Reproducción")

        self.nav_items_data = [
            (self.btn_nav_music, "🎵", "Música"),
            (self.btn_nav_playing, "💿", "En Reproducción"),
            (self.btn_nav_favs, "♥", "Favoritos"),
            (self.btn_nav_albums, "📚", "Biblioteca"),
            (self.btn_nav_playlists, "📋", "Listas"),
        ]
        self.nav_buttons = [btn for btn, _, _ in self.nav_items_data]
        self.active_nav_button = self.btn_nav_music

        for btn in self.nav_buttons:
            btn.setFixedHeight(38)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.sidebar_layout.addWidget(btn)

        # Contenedor dinámico de listas de reproducción
        self.playlists_container_frame = QWidget(self.sidebar)
        self.playlists_container_frame.setStyleSheet("background: transparent; border: none;")
        playlists_frame_layout = QVBoxLayout(self.playlists_container_frame)
        playlists_frame_layout.setContentsMargins(4, 2, 4, 2)
        playlists_frame_layout.setSpacing(4)

        listas_sub_header = QHBoxLayout()
        lbl_listas_sub = QLabel("Mis Listas", self.playlists_container_frame)
        lbl_listas_sub.setFont(QFont("Sans Serif", 8, QFont.Weight.Bold))
        lbl_listas_sub.setStyleSheet("color: #64748b; border: none;")
        listas_sub_header.addWidget(lbl_listas_sub)
        listas_sub_header.addStretch()

        self.btn_add_list = QPushButton("+", self.playlists_container_frame)
        self.btn_add_list.setFixedSize(20, 20)
        self.btn_add_list.setToolTip("Crear nueva lista")
        self.btn_add_list.setStyleSheet(f"QPushButton {{ background: transparent; border: none; color: {self.accent_color}; font-size: 14px; font-weight: bold; }} QPushButton:hover {{ color: #ffffff; }}")
        self.btn_add_list.clicked.connect(self._create_new_playlist)
        listas_sub_header.addWidget(self.btn_add_list)
        playlists_frame_layout.addLayout(listas_sub_header)

        scroll_playlists = QScrollArea(self.playlists_container_frame)
        scroll_playlists.setWidgetResizable(True)
        scroll_playlists.setFixedHeight(60)
        scroll_playlists.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.playlists_container = QWidget()
        self.playlists_layout = QVBoxLayout(self.playlists_container)
        self.playlists_layout.setContentsMargins(0, 0, 0, 0)
        self.playlists_layout.setSpacing(2)
        scroll_playlists.setWidget(self.playlists_container)
        playlists_frame_layout.addWidget(scroll_playlists)

        self.sidebar_layout.addWidget(self.playlists_container_frame)
        self.sidebar_layout.addStretch(1)

        # C. SEPARADOR HORIZONTAL SUTIL
        self.sidebar_sep = QFrame(self.sidebar)
        self.sidebar_sep.setFrameShape(QFrame.Shape.HLine)
        self.sidebar_sep.setStyleSheet("background-color: rgba(255, 255, 255, 0.12); max-height: 1px; border: none; margin: 4px 2px;")
        self.sidebar_layout.addWidget(self.sidebar_sep)

        # D. SECCIÓN "SETTINGS"
        self.lbl_settings_header = QLabel("AJUSTES", self.sidebar)
        self.lbl_settings_header.setFont(QFont("Sans Serif", 8, QFont.Weight.Bold))
        self.lbl_settings_header.setStyleSheet("color: #94a3b8; letter-spacing: 1px; border: none; background: transparent; padding-left: 4px;")
        self.sidebar_layout.addWidget(self.lbl_settings_header)

        # Fila de 5 botones de Ajustes: [▣] [▤] [▦] [🎨] [📁]
        self.settings_cards_container = QWidget(self.sidebar)
        self.settings_cards_container.setStyleSheet("background: transparent; border: none;")
        self.settings_grid_layout = QGridLayout(self.settings_cards_container)
        self.settings_grid_layout.setContentsMargins(0, 2, 0, 2)
        self.settings_grid_layout.setSpacing(4)

        card_btn_style = """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 8px;
                color: #e2e8f0;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.16);
                border: 1px solid rgba(255, 255, 255, 0.25);
                color: #ffffff;
            }
        """

        self.btn_set_mode_small = QPushButton("▣", self.settings_cards_container)
        self.btn_set_mode_small.setFixedSize(36, 32)
        self.btn_set_mode_small.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_set_mode_small.setToolTip("Modo Pequeño")
        self.btn_set_mode_small.setStyleSheet(card_btn_style)
        self.btn_set_mode_small.clicked.connect(lambda: self._on_mode_button_clicked("normal"))
        self.settings_grid_layout.addWidget(self.btn_set_mode_small, 0, 0)

        self.btn_set_mode_compact = QPushButton("▤", self.settings_cards_container)
        self.btn_set_mode_compact.setFixedSize(36, 32)
        self.btn_set_mode_compact.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_set_mode_compact.setToolTip("Modo Compacto")
        self.btn_set_mode_compact.setStyleSheet(card_btn_style)
        self.btn_set_mode_compact.clicked.connect(lambda: self._on_mode_button_clicked("compact"))
        self.settings_grid_layout.addWidget(self.btn_set_mode_compact, 0, 1)

        self.btn_set_mode_expanded = QPushButton("▦", self.settings_cards_container)
        self.btn_set_mode_expanded.setFixedSize(36, 32)
        self.btn_set_mode_expanded.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_set_mode_expanded.setToolTip("Modo Expandido")
        self.btn_set_mode_expanded.setStyleSheet(card_btn_style)
        self.btn_set_mode_expanded.clicked.connect(lambda: self._on_mode_button_clicked("expanded"))
        self.settings_grid_layout.addWidget(self.btn_set_mode_expanded, 0, 2)

        self.btn_set_theme = QPushButton("🎨", self.settings_cards_container)
        self.btn_set_theme.setFixedSize(36, 32)
        self.btn_set_theme.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_set_theme.setToolTip("Personalización y Temas Neón")
        self.btn_set_theme.setStyleSheet(card_btn_style)
        self.btn_set_theme.clicked.connect(self.open_personalization_requested)
        self.settings_grid_layout.addWidget(self.btn_set_theme, 0, 3)

        self.btn_set_folder = QPushButton("📁", self.settings_cards_container)
        self.btn_set_folder.setFixedSize(36, 32)
        self.btn_set_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_set_folder.setToolTip("Elegir Carpeta de Música")
        self.btn_set_folder.setStyleSheet(card_btn_style)
        self.btn_set_folder.clicked.connect(self.choose_music_folder_requested)
        self.settings_grid_layout.addWidget(self.btn_set_folder, 0, 4)

        self.sidebar_layout.addWidget(self.settings_cards_container)

        main_layout.addWidget(self.sidebar)

        # ----------------------------------------------------
        # 2. ÁREA CENTRAL PRINCIPAL (CENTER DASHBOARD)
        # ----------------------------------------------------
        self.center_area = QFrame(self)
        self.center_area.setObjectName("ExpandedCenterArea")
        self.center_area.setStyleSheet("QFrame#ExpandedCenterArea { background-color: rgba(8, 11, 20, 0.40); border-radius: 20px; border: 1.5px solid rgba(255, 255, 255, 0.15); }")
        self.center_area.installEventFilter(self)
        center_layout = QVBoxLayout(self.center_area)
        center_layout.setContentsMargins(18, 16, 18, 16)
        center_layout.setSpacing(12)

        # Botón de Acción Cerrar Aplicación (Overlay circular flotante)
        self.btn_close = QPushButton("×", self.center_area)
        self.btn_close.setObjectName("ExpandedCloseBtn")
        self.btn_close.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.btn_close.setFixedSize(32, 32)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setToolTip("Cerrar")
        self.btn_close.setStyleSheet(
            "QPushButton#ExpandedCloseBtn { font-size: 16px; font-weight: bold; border-radius: 16px; padding: 0px; border: 1px solid rgba(255, 255, 255, 0.20); background: rgba(20, 24, 38, 0.70); color: #ff1744; } "
            "QPushButton#ExpandedCloseBtn:hover { color: #ffffff; background-color: #ff1744; border: 1px solid #ff1744; }"
        )
        self.btn_close.clicked.connect(QApplication.instance().quit)

        self.update_active_view_mode("expanded")

        # Sub-páginas apiladas (Index 0: Home Música, Index 1: Biblioteca/Listas, Index 2: En Reproducción)
        self.center_stack = QStackedWidget(self.center_area)

        # ----------------------------------------------------
        # PAGE 0: VISTA MÚSICA (Spotify Home: Búsqueda, Recientes, Top, Listas)
        # ----------------------------------------------------
        self.music_home_view = MusicHomeView(
            accent_color=self.accent_color,
            audio_engine=self.audio_engine,
            parent=self.center_area,
        )
        self.music_home_view.play_track_requested.connect(self._on_home_play_track_requested)
        self.music_home_view.play_all_requested.connect(self._on_home_play_all_requested)
        self.music_home_view.playlist_changed.connect(self._refresh_playlists_sidebar_ui)
        self.center_stack.addWidget(self.music_home_view)

        # ----------------------------------------------------
        # PAGE 1: VISTA BIBLIOTECA / FAVORITOS
        # ----------------------------------------------------
        self.page_library = QWidget()
        page_lib_layout = QVBoxLayout(self.page_library)
        page_lib_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_lib = QScrollArea(self.page_library)
        self.scroll_lib.setWidgetResizable(True)
        self.scroll_lib.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.scroll_lib.verticalScrollBar().valueChanged.connect(self._on_scroll_grid_value_changed)

        scroll_content = QWidget()
        scroll_content_layout = QVBoxLayout(scroll_content)
        scroll_content_layout.setContentsMargins(14, 4, 14, 10)
        scroll_content_layout.setSpacing(16)

        # 1. Sección Escuchados recientemente
        self.lbl_recents_title = QLabel("Escuchados recientemente", scroll_content)
        self.lbl_recents_title.setFont(QFont("Sans Serif", 12, QFont.Weight.Bold))
        self.lbl_recents_title.setStyleSheet("color: #ffffff; letter-spacing: 0.3px;")
        scroll_content_layout.addWidget(self.lbl_recents_title)

        self.recents_scroll = QScrollArea(scroll_content)
        self.recents_scroll.setFixedHeight(248)
        self.recents_scroll.setWidgetResizable(True)
        self.recents_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.recents_widget = QWidget()
        self.recents_layout = QHBoxLayout(self.recents_widget)
        self.recents_layout.setContentsMargins(0, 0, 0, 0)
        self.recents_layout.setSpacing(18)
        self.recents_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.recents_scroll.setWidget(self.recents_widget)
        scroll_content_layout.addWidget(self.recents_scroll)

        # 2. Sección Todas tus canciones
        self.lbl_songs_title = QLabel("Todas tus canciones", scroll_content)
        self.lbl_songs_title.setFont(QFont("Sans Serif", 12, QFont.Weight.Bold))
        self.lbl_songs_title.setStyleSheet("color: #ffffff; letter-spacing: 0.3px;")
        scroll_content_layout.addWidget(self.lbl_songs_title)

        self.songs_grid_widget = QWidget(scroll_content)
        self.songs_grid_layout = QGridLayout(self.songs_grid_widget)
        self.songs_grid_layout.setContentsMargins(0, 0, 0, 0)
        self.songs_grid_layout.setSpacing(18)
        self.songs_grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        scroll_content_layout.addWidget(self.songs_grid_widget)
        scroll_content_layout.addStretch(1)

        self.scroll_lib.setWidget(scroll_content)
        page_lib_layout.addWidget(self.scroll_lib)
        self.center_stack.addWidget(self.page_library)

        # ----------------------------------------------------
        # PAGE 1: VISTA EN REPRODUCCIÓN (Dedicated Now Playing View)
        # Inspirada fielmente en la interfaz de tocadiscos con letras divididas
        # ----------------------------------------------------
        self.page_now_playing = QWidget()
        page_np_layout = QHBoxLayout(self.page_now_playing)
        page_np_layout.setContentsMargins(18, 12, 18, 16)
        page_np_layout.setSpacing(22)

        # ----------------------------------------------------
        # PANEL IZQUIERDO: TOCADISCOS / VINILO GIRATORIO + CONTROLES + BARRA DE PROGRESO
        # ----------------------------------------------------
        self.left_np_frame = QFrame(self.page_now_playing)
        self.left_np_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(10, 12, 22, 0.60);
                border-radius: 24px;
                border: 1.5px solid rgba(255, 255, 255, 0.12);
            }
        """)
        left_np_layout = QVBoxLayout(self.left_np_frame)
        left_np_layout.setContentsMargins(18, 10, 18, 12)
        left_np_layout.setSpacing(6)

        # 1. Tocadiscos / Disco de Vinilo con Brazo Animado
        self.turntable_widget = VinylTurntableWidget(self.left_np_frame)
        self.artwork_ekg_widget = self.turntable_widget  # Compatibilidad con métodos existentes
        left_np_layout.addWidget(self.turntable_widget, alignment=Qt.AlignmentFlag.AlignCenter, stretch=1)

        # 2. Fila de Controles de Reproducción Simétricos y Circulares de Vidrio
        controls_row = QHBoxLayout()
        controls_row.setSpacing(16)
        controls_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.np_btn_loop = QPushButton("↻", self.left_np_frame)
        self.np_btn_loop.setFixedSize(40, 40)
        self.np_btn_loop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.np_btn_loop.setToolTip("Modo Bucle (Loop)")
        self.np_btn_loop.setStyleSheet("QPushButton { background-color: rgba(255, 255, 255, 0.08); border: 1.5px solid rgba(255, 255, 255, 0.18); border-radius: 20px; color: #ffffff; font-size: 15px; font-weight: bold; } QPushButton:hover { background-color: rgba(255, 255, 255, 0.22); }")
        self.np_btn_loop.clicked.connect(self.loop_requested)
        controls_row.addWidget(self.np_btn_loop)

        self.np_btn_prev = QPushButton("⏮", self.left_np_frame)
        self.np_btn_prev.setFixedSize(48, 48)
        self.np_btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self.np_btn_prev.setToolTip("Pista anterior")
        self.np_btn_prev.setStyleSheet("QPushButton { background-color: rgba(255, 255, 255, 0.12); border: 1.5px solid rgba(255, 255, 255, 0.25); border-radius: 24px; color: #ffffff; font-size: 17px; font-weight: bold; } QPushButton:hover { background-color: rgba(255, 255, 255, 0.28); }")
        self.np_btn_prev.clicked.connect(self.prev_requested)
        controls_row.addWidget(self.np_btn_prev)

        clean_accent = self.accent_color.split(';')[0].strip() if self.accent_color else "#ff1744"
        self.np_btn_play = QPushButton("▶", self.left_np_frame)
        self.np_btn_play.setObjectName("PlayButton")
        self.np_btn_play.setFixedSize(62, 62)
        self.np_btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
        self.np_btn_play.setToolTip("Reproducir / Pausar")
        self.np_btn_play.setStyleSheet(f"QPushButton {{ background-color: #ffffff; border: none; border-radius: 31px; color: {clean_accent}; font-size: 24px; font-weight: bold; }} QPushButton:hover {{ background-color: #f1f5f9; }}")
        self.np_btn_play.clicked.connect(self.play_pause_requested)
        controls_row.addWidget(self.np_btn_play)

        self.np_btn_next = QPushButton("⏭", self.left_np_frame)
        self.np_btn_next.setFixedSize(48, 48)
        self.np_btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.np_btn_next.setToolTip("Pista siguiente")
        self.np_btn_next.setStyleSheet("QPushButton { background-color: rgba(255, 255, 255, 0.12); border: 1.5px solid rgba(255, 255, 255, 0.25); border-radius: 24px; color: #ffffff; font-size: 17px; font-weight: bold; } QPushButton:hover { background-color: rgba(255, 255, 255, 0.28); }")
        self.np_btn_next.clicked.connect(self.next_requested)
        controls_row.addWidget(self.np_btn_next)

        self.np_btn_mute = QPushButton("🔊", self.left_np_frame)
        self.np_btn_mute.setFixedSize(40, 40)
        self.np_btn_mute.setCursor(Qt.CursorShape.PointingHandCursor)
        self.np_btn_mute.setToolTip("Silenciar / Desilenciar")
        self.np_btn_mute.setStyleSheet("QPushButton { background-color: rgba(255, 255, 255, 0.08); border: 1.5px solid rgba(255, 255, 255, 0.18); border-radius: 20px; color: #ffffff; font-size: 14px; } QPushButton:hover { background-color: rgba(255, 255, 255, 0.22); }")
        self.np_btn_mute.clicked.connect(self._toggle_np_mute)
        controls_row.addWidget(self.np_btn_mute)

        left_np_layout.addLayout(controls_row)

        left_np_layout.addSpacing(4)

        # 3. Fila de Progreso y Tiempo
        time_row = QHBoxLayout()
        time_row.setSpacing(12)

        self.np_time_left = QLabel("00:00", self.left_np_frame)
        self.np_time_left.setFixedWidth(46)
        self.np_time_left.setFont(QFont("Sans Serif", 10, QFont.Weight.Bold))
        self.np_time_left.setStyleSheet("color: #cbd5e1; background: transparent; border: none;")
        self.np_time_left.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        time_row.addWidget(self.np_time_left)

        self.np_progress_bar = QSlider(Qt.Orientation.Horizontal, self.left_np_frame)
        self.np_progress_bar.setObjectName("ProgressBar")
        self.np_progress_bar.setRange(0, 1000)
        self.np_progress_bar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.np_progress_bar.sliderPressed.connect(self._on_np_slider_pressed)
        self.np_progress_bar.sliderReleased.connect(self._on_np_slider_released)
        time_row.addWidget(self.np_progress_bar, stretch=1)

        self.np_time_right = QLabel("-00:00", self.left_np_frame)
        self.np_time_right.setFixedWidth(46)
        self.np_time_right.setFont(QFont("Sans Serif", 10, QFont.Weight.Bold))
        self.np_time_right.setStyleSheet("color: #94a3b8; background: transparent; border: none;")
        self.np_time_right.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        time_row.addWidget(self.np_time_right)

        left_np_layout.addLayout(time_row)

        # Slider de volumen Y2K integrado en memoria y sincronización de volumen
        self.np_slider_volume = Y2KVolumeSlider(self.left_np_frame)
        self.np_slider_volume.setObjectName("VolumeSlider")
        self.np_slider_volume.setRange(0, 100)
        self.np_slider_volume.setValue(100)
        self.np_slider_volume.set_accent_color(self.accent_color)
        self.np_slider_volume.valueChanged.connect(self._on_np_vol_changed)
        self.np_slider_volume.setVisible(False)

        left_np_layout.addSpacing(6)

        page_np_layout.addWidget(self.left_np_frame, stretch=10)

        # ----------------------------------------------------
        # PANEL DERECHO: TÍTULO / ARTISTA + LETRAS DE LA CANCIÓN + BARRA DE ACCIONES
        # ----------------------------------------------------
        self.right_np_frame = QFrame(self.page_now_playing)
        self.right_np_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(10, 12, 22, 0.45);
                border-radius: 24px;
                border: 1.5px solid rgba(255, 255, 255, 0.10);
            }
        """)
        right_np_layout = QVBoxLayout(self.right_np_frame)
        right_np_layout.setContentsMargins(22, 12, 22, 14)
        right_np_layout.setSpacing(8)

        # 1. Cabecera con Título y Artista
        header_np_right = QVBoxLayout()
        header_np_right.setSpacing(3)

        self.np_song_title = MarqueeLabel("Sin reproducción", font=QFont("Sans Serif", 18, QFont.Weight.Bold), color_str="#ffffff", parent=self.right_np_frame)
        self.np_song_title.setFixedHeight(34)
        header_np_right.addWidget(self.np_song_title)

        self.np_song_artist = MarqueeLabel("Selecciona una canción", font=QFont("Sans Serif", 12), color_str="#94a3b8", parent=self.right_np_frame)
        self.np_song_artist.setFixedHeight(24)
        header_np_right.addWidget(self.np_song_artist)

        self.np_song_album = QLabel("", self.right_np_frame)
        self.np_song_album.setFont(QFont("Sans Serif", 9))
        self.np_song_album.setStyleSheet("color: #64748b; border: none; background: transparent;")
        self.np_song_album.setFixedHeight(16)
        header_np_right.addWidget(self.np_song_album)

        right_np_layout.addLayout(header_np_right)

        # 2. Área de Letras de la Canción (Visualización sincronizada / texto plano)
        self.lyrics_display_widget = LyricsDisplayWidget(self.right_np_frame)
        self.lyrics_display_widget.seek_requested.connect(self._on_lyrics_seek_requested)
        self.lyrics_container = self.lyrics_display_widget
        right_np_layout.addWidget(self.lyrics_display_widget, stretch=1)

        # 3. Barra de Acciones Inferior (Favoritos, Aleatorio, Añadir a Playlist)
        actions_row = QHBoxLayout()
        actions_row.setSpacing(14)
        actions_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.np_btn_fav = QPushButton("♡", self.right_np_frame)
        self.np_btn_fav.setFixedSize(40, 40)
        self.np_btn_fav.setCursor(Qt.CursorShape.PointingHandCursor)
        self.np_btn_fav.setToolTip("Marcar como Favorita (Ctrl+F)")
        self.np_btn_fav.setStyleSheet("QPushButton { background-color: rgba(255, 255, 255, 0.08); border: 1.5px solid rgba(255, 255, 255, 0.18); border-radius: 20px; color: #ffffff; font-size: 15px; font-weight: bold; } QPushButton:hover { background-color: rgba(255, 255, 255, 0.22); }")
        self.np_btn_fav.clicked.connect(self.toggle_fav_requested)
        actions_row.addWidget(self.np_btn_fav)

        self.np_btn_shuffle = QPushButton("⇄", self.right_np_frame)
        self.np_btn_shuffle.setFixedSize(40, 40)
        self.np_btn_shuffle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.np_btn_shuffle.setToolTip("Modo Aleatorio (Shuffle)")
        self.np_btn_shuffle.setStyleSheet("QPushButton { background-color: rgba(255, 255, 255, 0.08); border: 1.5px solid rgba(255, 255, 255, 0.18); border-radius: 20px; color: #ffffff; font-size: 15px; font-weight: bold; } QPushButton:hover { background-color: rgba(255, 255, 255, 0.22); }")
        self.np_btn_shuffle.clicked.connect(self.shuffle_requested)
        actions_row.addWidget(self.np_btn_shuffle)

        self.np_btn_add_playlist = QPushButton("＋", self.right_np_frame)
        self.np_btn_add_playlist.setFixedSize(40, 40)
        self.np_btn_add_playlist.setCursor(Qt.CursorShape.PointingHandCursor)
        self.np_btn_add_playlist.setToolTip("Añadir a una lista de reproducción")
        self.np_btn_add_playlist.setStyleSheet("QPushButton { background-color: rgba(255, 255, 255, 0.08); border: 1.5px solid rgba(255, 255, 255, 0.18); border-radius: 20px; color: #ffffff; font-size: 18px; font-weight: bold; } QPushButton:hover { background-color: rgba(255, 255, 255, 0.22); }")
        self.np_btn_add_playlist.clicked.connect(self._on_np_add_playlist_clicked)
        actions_row.addWidget(self.np_btn_add_playlist)

        self.np_btn_queue = QPushButton("📑", self.right_np_frame)
        self.np_btn_queue.setFixedSize(40, 40)
        self.np_btn_queue.setCursor(Qt.CursorShape.PointingHandCursor)
        self.np_btn_queue.setToolTip("Ver lista en curso (Cola de reproducción)")
        self.np_btn_queue.setStyleSheet("QPushButton { background-color: rgba(255, 255, 255, 0.08); border: 1.5px solid rgba(255, 255, 255, 0.18); border-radius: 20px; color: #ffffff; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: rgba(255, 255, 255, 0.22); }")
        self.np_btn_queue.clicked.connect(self._open_current_queue_dialog)
        actions_row.addWidget(self.np_btn_queue)

        right_np_layout.addLayout(actions_row)

        page_np_layout.addWidget(self.right_np_frame, stretch=10)

        # Cola auxiliar en memoria (compatibilidad)
        self.right_queue_frame = QFrame()
        self.queue_list_widget = QListWidget(self.right_queue_frame)
        self.center_stack.addWidget(self.page_now_playing)

        # ----------------------------------------------------
        # PAGE 3: VISTA LISTAS (Dedicated Playlists Page)
        # ----------------------------------------------------
        self.playlists_page_view = PlaylistsPageView(
            accent_color=self.accent_color,
            audio_engine=self.audio_engine,
            parent=self.center_area,
        )
        self.playlists_page_view.play_track_requested.connect(self._on_home_play_track_requested)
        self.playlists_page_view.play_all_requested.connect(self._on_home_play_all_requested)
        self.playlists_page_view.playlist_changed.connect(self._refresh_playlists_sidebar_ui)
        self.center_stack.addWidget(self.playlists_page_view)

        center_layout.addWidget(self.center_stack, stretch=1)
        main_layout.addWidget(self.center_area, stretch=1)
        self._reposition_close_button()

        # Conectar botones de navegación lateral
        self.btn_nav_music.clicked.connect(self._on_nav_music_clicked)
        self.btn_nav_playing.clicked.connect(self._on_nav_playing_clicked)
        self.btn_nav_favs.clicked.connect(self._on_nav_favs_clicked)
        self.btn_nav_albums.clicked.connect(self._on_nav_library_clicked)
        self.btn_nav_playlists.clicked.connect(self._on_nav_playlists_clicked)

    def _on_mode_button_clicked(self, mode: str) -> None:
        self.update_active_view_mode(mode)
        self.view_mode_requested.emit(mode)

    def update_active_view_mode(self, mode: str) -> None:
        self.current_view_mode = mode
        clean_hex = self.accent_color.split(';')[0].strip() if self.accent_color else "#ff1744"
        btn_grad = getattr(self, 'btn_gradient_effect', False)
        colors = getattr(self, 'gradient_colors', None)
        text_contrast = get_contrasting_text_color(clean_hex)

        from ui.styles import _build_qlineargradient
        if btn_grad and colors and len(colors) >= 2:
            grad_str = _build_qlineargradient(colors)
            active_bg = f"background: {grad_str};"
            active_hover = f"background: {grad_str}; opacity: 0.9;"
            c0 = colors[0] if colors else clean_hex
            text_contrast = get_contrasting_text_color(c0)
        else:
            active_bg = f"background-color: {clean_hex};"
            active_hover = f"background-color: {clean_hex}; opacity: 0.9;"

        mode_buttons = [
            ("normal", getattr(self, 'btn_set_mode_small', None)),
            ("compact", getattr(self, 'btn_set_mode_compact', None)),
            ("expanded", getattr(self, 'btn_set_mode_expanded', None)),
        ]
        for m_name, btn in mode_buttons:
            if btn:
                if mode == m_name:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            {active_bg}
                            color: {text_contrast};
                            border: 1px solid {clean_hex};
                            border-radius: 8px;
                            font-weight: bold;
                            font-size: 13px;
                        }}
                        QPushButton:hover {{
                            {active_hover}
                            color: {text_contrast};
                        }}
                    """)
                else:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: rgba(255, 255, 255, 0.06);
                            border: 1px solid rgba(255, 255, 255, 0.10);
                            border-radius: 8px;
                            color: #e2e8f0;
                            font-size: 13px;
                        }}
                        QPushButton:hover {{
                            background-color: rgba(255, 255, 255, 0.16);
                            border: 1px solid rgba(255, 255, 255, 0.25);
                            color: #ffffff;
                        }}
                    """)

        if hasattr(self, 'btn_close') and self.btn_close:
            self.btn_close.setStyleSheet(f"""
                QPushButton#ExpandedCloseBtn {{
                    background-color: rgba(20, 24, 38, 0.70);
                    border: 1px solid rgba(255, 255, 255, 0.20);
                    border-radius: 16px;
                    color: {clean_hex};
                    font-size: 16px;
                    font-weight: bold;
                    padding: 0px;
                }}
                QPushButton#ExpandedCloseBtn:hover {{
                    color: #ffffff;
                    background-color: {clean_hex};
                    border: 1px solid {clean_hex};
                }}
                QPushButton#ExpandedCloseBtn:pressed {{
                    background-color: {clean_hex};
                    color: #ffffff;
                }}
            """)

    def _on_home_play_track_requested(self, track_meta: dict) -> None:
        if not self.audio_engine:
            return

        target_path = track_meta.get("file_path") or track_meta.get("path") or ""
        target_id = track_meta.get("track_id", "")

        # 1. Buscar en la cola actual del motor de audio (por track_id o por file_path)
        existing_idx = -1
        current_pl = getattr(self.audio_engine, "playlist", []) or []
        for idx, t in enumerate(current_pl):
            t_id = t.get("track_id", "")
            t_path = t.get("file_path") or t.get("path") or ""
            if (target_id and t_id and target_id == t_id) or (target_path and t_path and target_path == t_path):
                existing_idx = idx
                break

        # 2. Si ya está en la cola, saltar directamente a su posición existente
        if existing_idx != -1:
            if hasattr(self.audio_engine, "play_index"):
                self.audio_engine.play_index(existing_idx)
        else:
            # 3. Solo agregar al final si genuinamente no está
            if hasattr(self.audio_engine, "playlist"):
                self.audio_engine.playlist.append(track_meta)
                if hasattr(self.audio_engine, "playlist_updated"):
                    self.audio_engine.playlist_updated.emit(self.audio_engine.playlist)
                if hasattr(self.audio_engine, "play_index"):
                    self.audio_engine.play_index(len(self.audio_engine.playlist) - 1)

    def _on_home_play_all_requested(self, tracks_list: list) -> None:
        if not tracks_list or not self.audio_engine:
            return
        if hasattr(self.audio_engine, "playlist"):
            self.audio_engine.playlist = list(tracks_list)
            if hasattr(self.audio_engine, "playlist_updated"):
                self.audio_engine.playlist_updated.emit(self.audio_engine.playlist)
            if hasattr(self.audio_engine, "play_index"):
                self.audio_engine.play_index(0)

    def _on_nav_music_clicked(self) -> None:
        self.active_filter_mode = "all"
        self.active_nav_button = self.btn_nav_music
        self._highlight_nav_button(self.btn_nav_music)
        if hasattr(self, "music_home_view") and self.music_home_view:
            self.center_stack.setCurrentWidget(self.music_home_view)
            self.music_home_view.refresh_all()
        else:
            self.center_stack.setCurrentIndex(0)

    def _on_nav_playing_clicked(self) -> None:
        self.active_nav_button = self.btn_nav_playing
        self._highlight_nav_button(self.btn_nav_playing)
        if hasattr(self, "page_now_playing") and self.page_now_playing:
            self.center_stack.setCurrentWidget(self.page_now_playing)
        else:
            self.center_stack.setCurrentIndex(1)

    def _on_nav_favs_clicked(self) -> None:
        self.active_filter_mode = "favorites"
        self.active_nav_button = self.btn_nav_favs
        self._highlight_nav_button(self.btn_nav_favs)
        if hasattr(self, "page_library") and self.page_library:
            self.center_stack.setCurrentWidget(self.page_library)

        fav_tracks = [dict(t) for t in self.playlist if self._is_track_favorite(t)]
        
        if self.config and hasattr(self.config, "get"):
            saved_favs = self.config.get("favorites", [])
            existing_keys = {
                ( (t.get("title") or "").strip().lower(), (t.get("artist") or "").strip().lower() )
                for t in fav_tracks
            }
            for sf in saved_favs:
                t_clean = (sf.get("title") or "").strip().lower()
                a_clean = (sf.get("artist") or "").strip().lower()
                if t_clean and (t_clean, a_clean) not in existing_keys:
                    fav_tracks.append({
                        "title": sf.get("title", ""),
                        "artist": sf.get("artist", ""),
                        "album": sf.get("album", ""),
                        "art_url": sf.get("art_url", ""),
                        "path": sf.get("path", "")
                    })
                    existing_keys.add((t_clean, a_clean))
        
        self.lbl_recents_title.setVisible(False)
        self.recents_scroll.setVisible(False)
        self.lbl_songs_title.setText(f"♥ Tus Canciones Favoritas ({len(fav_tracks)})")

        self.update_playlist_ui(fav_tracks, 0, is_filtered_view=True, show_recents=False)

    def set_album_art(self, pixmap: Optional[QPixmap]) -> None:
        if hasattr(self, 'artwork_ekg_widget') and self.artwork_ekg_widget:
            self.artwork_ekg_widget.set_album_art(pixmap)

    def set_accent_color(self, hex_color: str, btn_gradient_effect: bool = False, gradient_colors: list = None) -> None:
        clean_hex = hex_color.split(';')[0].strip() if hex_color else "#ff1744"
        self.accent_color = clean_hex
        self.btn_gradient_effect = btn_gradient_effect
        self.gradient_colors = gradient_colors or [clean_hex, "#0c0c10"]

        qc = QColor(clean_hex)
        if not qc.isValid():
            qc = QColor("#ff1744")
        r, g, b = qc.red(), qc.green(), qc.blue()

        # Dashboards con cristal traslúcido elegante y tinte dinámico visible acorde al tema
        glass_tint_sidebar = f"QFrame#ExpandedSidebar {{ background-color: rgba(10, 14, 24, 0.65); border-radius: 20px; border: 1.5px solid rgba({r}, {g}, {b}, 0.35); }}"
        glass_tint_center = f"QFrame#ExpandedCenterArea {{ background-color: rgba(8, 11, 20, 0.40); border-radius: 20px; border: 1.5px solid rgba({r}, {g}, {b}, 0.25); }}"
        glass_tint_panels = f"QFrame {{ background-color: rgba(10, 14, 24, 0.55); border-radius: 24px; border: 1.5px solid rgba({r}, {g}, {b}, 0.30); }}"

        if hasattr(self, 'sidebar') and self.sidebar:
            self.sidebar.setStyleSheet(glass_tint_sidebar)
        if hasattr(self, 'center_area') and self.center_area:
            self.center_area.setStyleSheet(glass_tint_center)
        if hasattr(self, 'left_np_frame') and self.left_np_frame:
            self.left_np_frame.setStyleSheet(glass_tint_panels)
        if hasattr(self, 'right_np_frame') and self.right_np_frame:
            self.right_np_frame.setStyleSheet(glass_tint_panels)
        if hasattr(self, 'right_queue_frame') and self.right_queue_frame:
            self.right_queue_frame.setStyleSheet(glass_tint_panels)

        # Botón de Play prominente estilo tocadiscos Hi-Fi y controles circulares de cristal
        np_play_style = f"QPushButton#PlayButton {{ background-color: #ffffff; color: {clean_hex}; border-radius: 31px; border: none; font-size: 24px; font-weight: bold; }} QPushButton#PlayButton:hover {{ background-color: #f1f5f9; }}"
        np_ctrl_48_style = f"QPushButton {{ background-color: rgba(255, 255, 255, 0.12); border: 1.5px solid rgba(255, 255, 255, 0.25); border-radius: 24px; color: #ffffff; font-size: 17px; font-weight: bold; }} QPushButton:hover {{ background-color: rgba(255, 255, 255, 0.28); border-color: {clean_hex}; }}"
        np_ctrl_40_style = f"QPushButton {{ background-color: rgba(255, 255, 255, 0.08); border: 1.5px solid rgba(255, 255, 255, 0.18); border-radius: 20px; color: #ffffff; font-size: 15px; font-weight: bold; }} QPushButton:hover {{ background-color: rgba(255, 255, 255, 0.22); border-color: {clean_hex}; }}"

        if hasattr(self, 'np_btn_play') and self.np_btn_play:
            self.np_btn_play.setStyleSheet(np_play_style)
        if hasattr(self, 'np_btn_prev') and self.np_btn_prev:
            self.np_btn_prev.setStyleSheet(np_ctrl_48_style)
        if hasattr(self, 'np_btn_next') and self.np_btn_next:
            self.np_btn_next.setStyleSheet(np_ctrl_48_style)
        if hasattr(self, 'np_btn_mute') and self.np_btn_mute:
            self.np_btn_mute.setStyleSheet(np_ctrl_40_style)
        if hasattr(self, 'np_btn_add_playlist') and self.np_btn_add_playlist:
            self.np_btn_add_playlist.setStyleSheet(np_ctrl_40_style)
        if hasattr(self, 'np_btn_stop') and self.np_btn_stop:
            self.np_btn_stop.setStyleSheet(np_ctrl_40_style)

        # Actualizar botones con estado activo manteniendo radios circulares
        self.update_shuffle_status(getattr(self, 'is_shuffle_active', False))
        self.update_loop_status(getattr(self, 'current_loop_status', 'None'))
        self.update_like_status(getattr(self, 'is_fav_active', False))

        if hasattr(self, 'sub_brand') and self.sub_brand:
            self.sub_brand.setStyleSheet(f"color: #ffffff; background-color: rgba(255, 255, 255, 0.08); padding: 3px 8px; border-radius: 8px; border: 1px solid {clean_hex};")

        # 1. Botón Cambiar Carpeta
        if hasattr(self, 'btn_choose_folder') and self.btn_choose_folder:
            self.btn_choose_folder.setStyleSheet(
                build_button_style(clean_hex, btn_gradient_effect=btn_gradient_effect, gradient_colors=self.gradient_colors, border_radius=14, font_size=11, padding="4px 12px")
            )

        # 2. Botón Nueva Lista
        if hasattr(self, 'btn_add_list') and self.btn_add_list:
            self.btn_add_list.setStyleSheet(
                f"QPushButton {{ color: {clean_hex}; background: transparent; border: none; font-weight: bold; font-size: 16px; text-align: center; }} "
                f"QPushButton:hover {{ color: #ffffff; }}"
            )

        # 3. Botones de Selección de Modo y Personalizar (Navegación Principal)
        self.update_active_view_mode(getattr(self, 'current_view_mode', 'expanded'))

        # 4. Artwork EKG & Artista Marquesina
        if hasattr(self, 'artwork_ekg_widget') and self.artwork_ekg_widget:
            self.artwork_ekg_widget.set_accent_color(clean_hex)

        if hasattr(self, 'np_slider_volume') and self.np_slider_volume:
            self.np_slider_volume.set_accent_color(clean_hex, self.gradient_colors if btn_gradient_effect else [clean_hex, clean_hex])

        if hasattr(self, 'np_song_artist') and self.np_song_artist:
            self.np_song_artist.set_color("#d0d4eb")

        if hasattr(self, 'lyrics_display_widget') and self.lyrics_display_widget:
            self.lyrics_display_widget.set_accent_color(clean_hex)



        # 6.5 Queue List Widget
        if hasattr(self, 'queue_list_widget') and self.queue_list_widget:
            self.queue_list_widget.setStyleSheet(f"""
                QListWidget {{
                    background: transparent;
                    border: none;
                    color: #ffffff;
                }}
                QListWidget::item {{
                    padding: 11px 12px;
                    border-radius: 8px;
                    margin-bottom: 6px;
                    color: #ffffff;
                }}
                QListWidget::item:hover {{
                    background-color: rgba(255, 255, 255, 0.12);
                    color: #ffffff;
                }}
                QListWidget::item:selected {{
                    background-color: rgba(255, 255, 255, 0.18);
                    border: 1.5px solid {clean_hex};
                    color: #ffffff;
                }}
            """)

        # 7. Highlight active nav button
        active_btn = getattr(self, 'active_nav_button', getattr(self, 'btn_nav_music', None))
        if active_btn:
            self._highlight_nav_button(active_btn)

        # 8. Refresh sidebar playlists & grid playlist cards
        self._refresh_playlists_sidebar_ui()
        if hasattr(self, 'music_home_view') and self.music_home_view:
            self.music_home_view.update_accent_color(clean_hex)
        if hasattr(self, 'playlists_page_view') and self.playlists_page_view:
            self.playlists_page_view.set_accent_color(clean_hex)
        if hasattr(self, 'playlist') and self.playlist:
            self.update_playlist_ui(self.playlist, getattr(self, 'current_index', 0), is_filtered_view=(getattr(self, 'active_filter_mode', 'all') != 'all'), show_recents=False)

    def toggle_sidebar(self) -> None:
        self.is_sidebar_collapsed = not getattr(self, 'is_sidebar_collapsed', False)
        target_w = self.sidebar_collapsed_width if self.is_sidebar_collapsed else self.sidebar_expanded_width
        self.sidebar.setFixedWidth(target_w)

        if hasattr(self, 'btn_sidebar_toggle') and self.btn_sidebar_toggle:
            self.btn_sidebar_toggle.setText(">" if self.is_sidebar_collapsed else "<")
            self.btn_sidebar_toggle.setToolTip("Expandir barra lateral" if self.is_sidebar_collapsed else "Colapsar barra lateral")
        
        if hasattr(self, 'lbl_sidebar_brand') and self.lbl_sidebar_brand:
            self.lbl_sidebar_brand.setText("🎧" if self.is_sidebar_collapsed else f"🎧 {self.brand_name.upper()}")

        if hasattr(self, 'lbl_menu_header') and self.lbl_menu_header:
            self.lbl_menu_header.setVisible(not self.is_sidebar_collapsed)

        if hasattr(self, 'lbl_settings_header') and self.lbl_settings_header:
            self.lbl_settings_header.setVisible(not self.is_sidebar_collapsed)

        if hasattr(self, 'playlists_container_frame') and self.playlists_container_frame:
            self.playlists_container_frame.setVisible(not self.is_sidebar_collapsed)

        for btn, icon, text in getattr(self, 'nav_items_data', []):
            if self.is_sidebar_collapsed:
                btn.setText(icon)
            else:
                btn.setText(f"  {icon}   {text}")

        # Reorganizar tarjetas de ajustes (fila horizontal vs cuadrícula compacta)
        card_btns = [
            getattr(self, 'btn_set_mode_small', None),
            getattr(self, 'btn_set_mode_compact', None),
            getattr(self, 'btn_set_mode_expanded', None),
            getattr(self, 'btn_set_theme', None),
            getattr(self, 'btn_set_folder', None),
        ]
        if hasattr(self, 'settings_grid_layout') and self.settings_grid_layout:
            if self.is_sidebar_collapsed:
                for i, b in enumerate(card_btns):
                    if b:
                        b.setFixedSize(22, 22)
                        self.settings_grid_layout.addWidget(b, i // 2, i % 2)
            else:
                for i, b in enumerate(card_btns):
                    if b:
                        b.setFixedSize(36, 32)
                        self.settings_grid_layout.addWidget(b, 0, i)

        self._highlight_nav_button(getattr(self, 'active_nav_button', self.btn_nav_music))
        self._reposition_close_button()

    def _highlight_nav_button(self, active_btn: Optional[QPushButton] = None) -> None:
        clean_accent = self.accent_color.split(';')[0].strip() if self.accent_color else "#ff1744"
        btn_grad_on = getattr(self, 'btn_gradient_effect', False)
        colors = getattr(self, 'gradient_colors', None)
        grad_str = _build_qlineargradient(colors) if (btn_grad_on and colors and len(colors) >= 2) else ""

        is_col = getattr(self, 'is_sidebar_collapsed', False)
        align = "center" if is_col else "left"
        pad_left = "0px" if is_col else "12px"

        for btn in self.nav_buttons:
            if btn == active_btn:
                accent_bg = f"background: {grad_str};" if (btn_grad_on and grad_str) else "background-color: rgba(255, 255, 255, 0.12);"
                btn.setStyleSheet(f"""
                    QPushButton {{
                        text-align: {align};
                        padding-left: {pad_left};
                        font-size: 12px;
                        font-weight: bold;
                        color: #ffffff;
                        {accent_bg}
                        border-left: 3.5px solid {clean_accent};
                        border-top: none;
                        border-right: none;
                        border-bottom: none;
                        border-top-right-radius: 10px;
                        border-bottom-right-radius: 10px;
                        border-top-left-radius: 2px;
                        border-bottom-left-radius: 2px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        text-align: {align};
                        padding-left: {pad_left};
                        font-size: 12px;
                        font-weight: 500;
                        color: #94a3b8;
                        background-color: transparent;
                        border: none;
                        border-radius: 10px;
                    }}
                    QPushButton:hover {{
                        background-color: rgba(255, 255, 255, 0.08);
                        color: #ffffff;
                    }}
                """)

    def _on_nav_playlists_clicked(self) -> None:
        self.active_filter_mode = "playlists"
        self.active_nav_button = self.btn_nav_playlists
        self._highlight_nav_button(self.btn_nav_playlists)
        if hasattr(self, "playlists_page_view") and self.playlists_page_view:
            self.center_stack.setCurrentWidget(self.playlists_page_view)
            self.playlists_page_view.refresh()

    def _is_track_favorite(self, track: dict) -> bool:
        title = track.get("title", "")
        artist = track.get("artist", "")
        if self.config and hasattr(self.config, "is_favorite"):
            return self.config.is_favorite(title, artist)
        return False

    def _create_new_playlist(self) -> None:
        dlg = CreatePlaylistDialog(accent_color=self.accent_color, parent=self.window())
        if dlg.exec() == QDialog.DialogCode.Accepted or getattr(dlg, "result", lambda: 0)() == 1:
            list_name = dlg.get_playlist_name()
            if not list_name:
                return
            from database_manager import get_database_manager
            db = get_database_manager()
            pl_id = db.create_playlist(list_name)
            if pl_id:
                self._refresh_playlists_sidebar_ui()
                if hasattr(self, "playlists_page_view") and self.playlists_page_view:
                    if hasattr(self.playlists_page_view, "refresh_playlists"):
                        self.playlists_page_view.refresh_playlists()
                    elif hasattr(self.playlists_page_view, "refresh"):
                        self.playlists_page_view.refresh()
                if hasattr(self, "music_home_view") and self.music_home_view:
                    if hasattr(self.music_home_view, "refresh_all"):
                        self.music_home_view.refresh_all()
                self._on_playlist_id_clicked(pl_id, list_name)
            else:
                QMessageBox.warning(
                    self,
                    "Nombre duplicado",
                    f"Ya existe una lista llamada '{list_name}'. Elegí otro nombre."
                )

    def _on_np_add_playlist_clicked(self) -> None:
        from database_manager import get_database_manager
        db = get_database_manager()

        meta = self.current_metadata or (getattr(self.audio_engine, "current_metadata", None) if hasattr(self, "audio_engine") else None)
        track_path = ""
        if meta and isinstance(meta, dict):
            track_path = (meta.get("file_path") or meta.get("path") or "").strip()

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(20, 24, 38, 0.95);
                border: 1.5px solid rgba(255, 255, 255, 0.20);
                border-radius: 12px;
                padding: 6px;
                color: #ffffff;
            }
            QMenu::item {
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 13px;
            }
            QMenu::item:selected {
                background-color: rgba(255, 255, 255, 0.18);
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 255, 255, 0.12);
                margin: 4px 8px;
            }
        """)

        act_new = menu.addAction("＋ Nueva lista...")
        menu.addSeparator()

        playlists = db.get_playlists_summary()
        pl_actions = {}
        for pl in playlists:
            act = menu.addAction(f"📋 {pl['name']} ({pl['track_count']})")
            pl_actions[act] = pl['id']

        pos = self.np_btn_add_playlist.mapToGlobal(QPoint(0, self.np_btn_add_playlist.height() + 4))
        action = menu.exec(pos)
        if not action:
            return

        if action == act_new:
            dlg = CreatePlaylistDialog(accent_color=self.accent_color, parent=self.window())
            if dlg.exec() == QDialog.DialogCode.Accepted or getattr(dlg, "result", lambda: 0)() == 1:
                clean_n = dlg.get_playlist_name()
                if not clean_n:
                    return
                pl_id = db.create_playlist(clean_n)
                if pl_id:
                    if meta and track_path:
                        meta_to_add = dict(meta)
                        if "file_path" not in meta_to_add:
                            meta_to_add["file_path"] = track_path
                        db.add_track_to_playlist(pl_id, meta_to_add)
                    self._refresh_playlists_sidebar_ui()
                    if hasattr(self, "playlists_page_view") and self.playlists_page_view:
                        if hasattr(self.playlists_page_view, "refresh_playlists"):
                            self.playlists_page_view.refresh_playlists()
                        elif hasattr(self.playlists_page_view, "refresh"):
                            self.playlists_page_view.refresh()
                    if hasattr(self, "music_home_view") and self.music_home_view:
                        if hasattr(self.music_home_view, "refresh_all"):
                            self.music_home_view.refresh_all()
                else:
                    QMessageBox.warning(
                        self,
                        "Nombre duplicado",
                        f"Ya existe una lista llamada '{clean_n}'. Elegí otro nombre."
                    )
        elif action in pl_actions:
            pl_id = pl_actions[action]
            if meta and track_path:
                meta_to_add = dict(meta)
                if "file_path" not in meta_to_add:
                    meta_to_add["file_path"] = track_path
                db.add_track_to_playlist(pl_id, meta_to_add)
                self._refresh_playlists_sidebar_ui()
                if hasattr(self, "playlists_page_view") and self.playlists_page_view:
                    if hasattr(self.playlists_page_view, "refresh_playlists"):
                        self.playlists_page_view.refresh_playlists()
                    elif hasattr(self.playlists_page_view, "refresh"):
                        self.playlists_page_view.refresh()
                if hasattr(self, "music_home_view") and self.music_home_view:
                    if hasattr(self.music_home_view, "refresh_all"):
                        self.music_home_view.refresh_all()
            else:
                QMessageBox.information(
                    self,
                    "Listas de reproducción",
                    "No hay ninguna canción en reproducción para agregar a la lista."
                )

    def _open_current_queue_dialog(self) -> None:
        playlist = getattr(self, "playlist", [])
        if not playlist and hasattr(self, "audio_engine") and hasattr(self.audio_engine, "playlist"):
            playlist = self.audio_engine.playlist or []

        curr_idx = getattr(self, "current_index", -1)
        if curr_idx < 0 and hasattr(self, "audio_engine") and hasattr(self.audio_engine, "current_index"):
            curr_idx = getattr(self.audio_engine, "current_index", -1)

        dlg = CurrentQueueDialog(
            playlist=playlist,
            current_index=curr_idx,
            accent_color=self.accent_color,
            parent=self.window(),
        )
        dlg.play_requested.connect(self._on_queue_dialog_play_requested)
        dlg.exec()

    def _on_queue_dialog_play_requested(self, index: int) -> None:
        self.play_track_requested.emit(index)
        if hasattr(self, "audio_engine") and hasattr(self.audio_engine, "play_index"):
            self.audio_engine.play_index(index)

    def _refresh_playlists_sidebar_ui(self) -> None:
        while self.playlists_layout.count():
            item = self.playlists_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        from database_manager import get_database_manager
        db = get_database_manager()
        playlists = db.get_playlists_summary()

        for pl in playlists:
            name = pl.get("name", "")
            pl_id = pl.get("id")
            count = pl.get("track_count", 0)
            p_btn = QPushButton(f"▶  {name} ({count})", self.playlists_container)
            p_btn.setFixedHeight(30)
            p_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            p_btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding-left: 10px;
                    font-size: 10px;
                    color: #a0a2b8;
                    background: transparent;
                    border: none;
                }
                QPushButton:hover { color: #ffffff; }
            """)
            p_btn.clicked.connect(lambda checked, pid=pl_id, n=name: self._on_playlist_id_clicked(pid, n))
            self.playlists_layout.addWidget(p_btn)

        self.playlists_layout.addStretch()

    def _on_playlist_id_clicked(self, pl_id: int, pl_name: str) -> None:
        if hasattr(self, "music_home_view") and self.music_home_view:
            self.center_stack.setCurrentWidget(self.music_home_view)
            self.music_home_view.page_playlist_detail.load_playlist(pl_id, pl_name)
            self.music_home_view.content_stack.setCurrentIndex(2)

    def _on_scroll_grid_value_changed(self, value: int) -> None:
        if hasattr(self, 'scroll_lib') and self.scroll_lib:
            vbar = self.scroll_lib.verticalScrollBar()
            if vbar.maximum() > 0 and value >= vbar.maximum() - 250:
                self._load_more_grid_cards()

    def _calculate_library_cols(self) -> int:
        card_w = 168
        spacing = 18
        w = 0
        if hasattr(self, 'scroll_lib') and self.scroll_lib and self.scroll_lib.viewport().width() > 100:
            w = self.scroll_lib.viewport().width() - 32
        elif hasattr(self, 'center_area') and self.center_area and self.center_area.width() > 100:
            w = self.center_area.width() - 64
        elif self.width() > 100:
            w = self.width() - 290
        else:
            w = 800

        return max(3, min(10, int((w + spacing) / (card_w + spacing))))

    def _re_layout_library_grid(self, cols: int) -> None:
        self._current_library_cols = cols
        if not hasattr(self, 'songs_grid_layout') or not self.songs_grid_layout:
            return

        widgets = []
        for i in range(self.songs_grid_layout.count()):
            item = self.songs_grid_layout.itemAt(i)
            if item and item.widget():
                widgets.append(item.widget())

        for w in widgets:
            self.songs_grid_layout.removeWidget(w)

        for idx, w in enumerate(widgets):
            row = idx // cols
            col = idx % cols
            self.songs_grid_layout.addWidget(w, row, col)

    def _load_more_grid_cards(self) -> None:
        if getattr(self, '_is_loading_more', False):
            return
        display_tracks = getattr(self, '_display_tracks', [])
        if not display_tracks:
            return
        
        current_loaded = getattr(self, '_loaded_cards_count', 0)
        total_tracks = len(display_tracks)
        if current_loaded >= total_tracks:
            return

        self._is_loading_more = True
        batch_size = 40
        next_count = min(current_loaded + batch_size, total_tracks)
        cols = self._calculate_library_cols()
        self._current_library_cols = cols

        for idx in range(current_loaded, next_count):
            track = display_tracks[idx]
            row = idx // cols
            col = idx % cols
            is_curr = (idx == self.current_index)
            card = SongCardWidget(
                track_index=idx,
                title=track.get("title", "Sin título"),
                artist=track.get("artist", "Artista desconocido"),
                art_url=track.get("art_url", ""),
                accent_color=self.accent_color,
                is_playing=is_curr,
                parent=self.songs_grid_widget
            )
            card.card_clicked.connect(self.play_track_requested)
            self.songs_grid_layout.addWidget(card, row, col)

        self._loaded_cards_count = next_count
        self._is_loading_more = False

    def _get_recent_tracks(self) -> List[Dict[str, Any]]:
        parent_player = self.parentWidget()
        while parent_player and not hasattr(parent_player, "config"):
            parent_player = parent_player.parentWidget()
        recents = []
        if parent_player and hasattr(parent_player, "config"):
            recents = parent_player.config.get("recent_tracks", [])
        clean = []
        for r in recents:
            if not isinstance(r, dict):
                continue
            t = (r.get("title") or "").strip()
            a = (r.get("artist") or "").strip()
            if not t or t.lower() in ("sin reproducción", "sin título", "no playback", "test title"):
                continue
            if a.lower() in ("cargando metadatos...", "test artist"):
                continue
            clean.append(r)
        return clean

    def _find_track_index(self, track: dict) -> int:
        t_clean = (track.get("title") or "").strip().lower()
        a_clean = (track.get("artist") or "").strip().lower()
        p_clean = (track.get("file_path") or track.get("path") or "").strip()
        for idx, item in enumerate(self.playlist):
            item_path = (item.get("file_path") or item.get("path") or "").strip()
            if p_clean and item_path == p_clean:
                return idx
            if (item.get("title") or "").strip().lower() == t_clean and (item.get("artist") or "").strip().lower() == a_clean:
                return idx
        return -1

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is getattr(self, 'center_area', None) and event.type() == QEvent.Type.Resize:
            self._reposition_close_button()
            new_cols = self._calculate_library_cols()
            if getattr(self, '_current_library_cols', 4) != new_cols:
                self._re_layout_library_grid(new_cols)
        return super().eventFilter(watched, event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._reposition_close_button()
        new_cols = self._calculate_library_cols()
        if getattr(self, '_current_library_cols', 4) != new_cols:
            self._re_layout_library_grid(new_cols)

    def showEvent(self, event: QShowEvent | None) -> None:
        super().showEvent(event)
        self._reposition_close_button()
        if getattr(self, '_dirty', False):
            self.update_playlist_ui(self.playlist, self.current_index, is_filtered_view=(getattr(self, 'active_filter_mode', 'all') != 'all'), show_recents=False)

    def _reposition_close_button(self) -> None:
        if hasattr(self, "btn_close") and self.btn_close and hasattr(self, "center_area") and self.center_area:
            btn_w = self.btn_close.width()
            x = self.center_area.width() - btn_w - 20
            y = 16
            self.btn_close.move(max(0, x), y)
            self.btn_close.raise_()

    def update_playlist_ui(self, playlist: List[Dict[str, Any]], current_index: int = 0, is_filtered_view: bool = False, show_recents: bool = False) -> None:
        if not is_filtered_view:
            self.playlist = playlist
        self.current_index = current_index
        self._display_tracks = playlist

        if not self.isVisible():
            self._dirty = True
            return

        if self._rebuilding:
            self._dirty = True
            return

        self._rebuilding = True
        self.setUpdatesEnabled(False)
        try:
            self._loaded_cards_count = 0

            while self.recents_layout.count():
                item = self.recents_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            while self.songs_grid_layout.count():
                item = self.songs_grid_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            self.queue_list_widget.clear()

            if not playlist:
                empty_lbl = QLabel("♥ No hay canciones para mostrar aquí aún.\nUsa el buscador o añade canciones a la lista.", self.songs_grid_widget)
                empty_lbl.setFont(QFont("Sans Serif", 10))
                empty_lbl.setStyleSheet("color: #888aa0; padding: 20px;")
                empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.songs_grid_layout.addWidget(empty_lbl, 0, 0)
                self.lbl_recents_title.setVisible(False)
                self.recents_scroll.setVisible(False)
                self._dirty = False
                return

            if show_recents:
                recents = self._get_recent_tracks()
                if recents:
                    self.lbl_recents_title.setVisible(True)
                    self.recents_scroll.setVisible(True)
                    for track in recents[:8]:
                        track_idx = self._find_track_index(track)
                        is_curr = (track_idx >= 0 and track_idx == current_index)
                        card = SongCardWidget(
                            track_index=track_idx if track_idx >= 0 else 0,
                            title=track.get("title", "Sin título"),
                            artist=track.get("artist", "Artista desconocido"),
                            art_url=track.get("art_url", ""),
                            accent_color=self.accent_color,
                            is_playing=is_curr,
                            parent=self.recents_widget
                        )
                        if track_idx >= 0:
                            card.card_clicked.connect(self.play_track_requested)
                        self.recents_layout.addWidget(card)
                else:
                    self.lbl_recents_title.setVisible(False)
                    self.recents_scroll.setVisible(False)
            else:
                self.lbl_recents_title.setVisible(False)
                self.recents_scroll.setVisible(False)

            # Cargar los primeros 60 de forma súper rápida
            self._load_more_grid_cards()

            # Población optimizada de la lista Queue usando setUpdatesEnabled(False)
            self.queue_list_widget.setUpdatesEnabled(False)
            clean_accent = self.accent_color.split(';')[0].strip() if self.accent_color else "#ff1744"
            for idx, track in enumerate(playlist):
                sec = track.get("length_sec", 0)
                mins = sec // 60
                s_rem = sec % 60
                dur_str = f"{mins}:{s_rem:02d}" if sec > 0 else "--:--"
                is_curr = (idx == current_index)
                prefix = "▶ " if is_curr else f"{idx + 1}. "
                item_text = f"{prefix}{track.get('title', 'Sin título')}  —  {track.get('artist', 'Artista')} ({dur_str})"
                
                list_item = QListWidgetItem(item_text)
                list_item.setData(Qt.ItemDataRole.UserRole, idx)
                font = list_item.font()
                if is_curr:
                    font.setBold(True)
                    list_item.setFont(font)
                    list_item.setForeground(QColor("#ffffff"))
                else:
                    font.setBold(False)
                    list_item.setFont(font)
                    list_item.setForeground(QColor("#ffffff"))
                self.queue_list_widget.addItem(list_item)

            self.queue_list_widget.setUpdatesEnabled(True)

            if 0 <= current_index < self.queue_list_widget.count():
                self.queue_list_widget.setCurrentRow(current_index)
            self._dirty = False
        finally:
            self.setUpdatesEnabled(True)
            self._rebuilding = False

    def set_cover_shape(self, shape: str) -> None:
        if hasattr(self, 'artwork_ekg_widget') and self.artwork_ekg_widget:
            self.artwork_ekg_widget.set_cover_shape(shape)

    def update_config_settings(self, config_dict: dict) -> None:
        self.inner_art_mode = config_dict.get("inner_art_mode", "auto")
        self.custom_inner_image = config_dict.get("custom_inner_image", "")
        if "cover_shape" in config_dict:
            self.set_cover_shape(config_dict["cover_shape"])
        if "brand_name" in config_dict:
            self.set_brand_name(config_dict["brand_name"])
        if hasattr(self, 'current_metadata'):
            self.update_metadata(self.current_metadata, self.current_index)
        if hasattr(self, 'playlist') and self.playlist:
            self.update_playlist_ui(self.playlist, self.current_index, is_filtered_view=(self.active_filter_mode != 'all'), show_recents=False)

    def update_metadata(self, metadata: dict, current_index: int = 0) -> None:
        self.current_metadata = metadata
        self.current_index = current_index
        title = metadata.get("title", "Sin reproducción")
        artist = metadata.get("artist", "Selecciona una canción")
        album = metadata.get("album", "")

        self.np_song_title.setText(title or "Sin reproducción")
        self.np_song_artist.setText(artist or "Selecciona una canción")
        if hasattr(self, 'np_song_album') and self.np_song_album:
            self.np_song_album.setText(f"💽 {album}" if album else "")

        # Destacar la canción activa en la lista queue_list_widget
        clean_accent = self.accent_color.split(';')[0].strip() if self.accent_color else "#ff1744"
        for i in range(self.queue_list_widget.count()):
            item = self.queue_list_widget.item(i)
            item_idx = item.data(Qt.ItemDataRole.UserRole)
            if item_idx == current_index:
                self.queue_list_widget.setCurrentRow(i)
                item.setSelected(True)
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                item.setForeground(QColor("#ffffff"))
            else:
                font = item.font()
                font.setBold(False)
                item.setFont(font)
                item.setForeground(QColor("#ffffff"))

        art_url = metadata.get("art_url", "")
        effective_art = art_url
        if self.inner_art_mode == "custom_always" and self.custom_inner_image and os.path.exists(self.custom_inner_image):
            effective_art = self.custom_inner_image

        pix = get_cached_pixmap(effective_art, 320, 320)
        self.artwork_ekg_widget.set_album_art(pix)

        if hasattr(self, 'lyrics_display_widget') and self.lyrics_display_widget:
            self.lyrics_display_widget.load_lyrics_for_track(metadata)

    def set_playing_status(self, is_playing: bool) -> None:
        self.artwork_ekg_widget.set_playing(is_playing)
        icon = "⏸" if is_playing else "▶"
        self.np_btn_play.setText(icon)

    def _on_lyrics_seek_requested(self, time_ms: int) -> None:
        if getattr(self, 'duration_sec', 0) > 0:
            val = int((time_ms / (self.duration_sec * 1000.0)) * 1000)
            self.seek_requested.emit(max(0, min(1000, val)))

    def _on_np_slider_pressed(self) -> None:
        self.is_user_seeking = True

    def _on_np_slider_released(self) -> None:
        self.is_user_seeking = False
        val = self.np_progress_bar.value()
        self.seek_requested.emit(val)

    def _on_np_vol_changed(self, val: int) -> None:
        if hasattr(self, 'np_lbl_vol_val') and self.np_lbl_vol_val:
            self.np_lbl_vol_val.setText(f"{val}%")
        if hasattr(self, 'np_btn_mute') and self.np_btn_mute:
            self.np_btn_mute.setText("🔇" if val == 0 else "🔊")
        self.volume_changed.emit(val / 100.0)

    def _toggle_np_mute(self) -> None:
        if self.np_slider_volume.value() > 0:
            self._last_vol = self.np_slider_volume.value()
            self.np_slider_volume.setValue(0)
        else:
            self.np_slider_volume.setValue(getattr(self, '_last_vol', 100))

    def update_position(self, pos_sec: int, length_sec: int) -> None:
        if getattr(self, 'is_user_seeking', False):
            return
        total_sec = length_sec if length_sec > 0 else getattr(self, 'duration_sec', 0)
        self.duration_sec = total_sec
        if total_sec > 0:
            val = int((pos_sec / total_sec) * 1000)
            self.np_progress_bar.blockSignals(True)
            self.np_progress_bar.setValue(val)
            self.np_progress_bar.blockSignals(False)

            rem_sec = max(0, total_sec - pos_sec)
            pos_min, pos_s = pos_sec // 60, pos_sec % 60
            rem_min, rem_s = rem_sec // 60, rem_sec % 60
            self.np_time_left.setText(f"{pos_min}:{pos_s:02d}")
            self.np_time_right.setText(f"-{rem_min}:{rem_s:02d}")
        else:
            self.np_progress_bar.setValue(0)
            self.np_time_left.setText("0:00")
            self.np_time_right.setText("-0:00")

        if hasattr(self, 'lyrics_display_widget') and self.lyrics_display_widget:
            self.lyrics_display_widget.update_position(int(pos_sec * 1000))

    def update_position_ms(self, pos_ms: int) -> None:
        """Actualiza la visualización de letras en tiempo real a nivel de milisegundos."""
        if hasattr(self, 'lyrics_display_widget') and self.lyrics_display_widget:
            self.lyrics_display_widget.update_position(pos_ms)

    def update_volume(self, volume: float) -> None:
        val = int(max(0.0, min(1.0, volume)) * 100)
        if hasattr(self, 'np_slider_volume') and self.np_slider_volume:
            self.np_slider_volume.blockSignals(True)
            self.np_slider_volume.setValue(val)
            self.np_slider_volume.blockSignals(False)
        if hasattr(self, 'np_lbl_vol_val') and self.np_lbl_vol_val:
            self.np_lbl_vol_val.setText(f"{val}%")
        if hasattr(self, 'np_btn_mute') and self.np_btn_mute:
            self.np_btn_mute.setText("🔇" if val == 0 else "🔊")

    def update_like_status(self, is_fav: bool) -> None:
        self.is_fav_active = is_fav
        clean_hex = self.accent_color.split(';')[0].strip() if self.accent_color else "#ff1744"
        if is_fav:
            self.np_btn_fav.setText("♥")
            grad_str = _build_qlineargradient(self.gradient_colors) if (getattr(self, 'btn_gradient_effect', False) and getattr(self, 'gradient_colors', None) and len(self.gradient_colors) >= 2) else ""
            if grad_str:
                self.np_btn_fav.setStyleSheet(
                    f"QPushButton {{ background: {grad_str}; border: 1.5px solid #ffffff; border-radius: 20px; color: #ffffff; font-size: 15px; font-weight: bold; }} "
                    f"QPushButton:hover {{ background: {grad_str}; border: 1.5px solid #ffffff; color: #ffffff; }} "
                    f"QPushButton:pressed {{ background: {grad_str}; border: 1.5px solid rgba(255, 255, 255, 0.70); color: #dddddd; }}"
                )
            else:
                self.np_btn_fav.setStyleSheet(f"QPushButton {{ background-color: {clean_hex}; border: 1.5px solid #ffffff; border-radius: 20px; color: #ffffff; font-size: 15px; font-weight: bold; }}")
        else:
            self.np_btn_fav.setText("♡")
            self.np_btn_fav.setStyleSheet(f"QPushButton {{ background-color: rgba(255, 255, 255, 0.08); border: 1.5px solid rgba(255, 255, 255, 0.18); border-radius: 20px; color: #ffffff; font-size: 15px; font-weight: bold; }} QPushButton:hover {{ background-color: rgba(255, 255, 255, 0.22); border-color: {clean_hex}; }}")

    def update_loop_status(self, status: str) -> None:
        self.current_loop_status = status
        clean_hex = self.accent_color.split(';')[0].strip() if self.accent_color else "#ff1744"
        if status in ("Track", "Playlist"):
            grad_str = _build_qlineargradient(self.gradient_colors) if (getattr(self, 'btn_gradient_effect', False) and getattr(self, 'gradient_colors', None) and len(self.gradient_colors) >= 2) else ""
            if grad_str:
                self.np_btn_loop.setStyleSheet(
                    f"QPushButton {{ background: {grad_str}; border: 1.5px solid #ffffff; border-radius: 20px; color: #ffffff; font-size: 15px; font-weight: bold; }} "
                    f"QPushButton:hover {{ background: {grad_str}; border: 1.5px solid #ffffff; color: #ffffff; }} "
                    f"QPushButton:pressed {{ background: {grad_str}; border: 1.5px solid rgba(255, 255, 255, 0.70); color: #dddddd; }}"
                )
            else:
                self.np_btn_loop.setStyleSheet(f"QPushButton {{ background-color: {clean_hex}; border: 1.5px solid #ffffff; border-radius: 20px; color: #ffffff; font-size: 15px; font-weight: bold; }}")
        else:
            self.np_btn_loop.setStyleSheet(f"QPushButton {{ background-color: rgba(255, 255, 255, 0.08); border: 1.5px solid rgba(255, 255, 255, 0.18); border-radius: 20px; color: #ffffff; font-size: 15px; font-weight: bold; }} QPushButton:hover {{ background-color: rgba(255, 255, 255, 0.22); border-color: {clean_hex}; }}")

    def update_shuffle_status(self, enabled: bool) -> None:
        self.is_shuffle_active = enabled
        clean_hex = self.accent_color.split(';')[0].strip() if self.accent_color else "#ff1744"
        if enabled:
            grad_str = _build_qlineargradient(self.gradient_colors) if (getattr(self, 'btn_gradient_effect', False) and getattr(self, 'gradient_colors', None) and len(self.gradient_colors) >= 2) else ""
            if grad_str:
                self.np_btn_shuffle.setStyleSheet(
                    f"QPushButton {{ background: {grad_str}; border: 1.5px solid #ffffff; border-radius: 20px; color: #ffffff; font-size: 15px; font-weight: bold; }} "
                    f"QPushButton:hover {{ background: {grad_str}; border: 1.5px solid #ffffff; color: #ffffff; }} "
                    f"QPushButton:pressed {{ background: {grad_str}; border: 1.5px solid rgba(255, 255, 255, 0.70); color: #dddddd; }}"
                )
            else:
                self.np_btn_shuffle.setStyleSheet(f"QPushButton {{ background-color: {clean_hex}; border: 1.5px solid #ffffff; border-radius: 20px; color: #ffffff; font-size: 15px; font-weight: bold; }}")
        else:
            self.np_btn_shuffle.setStyleSheet(f"QPushButton {{ background-color: rgba(255, 255, 255, 0.08); border: 1.5px solid rgba(255, 255, 255, 0.18); border-radius: 20px; color: #ffffff; font-size: 15px; font-weight: bold; }} QPushButton:hover {{ background-color: rgba(255, 255, 255, 0.22); border-color: {clean_hex}; }}")

    def _on_nav_library_clicked(self) -> None:
        self.active_filter_mode = "library"
        self.active_nav_button = self.btn_nav_albums
        self._highlight_nav_button(self.btn_nav_albums)
        if hasattr(self, "page_library") and self.page_library:
            self.center_stack.setCurrentWidget(self.page_library)

        self.lbl_recents_title.setVisible(False)
        self.recents_scroll.setVisible(False)
        total_songs = len(self.playlist)
        self.lbl_songs_title.setText(f"📚 Todas tus canciones ({total_songs})")
        self.update_playlist_ui(self.playlist, self.current_index, is_filtered_view=False, show_recents=False)

    def _on_queue_item_double_clicked(self, item: QListWidgetItem) -> None:
        idx = item.data(Qt.ItemDataRole.UserRole)
        if idx is not None:
            self.play_track_requested.emit(idx)
