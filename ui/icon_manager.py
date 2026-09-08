"""
ui/icon_manager.py - Gestor centralizado de iconos vectoriales/PNG para Custom Music Player.

Carga los iconos PNG desde assets/icons/, aplica tintado dinámico en memoria mediante
QPainter (DestinationIn) según el color de acento o contraste requerido, gestiona caché
y los asocia a QPushButtons o QActions.
"""

import os
import sys
from typing import Dict, Optional, Tuple, Union

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QPushButton

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ICONS_DIR = os.path.join(BASE_DIR, "assets", "icons")

ICON_FILE_MAP: Dict[str, str] = {
    # Reproducción y Navegación
    "play": "jugar.png",
    "pause": "pausa.png",
    "prev": "atras.png",
    "next": "siguiente.png",
    "rewind": "rebobinar.png",
    "fast_forward": "avance-rapido.png",
    # Modos de reproducción
    "shuffle": "barajar.png",
    "repeat": "repetir.png",
    "repeat_one": "repita-una-vez.png",
    # Favoritos y Menú
    "favorite": "amor.png",
    "menu": "menu.png",
    "playlist": "lista-de-reproduccion.png",
    "add_playlist": "anadir-lista.png",
    "music": "musica.png",
    # Audio y Volumen
    "mute_x": "mudo.png",
    "mute_slash": "silencio.png",
    "mute": "mudo.png",
    "volume_high": "volumen (1).png",
    "volume_mid": "volumen.png",
    "volume_low": "bajar-volumen.png",
    "volume": "volumen (1).png",
}

_raw_cache: Dict[str, QPixmap] = {}
_tinted_cache: Dict[Tuple[str, str, int], QIcon] = {}
_pixmap_cache: Dict[Tuple[str, str, int], QPixmap] = {}


import re


def parse_color(color_val: Union[str, QColor]) -> QColor:
    """Parsea de forma robusta colores en formato QColor, hex (#RRGGBB o #RRGGBBAA), y css rgb/rgba."""
    if isinstance(color_val, QColor):
        return color_val
    s = str(color_val).split(';')[0].strip()
    m = re.match(r'rgba?\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*([\d\.]+))?\s*\)', s, re.IGNORECASE)
    if m:
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        a = float(m.group(4)) if m.group(4) is not None else 1.0
        return QColor(r, g, b, int(a * 255 if a <= 1.0 else a))
    qc = QColor(s)
    if not qc.isValid():
        return QColor("#ffffff")
    return qc


def get_icon_path(name: str) -> str:
    """Resuelve la ruta absoluta de un icono dado su alias o nombre de archivo."""
    filename = ICON_FILE_MAP.get(name, name if name.endswith(".png") else f"{name}.png")
    return os.path.join(ICONS_DIR, filename)


def get_volume_icon_name(volume: float, is_muted: bool = False) -> str:
    """Retorna el alias del icono correspondiente al nivel de volumen actual."""
    if is_muted or volume <= 0.01:
        return "mute"
    if volume < 0.5:
        return "volume_low"
    return "volume_high"


def get_tinted_pixmap(name: str, color: Union[str, QColor] = "#ffffff", size: int = 24) -> QPixmap:
    """Genera un QPixmap tintado del icono especificado con el color y tamaño deseados."""
    qc = parse_color(color)
    cache_key = (name, f"{qc.red()},{qc.green()},{qc.blue()},{qc.alpha()}", size)
    if cache_key in _pixmap_cache:
        return _pixmap_cache[cache_key]

    path = get_icon_path(name)
    if not os.path.exists(path):
        return QPixmap()

    if path not in _raw_cache:
        _raw_cache[path] = QPixmap(path)

    raw_pix = _raw_cache[path]
    if raw_pix.isNull():
        return QPixmap()

    scaled_pix = raw_pix.scaled(
        size, size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation
    )

    tinted = QPixmap(scaled_pix.size())
    tinted.fill(Qt.GlobalColor.transparent)

    p = QPainter(tinted)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.fillRect(tinted.rect(), qc)
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
    p.drawPixmap(0, 0, scaled_pix)
    p.end()

    _pixmap_cache[cache_key] = tinted
    return tinted


def get_tinted_icon(name: str, color: Union[str, QColor] = "#ffffff", size: int = 24) -> QIcon:
    """Retorna un QIcon coloreado con el color indicado, escalado y cacheado."""
    qc = parse_color(color)
    cache_key = (name, f"{qc.red()},{qc.green()},{qc.blue()},{qc.alpha()}", size)
    if cache_key in _tinted_cache:
        return _tinted_cache[cache_key]

    pix = get_tinted_pixmap(name, color=qc, size=size)
    if pix.isNull():
        return QIcon()

    icon = QIcon(pix)
    _tinted_cache[cache_key] = icon
    return icon


def set_button_icon(btn: Optional[QPushButton], name: str, color: Union[str, QColor] = "#ffffff", size: int = 18) -> None:
    """Configura el icono tintado en un QPushButton y limpia su texto para evitar solapamiento."""
    if btn is None:
        return
    icon = get_tinted_icon(name, color=color, size=size)
    btn.setIcon(icon)
    btn.setIconSize(QSize(size, size))
    btn.setText("")
