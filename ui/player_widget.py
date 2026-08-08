import os
import random
import urllib.parse
from typing import Optional, Dict, Any, List
from PyQt6.QtCore import Qt, QSize, QPoint, pyqtSlot, QUrl, QTimer, QRectF, QFileSystemWatcher, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QAction, QShortcut, QKeySequence, QIcon, QPainter, QColor, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QMenu, QApplication, QLayout, QSlider, QStackedWidget,
    QSystemTrayIcon, QFileDialog, QColorDialog
)
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from ui.styles import MAIN_STYLE, get_main_style
from ui.marquee_label import MarqueeLabel
from ui.equalizer_widget import EqualizerWidget
from ui.color_extractor import extract_pastel_colors, extract_vibrant_accent_color
from mpris_client import MPRISClient
from config_manager import ConfigManager

class HeadphoneEKGWidget(QWidget):
    """Widget de fondo animado con carátula de canción / fondo semi-transparente y barras de ecualizador superpuestas."""
    def __init__(self, parent: Optional[QWidget] = None, accent_color: str = "#ff1744", custom_bg_path: Optional[str] = None, art_mode: str = "auto") -> None:
        super().__init__(parent)
        self.is_playing: bool = False
        self.bar_count = 18
        self.bar_heights: List[float] = [6.0] * self.bar_count
        self.headphone_pixmap: Optional[QPixmap] = None
        self.album_art_pixmap: Optional[QPixmap] = None
        self.accent_color: str = accent_color
        self.art_mode: str = art_mode  # 'auto' o 'custom_always'

        self.custom_bg_path = custom_bg_path or "/home/phame/Imágenes/imagen para perzonalizar/839921399301379570.jpeg"
        self._load_headphone_pixmap(self.custom_bg_path)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate_bars)
        self.timer.setInterval(60)

    def _load_headphone_pixmap(self, image_path: str) -> None:
        if image_path and os.path.exists(image_path):
            self.headphone_pixmap = QPixmap(image_path)
        else:
            default_folder = "/home/phame/Imágenes/fondo para mi reproducctor"
            if os.path.exists(default_folder) and os.path.isdir(default_folder):
                imgs = [os.path.join(default_folder, f) for f in sorted(os.listdir(default_folder)) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
                if imgs:
                    self.headphone_pixmap = QPixmap(imgs[0])

    def set_custom_bg_image(self, image_path: str) -> bool:
        if not image_path or not os.path.exists(image_path):
            return False
        pix = QPixmap(image_path)
        if pix.isNull():
            return False
        self.custom_bg_path = image_path
        self.headphone_pixmap = pix
        self.update()
        return True

    def set_art_mode(self, mode: str) -> None:
        self.art_mode = mode
        self.update()

    def set_album_art(self, pixmap: Optional[QPixmap]) -> None:
        self.album_art_pixmap = pixmap if (pixmap and not pixmap.isNull()) else None
        self.update()

    def set_playing(self, playing: bool) -> None:
        self.is_playing = playing
        if playing:
            if not self.timer.isActive():
                self.timer.start()
        else:
            self.timer.stop()
            self.bar_heights = [6.0] * self.bar_count
            self.update()

    def _animate_bars(self) -> None:
        if not self.is_playing:
            return
        self.bar_heights = [random.uniform(6.0, 48.0) for _ in range(self.bar_count)]
        self.update()

    def paintEvent(self, event: Any) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = float(self.width()), float(self.height())
        p.fillRect(self.rect(), QColor("#050508"))

        show_song_art = (self.art_mode == "auto") and (self.album_art_pixmap and not self.album_art_pixmap.isNull())

        # 1. Si el modo es 'auto' y hay carátula de canción activa, mostrar la foto de la canción a 100% opacidad
        if show_song_art:
            p.setOpacity(1.0)
            scaled_art = self.album_art_pixmap.scaled(
                int(w), int(h),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            x_art = (w - scaled_art.width()) / 2.0
            y_art = (h - scaled_art.height()) / 2.0
            p.drawPixmap(int(x_art), int(y_art), scaled_art)
        # 2. Si no hay carátula o se eligió modo 'custom_always', mostrar la imagen personalizada fija (opacidad 45%)
        elif self.headphone_pixmap and not self.headphone_pixmap.isNull():
            opacity = 0.85 if self.art_mode == "custom_always" else 0.45
            p.setOpacity(opacity)
            scaled_bg = self.headphone_pixmap.scaled(
                int(w), int(h),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            x_bg = (w - scaled_bg.width()) / 2.0
            y_bg = (h - scaled_bg.height()) / 2.0
            p.drawPixmap(int(x_bg), int(y_bg), scaled_bg)

        # Restablecer opacidad al 100% para las barras de ecualizador animadas
        p.setOpacity(1.0)

        # 3. Dibujar las barras de ecualizador animadas superpuestas por ENCIMA
        bar_w = max(3.0, (w - 12) / (self.bar_count * 1.6))
        spacing = bar_w * 0.6
        total_w = self.bar_count * (bar_w + spacing) - spacing
        start_x = (w - total_w) / 2.0
        base_y = h - 6.0
        max_h = max(8.0, h * 0.65)

        p.setPen(Qt.PenStyle.NoPen)

        for i in range(self.bar_count):
            raw_h = self.bar_heights[i] if self.is_playing else 4.0
            bar_h = min(raw_h, max_h)
            x_pos = start_x + i * (bar_w + spacing)
            y_pos = base_y - bar_h
            
            bar_color = QColor(self.accent_color) if i % 2 == 0 else QColor("#ffffff")
            p.setBrush(bar_color)
            p.drawRoundedRect(int(x_pos), int(y_pos), int(bar_w), int(bar_h), 2, 2)

        p.end()

class BackgroundContainer(QWidget):
    """Widget contenedor principal con bordes redondeados, galería de fondos e intercala imágenes con transición suave (cross-fade)."""
    image_changed = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None, bg_path: Optional[str] = None, interval_sec: int = 15, folder_path: Optional[str] = None, enabled: bool = True, aspect_mode: str = "fit", accent_color: str = "#ff1744") -> None:
        super().__init__(parent)
        self.current_pixmap: Optional[QPixmap] = None
        self.next_pixmap: Optional[QPixmap] = None
        self.is_transitioning: bool = False
        self.fade_progress: float = 0.0
        
        self.images_list: List[str] = []
        self.current_img_index: int = 0
        self.interval_sec: int = max(3, interval_sec)
        self.slideshow_enabled: bool = enabled
        self.aspect_mode: str = aspect_mode
        self.accent_color: str = accent_color

        self.folder_path = folder_path if (folder_path and os.path.exists(folder_path)) else "/home/phame/Imágenes/fondo para mi reproducctor"
        self.bg_path = bg_path
        self._scan_images(self.folder_path, fallback_path=self.bg_path)

        if self.bg_path and os.path.exists(self.bg_path):
            pix = QPixmap(self.bg_path)
            if not pix.isNull():
                self.current_pixmap = pix
                if self.bg_path in self.images_list:
                    self.current_img_index = self.images_list.index(self.bg_path)
        elif self.images_list:
            first_path = self.images_list[0]
            pix = QPixmap(first_path)
            if not pix.isNull():
                self.current_pixmap = pix
                self.current_img_index = 0

        # Monitor dinámico de sistema de archivos en tiempo real (FileSystemWatcher)
        self.fs_watcher = QFileSystemWatcher(self)
        if os.path.exists(self.folder_path):
            self.fs_watcher.addPath(self.folder_path)
            self.fs_watcher.directoryChanged.connect(self._on_directory_changed)

        # Timer para animación de transición (Cross-fade)
        self.fade_timer = QTimer(self)
        self.fade_timer.setInterval(20)  # ~50 FPS
        self.fade_timer.timeout.connect(self._update_transition)

        # Timer para el carrusel automático de fondos
        self.slideshow_timer = QTimer(self)
        self.slideshow_timer.timeout.connect(self.next_background)
        if self.slideshow_enabled and len(self.images_list) > 1:
            self.slideshow_timer.start(self.interval_sec * 1000)

    def _on_directory_changed(self, path: str) -> None:
        """Se ejecuta automáticamente cuando se añade, elimina o renombra una imagen en la carpeta."""
        self._scan_images(self.folder_path, fallback_path=self.bg_path)
        if self.slideshow_enabled and len(self.images_list) > 1 and not self.slideshow_timer.isActive():
            self.slideshow_timer.start(self.interval_sec * 1000)

    def _scan_images(self, folder_path: str, fallback_path: Optional[str] = None) -> None:
        valid_exts = (".jpeg", ".jpg", ".png", ".webp")
        found = []
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            for filename in sorted(os.listdir(folder_path)):
                if filename.lower().endswith(valid_exts):
                    found.append(os.path.join(folder_path, filename))
        
        if fallback_path and os.path.exists(fallback_path) and fallback_path not in found:
            found.insert(0, fallback_path)

        self.images_list = found

    def next_background(self) -> None:
        if self.is_transitioning:
            return
        
        # Re-escaneo en vivo por si se añadieron o borraron archivos
        self._scan_images(self.folder_path, fallback_path=self.bg_path)

        if len(self.images_list) <= 1:
            return
        
        self.current_img_index = (self.current_img_index + 1) % len(self.images_list)
        next_path = self.images_list[self.current_img_index]
        pix = QPixmap(next_path)
        if pix.isNull():
            return
        
        self.bg_path = next_path
        self.next_pixmap = pix
        self.fade_progress = 0.0
        self.is_transitioning = True
        self.fade_timer.start()
        self.image_changed.emit(next_path)

    def set_aspect_mode(self, mode: str) -> None:
        self.aspect_mode = mode
        self.update()

    def set_custom_image(self, image_path: str) -> bool:
        if not os.path.exists(image_path):
            return False
        pix = QPixmap(image_path)
        if pix.isNull():
            return False
        self.bg_path = image_path
        if image_path not in self.images_list:
            self.images_list.insert(0, image_path)
            self.current_img_index = 0
        else:
            self.current_img_index = self.images_list.index(image_path)
        self.current_pixmap = pix
        self.update()
        self.image_changed.emit(image_path)
        return True

    def set_folder_path(self, folder_path: str) -> bool:
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            return False
        if hasattr(self, 'fs_watcher') and self.fs_watcher.directories():
            self.fs_watcher.removePaths(self.fs_watcher.directories())
        self.folder_path = folder_path
        self.fs_watcher.addPath(self.folder_path)
        self._scan_images(self.folder_path)
        if self.images_list:
            self.current_img_index = 0
            pix = QPixmap(self.images_list[0])
            if not pix.isNull():
                self.current_pixmap = pix
        self.update()
        return True

    def toggle_slideshow(self, enable: Optional[bool] = None) -> bool:
        if enable is None:
            self.slideshow_enabled = not self.slideshow_enabled
        else:
            self.slideshow_enabled = enable

        if self.slideshow_enabled and len(self.images_list) > 1:
            self.slideshow_timer.start(self.interval_sec * 1000)
        else:
            self.slideshow_timer.stop()

        return self.slideshow_enabled

    def _update_transition(self) -> None:
        self.fade_progress += 0.04  # Transición en ~500ms
        if self.fade_progress >= 1.0:
            self.fade_progress = 1.0
            self.current_pixmap = self.next_pixmap
            self.next_pixmap = None
            self.is_transitioning = False
            self.fade_timer.stop()
        self.update()

    def paintEvent(self, event: Any) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        w, h = float(rect.width()), float(rect.height())

        # Clip al área del contenedor redondeado (radius=22px)
        path = QPainterPath()
        path.addRoundedRect(QRectF(0.5, 0.5, w - 1.0, h - 1.0), 22.0, 22.0)

        p.save()
        p.setClipPath(path)

        # 1. Relleno oscuro de fondo base (#0c0c10)
        p.fillRect(rect, QColor("#0c0c10"))

        base_opacity = 0.45

        if self.aspect_mode == "fill":
            qt_aspect_mode = Qt.AspectRatioMode.KeepAspectRatioByExpanding
        elif self.aspect_mode == "stretch":
            qt_aspect_mode = Qt.AspectRatioMode.IgnoreAspectRatio
        else:
            qt_aspect_mode = Qt.AspectRatioMode.KeepAspectRatio

        # 2. Renderizado de la imagen actual
        if self.current_pixmap and not self.current_pixmap.isNull():
            opacity = base_opacity * (1.0 - self.fade_progress) if self.is_transitioning else base_opacity
            p.setOpacity(opacity)
            scaled = self.current_pixmap.scaled(
                int(w), int(h),
                qt_aspect_mode,
                Qt.TransformationMode.SmoothTransformation
            )
            x = (w - scaled.width()) / 2.0
            y = (h - scaled.height()) / 2.0
            p.drawPixmap(int(x), int(y), scaled)

        # 3. Renderizado de la siguiente imagen durante la transición (Cross-fade)
        if self.is_transitioning and self.next_pixmap and not self.next_pixmap.isNull():
            p.setOpacity(base_opacity * self.fade_progress)
            scaled_next = self.next_pixmap.scaled(
                int(w), int(h),
                qt_aspect_mode,
                Qt.TransformationMode.SmoothTransformation
            )
            x_next = (w - scaled_next.width()) / 2.0
            y_next = (h - scaled_next.height()) / 2.0
            p.drawPixmap(int(x_next), int(y_next), scaled_next)

        p.restore()

        # 4. Borde de acento alrededor del contenedor principal
        p.setPen(QPen(QColor(self.accent_color), 2.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(1.0, 1.0, w - 2.0, h - 2.0), 21.0, 21.0)
        p.end()

class FloatingMusicPlayer(QWidget):
    RESIZE_MARGIN = 8

    def __init__(self, mpris_client: MPRISClient, config: ConfigManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.mpris = mpris_client
        self.config = config

        self.current_art_url: Optional[str] = None
        self.current_pixmap: Optional[QPixmap] = None
        self.drag_position: QPoint = QPoint()
        self.is_user_seeking: bool = False
        self.duration_sec: int = 0
        self.tray_icon: Optional[QSystemTrayIcon] = None

        self.stays_on_top: bool = self.config.get("stays_on_top", True)
        self.is_compact: bool = self.config.get("compact_mode", False)
        self.accent_color: str = self.config.get("accent_color", "#ff1744")

        self.net_manager = QNetworkAccessManager(self)
        self.net_manager.finished.connect(self._on_art_download_finished)

        self.init_ui()
        self.connect_signals()
        self.setup_shortcuts()
        self.setup_tray_icon()
        self.apply_mode()
        self._set_theme_color(self.accent_color)

        # Sincronización inicial del estado MPRIS con la UI tras conectar las señales
        self.mpris.refresh()

    def init_ui(self):
        self.set_window_flags()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        bg_img_path = self.config.get("background_image")
        interval_sec = self.config.get("bg_slideshow_interval_sec", 15)
        folder_path = self.config.get("bg_folder")
        enabled = self.config.get("bg_slideshow_enabled", True)
        aspect_mode = self.config.get("bg_aspect_mode", "fit")

        self.container = BackgroundContainer(
            self,
            bg_path=bg_img_path,
            interval_sec=interval_sec,
            folder_path=folder_path,
            enabled=enabled,
            aspect_mode=aspect_mode,
            accent_color=self.accent_color
        )
        self.container.setObjectName("CentralContainer")
        self.container.setStyleSheet(get_main_style(self.accent_color))
        self.container.setMouseTracking(True)

        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(14, 12, 14, 10)
        self.container_layout.setSpacing(8)

        # ----------------------------------------------------
        # 1. BARRA SUPERIOR
        # ----------------------------------------------------
        top_bar_layout = QHBoxLayout()
        top_bar_layout.setContentsMargins(4, 0, 4, 0)
        top_bar_layout.setSpacing(6)

        self.badge_label = QLabel("🎧 RED WORLD", self.container)
        self.badge_label.setObjectName("BadgeLabel")
        self.badge_label.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        self.badge_label.setStyleSheet("color: #ff1744;")
        top_bar_layout.addWidget(self.badge_label)

        self.equalizer = EqualizerWidget(self.container)
        top_bar_layout.addWidget(self.equalizer)

        top_bar_layout.addStretch()

        self.btn_compact_toggle = QPushButton("⤢", self.container)
        self.btn_compact_toggle.setFixedSize(20, 20)
        self.btn_compact_toggle.setToolTip("Alternar modo compacto/normal")
        self.btn_compact_toggle.setStyleSheet("QPushButton { font-size: 11px; font-weight: bold; border-radius: 10px; border: none; background: transparent; color: #ff1744; } QPushButton:hover { color: #ffffff; }")
        self.btn_compact_toggle.clicked.connect(self.toggle_compact_mode)
        top_bar_layout.addWidget(self.btn_compact_toggle)

        self.btn_close = QPushButton("×", self.container)
        self.btn_close.setFixedSize(20, 20)
        self.btn_close.setToolTip("Cerrar")
        self.btn_close.setStyleSheet(
            "QPushButton { font-size: 14px; font-weight: bold; border-radius: 10px; padding: 0px; border: none; background: transparent; color: #ff1744; } "
            "QPushButton:hover { color: #ffffff; background-color: #ff1744; }"
        )
        self.btn_close.clicked.connect(QApplication.instance().quit)
        top_bar_layout.addWidget(self.btn_close)

        self.container_layout.addLayout(top_bar_layout)

        # ----------------------------------------------------
        # 2. VISTA STACKED (Normal vs Compacto)
        # ----------------------------------------------------
        self.stacked = QStackedWidget(self.container)

        # --- VISTA NORMAL ---
        self.normal_page = QWidget()
        normal_layout = QVBoxLayout(self.normal_page)
        normal_layout.setContentsMargins(0, 0, 0, 0)
        normal_layout.setSpacing(8)

        # Pantalla de Arte / Fondo con Audífonos y EKG de シ︎🎧.jpeg
        self.art_screen = QLabel(self.normal_page)
        self.art_screen.setObjectName("ArtScreen")
        self.art_screen.setMinimumHeight(130)
        self.art_screen.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.art_screen.setScaledContents(True)

        art_screen_layout = QVBoxLayout(self.art_screen)
        art_screen_layout.setContentsMargins(0, 0, 0, 0)

        custom_inner_img = self.config.get("custom_inner_image", "/home/phame/Imágenes/imagen para perzonalizar/839921399301379570.jpeg")
        inner_mode = self.config.get("inner_art_mode", "auto")
        self.ekg_bg = HeadphoneEKGWidget(self.art_screen, accent_color=self.accent_color, custom_bg_path=custom_inner_img, art_mode=inner_mode)
        art_screen_layout.addWidget(self.ekg_bg)

        normal_layout.addWidget(self.art_screen, stretch=1)

        # Título y Artista al estilo mundo rosa.jpeg (Alineados a la izquierda + Corazón Favorito)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(1)

        self.title_label = MarqueeLabel("Sin título", font=QFont("Sans Serif", 11, QFont.Weight.Bold), color_str="#ffffff", parent=self.normal_page)
        self.title_label.setFixedHeight(22)
        info_layout.addWidget(self.title_label)

        self.artist_label = MarqueeLabel("Artista", font=QFont("Sans Serif", 9), color_str="#ff4d6d", parent=self.normal_page)
        self.artist_label.setFixedHeight(18)
        info_layout.addWidget(self.artist_label)

        normal_layout.addLayout(info_layout)

        # Seekbar & Tiempo Dual
        progress_layout = QVBoxLayout()
        progress_layout.setSpacing(2)

        self.progress_bar = QSlider(Qt.Orientation.Horizontal, self.normal_page)
        self.progress_bar.setObjectName("ProgressBar")
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.sliderPressed.connect(self._on_slider_pressed)
        self.progress_bar.sliderReleased.connect(self._on_slider_released)
        progress_layout.addWidget(self.progress_bar)

        time_box_layout = QHBoxLayout()
        time_box_layout.setContentsMargins(2, 0, 2, 0)

        self.time_left_label = QLabel("0:00", self.normal_page)
        self.time_left_label.setFont(QFont("Sans Serif", 8, QFont.Weight.Bold))
        self.time_left_label.setStyleSheet("color: #ffffff;")

        self.time_right_label = QLabel("-0:00", self.normal_page)
        self.time_right_label.setFont(QFont("Sans Serif", 8, QFont.Weight.Bold))
        self.time_right_label.setStyleSheet("color: #ff4d6d;")

        time_box_layout.addWidget(self.time_left_label)
        time_box_layout.addStretch()
        time_box_layout.addWidget(self.time_right_label)
        progress_layout.addLayout(time_box_layout)

        normal_layout.addLayout(progress_layout)

        # Fila de 5 Controles Perfectamente Simétricos ( ♥   ⏮   [▶/⏸]   ⏭   ↻ )
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(4, 2, 4, 2)
        controls_layout.setSpacing(12)

        controls_layout.addStretch()

        # 1. Extremo Izquierdo: Favoritos (♥)
        self.btn_like = QPushButton("♥", self.normal_page)
        self.btn_like.setFixedSize(32, 32)
        self.btn_like.setToolTip("Marcar / Desmarcar Favorito (Ctrl+F)")
        self.btn_like.setStyleSheet("QPushButton { font-size: 15px; border: none; background: transparent; color: #ff1744; } QPushButton:hover { color: #ffffff; }")
        self.btn_like.clicked.connect(self.toggle_favorite)
        controls_layout.addWidget(self.btn_like)

        # 2. Izquierda: Pista Anterior (⏮)
        self.btn_prev = QPushButton("⏮", self.normal_page)
        self.btn_prev.setFixedSize(34, 34)
        self.btn_prev.setToolTip("Pista anterior")
        self.btn_prev.setStyleSheet("QPushButton { font-size: 17px; border: none; background: transparent; color: #ff1744; } QPushButton:hover { color: #ffffff; }")
        self.btn_prev.clicked.connect(self.mpris.previous)
        controls_layout.addWidget(self.btn_prev)

        # 3. CENTRO EXACTO: Botón Play/Pausa principal en círculo rojo relleno
        self.btn_play = QPushButton("▶", self.normal_page)
        self.btn_play.setObjectName("PlayButton")
        self.btn_play.setFixedSize(44, 44)
        self.btn_play.setToolTip("Reproducir / Pausar")
        self.btn_play.clicked.connect(self.mpris.play_pause)
        controls_layout.addWidget(self.btn_play)

        # 4. Derecha: Pista Siguiente (⏭)
        self.btn_next = QPushButton("⏭", self.normal_page)
        self.btn_next.setFixedSize(34, 34)
        self.btn_next.setToolTip("Pista siguiente")
        self.btn_next.setStyleSheet("QPushButton { font-size: 17px; border: none; background: transparent; color: #ff1744; } QPushButton:hover { color: #ffffff; }")
        self.btn_next.clicked.connect(self.mpris.next)
        controls_layout.addWidget(self.btn_next)

        # 5. Extremo Derecho: Repetición (↻)
        self.btn_loop = QPushButton("↻", self.normal_page)
        self.btn_loop.setFixedSize(32, 32)
        self.btn_loop.setToolTip("Alternar repetición")
        self.btn_loop.setStyleSheet("QPushButton { font-size: 15px; border: none; background: transparent; color: #ff1744; } QPushButton:hover { color: #ffffff; }")
        self.btn_loop.clicked.connect(self.mpris.cycle_loop_status)
        controls_layout.addWidget(self.btn_loop)

        controls_layout.addStretch()

        normal_layout.addLayout(controls_layout)

        # Control de Volumen Inferior
        volume_layout = QHBoxLayout()
        volume_layout.setContentsMargins(4, 2, 4, 2)
        volume_layout.setSpacing(6)

        vol_min_icon = QLabel("🔊", self.normal_page)
        vol_min_icon.setStyleSheet("color: #ff1744; font-size: 11px; border: none;")

        self.slider_volume = QSlider(Qt.Orientation.Horizontal, self.normal_page)
        self.slider_volume.setObjectName("VolumeSlider")
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setValue(100)
        self.slider_volume.valueChanged.connect(self._on_volume_slider_changed)

        vol_max_icon = QLabel("🔊", self.normal_page)
        vol_max_icon.setStyleSheet("color: #ff1744; font-size: 14px; border: none;")

        volume_layout.addWidget(vol_min_icon)
        volume_layout.addWidget(self.slider_volume)
        volume_layout.addWidget(vol_max_icon)

        normal_layout.addLayout(volume_layout)
        self.stacked.addWidget(self.normal_page)

        # --- VISTA COMPACTA REDISEÑADA & OPTIMIZADA ---
        self.compact_page = QWidget()
        compact_layout = QHBoxLayout(self.compact_page)
        compact_layout.setContentsMargins(8, 4, 8, 4)
        compact_layout.setSpacing(8)

        # 1. Mini Pantalla de Arte / Audífonos & EKG Animado en Tiempo Real (50x50 px)
        self.compact_art_screen = QLabel(self.compact_page)
        self.compact_art_screen.setObjectName("ArtScreen")
        self.compact_art_screen.setFixedSize(50, 50)
        self.compact_art_screen.setStyleSheet(
            f"QLabel#ArtScreen {{ background-color: #050508; border: 2px solid {self.accent_color}; border-radius: 12px; }}"
        )
        self.compact_art_screen.setAlignment(Qt.AlignmentFlag.AlignCenter)

        compact_art_layout = QVBoxLayout(self.compact_art_screen)
        compact_art_layout.setContentsMargins(0, 0, 0, 0)
        self.compact_ekg_bg = HeadphoneEKGWidget(self.compact_art_screen, accent_color=self.accent_color)
        compact_art_layout.addWidget(self.compact_ekg_bg)

        # Superponer portada cuando hay carátula
        self.compact_art = QLabel(self.compact_ekg_bg)
        self.compact_art.setFixedSize(50, 50)
        self.compact_art.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.compact_art.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.compact_art.setStyleSheet("background: transparent; border: none;")
        
        compact_layout.addWidget(self.compact_art_screen)

        # 2. Información del Tema (Título y Artista en Marquesina)
        compact_info = QVBoxLayout()
        compact_info.setContentsMargins(0, 2, 0, 2)
        compact_info.setSpacing(2)

        self.compact_title = MarqueeLabel(
            "Sin título",
            font=QFont("Sans Serif", 10, QFont.Weight.Bold),
            color_str="#ffffff",
            parent=self.compact_page
        )
        self.compact_title.setFixedHeight(20)
        compact_info.addWidget(self.compact_title)

        self.compact_artist = MarqueeLabel(
            "Artista",
            font=QFont("Sans Serif", 8),
            color_str="#ff4d6d",
            parent=self.compact_page
        )
        self.compact_artist.setFixedHeight(16)
        compact_info.addWidget(self.compact_artist)
        compact_layout.addLayout(compact_info, stretch=1)

        # 3. Fila Completa de Controles Multimedia Simétricos en Modo Compacto
        compact_controls = QHBoxLayout()
        compact_controls.setContentsMargins(0, 0, 0, 0)
        compact_controls.setSpacing(4)

        # Favorito (♥)
        self.btn_compact_like = QPushButton("♥", self.compact_page)
        self.btn_compact_like.setFixedSize(28, 28)
        self.btn_compact_like.setToolTip("Marcar / Desmarcar Favorito (Ctrl+F)")
        self.btn_compact_like.setStyleSheet(f"QPushButton {{ font-size: 14px; border: none; background: transparent; color: {self.accent_color}; }} QPushButton:hover {{ color: #ffffff; }}")
        self.btn_compact_like.clicked.connect(self.toggle_favorite)
        compact_controls.addWidget(self.btn_compact_like)

        # Anterior (⏮)
        self.btn_compact_prev = QPushButton("⏮", self.compact_page)
        self.btn_compact_prev.setFixedSize(28, 28)
        self.btn_compact_prev.setToolTip("Pista anterior")
        self.btn_compact_prev.setStyleSheet(f"QPushButton {{ font-size: 15px; border: none; background: transparent; color: {self.accent_color}; }} QPushButton:hover {{ color: #ffffff; }}")
        self.btn_compact_prev.clicked.connect(self.mpris.previous)
        compact_controls.addWidget(self.btn_compact_prev)

        # Play/Pausa Principal (▶) - CÍRCULO PERFECTO
        self.btn_compact_play = QPushButton("▶", self.compact_page)
        self.btn_compact_play.setFixedSize(38, 38)
        self.btn_compact_play.setToolTip("Reproducir / Pausar")
        self.btn_compact_play.clicked.connect(self.mpris.play_pause)
        self._update_compact_play_style()
        compact_controls.addWidget(self.btn_compact_play)

        # Siguiente (⏭)
        self.btn_compact_next = QPushButton("⏭", self.compact_page)
        self.btn_compact_next.setFixedSize(28, 28)
        self.btn_compact_next.setToolTip("Pista siguiente")
        self.btn_compact_next.setStyleSheet(f"QPushButton {{ font-size: 15px; border: none; background: transparent; color: {self.accent_color}; }} QPushButton:hover {{ color: #ffffff; }}")
        self.btn_compact_next.clicked.connect(self.mpris.next)
        compact_controls.addWidget(self.btn_compact_next)

        compact_layout.addLayout(compact_controls)

        self.stacked.addWidget(self.compact_page)

        self.container_layout.addWidget(self.stacked)
        outer_layout.addWidget(self.container)

    def apply_mode(self):
        if self.is_compact:
            self.stacked.setCurrentIndex(1)
            if hasattr(self, 'drip') and self.drip:
                self.drip.hide()
            w = self.config.get("compact_width", 330)
            h = self.config.get("compact_height", 72)
            self.setMinimumSize(280, 64)
            self.setMaximumSize(900, 120)
            self.resize(w, h)
            self.btn_compact_toggle.setText("⤢")
        else:
            self.stacked.setCurrentIndex(0)
            if hasattr(self, 'drip') and self.drip:
                self.drip.show()
            w = self.config.get("width", 280)
            h = self.config.get("height", 360)
            self.setMinimumSize(240, 280)
            self.setMaximumSize(800, 900)
            self.resize(w, h)
            self.btn_compact_toggle.setText("⤢")


    def toggle_compact_mode(self):
        self.is_compact = not self.is_compact
        self.config.set("compact_mode", self.is_compact)
        self.apply_mode()

    def set_window_flags(self):
        flags = Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint
        if self.stays_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def changeEvent(self, event):
        if event and event.type() == event.Type.WindowStateChange:
            if self.isMaximized() or self.isFullScreen():
                self.showNormal()
                self.apply_mode()
        super().changeEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        if self.is_compact:
            self.config.set("compact_width", w)
            self.config.set("compact_height", h)
        else:
            self.config.set("width", w)
            self.config.set("height", h)

        if self.current_pixmap and not self.current_pixmap.isNull():
            self._apply_pixmap(self.current_pixmap)

    def connect_signals(self) -> None:
        self.mpris.metadata_changed.connect(self.update_metadata)
        self.mpris.playback_status_changed.connect(self.update_status)
        self.mpris.position_changed.connect(self.update_position)
        self.mpris.loop_status_changed.connect(self.update_loop_ui)
        self.mpris.shuffle_status_changed.connect(self.update_shuffle_ui)
        self.mpris.player_available.connect(self.on_player_available)
        self.mpris.volume_changed.connect(self.update_volume_ui)
        self.container.image_changed.connect(self._on_bg_image_changed)

    def setup_shortcuts(self) -> None:
        """Configura atajos de teclado locales y globales para controlar el reproductor."""
        # Toggle Visibilidad (Ctrl+H / F12 / Esc)
        shortcut_toggle_h = QShortcut(QKeySequence("Ctrl+H"), self)
        shortcut_toggle_h.activated.connect(self.toggle_visibility)

        shortcut_f12 = QShortcut(QKeySequence("F12"), self)
        shortcut_f12.activated.connect(self.toggle_visibility)

        shortcut_esc = QShortcut(QKeySequence("Esc"), self)
        shortcut_esc.activated.connect(self.hide)

        # Toggle Modo Compacto (Ctrl+C / F11)
        shortcut_compact = QShortcut(QKeySequence("Ctrl+C"), self)
        shortcut_compact.activated.connect(self.toggle_compact_mode)

        shortcut_f11 = QShortcut(QKeySequence("F11"), self)
        shortcut_f11.activated.connect(self.toggle_compact_mode)

        # Controles de Medios (Espacio / Flechas Derecha / Izquierda / Arriba / Abajo)
        shortcut_space = QShortcut(QKeySequence("Space"), self)
        shortcut_space.activated.connect(self.mpris.play_pause)

        shortcut_next = QShortcut(QKeySequence("Right"), self)
        shortcut_next.activated.connect(self.mpris.next)

        shortcut_prev = QShortcut(QKeySequence("Left"), self)
        shortcut_prev.activated.connect(self.mpris.previous)

        shortcut_vol_up = QShortcut(QKeySequence("Up"), self)
        shortcut_vol_up.activated.connect(lambda: self._adjust_volume(0.05))

        shortcut_vol_down = QShortcut(QKeySequence("Down"), self)
        shortcut_vol_down.activated.connect(lambda: self._adjust_volume(-0.05))

        # Toggle Favorito (Ctrl+F)
        shortcut_fav = QShortcut(QKeySequence("Ctrl+F"), self)
        shortcut_fav.activated.connect(self.toggle_favorite)

        # Siguiente Fondo de Pantalla (Ctrl+B)
        shortcut_bg = QShortcut(QKeySequence("Ctrl+B"), self)
        shortcut_bg.activated.connect(self.container.next_background)

        # Toggle Siempre Encima (Ctrl+T)
        shortcut_top = QShortcut(QKeySequence("Ctrl+T"), self)
        shortcut_top.activated.connect(self.toggle_always_on_top)

    def setup_tray_icon(self) -> None:
        """Inicializa el icono de la bandeja del sistema (System Tray Icon) para ocultar/mostrar la ventana."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        self.tray_icon = QSystemTrayIcon(self)

        # Dibujar icono personalizado 32x32 pastel rosa
        pix = QPixmap(32, 32)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor("#ff55a5"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(2, 2, 28, 28)
        p.setPen(QColor("#ffffff"))
        p.setFont(QFont("DejaVu Sans", 14, QFont.Weight.Bold))
        p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "♫")
        p.end()

        self.tray_icon.setIcon(QIcon(pix))
        self.tray_icon.setToolTip("Custom Floating Music Player")

        # Menú contextual de la bandeja
        tray_menu = QMenu()
        tray_menu.setStyleSheet(MAIN_STYLE)

        show_hide_act = QAction("👁️ Mostrar / Ocultar (Ctrl+H)", self)
        show_hide_act.triggered.connect(self.toggle_visibility)
        tray_menu.addAction(show_hide_act)

        tray_menu.addSeparator()

        play_act = QAction("⏯️ Reproducir / Pausar (Espacio)", self)
        play_act.triggered.connect(self.mpris.play_pause)
        tray_menu.addAction(play_act)

        next_act = QAction("⏭️ Pista Siguiente (Flecha Derecha)", self)
        next_act.triggered.connect(self.mpris.next)
        tray_menu.addAction(next_act)

        prev_act = QAction("⏮️ Pista Anterior (Flecha Izquierda)", self)
        prev_act.triggered.connect(self.mpris.previous)
        tray_menu.addAction(prev_act)

        tray_menu.addSeparator()

        quit_act = QAction("❌ Salir", self)
        quit_act.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(quit_act)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_icon_activated)
        self.tray_icon.show()

    def _on_tray_icon_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.toggle_visibility()

    def toggle_visibility(self) -> None:
        """Alterna la visibilidad de la ventana flotante."""
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def _adjust_volume(self, delta: float) -> None:
        """Ajusta progresivamente el volumen (+5% / -5%)."""
        current_vol = self.slider_volume.value() / 100.0 if hasattr(self, 'slider_volume') else 1.0
        new_vol = max(0.0, min(1.0, current_vol + delta))
        self.mpris.set_volume(new_vol)

    @pyqtSlot(float)
    def update_volume_ui(self, volume: float) -> None:
        """Sincroniza el slider de volumen cuando cambia el volumen en DBus/MPRIS."""
        val = int(max(0.0, min(1.0, volume)) * 100)
        self.slider_volume.blockSignals(True)
        self.slider_volume.setValue(val)
        self.slider_volume.blockSignals(False)

    def _on_volume_slider_changed(self, val: int) -> None:
        """Envia el nuevo volumen al reproductor MPRIS."""
        vol = val / 100.0
        self.mpris.set_volume(vol)

    @pyqtSlot(dict)
    def update_metadata(self, metadata: dict):
        if not metadata:
            self.title_label.setText("Sin reproducción")
            self.artist_label.setText("---")
            self.compact_title.setText("Sin reproducción")
            self.compact_artist.setText("---")
            self.set_art_placeholder()
            self._update_like_ui(False)
            return

        title = metadata.get("title", "Sin reproducción")
        artist = metadata.get("artist", "---")
        art_url = metadata.get("art_url", "")
        self.duration_sec = metadata.get("length_sec", 0)

        self.title_label.setText(title)
        self.artist_label.setText(artist)
        self.compact_title.setText(title)
        self.compact_artist.setText(artist)

        is_fav = self.config.is_favorite(title, artist)
        self._update_like_ui(is_fav)

        if art_url != self.current_art_url:
            self.current_art_url = art_url
            self.load_album_art(art_url)

    @pyqtSlot(str)
    def update_status(self, status: str):
        is_playing = (status == "Playing")
        self.equalizer.set_playing(is_playing)
        self.ekg_bg.set_playing(is_playing)
        if hasattr(self, 'compact_ekg_bg') and self.compact_ekg_bg:
            self.compact_ekg_bg.set_playing(is_playing)

        play_icon = "⏸" if is_playing else "▶"
        self.btn_play.setText(play_icon)
        if hasattr(self, 'btn_compact_play') and self.btn_compact_play:
            self.btn_compact_play.setText(play_icon)

    @pyqtSlot(int, int)
    def update_position(self, pos_sec: int, length_sec: int):
        if self.is_user_seeking:
            return

        total_sec = length_sec if length_sec > 0 else self.duration_sec
        if total_sec > 0:
            val = int((pos_sec / total_sec) * 1000)
            self.progress_bar.setValue(val)
            rem_sec = max(0, total_sec - pos_sec)
            
            pos_min, pos_s = pos_sec // 60, pos_sec % 60
            rem_min, rem_s = rem_sec // 60, rem_sec % 60
            
            self.time_left_label.setText(f"{pos_min}:{pos_s:02d}")
            self.time_right_label.setText(f"-{rem_min}:{rem_s:02d}")
        else:
            self.progress_bar.setValue(0)
            self.time_left_label.setText("0:00")
            self.time_right_label.setText("-0:00")

    def _on_slider_pressed(self):
        self.is_user_seeking = True

    def _on_slider_released(self):
        self.is_user_seeking = False
        val = self.progress_bar.value()
        if self.duration_sec > 0:
            target_sec = int((val / 1000.0) * self.duration_sec)
            self.mpris.set_position(target_sec)

    @pyqtSlot(str)
    def update_loop_ui(self, status: str):
        if status in ("Track", "Playlist"):
            self.btn_loop.setStyleSheet("QPushButton { font-size: 14px; border: none; background: transparent; color: #ffffff; font-weight: bold; }")
        else:
            self.btn_loop.setStyleSheet("QPushButton { font-size: 14px; border: none; background: transparent; color: #ff1744; } QPushButton:hover { color: #ffffff; }")

    @pyqtSlot(bool)
    def update_shuffle_ui(self, enabled: bool):
        pass

    @pyqtSlot(bool, str)
    def on_player_available(self, available: bool, name: str):
        if available and name:
            self.badge_label.setText(f"🎧 {name.upper()}")
        else:
            self.badge_label.setText("🎧 RED WORLD")
            self.title_label.setText("Sin reproductor")
            self.artist_label.setText("Abre Spotify, Strawberry o tu navegador")
            self.compact_title.setText("Sin reproductor")
            self.compact_artist.setText("Abre Spotify, Strawberry o tu navegador")
            self.btn_play.setText("▶")
            self.btn_compact_play.setText("▶")
            self.set_art_placeholder()

    def set_art_placeholder(self):
        self.current_art_url = ""
        self.current_pixmap = None
        if hasattr(self, 'ekg_bg') and self.ekg_bg:
            self.ekg_bg.set_album_art(None)
        if hasattr(self, 'compact_art') and self.compact_art:
            self.compact_art.setPixmap(QPixmap())

    def load_album_art(self, art_url: str):
        if not art_url:
            self.set_art_placeholder()
            return

        if art_url.startswith("file://"):
            local_path = urllib.parse.unquote(art_url[7:])
            pixmap = QPixmap(local_path)
            self._apply_pixmap(pixmap)
        elif art_url.startswith("http://") or art_url.startswith("https://"):
            req = QNetworkRequest(QUrl(art_url))
            self.net_manager.get(req)
        else:
            self.set_art_placeholder()

    @pyqtSlot(QNetworkReply)
    def _on_art_download_finished(self, reply: QNetworkReply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            self._apply_pixmap(pixmap)
        else:
            self.set_art_placeholder()
        reply.deleteLater()

    def _apply_pixmap(self, pixmap: QPixmap):
        self.current_pixmap = pixmap
        if not pixmap.isNull():
            stop0, stop1 = extract_pastel_colors(pixmap)
            self.art_screen.setStyleSheet(f"QLabel#ArtScreen {{ background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {stop0}, stop:1 {stop1}); border: 2px solid {self.accent_color}; border-radius: 12px; }}")

            if hasattr(self, 'ekg_bg') and self.ekg_bg:
                self.ekg_bg.set_album_art(pixmap)

            if hasattr(self, 'compact_art') and self.compact_art:
                scaled_compact = pixmap.scaled(
                    48, 48,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.compact_art.setPixmap(scaled_compact)
        else:
            self.set_art_placeholder()

    def toggle_favorite(self):
        meta = self.mpris.current_metadata
        is_fav = self.config.toggle_favorite(meta)
        self._update_like_ui(is_fav)

    def _update_like_ui(self, is_fav: bool):
        if is_fav:
            style_fav = "QPushButton { font-size: 15px; border: none; background: transparent; color: #ffffff; font-weight: bold; }"
            self.btn_like.setStyleSheet(style_fav)
            if hasattr(self, 'btn_compact_like') and self.btn_compact_like:
                self.btn_compact_like.setStyleSheet(style_fav)
        else:
            style_normal = f"QPushButton {{ font-size: 15px; border: none; background: transparent; color: {self.accent_color}; }} QPushButton:hover {{ color: #ffffff; }}"
            self.btn_like.setStyleSheet(style_normal)
            if hasattr(self, 'btn_compact_like') and self.btn_compact_like:
                self.btn_compact_like.setStyleSheet(style_normal)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta != 0:
            step = 0.05 if delta > 0 else -0.05
            vol_reply = self.mpris.props_iface.call("Get", "org.mpris.MediaPlayer2.Player", "Volume") if self.mpris.props_iface else None
            curr_vol = float(vol_reply.arguments()[0]) if vol_reply and vol_reply.arguments() else 1.0
            new_vol = max(0.0, min(1.0, curr_vol + step))
            self.mpris.set_volume(new_vol)
            event.accept()

    def _get_resize_edges(self, pos: QPoint) -> Qt.Edge:
        edges = Qt.Edge(0)
        w, h = self.width(), self.height()
        if pos.x() <= self.RESIZE_MARGIN:
            edges |= Qt.Edge.LeftEdge
        elif pos.x() >= w - self.RESIZE_MARGIN:
            edges |= Qt.Edge.RightEdge

        if pos.y() <= self.RESIZE_MARGIN:
            edges |= Qt.Edge.TopEdge
        elif pos.y() >= h - self.RESIZE_MARGIN:
            edges |= Qt.Edge.BottomEdge

        return edges

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        edges = self._get_resize_edges(pos)

        if edges.value != 0:
            if (edges & Qt.Edge.RightEdge and edges & Qt.Edge.BottomEdge) or (edges & Qt.Edge.LeftEdge and edges & Qt.Edge.TopEdge):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif (edges & Qt.Edge.LeftEdge and edges & Qt.Edge.BottomEdge) or (edges & Qt.Edge.RightEdge and edges & Qt.Edge.TopEdge):
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            elif edges & (Qt.Edge.LeftEdge | Qt.Edge.RightEdge):
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            elif edges & (Qt.Edge.TopEdge | Qt.Edge.BottomEdge):
                self.setCursor(Qt.CursorShape.SizeVerCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            edges = self._get_resize_edges(pos)

            if edges.value != 0 and self.windowHandle():
                self.windowHandle().startSystemResize(edges)
                event.accept()
                return
            elif self.windowHandle():
                self.windowHandle().startSystemMove()
                event.accept()
                return
        super().mousePressEvent(event)

    def moveEvent(self, event):
        super().moveEvent(event)
        self.config.set("pos_x", self.x())
        self.config.set("pos_y", self.y())

    def is_autostart_enabled(self) -> bool:
        import os
        return os.path.exists(os.path.expanduser("~/.config/autostart/custom-music-player.desktop"))

    def toggle_autostart(self):
        import os
        autostart_path = os.path.expanduser("~/.config/autostart/custom-music-player.desktop")
        if os.path.exists(autostart_path):
            os.remove(autostart_path)
        else:
            os.makedirs(os.path.dirname(autostart_path), exist_ok=True)
            content = """[Desktop Entry]
Type=Application
Name=Custom Floating Music Player
Comment=Reproductor flotante de música personalizado
Exec=/usr/bin/python3 /home/phame/.local/bin/custom-music-player/main.py
WorkingDirectory=/home/phame/.local/bin/custom-music-player
Icon=multimedia-audio-player
Terminal=false
Categories=AudioVideo;Player;
X-GNOME-Autostart-enabled=true
X-KDE-autostart-after=panel
"""
            with open(autostart_path, "w", encoding="utf-8") as f:
                f.write(content)
            os.chmod(autostart_path, 0o755)

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(MAIN_STYLE)

        hide_act = QAction("👁️ Ocultar a la bandeja (Ctrl+H / Esc)", self)
        hide_act.triggered.connect(self.hide)
        menu.addAction(hide_act)

        menu.addSeparator()

        players_menu = menu.addMenu("🎵 Reproductor Activo")
        services = self.mpris.get_available_services()

        if not services:
            no_player_act = QAction("No hay reproductores detectados", self)
            no_player_act.setEnabled(False)
            players_menu.addAction(no_player_act)
        else:
            for s in services:
                clean_name = s.replace("org.mpris.MediaPlayer2.", "").capitalize()
                act = QAction(clean_name, self)
                act.setCheckable(True)
                act.setChecked(s == self.mpris.active_service)
                act.triggered.connect(lambda checked, s_name=s: self.mpris.set_active_service(s_name))
                players_menu.addAction(act)

        menu.addSeparator()

        mode_text = "📐 Modo Normal (Ctrl+C)" if self.is_compact else "📐 Modo Compacto (Ctrl+C)"
        compact_act = QAction(mode_text, self)
        compact_act.triggered.connect(self.toggle_compact_mode)
        menu.addAction(compact_act)

        bg_menu = menu.addMenu("🖼️ Fondos de Pantalla")

        select_file_act = QAction("🖼️ Seleccionar Imagen de Fondo...", self)
        select_file_act.triggered.connect(self._choose_bg_image)
        bg_menu.addAction(select_file_act)

        select_folder_act = QAction("📁 Seleccionar Carpeta de Fondos...", self)
        select_folder_act.triggered.connect(self._choose_bg_folder)
        bg_menu.addAction(select_folder_act)

        bg_menu.addSeparator()

        next_bg_act = QAction("⏭️ Cambiar de fondo ahora (Ctrl+B)", self)
        next_bg_act.triggered.connect(self.container.next_background)
        bg_menu.addAction(next_bg_act)

        slideshow_act = QAction("🔄 Carrusel automático (15s)", self)
        slideshow_act.setCheckable(True)
        slideshow_act.setChecked(self.container.slideshow_enabled)
        slideshow_act.triggered.connect(self._toggle_slideshow_menu)
        bg_menu.addAction(slideshow_act)

        inner_art_menu = menu.addMenu("🖼️ Recuadro de Canción")

        select_inner_act = QAction("🖼️ Cambiar Imagen de Recuadro Central...", self)
        select_inner_act.triggered.connect(self._choose_inner_image)
        inner_art_menu.addAction(select_inner_act)

        inner_art_menu.addSeparator()

        mode_auto_act = QAction("🎵 Mostrar Carátula de Música (Auto)", self)
        mode_auto_act.setCheckable(True)
        mode_auto_act.setChecked(self.ekg_bg.art_mode == "auto")
        mode_auto_act.triggered.connect(lambda: self._set_inner_art_mode("auto"))
        inner_art_menu.addAction(mode_auto_act)

        mode_custom_act = QAction("📌 Mostrar SIEMPRE Imagen Personalizada", self)
        mode_custom_act.setCheckable(True)
        mode_custom_act.setChecked(self.ekg_bg.art_mode == "custom_always")
        mode_custom_act.triggered.connect(lambda: self._set_inner_art_mode("custom_always"))
        inner_art_menu.addAction(mode_custom_act)

        aspect_menu = bg_menu.addMenu("📐 Modo de Ajuste de Imagen")
        fit_act = QAction("Ajustar (Ver completa sin recortes)", self)
        fit_act.setCheckable(True)
        fit_act.setChecked(self.container.aspect_mode == "fit")
        fit_act.triggered.connect(lambda: self._set_bg_aspect_mode("fit"))
        aspect_menu.addAction(fit_act)

        fill_act = QAction("Llenar ventana (Recortar bordes)", self)
        fill_act.setCheckable(True)
        fill_act.setChecked(self.container.aspect_mode == "fill")
        fill_act.triggered.connect(lambda: self._set_bg_aspect_mode("fill"))
        aspect_menu.addAction(fill_act)

        stretch_act = QAction("Estirar a la ventana", self)
        stretch_act.setCheckable(True)
        stretch_act.setChecked(self.container.aspect_mode == "stretch")
        stretch_act.triggered.connect(lambda: self._set_bg_aspect_mode("stretch"))
        aspect_menu.addAction(stretch_act)

        theme_menu = menu.addMenu("🎨 Color de Tema & Controles")
        colors = [
            ("🔴 Carmesí Neón", "#ff1744"),
            ("🔵 Cyan / Azul Neón", "#00e5ff"),
            ("🟣 Púrpura Neón", "#e040fb"),
            ("🟢 Verde Esmeralda", "#00e676"),
            ("🟠 Naranja Neón", "#ff9100"),
            ("🩷 Rosa Neón", "#ff4081"),
            ("⚪ Blanco Puro", "#ffffff")
        ]
        for label, hex_c in colors:
            c_act = QAction(label, self)
            c_act.setCheckable(True)
            c_act.setChecked(self.accent_color.lower() == hex_c.lower())
            c_act.triggered.connect(lambda checked, h=hex_c: self._set_theme_color(h))
            theme_menu.addAction(c_act)

        theme_menu.addSeparator()
        custom_color_act = QAction("🎨 Color Personalizado...", self)
        custom_color_act.triggered.connect(self._pick_custom_color)
        theme_menu.addAction(custom_color_act)

        top_act = QAction("📌 Siempre encima (Ctrl+T)", self)
        top_act.setCheckable(True)
        top_act.setChecked(self.stays_on_top)
        top_act.triggered.connect(self.toggle_always_on_top)
        menu.addAction(top_act)

        autostart_act = QAction("🚀 Iniciar con el sistema", self)
        autostart_act.setCheckable(True)
        autostart_act.setChecked(self.is_autostart_enabled())
        autostart_act.triggered.connect(self.toggle_autostart)
        menu.addAction(autostart_act)

        favs_menu = menu.addMenu("♥ Favoritos Guardados (Ctrl+F)")
        favs = self.config.get("favorites", [])
        if not favs:
            no_fav = QAction("Sin favoritos guardados", self)
            no_fav.setEnabled(False)
            favs_menu.addAction(no_fav)
        else:
            for f in favs:
                label_str = f"{f.get('title')} - {f.get('artist')}"
                fav_act = QAction(label_str, self)
                favs_menu.addAction(fav_act)

        refresh_act = QAction("🔄 Refrescar MPRIS", self)
        refresh_act.triggered.connect(self.mpris.scan_services)
        menu.addAction(refresh_act)

        menu.addSeparator()

        quit_act = QAction("❌ Salir", self)
        quit_act.triggered.connect(QApplication.instance().quit)
        menu.addAction(quit_act)

        menu.exec(event.globalPos())

    def toggle_always_on_top(self) -> None:
        self.stays_on_top = not self.stays_on_top
        self.config.set("stays_on_top", self.stays_on_top)
        self.set_window_flags()
        self.show()

    def _toggle_slideshow_menu(self) -> None:
        new_state = self.container.toggle_slideshow()
        self.config.set("bg_slideshow_enabled", new_state)

    def _set_bg_aspect_mode(self, mode: str) -> None:
        self.container.set_aspect_mode(mode)
        self.config.set("bg_aspect_mode", mode)

    def _choose_inner_image(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Imagen para Recuadro de Canción", "", "Imágenes (*.png *.jpg *.jpeg *.webp)"
        )
        if file_path:
            if self.ekg_bg.set_custom_bg_image(file_path):
                self.config.set("custom_inner_image", file_path)

    def _set_inner_art_mode(self, mode: str) -> None:
        self.ekg_bg.set_art_mode(mode)
        self.config.set("inner_art_mode", mode)

    def _choose_bg_image(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Imagen de Fondo", "", "Imágenes (*.png *.jpg *.jpeg *.webp)"
        )
        if file_path:
            if self.container.set_custom_image(file_path):
                self.config.set("background_image", file_path)

    def _choose_bg_folder(self) -> None:
        folder_path = QFileDialog.getExistingDirectory(
            self, "Seleccionar Carpeta de Fondos", ""
        )
        if folder_path:
            if self.container.set_folder_path(folder_path):
                self.config.set("bg_folder", folder_path)

    def _update_compact_play_style(self) -> None:
        if not hasattr(self, 'btn_compact_play') or not self.btn_compact_play:
            return
        accent_qcol = QColor(self.accent_color)
        h, s, v, a = accent_qcol.getHsv()
        hover_qcol = QColor.fromHsv(h if h >= 0 else 0, max(0, s - 30), min(255, v + 30))
        hover_hex = hover_qcol.name()
        
        self.btn_compact_play.setStyleSheet(
            f"QPushButton {{ background-color: {self.accent_color}; color: #ffffff; border-radius: 19px; font-size: 16px; border: none; }} "
            f"QPushButton:hover {{ background-color: {hover_hex}; color: #ffffff; }} "
            f"QPushButton:pressed {{ background-color: {self.accent_color}; color: #dddddd; }}"
        )

    def _on_bg_image_changed(self, image_path: str) -> None:
        if not image_path:
            return
        self.config.set("background_image", image_path)
        
        # 1. Comprobar si esta imagen ya tiene un color de tema asignado expresamente
        saved_color = self.config.get_theme_color_for_image(image_path)
        if saved_color:
            self._set_theme_color(saved_color, save_to_img=False)
            return

        # 2. Si no tiene color asignado, extraer color neón/vibrante único de la imagen sin repetir el acento actual
        preset_colors = ["#ff1744", "#00e5ff", "#e040fb", "#00e676", "#ff9100", "#ff4081"]
        pix = QPixmap(image_path)
        
        if not pix.isNull():
            extracted = extract_vibrant_accent_color(pix, fallback_hex="#ff1744")
            if extracted.lower() == self.accent_color.lower():
                curr_idx = preset_colors.index(self.accent_color) if self.accent_color in preset_colors else 0
                new_color = preset_colors[(curr_idx + 1) % len(preset_colors)]
            else:
                new_color = extracted
        else:
            curr_idx = preset_colors.index(self.accent_color) if self.accent_color in preset_colors else 0
            new_color = preset_colors[(curr_idx + 1) % len(preset_colors)]

        self.config.set_theme_color_for_image(image_path, new_color)
        self._set_theme_color(new_color, save_to_img=False)

    def _set_theme_color(self, hex_color: str, save_to_img: bool = True) -> None:
        self.accent_color = hex_color
        self.config.set("accent_color", hex_color)

        if save_to_img:
            curr_bg = self.config.get("background_image")
            if curr_bg:
                self.config.set_theme_color_for_image(curr_bg, hex_color)

        self.container.accent_color = hex_color
        self.ekg_bg.accent_color = hex_color
        if hasattr(self, 'compact_ekg_bg') and self.compact_ekg_bg:
            self.compact_ekg_bg.accent_color = hex_color
        if hasattr(self, 'compact_art_screen') and self.compact_art_screen:
            self.compact_art_screen.setStyleSheet(f"QLabel#ArtScreen {{ background-color: #050508; border: 2px solid {hex_color}; border-radius: 12px; }}")

        style_qss = get_main_style(hex_color)
        self.container.setStyleSheet(style_qss)
        self.btn_play.setStyleSheet(f"QPushButton#PlayButton {{ background-color: {hex_color}; color: #ffffff; border-radius: 22px; font-size: 18px; border: none; }}")
        self._update_compact_play_style()

        if hasattr(self, 'btn_compact_prev') and self.btn_compact_prev:
            self.btn_compact_prev.setStyleSheet(f"QPushButton {{ font-size: 15px; border: none; background: transparent; color: {hex_color}; }} QPushButton:hover {{ color: #ffffff; }}")
        if hasattr(self, 'btn_compact_next') and self.btn_compact_next:
            self.btn_compact_next.setStyleSheet(f"QPushButton {{ font-size: 15px; border: none; background: transparent; color: {hex_color}; }} QPushButton:hover {{ color: #ffffff; }}")

        meta = self.mpris.current_metadata
        title = meta.get("title", "")
        artist = meta.get("artist", "")
        is_fav = self.config.is_favorite(title, artist)
        self._update_like_ui(is_fav)

        self.container.update()
        self.ekg_bg.update()
        if hasattr(self, 'compact_ekg_bg') and self.compact_ekg_bg:
            self.compact_ekg_bg.update()

    def _pick_custom_color(self) -> None:
        color = QColorDialog.getColor(QColor(self.accent_color), self, "Seleccionar Color de Tema")
        if color.isValid():
            self._set_theme_color(color.name(), save_to_img=True)




