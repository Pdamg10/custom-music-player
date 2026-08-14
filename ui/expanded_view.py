import os
import random
import urllib.parse
from typing import Optional, Dict, Any, List
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPoint, QPointF, QRectF, QTimer
from PyQt6.QtGui import QFont, QPixmap, QColor, QPainter, QPainterPath, QPen, QBrush, QIcon, QAction, QLinearGradient, QImage, QImageReader
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QLineEdit, QScrollArea, QFrame, QStackedWidget, QSlider,
    QGridLayout, QSizePolicy, QListWidget, QListWidgetItem,
    QInputDialog, QMenu, QMessageBox
)

from ui.marquee_label import MarqueeLabel
from ui.equalizer_widget import EqualizerWidget
from ui.y2k_volume_slider import Y2KVolumeSlider
from ui.color_extractor import get_contrasting_text_color
from ui.styles import MAIN_STYLE, _build_qlineargradient, build_button_style, build_mode_pill_style

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

def _get_placeholder_pixmap(width: int = 155, height: int = 135, is_playing: bool = False) -> QPixmap:
    key = (width, height, is_playing)
    if key in _PLACEHOLDER_CACHE:
        return _PLACEHOLDER_CACHE[key]
    
    pm = QPixmap(max(1, width), max(1, height))
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, width, height), 12, 12)
    p.setClipPath(path)
    
    grad = QLinearGradient(0, 0, width, height)
    grad.setColorAt(0.0, QColor(24, 28, 48, 230))
    grad.setColorAt(1.0, QColor(10, 12, 22, 250))
    p.fillRect(0, 0, width, height, grad)
    
    p.setPen(QPen(QColor(255, 255, 255, 30), 1.5))
    p.drawRoundedRect(QRectF(0.75, 0.75, width - 1.5, height - 1.5), 12, 12)
    
    p.setPen(QPen(QColor(255, 255, 255, 180)))
    p.setFont(QFont("Sans Serif", max(16, min(width // 4, 28)), QFont.Weight.Bold))
    symbol = "▶ 🎵" if is_playing else "🎧 🎵"
    p.drawText(QRectF(0, 0, width, height), Qt.AlignmentFlag.AlignCenter, symbol)
    p.end()
    
    _PLACEHOLDER_CACHE[key] = pm
    return pm

class ArtworkEKGDisplayWidget(QWidget):
    """Widget de la vista En Reproducción: Imagen de portada central destacada con barras EKG animadas detrás."""
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.album_art: Optional[QPixmap] = None
        self.accent_color: str = "#ff1744"
        self.is_playing: bool = False

        self.setMinimumSize(220, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.num_bars: int = 20
        self.bar_heights: List[float] = [0.08] * self.num_bars
        self.target_heights: List[float] = [random.uniform(0.15, 0.95) for _ in range(self.num_bars)]

        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(40)
        self.anim_timer.timeout.connect(self._update_animation)

    def sizeHint(self) -> QSize:
        return QSize(320, 260)

    def set_playing(self, is_playing: bool) -> None:
        self.is_playing = bool(is_playing)
        if self.is_playing:
            if not self.anim_timer.isActive():
                self.anim_timer.start()
        else:
            if self.anim_timer.isActive():
                self.anim_timer.stop()
            self.bar_heights = [0.08] * self.num_bars
            self.update()

    def set_album_art(self, pixmap: Optional[QPixmap]) -> None:
        self.album_art = pixmap if (pixmap and not pixmap.isNull()) else None
        self.update()

    def set_accent_color(self, hex_color: str) -> None:
        if hex_color:
            self.accent_color = hex_color
        self.update()

    def _update_animation(self) -> None:
        if not self.is_playing:
            return
        for i in range(self.num_bars):
            if abs(self.bar_heights[i] - self.target_heights[i]) < 0.05:
                self.target_heights[i] = random.uniform(0.15, 0.95)
            self.bar_heights[i] += (self.target_heights[i] - self.bar_heights[i]) * 0.15
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w = float(self.width())
        h = float(self.height())

        # Proporción cuadrada de portada adaptada dinámicamente al contenedor
        art_size = max(150.0, min(w * 0.72, h * 0.76, 270.0))
        art_w, art_h = art_size, art_size
        art_x = (w - art_w) / 2.0
        art_y = (h - art_h) / 2.0

        bar_w = max(3.5, min(5.5, art_w / 46.0))
        bar_gap = max(4.0, min(7.5, art_w / 36.0))
        total_bars_w = self.num_bars * (bar_w + bar_gap) - bar_gap
        start_x = (w - total_bars_w) / 2.0
        max_bar_h = min(h - 10.0, art_h + 46.0)

        qc = QColor(self.accent_color.split(';')[0].strip() if self.accent_color else "#ff1744")
        if not qc.isValid():
            qc = QColor("#ff1744")
        r, g, b = qc.red(), qc.green(), qc.blue()

        # 1. Barras EKG animadas en el fondo
        for i in range(self.num_bars):
            bx = start_x + i * (bar_w + bar_gap)
            bh = max(6.0, self.bar_heights[i] * max_bar_h)
            by = (h - bh) / 2.0

            grad = QLinearGradient(bx, by, bx, by + bh)
            grad.setColorAt(0.0, QColor(r, g, b, 230))
            grad.setColorAt(0.5, QColor(0, 229, 255, 190))
            grad.setColorAt(1.0, QColor(224, 64, 251, 210))

            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(grad))
            p.drawRoundedRect(QRectF(bx, by, bar_w, bh), 2.5, 2.5)

        # 2. Resplandor / Borde exterior de la portada
        glow_path = QPainterPath()
        glow_path.addRoundedRect(QRectF(art_x - 3.0, art_y - 3.0, art_w + 6.0, art_h + 6.0), 20.0, 20.0)
        p.setPen(QPen(QColor(r, g, b, 80), 2.0))
        p.setBrush(QBrush(QColor(6, 8, 16, 210)))
        p.drawPath(glow_path)

        # 3. Portada cuadrada con esquinas redondeadas
        path = QPainterPath()
        path.addRoundedRect(QRectF(art_x, art_y, art_w, art_h), 18.0, 18.0)

        p.setPen(QPen(QColor(255, 255, 255, 50), 1.5))
        p.setBrush(QBrush(QColor(10, 12, 22, 240)))
        p.drawPath(path)

        if self.album_art and not self.album_art.isNull():
            p.save()
            p.setClipPath(path)
            scaled = self.album_art.scaled(
                int(art_w), int(art_h),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            sx = int(art_x + (art_w - scaled.width()) / 2.0)
            sy = int(art_y + (art_h - scaled.height()) / 2.0)
            p.drawPixmap(sx, sy, scaled)
            p.restore()
        else:
            p.save()
            p.setClipPath(path)
            ph = _get_placeholder_pixmap(int(art_w), int(art_h), is_playing=self.is_playing)
            p.drawPixmap(int(art_x), int(art_y), ph)
            p.restore()

        p.end()

class SongCardWidget(QFrame):
    """Tarjeta individual para mostrar canciones o álbumes en la vista en grande."""
    card_clicked = pyqtSignal(int)

    def __init__(self, track_index: int, title: str, artist: str, art_url: str, duration_sec: int = 0, accent_color: str = "#ff1744", is_playing: bool = False, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.track_index = track_index
        self.accent_color = accent_color
        self.setFixedSize(175, 215)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        clean_accent = accent_color.split(';')[0].strip() if accent_color else "#ff1744"
        qc = QColor(clean_accent)
        if not qc.isValid():
            qc = QColor("#ff1744")
        r, g, b = qc.red(), qc.green(), qc.blue()

        if is_playing:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: rgba({r}, {g}, {b}, 0.28);
                    border-radius: 16px;
                    border: 2px solid {clean_accent};
                }}
                QFrame:hover {{
                    background-color: rgba({r}, {g}, {b}, 0.40);
                    border: 2px solid {clean_accent};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: rgba({r}, {g}, {b}, 0.12);
                    border-radius: 16px;
                    border: 1px solid rgba({r}, {g}, {b}, 0.28);
                }}
                QFrame:hover {{
                    background-color: rgba({r}, {g}, {b}, 0.24);
                    border: 1.5px solid {clean_accent};
                }}
            """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)

        # Contenedor de Carátula
        self.art_label = QLabel(self)
        self.art_label.setFixedSize(155, 135)
        self.art_label.setStyleSheet("border-radius: 10px; background-color: #080910;")
        self.art_label.setScaledContents(True)
        self.art_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        effective_art = art_url
        custom_art_path = getattr(parent, 'custom_inner_image', '') or ''
        inner_mode = getattr(parent, 'inner_art_mode', 'auto') or 'auto'
        if inner_mode == "custom_always" and custom_art_path and os.path.exists(custom_art_path):
            effective_art = custom_art_path

        pix = get_cached_pixmap(effective_art, 155, 135)
        if pix and not pix.isNull():
            self.art_label.setPixmap(pix)
        else:
            self.art_label.setPixmap(_get_placeholder_pixmap(155, 135, is_playing))

        layout.addWidget(self.art_label)

        # Título (Texto blanco nítido y legible)
        display_title = f"▶ {title}" if is_playing else (title or "Sin título")
        lbl_title = QLabel(display_title, self)
        lbl_title.setFont(QFont("Sans Serif", 10, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #ffffff; border: none; background: transparent;")
        lbl_title.setToolTip(title)
        layout.addWidget(lbl_title)

        # Artista (Texto gris claro nítido y legible)
        lbl_artist = QLabel(artist or "Artista desconocido", self)
        lbl_artist.setFont(QFont("Sans Serif", 9))
        lbl_artist.setStyleSheet("color: #c0c4de; border: none; background: transparent;")
        lbl_artist.setToolTip(artist)
        layout.addWidget(lbl_artist)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.card_clicked.emit(self.track_index)
        super().mousePressEvent(event)

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

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
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

        self.init_ui()

    def set_brand_name(self, name: str) -> None:
        self.brand_name = name or "RED WORLD"
        if hasattr(self, 'sub_brand') and self.sub_brand:
            self.sub_brand.setText(f"{self.brand_name} Edition")

    def init_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # ----------------------------------------------------
        # 1. PANEL LATERAL IZQUIERDO (SIDEBAR DASHBOARD ELEGANTE)
        # ----------------------------------------------------
        self.sidebar = QFrame(self)
        self.sidebar.setFixedWidth(220)
        self.sidebar.setStyleSheet("QFrame { background-color: rgba(10, 12, 22, 0.68); border-radius: 20px; border: 1.5px solid rgba(255, 255, 255, 0.18); }")

        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(14, 16, 14, 16)
        sidebar_layout.setSpacing(10)

        # Brand / Logo
        brand_label = QLabel("🎵 Música", self.sidebar)
        brand_label.setFont(QFont("Sans Serif", 14, QFont.Weight.Bold))
        brand_label.setStyleSheet("color: #ffffff; border: none;")
        sidebar_layout.addWidget(brand_label)

        sidebar_layout.addSpacing(4)

        # Encabezado Dashboard
        lbl_dash_header = QLabel("🎛️ NAVEGACIÓN DASHBOARD", self.sidebar)
        lbl_dash_header.setFont(QFont("Sans Serif", 8, QFont.Weight.Bold))
        lbl_dash_header.setStyleSheet("color: #94a3b8; letter-spacing: 1px; border: none;")
        sidebar_layout.addWidget(lbl_dash_header)

        # Botones de Navegación Lateral (Alta Visibilidad)
        self.btn_nav_music = QPushButton("🎵  Música", self.sidebar)
        self.btn_nav_playing = QPushButton("💿  En Reproducción", self.sidebar)
        self.btn_nav_favs = QPushButton("♥  Favoritos", self.sidebar)
        self.btn_nav_albums = QPushButton("📁  Biblioteca Local", self.sidebar)

        self.nav_buttons = [self.btn_nav_music, self.btn_nav_playing, self.btn_nav_favs, self.btn_nav_albums]
        self.active_nav_button = self.btn_nav_music
        for btn in self.nav_buttons:
            btn.setFixedHeight(42)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding-left: 14px;
                    font-size: 12px;
                    font-weight: bold;
                    color: #f1f5f9;
                    background-color: rgba(255, 255, 255, 0.07);
                    border-radius: 12px;
                    border: 1px solid rgba(255, 255, 255, 0.12);
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.18);
                    color: #ffffff;
                    border: 1px solid rgba(255, 255, 255, 0.30);
                }
            """)
            sidebar_layout.addWidget(btn)

        sidebar_layout.addSpacing(10)

        # Encabezado "Listas" con botón + para añadir lista
        listas_header_layout = QHBoxLayout()
        lbl_listas_header = QLabel("📋 Listas de Reproducción", self.sidebar)
        lbl_listas_header.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        lbl_listas_header.setStyleSheet("color: #e2e8f0; border: none;")
        listas_header_layout.addWidget(lbl_listas_header)
        listas_header_layout.addStretch()

        self.btn_add_list = QPushButton("+", self.sidebar)
        self.btn_add_list.setFixedSize(22, 22)
        self.btn_add_list.setToolTip("Crear nueva lista de reproducción")
        self.btn_add_list.setStyleSheet(f"QPushButton {{ background: transparent; border: none; color: {self.accent_color}; font-size: 16px; font-weight: bold; }} QPushButton:hover {{ color: #ffffff; }}")
        self.btn_add_list.clicked.connect(self._create_new_playlist)
        listas_header_layout.addWidget(self.btn_add_list)
        sidebar_layout.addLayout(listas_header_layout)

        # Scroll para contenedor dinámico de listas
        scroll_playlists = QScrollArea(self.sidebar)
        scroll_playlists.setWidgetResizable(True)
        scroll_playlists.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.playlists_container = QWidget()
        self.playlists_layout = QVBoxLayout(self.playlists_container)
        self.playlists_layout.setContentsMargins(0, 0, 0, 0)
        self.playlists_layout.setSpacing(4)
        scroll_playlists.setWidget(self.playlists_container)
        sidebar_layout.addWidget(scroll_playlists, stretch=1)

        main_layout.addWidget(self.sidebar)

        # ----------------------------------------------------
        # 2. ÁREA CENTRAL PRINCIPAL (CENTER DASHBOARD)
        # ----------------------------------------------------
        self.center_area = QFrame(self)
        self.center_area.setStyleSheet("QFrame { background-color: rgba(8, 10, 18, 0.55); border-radius: 18px; border: 1.5px solid rgba(255, 255, 255, 0.15); }")
        center_layout = QVBoxLayout(self.center_area)
        center_layout.setContentsMargins(16, 14, 16, 14)
        center_layout.setSpacing(10)

        # Barra Superior (Buscador & Acciones)
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        self.search_input = QLineEdit(self.center_area)
        self.search_input.setPlaceholderText("🔍 Buscador de canciones, artista o álbum...")
        self.search_input.setFixedHeight(34)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(20, 22, 34, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 17px;
                padding-left: 16px;
                padding-right: 16px;
                color: #ffffff;
                font-size: 11px;
            }
            QLineEdit:focus {
                border: 1.5px solid #ff1744;
            }
        """)
        top_bar.addWidget(self.search_input, stretch=1)

        # Botones de Selección de Modo (Navegación de la App)
        self.btn_mode_normal = QPushButton("▣ Pequeño", self.center_area)
        self.btn_mode_normal.setFixedHeight(34)
        self.btn_mode_normal.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mode_normal.setToolTip("Cambiar a Modo Pequeño (350x410)")
        self.btn_mode_normal.clicked.connect(lambda: self._on_mode_button_clicked("normal"))
        top_bar.addWidget(self.btn_mode_normal)

        self.btn_mode_compact = QPushButton("▤ Compacto", self.center_area)
        self.btn_mode_compact.setFixedHeight(34)
        self.btn_mode_compact.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mode_compact.setToolTip("Cambiar a Modo Compacto (Barra Flotante)")
        self.btn_mode_compact.clicked.connect(lambda: self._on_mode_button_clicked("compact"))
        top_bar.addWidget(self.btn_mode_compact)

        self.btn_mode_expanded = QPushButton("▦ Expandido", self.center_area)
        self.btn_mode_expanded.setFixedHeight(34)
        self.btn_mode_expanded.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mode_expanded.setToolTip("Modo Expandido Actual (Escritorio)")
        self.btn_mode_expanded.clicked.connect(lambda: self._on_mode_button_clicked("expanded"))
        top_bar.addWidget(self.btn_mode_expanded)

        # Botón Personalizar Único (Abre la ventana emergente con todas las opciones)
        self.btn_settings = QPushButton("⚙ Personalizar", self.center_area)
        self.btn_settings.setFixedHeight(34)
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings.setToolTip("Opciones de Personalización y Temas")
        self.btn_settings.clicked.connect(self.open_personalization_requested)
        top_bar.addWidget(self.btn_settings)

        self.update_active_view_mode("expanded")

        center_layout.addLayout(top_bar)

        # Sub-páginas apiladas (Index 0: Biblioteca, Index 1: En Reproducción)
        self.center_stack = QStackedWidget(self.center_area)

        # ----------------------------------------------------
        # PAGE 0: VISTA BIBLIOTECA / FAVORITOS / LISTAS
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
        scroll_content_layout.setContentsMargins(0, 4, 10, 4)
        scroll_content_layout.setSpacing(14)

        # 1. Sección Escuchados recientemente
        self.lbl_recents_title = QLabel("Escuchados recientemente", scroll_content)
        self.lbl_recents_title.setFont(QFont("Sans Serif", 11, QFont.Weight.Bold))
        self.lbl_recents_title.setStyleSheet("color: #ffffff;")
        scroll_content_layout.addWidget(self.lbl_recents_title)

        self.recents_scroll = QScrollArea(scroll_content)
        self.recents_scroll.setFixedHeight(230)
        self.recents_scroll.setWidgetResizable(True)
        self.recents_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.recents_widget = QWidget()
        self.recents_layout = QHBoxLayout(self.recents_widget)
        self.recents_layout.setContentsMargins(0, 0, 0, 0)
        self.recents_layout.setSpacing(16)
        self.recents_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.recents_scroll.setWidget(self.recents_widget)
        scroll_content_layout.addWidget(self.recents_scroll)

        # 2. Sección Todas tus canciones
        self.lbl_songs_title = QLabel("Todas tus canciones", scroll_content)
        self.lbl_songs_title.setFont(QFont("Sans Serif", 11, QFont.Weight.Bold))
        self.lbl_songs_title.setStyleSheet("color: #ffffff;")
        scroll_content_layout.addWidget(self.lbl_songs_title)

        self.songs_grid_widget = QWidget(scroll_content)
        self.songs_grid_layout = QGridLayout(self.songs_grid_widget)
        self.songs_grid_layout.setContentsMargins(0, 0, 0, 0)
        self.songs_grid_layout.setSpacing(16)
        self.songs_grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        scroll_content_layout.addWidget(self.songs_grid_widget)
        scroll_content_layout.addStretch(1)

        self.scroll_lib.setWidget(scroll_content)
        page_lib_layout.addWidget(self.scroll_lib)
        self.center_stack.addWidget(self.page_library)

        # ----------------------------------------------------
        # PAGE 1: VISTA EN REPRODUCCIÓN (Dedicated Now Playing View)
        # ----------------------------------------------------
        self.page_now_playing = QWidget()
        page_np_layout = QHBoxLayout(self.page_now_playing)
        page_np_layout.setContentsMargins(0, 0, 0, 0)
        page_np_layout.setSpacing(16)

        # Columna Izquierda / Principal: Card Dedicada "En Reproducción"
        self.left_np_frame = QFrame(self.page_now_playing)
        self.left_np_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(8, 10, 20, 0.65);
                border-radius: 20px;
                border: 1.5px solid rgba(255, 255, 255, 0.14);
            }
        """)
        left_np_layout = QVBoxLayout(self.left_np_frame)
        left_np_layout.setContentsMargins(24, 18, 24, 20)
        left_np_layout.setSpacing(8)

        # Header elegante con indicador
        header_row = QHBoxLayout()
        header_row.setSpacing(8)
        lbl_np_title = QLabel("💿 EN REPRODUCCIÓN", self.left_np_frame)
        lbl_np_title.setFont(QFont("Sans Serif", 11, QFont.Weight.Bold))
        lbl_np_title.setStyleSheet("color: #ffffff; letter-spacing: 1.5px; border: none; background: transparent;")
        header_row.addWidget(lbl_np_title)
        header_row.addStretch()
        left_np_layout.addLayout(header_row)

        # 1. Carátula Central con EKG
        self.artwork_ekg_widget = ArtworkEKGDisplayWidget(self.left_np_frame)
        left_np_layout.addWidget(self.artwork_ekg_widget, alignment=Qt.AlignmentFlag.AlignCenter, stretch=1)

        # 2. Información de la Canción (Título, Artista, Álbum)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.np_song_title = MarqueeLabel("Sin reproducción", font=QFont("Sans Serif", 15, QFont.Weight.Bold), color_str="#ffffff", parent=self.left_np_frame)
        self.np_song_title.setFixedHeight(30)
        info_layout.addWidget(self.np_song_title)

        self.np_song_artist = MarqueeLabel("Selecciona una canción", font=QFont("Sans Serif", 11), color_str="#cbd5e1", parent=self.left_np_frame)
        self.np_song_artist.setFixedHeight(22)
        info_layout.addWidget(self.np_song_artist)

        self.np_song_album = QLabel("", self.left_np_frame)
        self.np_song_album.setFont(QFont("Sans Serif", 9))
        self.np_song_album.setStyleSheet("color: #94a3b8; border: none; background: transparent;")
        self.np_song_album.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.np_song_album.setFixedHeight(18)
        info_layout.addWidget(self.np_song_album)

        left_np_layout.addLayout(info_layout)

        left_np_layout.addSpacing(6)

        # 3. Fila de Progreso y Tiempo
        time_row = QHBoxLayout()
        time_row.setSpacing(10)

        self.np_time_left = QLabel("0:00", self.left_np_frame)
        self.np_time_left.setFixedWidth(44)
        self.np_time_left.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        self.np_time_left.setStyleSheet("color: #f1f5f9; background: transparent; border: none;")
        self.np_time_left.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        time_row.addWidget(self.np_time_left)

        self.np_progress_bar = QSlider(Qt.Orientation.Horizontal, self.left_np_frame)
        self.np_progress_bar.setObjectName("ProgressBar")
        self.np_progress_bar.setRange(0, 1000)
        self.np_progress_bar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.np_progress_bar.sliderPressed.connect(self._on_np_slider_pressed)
        self.np_progress_bar.sliderReleased.connect(self._on_np_slider_released)
        time_row.addWidget(self.np_progress_bar, stretch=1)

        self.np_time_right = QLabel("-0:00", self.left_np_frame)
        self.np_time_right.setFixedWidth(44)
        self.np_time_right.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        self.np_time_right.setStyleSheet("color: #94a3b8; background: transparent; border: none;")
        self.np_time_right.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        time_row.addWidget(self.np_time_right)

        left_np_layout.addLayout(time_row)

        left_np_layout.addSpacing(4)

        # 4. Fila de Controles de Reproducción Simétricos y Armoniosos
        controls_row = QHBoxLayout()
        controls_row.setSpacing(14)
        controls_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.np_btn_fav = QPushButton("♡", self.left_np_frame)
        self.np_btn_fav.setFixedSize(40, 40)
        self.np_btn_fav.setCursor(Qt.CursorShape.PointingHandCursor)
        self.np_btn_fav.setToolTip("Marcar como Favorita (Ctrl+F)")
        self.np_btn_fav.setStyleSheet("QPushButton { background-color: rgba(255, 255, 255, 0.08); border: 1.5px solid rgba(255, 255, 255, 0.22); border-radius: 20px; color: #ffffff; font-size: 14px; font-weight: bold; } QPushButton:hover { background-color: rgba(255, 255, 255, 0.22); }")
        self.np_btn_fav.clicked.connect(self.toggle_fav_requested)
        controls_row.addWidget(self.np_btn_fav)

        self.np_btn_shuffle = QPushButton("🔀", self.left_np_frame)
        self.np_btn_shuffle.setFixedSize(40, 40)
        self.np_btn_shuffle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.np_btn_shuffle.setToolTip("Modo Aleatorio (Shuffle)")
        self.np_btn_shuffle.setStyleSheet("QPushButton { background-color: rgba(255, 255, 255, 0.08); border: 1.5px solid rgba(255, 255, 255, 0.22); border-radius: 20px; color: #ffffff; font-size: 14px; font-weight: bold; } QPushButton:hover { background-color: rgba(255, 255, 255, 0.22); }")
        self.np_btn_shuffle.clicked.connect(self.shuffle_requested)
        controls_row.addWidget(self.np_btn_shuffle)

        self.np_btn_prev = QPushButton("⏮", self.left_np_frame)
        self.np_btn_prev.setFixedSize(44, 44)
        self.np_btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self.np_btn_prev.setToolTip("Pista anterior")
        self.np_btn_prev.setStyleSheet("QPushButton { background-color: rgba(255, 255, 255, 0.08); border: 1.5px solid rgba(255, 255, 255, 0.22); border-radius: 22px; color: #ffffff; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: rgba(255, 255, 255, 0.22); }")
        self.np_btn_prev.clicked.connect(self.prev_requested)
        controls_row.addWidget(self.np_btn_prev)

        self.np_btn_play = QPushButton("▶", self.left_np_frame)
        self.np_btn_play.setObjectName("PlayButton")
        self.np_btn_play.setFixedSize(58, 58)
        self.np_btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
        self.np_btn_play.setToolTip("Reproducir / Pausar")
        self.np_btn_play.setStyleSheet(f"QPushButton {{ background-color: {self.accent_color}; border: none; border-radius: 29px; color: #ffffff; font-size: 22px; font-weight: bold; }}")
        self.np_btn_play.clicked.connect(self.play_pause_requested)
        controls_row.addWidget(self.np_btn_play)

        self.np_btn_next = QPushButton("⏭", self.left_np_frame)
        self.np_btn_next.setFixedSize(44, 44)
        self.np_btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.np_btn_next.setToolTip("Pista siguiente")
        self.np_btn_next.setStyleSheet("QPushButton { background-color: rgba(255, 255, 255, 0.08); border: 1.5px solid rgba(255, 255, 255, 0.22); border-radius: 22px; color: #ffffff; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: rgba(255, 255, 255, 0.22); }")
        self.np_btn_next.clicked.connect(self.next_requested)
        controls_row.addWidget(self.np_btn_next)

        self.np_btn_loop = QPushButton("↻", self.left_np_frame)
        self.np_btn_loop.setFixedSize(40, 40)
        self.np_btn_loop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.np_btn_loop.setToolTip("Modo Bucle (Loop)")
        self.np_btn_loop.setStyleSheet("QPushButton { background-color: rgba(255, 255, 255, 0.08); border: 1.5px solid rgba(255, 255, 255, 0.22); border-radius: 20px; color: #ffffff; font-size: 15px; font-weight: bold; } QPushButton:hover { background-color: rgba(255, 255, 255, 0.22); }")
        self.np_btn_loop.clicked.connect(self.loop_requested)
        controls_row.addWidget(self.np_btn_loop)

        left_np_layout.addLayout(controls_row)

        left_np_layout.addSpacing(4)

        # 5. Fila de Control de Volumen
        vol_row = QHBoxLayout()
        vol_row.setSpacing(10)
        vol_row.setContentsMargins(12, 0, 12, 0)

        self.np_btn_mute = QPushButton("🔊", self.left_np_frame)
        self.np_btn_mute.setFixedSize(30, 30)
        self.np_btn_mute.setCursor(Qt.CursorShape.PointingHandCursor)
        self.np_btn_mute.setToolTip("Silenciar / Desilenciar")
        self.np_btn_mute.setStyleSheet("QPushButton { background: transparent; border: none; font-size: 14px; color: #ffffff; } QPushButton:hover { color: #cbd5e1; }")
        self.np_btn_mute.clicked.connect(self._toggle_np_mute)
        vol_row.addWidget(self.np_btn_mute)

        self.np_slider_volume = Y2KVolumeSlider(self.left_np_frame)
        self.np_slider_volume.setObjectName("VolumeSlider")
        self.np_slider_volume.setRange(0, 100)
        self.np_slider_volume.setValue(100)
        self.np_slider_volume.set_accent_color(self.accent_color)
        self.np_slider_volume.valueChanged.connect(self._on_np_vol_changed)
        vol_row.addWidget(self.np_slider_volume, stretch=1)

        self.np_lbl_vol_val = QLabel("100%", self.left_np_frame)
        self.np_lbl_vol_val.setFixedWidth(38)
        self.np_lbl_vol_val.setFont(QFont("Sans Serif", 9))
        self.np_lbl_vol_val.setStyleSheet("color: #94a3b8; border: none; background: transparent;")
        self.np_lbl_vol_val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        vol_row.addWidget(self.np_lbl_vol_val)

        left_np_layout.addLayout(vol_row)

        page_np_layout.addWidget(self.left_np_frame, stretch=13)

        # Columna Derecha: Cola "Siguiente en reproducir"
        self.right_queue_frame = QFrame(self.page_now_playing)
        self.right_queue_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(8, 10, 20, 0.55);
                border-radius: 20px;
                border: 1.5px solid rgba(255, 255, 255, 0.12);
            }
        """)
        right_queue_layout = QVBoxLayout(self.right_queue_frame)
        right_queue_layout.setContentsMargins(18, 18, 18, 18)
        right_queue_layout.setSpacing(10)

        lbl_queue_header = QLabel("📋 Siguiente en reproducir", self.right_queue_frame)
        lbl_queue_header.setFont(QFont("Sans Serif", 11, QFont.Weight.Bold))
        lbl_queue_header.setStyleSheet("color: #ffffff; letter-spacing: 0.5px; border: none; background: transparent;")
        right_queue_layout.addWidget(lbl_queue_header)

        clean_accent = self.accent_color.split(';')[0].strip() if self.accent_color else "#ff1744"
        self.queue_list_widget = QListWidget(self.right_queue_frame)
        self.queue_list_widget.setStyleSheet(f"""
            QListWidget {{
                background: transparent;
                border: none;
                color: #ffffff;
            }}
            QListWidget::item {{
                padding: 10px 12px;
                border-radius: 10px;
                margin-bottom: 6px;
                color: #ffffff;
                background-color: rgba(255, 255, 255, 0.05);
            }}
            QListWidget::item:hover {{
                background-color: rgba(255, 255, 255, 0.15);
                color: #ffffff;
            }}
            QListWidget::item:selected {{
                background-color: rgba(255, 255, 255, 0.22);
                border: 1.5px solid {clean_accent};
                color: #ffffff;
            }}
        """)
        self.queue_list_widget.itemDoubleClicked.connect(self._on_queue_item_double_clicked)
        right_queue_layout.addWidget(self.queue_list_widget, stretch=1)

        page_np_layout.addWidget(self.right_queue_frame, stretch=10)
        self.center_stack.addWidget(self.page_now_playing)

        center_layout.addWidget(self.center_stack, stretch=1)
        main_layout.addWidget(self.center_area, stretch=1)

        # Conectar botones de navegación lateral
        self.btn_nav_music.clicked.connect(self._on_nav_music_clicked)
        self.btn_nav_playing.clicked.connect(self._on_nav_playing_clicked)
        self.btn_nav_favs.clicked.connect(self._on_nav_favs_clicked)
        self.btn_nav_albums.clicked.connect(self.choose_music_folder_requested)
        self.search_input.textChanged.connect(self._filter_songs)

    def _on_mode_button_clicked(self, mode: str) -> None:
        self.update_active_view_mode(mode)
        self.view_mode_requested.emit(mode)

    def update_active_view_mode(self, mode: str) -> None:
        self.current_view_mode = mode
        clean_hex = self.accent_color.split(';')[0].strip() if self.accent_color else "#ff1744"
        btn_grad = getattr(self, 'btn_gradient_effect', False)
        colors = getattr(self, 'gradient_colors', None)

        mode_buttons = [
            ("normal", getattr(self, 'btn_mode_normal', None)),
            ("compact", getattr(self, 'btn_mode_compact', None)),
            ("expanded", getattr(self, 'btn_mode_expanded', None)),
        ]
        for m_name, btn in mode_buttons:
            if btn:
                is_active = (mode == m_name)
                btn.setStyleSheet(build_mode_pill_style(
                    is_active=is_active,
                    accent_hex=clean_hex,
                    btn_gradient_effect=btn_grad,
                    gradient_colors=colors,
                    border_radius=17,
                    font_size=11,
                    padding="0 14px"
                ))

        if hasattr(self, 'btn_settings') and self.btn_settings:
            self.btn_settings.setStyleSheet(build_mode_pill_style(
                is_active=False,
                accent_hex=clean_hex,
                btn_gradient_effect=btn_grad,
                gradient_colors=colors,
                border_radius=17,
                font_size=11,
                padding="0 14px"
            ))

    def _on_nav_music_clicked(self) -> None:
        self.active_filter_mode = "all"
        self.active_nav_button = self.btn_nav_music
        self._highlight_nav_button(self.btn_nav_music)
        self.center_stack.setCurrentIndex(0)
        self.lbl_songs_title.setText(f"Todas tus canciones ({len(self.playlist)})")
        self.lbl_recents_title.setVisible(True)
        self.recents_scroll.setVisible(True)
        self.update_playlist_ui(self.playlist, self.current_index)

    def _on_nav_playing_clicked(self) -> None:
        self.active_nav_button = self.btn_nav_playing
        self._highlight_nav_button(self.btn_nav_playing)
        self.center_stack.setCurrentIndex(1)

    def _on_nav_favs_clicked(self) -> None:
        self.active_filter_mode = "favorites"
        self.active_nav_button = self.btn_nav_favs
        self._highlight_nav_button(self.btn_nav_favs)
        self.center_stack.setCurrentIndex(0)

        fav_tracks = [dict(t) for t in self.playlist if self._is_track_favorite(t)]
        
        parent_player = self.parentWidget()
        while parent_player and not hasattr(parent_player, "config"):
            parent_player = parent_player.parentWidget()
        
        if parent_player and hasattr(parent_player, "config"):
            saved_favs = parent_player.config.get("favorites", [])
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

        self.update_playlist_ui(fav_tracks, 0, is_filtered_view=True)

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
        glass_tint_sidebar = f"QFrame {{ background-color: rgba(12, 14, 26, 0.88); border-radius: 18px; border: 1.5px solid rgba({r}, {g}, {b}, 0.50); }}"
        glass_tint_center = f"QFrame {{ background-color: rgba(10, 12, 22, 0.82); border-radius: 18px; border: 1.5px solid rgba({r}, {g}, {b}, 0.40); }}"
        glass_tint_panels = f"QFrame {{ background-color: rgba(12, 14, 26, 0.85); border-radius: 18px; border: 1.5px solid rgba({r}, {g}, {b}, 0.45); }}"

        if hasattr(self, 'sidebar') and self.sidebar:
            self.sidebar.setStyleSheet(glass_tint_sidebar)
        if hasattr(self, 'center_area') and self.center_area:
            self.center_area.setStyleSheet(glass_tint_center)
        if hasattr(self, 'left_np_frame') and self.left_np_frame:
            self.left_np_frame.setStyleSheet(glass_tint_panels)
        if hasattr(self, 'right_queue_frame') and self.right_queue_frame:
            self.right_queue_frame.setStyleSheet(glass_tint_panels)

        # Relleno de degradado o color acento para los botones de la vista "En Reproducción"
        text_contrast = get_contrasting_text_color(clean_hex)
        grad_str = _build_qlineargradient(self.gradient_colors) if (btn_gradient_effect and self.gradient_colors and len(self.gradient_colors) >= 2) else ""
        if btn_gradient_effect and grad_str:
            c0 = self.gradient_colors[0]
            text_contrast = get_contrasting_text_color(c0)
            np_play_style = (
                f"QPushButton {{ background: {grad_str}; color: {text_contrast}; border-radius: 29px; border: none; font-size: 22px; font-weight: bold; }} "
                f"QPushButton:hover {{ background: {grad_str}; border: 1.5px solid #ffffff; color: #ffffff; }} "
                f"QPushButton:pressed {{ background: {grad_str}; border: 1.5px solid rgba(255, 255, 255, 0.70); color: #dddddd; }}"
            )
            np_ctrl_style = (
                f"QPushButton {{ background: {grad_str}; color: {text_contrast}; border-radius: 20px; border: 1.5px solid #ffffff; font-size: 14px; font-weight: bold; }} "
                f"QPushButton:hover {{ background: {grad_str}; border: 1.5px solid #ffffff; color: #ffffff; }} "
                f"QPushButton:pressed {{ background: {grad_str}; border: 1.5px solid rgba(255, 255, 255, 0.70); color: #dddddd; }}"
            )
        else:
            np_play_style = f"QPushButton {{ background-color: {clean_hex}; color: {text_contrast}; border-radius: 29px; border: none; font-size: 22px; font-weight: bold; }} QPushButton:hover {{ opacity: 0.88; }}"
            np_ctrl_style = f"QPushButton {{ background-color: rgba(255, 255, 255, 0.08); border: 1.5px solid {clean_hex}; border-radius: 20px; color: {clean_hex}; font-size: 14px; font-weight: bold; }} QPushButton:hover {{ background-color: {clean_hex}; color: #ffffff; }}"

        if hasattr(self, 'np_btn_play') and self.np_btn_play:
            self.np_btn_play.setStyleSheet(np_play_style)
        if hasattr(self, 'np_btn_prev') and self.np_btn_prev:
            self.np_btn_prev.setStyleSheet(np_ctrl_style)
        if hasattr(self, 'np_btn_next') and self.np_btn_next:
            self.np_btn_next.setStyleSheet(np_ctrl_style)
        if hasattr(self, 'np_btn_stop') and self.np_btn_stop:
            self.np_btn_stop.setStyleSheet(np_ctrl_style)
        if hasattr(self, 'np_btn_shuffle') and self.np_btn_shuffle:
            self.np_btn_shuffle.setStyleSheet(np_ctrl_style)
        if hasattr(self, 'np_btn_loop') and self.np_btn_loop:
            self.np_btn_loop.setStyleSheet(np_ctrl_style)
        if hasattr(self, 'np_btn_fav') and self.np_btn_fav:
            self.np_btn_fav.setStyleSheet(np_ctrl_style)

        if hasattr(self, 'sub_brand') and self.sub_brand:
            self.sub_brand.setStyleSheet(f"color: #ffffff; background-color: rgba(255, 255, 255, 0.08); padding: 3px 8px; border-radius: 8px; border: 1px solid {clean_hex};")

        # 1. Botón de Configuración
        if hasattr(self, 'btn_settings') and self.btn_settings:
            self.btn_settings.setStyleSheet(
                build_button_style(clean_hex, btn_gradient_effect=btn_gradient_effect, gradient_colors=self.gradient_colors, border_radius=17, font_size=11, padding="4px 14px")
            )

        # 2. Botón Cambiar Carpeta
        if hasattr(self, 'btn_choose_folder') and self.btn_choose_folder:
            self.btn_choose_folder.setStyleSheet(
                build_button_style(clean_hex, btn_gradient_effect=btn_gradient_effect, gradient_colors=self.gradient_colors, border_radius=14, font_size=11, padding="4px 12px")
            )

        # 3. Botón Nueva Lista
        if hasattr(self, 'btn_add_list') and self.btn_add_list:
            self.btn_add_list.setStyleSheet(
                f"QPushButton {{ color: {clean_hex}; background: transparent; border: none; font-weight: bold; font-size: 16px; text-align: center; }} "
                f"QPushButton:hover {{ color: #ffffff; }}"
            )

        # 4. Botones de Selección de Modo (Navegación Principal)
        self.update_active_view_mode(getattr(self, 'current_view_mode', 'expanded'))

        # 5. Artwork EKG & Artista Marquesina
        if hasattr(self, 'artwork_ekg_widget') and self.artwork_ekg_widget:
            self.artwork_ekg_widget.set_accent_color(clean_hex)

        if hasattr(self, 'np_slider_volume') and self.np_slider_volume:
            self.np_slider_volume.set_accent_color(clean_hex, self.gradient_colors if btn_gradient_effect else [clean_hex, clean_hex])

        if hasattr(self, 'np_song_artist') and self.np_song_artist:
            self.np_song_artist.set_color("#d0d4eb")

        # 6. Campo de Búsqueda
        if hasattr(self, 'search_input') and self.search_input:
            self.search_input.setStyleSheet(f"""
                QLineEdit {{
                    background-color: rgba(14, 16, 26, 0.7);
                    color: #ffffff;
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 17px;
                    padding-left: 16px;
                    padding-right: 16px;
                    font-size: 11px;
                }}
                QLineEdit:focus {{
                    border: 1.5px solid {clean_hex};
                }}
            """)

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
        if hasattr(self, 'playlist') and self.playlist:
            self.update_playlist_ui(self.playlist, getattr(self, 'current_index', 0), is_filtered_view=(getattr(self, 'active_filter_mode', 'all') != 'all'))

    def _highlight_nav_button(self, active_btn: QPushButton) -> None:
        clean_accent = self.accent_color.split(';')[0].strip() if self.accent_color else "#ff1744"
        btn_grad_on = getattr(self, 'btn_gradient_effect', False)
        colors = getattr(self, 'gradient_colors', None)
        grad_str = _build_qlineargradient(colors) if (btn_grad_on and colors and len(colors) >= 2) else ""

        for btn in self.nav_buttons:
            if btn == active_btn:
                bg_rule = f"background: {grad_str};" if (btn_grad_on and grad_str) else f"background-color: {clean_accent};"
                btn.setStyleSheet(f"""
                    QPushButton {{
                        text-align: left;
                        padding-left: 14px;
                        font-size: 12px;
                        font-weight: bold;
                        color: #ffffff;
                        {bg_rule}
                        border-radius: 12px;
                        border: 1.5px solid #ffffff;
                    }}
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding-left: 14px;
                        font-size: 12px;
                        font-weight: bold;
                        color: #e2e8f0;
                        background-color: rgba(255, 255, 255, 0.07);
                        border-radius: 12px;
                        border: 1px solid rgba(255, 255, 255, 0.12);
                    }
                    QPushButton:hover {
                        background-color: rgba(255, 255, 255, 0.18);
                        color: #ffffff;
                        border: 1px solid rgba(255, 255, 255, 0.30);
                    }
                """)

    def _on_nav_music_clicked(self) -> None:
        self.active_filter_mode = "all"
        self.active_nav_button = self.btn_nav_music
        self._highlight_nav_button(self.btn_nav_music)
        self.center_stack.setCurrentIndex(0)
        self.lbl_recents_title.setText("Escuchados recientemente")
        self.lbl_songs_title.setText("Todas tus canciones")
        self.recents_scroll.setVisible(True)
        self.lbl_recents_title.setVisible(True)
        self.update_playlist_ui(self.playlist, self.current_index)

    def _on_nav_playing_clicked(self) -> None:
        self.active_nav_button = self.btn_nav_playing
        self._highlight_nav_button(self.btn_nav_playing)
        self.center_stack.setCurrentIndex(1)

    def _on_nav_favs_clicked(self) -> None:
        self.active_filter_mode = "favorites"
        self.active_nav_button = self.btn_nav_favs
        self._highlight_nav_button(self.btn_nav_favs)
        self.center_stack.setCurrentIndex(0)

        fav_tracks = [dict(t) for t in self.playlist if self._is_track_favorite(t)]
        
        parent_player = self.parentWidget()
        while parent_player and not hasattr(parent_player, "config"):
            parent_player = parent_player.parentWidget()
        
        if parent_player and hasattr(parent_player, "config"):
            saved_favs = parent_player.config.get("favorites", [])
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

        self.update_playlist_ui(fav_tracks, 0, is_filtered_view=True)

    def _is_track_favorite(self, track: dict) -> bool:
        title = track.get("title", "")
        artist = track.get("artist", "")
        parent_player = self.parentWidget()
        while parent_player and not hasattr(parent_player, "config"):
            parent_player = parent_player.parentWidget()
        if parent_player and hasattr(parent_player, "config"):
            return parent_player.config.is_favorite(title, artist)
        return False

    def _create_new_playlist(self) -> None:
        name, ok = QInputDialog.getText(self, "Nueva Lista", "Nombre de la lista de reproducción:")
        if ok and name.strip():
            list_name = name.strip()
            if list_name not in self.user_playlists:
                self.user_playlists[list_name] = []
                self._refresh_playlists_sidebar_ui()
                self._on_playlist_clicked(list_name)

    def _refresh_playlists_sidebar_ui(self) -> None:
        while self.playlists_layout.count():
            item = self.playlists_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for name in self.user_playlists.keys():
            p_btn = QPushButton(f"▶  {name}", self.playlists_container)
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
            p_btn.clicked.connect(lambda checked, n=name: self._on_playlist_clicked(n))
            self.playlists_layout.addWidget(p_btn)

        self.playlists_layout.addStretch()

    def _on_playlist_clicked(self, playlist_name: str) -> None:
        self.active_filter_mode = "playlist"
        self.selected_playlist_name = playlist_name
        self.center_stack.setCurrentIndex(0)

        self.lbl_recents_title.setVisible(False)
        self.recents_scroll.setVisible(False)
        self.lbl_songs_title.setText(f"📋 Lista: {playlist_name}")

        track_indices = self.user_playlists.get(playlist_name, [])
        playlist_tracks = [self.playlist[i] for i in track_indices if 0 <= i < len(self.playlist)] if track_indices else self.playlist
        self.update_playlist_ui(playlist_tracks, 0, is_filtered_view=True)

    def _on_scroll_grid_value_changed(self, value: int) -> None:
        if hasattr(self, 'scroll_lib') and self.scroll_lib:
            vbar = self.scroll_lib.verticalScrollBar()
            if vbar.maximum() > 0 and value >= vbar.maximum() - 250:
                self._load_more_grid_cards()

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
        cols = 4

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
        if parent_player and hasattr(parent_player, "config"):
            return parent_player.config.get("recent_tracks", [])
        return []

    def _find_track_index(self, track: dict) -> int:
        t_clean = (track.get("title") or "").strip().lower()
        a_clean = (track.get("artist") or "").strip().lower()
        p_clean = (track.get("path") or "").strip()
        for idx, item in enumerate(self.playlist):
            if p_clean and item.get("path") == p_clean:
                return idx
            if (item.get("title") or "").strip().lower() == t_clean and (item.get("artist") or "").strip().lower() == a_clean:
                return idx
        return -1

    def update_playlist_ui(self, playlist: List[Dict[str, Any]], current_index: int = 0, is_filtered_view: bool = False) -> None:
        if not is_filtered_view:
            self.playlist = playlist
        self.current_index = current_index
        self._display_tracks = playlist
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
            return

        if not is_filtered_view:
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

        # Cargar los primeros 60 de forma súper rápida (0ms)
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

    def update_config_settings(self, config_dict: dict) -> None:
        self.inner_art_mode = config_dict.get("inner_art_mode", "auto")
        self.custom_inner_image = config_dict.get("custom_inner_image", "")
        if "brand_name" in config_dict:
            self.set_brand_name(config_dict["brand_name"])
        if hasattr(self, 'current_metadata'):
            self.update_metadata(self.current_metadata, self.current_index)
        if hasattr(self, 'playlist') and self.playlist:
            self.update_playlist_ui(self.playlist, self.current_index, is_filtered_view=(self.active_filter_mode != 'all'))

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

    def set_playing_status(self, is_playing: bool) -> None:
        self.artwork_ekg_widget.set_playing(is_playing)
        icon = "⏸" if is_playing else "▶"
        self.np_btn_play.setText(icon)

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
        if is_fav:
            self.np_btn_fav.setText("♥")
            grad_str = _build_qlineargradient(self.gradient_colors) if (getattr(self, 'btn_gradient_effect', False) and getattr(self, 'gradient_colors', None) and len(self.gradient_colors) >= 2) else ""
            if grad_str:
                self.np_btn_fav.setStyleSheet(
                    f"QPushButton {{ background: {grad_str}; border: 1.5px solid #ffffff; border-radius: 18px; color: #ffffff; font-size: 13px; font-weight: bold; }} "
                    f"QPushButton:hover {{ background: {grad_str}; border: 1.5px solid #ffffff; color: #ffffff; }} "
                    f"QPushButton:pressed {{ background: {grad_str}; border: 1.5px solid rgba(255, 255, 255, 0.70); color: #dddddd; }}"
                )
            else:
                self.np_btn_fav.setStyleSheet(f"QPushButton {{ background-color: {self.accent_color}; border: 1.5px solid {self.accent_color}; border-radius: 18px; color: #ffffff; font-size: 13px; font-weight: bold; }}")
        else:
            self.np_btn_fav.setText("♡")
            self.np_btn_fav.setStyleSheet("QPushButton { background-color: rgba(255, 255, 255, 0.06); border: 1.5px solid rgba(255, 255, 255, 0.25); border-radius: 18px; color: #ffffff; font-size: 13px; font-weight: bold; }")

    def update_loop_status(self, status: str) -> None:
        if status in ("Track", "Playlist"):
            grad_str = _build_qlineargradient(self.gradient_colors) if (getattr(self, 'btn_gradient_effect', False) and getattr(self, 'gradient_colors', None) and len(self.gradient_colors) >= 2) else ""
            if grad_str:
                self.np_btn_loop.setStyleSheet(
                    f"QPushButton {{ background: {grad_str}; border: 1.5px solid #ffffff; border-radius: 18px; color: #ffffff; font-size: 13px; font-weight: bold; }} "
                    f"QPushButton:hover {{ background: {grad_str}; border: 1.5px solid #ffffff; color: #ffffff; }} "
                    f"QPushButton:pressed {{ background: {grad_str}; border: 1.5px solid rgba(255, 255, 255, 0.70); color: #dddddd; }}"
                )
            else:
                self.np_btn_loop.setStyleSheet(f"QPushButton {{ background-color: {self.accent_color}; border: 1.5px solid {self.accent_color}; border-radius: 18px; color: #ffffff; font-size: 13px; font-weight: bold; }}")
        else:
            self.np_btn_loop.setStyleSheet("QPushButton { background-color: rgba(255, 255, 255, 0.06); border: 1.5px solid rgba(255, 255, 255, 0.25); border-radius: 18px; color: #ffffff; font-size: 13px; font-weight: bold; }")

    def update_shuffle_status(self, enabled: bool) -> None:
        if enabled:
            grad_str = _build_qlineargradient(self.gradient_colors) if (getattr(self, 'btn_gradient_effect', False) and getattr(self, 'gradient_colors', None) and len(self.gradient_colors) >= 2) else ""
            if grad_str:
                self.np_btn_shuffle.setStyleSheet(
                    f"QPushButton {{ background: {grad_str}; border: 1.5px solid #ffffff; border-radius: 18px; color: #ffffff; font-size: 13px; font-weight: bold; }} "
                    f"QPushButton:hover {{ background: {grad_str}; border: 1.5px solid #ffffff; color: #ffffff; }} "
                    f"QPushButton:pressed {{ background: {grad_str}; border: 1.5px solid rgba(255, 255, 255, 0.70); color: #dddddd; }}"
                )
            else:
                self.np_btn_shuffle.setStyleSheet(f"QPushButton {{ background-color: {self.accent_color}; border: 1.5px solid {self.accent_color}; border-radius: 18px; color: #ffffff; font-size: 13px; font-weight: bold; }}")
        else:
            self.np_btn_shuffle.setStyleSheet("QPushButton { background-color: rgba(255, 255, 255, 0.06); border: 1.5px solid rgba(255, 255, 255, 0.25); border-radius: 18px; color: #ffffff; font-size: 13px; font-weight: bold; }")

    def _filter_songs(self, text: str) -> None:
        query = text.strip().lower()
        
        while self.songs_grid_layout.count():
            item = self.songs_grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not query:
            filtered = self.playlist
        else:
            filtered = [
                (idx, t) for idx, t in enumerate(self.playlist)
                if query in t.get("title", "").lower() or query in t.get("artist", "").lower() or query in t.get("album", "").lower()
            ]

        cols = 4
        for cell_idx, item in enumerate(filtered):
            if isinstance(item, tuple):
                real_idx, track = item
            else:
                real_idx, track = cell_idx, item

            row = cell_idx // cols
            col = cell_idx % cols
            card = SongCardWidget(
                track_index=real_idx,
                title=track.get("title", "Sin título"),
                artist=track.get("artist", "Artista desconocido"),
                art_url=track.get("art_url", ""),
                accent_color=self.accent_color,
                parent=self.songs_grid_widget
            )
            card.card_clicked.connect(self.play_track_requested)
            self.songs_grid_layout.addWidget(card, row, col)

    def _on_queue_item_double_clicked(self, item: QListWidgetItem) -> None:
        idx = item.data(Qt.ItemDataRole.UserRole)
        if idx is not None:
            self.play_track_requested.emit(idx)
