import os
import random
import urllib.parse
from typing import Optional, Dict, Any, List
from PyQt6.QtCore import Qt, QSize, QPoint, QRect, pyqtSlot, QUrl, QTimer, QRectF, QFileSystemWatcher, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QAction, QShortcut, QKeySequence, QIcon, QPainter, QColor, QPainterPath, QPen, QLinearGradient
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QApplication, QLayout, QSlider, QStackedWidget, QMenu,
    QSystemTrayIcon, QFileDialog, QColorDialog, QFrame
)
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from ui.styles import (
    MAIN_STYLE, get_main_style, _build_qlineargradient, build_mode_pill_style,
    WINDOW_RADIUS, CARD_RADIUS, BUTTON_RADIUS, ARTWORK_RADIUS, CONTROL_RADIUS,
    NORMAL_WIDTH, NORMAL_HEIGHT, COMPACT_WIDTH, COMPACT_HEIGHT, COMPACT_ART_SIZE,
    EXPANDED_MIN_WIDTH, EXPANDED_MIN_HEIGHT
)
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
        self.art_mode: str = art_mode

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