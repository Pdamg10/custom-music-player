import os
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QPainterPath

HEART_ICON_PATH = os.path.expanduser("~/.config/custom-music-player/heart_knob.png")
CIRCLE_ICON_PATH = os.path.expanduser("~/.config/custom-music-player/circle_knob.png")

# =====================================================================
# DESIGN SYSTEM TOKENS (Radii, Dimensions & Spacing)
# =====================================================================
WINDOW_RADIUS = 22
CARD_RADIUS = 14
BUTTON_RADIUS = 12
ARTWORK_RADIUS = 14
CONTROL_RADIUS = 16

NORMAL_WIDTH = 350
NORMAL_HEIGHT = 430

COMPACT_WIDTH = 640
COMPACT_HEIGHT = 260
COMPACT_ART_SIZE = 220

EXPANDED_MIN_WIDTH = 900
EXPANDED_MIN_HEIGHT = 600

from ui.color_extractor import get_contrasting_text_color

def _build_qlineargradient(colors: list) -> str:
    if not colors or not isinstance(colors, list):
        return ""
    clean_colors = [c for c in colors if c and isinstance(c, str)]
    if len(clean_colors) == 0:
        return ""
    if len(clean_colors) == 1:
        return f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {clean_colors[0]}, stop:1 {clean_colors[0]})"

    n = len(clean_colors)
    stops = []
    for i, col in enumerate(clean_colors):
        pos = i / max(1, n - 1)
        stops.append(f"stop:{pos:.2f} {col}")

    return f"qlineargradient(x1:0, y1:0, x2:1, y2:1, {', '.join(stops)})"

def build_button_style(
    accent_hex: str = "#ff1744",
    btn_gradient_effect: bool = False,
    gradient_colors: list = None,
    border_radius: int = 14,
    font_size: int = 13,
    padding: str = "6px 12px",
    border: str = "none"
) -> str:
    grad_str = _build_qlineargradient(gradient_colors) if (btn_gradient_effect and gradient_colors and len(gradient_colors) >= 2) else ""
    text_contrast = get_contrasting_text_color(gradient_colors[0] if (btn_gradient_effect and gradient_colors) else accent_hex)

    if btn_gradient_effect and grad_str:
        return (
            f"QPushButton {{ background: {grad_str}; color: {text_contrast}; border-radius: {border_radius}px; font-size: {font_size}px; font-weight: bold; padding: {padding}; border: {border}; }} "
            f"QPushButton:hover {{ background: {grad_str}; border: 1.5px solid #ffffff; color: #ffffff; }} "
            f"QPushButton:pressed {{ background: {grad_str}; border: 1.5px solid rgba(255, 255, 255, 0.70); color: #dddddd; }}"
        )
    else:
        return (
            f"QPushButton {{ background-color: {accent_hex}; color: {text_contrast}; border-radius: {border_radius}px; font-size: {font_size}px; font-weight: bold; padding: {padding}; border: {border}; }} "
            f"QPushButton:hover {{ background-color: {accent_hex}; opacity: 0.88; color: #ffffff; }} "
            f"QPushButton:pressed {{ background-color: {accent_hex}; opacity: 0.75; color: #dddddd; }}"
        )

def build_mode_pill_style(
    is_active: bool,
    accent_hex: str = "#ff1744",
    btn_gradient_effect: bool = False,
    gradient_colors: list = None,
    border_radius: int = 14,
    font_size: int = 11,
    padding: str = "4px 12px"
) -> str:
    clean_hex = accent_hex.split(';')[0].strip() if accent_hex else "#ff1744"
    if is_active:
        grad_str = _build_qlineargradient(gradient_colors) if (btn_gradient_effect and gradient_colors and len(gradient_colors) >= 2) else ""
        text_contrast = get_contrasting_text_color(gradient_colors[0] if (btn_gradient_effect and gradient_colors) else clean_hex)
        if btn_gradient_effect and grad_str:
            return (
                f"QPushButton {{ background: {grad_str}; color: {text_contrast}; border-radius: {border_radius}px; font-size: {font_size}px; font-weight: bold; padding: {padding}; border: 1.5px solid #ffffff; }} "
                f"QPushButton:hover {{ border: 2px solid #ffffff; color: #ffffff; }} "
                f"QPushButton:pressed {{ border: 1.5px solid rgba(255, 255, 255, 0.70); color: #dddddd; }}"
            )
        else:
            return (
                f"QPushButton {{ background-color: {clean_hex}; color: {text_contrast}; border-radius: {border_radius}px; font-size: {font_size}px; font-weight: bold; padding: {padding}; border: 1.5px solid #ffffff; }} "
                f"QPushButton:hover {{ background-color: {clean_hex}; opacity: 0.92; color: #ffffff; }} "
                f"QPushButton:pressed {{ background-color: {clean_hex}; opacity: 0.80; color: #dddddd; }}"
            )
    else:
        return (
            f"QPushButton {{ background-color: rgba(25, 28, 44, 0.75); color: #cbd5e1; border-radius: {border_radius}px; font-size: {font_size}px; font-weight: bold; padding: {padding}; border: 1px solid rgba(255, 255, 255, 0.15); }} "
            f"QPushButton:hover {{ background-color: rgba(255, 255, 255, 0.18); color: #ffffff; border: 1px solid rgba(255, 255, 255, 0.35); }} "
            f"QPushButton:pressed {{ background-color: rgba(255, 255, 255, 0.28); color: #ffffff; }}"
        )

def get_main_style(accent_hex: str = "#ff1744", btn_gradient_effect: bool = False, gradient_colors: list = None) -> str:
    try:
        from PyQt6.QtWidgets import QApplication
        if QApplication.instance() is not None:
            os.makedirs(os.path.dirname(HEART_ICON_PATH), exist_ok=True)
            
            accent_color = QColor(accent_hex)
            
            # 1. Generar tirador de corazón para la barra de reproducción
            pix = QPixmap(18, 18)
            pix.fill(Qt.GlobalColor.transparent)
            p = QPainter(pix)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            path = QPainterPath()
            path.moveTo(9, 15.5)
            path.cubicTo(1.5, 10, 0.5, 4.5, 4.5, 2.5)
            path.cubicTo(7.5, 1.0, 9, 3.8, 9, 3.8)
            path.cubicTo(9, 3.8, 10.5, 1.0, 13.5, 2.5)
            path.cubicTo(17.5, 4.5, 16.5, 10, 9, 15.5)
            
            p.setBrush(accent_color)
            p.setPen(QPen(QColor("#ffffff"), 1.2))
            p.drawPath(path)
            p.end()
            pix.save(HEART_ICON_PATH, "PNG")

            # 2. Generar tirador circular perfecto para la barra de volumen
            pix_c = QPixmap(16, 16)
            pix_c.fill(Qt.GlobalColor.transparent)
            p_c = QPainter(pix_c)
            p_c.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            p_c.setBrush(QColor("#ffffff"))
            p_c.setPen(QPen(accent_color, 2.0))
            p_c.drawEllipse(1, 1, 13, 13)
            p_c.end()
            pix_c.save(CIRCLE_ICON_PATH, "PNG")
    except Exception as e:
        print(f"[Styles] Error generando iconos de tiradores: {e}")

    accent_qcol = QColor(accent_hex)
    h, s, v, a = accent_qcol.getHsv()
    hover_qcol = QColor.fromHsv(h if h >= 0 else 0, max(0, s - 30), min(255, v + 30))
    hover_hex = hover_qcol.name()

    text_contrast = get_contrasting_text_color(accent_hex)

    grad_str = _build_qlineargradient(gradient_colors) if (btn_gradient_effect and gradient_colors and len(gradient_colors) >= 2) else ""

    if btn_gradient_effect and grad_str:
        c0 = gradient_colors[0]
        play_bg_style = f"background: {grad_str};"
        play_hover_style = f"background: {grad_str}; border: 1.5px solid #ffffff;"
        play_pressed_style = f"background: {grad_str}; border: 1px solid rgba(255, 255, 255, 0.7);"
        circle_active_style = f"background: {grad_str}; border: 1.5px solid {accent_hex};"
        text_contrast = get_contrasting_text_color(c0)
    else:
        play_bg_style = f"background-color: {accent_hex};"
        play_hover_style = f"background-color: {hover_hex};"
        play_pressed_style = f"background-color: {accent_hex};"
        circle_active_style = f"background-color: {accent_hex}; border: 1.5px solid {accent_hex};"

    return f"""
    QWidget#CentralContainer {{
        background-color: transparent;
        color: #ffffff;
        border-radius: 22px;
        border: none;
    }}
    QLabel {{
        border: none;
        background: transparent;
        color: #ffffff;
    }}
    QLabel#BadgeLabel {{
        color: {accent_hex};
        font-weight: bold;
        font-size: 13px;
        font-family: 'Sans Serif', 'Inter', sans-serif;
    }}
    QLabel#ArtistLabel {{
        color: {hover_hex};
    }}
    QLabel#ArtScreen {{
        background-color: #050508;
        border: 2px solid {accent_hex};
        border-radius: 18px;
        color: {accent_hex};
    }}
    QPushButton {{
        background-color: transparent;
        border: none;
        font-size: 16px;
        color: {accent_hex};
        font-weight: bold;
    }}
    QPushButton:hover {{
        color: #ffffff;
    }}
    QPushButton:pressed {{
        color: {hover_hex};
    }}
    QPushButton#PlayButton {{
        {play_bg_style}
        color: {text_contrast};
        border-radius: 22px;
        font-size: 18px;
        border: none;
    }}
    QPushButton#PlayButton:hover {{
        {play_hover_style}
        color: #ffffff;
    }}
    QPushButton#PlayButton:pressed {{
        {play_pressed_style}
        color: #dddddd;
    }}

    /* Estilo de Botones Circulares Minimalistas (Basado en referencia visual) */
    QPushButton.CircleControl {{
        background-color: rgba(255, 255, 255, 0.06);
        border: 1.5px solid rgba(255, 255, 255, 0.25);
        border-radius: 18px;
        color: #ffffff;
        font-size: 13px;
        font-weight: bold;
    }}
    QPushButton.CircleControl:hover {{
        background-color: rgba(255, 255, 255, 0.18);
        border-color: {accent_hex};
        color: {accent_hex};
    }}
    QPushButton.CircleControl:pressed {{
        background-color: {accent_hex};
        color: #ffffff;
    }}
    QPushButton.CircleControlActive {{
        {circle_active_style}
        border-radius: 18px;
        color: {text_contrast};
        font-size: 13px;
        font-weight: bold;
    }}

    /* Slider de Reproducción con Tirador en forma de Corazón ♥ */
    QSlider#ProgressBar::groove:horizontal {{
        border: 1px solid rgba(255, 255, 255, 0.25);
        height: 6px;
        background: rgba(15, 17, 26, 0.85);
        border-radius: 3px;
    }}
    QSlider#ProgressBar::sub-page:horizontal {{
        background: {accent_hex};
        border-radius: 3px;
    }}
    QSlider#ProgressBar::handle:horizontal {{
        image: url("{HEART_ICON_PATH}");
        width: 18px;
        height: 18px;
        margin: -6px 0;
    }}

    /* Slider de Volumen con Tirador Circular Perfecto */
    QSlider#VolumeSlider::groove:horizontal {{
        border: 1px solid rgba(255, 255, 255, 0.25);
        height: 5px;
        background: rgba(15, 17, 26, 0.85);
        border-radius: 2px;
    }}
    QSlider#VolumeSlider::sub-page:horizontal {{
        background: {accent_hex};
        border-radius: 2px;
    }}
    QSlider#VolumeSlider::handle:horizontal {{
        image: url("{CIRCLE_ICON_PATH}");
        width: 16px;
        height: 16px;
        margin: -5px 0;
    }}

    /* Barras de Desplazamiento (Scrollbars) Laterales de Alto Contraste */
    QScrollBar:vertical {{
        background: rgba(10, 12, 22, 0.55);
        width: 10px;
        margin: 2px 2px 2px 2px;
        border-radius: 5px;
        border: 1px solid rgba(255, 255, 255, 0.12);
    }}
    QScrollBar::handle:vertical {{
        background: rgba(255, 255, 255, 0.40);
        border: 1px solid {accent_hex};
        min-height: 25px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {accent_hex};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
        background: transparent;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: transparent;
    }}

    QScrollBar:horizontal {{
        background: rgba(10, 12, 22, 0.55);
        height: 10px;
        margin: 2px 2px 2px 2px;
        border-radius: 5px;
        border: 1px solid rgba(255, 255, 255, 0.12);
    }}
    QScrollBar::handle:horizontal {{
        background: rgba(255, 255, 255, 0.40);
        border: 1px solid {accent_hex};
        min-width: 25px;
        border-radius: 4px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {accent_hex};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
        background: transparent;
    }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
        background: transparent;
    }}

    QMenu {{
        background-color: #0c0c10;
        color: #ffffff;
        border: 2px solid {accent_hex};
        border-radius: 12px;
        padding: 6px;
    }}
    QMenu::item {{
        padding: 6px 18px;
        border-radius: 6px;
    }}
    QMenu::item:selected {{
        background-color: {accent_hex};
        color: #ffffff;
    }}
"""

MAIN_STYLE = get_main_style()
