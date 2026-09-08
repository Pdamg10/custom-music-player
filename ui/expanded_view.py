import os
import time
import random
import urllib.parse
from typing import Optional, Dict, Any, List
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPoint, QPointF, QRect, QRectF, QTimer, QEvent, QObject, QModelIndex, QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QVideoSink
from PyQt6.QtGui import (
    QFont, QFontMetrics, QPixmap, QColor, QPainter, QPainterPath, QPen, QBrush,
    QLinearGradient, QRadialGradient, QConicalGradient, QShowEvent, QMovie
)
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QLineEdit, QScrollArea, QFrame, QStackedWidget, QSlider,
    QGridLayout, QSizePolicy, QListWidget, QListWidgetItem,
    QMenu, QMessageBox, QApplication, QDialog,
    QStyledItemDelegate, QStyleOptionViewItem, QStyle, QComboBox
)

from ui.marquee_label import MarqueeLabel
from ui.seek_slider import SeekSlider
from ui.y2k_volume_slider import Y2KVolumeSlider
from ui.color_extractor import get_contrasting_text_color, extract_lyrics_theme_colors
from ui.styles import _build_qlineargradient, build_button_style
from ui.music_home_view import MusicHomeView, PlaylistsPageView, CreatePlaylistDialog
from ui.lyrics_view_widget import LyricsDisplayWidget
from ui.image_cache import (
    get_cached_pixmap,
    get_cached_rounded_pixmap,
    _PLACEHOLDER_CACHE,
    resolve_library_art,
    resolve_now_playing_art,
    clean_art_path,
    is_gif_file,
    is_video_file,
)

from library_manager import (
    SORT_OPTIONS,
    _get_track_download_timestamp,
    sort_tracks,
)

def format_time_str(seconds: int, force_hours: bool = False) -> str:
    """Formatea una duración en segundos a 'M:SS' o 'H:MM:SS' para audios largos (> 1 hora)."""
    if seconds < 0:
        seconds = 0
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0 or force_hours:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

def format_rem_time_str(rem_sec: int, force_hours: bool = False) -> str:
    """Formatea el tiempo restante antecedido por signo menos."""
    return f"-{format_time_str(rem_sec, force_hours)}"

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


def _interpolate_color_list(colors: List[str], pos: float) -> QColor:
    """Interpola suavemente entre una lista de colores hexadecimales según una posición normalizada (0.0 a 1.0)."""
    if not colors:
        return QColor("#ff1744")
    if len(colors) == 1:
        return QColor(colors[0])
    pos = max(0.0, min(1.0, pos))
    scaled = pos * (len(colors) - 1)
    idx = int(scaled)
    frac = scaled - idx
    if idx >= len(colors) - 1:
        c = QColor(colors[-1])
        return c if c.isValid() else QColor("#ff1744")
    c1 = QColor(colors[idx])
    c2 = QColor(colors[idx + 1])
    if not c1.isValid():
        c1 = QColor("#ff1744")
    if not c2.isValid():
        c2 = QColor("#00e5ff")
    r = int(c1.red() + (c2.red() - c1.red()) * frac)
    g = int(c1.green() + (c2.green() - c1.green()) * frac)
    b = int(c1.blue() + (c2.blue() - c1.blue()) * frac)
    return QColor(r, g, b)


class ExpandedArtworkDisplayWidget(QWidget):
    """
    Widget visualizador de reproducción para Modo Expandido.
    Soporta múltiples modos visuales:
      - 'radial_waves': Visualizador Radial de Ondas Espectrales (estilo Trap Nation / YouTube) con ondas de choque y pulso rítmico.
      - 'vinyl': Tocadiscos de Vinilo Clásico Hi-Fi con brazo dinámico y plato giratorio.
      - 'card_glow': Carátula Flotante con Halo Neón y ecualizador horizontal inferior.
    """
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.album_art: Optional[QPixmap] = None
        self.accent_color: str = "#ff1744"
        self.gradient_colors: List[str] = ["#ff1744", "#00e5ff", "#e040fb"]
        self.cover_shape: str = "circle"
        self.visualizer_style: str = "radial_waves"
        self.cover_fit: str = "full_bleed"
        self.scrim_opacity: float = 0.35
        self.show_lyrics: bool = True
        self.is_light_bg: bool = False
        self.is_playing: bool = False
        self.always_play: bool = False

        self.setMinimumSize(260, 260)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Estados de animación de Vinilo
        self._rotation_angle: float = 0.0
        self._arm_angle: float = -26.0  # -26° = reposo/pausado, 0° = sobre el vinilo
        self._target_arm_angle: float = -26.0

        # Estados de animación Radial / Espectral
        self.radial_bar_count: int = 72
        self.radial_heights: List[float] = [0.08] * self.radial_bar_count
        self.target_radial_heights: List[float] = [0.08] * self.radial_bar_count
        self._radial_phase: float = 0.0
        self._bass_pulse: float = 0.0
        self._shockwaves: List[dict] = []
        self._shockwave_cooldown: int = 0

        # Estados de animación Horizontal (Card Glow)
        self.h_bar_count: int = 36
        self.h_bar_heights: List[float] = [0.06] * self.h_bar_count

        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(30)
        self.anim_timer.timeout.connect(self._update_animation)
        self._gif_movie: Optional[QMovie] = None
        self._current_art_path: str = ""

    def sizeHint(self) -> QSize:
        return QSize(360, 360)

    def set_visualizer_style(self, style: str) -> None:
        valid_styles = ("radial_waves", "vinyl", "card_glow")
        self.visualizer_style = style if style in valid_styles else "radial_waves"
        self.update()

    def set_cover_fit(self, fit: str) -> None:
        valid_fits = ("full_bleed", "fit_glow", "radial_waves", "vinyl", "card_glow")
        self.cover_fit = fit if fit in valid_fits else "full_bleed"
        self.update()

    def set_scrim_opacity(self, opacity: float) -> None:
        try:
            self.scrim_opacity = max(0.0, min(1.0, float(opacity)))
        except Exception:
            self.scrim_opacity = 0.35
        self.update()

    def set_show_lyrics(self, show: bool) -> None:
        self.show_lyrics = bool(show)
        self.update()

    def set_is_light_bg(self, is_light: bool) -> None:
        is_light = bool(is_light)
        if getattr(self, 'is_light_bg', False) != is_light:
            self.is_light_bg = is_light
            self._cached_overlay_key = None
            self._cached_overlay_pixmap = None
            self.update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._gif_movie:
            self._gif_movie.setScaledSize(self.size())

    def set_gradient_colors(self, colors: List[str]) -> None:
        if colors:
            self.gradient_colors = list(colors)
            self.update()

    def set_playing(self, is_playing: bool) -> None:
        self.is_playing = bool(is_playing)
        self._target_arm_angle = 0.0 if self.is_playing else -26.0
        always_play = getattr(self, 'always_play', False)
        if self._gif_movie:
            if self.is_playing or always_play:
                self._gif_movie.start()
            else:
                self._gif_movie.setPaused(True)
        if hasattr(self, '_video_player') and self._video_player:
            if self.is_playing or always_play:
                if self._video_player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
                    self._video_player.play()
            else:
                self._video_player.pause()
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

    def stop_video(self) -> None:
        if self._gif_movie:
            try:
                self._gif_movie.stop()
                self._gif_movie.deleteLater()
            except Exception:
                pass
            self._gif_movie = None
        if hasattr(self, '_video_player') and self._video_player:
            try:
                self._video_player.stop()
                self._video_player.deleteLater()
            except Exception:
                pass
            self._video_player = None
            self._video_sink = None

    def set_album_art(self, pixmap: Optional[QPixmap], art_path: str = "") -> None:
        self._current_art_path = art_path
        self.stop_video()

        w = max(10, self.width() if self.width() > 10 else 1200)
        h = max(10, self.height() if self.height() > 10 else 760)

        always_play = getattr(self, 'always_play', False)
        if art_path and is_gif_file(art_path) and os.path.exists(art_path):
            self._gif_movie = QMovie(art_path)
            self._gif_movie.setScaledSize(QSize(w, h))
            self._gif_movie.setSpeed(100)
            self._gif_movie.frameChanged.connect(self._on_gif_frame_changed)
            if self.is_playing or always_play:
                self._gif_movie.start()
            else:
                self._gif_movie.jumpToFrame(0)
                pm = self._gif_movie.currentPixmap()
                if pm and not pm.isNull():
                    self.album_art = pm
                    self.update()
                    return
        elif art_path and is_video_file(art_path) and os.path.exists(art_path):
            if pixmap and not pixmap.isNull():
                self.album_art = pixmap
            else:
                from ui.image_cache import extract_video_thumbnail
                tb = extract_video_thumbnail(art_path)
                if tb and os.path.exists(tb):
                    pm = QPixmap(tb)
                    if not pm.isNull():
                        self.album_art = pm
            self.update()

            try:
                from ui.image_cache import get_video_playback_source

                def _on_expanded_proxy_ready(proxy_p: str):
                    from PyQt6.QtCore import QTimer
                    def _switch():
                        if hasattr(self, '_video_player') and self._video_player:
                            curr_pos = self._video_player.position()
                            self._video_player.setSource(QUrl.fromLocalFile(proxy_p))
                            self._video_player.setPosition(curr_pos)
                            always_p = getattr(self, 'always_play', False)
                            if self.is_playing or always_p:
                                self._video_player.play()
                    QTimer.singleShot(0, _switch)

                play_src = get_video_playback_source(art_path, on_ready_callback=_on_expanded_proxy_ready)
                self._video_player = QMediaPlayer(self)
                self._video_sink = QVideoSink(self)
                self._video_sink.videoFrameChanged.connect(self._on_video_frame_changed)
                self._video_player.setVideoOutput(self._video_sink)
                self._video_player.setLoops(QMediaPlayer.Loops.Infinite)
                self._video_player.setSource(QUrl.fromLocalFile(play_src))
                self._last_video_frame_time = 0.0
                if self.is_playing or always_play:
                    self._video_player.play()
            except Exception as e:
                print(f"[ExpandedArtworkDisplayWidget] Error cargando video: {e}")
        elif art_path and os.path.exists(art_path) and not is_gif_file(art_path) and not is_video_file(art_path):
            pm = QPixmap(art_path)
            if not pm.isNull():
                self.album_art = pm
            else:
                self.album_art = pixmap if (pixmap and not pixmap.isNull()) else None
        else:
            self.album_art = pixmap if (pixmap and not pixmap.isNull()) else None

        self.update()

    def _on_gif_frame_changed(self, frame_number: int) -> None:
        if self._gif_movie:
            pm = self._gif_movie.currentPixmap()
            if pm and not pm.isNull():
                self.album_art = pm
                self.update()

    def _on_video_frame_changed(self, frame: Any) -> None:
        if not self.isVisible():
            return
        if not hasattr(self, '_video_player') or self._video_player is None:
            return
        if frame is None or not hasattr(frame, 'isValid') or not frame.isValid():
            return
        import time
        now = time.time()
        min_interval = 0.040  # 25 FPS para fluidez cinematográfica con 0% sobrecarga en CPU
        if now - getattr(self, '_last_video_frame_time', 0.0) < min_interval:
            return
        if getattr(self, '_processing_video_frame', False):
            return
        self._last_video_frame_time = now
        self._processing_video_frame = True
        try:
            img = frame.toImage()
            if img is not None and not img.isNull():
                target_max = 960
                if img.width() > target_max or img.height() > target_max:
                    img = img.scaled(target_max, target_max, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)
                self.album_art = QPixmap.fromImage(img)
                self.update()
        except Exception:
            pass
        finally:
            self._processing_video_frame = False

    def set_accent_color(self, hex_color: str, gradient_colors: Optional[List[str]] = None) -> None:
        if hex_color:
            self.accent_color = hex_color
        if gradient_colors:
            self.gradient_colors = list(gradient_colors)
        self.update()

    def set_cover_shape(self, shape: str) -> None:
        self.cover_shape = shape if shape in ("circle", "rounded", "heart") else "rounded"
        self.update()

    def _update_animation(self) -> None:
        if not self.isVisible():
            return

        import math, random

        # 1. Animación del brazo de vinilo
        arm_diff = self._target_arm_angle - self._arm_angle
        if abs(arm_diff) > 0.4:
            self._arm_angle += arm_diff * 0.16
        else:
            self._arm_angle = self._target_arm_angle

        # 2. Rotación continua
        if self.is_playing:
            rot_speed = 0.6 if self.visualizer_style == "vinyl" else 0.35
            self._rotation_angle = (self._rotation_angle + rot_speed) % 360.0

        # 3. Simulación Acústica Espectral (Radial Waves y Card Glow)
        if self.is_playing:
            self._radial_phase += 0.22
            bass_val = 0.0
            for i in range(self.radial_bar_count):
                norm_a = i / float(self.radial_bar_count)
                sym_x = abs(math.sin(norm_a * math.pi))
                w1 = math.sin(self._radial_phase * 1.8 + norm_a * 12.0) * 0.42 + 0.50
                w2 = math.cos(self._radial_phase * 2.8 - norm_a * 18.0) * 0.28 + 0.35
                noise = random.uniform(-0.10, 0.25)
                target = max(0.08, min(0.98, (w1 * 0.55 + w2 * 0.45 + noise) * (0.55 + 0.45 * sym_x)))
                factor = 0.40 if target > self.radial_heights[i] else 0.20
                self.radial_heights[i] += (target - self.radial_heights[i]) * factor
                if i in (0, 1, 2, 35, 36, 70, 71):
                    bass_val = max(bass_val, target)

            # Pulso rítmico central
            self._bass_pulse = max(self._bass_pulse * 0.88, bass_val * 0.30)

            # Ondas de choque expansivas (Shockwaves)
            self._shockwave_cooldown -= 1
            if self._bass_pulse > 0.18 and self._shockwave_cooldown <= 0:
                self._shockwaves.append({"radius_factor": 1.0, "opacity": 0.80})
                self._shockwave_cooldown = 14

            # Simulación para barras horizontales (Card Glow)
            for j in range(self.h_bar_count):
                norm_j = j / max(1, self.h_bar_count - 1)
                hw1 = math.sin(self._radial_phase * 1.6 + norm_j * 5.2) * 0.40 + 0.50
                hw2 = math.cos(self._radial_phase * 2.9 - norm_j * 8.5) * 0.28 + 0.35
                htarget = max(0.08, min(0.98, (hw1 * 0.55 + hw2 * 0.45 + random.uniform(-0.10, 0.22)) * (math.sin(norm_j * math.pi) * 0.45 + 0.55)))
                hfactor = 0.35 if htarget > self.h_bar_heights[j] else 0.18
                self.h_bar_heights[j] += (htarget - self.h_bar_heights[j]) * hfactor

        else:
            # Decaimiento suave a línea base en pausa
            all_rest = True
            for i in range(self.radial_bar_count):
                self.radial_heights[i] += (0.05 - self.radial_heights[i]) * 0.14
                if self.radial_heights[i] > 0.06:
                    all_rest = False
            for j in range(self.h_bar_count):
                self.h_bar_heights[j] += (0.05 - self.h_bar_heights[j]) * 0.14
                if self.h_bar_heights[j] > 0.06:
                    all_rest = False
            self._bass_pulse *= 0.80
            if all_rest and abs(arm_diff) <= 0.4 and not self._shockwaves:
                if self.anim_timer.isActive():
                    self.anim_timer.stop()

        # Actualizar ondas de choque
        new_shockwaves = []
        for sw in self._shockwaves:
            sw["radius_factor"] += 0.032
            sw["opacity"] -= 0.040
            if sw["opacity"] > 0.02 and sw["radius_factor"] < 1.70:
                new_shockwaves.append(sw)
        self._shockwaves = new_shockwaves

        # Si el video está en reproducción activa, los fotogramas del video
        # ya invocan update() a 25 FPS. Evitamos duplicar llamadas a update() aquí
        # para no saturar el renderizador de la ventana a 60 FPS innecesariamente.
        is_video_running = bool(
            hasattr(self, '_video_player') and
            self._video_player and
            self._video_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        )
        if not is_video_running:
            self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w = float(self.width())
        h = float(self.height())
        if w <= 0 or h <= 0:
            p.end()
            return

        # 1. Recorte con esquinas redondeadas orgánicas (elimina la apariencia cuadrada rígida)
        corner_r = 24.0
        clip_path = QPainterPath()
        clip_path.addRoundedRect(QRectF(0, 0, w, h), corner_r, corner_r)
        p.save()
        p.setClipPath(clip_path)

        # 2. Renderizado del contenido visual
        fit_mode = getattr(self, 'cover_fit', 'full_bleed')
        if fit_mode == "fit_glow":
            self._paint_fit_glow(p, w, h)
        elif fit_mode == "radial_waves" or (fit_mode == "visualizer" and self.visualizer_style == "radial_waves"):
            self._paint_radial_waves(p, w, h)
        elif fit_mode == "vinyl" or (fit_mode == "visualizer" and self.visualizer_style == "vinyl"):
            self._paint_vinyl_turntable(p, w, h)
        elif fit_mode == "card_glow" or (fit_mode == "visualizer" and self.visualizer_style == "card_glow"):
            self._paint_card_glow(p, w, h)
        else:
            self._paint_full_bleed(p, w, h)

        # 3. Dibujado acelerado por hardware de bordes difuminados y velo de letras en 1 solo pase
        overlay_pm = self._get_cached_scrim_overlay(int(w), int(h))
        if overlay_pm and not overlay_pm.isNull():
            p.drawPixmap(0, 0, overlay_pm)

        p.restore()

        # 5. Contorno sutil redondeado de cristal para rematar el borde suavemente
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(255, 255, 255, 22), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(0.75, 0.75, w - 1.5, h - 1.5), corner_r, corner_r)
        p.restore()

        p.end()

    def _get_cached_scrim_overlay(self, w: int, h: int) -> Optional[QPixmap]:
        if w <= 0 or h <= 0:
            return None
        opacity_val = float(getattr(self, 'scrim_opacity', 0.35))
        show_lyrics = bool(getattr(self, 'show_lyrics', True))
        has_art = bool(self.album_art and not self.album_art.isNull())
        is_light = bool(getattr(self, 'is_light_bg', False))
        cache_key = (w, h, int(opacity_val * 100), show_lyrics, has_art, is_light)

        if getattr(self, '_cached_overlay_key', None) == cache_key and getattr(self, '_cached_overlay_pixmap', None) is not None:
            return self._cached_overlay_pixmap

        pm = QPixmap(w, h)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Borde difuminado orgánico (feathered edges adaptativo)
        bg_c = QColor(240, 242, 248) if is_light else QColor(8, 11, 20)
        fade_top = min(75.0, h * 0.16)
        fade_bottom = min(110.0, h * 0.24)
        fade_side = min(80.0, w * 0.13)

        top_grad = QLinearGradient(0, 0, 0, fade_top)
        top_grad.setColorAt(0.0, QColor(bg_c.red(), bg_c.green(), bg_c.blue(), 235))
        top_grad.setColorAt(0.50, QColor(bg_c.red(), bg_c.green(), bg_c.blue(), 110))
        top_grad.setColorAt(1.0, QColor(bg_c.red(), bg_c.green(), bg_c.blue(), 0))
        p.fillRect(QRectF(0, 0, w, fade_top), QBrush(top_grad))

        bottom_grad = QLinearGradient(0, h, 0, h - fade_bottom)
        bottom_grad.setColorAt(0.0, QColor(bg_c.red(), bg_c.green(), bg_c.blue(), 245))
        bottom_grad.setColorAt(0.45, QColor(bg_c.red(), bg_c.green(), bg_c.blue(), 130))
        bottom_grad.setColorAt(1.0, QColor(bg_c.red(), bg_c.green(), bg_c.blue(), 0))
        p.fillRect(QRectF(0, h - fade_bottom, w, fade_bottom), QBrush(bottom_grad))

        left_grad = QLinearGradient(0, 0, fade_side, 0)
        left_grad.setColorAt(0.0, QColor(bg_c.red(), bg_c.green(), bg_c.blue(), 220))
        left_grad.setColorAt(0.50, QColor(bg_c.red(), bg_c.green(), bg_c.blue(), 90))
        left_grad.setColorAt(1.0, QColor(bg_c.red(), bg_c.green(), bg_c.blue(), 0))
        p.fillRect(QRectF(0, 0, fade_side, h), QBrush(left_grad))

        right_grad = QLinearGradient(w, 0, w - fade_side, 0)
        right_grad.setColorAt(0.0, QColor(bg_c.red(), bg_c.green(), bg_c.blue(), 220))
        right_grad.setColorAt(0.50, QColor(bg_c.red(), bg_c.green(), bg_c.blue(), 90))
        right_grad.setColorAt(1.0, QColor(bg_c.red(), bg_c.green(), bg_c.blue(), 0))
        p.fillRect(QRectF(w - fade_side, 0, fade_side, h), QBrush(right_grad))

        corner_r = max(fade_side, fade_top) * 1.3
        quadrants = [
            (0.0, 0.0, 0.0, 0.0),
            (w, 0.0, w - corner_r, 0.0),
            (0.0, h, 0.0, h - corner_r),
            (w, h, w - corner_r, h - corner_r)
        ]
        for cx, cy, rx, ry in quadrants:
            c_grad = QRadialGradient(cx, cy, corner_r)
            c_grad.setColorAt(0.0, QColor(bg_c.red(), bg_c.green(), bg_c.blue(), 230))
            c_grad.setColorAt(0.50, QColor(bg_c.red(), bg_c.green(), bg_c.blue(), 75))
            c_grad.setColorAt(1.0, QColor(bg_c.red(), bg_c.green(), bg_c.blue(), 0))
            p.fillRect(QRectF(rx, ry, corner_r, corner_r), QBrush(c_grad))

        # 2. Velo de contraste para letras (adaptativo a carátulas claras vs oscuras)
        if has_art and show_lyrics:
            op_clamped = max(0.12, min(0.55, opacity_val))
            scrim_grad = QLinearGradient(0, 0, 0, h)
            if is_light:
                # Velo luminoso traslúcido para carátulas claras que mantiene su brillo estético
                scrim_grad.setColorAt(0.0, QColor(255, 255, 255, int(op_clamped * 130)))
                scrim_grad.setColorAt(0.35, QColor(255, 255, 255, int(op_clamped * 90)))
                scrim_grad.setColorAt(0.75, QColor(255, 255, 255, int(op_clamped * 120)))
                scrim_grad.setColorAt(1.0, QColor(255, 255, 255, int(op_clamped * 160)))
            else:
                # Velo oscuro para carátulas oscuras
                scrim_grad.setColorAt(0.0, QColor(8, 10, 18, int(op_clamped * 160)))
                scrim_grad.setColorAt(0.35, QColor(8, 10, 18, int(op_clamped * 120)))
                scrim_grad.setColorAt(0.75, QColor(8, 10, 18, int(op_clamped * 150)))
                scrim_grad.setColorAt(1.0, QColor(8, 10, 18, int(op_clamped * 210)))
            p.fillRect(QRectF(0, 0, w, h), QBrush(scrim_grad))

        p.end()

        self._cached_overlay_key = cache_key
        self._cached_overlay_pixmap = pm
        return pm

    def _paint_feathered_edges(self, p: QPainter, w: float, h: float) -> None:
        """Aplica un difuminado suave en los 4 bordes y esquinas para fundir la carátula orgánicamente."""
        p.save()
        bg_c = QColor(8, 11, 20)

        fade_top = min(75.0, h * 0.16)
        fade_bottom = min(110.0, h * 0.24)
        fade_side = min(80.0, w * 0.13)

        # Borde superior (fade out suave hacia arriba)
        top_grad = QLinearGradient(0, 0, 0, fade_top)
        top_grad.setColorAt(0.0, QColor(bg_c.red(), bg_c.green(), bg_c.blue(), 235))
        top_grad.setColorAt(0.50, QColor(bg_c.red(), bg_c.green(), bg_c.blue(), 110))
        top_grad.setColorAt(1.0, QColor(bg_c.red(), bg_c.green(), bg_c.blue(), 0))
        p.fillRect(QRectF(0, 0, w, fade_top), QBrush(top_grad))

        # Borde inferior (fade out hacia abajo enmarcando controles con máxima legibilidad)
        bottom_grad = QLinearGradient(0, h, 0, h - fade_bottom)
        bottom_grad.setColorAt(0.0, QColor(bg_c.red(), bg_c.green(), bg_c.blue(), 245))
        bottom_grad.setColorAt(0.45, QColor(bg_c.red(), bg_c.green(), bg_c.blue(), 130))
        bottom_grad.setColorAt(1.0, QColor(bg_c.red(), bg_c.green(), bg_c.blue(), 0))
        p.fillRect(QRectF(0, h - fade_bottom, w, fade_bottom), QBrush(bottom_grad))

        # Borde lateral izquierdo
        left_grad = QLinearGradient(0, 0, fade_side, 0)
        left_grad.setColorAt(0.0, QColor(bg_c.red(), bg_c.green(), bg_c.blue(), 220))
        left_grad.setColorAt(0.50, QColor(bg_c.red(), bg_c.green(), bg_c.blue(), 90))
        left_grad.setColorAt(1.0, QColor(bg_c.red(), bg_c.green(), bg_c.blue(), 0))
        p.fillRect(QRectF(0, 0, fade_side, h), QBrush(left_grad))

        # Borde lateral derecho
        right_grad = QLinearGradient(w, 0, w - fade_side, 0)
        right_grad.setColorAt(0.0, QColor(bg_c.red(), bg_c.green(), bg_c.blue(), 220))
        right_grad.setColorAt(0.50, QColor(bg_c.red(), bg_c.green(), bg_c.blue(), 90))
        right_grad.setColorAt(1.0, QColor(bg_c.red(), bg_c.green(), bg_c.blue(), 0))
        p.fillRect(QRectF(w - fade_side, 0, fade_side, h), QBrush(right_grad))

        # Viñeta suave en las 4 esquinas
        corner_r = max(fade_side, fade_top) * 1.3
        quadrants = [
            (0.0, 0.0, 0.0, 0.0),
            (w, 0.0, w - corner_r, 0.0),
            (0.0, h, 0.0, h - corner_r),
            (w, h, w - corner_r, h - corner_r)
        ]
        for cx, cy, rx, ry in quadrants:
            c_grad = QRadialGradient(cx, cy, corner_r)
            c_grad.setColorAt(0.0, QColor(bg_c.red(), bg_c.green(), bg_c.blue(), 230))
            c_grad.setColorAt(0.50, QColor(bg_c.red(), bg_c.green(), bg_c.blue(), 75))
            c_grad.setColorAt(1.0, QColor(bg_c.red(), bg_c.green(), bg_c.blue(), 0))
            p.fillRect(QRectF(rx, ry, corner_r, corner_r), QBrush(c_grad))

        p.restore()

    def _paint_lyrics_scrim(self, p: QPainter, w: float, h: float) -> None:
        """Aplica un velo suave para legibilidad de letras sin ocultar la carátula o video."""
        if not self.album_art or self.album_art.isNull():
            return

        if not getattr(self, 'show_lyrics', True):
            return

        opacity_val = float(getattr(self, 'scrim_opacity', 0.35))
        opacity_val = max(0.12, min(0.55, opacity_val))

        p.save()
        scrim_grad = QLinearGradient(0, 0, 0, h)
        scrim_grad.setColorAt(0.0, QColor(8, 10, 18, int(opacity_val * 160)))
        scrim_grad.setColorAt(0.35, QColor(8, 10, 18, int(opacity_val * 120)))
        scrim_grad.setColorAt(0.75, QColor(8, 10, 18, int(opacity_val * 150)))
        scrim_grad.setColorAt(1.0, QColor(8, 10, 18, int(opacity_val * 210)))
        p.fillRect(QRectF(0, 0, w, h), QBrush(scrim_grad))
        p.restore()

    def _paint_full_bleed(self, p: QPainter, w: float, h: float) -> None:
        """Renderiza la carátula o video/GIF llenando el 100% del área con aceleración de hardware."""
        if self.album_art and not self.album_art.isNull():
            pulse = 1.0 + (self._bass_pulse * 0.025 if self.is_playing else 0.0)
            art_w = float(self.album_art.width())
            art_h = float(self.album_art.height())
            if art_w > 0 and art_h > 0:
                scale = max(w / art_w, h / art_h) * pulse
                draw_w = art_w * scale
                draw_h = art_h * scale
                sx = (w - draw_w) / 2.0
                sy = (h - draw_h) / 2.0
                p.drawPixmap(QRectF(sx, sy, draw_w, draw_h), self.album_art, QRectF(0.0, 0.0, art_w, art_h))
        else:
            # Fondo ambiente dinámico Hi-Fi cuando no hay carátula activa
            qc = QColor(self.accent_color.split(';')[0].strip() if self.accent_color else "#ff1744")
            if not qc.isValid():
                qc = QColor("#ff1744")
            r, g, b = qc.red(), qc.green(), qc.blue()

            bg_grad = QLinearGradient(0, 0, w, h)
            if getattr(self, 'gradient_colors', None) and len(self.gradient_colors) >= 2:
                c1 = QColor(self.gradient_colors[0])
                c2 = QColor(self.gradient_colors[-1])
                bg_grad.setColorAt(0.0, QColor(c1.red(), c1.green(), c1.blue(), 150))
                bg_grad.setColorAt(0.48, QColor(14, 18, 30))
                bg_grad.setColorAt(1.0, QColor(c2.red(), c2.green(), c2.blue(), 120))
            else:
                bg_grad.setColorAt(0.0, QColor(r, g, b, 140))
                bg_grad.setColorAt(0.50, QColor(12, 16, 28))
                bg_grad.setColorAt(1.0, QColor(6, 8, 16))
            p.fillRect(QRectF(0, 0, w, h), bg_grad)

            # Brillo radial atmosférico central
            ambient_rad = QRadialGradient(w / 2.0, h * 0.42, max(w, h) * 0.42)
            ambient_rad.setColorAt(0.0, QColor(r, g, b, 65))
            ambient_rad.setColorAt(0.70, QColor(r, g, b, 15))
            ambient_rad.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.fillRect(QRectF(0, 0, w, h), QBrush(ambient_rad))

            # Anillo concéntrico sutil de vinilo / Hi-Fi
            cx, cy = w / 2.0, h * 0.40
            center_r = min(w, h) * 0.22
            p.save()
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setPen(QPen(QColor(255, 255, 255, 25), 1.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), center_r, center_r)
            p.drawEllipse(QPointF(cx, cy), center_r * 0.65, center_r * 0.65)
            p.setPen(QPen(QColor(r, g, b, 90), 2.0))
            p.drawEllipse(QPointF(cx, cy), center_r * 0.30, center_r * 0.30)
            p.setPen(QPen(QColor(255, 255, 255, 140)))
            p.setFont(QFont("Sans Serif", int(max(18, min(center_r * 0.32, 42))), QFont.Weight.Bold))
            symbol = "▶" if self.is_playing else "🎧"
            p.drawText(QRectF(cx - center_r, cy - center_r, center_r * 2, center_r * 2), Qt.AlignmentFlag.AlignCenter, symbol)
            p.restore()

    def _paint_fit_glow(self, p: QPainter, w: float, h: float) -> None:
        """Renderiza la carátula proporcional en el centro con fondo difuminado expansivo."""
        if self.album_art and not self.album_art.isNull():
            art_w = float(self.album_art.width())
            art_h = float(self.album_art.height())
            if art_w <= 0 or art_h <= 0:
                return

            # Fondo ambiental expandido acelerado
            scale_bg = max(w / art_w, h / art_h)
            dw_bg = art_w * scale_bg
            dh_bg = art_h * scale_bg
            sx_bg = (w - dw_bg) / 2.0
            sy_bg = (h - dh_bg) / 2.0

            p.save()
            p.setOpacity(0.35)
            p.drawPixmap(QRectF(sx_bg, sy_bg, dw_bg, dh_bg), self.album_art, QRectF(0.0, 0.0, art_w, art_h))
            p.restore()

            margin_v = h * 0.14
            avail_h = max(100.0, h - margin_v * 2.0)
            avail_w = max(100.0, w * 0.65)
            fit_size = min(avail_w, avail_h)

            scale_fg = min(fit_size / art_w, fit_size / art_h)
            dw_fg = art_w * scale_fg
            dh_fg = art_h * scale_fg
            fx = (w - dw_fg) / 2.0
            fy = (h - dh_fg) / 2.0

            qc = QColor(self.accent_color.split(';')[0].strip() if self.accent_color else "#ff1744")
            if not qc.isValid():
                qc = QColor("#ff1744")
            halo_r = max(dw_fg, dh_fg) * 0.65
            halo = QRadialGradient(w / 2.0, h / 2.0, halo_r)
            halo.setColorAt(0.0, QColor(qc.red(), qc.green(), qc.blue(), 90))
            halo.setColorAt(0.75, QColor(qc.red(), qc.green(), qc.blue(), 20))
            halo.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.fillRect(QRectF(0, 0, w, h), QBrush(halo))

            card_rect = QRectF(fx, fy, dw_fg, dh_fg)
            clip_path = QPainterPath()
            clip_path.addRoundedRect(card_rect, 18.0, 18.0)
            p.save()
            p.setClipPath(clip_path)
            p.drawPixmap(card_rect, self.album_art, QRectF(0.0, 0.0, art_w, art_h))
            p.restore()

            p.setPen(QPen(QColor(qc.red(), qc.green(), qc.blue(), 180), 2.0))
            p.drawRoundedRect(card_rect, 18.0, 18.0)
        else:
            ph = _get_placeholder_pixmap(int(w), int(h), is_playing=self.is_playing, accent_color=self.accent_color)
            p.drawPixmap(0, 0, ph)

    def _paint_radial_waves(self, p: QPainter, w: float, h: float) -> None:
        """Renderiza el Visualizador Radial de Ondas Espectrales al ritmo de la música (estilo Trap Nation)."""
        import math

        cx = w / 2.0
        cy = h * 0.50
        base_art_size = max(140.0, min(w * 0.52, h * 0.52, 220.0))
        pulse_scale = 1.0 + (self._bass_pulse * 0.12 if self.is_playing else 0.0)
        art_size = base_art_size * pulse_scale
        art_r = art_size / 2.0

        # 1. Resplandor radial de fondo ambiental con color de acento / tema
        qc = QColor(self.accent_color.split(';')[0].strip() if self.accent_color else "#ff1744")
        if not qc.isValid():
            qc = QColor("#ff1744")

        ambient_grad = QRadialGradient(cx, cy, art_r * 2.2)
        ambient_grad.setColorAt(0.0, QColor(qc.red(), qc.green(), qc.blue(), 90))
        ambient_grad.setColorAt(0.55, QColor(qc.red(), qc.green(), qc.blue(), 25))
        ambient_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(ambient_grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(cx - art_r * 2.2, cy - art_r * 2.2, art_r * 4.4, art_r * 4.4))

        # 2. Ondas de Choque Concéntricas (Shockwave Ripple Rings)
        for sw in self._shockwaves:
            sw_r = art_r * sw["radius_factor"]
            sw_alpha = int(max(0, min(255, sw["opacity"] * 255)))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(qc.red(), qc.green(), qc.blue(), sw_alpha), 2.5))
            p.drawEllipse(QRectF(cx - sw_r, cy - sw_r, sw_r * 2, sw_r * 2))

        # 3. Barras de Espectro Radial (72 barras cilíndricas que emanan del círculo)
        r_inner = art_r + 6.0
        max_bar_len = min(w, h) * 0.18
        p.setBrush(Qt.BrushStyle.NoBrush)

        for i in range(self.radial_bar_count):
            theta = i * (2.0 * math.pi / float(self.radial_bar_count))
            bh = max(4.0, self.radial_heights[i] * max_bar_len)
            
            x1 = cx + r_inner * math.cos(theta)
            y1 = cy + r_inner * math.sin(theta)
            x2 = cx + (r_inner + bh) * math.cos(theta)
            y2 = cy + (r_inner + bh) * math.sin(theta)

            # Color interpolado según posición angular dentro del degradado del tema
            norm_pos = i / float(self.radial_bar_count)
            bar_color = _interpolate_color_list(self.gradient_colors, norm_pos)

            p.setPen(QPen(bar_color, 3.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # 4. Carátula Central con rotación suave y recorte geométrico
        art_rect = QRectF(-art_r, -art_r, art_r * 2, art_r * 2)
        if self.cover_shape == "heart":
            art_clip = create_heart_path(art_rect)
        elif self.cover_shape == "rounded":
            art_clip = QPainterPath()
            art_clip.addRoundedRect(art_rect, 18.0, 18.0)
        else:
            art_clip = QPainterPath()
            art_clip.addEllipse(art_rect)

        p.save()
        p.translate(cx, cy)
        p.rotate(self._rotation_angle)

        p.save()
        p.setClipPath(art_clip)

        if self.album_art and not self.album_art.isNull():
            art_w = float(self.album_art.width())
            art_h = float(self.album_art.height())
            if art_w > 0 and art_h > 0:
                if art_w > art_h:
                    src_x = (art_w - art_h) / 2.0
                    src_y = 0.0
                    crop_w = art_h
                    crop_h = art_h
                else:
                    src_x = 0.0
                    src_y = (art_h - art_w) / 2.0
                    crop_w = art_w
                    crop_h = art_w
                p.drawPixmap(art_rect, self.album_art, QRectF(src_x, src_y, crop_w, crop_h))
        else:
            ph = _get_placeholder_pixmap(int(art_r * 2), int(art_r * 2), is_playing=self.is_playing, accent_color=self.accent_color)
            p.drawPixmap(int(-art_r), int(-art_r), ph)

        p.restore()

        # Borde iluminado de la carátula central
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(qc.red(), qc.green(), qc.blue(), 230), 3.0))
        p.drawPath(art_clip)

        p.restore()

    def _paint_card_glow(self, p: QPainter, w: float, h: float) -> None:
        """Renderiza la Carátula Flotante con Halo Neón y ecualizador horizontal inferior."""
        cx = w / 2.0
        cy = h * 0.44
        card_size = max(150.0, min(w * 0.65, h * 0.58, 260.0))
        card_rect = QRectF(cx - card_size / 2.0, cy - card_size / 2.0, card_size, card_size)

        qc = QColor(self.accent_color.split(';')[0].strip() if self.accent_color else "#ff1744")
        if not qc.isValid():
            qc = QColor("#ff1744")

        # 1. Halo Neón difuso detrás de la tarjeta
        halo_grad = QRadialGradient(cx, cy, card_size * 0.75)
        halo_grad.setColorAt(0.0, QColor(qc.red(), qc.green(), qc.blue(), 110))
        halo_grad.setColorAt(0.65, QColor(qc.red(), qc.green(), qc.blue(), 30))
        halo_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(halo_grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(cx - card_size * 0.75, cy - card_size * 0.75, card_size * 1.5, card_size * 1.5))

        # 2. Carátula
        card_path = QPainterPath()
        if self.cover_shape == "circle":
            card_path.addEllipse(card_rect)
        elif self.cover_shape == "heart":
            card_path = create_heart_path(card_rect)
        else:
            card_path.addRoundedRect(card_rect, 20.0, 20.0)

        p.save()
        p.setClipPath(card_path)

        if self.album_art and not self.album_art.isNull():
            art_w = float(self.album_art.width())
            art_h = float(self.album_art.height())
            if art_w > 0 and art_h > 0:
                if art_w > art_h:
                    src_x = (art_w - art_h) / 2.0
                    src_y = 0.0
                    crop_w = art_h
                    crop_h = art_h
                else:
                    src_x = 0.0
                    src_y = (art_h - art_w) / 2.0
                    crop_w = art_w
                    crop_h = art_w
                p.drawPixmap(card_rect, self.album_art, QRectF(src_x, src_y, crop_w, crop_h))
        else:
            ph = _get_placeholder_pixmap(int(card_size), int(card_size), is_playing=self.is_playing, accent_color=self.accent_color)
            p.drawPixmap(int(card_rect.x()), int(card_rect.y()), ph)

        p.restore()

        # Borde exterior de la tarjeta
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(qc.red(), qc.green(), qc.blue(), 220), 2.5))
        p.drawPath(card_path)

        # 3. Ecualizador horizontal inferior
        eq_y = card_rect.bottom() + 16.0
        eq_w = card_size * 0.95
        eq_x = cx - eq_w / 2.0
        gap = max(2.0, (eq_w / self.h_bar_count) * 0.30)
        total_gaps = (self.h_bar_count - 1) * gap
        b_w = max(2.0, (eq_w - total_gaps) / self.h_bar_count)
        max_h = 32.0

        p.setPen(Qt.PenStyle.NoPen)
        for j in range(self.h_bar_count):
            bx = eq_x + j * (b_w + gap)
            bh = max(3.0, self.h_bar_heights[j] * max_h)
            by = eq_y + (max_h - bh)
            norm_j = j / float(self.h_bar_count)
            bar_col = _interpolate_color_list(self.gradient_colors, norm_j)
            p.setBrush(QBrush(bar_col))
            p.drawRoundedRect(QRectF(bx, by, b_w, bh), 1.5, 1.5)

    def _paint_vinyl_turntable(self, p: QPainter, w: float, h: float) -> None:
        """Renderiza el Tocadiscos de Vinilo Clásico Hi-Fi con plato giratorio y brazo dinámico."""
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

        if self.album_art and not self.album_art.isNull():
            art_w = float(self.album_art.width())
            art_h = float(self.album_art.height())
            if art_w > 0 and art_h > 0:
                if art_w > art_h:
                    src_x = (art_w - art_h) / 2.0
                    src_y = 0.0
                    crop_w = art_h
                    crop_h = art_h
                else:
                    src_x = 0.0
                    src_y = (art_h - art_w) / 2.0
                    crop_w = art_w
                    crop_h = art_w
                p.drawPixmap(art_rect, self.album_art, QRectF(src_x, src_y, crop_w, crop_h))
        else:
            ph = _get_placeholder_pixmap(int(art_r * 2), int(art_r * 2), is_playing=self.is_playing, accent_color=self.accent_color)
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

        # 5. Brazo de Tocadiscos (Tonearm) estilo Hi-Fi
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


VinylTurntableWidget = ExpandedArtworkDisplayWidget
ArtworkEKGDisplayWidget = ExpandedArtworkDisplayWidget

class SongCardWidget(QFrame):
    """Tarjeta individual unificada para canciones en Escuchados recientemente y Todas tus canciones."""
    card_clicked = pyqtSignal(dict)

    def __init__(
        self,
        track_index: int,
        title: str,
        artist: str,
        art_url: str,
        duration_sec: int = 0,
        accent_color: str = "#ff1744",
        is_playing: bool = False,
        audio_engine: Optional[Any] = None,
        track_meta: Optional[Dict[str, Any]] = None,
        on_playlist_changed: Optional[Any] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.track_index = track_index
        self.accent_color = accent_color
        self.audio_engine = audio_engine
        self.track_meta = dict(track_meta) if track_meta else {
            "title": title,
            "artist": artist,
            "art_url": art_url,
            "length_sec": duration_sec,
        }
        self.on_playlist_changed = on_playlist_changed
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

        # Jerarquía Inteligente de Biblioteca: Conservar carátula original y usar global solo si no tiene portada
        global_custom = ""
        curr_p = parent
        while curr_p:
            if hasattr(curr_p, 'custom_inner_image'):
                global_custom = getattr(curr_p, 'custom_inner_image', '') or ''
                break
            curr_p = curr_p.parentWidget()

        effective_art = resolve_library_art(self.track_meta, global_custom)
        pix = get_cached_pixmap(effective_art, 148, 148) if effective_art else None
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

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.card_clicked.emit(self.track_meta)
        elif event.button() == Qt.MouseButton.RightButton:
            from ui.context_menus import show_track_context_menu

            show_track_context_menu(
                track_meta=self.track_meta,
                parent_widget=self,
                global_pos=event.globalPosition().toPoint(),
                audio_engine=self.audio_engine,
                accent_color=self.accent_color,
                on_playlist_changed=self.on_playlist_changed,
                on_track_play_requested=lambda t: self.card_clicked.emit(t if isinstance(t, dict) else self.track_meta),
            )
        super().mousePressEvent(event)


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
        art_path = index.data(Qt.ItemDataRole.UserRole + 3) or ""
        pix = get_cached_rounded_pixmap(art_path, 34, 34, radius=6.0, placeholder_text="♫")
        painter.drawPixmap(art_rect, pix)

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
        audio_engine: Optional[Any] = None,
        on_playlist_changed: Optional[Any] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.playlist = list(playlist or [])
        self.current_index = current_index
        self.accent_color = accent_color
        self.audio_engine = audio_engine
        self.on_playlist_changed = on_playlist_changed

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

        # Lista de canciones con menú contextual habilitado (Frente B)
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
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._on_context_menu_requested)
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

    def _on_context_menu_requested(self, pos: QPoint) -> None:
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        idx = item.data(Qt.ItemDataRole.UserRole)
        if idx is None or not (0 <= idx < len(self.playlist)):
            return
        track = self.playlist[idx]

        from ui.context_menus import show_track_context_menu

        show_track_context_menu(
            track_meta=track,
            parent_widget=self.list_widget,
            global_pos=self.list_widget.mapToGlobal(pos),
            audio_engine=self.audio_engine,
            is_active_queue=True,
            queue_index=idx,
            accent_color=self.accent_color,
            on_queue_changed=self._on_queue_modified_internally,
            on_playlist_changed=self._on_playlist_changed_internally,
            on_track_play_requested=lambda t: self._play_track_at_index(idx),
        )

    def _play_track_at_index(self, idx: int) -> None:
        self.current_index = idx
        self._populate_list()
        self.play_requested.emit(idx)

    def _on_queue_modified_internally(self) -> None:
        if self.audio_engine and hasattr(self.audio_engine, "playlist"):
            self.playlist = list(self.audio_engine.playlist or [])
            self.current_index = getattr(self.audio_engine, "current_index", -1)
        self.lbl_count.setText(f"{len(self.playlist)} canciones")
        self._populate_list()

    def _on_playlist_changed_internally(self) -> None:
        if self.on_playlist_changed:
            self.on_playlist_changed()

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
        else:
            self.lbl_empty.hide()
            self.list_widget.show()

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
    open_add_link_requested = pyqtSignal()

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
        self.gradient_colors: List[str] = ["#ff1744", "#7b1fa2", "#0c0c10"]
        self.brand_name: str = "RED WORLD"
        self.inner_art_mode: str = "auto"
        self.custom_inner_image: str = ""
        self.playlist: List[Dict[str, Any]] = []
        self._raw_playlist: List[Dict[str, Any]] = []
        self.library_sort_order: str = "recent"
        self.library_view_mode: str = "grid"
        self.current_index: int = -1
        self.current_view_mode: str = "expanded"
        self.is_shuffle_active: bool = bool(getattr(self.audio_engine, 'is_shuffle', False)) if self.audio_engine else False
        self.active_filter_mode: str = "all"
        self.selected_playlist_name: Optional[str] = None
        self.user_playlists: Dict[str, List[int]] = {"Lista 1": [], "Lista 2": []}
        self._dirty: bool = False
        self._rebuilding: bool = False
        self._current_library_cols: int = 4

        self.expanded_cover_fit: str = "full_bleed"
        self.expanded_show_lyrics: bool = True
        self.expanded_scrim_opacity: float = 0.35

        if self.config and hasattr(self.config, 'get'):
            self.library_sort_order = self.config.get("library_sort_order", "recent")
            self.library_view_mode = self.config.get("library_view_mode", "grid")
        if self.config and hasattr(self.config, 'get_personalization'):
            exp_p = self.config.get_personalization("expanded")
            if exp_p:
                self.expanded_cover_fit = exp_p.get("expanded_cover_fit", "full_bleed")
                self.expanded_show_lyrics = bool(exp_p.get("expanded_show_lyrics", True))
                self.expanded_scrim_opacity = float(exp_p.get("expanded_scrim_opacity", 0.35))
                self.inner_art_mode = exp_p.get("inner_art_mode", "auto")
                self.custom_inner_image = exp_p.get("custom_inner_image", "")

        self.init_ui()
        self.update_shuffle_status(self.is_shuffle_active)

    def _get_config_val(self, key: str, default: Any = None) -> Any:
        if self.config and hasattr(self.config, 'get'):
            return self.config.get(key, default)
        p = self.parentWidget()
        while p:
            if hasattr(p, 'config') and hasattr(p.config, 'get'):
                return p.config.get(key, default)
            p = p.parentWidget()
        return default

    def _set_config_val(self, key: str, value: Any) -> None:
        if self.config and hasattr(self.config, 'set'):
            self.config.set(key, value)
            return
        p = self.parentWidget()
        while p:
            if hasattr(p, 'config') and hasattr(p.config, 'set'):
                p.config.set(key, value)
                return
            p = p.parentWidget()

    def set_audio_engine(self, engine: Any) -> None:
        self.audio_engine = engine
        if hasattr(self, "music_home_view") and self.music_home_view:
            self.music_home_view.set_audio_engine(engine)
        if hasattr(self, "playlists_page_view") and self.playlists_page_view:
            self.playlists_page_view.set_audio_engine(engine)
        if engine:
            self.update_shuffle_status(getattr(engine, 'is_shuffle', False))

    def set_config(self, config: Any) -> None:
        self.config = config
        if config and hasattr(config, 'get'):
            self.library_sort_order = config.get("library_sort_order", "recent")
            self.library_view_mode = config.get("library_view_mode", "grid")
            if hasattr(self, 'combo_sort') and self.combo_sort:
                idx = self.combo_sort.findData(self.library_sort_order)
                if idx >= 0:
                    self.combo_sort.blockSignals(True)
                    self.combo_sort.setCurrentIndex(idx)
                    self.combo_sort.blockSignals(False)
            if hasattr(self, '_update_view_mode_buttons'):
                self._update_view_mode_buttons()

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

        self.btn_nav_add_link = QPushButton("  🔗   Agregar Link", self.sidebar)
        self.btn_nav_add_link.setToolTip("Agregar música desde YouTube o Spotify (Online / Offline)")
        self.btn_nav_add_link.clicked.connect(self.open_add_link_requested.emit)

        self.nav_items_data = [
            (self.btn_nav_music, "🎵", "Música"),
            (self.btn_nav_playing, "💿", "En Reproducción"),
            (self.btn_nav_favs, "♥", "Favoritos"),
            (self.btn_nav_albums, "📚", "Biblioteca"),
            (self.btn_nav_playlists, "📋", "Listas"),
            (self.btn_nav_add_link, "🔗", "Agregar Link"),
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
        self.music_home_view.playlist_changed.connect(self._on_playlists_data_changed)
        self.center_stack.addWidget(self.music_home_view)

        # ----------------------------------------------------
        # PAGE 1: VISTA BIBLIOTECA / FAVORITOS
        # ----------------------------------------------------
        self.page_library = QWidget()
        page_lib_layout = QVBoxLayout(self.page_library)
        page_lib_layout.setContentsMargins(18, 14, 18, 14)
        page_lib_layout.setSpacing(14)

        # 1. BARRA DE BÚSQUEDA DE BIBLIOTECA (Idéntica a la sección Música)
        search_row = QHBoxLayout()
        search_row.setContentsMargins(0, 0, 0, 0)
        search_row.setSpacing(10)

        search_frame = QFrame(self.page_library)
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
        search_layout.setContentsMargins(14, 0, 14, 0)
        search_layout.setSpacing(10)

        lbl_search_icon = QLabel("🔍", search_frame)
        lbl_search_icon.setFont(QFont("Sans Serif", 11))
        lbl_search_icon.setStyleSheet("border: none; background: transparent;")
        search_layout.addWidget(lbl_search_icon)

        self.lib_search_input = QLineEdit(search_frame)
        self.lib_search_input.setPlaceholderText(
            "Buscar canciones, artistas o álbumes en tu biblioteca..."
        )
        self.lib_search_input.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #ffffff;
                font-size: 13px;
                padding: 0px;
            }
        """)
        self.lib_search_input.textChanged.connect(self._on_lib_search_text_changed)
        search_layout.addWidget(self.lib_search_input, stretch=1)

        self.btn_lib_search_clear = QPushButton("✕", search_frame)
        self.btn_lib_search_clear.setFixedSize(24, 24)
        self.btn_lib_search_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_lib_search_clear.setVisible(False)
        self.btn_lib_search_clear.setStyleSheet("""
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
        self.btn_lib_search_clear.clicked.connect(self.lib_search_input.clear)
        search_layout.addWidget(self.btn_lib_search_clear)

        search_row.addWidget(search_frame, stretch=1)
        search_row.addSpacing(54)
        page_lib_layout.addLayout(search_row)

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

        # 2. Sección Todas tus canciones con barra de herramientas de orden y modo de vista
        lib_header_layout = QHBoxLayout()
        lib_header_layout.setContentsMargins(0, 8, 0, 4)
        lib_header_layout.setSpacing(10)

        self.lbl_songs_title = QLabel("Todas tus canciones", scroll_content)
        self.lbl_songs_title.setFont(QFont("Sans Serif", 12, QFont.Weight.Bold))
        self.lbl_songs_title.setStyleSheet("color: #ffffff; letter-spacing: 0.3px;")
        lib_header_layout.addWidget(self.lbl_songs_title)
        lib_header_layout.addStretch(1)

        lbl_sort = QLabel("Ordenar:", scroll_content)
        lbl_sort.setFont(QFont("Sans Serif", 8, QFont.Weight.Medium))
        lbl_sort.setStyleSheet("color: rgba(255, 255, 255, 0.60); border: none; background: transparent;")
        lib_header_layout.addWidget(lbl_sort)

        self.combo_sort = QComboBox(scroll_content)
        self.combo_sort.setCursor(Qt.CursorShape.PointingHandCursor)
        for key, label in SORT_OPTIONS:
            self.combo_sort.addItem(label, userData=key)

        idx_sort = self.combo_sort.findData(self.library_sort_order)
        if idx_sort >= 0:
            self.combo_sort.setCurrentIndex(idx_sort)
        self.combo_sort.currentIndexChanged.connect(self._on_sort_changed)
        lib_header_layout.addWidget(self.combo_sort)
        scroll_content_layout.addLayout(lib_header_layout)

        self._apply_sort_combo_style()

        self.songs_grid_widget = QWidget(scroll_content)
        self.songs_grid_layout = QGridLayout(self.songs_grid_widget)
        self.songs_grid_layout.setContentsMargins(0, 0, 0, 0)
        self.songs_grid_layout.setSpacing(14)
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
        # ----------------------------------------------------
        # PAGE 1: VISTA EN REPRODUCCIÓN UNIFICADA (Canvas Inmersivo Full-Bleed + Letras Flotantes)
        # ----------------------------------------------------
        self.page_now_playing = QWidget()
        page_np_layout = QGridLayout(self.page_now_playing)
        page_np_layout.setContentsMargins(0, 0, 0, 0)
        page_np_layout.setSpacing(0)

        # 1. Capa 0 (Fondo Inmersivo): Carátula / GIF / Video en tamaño completo
        self.artwork_ekg_widget = ExpandedArtworkDisplayWidget(self.page_now_playing)
        self.turntable_widget = self.artwork_ekg_widget
        self.artwork_ekg_widget.set_cover_fit(self.expanded_cover_fit)
        self.artwork_ekg_widget.set_scrim_opacity(self.expanded_scrim_opacity)
        self.artwork_ekg_widget.set_show_lyrics(self.expanded_show_lyrics)
        if getattr(self, 'inner_art_mode', 'auto') == "custom_always" and getattr(self, 'custom_inner_image', ''):
            self.artwork_ekg_widget.always_play = True
            eff_art, _ = resolve_now_playing_art({}, self.custom_inner_image, self.inner_art_mode)
            if eff_art:
                pix = get_cached_pixmap(eff_art, 1200, 760)
                self.artwork_ekg_widget.set_album_art(pix, art_path=eff_art)
        page_np_layout.addWidget(self.artwork_ekg_widget, 0, 0)

        # 2. Capa 1 (Overlay Interactivo): Cabecera de canción, Letras y Deck flotante de controles
        self.np_overlay_widget = QWidget(self.page_now_playing)
        self.np_overlay_widget.setStyleSheet("background: transparent; border: none;")
        self.np_overlay_widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        np_overlay_layout = QVBoxLayout(self.np_overlay_widget)
        np_overlay_layout.setContentsMargins(24, 16, 24, 18)
        np_overlay_layout.setSpacing(10)

        # --- A. BARRA SUPERIOR (Info de Canción + Acciones + Botón de Letras) ---
        header_top_row = QHBoxLayout()
        header_top_row.setSpacing(16)

        track_info_col = QVBoxLayout()
        track_info_col.setSpacing(2)

        self.np_song_title = MarqueeLabel("Sin reproducción", font=QFont("Sans Serif", 19, QFont.Weight.Bold), color_str="#ffffff", parent=self.np_overlay_widget)
        self.np_song_title.setFixedHeight(34)
        track_info_col.addWidget(self.np_song_title)

        sub_info_row = QHBoxLayout()
        sub_info_row.setSpacing(12)
        self.np_song_artist = MarqueeLabel("Selecciona una canción", font=QFont("Sans Serif", 12), color_str="#cbd5e1", parent=self.np_overlay_widget)
        self.np_song_artist.setFixedHeight(22)
        sub_info_row.addWidget(self.np_song_artist)

        self.np_song_album = QLabel("", self.np_overlay_widget)
        self.np_song_album.setFont(QFont("Sans Serif", 10))
        self.np_song_album.setStyleSheet("color: rgba(255, 255, 255, 0.65); border: none; background: transparent;")
        self.np_song_album.setFixedHeight(22)
        sub_info_row.addWidget(self.np_song_album)
        sub_info_row.addStretch(1)

        track_info_col.addLayout(sub_info_row)
        header_top_row.addLayout(track_info_col, stretch=1)
        np_overlay_layout.addLayout(header_top_row)

        # --- B. ÁREA CENTRAL (Letras Flotantes con Desenfoque o Espacio Abierto) ---
        self.lyrics_display_widget = LyricsDisplayWidget(self.np_overlay_widget)
        self.lyrics_display_widget.seek_requested.connect(self._on_lyrics_seek_requested)
        self.lyrics_container = self.lyrics_display_widget
        self.lyrics_display_widget.setStyleSheet("background: transparent; border: none;")
        self.lyrics_display_widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        np_overlay_layout.addWidget(self.lyrics_display_widget, stretch=1)

        self.np_art_spacer = QWidget(self.np_overlay_widget)
        self.np_art_spacer.setStyleSheet("background: transparent; border: none;")
        np_overlay_layout.addWidget(self.np_art_spacer, stretch=1)

        # --- C. DECK FLOTANTE INFERIOR DE CONTROLES (Cápsula de Cristal) ---
        self.np_controls_deck = QFrame(self.np_overlay_widget)
        self.np_controls_deck.setObjectName("NPControlsDeck")
        self.np_controls_deck.setStyleSheet("""
            QFrame#NPControlsDeck {
                background-color: rgba(10, 14, 26, 0.72);
                border-radius: 22px;
                border: 1.5px solid rgba(255, 255, 255, 0.14);
            }
        """)
        controls_deck_layout = QVBoxLayout(self.np_controls_deck)
        controls_deck_layout.setContentsMargins(20, 10, 20, 12)
        controls_deck_layout.setSpacing(6)

        # 1. Fila de Progreso y Tiempo
        time_row = QHBoxLayout()
        time_row.setSpacing(12)

        self.np_time_left = QLabel("00:00", self.np_controls_deck)
        self.np_time_left.setMinimumWidth(56)
        self.np_time_left.setFont(QFont("Sans Serif", 10, QFont.Weight.Bold))
        self.np_time_left.setStyleSheet("color: #cbd5e1; background: transparent; border: none;")
        self.np_time_left.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        time_row.addWidget(self.np_time_left)

        self.np_progress_bar = SeekSlider(Qt.Orientation.Horizontal, self.np_controls_deck)
        self.np_progress_bar.setObjectName("ProgressBar")
        self.np_progress_bar.setRange(0, 1000)
        self.np_progress_bar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.np_progress_bar.sliderPressed.connect(self._on_np_slider_pressed)
        self.np_progress_bar.sliderMoved.connect(self._on_np_slider_moved)
        self.np_progress_bar.sliderReleased.connect(self._on_np_slider_released)
        time_row.addWidget(self.np_progress_bar, stretch=1)

        self.np_time_right = QLabel("-00:00", self.np_controls_deck)
        self.np_time_right.setMinimumWidth(64)
        self.np_time_right.setFont(QFont("Sans Serif", 10, QFont.Weight.Bold))
        self.np_time_right.setStyleSheet("color: #94a3b8; background: transparent; border: none;")
        self.np_time_right.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        time_row.addWidget(self.np_time_right)

        controls_deck_layout.addLayout(time_row)

        # 2. Fila de Botones de Reproducción, Herramientas y Control de Volumen
        deck_bottom_row = QHBoxLayout()
        deck_bottom_row.setContentsMargins(12, 4, 12, 6)
        deck_bottom_row.setSpacing(12)

        # 2.1 Bloque izquierdo: Acciones de Pista y Biblioteca (Favoritos, Agregar a Lista, Cola)
        left_actions = QHBoxLayout()
        left_actions.setSpacing(10)
        left_actions.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.np_btn_fav = QPushButton("♡", self.np_controls_deck)
        self.np_btn_fav.setFixedSize(40, 40)
        self.np_btn_fav.setCursor(Qt.CursorShape.PointingHandCursor)
        self.np_btn_fav.setToolTip("Marcar como Favorita (Ctrl+F)")
        self.np_btn_fav.setStyleSheet("QPushButton { background: rgba(255, 255, 255, 0.08); border: 1.5px solid rgba(255, 255, 255, 0.18); border-radius: 20px; color: #ffffff; font-size: 15px; font-weight: bold; } QPushButton:hover { background: rgba(255, 255, 255, 0.22); }")
        self.np_btn_fav.clicked.connect(self.toggle_fav_requested)
        left_actions.addWidget(self.np_btn_fav)

        self.np_btn_add_playlist = QPushButton("＋", self.np_controls_deck)
        self.np_btn_add_playlist.setFixedSize(40, 40)
        self.np_btn_add_playlist.setCursor(Qt.CursorShape.PointingHandCursor)
        self.np_btn_add_playlist.setToolTip("Añadir a una lista de reproducción")
        self.np_btn_add_playlist.setStyleSheet("QPushButton { background: rgba(255, 255, 255, 0.08); border: 1.5px solid rgba(255, 255, 255, 0.18); border-radius: 20px; color: #ffffff; font-size: 17px; font-weight: bold; } QPushButton:hover { background: rgba(255, 255, 255, 0.22); }")
        self.np_btn_add_playlist.clicked.connect(self._on_np_add_playlist_clicked)
        left_actions.addWidget(self.np_btn_add_playlist)

        self.np_btn_queue = QPushButton("📑", self.np_controls_deck)
        self.np_btn_queue.setFixedSize(40, 40)
        self.np_btn_queue.setCursor(Qt.CursorShape.PointingHandCursor)
        self.np_btn_queue.setToolTip("Ver lista en curso (Cola de reproducción)")
        self.np_btn_queue.setStyleSheet("QPushButton { background: rgba(255, 255, 255, 0.08); border: 1.5px solid rgba(255, 255, 255, 0.18); border-radius: 20px; color: #ffffff; font-size: 15px; font-weight: bold; } QPushButton:hover { background: rgba(255, 255, 255, 0.22); }")
        self.np_btn_queue.clicked.connect(self._open_current_queue_dialog)
        left_actions.addWidget(self.np_btn_queue)

        deck_bottom_row.addLayout(left_actions, stretch=1)

        # 2.2 Bloque central: Controles de Reproducción (Aleatorio, Anterior, Play, Siguiente, Repetir)
        ctrls_center = QHBoxLayout()
        ctrls_center.setSpacing(14)
        ctrls_center.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.np_btn_shuffle = QPushButton("⇄", self.np_controls_deck)
        self.np_btn_shuffle.setFixedSize(40, 40)
        self.np_btn_shuffle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.np_btn_shuffle.setToolTip("Modo Aleatorio: Desactivado")
        self.np_btn_shuffle.setStyleSheet("QPushButton { background: rgba(255, 255, 255, 0.08); border: 1.5px solid rgba(255, 255, 255, 0.18); border-radius: 20px; color: rgba(255, 255, 255, 0.65); font-size: 15px; font-weight: bold; } QPushButton:hover { background: rgba(255, 255, 255, 0.22); color: #ffffff; }")
        self.np_btn_shuffle.clicked.connect(self.shuffle_requested)
        ctrls_center.addWidget(self.np_btn_shuffle)

        self.np_btn_prev = QPushButton("⏮", self.np_controls_deck)
        self.np_btn_prev.setFixedSize(48, 48)
        self.np_btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self.np_btn_prev.setToolTip("Pista anterior")
        self.np_btn_prev.setStyleSheet("QPushButton { background: rgba(255, 255, 255, 0.12); border: 1.5px solid rgba(255, 255, 255, 0.25); border-radius: 24px; color: #ffffff; font-size: 17px; font-weight: bold; } QPushButton:hover { background: rgba(255, 255, 255, 0.28); }")
        self.np_btn_prev.clicked.connect(self.prev_requested)
        ctrls_center.addWidget(self.np_btn_prev)

        clean_accent = self.accent_color.split(';')[0].strip() if self.accent_color else "#ff1744"
        self.np_btn_play = QPushButton("▶", self.np_controls_deck)
        self.np_btn_play.setObjectName("PlayButton")
        self.np_btn_play.setFixedSize(60, 60)
        self.np_btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
        self.np_btn_play.setToolTip("Reproducir / Pausar")
        self.np_btn_play.setStyleSheet(f"QPushButton {{ background-color: #ffffff; border: none; border-radius: 30px; color: {clean_accent}; font-size: 24px; font-weight: bold; }} QPushButton:hover {{ background-color: #f1f5f9; }}")
        self.np_btn_play.clicked.connect(self.play_pause_requested)
        ctrls_center.addWidget(self.np_btn_play)

        self.np_btn_next = QPushButton("⏭", self.np_controls_deck)
        self.np_btn_next.setFixedSize(48, 48)
        self.np_btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.np_btn_next.setToolTip("Pista siguiente")
        self.np_btn_next.setStyleSheet("QPushButton { background: rgba(255, 255, 255, 0.12); border: 1.5px solid rgba(255, 255, 255, 0.25); border-radius: 24px; color: #ffffff; font-size: 17px; font-weight: bold; } QPushButton:hover { background: rgba(255, 255, 255, 0.28); }")
        self.np_btn_next.clicked.connect(self.next_requested)
        ctrls_center.addWidget(self.np_btn_next)

        self.np_btn_loop = QPushButton("↻", self.np_controls_deck)
        self.np_btn_loop.setFixedSize(40, 40)
        self.np_btn_loop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.np_btn_loop.setToolTip("Modo Bucle: Desactivado")
        self.np_btn_loop.setStyleSheet("QPushButton { background: rgba(255, 255, 255, 0.08); border: 1.5px solid rgba(255, 255, 255, 0.18); border-radius: 20px; color: rgba(255, 255, 255, 0.65); font-size: 15px; font-weight: bold; } QPushButton:hover { background: rgba(255, 255, 255, 0.22); color: #ffffff; }")
        self.np_btn_loop.clicked.connect(self.loop_requested)
        ctrls_center.addWidget(self.np_btn_loop)

        deck_bottom_row.addLayout(ctrls_center, stretch=0)

        # 2.3 Bloque derecho: Letras y Control de Volumen
        right_actions = QHBoxLayout()
        right_actions.setSpacing(10)
        right_actions.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.np_btn_toggle_lyrics = QPushButton("♪", self.np_controls_deck)
        self.np_btn_toggle_lyrics.setObjectName("ExpandedLyricsToggleBtn")
        self.np_btn_toggle_lyrics.setFixedSize(40, 40)
        self.np_btn_toggle_lyrics.setCursor(Qt.CursorShape.PointingHandCursor)
        self.np_btn_toggle_lyrics.setCheckable(True)
        self.np_btn_toggle_lyrics.setChecked(self.expanded_show_lyrics)
        self.np_btn_toggle_lyrics.setToolTip("Mostrar / Ocultar Letras (♪)")
        self.np_btn_toggle_lyrics.clicked.connect(self._toggle_np_lyrics)
        right_actions.addWidget(self.np_btn_toggle_lyrics)

        self.np_btn_mute = QPushButton("🔊", self.np_controls_deck)
        self.np_btn_mute.setFixedSize(40, 40)
        self.np_btn_mute.setCursor(Qt.CursorShape.PointingHandCursor)
        self.np_btn_mute.setToolTip("Silenciar / Desilenciar")
        self.np_btn_mute.setStyleSheet("QPushButton { background: rgba(255, 255, 255, 0.08); border: 1.5px solid rgba(255, 255, 255, 0.18); border-radius: 20px; color: #ffffff; font-size: 13px; } QPushButton:hover { background: rgba(255, 255, 255, 0.22); }")
        self.np_btn_mute.clicked.connect(self._toggle_np_mute)
        right_actions.addWidget(self.np_btn_mute)

        self.np_vol_icon = QLabel("🔊", self.np_controls_deck)
        self.np_vol_icon.setFixedSize(20, 20)
        self.np_vol_icon.setStyleSheet("color: rgba(255, 255, 255, 0.70); font-size: 12px; border: none; background: transparent;")
        self.np_vol_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.np_vol_icon.setVisible(False)

        self.np_slider_volume = Y2KVolumeSlider(self.np_controls_deck)
        self.np_slider_volume.setObjectName("VolumeSlider")
        self.np_slider_volume.setFixedHeight(20)
        self.np_slider_volume.setFixedWidth(110)
        self.np_slider_volume.setRange(0, 100)
        self.np_slider_volume.setValue(100)
        self.np_slider_volume.set_accent_color(self.accent_color, self.gradient_colors)
        self.np_slider_volume.valueChanged.connect(self._on_np_vol_changed)
        right_actions.addWidget(self.np_slider_volume)

        self.np_lbl_vol_val = QLabel("100%", self.np_controls_deck)
        self.np_lbl_vol_val.setFixedWidth(36)
        self.np_lbl_vol_val.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        self.np_lbl_vol_val.setStyleSheet("color: rgba(255, 255, 255, 0.70); border: none; background: transparent;")
        self.np_lbl_vol_val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        right_actions.addWidget(self.np_lbl_vol_val)

        deck_bottom_row.addLayout(right_actions, stretch=1)

        controls_deck_layout.addLayout(deck_bottom_row)
        np_overlay_layout.addWidget(self.np_controls_deck)

        page_np_layout.addWidget(self.np_overlay_widget, 0, 0)

        # Referencias de retrocompatibilidad
        self.left_np_frame = self.np_controls_deck
        self.right_np_frame = self.np_overlay_widget

        # Aplicar visibilidad inicial de letras
        self._apply_np_lyrics_visibility()

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
        self.playlists_page_view.playlist_changed.connect(self._on_playlists_data_changed)
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
        if not self.audio_engine or not track_meta:
            return

        target_path = (track_meta.get("file_path") or track_meta.get("path") or "").strip()
        target_id = str(track_meta.get("track_id", "")).strip()
        target_title = str(track_meta.get("title", "")).strip().lower()
        target_artist = str(track_meta.get("artist", "")).strip().lower()
        target_basename = os.path.basename(target_path).lower() if target_path else ""

        # 1. Buscar en la cola actual del motor de audio (por track_id, ruta, nombre de archivo o título+artista)
        existing_idx = -1
        current_pl = getattr(self.audio_engine, "playlist", []) or []
        for idx, t in enumerate(current_pl):
            t_id = str(t.get("track_id", "")).strip()
            t_path = (t.get("file_path") or t.get("path") or "").strip()
            t_title = str(t.get("title", "")).strip().lower()
            t_artist = str(t.get("artist", "")).strip().lower()
            t_basename = os.path.basename(t_path).lower() if t_path else ""

            if target_id and t_id and target_id == t_id:
                existing_idx = idx
                break
            if target_path and t_path and (target_path == t_path or os.path.abspath(target_path) == os.path.abspath(t_path)):
                existing_idx = idx
                break
            if target_basename and t_basename and target_basename == t_basename:
                existing_idx = idx
                break
            if target_title and target_artist and t_title == target_title and t_artist == target_artist:
                existing_idx = idx
                break

        # 2. Si ya está en la cola, reproducir directamente en su índice existente
        if existing_idx != -1:
            if hasattr(self.audio_engine, "play_index"):
                self.audio_engine.play_index(existing_idx)
        else:
            # Comprobar si existe en la biblioteca global/filtrada
            fallback_list = getattr(self, '_display_tracks', None) or getattr(self, 'playlist', None) or []
            found_lib_idx = -1
            for idx, t in enumerate(fallback_list):
                t_id = str(t.get("track_id", "")).strip()
                t_path = (t.get("file_path") or t.get("path") or "").strip()
                t_title = str(t.get("title", "")).strip().lower()
                t_artist = str(t.get("artist", "")).strip().lower()
                if (target_id and t_id and target_id == t_id) or \
                   (target_path and t_path and (target_path == t_path or os.path.abspath(target_path) == os.path.abspath(t_path))) or \
                   (target_title and target_artist and t_title == target_title and t_artist == target_artist):
                    found_lib_idx = idx
                    break

            if found_lib_idx != -1 and hasattr(self.audio_engine, "set_playlist"):
                self.audio_engine.set_playlist(fallback_list, start_index=found_lib_idx, auto_play=True)
            elif hasattr(self.audio_engine, "add_track"):
                self.audio_engine.add_track(track_meta, play_now=True)
            elif hasattr(self.audio_engine, "playlist"):
                self.audio_engine.playlist.append(track_meta)
                if hasattr(self.audio_engine, "_rebuild_shuffle_indices"):
                    self.audio_engine._rebuild_shuffle_indices()
                if hasattr(self.audio_engine, "playlist_updated"):
                    self.audio_engine.playlist_updated.emit(self.audio_engine.playlist)
                if hasattr(self.audio_engine, "play_index"):
                    self.audio_engine.play_index(len(self.audio_engine.playlist) - 1)

    def _on_home_play_all_requested(self, tracks_list: list) -> None:
        if not tracks_list or not self.audio_engine:
            return
        if hasattr(self.audio_engine, "set_playlist"):
            self.audio_engine.set_playlist(tracks_list, start_index=0, auto_play=True)
        elif hasattr(self.audio_engine, "playlist"):
            self.audio_engine.playlist = list(tracks_list)
            if hasattr(self.audio_engine, "_rebuild_shuffle_indices"):
                self.audio_engine._rebuild_shuffle_indices()
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

    def set_album_art(self, pixmap: Optional[QPixmap], art_path: str = "") -> None:
        if hasattr(self, 'artwork_ekg_widget') and self.artwork_ekg_widget:
            self.artwork_ekg_widget.set_album_art(pixmap, art_path=art_path)

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
        if hasattr(self, 'np_controls_deck') and self.np_controls_deck:
            self.np_controls_deck.setStyleSheet(f"QFrame#NPControlsDeck {{ background-color: rgba(10, 14, 26, 0.72); border-radius: 22px; border: 1.5px solid rgba({r}, {g}, {b}, 0.35); }}")
        if hasattr(self, 'left_np_frame') and self.left_np_frame and self.left_np_frame is not getattr(self, 'np_controls_deck', None):
            self.left_np_frame.setStyleSheet(glass_tint_panels)
        if hasattr(self, 'right_np_frame') and self.right_np_frame and self.right_np_frame is not getattr(self, 'np_overlay_widget', None):
            self.right_np_frame.setStyleSheet(glass_tint_panels)
        if hasattr(self, 'right_queue_frame') and self.right_queue_frame:
            self.right_queue_frame.setStyleSheet(glass_tint_panels)

        # Botón de Play prominente estilo tocadiscos Hi-Fi y controles circulares de cristal
        np_play_style = f"QPushButton#PlayButton {{ background-color: #ffffff; color: {clean_hex}; border-radius: 30px; border: none; font-size: 24px; font-weight: bold; }} QPushButton#PlayButton:hover {{ background-color: #f1f5f9; }}"
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
        if hasattr(self, 'np_btn_queue') and self.np_btn_queue:
            self.np_btn_queue.setStyleSheet(np_ctrl_40_style)
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
            self.artwork_ekg_widget.set_accent_color(clean_hex, gradient_colors=self.gradient_colors)

        if hasattr(self, 'np_slider_volume') and self.np_slider_volume:
            self.np_slider_volume.set_accent_color(clean_hex, self.gradient_colors if btn_gradient_effect else [clean_hex, clean_hex])

        cur_pal = getattr(self, '_current_lyrics_palette', {}) or {}
        is_light = cur_pal.get("is_light_bg", False)
        if hasattr(self, 'np_song_artist') and self.np_song_artist:
            artist_col = cur_pal.get("artist_color", "#d0d4eb")
            self.np_song_artist.set_color(artist_col, shadow_color_str="rgba(255, 255, 255, 0.75)" if is_light else "rgba(0, 0, 0, 0.85)")

        if hasattr(self, 'lyrics_display_widget') and self.lyrics_display_widget:
            try:
                if hasattr(self, 'artwork_ekg_widget') and self.artwork_ekg_widget and self.artwork_ekg_widget.album_art:
                    lyrics_palette = extract_lyrics_theme_colors(self.artwork_ekg_widget.album_art, clean_hex)
                    self._current_lyrics_palette = lyrics_palette
                    self.lyrics_display_widget.set_cover_palette(lyrics_palette)
                self.lyrics_display_widget.set_accent_color(clean_hex)
            except Exception:
                pass

        self._apply_sort_combo_style()
        self._update_view_mode_buttons()
        self._apply_np_lyrics_visibility()



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

    def _on_playlists_data_changed(self) -> None:
        self._refresh_playlists_sidebar_ui()
        if hasattr(self, "playlists_page_view") and self.playlists_page_view:
            if hasattr(self.playlists_page_view, "refresh_playlists"):
                self.playlists_page_view.refresh_playlists()
            elif hasattr(self.playlists_page_view, "refresh"):
                self.playlists_page_view.refresh()
        if hasattr(self, "music_home_view") and self.music_home_view:
            if hasattr(self.music_home_view, "_refresh_playlists"):
                self.music_home_view._refresh_playlists()

    def _on_song_card_playlist_changed(self, is_filtered: bool = False, show_recents: bool = False) -> None:
        self.update_playlist_ui(
            self.playlist,
            self.current_index,
            is_filtered_view=is_filtered,
            show_recents=show_recents,
        )
        self._on_playlists_data_changed()

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
                self._on_playlists_data_changed()
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
                    self._on_playlists_data_changed()
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
                self._on_playlists_data_changed()
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
            audio_engine=self.audio_engine,
            on_playlist_changed=self._on_playlists_data_changed,
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

    def _load_more_library_items(self) -> None:
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

        # Obtener pista en reproducción para resaltar
        curr_track = None
        if 0 <= self.current_index < len(self.playlist):
            curr_track = self.playlist[self.current_index]

        for idx in range(current_loaded, next_count):
            track = display_tracks[idx]

            # Comprobar si esta pista está activa
            is_curr = False
            if curr_track:
                t_id = str(track.get("track_id") or "")
                c_id = str(curr_track.get("track_id") or "")
                t_path = str(track.get("file_path") or track.get("path") or "")
                c_path = str(curr_track.get("file_path") or curr_track.get("path") or "")
                if t_id and c_id and t_id == c_id:
                    is_curr = True
                elif t_path and c_path and (t_path == c_path or os.path.abspath(t_path) == os.path.abspath(c_path)):
                    is_curr = True
                elif (track.get("title") == curr_track.get("title")) and (track.get("artist") == curr_track.get("artist")):
                    is_curr = True
            elif idx == self.current_index:
                is_curr = True

            dur = int(track.get("length_sec") or track.get("duration") or 0)

            row = idx // cols
            col = idx % cols
            card = SongCardWidget(
                track_index=idx,
                title=track.get("title", "Sin título"),
                artist=track.get("artist", "Artista desconocido"),
                art_url=track.get("art_url", ""),
                duration_sec=dur,
                accent_color=self.accent_color,
                is_playing=is_curr,
                audio_engine=self.audio_engine,
                track_meta=track,
                on_playlist_changed=lambda: self._on_song_card_playlist_changed(
                    is_filtered=(getattr(self, 'active_filter_mode', 'all') != 'all'),
                    show_recents=(getattr(self, 'active_filter_mode', 'all') == 'all')
                ),
                parent=self.songs_grid_widget
            )
            card.card_clicked.connect(lambda meta, i=idx: self._on_library_card_clicked(i, meta))
            self.songs_grid_layout.addWidget(card, row, col)

        self._loaded_cards_count = next_count
        self._is_loading_more = False

    def _on_library_card_clicked(self, index: int, track_meta: dict) -> None:
        if not self.audio_engine:
            return
        display_tracks = getattr(self, '_display_tracks', [])
        if display_tracks and 0 <= index < len(display_tracks):
            engine_pl = getattr(self.audio_engine, "playlist", None)
            if engine_pl != display_tracks:
                if hasattr(self.audio_engine, "set_playlist"):
                    self.audio_engine.set_playlist(display_tracks, start_index=index, auto_play=True)
                    return
            if hasattr(self.audio_engine, "play_index"):
                self.audio_engine.play_index(index)
        else:
            self._on_home_play_track_requested(track_meta)

    def _load_more_grid_cards(self) -> None:
        self._load_more_library_items()

    def _on_sort_changed(self, index: int) -> None:
        if not hasattr(self, 'combo_sort') or not self.combo_sort:
            return
        sort_key = self.combo_sort.itemData(index)
        if sort_key and sort_key != getattr(self, 'library_sort_order', 'recent'):
            self.set_library_sort_order(str(sort_key))

    def set_library_sort_order(self, sort_key: str) -> None:
        self.library_sort_order = sort_key
        self._set_config_val("library_sort_order", sort_key)
        if self.audio_engine and hasattr(self.audio_engine, "apply_sort"):
            self.audio_engine.apply_sort(sort_key)
        else:
            self.refresh_library_views()

    def set_library_view_mode(self, mode: str) -> None:
        pass

    def _update_view_mode_buttons(self) -> None:
        pass

    def _apply_sort_combo_style(self) -> None:
        if not hasattr(self, 'combo_sort') or not self.combo_sort:
            return
        clean_accent = self.accent_color.split(';')[0].strip() if self.accent_color else "#ff1744"
        self.combo_sort.setStyleSheet(f"""
            QComboBox {{
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 6px;
                padding: 3px 8px;
                color: #e2e8f0;
                font-size: 11px;
                font-weight: 500;
                min-width: 140px;
            }}
            QComboBox:hover {{
                background-color: rgba(255, 255, 255, 0.14);
                border: 1px solid rgba(255, 255, 255, 0.25);
            }}
            QComboBox::drop-down {{
                border: none;
                width: 18px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #121624;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                selection-background-color: {clean_accent};
                selection-color: #ffffff;
                color: #e2e8f0;
                padding: 4px;
                outline: none;
            }}
        """)

    def refresh_library_views(self) -> None:
        raw = getattr(self, '_raw_playlist', None) or self.playlist
        if raw:
            is_filtered = (getattr(self, 'active_filter_mode', 'all') != 'all')
            self.update_playlist_ui(raw, self.current_index, is_filtered_view=is_filtered, show_recents=not is_filtered)

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
            self._raw_playlist = list(playlist)
        self.current_index = current_index

        sort_key = getattr(self, 'library_sort_order', 'recent')
        sorted_tracks = sort_tracks(playlist, sort_key, raw_order=getattr(self, '_raw_playlist', None))
        self._display_tracks = sorted_tracks

        if not self.isVisible():
            self._dirty = True
            return

        if self._rebuilding:
            self._dirty = True
            QTimer.singleShot(40, lambda: self.update_playlist_ui(self.playlist, self.current_index, is_filtered_view=is_filtered_view, show_recents=show_recents))
            return

        self._rebuilding = True
        self.setUpdatesEnabled(False)
        try:
            self._loaded_cards_count = 0

            while self.recents_layout.count():
                item = self.recents_layout.takeAt(0)
                w = item.widget()
                if w:
                    w.setParent(None)
                    w.deleteLater()

            while self.songs_grid_layout.count():
                item = self.songs_grid_layout.takeAt(0)
                w = item.widget()
                if w:
                    w.setParent(None)
                    w.deleteLater()

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
                            audio_engine=self.audio_engine,
                            track_meta=track,
                            on_playlist_changed=lambda: self._on_song_card_playlist_changed(
                                is_filtered=(getattr(self, 'active_filter_mode', 'all') != 'all'),
                                show_recents=True
                            ),
                            parent=self.recents_widget
                        )
                        card.card_clicked.connect(self._on_home_play_track_requested)
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

    def set_visualizer_style(self, style: str) -> None:
        if hasattr(self, 'artwork_ekg_widget') and self.artwork_ekg_widget:
            self.artwork_ekg_widget.set_visualizer_style(style)

    def set_cover_fit(self, fit: str) -> None:
        self.expanded_cover_fit = fit
        if hasattr(self, 'artwork_ekg_widget') and self.artwork_ekg_widget:
            self.artwork_ekg_widget.set_cover_fit(fit)

    def set_scrim_opacity(self, opacity: float) -> None:
        try:
            self.expanded_scrim_opacity = float(opacity)
        except Exception:
            self.expanded_scrim_opacity = 0.35
        if hasattr(self, 'artwork_ekg_widget') and self.artwork_ekg_widget:
            self.artwork_ekg_widget.set_scrim_opacity(self.expanded_scrim_opacity)

    def set_show_lyrics(self, show: bool) -> None:
        self.expanded_show_lyrics = bool(show)
        self._apply_np_lyrics_visibility()

    def _toggle_np_lyrics(self) -> None:
        self.expanded_show_lyrics = not self.expanded_show_lyrics
        if self.config and hasattr(self.config, 'set_personalization'):
            self.config.set_personalization("expanded", "expanded_show_lyrics", self.expanded_show_lyrics)
        self._apply_np_lyrics_visibility()

    def _apply_np_lyrics_visibility(self) -> None:
        if hasattr(self, 'np_btn_toggle_lyrics') and self.np_btn_toggle_lyrics:
            self.np_btn_toggle_lyrics.setChecked(self.expanded_show_lyrics)
            clean_accent = self.accent_color.split(';')[0].strip() if self.accent_color else "#ff1744"
            if self.expanded_show_lyrics:
                grad_str = _build_qlineargradient(self.gradient_colors) if (getattr(self, 'btn_gradient_effect', False) and getattr(self, 'gradient_colors', None) and len(self.gradient_colors) >= 2) else ""
                if grad_str:
                    self.np_btn_toggle_lyrics.setStyleSheet(
                        f"QPushButton#ExpandedLyricsToggleBtn {{ background: {grad_str}; border: 1.5px solid #ffffff; border-radius: 20px; color: #ffffff; font-size: 16px; font-weight: bold; }} "
                        f"QPushButton#ExpandedLyricsToggleBtn:hover {{ background: {grad_str}; border: 1.5px solid #ffffff; color: #ffffff; }} "
                        f"QPushButton#ExpandedLyricsToggleBtn:pressed {{ background: {grad_str}; border: 1.5px solid rgba(255, 255, 255, 0.70); color: #dddddd; }}"
                    )
                else:
                    self.np_btn_toggle_lyrics.setStyleSheet(
                        f"QPushButton#ExpandedLyricsToggleBtn {{ background: {clean_accent}; border: 1.5px solid #ffffff; border-radius: 20px; color: #ffffff; font-size: 16px; font-weight: bold; }} "
                        f"QPushButton#ExpandedLyricsToggleBtn:hover {{ background: #ffffff; color: #0c0e14; border: 1.5px solid #ffffff; }}"
                    )
                self.np_btn_toggle_lyrics.setToolTip("Ocultar Letras (♪)")
            else:
                self.np_btn_toggle_lyrics.setStyleSheet(
                    f"QPushButton#ExpandedLyricsToggleBtn {{ background: rgba(255, 255, 255, 0.08); border: 1.5px solid rgba(255, 255, 255, 0.18); border-radius: 20px; color: rgba(255, 255, 255, 0.65); font-size: 16px; font-weight: bold; }} "
                    f"QPushButton#ExpandedLyricsToggleBtn:hover {{ background: rgba(255, 255, 255, 0.22); border-color: {clean_accent}; color: #ffffff; }}"
                )
                self.np_btn_toggle_lyrics.setToolTip("Mostrar Letras (♪)")
        if hasattr(self, 'np_lyrics_center_container') and self.np_lyrics_center_container:
            self.np_lyrics_center_container.setVisible(self.expanded_show_lyrics)
        if hasattr(self, 'lyrics_display_widget') and self.lyrics_display_widget:
            self.lyrics_display_widget.setVisible(self.expanded_show_lyrics)
        if hasattr(self, 'np_art_spacer') and self.np_art_spacer:
            self.np_art_spacer.setVisible(not self.expanded_show_lyrics)
        if hasattr(self, 'artwork_ekg_widget') and self.artwork_ekg_widget:
            self.artwork_ekg_widget.set_show_lyrics(self.expanded_show_lyrics)

    def update_font_family(self, font_family: str) -> None:
        self.font_family = font_family or "Sans Serif"
        from ui.font_manager import apply_font_family_to_tree
        apply_font_family_to_tree(self, self.font_family)
        if hasattr(self, 'lyrics_display_widget') and self.lyrics_display_widget:
            if hasattr(self.lyrics_display_widget, 'set_font_family'):
                self.lyrics_display_widget.set_font_family(self.font_family)
        if hasattr(self, 'music_home_view') and self.music_home_view:
            apply_font_family_to_tree(self.music_home_view, self.font_family)
        if hasattr(self, 'playlists_page_view') and self.playlists_page_view:
            apply_font_family_to_tree(self.playlists_page_view, self.font_family)
        if hasattr(self, 'queue_list_widget') and self.queue_list_widget:
            apply_font_family_to_tree(self.queue_list_widget, self.font_family)

    def update_config_settings(self, config_dict: dict) -> None:
        old_inner_mode = getattr(self, 'inner_art_mode', 'auto')
        old_inner_img = getattr(self, 'custom_inner_image', '')
        self.inner_art_mode = config_dict.get("inner_art_mode", "auto")
        self.custom_inner_image = config_dict.get("custom_inner_image", "")
        if hasattr(self, 'artwork_ekg_widget') and self.artwork_ekg_widget:
            self.artwork_ekg_widget.always_play = (self.inner_art_mode == "custom_always")

        if "cover_shape" in config_dict:
            self.set_cover_shape(config_dict["cover_shape"])
        if "expanded_visualizer_style" in config_dict:
            self.set_visualizer_style(config_dict["expanded_visualizer_style"])
        if "expanded_cover_fit" in config_dict:
            self.set_cover_fit(config_dict["expanded_cover_fit"])
        if "expanded_scrim_opacity" in config_dict:
            self.set_scrim_opacity(config_dict["expanded_scrim_opacity"])
        if "expanded_show_lyrics" in config_dict:
            self.set_show_lyrics(config_dict["expanded_show_lyrics"])
        if "brand_name" in config_dict:
            self.set_brand_name(config_dict["brand_name"])
        if "font_family" in config_dict:
            self.update_font_family(config_dict["font_family"])

        # Solo refrescar el arte de reproducción si cambiaron las opciones de carátula personalizada
        if old_inner_mode != self.inner_art_mode or old_inner_img != self.custom_inner_image:
            meta = getattr(self, 'current_metadata', {}) or {}
            effective_art, media_type = resolve_now_playing_art(
                meta,
                self.custom_inner_image,
                self.inner_art_mode
            )
            pix = get_cached_pixmap(effective_art, 1200, 760) if effective_art else None
            self.artwork_ekg_widget.set_album_art(pix, art_path=effective_art)

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

        effective_art, media_type = resolve_now_playing_art(
            metadata,
            self.custom_inner_image,
            self.inner_art_mode
        )
        if hasattr(self, 'artwork_ekg_widget') and self.artwork_ekg_widget:
            self.artwork_ekg_widget.always_play = (self.inner_art_mode == "custom_always")
        pix = get_cached_pixmap(effective_art, 1200, 760) if effective_art else None
        self.apply_album_art(pix, art_path=effective_art)

        if hasattr(self, 'lyrics_display_widget') and self.lyrics_display_widget:
            try:
                self.lyrics_display_widget.load_lyrics_for_track(metadata)
            except Exception as e:
                print(f"[ExpandedPage] Error cargando letras: {e}")

    def apply_album_art(self, pixmap: Optional[QPixmap], art_path: str = "") -> None:
        """Aplica la carátula, sincroniza los colores de las letras y actualiza la luminancia de la vista."""
        if hasattr(self, 'artwork_ekg_widget') and self.artwork_ekg_widget:
            self.artwork_ekg_widget.set_album_art(pixmap, art_path=art_path)

        clean_accent = self.accent_color.split(';')[0].strip() if self.accent_color else "#ff1744"
        lyrics_palette = extract_lyrics_theme_colors(pixmap, clean_accent)
        self._current_lyrics_palette = lyrics_palette
        is_light = lyrics_palette.get("is_light_bg", False)

        if hasattr(self, 'artwork_ekg_widget') and self.artwork_ekg_widget:
            self.artwork_ekg_widget.set_is_light_bg(is_light)

        # Adaptar colores del título y artista en Now Playing
        if hasattr(self, 'np_song_title') and self.np_song_title:
            self.np_song_title.set_color(
                lyrics_palette.get("title_color", "#ffffff"),
                shadow_color_str="rgba(255, 255, 255, 0.75)" if is_light else "rgba(0, 0, 0, 0.85)"
            )
        if hasattr(self, 'np_song_artist') and self.np_song_artist:
            self.np_song_artist.set_color(
                lyrics_palette.get("artist_color", "#cbd5e1"),
                shadow_color_str="rgba(255, 255, 255, 0.75)" if is_light else "rgba(0, 0, 0, 0.85)"
            )

        if hasattr(self, 'lyrics_display_widget') and self.lyrics_display_widget:
            try:
                self.lyrics_display_widget.set_cover_palette(lyrics_palette)
            except Exception as e:
                print(f"[ExpandedPage] Error aplicando paleta de letras: {e}")

    def set_playing_status(self, is_playing: bool) -> None:
        self.artwork_ekg_widget.set_playing(is_playing)
        icon = "⏸" if is_playing else "▶"
        self.np_btn_play.setText(icon)

    def _on_lyrics_seek_requested(self, time_ms: int) -> None:
        if getattr(self, 'duration_sec', 0) > 0:
            val = int((time_ms / (self.duration_sec * 1000.0)) * 1000)
            self._last_seek_time = time.time()
            self.seek_requested.emit(max(0, min(1000, val)))

    def _on_np_slider_pressed(self) -> None:
        self.is_user_seeking = True

    def _on_np_slider_moved(self, val: int) -> None:
        total_sec = getattr(self, 'duration_sec', 0)
        if total_sec > 0:
            pos_sec = max(0, min(total_sec, int((val / 1000.0) * total_sec)))
            rem_sec = max(0, total_sec - pos_sec)
            force_h = (total_sec >= 3600)
            self.np_time_left.setText(format_time_str(pos_sec, force_h))
            self.np_time_right.setText(format_rem_time_str(rem_sec, force_h))

    def _on_np_slider_released(self) -> None:
        self.is_user_seeking = False
        self._last_seek_time = time.time()
        val = self.np_progress_bar.value()
        self.seek_requested.emit(val)

    def _on_np_vol_changed(self, val: int) -> None:
        if hasattr(self, 'np_lbl_vol_val') and self.np_lbl_vol_val:
            self.np_lbl_vol_val.setText(f"{val}%")
        if hasattr(self, 'np_btn_mute') and self.np_btn_mute:
            self.np_btn_mute.setText("🔇" if val == 0 else "🔊")
        if hasattr(self, 'np_vol_icon') and self.np_vol_icon:
            self.np_vol_icon.setText("🔇" if val == 0 else "🔊")
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
        if time.time() - getattr(self, '_last_seek_time', 0.0) < 0.4:
            return
        total_sec = length_sec if length_sec > 0 else getattr(self, 'duration_sec', 0)
        self.duration_sec = total_sec
        if total_sec > 0:
            val = int((pos_sec / total_sec) * 1000)
            self.np_progress_bar.blockSignals(True)
            self.np_progress_bar.setValue(val)
            self.np_progress_bar.blockSignals(False)

            rem_sec = max(0, total_sec - pos_sec)
            force_h = (total_sec >= 3600)
            self.np_time_left.setText(format_time_str(pos_sec, force_h))
            self.np_time_right.setText(format_rem_time_str(rem_sec, force_h))
        else:
            self.np_progress_bar.setValue(0)
            self.np_time_left.setText("0:00")
            self.np_time_right.setText("-0:00")

        if hasattr(self, 'lyrics_display_widget') and self.lyrics_display_widget:
            if time.time() - getattr(self, '_last_ms_pos_update', 0) > 1.2:
                self.lyrics_display_widget.update_position(int(pos_sec * 1000))

    def update_position_ms(self, pos_ms: int) -> None:
        """Actualiza la visualización de letras en tiempo real a nivel de milisegundos."""
        self._last_ms_pos_update = time.time()
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
        if hasattr(self, 'np_vol_icon') and self.np_vol_icon:
            self.np_vol_icon.setText("🔇" if val == 0 else "🔊")

    def update_like_status(self, is_fav: bool) -> None:
        self.is_fav_active = is_fav
        clean_hex = self.accent_color.split(';')[0].strip() if self.accent_color else "#ff1744"
        if not hasattr(self, 'np_btn_fav') or not self.np_btn_fav:
            return
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
            self.np_btn_fav.setToolTip("Favorita: Sí (Ctrl+F para quitar)")
        else:
            self.np_btn_fav.setText("♡")
            self.np_btn_fav.setStyleSheet(
                f"QPushButton {{ background: rgba(255, 255, 255, 0.08); border: 1.5px solid rgba(255, 255, 255, 0.18); border-radius: 20px; color: rgba(255, 255, 255, 0.65); font-size: 15px; font-weight: bold; }} "
                f"QPushButton:hover {{ background: rgba(255, 255, 255, 0.22); border-color: {clean_hex}; color: #ffffff; }}"
            )
            self.np_btn_fav.setToolTip("Marcar como Favorita (Ctrl+F)")

    def update_loop_status(self, status: str) -> None:
        self.current_loop_status = status
        clean_hex = self.accent_color.split(';')[0].strip() if self.accent_color else "#ff1744"
        if not hasattr(self, 'np_btn_loop') or not self.np_btn_loop:
            return
        if status in ("Track", "Playlist"):
            icon = "🔂" if status == "Track" else "↻"
            self.np_btn_loop.setText(icon)
            grad_str = _build_qlineargradient(self.gradient_colors) if (getattr(self, 'btn_gradient_effect', False) and getattr(self, 'gradient_colors', None) and len(self.gradient_colors) >= 2) else ""
            if grad_str:
                self.np_btn_loop.setStyleSheet(
                    f"QPushButton {{ background: {grad_str}; border: 1.5px solid #ffffff; border-radius: 20px; color: #ffffff; font-size: 15px; font-weight: bold; }} "
                    f"QPushButton:hover {{ background: {grad_str}; border: 1.5px solid #ffffff; color: #ffffff; }} "
                    f"QPushButton:pressed {{ background: {grad_str}; border: 1.5px solid rgba(255, 255, 255, 0.70); color: #dddddd; }}"
                )
            else:
                self.np_btn_loop.setStyleSheet(f"QPushButton {{ background-color: {clean_hex}; border: 1.5px solid #ffffff; border-radius: 20px; color: #ffffff; font-size: 15px; font-weight: bold; }}")
            self.np_btn_loop.setToolTip(f"Modo Bucle: {'Pista Actual' if status == 'Track' else 'Lista Completa'}")
        else:
            self.np_btn_loop.setText("↻")
            self.np_btn_loop.setStyleSheet(
                f"QPushButton {{ background: rgba(255, 255, 255, 0.08); border: 1.5px solid rgba(255, 255, 255, 0.18); border-radius: 20px; color: rgba(255, 255, 255, 0.65); font-size: 15px; font-weight: bold; }} "
                f"QPushButton:hover {{ background: rgba(255, 255, 255, 0.22); border-color: {clean_hex}; color: #ffffff; }}"
            )
            self.np_btn_loop.setToolTip("Modo Bucle: Desactivado")

    def update_shuffle_status(self, enabled: bool) -> None:
        self.is_shuffle_active = bool(enabled)
        clean_hex = self.accent_color.split(';')[0].strip() if self.accent_color else "#ff1744"
        if not hasattr(self, 'np_btn_shuffle') or not self.np_btn_shuffle:
            return
        if self.is_shuffle_active:
            self.np_btn_shuffle.setText("🔀")
            grad_str = _build_qlineargradient(self.gradient_colors) if (getattr(self, 'btn_gradient_effect', False) and getattr(self, 'gradient_colors', None) and len(self.gradient_colors) >= 2) else ""
            if grad_str:
                self.np_btn_shuffle.setStyleSheet(
                    f"QPushButton {{ background: {grad_str}; border: 2px solid #ffffff; border-radius: 20px; color: #ffffff; font-size: 15px; font-weight: bold; }} "
                    f"QPushButton:hover {{ background: {grad_str}; border: 2px solid #ffffff; color: #ffffff; }} "
                    f"QPushButton:pressed {{ background: {grad_str}; border: 2px solid rgba(255, 255, 255, 0.70); color: #dddddd; }}"
                )
            else:
                self.np_btn_shuffle.setStyleSheet(
                    f"QPushButton {{ background-color: {clean_hex}; border: 2px solid #ffffff; border-radius: 20px; color: #ffffff; font-size: 15px; font-weight: bold; }} "
                    f"QPushButton:hover {{ background-color: {clean_hex}; border: 2px solid #ffffff; color: #ffffff; }}"
                )
            self.np_btn_shuffle.setToolTip("Modo Aleatorio: Activado")
        else:
            self.np_btn_shuffle.setText("⇄")
            self.np_btn_shuffle.setStyleSheet(
                f"QPushButton {{ background: rgba(255, 255, 255, 0.08); border: 1.5px solid rgba(255, 255, 255, 0.18); border-radius: 20px; color: rgba(255, 255, 255, 0.65); font-size: 15px; font-weight: bold; }} "
                f"QPushButton:hover {{ background: rgba(255, 255, 255, 0.22); border-color: {clean_hex}; color: #ffffff; }}"
            )
            self.np_btn_shuffle.setToolTip("Modo Aleatorio: Desactivado")

    def _on_lib_search_text_changed(self, query: str) -> None:
        q = query.strip().lower()
        if hasattr(self, 'btn_lib_search_clear'):
            self.btn_lib_search_clear.setVisible(bool(q))

        if not q:
            total_songs = len(self.playlist)
            self.lbl_songs_title.setText(f"📚 Todas tus canciones ({total_songs})")
            self.update_playlist_ui(self.playlist, self.current_index, is_filtered_view=False, show_recents=False)
            return

        filtered = []
        for track in self.playlist:
            t_title = str(track.get("title", "")).lower()
            t_artist = str(track.get("artist", "")).lower()
            t_album = str(track.get("album", "")).lower()
            if q in t_title or q in t_artist or q in t_album:
                filtered.append(track)

        self.lbl_songs_title.setText(f"🔍 Resultados de búsqueda ({len(filtered)})")
        self.update_playlist_ui(filtered, self.current_index, is_filtered_view=True, show_recents=False)

    def _on_nav_library_clicked(self) -> None:
        self.active_filter_mode = "library"
        self.active_nav_button = self.btn_nav_albums
        self._highlight_nav_button(self.btn_nav_albums)
        if hasattr(self, "page_library") and self.page_library:
            self.center_stack.setCurrentWidget(self.page_library)

        self.lbl_recents_title.setVisible(False)
        self.recents_scroll.setVisible(False)
        if hasattr(self, 'lib_search_input') and self.lib_search_input.text().strip():
            self._on_lib_search_text_changed(self.lib_search_input.text())
        else:
            total_songs = len(self.playlist)
            self.lbl_songs_title.setText(f"📚 Todas tus canciones ({total_songs})")
            self.update_playlist_ui(self.playlist, self.current_index, is_filtered_view=False, show_recents=False)

    def _on_queue_item_double_clicked(self, item: QListWidgetItem) -> None:
        idx = item.data(Qt.ItemDataRole.UserRole)
        if idx is not None:
            self.play_track_requested.emit(idx)
