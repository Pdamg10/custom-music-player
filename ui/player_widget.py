import os
import random
import urllib.parse
from typing import Optional, Dict, Any, List
from PyQt6.QtCore import Qt, QSize, QPoint, QRect, pyqtSlot, QUrl, QTimer, QRectF, QFileSystemWatcher, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QAction, QShortcut, QKeySequence, QIcon, QPainter, QColor, QPainterPath, QPen, QLinearGradient
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QMenu, QApplication, QLayout, QSlider, QStackedWidget,
    QSystemTrayIcon, QFileDialog, QColorDialog
)
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from ui.styles import MAIN_STYLE, get_main_style, _build_qlineargradient
from ui.marquee_label import MarqueeLabel
from ui.equalizer_widget import EqualizerWidget
from ui.color_extractor import extract_pastel_colors, extract_vibrant_accent_color, extract_dominant_gradient_colors, get_contrasting_text_color
from ui.gradient_dialog import GradientThemeDialog
from ui.expanded_view import ExpandedPageView
from ui.y2k_volume_slider import Y2KVolumeSlider
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
        self._cached_scaled_art: Optional[QPixmap] = None
        self._cached_scaled_bg: Optional[QPixmap] = None
        self._load_headphone_pixmap(self.custom_bg_path)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate_bars)
        self.timer.setInterval(60)

    def _update_scaled_pixmaps(self) -> None:
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return
        if self.album_art_pixmap and not self.album_art_pixmap.isNull():
            self._cached_scaled_art = self.album_art_pixmap.scaled(
                w, h,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
        else:
            self._cached_scaled_art = None

        if self.headphone_pixmap and not self.headphone_pixmap.isNull():
            self._cached_scaled_bg = self.headphone_pixmap.scaled(
                w, h,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
        else:
            self._cached_scaled_bg = None

    def resizeEvent(self, event: Any) -> None:
        super().resizeEvent(event)
        self._update_scaled_pixmaps()

    def _load_headphone_pixmap(self, image_path: str) -> None:
        if image_path and os.path.exists(image_path):
            self.headphone_pixmap = QPixmap(image_path)
        else:
            default_folder = "/home/phame/Imágenes/fondo para mi reproducctor"
            if os.path.exists(default_folder) and os.path.isdir(default_folder):
                imgs = [os.path.join(default_folder, f) for f in sorted(os.listdir(default_folder)) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
                if imgs:
                    self.headphone_pixmap = QPixmap(imgs[0])
        self._update_scaled_pixmaps()

    def set_custom_bg_image(self, image_path: str) -> bool:
        if not image_path or not os.path.exists(image_path):
            return False
        pix = QPixmap(image_path)
        if pix.isNull():
            return False
        self.custom_bg_path = image_path
        self.headphone_pixmap = pix
        self._update_scaled_pixmaps()
        self.update()
        return True

    def set_art_mode(self, mode: str) -> None:
        self.art_mode = mode
        self._update_scaled_pixmaps()
        self.update()

    def set_album_art(self, pixmap: Optional[QPixmap]) -> None:
        self.album_art_pixmap = pixmap if (pixmap and not pixmap.isNull()) else None
        self._update_scaled_pixmaps()
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
            if not self._cached_scaled_art and self.album_art_pixmap:
                self._update_scaled_pixmaps()
            pix = self._cached_scaled_art or self.album_art_pixmap
            if pix and not pix.isNull():
                p.setOpacity(1.0)
                x_art = (w - pix.width()) / 2.0
                y_art = (h - pix.height()) / 2.0
                p.drawPixmap(int(x_art), int(y_art), pix)
        # 2. Si no hay carátula o se eligió modo 'custom_always', mostrar la imagen personalizada fija (opacidad 45%)
        elif self.headphone_pixmap and not self.headphone_pixmap.isNull():
            if not self._cached_scaled_bg and self.headphone_pixmap:
                self._update_scaled_pixmaps()
            pix = self._cached_scaled_bg or self.headphone_pixmap
            if pix and not pix.isNull():
                opacity = 0.85 if self.art_mode == "custom_always" else 0.45
                p.setOpacity(opacity)
                x_bg = (w - pix.width()) / 2.0
                y_bg = (h - pix.height()) / 2.0
                p.drawPixmap(int(x_bg), int(y_bg), pix)

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

    def __init__(self, parent: Optional[QWidget] = None, bg_path: Optional[str] = None, interval_sec: int = 15, folder_path: Optional[str] = None, enabled: bool = True, aspect_mode: str = "fit", accent_color: str = "#ff1744", theme_mode: str = "gradient_auto", gradient_colors: Optional[List[str]] = None, background_type: str = "gradient") -> None:
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
        self.theme_mode: str = theme_mode
        self.gradient_colors: List[str] = gradient_colors or ["#2b0b10", "#180718", "#08060c"]
        self.background_type: str = background_type

        self.folder_path = folder_path if (folder_path and os.path.exists(folder_path)) else "/home/phame/Imágenes/fondo para mi reproducctor"
        self.bg_path = bg_path
        self._scan_images(self.folder_path, fallback_path=self.bg_path)

        from ui.expanded_view import get_cached_pixmap

        if self.bg_path and os.path.exists(self.bg_path):
            pix = get_cached_pixmap(self.bg_path, 0, 0)
            if pix and not pix.isNull():
                self.current_pixmap = pix
                if self.bg_path in self.images_list:
                    self.current_img_index = self.images_list.index(self.bg_path)
        elif self.images_list:
            first_path = self.images_list[0]
            pix = get_cached_pixmap(first_path, 0, 0)
            if pix and not pix.isNull():
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

    def set_gradient_colors(self, colors: List[str], theme_mode: str = "gradient_auto") -> None:
        self.gradient_colors = colors
        self.theme_mode = theme_mode
        self.update()

    def _on_directory_changed(self, path: str) -> None:
        """Se ejecuta automáticamente cuando se añade, elimina o renombra una imagen en la carpeta."""
        self._scan_images(self.folder_path, fallback_path=self.bg_path)
        if self.slideshow_enabled and len(self.images_list) > 1 and not self.slideshow_timer.isActive():
            self.slideshow_timer.start(self.interval_sec * 1000)

    def _scan_images(self, folder_path: str, fallback_path: Optional[str] = None) -> None:
        from ui.expanded_view import get_cached_pixmap
        found = []
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            for filename in sorted(os.listdir(folder_path)):
                if filename.startswith('.'):
                    continue
                full_p = os.path.join(folder_path, filename)
                if os.path.isfile(full_p):
                    pix = get_cached_pixmap(full_p, 0, 0)
                    if pix and not pix.isNull():
                        found.append(full_p)
        
        if fallback_path and os.path.exists(fallback_path) and fallback_path not in found:
            found.insert(0, fallback_path)

        self.images_list = found

    def next_background(self) -> None:
        from ui.expanded_view import get_cached_pixmap
        if self.is_transitioning:
            return
        
        # Re-escaneo en vivo por si se añadieron o borraron archivos
        self._scan_images(self.folder_path, fallback_path=self.bg_path)

        if not self.images_list or len(self.images_list) <= 1:
            return
        
        self.current_img_index = (self.current_img_index + 1) % len(self.images_list)
        next_path = self.images_list[self.current_img_index]
        pix = get_cached_pixmap(next_path, 0, 0)
        if not pix or pix.isNull():
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
        from ui.expanded_view import get_cached_pixmap
        if not image_path or not os.path.exists(image_path):
            return False
        pix = get_cached_pixmap(image_path, 0, 0)
        if not pix or pix.isNull():
            return False
        self.bg_path = image_path
        self.background_type = "image"
        if image_path not in self.images_list:
            self.images_list.insert(0, image_path)
            self.current_img_index = 0
        else:
            self.current_img_index = self.images_list.index(image_path)
        self.current_pixmap = pix
        self.update()
        self.repaint()
        self.image_changed.emit(image_path)
        return True

    def set_background_image(self, image_path: str) -> bool:
        return self.set_custom_image(image_path)

    def set_folder_path(self, folder_path: str, active_image_path: Optional[str] = None) -> bool:
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            return False
        if hasattr(self, 'fs_watcher') and self.fs_watcher.directories():
            self.fs_watcher.removePaths(self.fs_watcher.directories())
        self.folder_path = folder_path
        self.fs_watcher.addPath(self.folder_path)
        self._scan_images(self.folder_path)

        from ui.expanded_view import get_cached_pixmap
        target_img = active_image_path if (active_image_path and os.path.exists(active_image_path)) else (self.images_list[0] if self.images_list else None)
        if target_img:
            pix = get_cached_pixmap(target_img, 0, 0)
            if pix and not pix.isNull():
                self.bg_path = target_img
                self.current_pixmap = pix
                if target_img in self.images_list:
                    self.current_img_index = self.images_list.index(target_img)
        self.update()
        self.repaint()
        return True

    def set_background_image(self, image_path: str) -> bool:
        return self.set_custom_image(image_path)

    def set_background_folder(self, folder_path: str, active_image_path: Optional[str] = None) -> bool:
        return self.set_folder_path(folder_path, active_image_path=active_image_path)

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

        # 1. Relleno de fondo: Si es modo degradado, pintar degradado al 100% y NO mostrar imagen de fondo
        if self.background_type == "gradient":
            if self.theme_mode in ("gradient_auto", "gradient_manual") and self.gradient_colors and len(self.gradient_colors) >= 2:
                grad = QLinearGradient(0, 0, w, h)
                count = len(self.gradient_colors)
                for idx, hex_c in enumerate(self.gradient_colors):
                    pos = idx / max(1, count - 1)
                    grad.setColorAt(pos, QColor(hex_c))
                p.fillRect(rect, grad)
            else:
                p.fillRect(rect, QColor(self.accent_color))
            p.restore()
            p.end()
            return

        # Si es modo imagen (wallpaper), dibujar base oscura e imagen con transparencia de alto detalle
        p.fillRect(rect, QColor("#0c0c10"))

        base_opacity = 0.85

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

        # 3.5 Vignette ligero traslúcido para destacar contenido y permitir ver la imagen al 100%
        p.setOpacity(1.0)
        overlay_grad = QLinearGradient(0, 0, 0, h)
        overlay_grad.setColorAt(0.0, QColor(5, 6, 12, 35))
        overlay_grad.setColorAt(1.0, QColor(5, 6, 12, 85))
        p.fillRect(rect, overlay_grad)

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
        self._is_manual_resizing: bool = False
        self._is_manual_moving: bool = False
        self._resize_start_geometry: Optional[QRect] = None
        self._resize_start_mouse_pos: Optional[QPoint] = None
        self._active_edges: Qt.Edge = Qt.Edge(0)
        self.is_user_seeking: bool = False
        self.duration_sec: int = 0
        self.tray_icon: Optional[QSystemTrayIcon] = None

        self.stays_on_top: bool = self.config.get("stays_on_top", False)
        self.accent_color: str = self.config.get("accent_color", "#ff1744")
        self.background_type: str = self.config.get("background_type", "gradient")
        self.theme_mode: str = self.config.get("theme_mode", "gradient_auto")
        self.button_color_source: str = self.config.get("button_color_source", "wallpaper" if self.background_type == "image" else "gradient")
        self.btn_gradient_effect: bool = self.config.get("btn_gradient_effect", True)
        self.manual_gradient_colors: List[str] = list(self.config.get("manual_gradient_colors", ["#ff1744", "#7b1fa2", "#0c0c10"]))
        self.auto_gradient_colors: List[str] = list(self.config.get("auto_gradient_colors", ["#2b0b10", "#180718", "#08060c"]))
        self.custom_btn_gradient_colors: List[str] = list(self.config.get("custom_btn_gradient_colors", ["#ff1744", "#00e5ff", "#e040fb"]))
        self.view_mode: str = self.config.get("view_mode", "normal")
        self.is_compact: bool = (self.view_mode == "compact")

        self.net_manager = QNetworkAccessManager(self)
        self.net_manager.finished.connect(self._on_art_download_finished)

        self.init_ui()
        self.connect_signals()
        self.setup_shortcuts()
        self.setup_tray_icon()
        self.apply_mode()
        self._set_theme_color(self.accent_color)

        # Cargar configuración guardada en la vista expandida en el arranque inicial
        if hasattr(self, 'expanded_page') and self.expanded_page:
            self.expanded_page.update_config_settings(self.config.config)

        # Sincronización inicial del estado MPRIS con la UI tras conectar las señales
        from ui.styles import MAIN_STYLE, get_main_style, _build_qlineargradient
        self.mpris.refresh()

    def _get_button_gradient_colors(self) -> List[str]:
        source = getattr(self, 'button_color_source', 'wallpaper' if getattr(self, 'background_type', 'gradient') == 'image' else 'gradient')
        
        raw_colors = None
        if source == "gradient":
            theme = getattr(self, 'theme_mode', 'gradient_auto')
            if theme == "gradient_manual":
                raw_colors = getattr(self, 'manual_gradient_colors', None)
            elif theme == "gradient_auto":
                raw_colors = getattr(self, 'auto_gradient_colors', None)
            else:
                raw_colors = [getattr(self, 'accent_color', '#ff1744')]
        elif source == "wallpaper":
            raw_colors = getattr(self, 'auto_gradient_colors', None)
        elif source == "custom":
            raw_colors = getattr(self, 'custom_btn_gradient_colors', None)

        fallback_accent = getattr(self, 'accent_color', '#ff1744') or '#ff1744'
        if not raw_colors or not isinstance(raw_colors, list) or len(raw_colors) < 1:
            return [fallback_accent, fallback_accent]

        clean_list = [c for c in raw_colors if c and isinstance(c, str)]
        if len(clean_list) == 0:
            return [fallback_accent, fallback_accent]
        elif len(clean_list) == 1:
            return [clean_list[0], clean_list[0]]

        return clean_list

    def _get_current_gradient_colors(self) -> List[str]:
        return self._get_button_gradient_colors()

    def _apply_button_style(self) -> None:
        colors = self._get_button_gradient_colors()
        btn_grad_on = bool(getattr(self, 'btn_gradient_effect', True))

        if hasattr(self, 'slider_volume') and self.slider_volume:
            self.slider_volume.set_accent_color(self.accent_color, colors)

        style_qss = get_main_style(self.accent_color, btn_gradient_effect=btn_grad_on, gradient_colors=colors)
        if hasattr(self, 'container') and self.container:
            self.container.setStyleSheet(style_qss)

        text_contrast = get_contrasting_text_color(self.accent_color)
        grad_str = _build_qlineargradient(colors) if (btn_grad_on and colors and len(colors) >= 2) else ""

        if btn_grad_on and grad_str:
            c0 = colors[0]
            text_contrast = get_contrasting_text_color(c0)
            play_style = (
                f"QPushButton#PlayButton {{ background: {grad_str}; color: {text_contrast}; border-radius: 22px; font-size: 18px; border: none; }} "
                f"QPushButton#PlayButton:hover {{ background: {grad_str}; border: 1.5px solid #ffffff; color: #ffffff; }} "
                f"QPushButton#PlayButton:pressed {{ background: {grad_str}; border: 1px solid rgba(255, 255, 255, 0.7); color: #dddddd; }}"
            )
            ctrl_btn_style = (
                f"QPushButton {{ background: {grad_str}; color: {text_contrast}; border-radius: 14px; border: 1px solid #ffffff; font-size: 15px; font-weight: bold; }} "
                f"QPushButton:hover {{ background: {grad_str}; border: 1.5px solid #ffffff; color: #ffffff; }} "
                f"QPushButton:pressed {{ background: {grad_str}; border: 1px solid rgba(255, 255, 255, 0.7); color: #dddddd; }}"
            )
        else:
            play_style = (
                f"QPushButton#PlayButton {{ background-color: {self.accent_color}; color: {text_contrast}; border-radius: 22px; font-size: 18px; border: none; }} "
                f"QPushButton#PlayButton:hover {{ background-color: {self.accent_color}; opacity: 0.88; color: #ffffff; }} "
                f"QPushButton#PlayButton:pressed {{ background-color: {self.accent_color}; opacity: 0.75; color: #dddddd; }}"
            )
            ctrl_btn_style = (
                f"QPushButton {{ background-color: {self.accent_color}; color: {text_contrast}; border-radius: 14px; border: none; font-size: 15px; font-weight: bold; }} "
                f"QPushButton:hover {{ background-color: {self.accent_color}; opacity: 0.88; color: #ffffff; }} "
                f"QPushButton:pressed {{ background-color: {self.accent_color}; opacity: 0.75; color: #dddddd; }}"
            )

        if hasattr(self, 'btn_play') and self.btn_play:
            self.btn_play.setStyleSheet(play_style)
        if hasattr(self, 'btn_compact_play') and self.btn_compact_play:
            self.btn_compact_play.setStyleSheet(play_style)

        if hasattr(self, 'btn_theme') and self.btn_theme:
            self.btn_theme.setStyleSheet(ctrl_btn_style)
        if hasattr(self, 'btn_prev') and self.btn_prev:
            self.btn_prev.setStyleSheet(ctrl_btn_style)
        if hasattr(self, 'btn_stop') and self.btn_stop:
            self.btn_stop.setStyleSheet(ctrl_btn_style)
        if hasattr(self, 'btn_next') and self.btn_next:
            self.btn_next.setStyleSheet(ctrl_btn_style)

        if hasattr(self, 'btn_compact_prev') and self.btn_compact_prev:
            self.btn_compact_prev.setStyleSheet(ctrl_btn_style)
        if hasattr(self, 'btn_compact_next') and self.btn_compact_next:
            self.btn_compact_next.setStyleSheet(ctrl_btn_style)

        if hasattr(self, 'expanded_page') and self.expanded_page:
            self.expanded_page.set_accent_color(self.accent_color, btn_gradient_effect=btn_grad_on, gradient_colors=colors)

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
            accent_color=self.accent_color,
            theme_mode=self.theme_mode,
            gradient_colors=self._get_current_gradient_colors(),
            background_type=self.background_type
        )
        self.container.setObjectName("CentralContainer")
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

        brand_str = str(self.config.get("brand_name", "RED WORLD")).upper()
        self.badge_label = QLabel(f"🎧 {brand_str}", self.container)
        self.badge_label.setObjectName("BadgeLabel")
        self.badge_label.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        self.badge_label.setStyleSheet("color: #ffffff; background-color: rgba(0, 0, 0, 0.45); padding: 3px 10px; border-radius: 10px; border: 1px solid #ff1744;")
        top_bar_layout.addWidget(self.badge_label)
        top_bar_layout.addStretch()

        self.btn_compact_toggle = QPushButton("⤢", self.container)
        self.btn_compact_toggle.setFixedSize(20, 20)
        self.btn_compact_toggle.setToolTip("Alternar tamaño (Normal / Compacto / Vista Grande)")
        self.btn_compact_toggle.setStyleSheet("QPushButton { font-size: 11px; font-weight: bold; border-radius: 10px; border: none; background: transparent; color: #ff1744; } QPushButton:hover { color: #ffffff; }")
        self.btn_compact_toggle.clicked.connect(self.cycle_view_mode)
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
        # 2. VISTA STACKED (Index 0: Normal, Index 1: Compacto, Index 2: Expandido en Grande)
        # ----------------------------------------------------
        self.stacked = QStackedWidget(self.container)

        # --- VISTA NORMAL (INDEX 0) ---
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

        self.artist_label = MarqueeLabel("Artista", font=QFont("Sans Serif", 9), color_str="#d0d4eb", parent=self.normal_page)
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
        self.time_right_label.setStyleSheet("color: #d0d4eb;")

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

        self.btn_mute = QPushButton("🔊", self.normal_page)
        self.slider_volume = Y2KVolumeSlider(self.normal_page)
        self.slider_volume.setObjectName("VolumeSlider")
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setValue(100)
        self.slider_volume.set_accent_color(self.accent_color, self._get_button_gradient_colors())
        self.slider_volume.valueChanged.connect(self._on_volume_slider_changed)

        volume_layout.addWidget(self.slider_volume)

        normal_layout.addLayout(volume_layout)
        self.stacked.addWidget(self.normal_page)

        # --- VISTA COMPACTA (INDEX 1) ---
        self.compact_page = QWidget()
        compact_layout = QHBoxLayout(self.compact_page)
        compact_layout.setContentsMargins(8, 4, 8, 4)
        compact_layout.setSpacing(8)

        # Mini Pantalla de Arte
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

        self.compact_art = QLabel(self.compact_ekg_bg)
        self.compact_art.setFixedSize(50, 50)
        self.compact_art.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.compact_art.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.compact_art.setStyleSheet("background: transparent; border: none;")
        
        compact_layout.addWidget(self.compact_art_screen)

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

        compact_controls = QHBoxLayout()
        compact_controls.setContentsMargins(0, 0, 0, 0)
        compact_controls.setSpacing(4)

        self.btn_compact_like = QPushButton("♥", self.compact_page)
        self.btn_compact_like.setFixedSize(28, 28)
        self.btn_compact_like.setToolTip("Marcar / Desmarcar Favorito (Ctrl+F)")
        self.btn_compact_like.setStyleSheet(f"QPushButton {{ font-size: 14px; border: none; background: transparent; color: {self.accent_color}; }} QPushButton:hover {{ color: #ffffff; }}")
        self.btn_compact_like.clicked.connect(self.toggle_favorite)
        compact_controls.addWidget(self.btn_compact_like)

        self.btn_compact_prev = QPushButton("⏮", self.compact_page)
        self.btn_compact_prev.setFixedSize(28, 28)
        self.btn_compact_prev.setToolTip("Pista anterior")
        self.btn_compact_prev.setStyleSheet(f"QPushButton {{ font-size: 15px; border: none; background: transparent; color: {self.accent_color}; }} QPushButton:hover {{ color: #ffffff; }}")
        self.btn_compact_prev.clicked.connect(self.mpris.previous)
        compact_controls.addWidget(self.btn_compact_prev)

        self.btn_compact_play = QPushButton("▶", self.compact_page)
        self.btn_compact_play.setObjectName("PlayButton")
        self.btn_compact_play.setFixedSize(38, 38)
        self.btn_compact_play.setToolTip("Reproducir / Pausar")
        self.btn_compact_play.clicked.connect(self.mpris.play_pause)
        self._update_compact_play_style()
        compact_controls.addWidget(self.btn_compact_play)

        self.btn_compact_next = QPushButton("⏭", self.compact_page)
        self.btn_compact_next.setFixedSize(28, 28)
        self.btn_compact_next.setToolTip("Pista siguiente")
        self.btn_compact_next.setStyleSheet(f"QPushButton {{ font-size: 15px; border: none; background: transparent; color: {self.accent_color}; }} QPushButton:hover {{ color: #ffffff; }}")
        self.btn_compact_next.clicked.connect(self.mpris.next)
        compact_controls.addWidget(self.btn_compact_next)

        compact_layout.addLayout(compact_controls)
        self.stacked.addWidget(self.compact_page)

        # --- VISTA EXPANDIDA EN GRANDE (INDEX 2) ---
        self.expanded_page = ExpandedPageView(self.container)
        self.expanded_page.set_accent_color(self.accent_color)
        self.expanded_page.update_config_settings(self.config.config)
        self.expanded_page.play_track_requested.connect(self._on_expanded_play_track)
        self.expanded_page.open_personalization_requested.connect(self.open_personalization_dialog)
        self.expanded_page.toggle_compact_mode_requested.connect(self.toggle_compact_mode)
        self.expanded_page.toggle_normal_mode_requested.connect(self.toggle_normal_mode)
        self.expanded_page.choose_music_folder_requested.connect(self._choose_music_folder)

        self.expanded_page.play_pause_requested.connect(self.mpris.play_pause)
        self.expanded_page.stop_requested.connect(self.mpris.stop)
        self.expanded_page.next_requested.connect(self.mpris.next)
        self.expanded_page.prev_requested.connect(self.mpris.previous)
        self.expanded_page.seek_requested.connect(self._on_expanded_seek)
        self.expanded_page.volume_changed.connect(self.mpris.set_volume)
        self.expanded_page.toggle_fav_requested.connect(self.toggle_favorite)
        self.expanded_page.loop_requested.connect(self.mpris.cycle_loop_status)
        self.expanded_page.shuffle_requested.connect(self.mpris.toggle_shuffle)
        self.stacked.addWidget(self.expanded_page)

        self.container_layout.addWidget(self.stacked)
        outer_layout.addWidget(self.container)

    def apply_mode(self):
        self.set_window_flags()

        if self.view_mode == "compact": # Modo Compacto
            self.stacked.setCurrentIndex(1)
            w = self.config.get("compact_width", 280)
            h = self.config.get("compact_height", 68)
            self.setMinimumSize(220, 50)
            self.setMaximumSize(1920, 300)
            self.resize(w, h)
            self.btn_compact_toggle.setText("⤢")
            self.btn_compact_toggle.setToolTip("Modo Compacto — Clic para alternar modo")
        elif self.view_mode == "expanded": # Modo Grande (Ventana Nativa Desktop)
            self.stacked.setCurrentIndex(2)
            w = self.config.get("expanded_width", 1200)
            h = self.config.get("expanded_height", 760)
            self.setMinimumSize(900, 600)
            self.setMaximumSize(16777215, 16777215)
            self.resize(w, h)
            self.btn_compact_toggle.setText("🗖")
            self.btn_compact_toggle.setToolTip("Modo Grande — Clic para alternar modo")
        else: # "normal" -> Modo Pequeño
            self.stacked.setCurrentIndex(0)
            w = self.config.get("normal_width", 350)
            h = self.config.get("normal_height", 410)
            if w > 550:
                w = 350
            if h > 550:
                h = 410
            self.setMinimumSize(280, 320)
            self.setMaximumSize(550, 550)
            self.resize(w, h)
            self.setMaximumSize(1920, 1440)
            self.btn_compact_toggle.setText("⤢")
            self.btn_compact_toggle.setToolTip("Modo Pequeño — Clic para alternar modo")

        pos_x = self.config.get("pos_x")
        pos_y = self.config.get("pos_y")
        if pos_x is not None and pos_y is not None:
            screen = self.screen() or QApplication.primaryScreen()
            if screen:
                avail = screen.availableGeometry()
                if pos_x < avail.x() or pos_x > avail.x() + avail.width() - 50 or pos_y < avail.y() or pos_y > avail.y() + avail.height() - 50:
                    x = avail.x() + (avail.width() - self.width()) // 2
                    y = avail.y() + (avail.height() - self.height()) // 2
                    self.move(x, y)
                    self.config.set("pos_x", x)
                    self.config.set("pos_y", y)

    def cycle_view_mode(self):
        if self.view_mode == "normal":
            self.view_mode = "expanded"
        elif self.view_mode == "expanded":
            self.view_mode = "compact"
        else:
            self.view_mode = "normal"
        self.is_compact = (self.view_mode == "compact")
        self.config.set("view_mode", self.view_mode)
        self.config.set("compact_mode", self.is_compact)
        self.apply_mode()

    def toggle_compact_mode(self):
        if self.view_mode == "compact":
            self.view_mode = "normal"
        else:
            self.view_mode = "compact"
        self.is_compact = (self.view_mode == "compact")
        self.config.set("view_mode", self.view_mode)
        self.config.set("compact_mode", self.is_compact)
        self.apply_mode()

    def toggle_expanded_mode(self):
        if self.view_mode == "expanded":
            self.view_mode = "normal"
        else:
            self.view_mode = "expanded"
        self.is_compact = (self.view_mode == "compact")
        self.config.set("view_mode", self.view_mode)
        self.config.set("compact_mode", self.is_compact)
        self.apply_mode()

    def toggle_normal_mode(self):
        self.view_mode = "normal"
        self.is_compact = False
        self.config.set("view_mode", self.view_mode)
        self.config.set("compact_mode", self.is_compact)
        self.apply_mode()

    def _on_expanded_play_track(self, index: int) -> None:
        if hasattr(self.mpris, "play_index"):
            self.mpris.play_index(index)

    def open_personalization_dialog(self) -> None:
        from ui.personalization_dialog import PersonalizationDialog
        dlg = PersonalizationDialog(current_config=self.config.config, parent=self)
        dlg.settings_saved.connect(self._on_personalization_saved)
        dlg.exec()

    def _on_personalization_saved(self, new_cfg: dict) -> None:
        for k, v in new_cfg.items():
            self.config.set(k, v)

        self.background_type = new_cfg.get("background_type", "gradient")
        self.theme_mode = new_cfg.get("theme_mode", "gradient_auto")
        self.button_color_source = new_cfg.get("button_color_source", "wallpaper" if self.background_type == "image" else "gradient")
        self.btn_gradient_effect = new_cfg.get("btn_gradient_effect", True)
        self.manual_gradient_colors = list(new_cfg.get("manual_gradient_colors", ["#ff1744", "#7b1fa2", "#0c0c10"]))
        self.auto_gradient_colors = list(new_cfg.get("auto_gradient_colors", ["#2b0b10", "#180718", "#08060c"]))
        self.custom_btn_gradient_colors = list(new_cfg.get("custom_btn_gradient_colors", ["#ff1744", "#00e5ff", "#e040fb"]))
        self.accent_color = new_cfg.get("accent_color", "#ff1744")
        self.config.set("accent_color", self.accent_color)

        self.container.background_type = self.background_type
        self.container.theme_mode = self.theme_mode
        self.container.aspect_mode = new_cfg.get("bg_aspect_mode", "stretch")

        def _clean_path(p: str) -> str:
            if not p:
                return ""
            c = str(p).strip()
            if c.startswith("file://"):
                c = urllib.parse.unquote(c[7:])
            elif c.startswith("file:"):
                c = urllib.parse.unquote(c[5:])
            return os.path.expanduser(c.strip("'\""))

        if self.background_type == "image":
            raw_img = new_cfg.get("background_image", "")
            clean_img = _clean_path(raw_img)

            raw_folder = new_cfg.get("bg_folder", "")
            clean_folder = _clean_path(raw_folder)

            if clean_folder and os.path.exists(clean_folder):
                self.container.set_folder_path(clean_folder, active_image_path=clean_img)
            elif clean_img and os.path.exists(clean_img):
                self.container.set_background_image(clean_img)

            self.container.toggle_slideshow(new_cfg.get("bg_slideshow_enabled", True))
        else:
            self.container.toggle_slideshow(False)
            colors = self._get_current_gradient_colors()
            self.container.set_gradient_colors(colors, self.theme_mode)

        self.stays_on_top = new_cfg.get("stays_on_top", False)
        self.set_window_flags()

        if hasattr(self, 'expanded_page') and self.expanded_page:
            self.expanded_page.update_config_settings(new_cfg)

        if hasattr(self, 'badge_label') and self.badge_label:
            if not (hasattr(self, 'mpris') and getattr(self.mpris, 'player_available', False) and getattr(self.mpris, 'player_name', '')):
                brand_str = str(new_cfg.get("brand_name", "RED WORLD")).upper()
                self.badge_label.setText(f"🎧 {brand_str}")

        self._set_theme_color(self.accent_color, save_to_img=False)
        self.config.save()
        self.container.update()
        self.container.repaint()
        self.update()
        self.repaint()

    def open_gradient_theme_dialog(self) -> None:
        self.open_personalization_dialog()

    def _on_theme_dialog_changed(self, mode: str, manual_colors: list, solid_accent: str) -> None:
        self.theme_mode = mode
        self.manual_gradient_colors = manual_colors
        self.accent_color = solid_accent

        self.config.set("theme_mode", mode)
        self.config.set("manual_gradient_colors", manual_colors)
        self.config.set("accent_color", solid_accent)

        self._update_gradient_theme()

    def _update_gradient_theme(self) -> None:
        colors = self._get_current_gradient_colors()
        self.container.set_gradient_colors(colors, theme_mode=self.theme_mode)
        self._set_theme_color(self.accent_color, save_to_img=False)

    def set_window_flags(self):
        was_visible = self.isVisible()
        if self.view_mode == "expanded":
            flags = (
                Qt.WindowType.Window
                | Qt.WindowType.WindowTitleHint
                | Qt.WindowType.WindowSystemMenuHint
                | Qt.WindowType.WindowMinimizeButtonHint
                | Qt.WindowType.WindowMaximizeButtonHint
                | Qt.WindowType.WindowCloseButtonHint
            )
            if self.stays_on_top:
                flags |= Qt.WindowType.WindowStaysOnTopHint
            self.setWindowFlags(flags)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            brand = str(self.config.get("brand_name", "Custom Music Player"))
            self.setWindowTitle(brand if brand and brand != "RED WORLD" else "Custom Music Player")
        else:
            flags = Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
            if self.stays_on_top:
                flags |= Qt.WindowType.WindowStaysOnTopHint
            self.setWindowFlags(flags)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        if was_visible:
            self.show()

    def changeEvent(self, event):
        if event and event.type() == event.Type.WindowStateChange:
            if self.view_mode != "expanded":
                if self.isMaximized() or self.isFullScreen():
                    self.showNormal()
                    self.apply_mode()
        super().changeEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        if not self.isMaximized() and not self.isFullScreen():
            if self.view_mode == "compact":
                self.config.set("compact_width", w)
                self.config.set("compact_height", h)
            elif self.view_mode == "expanded":
                self.config.set("expanded_width", w)
                self.config.set("expanded_height", h)
            else: # Modo Pequeño (normal)
                self.config.set("normal_width", w)
                self.config.set("normal_height", h)
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

        if hasattr(self.mpris, "playlist_updated"):
            self.mpris.playlist_updated.connect(self.on_playlist_updated)

    @pyqtSlot(list)
    def on_playlist_updated(self, playlist: list) -> None:
        if hasattr(self, 'expanded_page') and self.expanded_page:
            self.expanded_page.update_playlist_ui(playlist, getattr(self.mpris, 'current_index', 0))

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
        shortcut_compact.activated.connect(self.cycle_view_mode)

        shortcut_f11 = QShortcut(QKeySequence("F11"), self)
        shortcut_f11.activated.connect(self.cycle_view_mode)

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

        # Abrir Carpeta de Música (Ctrl+O)
        shortcut_open = QShortcut(QKeySequence("Ctrl+O"), self)
        shortcut_open.activated.connect(self._choose_music_folder)

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

    def _toggle_mute(self) -> None:
        if self.slider_volume.value() > 0:
            self._last_vol = self.slider_volume.value()
            self.slider_volume.setValue(0)
            self.btn_mute.setText("🔇")
            self.mpris.set_volume(0.0)
        else:
            last = getattr(self, '_last_vol', 100)
            self.slider_volume.setValue(last)
            self.btn_mute.setText("🔊")
            self.mpris.set_volume(last / 100.0)

    @pyqtSlot(float)
    def update_volume_ui(self, volume: float) -> None:
        """Sincroniza el slider de volumen cuando cambia el volumen en DBus/MPRIS."""
        val = int(max(0.0, min(1.0, volume)) * 100)
        self.slider_volume.blockSignals(True)
        self.slider_volume.setValue(val)
        self.slider_volume.blockSignals(False)
        if hasattr(self, 'btn_mute') and self.btn_mute:
            self.btn_mute.setText("🔇" if val == 0 else "🔊")
        if hasattr(self, 'expanded_page') and self.expanded_page:
            self.expanded_page.update_volume(volume)

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

        if hasattr(self, 'expanded_page') and self.expanded_page:
            self.expanded_page.update_metadata(metadata, getattr(self.mpris, 'current_index', 0))

        is_fav = self.config.is_favorite(title, artist)
        self._update_like_ui(is_fav)

        if art_url != self.current_art_url:
            self.current_art_url = art_url
            self.load_album_art(art_url)

    @pyqtSlot(str)
    def update_status(self, status: str):
        is_playing = (status == "Playing")
        if hasattr(self, 'equalizer') and self.equalizer:
            self.equalizer.set_playing(is_playing)
        self.ekg_bg.set_playing(is_playing)
        if hasattr(self, 'compact_ekg_bg') and self.compact_ekg_bg:
            self.compact_ekg_bg.set_playing(is_playing)
        if hasattr(self, 'expanded_page') and self.expanded_page:
            self.expanded_page.set_playing_status(is_playing)

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

        if hasattr(self, 'expanded_page') and self.expanded_page:
            self.expanded_page.update_position(pos_sec, total_sec)

    def _on_slider_pressed(self):
        self.is_user_seeking = True

    def _on_slider_released(self):
        self.is_user_seeking = False
        val = self.progress_bar.value()
        if self.duration_sec > 0:
            target_sec = int((val / 1000.0) * self.duration_sec)
            self.mpris.set_position(target_sec)

    def _on_expanded_seek(self, val: int) -> None:
        if self.duration_sec > 0:
            target_sec = int((val / 1000.0) * self.duration_sec)
            self.mpris.set_position(target_sec)

    @pyqtSlot(str)
    def update_loop_ui(self, status: str):
        if status in ("Track", "Playlist"):
            self.btn_loop.setStyleSheet("QPushButton { font-size: 14px; border: none; background: transparent; color: #ffffff; font-weight: bold; }")
        else:
            self.btn_loop.setStyleSheet("QPushButton { font-size: 14px; border: none; background: transparent; color: #ff1744; } QPushButton:hover { color: #ffffff; }")
        if hasattr(self, 'expanded_page') and self.expanded_page:
            self.expanded_page.update_loop_status(status)

    @pyqtSlot(bool)
    def update_shuffle_ui(self, enabled: bool):
        if hasattr(self, 'expanded_page') and self.expanded_page:
            self.expanded_page.update_shuffle_status(enabled)

    @pyqtSlot(bool, str)
    def on_player_available(self, available: bool, name: str):
        if available and name:
            self.badge_label.setText(f"🎧 {name.upper()}")
        else:
            brand_str = str(self.config.get("brand_name", "RED WORLD")).upper()
            self.badge_label.setText(f"🎧 {brand_str}")
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
        from ui.expanded_view import get_cached_pixmap
        inner_mode = self.config.get("inner_art_mode", "auto")
        custom_art = self.config.get("custom_inner_image", "")

        effective_art = art_url
        if inner_mode == "custom_always" and custom_art and os.path.exists(custom_art):
            effective_art = custom_art

        if not effective_art:
            self.set_art_placeholder()
            return

        pixmap = get_cached_pixmap(effective_art, 250, 250)
        if pixmap and not pixmap.isNull():
            self._apply_pixmap(pixmap)
        elif effective_art.startswith("http://") or effective_art.startswith("https://"):
            req = QNetworkRequest(QUrl(effective_art))
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

            # Extraer colores degradados automáticos multi-parada de la imagen/carátula activa
            extracted_stops = extract_dominant_gradient_colors(pixmap, max_colors=4)
            self.auto_gradient_colors = extracted_stops
            self.config.set("auto_gradient_colors", extracted_stops)

            if self.theme_mode == "gradient_auto":
                self.container.set_gradient_colors(extracted_stops, theme_mode="gradient_auto")

            if hasattr(self, 'ekg_bg') and self.ekg_bg:
                self.ekg_bg.set_album_art(pixmap)

            if hasattr(self, 'expanded_page') and self.expanded_page:
                self.expanded_page.update_metadata(self.mpris.current_metadata, getattr(self.mpris, 'current_index', 0))

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
        if hasattr(self, 'expanded_page') and self.expanded_page:
            self.expanded_page.update_like_status(is_fav)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta != 0:
            step = 0.05 if delta > 0 else -0.05
            curr_vol = self.slider_volume.value() / 100.0 if hasattr(self, 'slider_volume') else 1.0
            new_vol = max(0.0, min(1.0, curr_vol + step))
            self.mpris.set_volume(new_vol)
            event.accept()

    def _get_resize_edges(self, pos: QPoint) -> Qt.Edge:
        edges = Qt.Edge(0)
        w, h = self.width(), self.height()
        margin = self.RESIZE_MARGIN
        if pos.x() <= margin:
            edges |= Qt.Edge.LeftEdge
        elif pos.x() >= w - margin:
            edges |= Qt.Edge.RightEdge

        if pos.y() <= margin:
            edges |= Qt.Edge.TopEdge
        elif pos.y() >= h - margin:
            edges |= Qt.Edge.BottomEdge

        return edges

    def mousePressEvent(self, event):
        if self.view_mode == "expanded":
            super().mousePressEvent(event)
            return

        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            edges = self._get_resize_edges(pos)
            global_pos = event.globalPosition().toPoint()

            if edges.value != 0:
                if self.windowHandle() and self.windowHandle().startSystemResize(edges):
                    event.accept()
                    return
                # Redimensionamiento manual de respaldo
                self._is_manual_resizing = True
                self._active_edges = edges
                self._resize_start_mouse_pos = global_pos
                self._resize_start_geometry = self.geometry()
                event.accept()
                return
            else:
                if self.windowHandle() and self.windowHandle().startSystemMove():
                    event.accept()
                    return
                # Desplazamiento manual de respaldo
                self._is_manual_moving = True
                self.drag_position = global_pos - self.frameGeometry().topLeft()
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.view_mode == "expanded":
            super().mouseMoveEvent(event)
            return

        global_pos = event.globalPosition().toPoint()

        if self._is_manual_resizing and self._resize_start_geometry and self._resize_start_mouse_pos:
            delta = global_pos - self._resize_start_mouse_pos
            geom = QRect(self._resize_start_geometry)

            min_w = self.minimumWidth()
            min_h = self.minimumHeight()
            max_w = self.maximumWidth()
            max_h = self.maximumHeight()

            edges = self._active_edges

            if edges & Qt.Edge.LeftEdge:
                new_w = max(min_w, min(max_w, geom.width() - delta.x()))
                geom.setLeft(geom.right() - new_w)
            elif edges & Qt.Edge.RightEdge:
                new_w = max(min_w, min(max_w, geom.width() + delta.x()))
                geom.setWidth(new_w)

            if edges & Qt.Edge.TopEdge:
                new_h = max(min_h, min(max_h, geom.height() - delta.y()))
                geom.setTop(geom.bottom() - new_h)
            elif edges & Qt.Edge.BottomEdge:
                new_h = max(min_h, min(max_h, geom.height() + delta.y()))
                geom.setHeight(new_h)

            self.setGeometry(geom)
            event.accept()
            return

        elif self._is_manual_moving:
            self.move(global_pos - self.drag_position)
            event.accept()
            return

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

    def mouseReleaseEvent(self, event):
        if self.view_mode == "expanded":
            super().mouseReleaseEvent(event)
            return

        if event.button() == Qt.MouseButton.LeftButton:
            if self._is_manual_resizing:
                self._is_manual_resizing = False
                w, h = self.width(), self.height()
                if self.view_mode == "compact":
                    self.config.set("compact_width", w)
                    self.config.set("compact_height", h)
                elif self.view_mode == "expanded":
                    self.config.set("expanded_width", w)
                    self.config.set("expanded_height", h)
                else:
                    self.config.set("width", w)
                    self.config.set("height", h)
            self._is_manual_moving = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(event)

    def moveEvent(self, event):
        super().moveEvent(event)
        if not self.isMaximized() and not self.isFullScreen():
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

        folder_act = QAction("📁 Seleccionar Carpeta de Música (Ctrl+O)...", self)
        folder_act.triggered.connect(self._choose_music_folder)
        menu.addAction(folder_act)

        if hasattr(self.mpris, "playlist") and self.mpris.playlist:
            pl = self.mpris.playlist
            curr_idx = getattr(self.mpris, "current_index", -1)
            pl_menu = menu.addMenu(f"📋 Lista de Reproducción ({len(pl)} canciones)")
            for idx, track in enumerate(pl):
                t_title = track.get("title", "Canción sin título")
                t_artist = track.get("artist", "Artista desconocido")
                prefix = "▶ " if idx == curr_idx else "   "
                t_act = QAction(f"{prefix}{t_title} - {t_artist}", self)
                t_act.triggered.connect(lambda checked, i=idx: self.mpris.play_index(i))
                pl_menu.addAction(t_act)

        menu.addSeparator()

        size_menu = menu.addMenu("📐 Tamaños & Vistas de Ventana")
        
        mode_normal_act = QAction("📱 Modo Pequeño (350x410)", self)
        mode_normal_act.setCheckable(True)
        mode_normal_act.setChecked(self.view_mode == "normal")
        mode_normal_act.triggered.connect(self.toggle_normal_mode)
        size_menu.addAction(mode_normal_act)

        mode_compact_act = QAction("⤢ Modo Compacto (Barra Flotante)", self)
        mode_compact_act.setCheckable(True)
        mode_compact_act.setChecked(self.view_mode == "compact")
        mode_compact_act.triggered.connect(self.toggle_compact_mode)
        size_menu.addAction(mode_compact_act)

        mode_expanded_act = QAction("🗖 Modo Grande (Biblioteca Completa)", self)
        mode_expanded_act.setCheckable(True)
        mode_expanded_act.setChecked(self.view_mode == "expanded")
        mode_expanded_act.triggered.connect(self.toggle_expanded_mode)
        size_menu.addAction(mode_expanded_act)

        pers_act = QAction("⚙️ Personalización Completa...", self)
        pers_act.triggered.connect(self.open_personalization_dialog)
        menu.addAction(pers_act)

        grad_dialog_act = QAction("🎨 Tema & Fondo Degradado (Auto/Manual)...", self)
        grad_dialog_act.triggered.connect(self.open_personalization_dialog)
        menu.addAction(grad_dialog_act)

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

        align_bl_act = QAction("📍 Mover a esquina inferior izquierda", self)
        align_bl_act.triggered.connect(self.align_bottom_left)
        menu.addAction(align_bl_act)

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

    def align_bottom_left(self) -> None:
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            x = geom.x() + 40
            y = geom.y() + geom.height() - self.height() - 40
            self.move(x, y)
            self.config.set("pos_x", x)
            self.config.set("pos_y", y)

    def _choose_music_folder(self) -> None:
        current = self.config.get("music_folder", "")
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta de Música Local", current)
        if folder and hasattr(self.mpris, "load_music_folder"):
            self.mpris.load_music_folder(folder, auto_play=True)

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
        self._apply_button_style()

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

        curr_bg = self.config.get("background_image")
        if curr_bg:
            self.config.set_theme_color_for_image(curr_bg, hex_color)

        self.container.accent_color = hex_color
        self.ekg_bg.accent_color = hex_color
        if hasattr(self, 'compact_ekg_bg') and self.compact_ekg_bg:
            self.compact_ekg_bg.accent_color = hex_color
        if hasattr(self, 'compact_art_screen') and self.compact_art_screen:
            self.compact_art_screen.setStyleSheet(f"QLabel#ArtScreen {{ background-color: #050508; border: 2px solid {hex_color}; border-radius: 12px; }}")

        # 1. Badge label y Top Bar
        if hasattr(self, 'badge_label') and self.badge_label:
            self.badge_label.setStyleSheet(
                f"color: #ffffff; background-color: rgba(0, 0, 0, 0.45); padding: 3px 10px; border-radius: 10px; border: 1px solid {hex_color}; font-weight: bold; font-size: 11px; font-family: 'Sans Serif', sans-serif;"
            )
        if hasattr(self, 'btn_compact_toggle') and self.btn_compact_toggle:
            self.btn_compact_toggle.setStyleSheet(f"QPushButton {{ font-size: 11px; font-weight: bold; border-radius: 10px; border: none; background: transparent; color: {hex_color}; }} QPushButton:hover {{ color: #ffffff; }}")
        if hasattr(self, 'btn_close') and self.btn_close:
            self.btn_close.setStyleSheet(f"QPushButton {{ font-size: 14px; font-weight: bold; border-radius: 10px; padding: 0px; border: none; background: transparent; color: {hex_color}; }} QPushButton:hover {{ color: #ffffff; background-color: {hex_color}; }}")

        self._apply_button_style()

        meta = self.mpris.current_metadata
        title = meta.get("title", "")
        artist = meta.get("artist", "")
        is_fav = self.config.is_favorite(title, artist)
        self._update_like_ui(is_fav)

        loop_st = getattr(self.mpris, 'loop_status', 'None')
        self.update_loop_ui(loop_st)

        self.config.save()
        self.container.update()
        self.ekg_bg.update()
        if hasattr(self, 'compact_ekg_bg') and self.compact_ekg_bg:
            self.compact_ekg_bg.update()

    def _pick_custom_color(self) -> None:
        color = QColorDialog.getColor(QColor(self.accent_color), self, "Seleccionar Color de Tema")
        if color.isValid():
            self._set_theme_color(color.name(), save_to_img=True)




