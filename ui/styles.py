import os
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QPainterPath

HEART_ICON_PATH = os.path.expanduser("~/.config/custom-music-player/heart_knob.png")
CIRCLE_ICON_PATH = os.path.expanduser("~/.config/custom-music-player/circle_knob.png")

def get_main_style(accent_hex: str = "#ff1744") -> str:
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
        background-color: {accent_hex};
        color: #ffffff;
        border-radius: 22px;
        font-size: 18px;
        border: none;
    }}
    QPushButton#PlayButton:hover {{
        background-color: {hover_hex};
        color: #ffffff;
    }}
    QPushButton#PlayButton:pressed {{
        background-color: {accent_hex};
        color: #dddddd;
    }}

    /* Slider de Reproducción con Tirador en forma de Corazón ♥ */
    QSlider#ProgressBar::groove:horizontal {{
        border: none;
        height: 6px;
        background: #22222a;
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
        border: none;
        height: 5px;
        background: #22222a;
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
