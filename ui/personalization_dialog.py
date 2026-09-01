import os
import urllib.parse
from copy import deepcopy
from typing import List, Optional, Dict, Any
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPoint, QStandardPaths
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QBrush, QPen, QFont, QPixmap
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QRadioButton, QButtonGroup, QFrame, QScrollArea, QWidget, QSizePolicy,
    QColorDialog, QFileDialog, QCheckBox, QComboBox, QLineEdit, QMessageBox, QApplication
)

from config_manager import get_config_manager
from ui.color_extractor import extract_vibrant_accent_color, get_contrasting_text_color, extract_dominant_gradient_colors
from ui.image_cache import get_cached_pixmap


class GradientPreviewWidget(QWidget):
    """Widget de previsualización en vivo del botón con degradado o color sólido."""
    def __init__(self, colors: List[str], btn_gradient: bool = False, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.colors = colors
        self.btn_gradient = btn_gradient
        self.setFixedHeight(68)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_colors(self, colors: List[str], btn_gradient: bool = False) -> None:
        self.colors = colors
        self.btn_gradient = btn_gradient
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        w, h = float(rect.width()), float(rect.height())

        # Fondo del recuadro de previsualización (Gris oscuro cristal)
        p.setPen(QPen(QColor("rgba(255, 255, 255, 0.15)"), 1.2))
        p.setBrush(QBrush(QColor("#0e101a")))
        p.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), 12.0, 12.0)

        # Muestra de Botón en el centro de la previsualización
        btn_w, btn_h = min(220.0, w - 40.0), 34.0
        btn_x, btn_y = (w - btn_w) / 2.0, (h - btn_h) / 2.0
        btn_rect = QRectF(btn_x, btn_y, btn_w, btn_h)

        if self.btn_gradient and self.colors and len(self.colors) >= 2:
            b_grad = QLinearGradient(btn_x, btn_y, btn_x + btn_w, btn_y + btn_h)
            count = len(self.colors)
            for idx, hex_c in enumerate(self.colors):
                pos = idx / max(1, count - 1)
                b_grad.setColorAt(pos, QColor(hex_c))
            p.setBrush(QBrush(b_grad))
            text_c = get_contrasting_text_color(self.colors[0])
            p.setPen(QPen(QColor("#ffffff"), 1.2))
        else:
            accent = self.colors[0] if self.colors else "#ff1744"
            p.setBrush(QBrush(QColor(accent)))
            text_c = get_contrasting_text_color(accent)
            p.setPen(QPen(QColor("#ffffff"), 1.2))

        p.drawRoundedRect(btn_rect, 17.0, 17.0)
        p.setPen(QPen(QColor(text_c)))
        p.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        p.drawText(btn_rect, Qt.AlignmentFlag.AlignCenter, " Botón Ejemplo ")

        p.end()


class PersonalizationDialog(QDialog):
    """Ventana emergente de personalización organizada en apartados claros para todos los modos."""
    settings_saved = pyqtSignal(dict, str)

    PRESETS = [
        ("💗 APT. (Rosa & Negro)", ["#ff4081", "#8e24aa", "#14070e"]),
        ("🌌 Aurora Boreal", ["#00e5ff", "#7c4dff", "#0c051a"]),
        ("🔥 Sunset Neón", ["#ff9100", "#ff1744", "#1a080c"]),
        ("🟢 Esmeralda Ciberpunk", ["#00e676", "#00838f", "#04140d"]),
        ("🟣 Vía Láctea", ["#e040fb", "#311b92", "#080512"])
    ]

    QUICK_PALETTE = [
        "#ff1744", "#00e5ff", "#e040fb", "#00e676", "#ff9100", "#ff4081",
        "#7c4dff", "#ffea00", "#00b0ff", "#76ff03", "#f50057", "#651fff"
    ]

    def __init__(self, current_config: dict, mode: str = "normal", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.config_manager = get_config_manager()
        self.per_mode_configs: Dict[str, Dict[str, Any]] = {
            "normal": deepcopy(self.config_manager.get_personalization("normal")),
            "compact": deepcopy(self.config_manager.get_personalization("compact")),
            "expanded": deepcopy(self.config_manager.get_personalization("expanded")),
        }
        self.mode = "normal" if mode in ("normal", "small", None) else mode
        if current_config and isinstance(current_config, dict):
            self.per_mode_configs[self.mode].update(deepcopy(current_config))

        self.mode_label = {
            "normal": "Modo Pequeño",
            "compact": "Modo Compacto",
            "expanded": "Modo Expandido"
        }.get(self.mode, "Modo Pequeño")

        self.setWindowTitle(f"⚙️ Personalización — {self.mode_label}")
        self.setMinimumSize(640, 540)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            w = min(720, max(640, int(avail.width() * 0.55)))
            h = min(820, max(580, int(avail.height() * 0.85)))
            self.resize(w, h)
        else:
            self.resize(680, 720)

        self.cfg = dict(self.per_mode_configs[self.mode])

        self.background_type = self.cfg.get("background_type", "gradient")
        self.theme_mode = self.cfg.get("theme_mode", "gradient_auto")
        self.button_color_source = self.cfg.get("button_color_source", "wallpaper" if self.background_type == "image" else "gradient")
        self.btn_gradient_effect = self.cfg.get("btn_gradient_effect", True)
        self.auto_extract_wallpaper_color = self.cfg.get("auto_extract_wallpaper_color", True)

        self.manual_colors = list(self.cfg.get("manual_gradient_colors", ["#ff1744", "#7b1fa2", "#0c0c10"]))
        self.solid_accent = self.cfg.get("accent_color", "#ff1744")
        self.auto_colors = list(self.cfg.get("auto_gradient_colors", ["#2b0b10", "#180718", "#08060c"]))
        self.wallpaper_gradient_colors = list(self.cfg.get("wallpaper_gradient_colors", ["#ff1744", "#7b1fa2"]))
        self.custom_btn_gradient_colors = list(self.cfg.get("custom_btn_gradient_colors", ["#ff1744", "#00e5ff", "#e040fb"]))
        self.custom_button_swatches = list(self.cfg.get("custom_button_swatches", ["#ff1744", "#00e5ff", "#e040fb", "#00e676", "#ff9100", "#ff4081"]))
        
        self.active_gradient_stop_index: int = 0
        self.active_manual_stop_index: int = 0
        self._last_highlight_accent: Optional[str] = None

        self.bg_image_path = self.cfg.get("background_image", "")
        self.bg_folder_path = self.cfg.get("bg_folder", "")
        self.bg_theme_colors = dict(self.cfg.get("bg_theme_colors", {}))
        self.slideshow_enabled = self.cfg.get("bg_slideshow_enabled", True)
        self.aspect_mode = self.cfg.get("bg_aspect_mode", "stretch")

        self.inner_art_mode = self.cfg.get("inner_art_mode", "auto")
        self.custom_inner_image = self.cfg.get("custom_inner_image", "")
        self.cover_shape = self.cfg.get("cover_shape", "rounded")
        self.expanded_visualizer_style = self.cfg.get("expanded_visualizer_style", "radial_waves")
        self.stays_on_top = self.cfg.get("stays_on_top", False)
        self.brand_name = self.cfg.get("brand_name", "RED WORLD")
        self.font_family = self.cfg.get("font_family", "Sans Serif")
        self.custom_font_path = self.cfg.get("custom_font_path", "")

        self.init_ui()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, "_drag_pos"):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def _build_dialog_stylesheet(self, font_family: str) -> str:
        clean_font = (font_family or "Sans Serif").strip() or "Sans Serif"
        return f"""
            QDialog {{
                background: transparent;
                color: #ffffff;
                font-family: '{clean_font}', 'Sans Serif', sans-serif;
            }}
            QLabel {{
                color: #ffffff;
                font-family: '{clean_font}', 'Sans Serif', sans-serif;
            }}
            QRadioButton, QCheckBox {{
                color: #ffffff;
                font-weight: bold;
                font-size: 12px;
                spacing: 10px;
                padding-top: 3px;
                padding-bottom: 3px;
                font-family: '{clean_font}', 'Sans Serif', sans-serif;
            }}
            QRadioButton::indicator, QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 2px solid #ff1744;
            }}
            QRadioButton::indicator {{
                border-radius: 8px;
            }}
            QRadioButton::indicator:checked, QCheckBox::indicator:checked {{
                background-color: #ff1744;
            }}
            QPushButton {{
                background-color: #1a1c29;
                color: #ffffff;
                border: 1px solid #33364d;
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 12px;
                font-family: '{clean_font}', 'Sans Serif', sans-serif;
            }}
            QPushButton:hover {{
                background-color: #26293d;
                border-color: #52577a;
            }}
            QComboBox {{
                background-color: #1a1c29;
                color: #ffffff;
                border: 1px solid #33364d;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-family: '{clean_font}', 'Sans Serif', sans-serif;
            }}
            QComboBox QAbstractItemView {{
                background-color: #131522;
                color: #ffffff;
                selection-background-color: #ff1744;
                font-family: '{clean_font}', 'Sans Serif', sans-serif;
            }}
        """

    def init_ui(self) -> None:
        clean_accent = (self.solid_accent.split(';')[0].strip() if hasattr(self, 'solid_accent') and self.solid_accent else "#ff1744") or "#ff1744"
        clean_font = getattr(self, 'font_family', 'Sans Serif') or 'Sans Serif'

        self.setStyleSheet(self._build_dialog_stylesheet(clean_font))

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        self.frame_card = QFrame(self)
        self.frame_card.setObjectName("PersonalizationMainCard")
        self.frame_card.setStyleSheet(f"""
            QFrame#PersonalizationMainCard {{
                background-color: rgba(13, 17, 29, 0.96);
                border: 1.5px solid {clean_accent};
                border-radius: 20px;
            }}
        """)
        f_layout = QVBoxLayout(self.frame_card)
        f_layout.setContentsMargins(18, 16, 18, 16)
        f_layout.setSpacing(12)

        # Encabezado elegante con icono, título, badge de modo y botón cerrar ×
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        lbl_icon = QLabel("🎨", self.frame_card)
        lbl_icon.setFont(QFont("Sans Serif", 14))
        lbl_icon.setStyleSheet("border: none; background: transparent;")
        header_layout.addWidget(lbl_icon)

        lbl_title = QLabel("Personalización", self.frame_card)
        lbl_title.setFont(QFont("Sans Serif", 13, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #ffffff; border: none; background: transparent;")
        header_layout.addWidget(lbl_title)

        self.lbl_mode_badge = QLabel(self.mode_label, self.frame_card)
        self.lbl_mode_badge.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        self.lbl_mode_badge.setStyleSheet("""
            color: rgba(255, 255, 255, 0.85);
            background-color: rgba(255, 255, 255, 0.08);
            border-radius: 10px;
            padding: 2px 10px;
            border: 1px solid rgba(255, 255, 255, 0.15);
        """)
        header_layout.addWidget(self.lbl_mode_badge)

        header_layout.addStretch(1)

        btn_close = QPushButton("✕", self.frame_card)
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
        header_layout.addWidget(btn_close)
        f_layout.addLayout(header_layout)

        # Barra de Selección de Modo (Personalización 100% Independiente por Modo)
        mode_select_layout = QHBoxLayout()
        mode_select_layout.setSpacing(10)

        self.btn_mode_tab_normal = QPushButton("▣  Modo Pequeño", self.frame_card)
        self.btn_mode_tab_compact = QPushButton("▤  Modo Compacto", self.frame_card)
        self.btn_mode_tab_expanded = QPushButton("▦  Modo Expandido", self.frame_card)

        for btn in (self.btn_mode_tab_normal, self.btn_mode_tab_compact, self.btn_mode_tab_expanded):
            btn.setFixedHeight(34)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_mode_tab_normal.clicked.connect(lambda: self._switch_editing_mode("normal"))
        self.btn_mode_tab_compact.clicked.connect(lambda: self._switch_editing_mode("compact"))
        self.btn_mode_tab_expanded.clicked.connect(lambda: self._switch_editing_mode("expanded"))

        mode_select_layout.addWidget(self.btn_mode_tab_normal)
        mode_select_layout.addWidget(self.btn_mode_tab_compact)
        mode_select_layout.addWidget(self.btn_mode_tab_expanded)
        f_layout.addLayout(mode_select_layout)

        # Área de Scroll Principal
        scroll = QScrollArea(self.frame_card)
        scroll.setWidgetResizable(True)
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                width: 6px;
                background: transparent;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.20);
                min-height: 25px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.40);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        scroll_content = QWidget()
        scroll_content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sc_layout = QVBoxLayout(scroll_content)
        sc_layout.setContentsMargins(4, 4, 8, 4)
        sc_layout.setSpacing(16)

        # ════════════════════════════════════════════════════════
        # APARTADO 1: 🎧 SISTEMA & COMPORTAMIENTO (PRIMERA OPCIÓN)
        # ════════════════════════════════════════════════════════
        self.sec_sys_box = QFrame(scroll_content)
        self.sec_sys_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.sec_sys_box.setStyleSheet("QFrame { background-color: #121420; border-radius: 14px; border: 1.5px solid rgba(255, 255, 255, 0.12); }")
        sec_sys_layout = QVBoxLayout(self.sec_sys_box)
        sec_sys_layout.setContentsMargins(18, 16, 18, 16)
        sec_sys_layout.setSpacing(12)

        lbl_sys_title = QLabel("🎧 1. SISTEMA & COMPORTAMIENTO", self.sec_sys_box)
        lbl_sys_title.setFont(QFont("Sans Serif", 11, QFont.Weight.Bold))
        lbl_sys_title.setStyleSheet("color: #00e5ff; border: none;")
        sec_sys_layout.addWidget(lbl_sys_title)

        lbl_brand_desc = QLabel("Título / Marca mostrado en cabecera:", self.sec_sys_box)
        lbl_brand_desc.setStyleSheet("color: #a0aec0; font-size: 11px; border: none;")
        sec_sys_layout.addWidget(lbl_brand_desc)

        self.input_brand_name = QLineEdit(self.sec_sys_box)
        self.input_brand_name.setText(self.brand_name)
        self.input_brand_name.setPlaceholderText("Ej: RED WORLD")
        self.input_brand_name.setFixedHeight(34)
        self.input_brand_name.setStyleSheet("""
            QLineEdit {
                background-color: #0b0c12;
                color: #ffffff;
                border: 1.5px solid rgba(255, 255, 255, 0.18);
                border-radius: 8px;
                padding: 4px 10px;
                font-weight: bold;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1.5px solid #00e5ff;
            }
        """)
        sec_sys_layout.addWidget(self.input_brand_name)

        self.chk_top = QCheckBox("📌 Ventana Siempre Encima (Stays on Top)", self.sec_sys_box)
        self.chk_top.setChecked(self.stays_on_top)
        sec_sys_layout.addWidget(self.chk_top)

        sc_layout.addWidget(self.sec_sys_box)

        # ════════════════════════════════════════════════════════
        # APARTADO 2: 🎨 TEMA & FONDO
        # ════════════════════════════════════════════════════════
        self.sec_theme_box = QFrame(scroll_content)
        self.sec_theme_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.sec_theme_box.setStyleSheet(f"QFrame {{ background-color: #121420; border-radius: 14px; border: 1.5px solid {self.solid_accent}; }}")
        sec_theme_layout = QVBoxLayout(self.sec_theme_box)
        sec_theme_layout.setContentsMargins(18, 16, 18, 16)
        sec_theme_layout.setSpacing(14)

        lbl_theme_title = QLabel("🎨 2. TEMA & FONDO", self.sec_theme_box)
        lbl_theme_title.setFont(QFont("Sans Serif", 11, QFont.Weight.Bold))
        lbl_theme_title.setStyleSheet("color: #ffffff; border: none;")
        sec_theme_layout.addWidget(lbl_theme_title)

        # Selector principal: Degradado vs Imagen
        self.bg_type_group = QButtonGroup(self)
        self.radio_bg_type_gradient = QRadioButton("🎨 Fondo en Degradado / Color", self.sec_theme_box)
        self.radio_bg_type_image = QRadioButton("🖼️ Fondo de Imagen de Pantalla (Wallpaper)", self.sec_theme_box)
        self.bg_type_group.addButton(self.radio_bg_type_gradient)
        self.bg_type_group.addButton(self.radio_bg_type_image)

        if self.background_type == "image":
            self.radio_bg_type_image.setChecked(True)
        else:
            self.radio_bg_type_gradient.setChecked(True)

        self.radio_bg_type_gradient.toggled.connect(self._on_bg_type_toggled)
        self.radio_bg_type_image.toggled.connect(self._on_bg_type_toggled)

        bg_mode_row = QHBoxLayout()
        bg_mode_row.setSpacing(16)
        bg_mode_row.addWidget(self.radio_bg_type_gradient)
        bg_mode_row.addWidget(self.radio_bg_type_image)
        sec_theme_layout.addLayout(bg_mode_row)

        # Panel de Opciones de Fondo en Degradado / Color Sólido
        self.panel_bg_gradient = QWidget(self.sec_theme_box)
        panel_grad_layout = QVBoxLayout(self.panel_bg_gradient)
        panel_grad_layout.setContentsMargins(0, 4, 0, 0)
        panel_grad_layout.setSpacing(10)

        theme_group = QButtonGroup(self)
        self.radio_auto = QRadioButton("✨ Automático (Extraído de carátula de música)", self.panel_bg_gradient)
        self.radio_manual = QRadioButton("🎨 Manual Multi-Color (Degradado personalizado)", self.panel_bg_gradient)
        self.radio_solid = QRadioButton("🔴 Color Sólido Neón", self.panel_bg_gradient)
        theme_group.addButton(self.radio_auto)
        theme_group.addButton(self.radio_manual)
        theme_group.addButton(self.radio_solid)

        panel_grad_layout.addWidget(self.radio_auto)
        panel_grad_layout.addWidget(self.radio_manual)

        # Panel Manual Degradado (Multi-paradas con selector libre y paleta)
        self.manual_panel = QWidget(self.panel_bg_gradient)
        manual_main_layout = QVBoxLayout(self.manual_panel)
        manual_main_layout.setContentsMargins(0, 4, 0, 4)
        manual_main_layout.setSpacing(10)

        # Contenedor dinámico exclusivo para las paradas y paleta (se refresca sin tocar los presets)
        self.manual_stops_widget = QWidget(self.manual_panel)
        self.manual_stops_layout = QVBoxLayout(self.manual_stops_widget)
        self.manual_stops_layout.setContentsMargins(0, 0, 0, 0)
        self.manual_stops_layout.setSpacing(8)
        manual_main_layout.addWidget(self.manual_stops_widget)

        # Presets rápidos estáticos (permanentes, nunca se destruyen al hacer clic)
        lbl_presets = QLabel("✨ Presets Rápidos de Degradado:", self.manual_panel)
        lbl_presets.setStyleSheet("color: #a0a4c0; font-size: 10px; font-weight: bold; border: none; margin-top: 2px;")
        manual_main_layout.addWidget(lbl_presets)

        presets_layout = QGridLayout()
        presets_layout.setSpacing(6)
        for p_idx, (name, p_colors) in enumerate(self.PRESETS[:4]):
            btn_p = QPushButton(name, self.manual_panel)
            btn_p.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_p.clicked.connect(lambda checked, c=p_colors: self._apply_preset(c))
            r, col = divmod(p_idx, 2)
            presets_layout.addWidget(btn_p, r, col)
        manual_main_layout.addLayout(presets_layout)

        panel_grad_layout.addWidget(self.manual_panel)

        # Panel de Color Sólido
        panel_grad_layout.addWidget(self.radio_solid)

        self.solid_panel = QWidget(self.panel_bg_gradient)
        solid_layout = QVBoxLayout(self.solid_panel)
        solid_layout.setContentsMargins(4, 4, 4, 4)
        solid_layout.setSpacing(8)

        solid_row = QHBoxLayout()
        solid_row.setSpacing(10)

        self.btn_solid_swatch = QPushButton(f"  Color Activo: {self.solid_accent}  ", self.solid_panel)
        self.btn_solid_swatch.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_solid_swatch.clicked.connect(self._pick_solid_accent_color)
        solid_row.addWidget(self.btn_solid_swatch)

        self.btn_pick_solid = QPushButton("🎨 Seleccionar Color Sólido...", self.solid_panel)
        self.btn_pick_solid.clicked.connect(self._pick_solid_accent_color)
        solid_row.addWidget(self.btn_pick_solid)
        solid_row.addStretch()

        solid_layout.addLayout(solid_row)
        panel_grad_layout.addWidget(self.solid_panel)

        # Configurar estado inicial y señales
        if self.theme_mode == "gradient_auto":
            self.radio_auto.setChecked(True)
        elif self.theme_mode == "gradient_manual":
            self.radio_manual.setChecked(True)
        else:
            self.radio_solid.setChecked(True)

        self.radio_auto.toggled.connect(self._select_gradient_mode)
        self.radio_manual.toggled.connect(self._select_gradient_mode)
        self.radio_solid.toggled.connect(self._select_gradient_mode)
        self.radio_bg_type_gradient.toggled.connect(self._on_bg_type_toggled)
        self.radio_bg_type_image.toggled.connect(self._on_bg_type_toggled)

        self._refresh_manual_stops_ui()
        self._update_solid_panel_ui()

        sec_theme_layout.addWidget(self.panel_bg_gradient)

        # Panel de Opciones de Wallpaper
        self.panel_bg_image = QWidget(self.sec_theme_box)
        panel_img_layout = QVBoxLayout(self.panel_bg_image)
        panel_img_layout.setContentsMargins(0, 4, 0, 0)
        panel_img_layout.setSpacing(8)

        btns_img_layout = QHBoxLayout()
        self.btn_choose_img = QPushButton("🖼️ Seleccionar Imagen...", self.panel_bg_image)
        self.btn_choose_img.clicked.connect(self._choose_bg_image)
        self.btn_choose_folder = QPushButton("📁 Seleccionar Carpeta...", self.panel_bg_image)
        self.btn_choose_folder.clicked.connect(self._choose_bg_folder)
        btns_img_layout.addWidget(self.btn_choose_img)
        btns_img_layout.addWidget(self.btn_choose_folder)
        panel_img_layout.addLayout(btns_img_layout)

        img_name = os.path.basename(self.bg_image_path) if self.bg_image_path else "Ninguna"
        folder_name = os.path.basename(self.bg_folder_path) if self.bg_folder_path else "Ninguna"

        self.lbl_selected_img_info = QLabel(f"Imagen seleccionada: {img_name}", self.panel_bg_image)
        self.lbl_selected_img_info.setWordWrap(True)
        self.lbl_selected_img_info.setStyleSheet("color: #a0a4c0; font-size: 10px; border: none;")
        panel_img_layout.addWidget(self.lbl_selected_img_info)

        self.lbl_selected_folder_info = QLabel(f"Carpeta activa: {folder_name}", self.panel_bg_image)
        self.lbl_selected_folder_info.setWordWrap(True)
        self.lbl_selected_folder_info.setStyleSheet("color: #a0a4c0; font-size: 10px; border: none;")
        panel_img_layout.addWidget(self.lbl_selected_folder_info)

        self.chk_slideshow = QCheckBox("🔄 Carrusel Automático de Fondos (Cada 15s)", self.panel_bg_image)
        self.chk_slideshow.setChecked(self.slideshow_enabled)
        self.chk_slideshow.toggled.connect(self._select_image_mode)
        panel_img_layout.addWidget(self.chk_slideshow)

        aspect_layout = QHBoxLayout()
        lbl_aspect = QLabel("Modo de Ajuste:", self.panel_bg_image)
        self.combo_aspect = QComboBox(self.panel_bg_image)
        self.combo_aspect.addItems(["Estirar a la ventana", "Llenar ventana (Recortar)", "Ajustar (Sin recortes)"])
        aspect_map = {"stretch": 0, "fill": 1, "fit": 2}
        self.combo_aspect.setCurrentIndex(aspect_map.get(self.aspect_mode, 0))
        self.combo_aspect.currentIndexChanged.connect(self._select_image_mode)
        aspect_layout.addWidget(lbl_aspect)
        aspect_layout.addWidget(self.combo_aspect)
        panel_img_layout.addLayout(aspect_layout)

        sec_theme_layout.addWidget(self.panel_bg_image)
        sc_layout.addWidget(self.sec_theme_box)

        # ════════════════════════════════════════════════════════
        # APARTADO 3: 🎛️ ESTILO Y COLORES DE BOTONES (SEPARADO)
        # ════════════════════════════════════════════════════════
        self.sec_btn_box = QFrame(scroll_content)
        self.sec_btn_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.sec_btn_box.setStyleSheet("QFrame { background-color: #121420; border-radius: 14px; border: 1.5px solid rgba(255, 255, 255, 0.12); }")
        sec_btn_layout = QVBoxLayout(self.sec_btn_box)
        sec_btn_layout.setContentsMargins(18, 16, 18, 16)
        sec_btn_layout.setSpacing(12)

        lbl_btn_title = QLabel("🎛️ 3. COLORES Y ESTILO DE BOTONES", self.sec_btn_box)
        lbl_btn_title.setFont(QFont("Sans Serif", 11, QFont.Weight.Bold))
        lbl_btn_title.setStyleSheet("color: #00e5ff; border: none;")
        sec_btn_layout.addWidget(lbl_btn_title)

        # Previsualización en Vivo del Botón
        self.btn_preview_widget = GradientPreviewWidget(self._get_active_colors_for_preview(), self.btn_gradient_effect, self.sec_btn_box)
        sec_btn_layout.addWidget(self.btn_preview_widget)

        lbl_src_title = QLabel("Origen del color de los botones:", self.sec_btn_box)
        lbl_src_title.setStyleSheet("color: #a0aec0; font-size: 11px; font-weight: bold; border: none; margin-top: 4px;")
        sec_btn_layout.addWidget(lbl_src_title)

        btn_src_group = QButtonGroup(self)
        self.radio_src_gradient = QRadioButton("🎨 Usar Colores del Tema en Degradado", self.sec_btn_box)
        self.radio_src_wallpaper = QRadioButton("🖼️ Usar Colores Extraídos del Wallpaper", self.sec_btn_box)
        self.radio_src_custom = QRadioButton("🔮 Usar Color / Degradado Libre e Independiente", self.sec_btn_box)
        btn_src_group.addButton(self.radio_src_gradient)
        btn_src_group.addButton(self.radio_src_wallpaper)
        btn_src_group.addButton(self.radio_src_custom)

        if self.button_color_source == "gradient":
            self.radio_src_gradient.setChecked(True)
        elif self.button_color_source == "custom":
            self.radio_src_custom.setChecked(True)
        else:
            self.radio_src_wallpaper.setChecked(True)

        self.radio_src_gradient.toggled.connect(self._on_btn_source_changed)
        self.radio_src_wallpaper.toggled.connect(self._on_btn_source_changed)
        sec_btn_layout.addWidget(self.radio_src_gradient)
        sec_btn_layout.addWidget(self.radio_src_wallpaper)
        sec_btn_layout.addWidget(self.radio_src_custom)

        self.chk_btn_gradient = QCheckBox("🎨 Aplicar efecto de degradado a los botones", self.sec_btn_box)
        self.chk_btn_gradient.setChecked(self.btn_gradient_effect)
        self.chk_btn_gradient.toggled.connect(self._on_btn_gradient_toggled)
        sec_btn_layout.addWidget(self.chk_btn_gradient)

        # Panel exclusivo para Color Personalizado de Botones (solo visible cuando radio_src_custom está activo)
        self.panel_btn_custom_colors = QWidget(self.sec_btn_box)
        panel_btn_custom_layout = QVBoxLayout(self.panel_btn_custom_colors)
        panel_btn_custom_layout.setContentsMargins(0, 4, 0, 0)
        panel_btn_custom_layout.setSpacing(8)

        self.lbl_btn_stop_title = QLabel("📍 Seleccionar Stop a Editar:", self.panel_btn_custom_colors)
        self.lbl_btn_stop_title.setStyleSheet("color: #00e5ff; font-weight: bold; font-size: 11px; border: none;")
        panel_btn_custom_layout.addWidget(self.lbl_btn_stop_title)

        self.btn_stops_container = QWidget(self.panel_btn_custom_colors)
        self.btn_stops_layout = QHBoxLayout(self.btn_stops_container)
        self.btn_stops_layout.setContentsMargins(0, 0, 0, 0)
        self.btn_stops_layout.setSpacing(6)
        panel_btn_custom_layout.addWidget(self.btn_stops_container)

        self.lbl_btn_palette_title = QLabel("🎨 Paleta Rápida para Editar Stop A:", self.panel_btn_custom_colors)
        self.lbl_btn_palette_title.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 11px; border: none; margin-top: 2px;")
        panel_btn_custom_layout.addWidget(self.lbl_btn_palette_title)

        self.btn_palette_container = QWidget(self.panel_btn_custom_colors)
        self.btn_palette_layout = QHBoxLayout(self.btn_palette_container)
        self.btn_palette_layout.setContentsMargins(0, 0, 0, 0)
        self.btn_palette_layout.setSpacing(6)
        panel_btn_custom_layout.addWidget(self.btn_palette_container)

        self.btn_custom_picker = QPushButton("🎨 Seleccionar Color Libre para Stop A...", self.panel_btn_custom_colors)
        self.btn_custom_picker.setStyleSheet("QPushButton { background-color: #1a1c29; color: #00e5ff; border: 1px solid #2a2d42; border-radius: 8px; font-weight: bold; padding: 6px 12px; } QPushButton:hover { background-color: #24273b; }")
        self.btn_custom_picker.clicked.connect(self._pick_custom_button_color)
        panel_btn_custom_layout.addWidget(self.btn_custom_picker)

        sec_btn_layout.addWidget(self.panel_btn_custom_colors)
        sc_layout.addWidget(self.sec_btn_box)

        # ════════════════════════════════════════════════════════
        # APARTADO 4: 🖼️ CARÁTULA & RECUADRO CENTRAL
        # ════════════════════════════════════════════════════════
        self.sec_art_box = QFrame(scroll_content)
        self.sec_art_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.sec_art_box.setStyleSheet("QFrame { background-color: #121420; border-radius: 14px; border: 1.5px solid rgba(255, 255, 255, 0.12); }")
        sec_art_layout = QVBoxLayout(self.sec_art_box)
        sec_art_layout.setContentsMargins(18, 16, 18, 16)
        sec_art_layout.setSpacing(12)

        lbl_art_title = QLabel("🖼️ 4. CARÁTULA & RECUADRO CENTRAL", self.sec_art_box)
        lbl_art_title.setFont(QFont("Sans Serif", 11, QFont.Weight.Bold))
        lbl_art_title.setStyleSheet("color: #ffffff; border: none;")
        sec_art_layout.addWidget(lbl_art_title)

        # A. Modo de Imagen de Carátula
        self.radio_art_auto = QRadioButton("🎵 Mostrar Carátula de la Canción (Automático)", self.sec_art_box)
        self.radio_art_custom = QRadioButton("📌 Mostrar SIEMPRE Imagen Personalizada Fija", self.sec_art_box)
        art_group = QButtonGroup(self)
        art_group.addButton(self.radio_art_auto)
        art_group.addButton(self.radio_art_custom)

        if self.inner_art_mode == "custom_always":
            self.radio_art_custom.setChecked(True)
        else:
            self.radio_art_auto.setChecked(True)

        sec_art_layout.addWidget(self.radio_art_auto)
        sec_art_layout.addWidget(self.radio_art_custom)

        self.btn_choose_inner = QPushButton("🖼️ Cambiar Imagen Personalizada Fija...", self.sec_art_box)
        self.btn_choose_inner.clicked.connect(self._choose_inner_image)
        sec_art_layout.addWidget(self.btn_choose_inner)

        # B. Forma Geométrica de la Carátula (Redonda vs Cuadrada vs Corazón)
        lbl_shape_title = QLabel("📐 Forma de la Carátula:", self.sec_art_box)
        lbl_shape_title.setStyleSheet("color: #a0aec0; font-size: 11px; border: none; margin-top: 4px;")
        sec_art_layout.addWidget(lbl_shape_title)

        shape_row = QHBoxLayout()
        shape_row.setSpacing(14)
        self.radio_shape_circle = QRadioButton("🔘 Redonda / Circular", self.sec_art_box)
        self.radio_shape_rounded = QRadioButton("🔲 Cuadrada redondeada", self.sec_art_box)
        self.radio_shape_heart = QRadioButton("💖 Corazón", self.sec_art_box)
        shape_group = QButtonGroup(self)
        shape_group.addButton(self.radio_shape_circle)
        shape_group.addButton(self.radio_shape_rounded)
        shape_group.addButton(self.radio_shape_heart)

        curr_shape = getattr(self, 'cover_shape', 'rounded')
        if curr_shape == "circle":
            self.radio_shape_circle.setChecked(True)
        elif curr_shape == "heart":
            self.radio_shape_heart.setChecked(True)
        else:
            self.radio_shape_rounded.setChecked(True)

        shape_row.addWidget(self.radio_shape_circle)
        shape_row.addWidget(self.radio_shape_rounded)
        shape_row.addWidget(self.radio_shape_heart)
        shape_row.addStretch()
        sec_art_layout.addLayout(shape_row)

        # C. Estilo de Reproducción / Tocadiscos en Modo Expandido
        self.sec_expanded_vis_container = QWidget(self.sec_art_box)
        sec_vis_layout = QVBoxLayout(self.sec_expanded_vis_container)
        sec_vis_layout.setContentsMargins(0, 4, 0, 0)
        sec_vis_layout.setSpacing(6)

        lbl_vis_title = QLabel("🎛️ Estilo de Visualización / Tocadiscos (Modo Expandido):", self.sec_expanded_vis_container)
        lbl_vis_title.setStyleSheet("color: #00e5ff; font-size: 11px; font-weight: bold; border: none; margin-top: 6px;")
        sec_vis_layout.addWidget(lbl_vis_title)

        vis_group = QButtonGroup(self)
        self.radio_vis_radial = QRadioButton("🔊 Visualizador Radial de Ondas (Trap Nation / Espectral)", self.sec_expanded_vis_container)
        self.radio_vis_vinyl = QRadioButton("📀 Tocadiscos Clásico de Vinilo con Brazo Hi-Fi", self.sec_expanded_vis_container)
        self.radio_vis_card = QRadioButton("🖼️ Carátula Flotante con Halo Neón y Espectro", self.sec_expanded_vis_container)

        vis_group.addButton(self.radio_vis_radial)
        vis_group.addButton(self.radio_vis_vinyl)
        vis_group.addButton(self.radio_vis_card)

        curr_vis = getattr(self, 'expanded_visualizer_style', 'radial_waves')
        if curr_vis == "vinyl":
            self.radio_vis_vinyl.setChecked(True)
        elif curr_vis == "card_glow":
            self.radio_vis_card.setChecked(True)
        else:
            self.radio_vis_radial.setChecked(True)

        sec_vis_layout.addWidget(self.radio_vis_radial)
        sec_vis_layout.addWidget(self.radio_vis_vinyl)
        sec_vis_layout.addWidget(self.radio_vis_card)

        self.sec_expanded_vis_container.setVisible(self.mode == "expanded")
        sec_art_layout.addWidget(self.sec_expanded_vis_container)

        sc_layout.addWidget(self.sec_art_box)

        # ════════════════════════════════════════════════════════
        # APARTADO 5: 🔤 TIPOGRAFÍA & FUENTE DEL REPRODUCTOR
        # ════════════════════════════════════════════════════════
        self.sec_font_box = QFrame(scroll_content)
        self.sec_font_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.sec_font_box.setStyleSheet("QFrame { background-color: #121420; border-radius: 14px; border: 1.5px solid rgba(255, 255, 255, 0.12); }")
        sec_font_layout = QVBoxLayout(self.sec_font_box)
        sec_font_layout.setContentsMargins(18, 16, 18, 16)
        sec_font_layout.setSpacing(12)

        font_header_layout = QHBoxLayout()
        lbl_font_title = QLabel("🔤 5. TIPOGRAFÍA & LETRAS DEL REPRODUCTOR", self.sec_font_box)
        lbl_font_title.setFont(QFont("Sans Serif", 11, QFont.Weight.Bold))
        lbl_font_title.setStyleSheet("color: #00e5ff; border: none;")
        font_header_layout.addWidget(lbl_font_title)

        lbl_font_badge = QLabel(self.mode_label, self.sec_font_box)
        lbl_font_badge.setFont(QFont("Sans Serif", 8, QFont.Weight.Bold))
        lbl_font_badge.setStyleSheet("color: rgba(255, 255, 255, 0.85); background: rgba(0, 229, 255, 0.15); border: 1px solid #00e5ff; border-radius: 8px; padding: 2px 8px;")
        font_header_layout.addWidget(lbl_font_badge)
        font_header_layout.addStretch(1)
        sec_font_layout.addLayout(font_header_layout)

        lbl_font_desc = QLabel(f"Personaliza la tipografía de todos los textos, títulos y letras para {self.mode_label}:", self.sec_font_box)
        lbl_font_desc.setStyleSheet("color: #a0aec0; font-size: 11px; border: none;")
        sec_font_layout.addWidget(lbl_font_desc)

        # Fila de selección y carga de fuente
        font_select_row = QHBoxLayout()
        font_select_row.setSpacing(10)

        from ui.font_manager import discover_available_fonts, load_custom_font
        self.available_font_families, self.font_path_map = discover_available_fonts()

        self.combo_font = QComboBox(self.sec_font_box)
        self.combo_font.setFixedHeight(34)
        self.combo_font.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        for fam in self.available_font_families:
            self.combo_font.addItem(fam)

        # Seleccionar la fuente actual si existe
        cur_font_idx = self.combo_font.findText(self.font_family)
        if cur_font_idx >= 0:
            self.combo_font.setCurrentIndex(cur_font_idx)
        else:
            self.combo_font.insertItem(0, self.font_family)
            self.combo_font.setCurrentIndex(0)

        self.combo_font.currentTextChanged.connect(self._on_font_family_changed)
        font_select_row.addWidget(self.combo_font, stretch=1)

        btn_browse_font = QPushButton("📁 Cargar (.ttf / .otf / .zip)...", self.sec_font_box)
        btn_browse_font.setFixedHeight(34)
        btn_browse_font.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_browse_font.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 229, 255, 0.15);
                color: #00e5ff;
                border: 1px solid #00e5ff;
                border-radius: 8px;
                padding: 4px 12px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(0, 229, 255, 0.30);
                color: #ffffff;
            }
        """)
        btn_browse_font.clicked.connect(self._browse_custom_font)
        font_select_row.addWidget(btn_browse_font)

        btn_reset_font = QPushButton("🔄 Restablecer", self.sec_font_box)
        btn_reset_font.setFixedHeight(34)
        btn_reset_font.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reset_font.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                color: rgba(255, 255, 255, 0.85);
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 8px;
                padding: 4px 10px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.18);
                color: #ffffff;
            }
        """)
        btn_reset_font.clicked.connect(self._reset_font_default)
        font_select_row.addWidget(btn_reset_font)

        sec_font_layout.addLayout(font_select_row)

        # Previsualización en vivo de la tipografía
        self.font_preview_card = QFrame(self.sec_font_box)
        self.font_preview_card.setStyleSheet("QFrame { background-color: #0b0c14; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 10px; padding: 10px; }")
        card_layout = QVBoxLayout(self.font_preview_card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(4)

        self.lbl_font_preview_title = QLabel("Título de Ejemplo — Canción Destacada", self.font_preview_card)
        self.lbl_font_preview_title.setStyleSheet("color: #ffffff; border: none; background: transparent;")
        card_layout.addWidget(self.lbl_font_preview_title)

        self.lbl_font_preview_body = QLabel("01:23 / 03:45 ♪ Letras y controles adaptados con esta tipografía — RED WORLD", self.font_preview_card)
        self.lbl_font_preview_body.setStyleSheet("color: #00e5ff; border: none; background: transparent;")
        card_layout.addWidget(self.lbl_font_preview_body)

        sec_font_layout.addWidget(self.font_preview_card)
        self._update_font_preview(self.font_family)

        sc_layout.addWidget(self.sec_font_box)

        scroll.setWidget(scroll_content)
        f_layout.addWidget(scroll, stretch=1)

        # Botones de Acción final
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(12)
        actions_layout.addStretch()

        btn_cancel = QPushButton("Cancelar", self.frame_card)
        btn_cancel.setFixedHeight(36)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                color: #ffffff;
                border-radius: 10px;
                padding: 4px 18px;
                font-size: 12px;
                font-weight: bold;
                border: 1px solid rgba(255, 255, 255, 0.15);
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.18);
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        actions_layout.addWidget(btn_cancel)

        self.btn_apply = QPushButton("💾 Guardar y Aplicar", self.frame_card)
        self.btn_apply.setFixedHeight(36)
        self.btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_apply.setStyleSheet(f"""
            QPushButton {{
                background-color: {clean_accent};
                color: #ffffff;
                font-weight: bold;
                padding: 4px 20px;
                border-radius: 10px;
                border: none;
                font-size: 12px;
            }}
            QPushButton:hover {{
                opacity: 0.90;
            }}
        """)
        self.btn_apply.clicked.connect(self._on_apply_clicked)
        actions_layout.addWidget(self.btn_apply)

        f_layout.addLayout(actions_layout)
        main_layout.addWidget(self.frame_card)

        self._on_bg_type_toggled()
        self._on_btn_source_changed()
        self._refresh_button_swatches_ui()
        self._update_section_highlights()
        self._apply_dialog_font(self.font_family)
        self._update_mode_tab_styles()

    def _is_button_gradient_enabled(self) -> bool:
        if hasattr(self, 'chk_btn_gradient') and self.chk_btn_gradient is not None:
            return bool(self.chk_btn_gradient.isChecked())
        return bool(getattr(self, 'btn_gradient_effect', True))

    def _get_active_button_colors(self) -> List[str]:
        if not self._is_button_gradient_enabled():
            accent = getattr(self, 'solid_accent', '#ff1744') or '#ff1744'
            return [accent, accent]

        source = getattr(self, 'button_color_source', 'wallpaper' if getattr(self, 'background_type', 'gradient') == 'image' else 'gradient')
        if getattr(self, 'background_type', 'gradient') == 'gradient' and source == 'wallpaper':
            source = 'gradient'

        raw_colors = None

        if source == "gradient":
            if self.theme_mode == "gradient_manual":
                raw_colors = getattr(self, 'manual_colors', None)
            elif self.theme_mode == "gradient_auto":
                raw_colors = getattr(self, 'auto_colors', None)
            elif self.theme_mode == "solid":
                raw_colors = [getattr(self, 'solid_accent', '#ff1744'), getattr(self, 'solid_accent', '#ff1744')]
            else:
                raw_colors = [getattr(self, 'solid_accent', '#ff1744'), getattr(self, 'solid_accent', '#ff1744')]
        elif source == "wallpaper":
            raw_colors = getattr(self, 'wallpaper_gradient_colors', None) or getattr(self, 'auto_colors', None)
            if not raw_colors:
                raw_colors = self._extract_wallpaper_colors()
                self.wallpaper_gradient_colors = raw_colors
        elif source == "custom":
            raw_colors = getattr(self, 'custom_btn_gradient_colors', None)
        else:
            raw_colors = [getattr(self, 'solid_accent', '#ff1744')]

        fallback_accent = getattr(self, 'solid_accent', '#ff1744') or '#ff1744'
        if not raw_colors or not isinstance(raw_colors, list) or len(raw_colors) < 1:
            return [fallback_accent, fallback_accent]

        clean_list = [c for c in raw_colors if c and isinstance(c, str)]
        if len(clean_list) == 0:
            return [fallback_accent, fallback_accent]
        elif len(clean_list) == 1:
            return [clean_list[0], clean_list[0]]

        return clean_list

    def _get_active_colors_for_preview(self) -> List[str]:
        return self._get_active_button_colors()

    def _update_preview(self) -> None:
        if hasattr(self, 'btn_preview_widget') and self.btn_preview_widget:
            colors = self._get_active_button_colors()
            enabled = self._is_button_gradient_enabled()
            self.btn_preview_widget.set_colors(colors, enabled)

    def _refresh_button_visual_state(self) -> None:
        self.btn_gradient_effect = self._is_button_gradient_enabled()
        self._refresh_button_swatches_ui()
        self._update_preview()
        self._update_section_highlights()

    def _select_gradient_mode(self, checked: bool = True) -> None:
        if not checked:
            return
        self.background_type = "gradient"
        if hasattr(self, 'radio_bg_type_gradient') and self.radio_bg_type_gradient and not self.radio_bg_type_gradient.isChecked():
            self.radio_bg_type_gradient.setChecked(True)
        if self.radio_auto.isChecked():
            self.theme_mode = "gradient_auto"
            if hasattr(self, 'manual_panel'): self.manual_panel.setVisible(False)
            if hasattr(self, 'solid_panel'): self.solid_panel.setVisible(False)
        elif self.radio_manual.isChecked():
            self.theme_mode = "gradient_manual"
            if hasattr(self, 'manual_panel'): self.manual_panel.setVisible(True)
            if hasattr(self, 'solid_panel'): self.solid_panel.setVisible(False)
            if self.manual_colors:
                self.solid_accent = self.manual_colors[0]
            self._refresh_manual_stops_ui()
        else:
            self.theme_mode = "solid"
            if hasattr(self, 'manual_panel'): self.manual_panel.setVisible(False)
            if hasattr(self, 'solid_panel'): self.solid_panel.setVisible(True)
            self._update_solid_panel_ui()

        if getattr(self, 'button_color_source', 'gradient') == "wallpaper":
            self.button_color_source = "gradient"
            if hasattr(self, 'radio_src_gradient') and self.radio_src_gradient:
                self.radio_src_gradient.setChecked(True)

        self._refresh_button_visual_state()

    def _update_solid_panel_ui(self) -> None:
        if not hasattr(self, 'btn_solid_swatch') or not self.btn_solid_swatch:
            return
        accent = getattr(self, 'solid_accent', '#ff1744') or '#ff1744'
        text_c = get_contrasting_text_color(accent)
        self.btn_solid_swatch.setText(f"  Color Activo: {accent}  ")
        self.btn_solid_swatch.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent};
                color: {text_c};
                font-size: 11px;
                font-weight: bold;
                border: 1.5px solid rgba(255, 255, 255, 0.40);
                border-radius: 8px;
                padding: 6px 14px;
            }}
            QPushButton:hover {{
                border: 1.5px solid #ffffff;
            }}
        """)

    def _pick_solid_accent_color(self) -> None:
        current = getattr(self, 'solid_accent', '#ff1744') or '#ff1744'
        col = QColorDialog.getColor(QColor(current), self, "Seleccionar Color Sólido del Tema")
        if col.isValid():
            hex_c = col.name()
            self.solid_accent = hex_c
            self.background_type = "gradient"
            self.theme_mode = "solid"
            if getattr(self, 'button_color_source', 'gradient') == "wallpaper":
                self.button_color_source = "gradient"
                if hasattr(self, 'radio_src_gradient') and self.radio_src_gradient:
                    self.radio_src_gradient.setChecked(True)
            if hasattr(self, 'radio_bg_type_gradient') and self.radio_bg_type_gradient and not self.radio_bg_type_gradient.isChecked():
                self.radio_bg_type_gradient.setChecked(True)
            if hasattr(self, 'radio_solid') and self.radio_solid:
                self.radio_solid.setChecked(True)
            self._update_solid_panel_ui()
            self._refresh_button_visual_state()

    def _on_bg_type_toggled(self) -> None:
        if hasattr(self, 'radio_bg_type_image') and self.radio_bg_type_image.isChecked():
            self.background_type = "image"
            if hasattr(self, 'panel_bg_gradient'): self.panel_bg_gradient.setVisible(False)
            if hasattr(self, 'panel_bg_image'): self.panel_bg_image.setVisible(True)
        else:
            self.background_type = "gradient"
            if hasattr(self, 'panel_bg_gradient'): self.panel_bg_gradient.setVisible(True)
            if hasattr(self, 'panel_bg_image'): self.panel_bg_image.setVisible(False)
            self._select_gradient_mode(True)

        if hasattr(self, 'radio_src_gradient'): self.radio_src_gradient.setVisible(True)
        if hasattr(self, 'radio_src_wallpaper'): self.radio_src_wallpaper.setVisible(True)

        self._refresh_button_visual_state()

    def _select_image_mode(self) -> None:
        self.background_type = "image"
        if hasattr(self, 'radio_bg_type_image') and self.radio_bg_type_image:
            self.radio_bg_type_image.setChecked(True)
        self._refresh_button_visual_state()

    def _update_section_highlights(self) -> None:
        accent = getattr(self, 'solid_accent', '#ff1744') or '#ff1744'
        clean_accent = accent.split(';')[0].strip() or "#ff1744"
        if getattr(self, '_last_highlight_accent', None) == clean_accent:
            return
        self._last_highlight_accent = clean_accent

        if hasattr(self, 'btn_apply') and self.btn_apply:
            self.btn_apply.setStyleSheet(f"""
                QPushButton {{
                    background-color: {clean_accent};
                    color: #ffffff;
                    font-weight: bold;
                    padding: 4px 20px;
                    border-radius: 10px;
                    border: none;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    opacity: 0.90;
                }}
            """)

        if hasattr(self, 'frame_card') and self.frame_card:
            self.frame_card.setStyleSheet(f"""
                QFrame#PersonalizationMainCard {{
                    background-color: rgba(13, 17, 29, 0.96);
                    border: 1.5px solid {clean_accent};
                    border-radius: 20px;
                }}
            """)

        if hasattr(self, 'sec_theme_box') and self.sec_theme_box:
            self.sec_theme_box.setStyleSheet(f"QFrame {{ background-color: #121420; border-radius: 14px; border: 1.5px solid {clean_accent}; }}")

    def _on_btn_source_changed(self) -> None:
        if hasattr(self, 'radio_src_gradient') and self.radio_src_gradient.isChecked():
            self.button_color_source = "gradient"
            if hasattr(self, 'panel_btn_custom_colors'): self.panel_btn_custom_colors.setVisible(False)
        elif hasattr(self, 'radio_src_wallpaper') and self.radio_src_wallpaper.isChecked():
            self.button_color_source = "wallpaper"
            if hasattr(self, 'panel_btn_custom_colors'): self.panel_btn_custom_colors.setVisible(False)
        elif hasattr(self, 'radio_src_custom') and self.radio_src_custom.isChecked():
            self.button_color_source = "custom"
            if hasattr(self, 'panel_btn_custom_colors'): self.panel_btn_custom_colors.setVisible(True)

        self._refresh_button_visual_state()

    def _on_btn_gradient_toggled(self, checked: bool) -> None:
        self.btn_gradient_effect = checked
        self._refresh_button_visual_state()

    def _set_active_stop_index(self, idx: int) -> None:
        self.active_gradient_stop_index = idx
        self._refresh_button_swatches_ui()
        self._update_preview()

    def _refresh_button_swatches_ui(self) -> None:
        if not hasattr(self, 'btn_stops_layout') or self.btn_stops_layout is None:
            return

        # Solo renderizar contenido si la fuente es personalizada
        if getattr(self, 'button_color_source', 'gradient') != "custom":
            return

        stops_list = getattr(self, 'custom_btn_gradient_colors', ["#ff1744", "#00e5ff", "#e040fb"])
        if not stops_list:
            stops_list = ["#ff1744", "#00e5ff", "#e040fb"]

        idx_active = max(0, min(getattr(self, 'active_gradient_stop_index', 0), len(stops_list) - 1))
        self.active_gradient_stop_index = idx_active

        if hasattr(self, 'lbl_btn_palette_title') and self.lbl_btn_palette_title:
            self.lbl_btn_palette_title.setText(f"🎨 Paleta Rápida para Editar Stop {chr(65 + idx_active)}:")

        if hasattr(self, 'btn_custom_picker') and self.btn_custom_picker:
            active_c = stops_list[idx_active]
            self.btn_custom_picker.setText(f"🎨 Seleccionar Color Libre para Stop {chr(65 + idx_active)} ({active_c})...")

        # 1. Actualizar o crear botones de paradas (Stop A, B, C) sin destruirlos
        while self.btn_stops_layout.count() > len(stops_list):
            item = self.btn_stops_layout.takeAt(self.btn_stops_layout.count() - 1)
            if item.widget():
                w = item.widget()
                w.hide()
                w.deleteLater()

        for s_idx, stop_c in enumerate(stops_list):
            is_sel = (s_idx == idx_active)
            border_color = "#00e5ff" if is_sel else "rgba(255, 255, 255, 0.25)"
            border_w = "2.5px" if is_sel else "1px"
            text_c = get_contrasting_text_color(stop_c)
            btn_text = f"Stop {chr(65 + s_idx)}\n{stop_c}"
            style = f"""
                QPushButton {{
                    background-color: {stop_c};
                    color: {text_c};
                    border: {border_w} solid {border_color};
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 10px;
                }}
            """

            if s_idx < self.btn_stops_layout.count():
                btn_w = self.btn_stops_layout.itemAt(s_idx).widget()
                if isinstance(btn_w, QPushButton):
                    btn_w.setText(btn_text)
                    btn_w.setStyleSheet(style)
            else:
                btn_stop = QPushButton(btn_text, self.btn_stops_container)
                btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_stop.setFixedHeight(36)
                btn_stop.setStyleSheet(style)
                btn_stop.clicked.connect(lambda checked, idx=s_idx: self._set_active_stop_index(idx))
                self.btn_stops_layout.addWidget(btn_stop)

        # 2. Actualizar o crear botones de paleta circular sin destruirlos
        colors_to_show = getattr(self, 'custom_button_swatches', self.QUICK_PALETTE)[:6]
        while self.btn_palette_layout.count() > len(colors_to_show):
            item = self.btn_palette_layout.takeAt(self.btn_palette_layout.count() - 1)
            if item.widget():
                w = item.widget()
                w.hide()
                w.deleteLater()

        for idx, hex_c in enumerate(colors_to_show):
            is_active = (hex_c.lower() == stops_list[idx_active].lower())
            border = "2.5px solid #00e5ff" if is_active else "1px solid rgba(255, 255, 255, 0.20)"
            style = f"QPushButton {{ background-color: {hex_c}; border-radius: 19px; border: {border}; }} QPushButton:hover {{ border: 2px solid #ffffff; }}"

            if idx < self.btn_palette_layout.count():
                btn_p = self.btn_palette_layout.itemAt(idx).widget()
                if isinstance(btn_p, QPushButton):
                    btn_p.setStyleSheet(style)
            else:
                btn = QPushButton(self.btn_palette_container)
                btn.setFixedSize(38, 38)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet(style)
                btn.clicked.connect(lambda checked, c=hex_c: self._select_button_color(c))
                self.btn_palette_layout.addWidget(btn)

    def _select_button_color(self, hex_color: str) -> None:
        self.solid_accent = hex_color
        self.button_color_source = "custom"
        if hasattr(self, 'radio_src_custom') and self.radio_src_custom and not self.radio_src_custom.isChecked():
            self.radio_src_custom.setChecked(True)
        if not hasattr(self, 'custom_btn_gradient_colors') or not self.custom_btn_gradient_colors:
            self.custom_btn_gradient_colors = [hex_color, "#00e5ff", "#e040fb"]
        else:
            idx = max(0, min(getattr(self, 'active_gradient_stop_index', 0), len(self.custom_btn_gradient_colors) - 1))
            self.custom_btn_gradient_colors[idx] = hex_color

        self._refresh_button_visual_state()

    def _pick_custom_button_color(self) -> None:
        idx = max(0, min(getattr(self, 'active_gradient_stop_index', 0), len(self.custom_btn_gradient_colors) - 1))
        curr_c = self.custom_btn_gradient_colors[idx] if getattr(self, 'custom_btn_gradient_colors', None) else self.solid_accent
        color = QColorDialog.getColor(QColor(curr_c), self, f"Seleccionar Color para Stop {chr(65 + idx)}")
        if color.isValid():
            hex_c = color.name()
            if not hasattr(self, 'custom_button_swatches'):
                self.custom_button_swatches = list(self.QUICK_PALETTE)
            if hex_c not in self.custom_button_swatches:
                self.custom_button_swatches.insert(0, hex_c)

            if not hasattr(self, 'custom_btn_gradient_colors') or not self.custom_btn_gradient_colors:
                self.custom_btn_gradient_colors = ["#ff1744", "#00e5ff", "#e040fb"]
            self.custom_btn_gradient_colors[idx] = hex_c
            self.solid_accent = hex_c
            if hasattr(self, 'radio_src_custom') and self.radio_src_custom:
                self.radio_src_custom.setChecked(True)
            self.button_color_source = "custom"
            self._refresh_button_visual_state()

    def _apply_preset(self, colors: List[str]) -> None:
        self.manual_colors = list(colors)
        self.active_manual_stop_index = 0
        if self.manual_colors:
            self.solid_accent = self.manual_colors[0]
        self.background_type = "gradient"
        self.theme_mode = "gradient_manual"
        self.button_color_source = "gradient"
        self.btn_gradient_effect = True
        if hasattr(self, 'radio_bg_type_gradient') and self.radio_bg_type_gradient and not self.radio_bg_type_gradient.isChecked():
            self.radio_bg_type_gradient.setChecked(True)
        if hasattr(self, 'radio_manual') and self.radio_manual and not self.radio_manual.isChecked():
            self.radio_manual.blockSignals(True)
            self.radio_manual.setChecked(True)
            self.radio_manual.blockSignals(False)
        if hasattr(self, 'radio_src_gradient') and self.radio_src_gradient and not self.radio_src_gradient.isChecked():
            self.radio_src_gradient.setChecked(True)
        if hasattr(self, 'chk_btn_gradient') and self.chk_btn_gradient:
            self.chk_btn_gradient.setChecked(True)
        self._refresh_manual_stops_ui()
        self._refresh_button_visual_state()

    def _set_active_manual_stop_index(self, idx: int) -> None:
        self.active_manual_stop_index = idx
        self._refresh_manual_stops_ui()

    def _select_manual_stop_palette_color(self, hex_color: str) -> None:
        if 0 <= self.active_manual_stop_index < len(self.manual_colors):
            self.manual_colors[self.active_manual_stop_index] = hex_color
            if self.active_manual_stop_index == 0:
                self.solid_accent = hex_color
            self._refresh_manual_stops_ui()
            self._refresh_button_visual_state()

    def _pick_manual_active_stop_color(self) -> None:
        idx = max(0, min(getattr(self, 'active_manual_stop_index', 0), len(self.manual_colors) - 1))
        curr_c = self.manual_colors[idx]
        col = QColorDialog.getColor(QColor(curr_c), self, f"Seleccionar Color Personalizado para Parada {chr(65 + idx)}")
        if col.isValid():
            hex_c = col.name()
            self.manual_colors[idx] = hex_c
            if idx == 0:
                self.solid_accent = hex_c
            self._refresh_manual_stops_ui()
            self._refresh_button_visual_state()

    def _refresh_manual_stops_ui(self) -> None:
        if not hasattr(self, 'manual_stops_layout') or self.manual_stops_layout is None:
            return

        while self.manual_stops_layout.count():
            item = self.manual_stops_layout.takeAt(0)
            if item.widget():
                w = item.widget()
                w.hide()
                w.deleteLater()
            elif item.layout():
                sub_l = item.layout()
                while sub_l.count():
                    sub = sub_l.takeAt(0)
                    if sub.widget():
                        sw = sub.widget()
                        sw.hide()
                        sw.deleteLater()

        if not hasattr(self, 'manual_colors') or not self.manual_colors or len(self.manual_colors) < 2:
            self.manual_colors = ["#ff1744", "#7b1fa2", "#0c0c10"]

        idx_active = max(0, min(getattr(self, 'active_manual_stop_index', 0), len(self.manual_colors) - 1))
        self.active_manual_stop_index = idx_active
        can_remove = len(self.manual_colors) > 2
        active_hex = self.manual_colors[idx_active]

        # 1. Título y lista interactiva de paradas
        lbl_stop_title = QLabel(f"📍 Paradas del Degradado ({len(self.manual_colors)} colores — clic para editar):", self.manual_stops_widget)
        lbl_stop_title.setStyleSheet("color: #00e5ff; font-weight: bold; font-size: 11px; border: none;")
        self.manual_stops_layout.addWidget(lbl_stop_title)

        stops_grid = QGridLayout()
        stops_grid.setContentsMargins(0, 2, 0, 2)
        stops_grid.setSpacing(8)

        for s_idx, stop_c in enumerate(self.manual_colors):
            card_w = QWidget(self.manual_stops_widget)
            card_layout = QHBoxLayout(card_w)
            card_layout.setContentsMargins(4, 2, 4, 2)
            card_layout.setSpacing(6)
            is_sel = (s_idx == idx_active)
            border_color = "#00e5ff" if is_sel else "rgba(255, 255, 255, 0.15)"
            border_w = "2.5px" if is_sel else "1px"
            card_w.setStyleSheet(f"""
                QWidget {{
                    background-color: rgba(255, 255, 255, 0.05);
                    border: {border_w} solid {border_color};
                    border-radius: 8px;
                }}
            """)

            btn_stop = QPushButton(f"Stop {chr(65 + s_idx)}: {stop_c}", card_w)
            btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_stop.setFixedHeight(32)
            text_c = get_contrasting_text_color(stop_c)
            btn_stop.setStyleSheet(f"""
                QPushButton {{
                    background-color: {stop_c};
                    color: {text_c};
                    border: none;
                    border-radius: 6px;
                    font-weight: bold;
                    font-size: 11px;
                    padding: 2px 8px;
                }}
            """)
            btn_stop.clicked.connect(lambda checked, idx=s_idx: self._set_active_manual_stop_index(idx))
            card_layout.addWidget(btn_stop, stretch=1)

            btn_del = QPushButton("✕", card_w)
            btn_del.setFixedSize(26, 26)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor if can_remove else Qt.CursorShape.ForbiddenCursor)
            btn_del.setEnabled(can_remove)
            if can_remove:
                btn_del.setToolTip("Eliminar esta parada de color")
                btn_del.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(255, 23, 68, 0.20);
                        color: #ff1744;
                        font-weight: bold;
                        font-size: 13px;
                        border: 1px solid rgba(255, 23, 68, 0.50);
                        border-radius: 6px;
                        padding: 0px;
                        text-align: center;
                    }
                    QPushButton:hover {
                        background-color: #ff1744;
                        color: #ffffff;
                    }
                """)
                btn_del.clicked.connect(lambda checked, idx=s_idx: self._remove_manual_stop(idx))
            else:
                btn_del.setToolTip("Se requieren mínimo 2 paradas de color")
                btn_del.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(255, 255, 255, 0.05);
                        color: rgba(255, 255, 255, 0.25);
                        border: 1px solid transparent;
                        border-radius: 6px;
                        padding: 0px;
                        text-align: center;
                        font-size: 13px;
                    }
                """)
            card_layout.addWidget(btn_del)

            r, col = divmod(s_idx, 3)
            stops_grid.addWidget(card_w, r, col)

        self.manual_stops_layout.addLayout(stops_grid)

        # 2. Botón principal para elegir color libre con QColorDialog y botón de agregar parada
        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)

        btn_pick = QPushButton(f"🎨 Seleccionar Color Libre para Stop {chr(65 + idx_active)} ({active_hex})...", self.manual_stops_widget)
        btn_pick.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_pick.setStyleSheet("""
            QPushButton {
                background-color: #1a1c29;
                color: #00e5ff;
                font-weight: bold;
                font-size: 11px;
                border: 1.5px solid #00e5ff;
                border-radius: 8px;
                padding: 7px 14px;
            }
            QPushButton:hover {
                background-color: rgba(0, 229, 255, 0.25);
            }
        """)
        btn_pick.clicked.connect(self._pick_manual_active_stop_color)
        actions_row.addWidget(btn_pick, stretch=2)

        btn_add = QPushButton("＋ Agregar Parada", self.manual_stops_widget)
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                color: #ffffff;
                font-weight: bold;
                font-size: 11px;
                border: 1.5px dashed rgba(255, 255, 255, 0.35);
                border-radius: 8px;
                padding: 7px 14px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.18);
                border-color: #ffffff;
            }
        """)
        btn_add.clicked.connect(self._add_manual_stop)
        actions_row.addWidget(btn_add, stretch=1)

        self.manual_stops_layout.addLayout(actions_row)

        # 3. Paleta de colores rápidos para el stop activo
        lbl_palette_title = QLabel(f"🎨 Paleta Rápida para Editar Stop {chr(65 + idx_active)}:", self.manual_stops_widget)
        lbl_palette_title.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 11px; border: none; margin-top: 2px;")
        self.manual_stops_layout.addWidget(lbl_palette_title)

        pal_layout = QHBoxLayout()
        pal_layout.setSpacing(6)
        for hex_c in self.QUICK_PALETTE[:8]:
            btn_c = QPushButton(self.manual_stops_widget)
            btn_c.setFixedSize(32, 32)
            btn_c.setCursor(Qt.CursorShape.PointingHandCursor)
            is_c_active = (hex_c.lower() == active_hex.lower())
            border = "2.5px solid #00e5ff" if is_c_active else "1px solid rgba(255, 255, 255, 0.20)"
            btn_c.setStyleSheet(f"QPushButton {{ background-color: {hex_c}; border-radius: 16px; border: {border}; }} QPushButton:hover {{ border: 2px solid #ffffff; }}")
            btn_c.clicked.connect(lambda checked, c=hex_c: self._select_manual_stop_palette_color(c))
            pal_layout.addWidget(btn_c)
        pal_layout.addStretch()
        self.manual_stops_layout.addLayout(pal_layout)

    def _remove_manual_stop(self, idx: int) -> None:
        if len(self.manual_colors) > 2 and 0 <= idx < len(self.manual_colors):
            self.manual_colors.pop(idx)
            self.active_manual_stop_index = max(0, min(self.active_manual_stop_index, len(self.manual_colors) - 1))
            self._refresh_manual_stops_ui()
            self._refresh_button_visual_state()

    def _add_manual_stop(self) -> None:
        last_c = QColor(self.manual_colors[-1]) if self.manual_colors else QColor("#ff1744")
        accent_c = QColor(getattr(self, 'solid_accent', '#00e5ff'))

        r = (last_c.red() + accent_c.red()) // 2
        g = (last_c.green() + accent_c.green()) // 2
        b = (last_c.blue() + accent_c.blue()) // 2
        new_hex = QColor(r, g, b).name()

        if new_hex == self.manual_colors[-1]:
            new_hex = "#00e5ff" if new_hex != "#00e5ff" else "#e040fb"

        self.manual_colors.append(new_hex)
        self.active_manual_stop_index = len(self.manual_colors) - 1
        self._refresh_manual_stops_ui()
        self._refresh_button_visual_state()

    def _extract_wallpaper_colors(self) -> List[str]:
        def _clean(p: str) -> str:
            if not p:
                return ""
            c = str(p).strip()
            if c.startswith("file://"):
                c = urllib.parse.unquote(c[7:])
            elif c.startswith("file:"):
                c = urllib.parse.unquote(c[5:])
            return os.path.expanduser(c.strip("'\""))

        target_path = _clean(self.bg_image_path)
        if not target_path or not os.path.exists(target_path):
            folder_clean = _clean(self.bg_folder_path)
            if folder_clean and os.path.exists(folder_clean):
                for f in sorted(os.listdir(folder_clean)):
                    if f.startswith('.'):
                        continue
                    fp = os.path.join(folder_clean, f)
                    if os.path.isfile(fp):
                        pix = get_cached_pixmap(fp, 0, 0)
                        if pix and not pix.isNull():
                            target_path = fp
                            break

        if target_path and os.path.exists(target_path):
            pix = get_cached_pixmap(target_path, 0, 0)
            if pix and not pix.isNull():
                colors = extract_dominant_gradient_colors(pix, max_colors=4)
                if colors and len(colors) >= 2:
                    return colors
                vibrant = extract_vibrant_accent_color(pix)
                return [vibrant, "#1a1c29"]
        return ["#ff1744", "#7b1fa2"]

    def _get_default_pictures_dir(self) -> str:
        if self.bg_folder_path and os.path.exists(self.bg_folder_path):
            return self.bg_folder_path
        pics = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation)
        if pics and os.path.exists(pics):
            return pics
        home = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.HomeLocation) or os.path.expanduser("~")
        if home and os.path.exists(home):
            return home
        return ""

    def _choose_bg_image(self) -> None:
        initial_dir = self._get_default_pictures_dir()
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Imagen de Fondo",
            initial_dir,
            "Imágenes (*.png *.jpg *.jpeg *.webp *.jfif *.bmp);;Todos los archivos (*)"
        )
        if path:
            self.bg_image_path = path
            self.background_type = "image"
            self._select_image_mode()
            self.lbl_selected_img_info.setText(f"Imagen seleccionada: {os.path.basename(path)}")
            wp_colors = self._extract_wallpaper_colors()
            if wp_colors:
                self.wallpaper_gradient_colors = wp_colors
                self.auto_colors = wp_colors
                self.solid_accent = wp_colors[0]
            if getattr(self, 'button_color_source', 'wallpaper') != "custom":
                self.button_color_source = "wallpaper"
                if hasattr(self, 'radio_src_wallpaper') and self.radio_src_wallpaper:
                    self.radio_src_wallpaper.setChecked(True)
            if not hasattr(self, 'bg_theme_colors'):
                self.bg_theme_colors = dict(self.cfg.get("bg_theme_colors", {}))
            self.bg_theme_colors[path] = self.solid_accent
            self._refresh_button_swatches_ui()
            self._refresh_button_visual_state()

    def _choose_bg_folder(self) -> None:
        initial_dir = self._get_default_pictures_dir()
        folder = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar Carpeta de Fondos",
            initial_dir
        )
        if folder:
            self.bg_folder_path = folder
            self.background_type = "image"
            self._select_image_mode()
            self.lbl_selected_folder_info.setText(f"Carpeta activa: {os.path.basename(folder) or folder}")
            wp_colors = self._extract_wallpaper_colors()
            if wp_colors:
                self.wallpaper_gradient_colors = wp_colors
                self.auto_colors = wp_colors
                self.solid_accent = wp_colors[0]
            if getattr(self, 'button_color_source', 'wallpaper') != "custom":
                self.button_color_source = "wallpaper"
                if hasattr(self, 'radio_src_wallpaper') and self.radio_src_wallpaper:
                    self.radio_src_wallpaper.setChecked(True)
            self._refresh_button_swatches_ui()
            self._refresh_button_visual_state()

    def _choose_inner_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Imagen Personalizada de Carátula Global",
            "",
            "Imágenes (*.png *.jpg *.jpeg *.webp *.jfif *.bmp);;Todos los archivos (*)"
        )
        if path:
            self.custom_inner_image = path
            self.radio_art_custom.setChecked(True)
            self.inner_art_mode = "custom_always"
            if hasattr(self, 'btn_choose_inner') and self.btn_choose_inner:
                self.btn_choose_inner.setText(f"🖼️ Carátula Fija: {os.path.basename(path)}")

    def _apply_dialog_font(self, font_name: str) -> None:
        clean_font = (font_name or "Sans Serif").strip() or "Sans Serif"
        self.font_family = clean_font
        self.setStyleSheet(self._build_dialog_stylesheet(clean_font))
        from ui.font_manager import apply_font_family_to_tree
        apply_font_family_to_tree(self, clean_font)
        self._update_font_preview(clean_font)

    def _on_font_family_changed(self, font_name: str) -> None:
        if font_name:
            if hasattr(self, 'font_path_map') and font_name in self.font_path_map:
                self.custom_font_path = self.font_path_map[font_name]
            self._apply_dialog_font(font_name)

    def _browse_custom_font(self) -> None:
        default_dir = os.path.expanduser("~/Documentos/tipografia")
        if not os.path.exists(default_dir):
            default_dir = os.path.expanduser("~")

        path, _ = QFileDialog.getOpenFileName(
            self,
            f"Seleccionar Archivo de Fuente para {self.mode_label}",
            default_dir,
            "Fuentes y Zips (*.ttf *.otf *.zip);;Fuentes TrueType / OpenType (*.ttf *.otf);;Archivos Zip (*.zip);;Todos los archivos (*)"
        )
        if path:
            from ui.font_manager import load_custom_font
            fam = load_custom_font(path)
            if fam:
                self.custom_font_path = path
                if hasattr(self, 'font_path_map'):
                    self.font_path_map[fam] = path
                idx = self.combo_font.findText(fam)
                if idx >= 0:
                    self.combo_font.setCurrentIndex(idx)
                else:
                    self.combo_font.insertItem(0, fam)
                    self.combo_font.setCurrentIndex(0)
                self._apply_dialog_font(fam)
            else:
                QMessageBox.warning(self, "Fuente no compatible", f"No se pudo cargar la tipografía desde:\n{path}")

    def _reset_font_default(self) -> None:
        self.custom_font_path = ""
        idx = self.combo_font.findText("Sans Serif")
        if idx >= 0:
            self.combo_font.setCurrentIndex(idx)
        else:
            self.combo_font.setCurrentText("Sans Serif")
        self._apply_dialog_font("Sans Serif")

    def _update_font_preview(self, font_family: str) -> None:
        fam = font_family or "Sans Serif"
        if hasattr(self, 'lbl_font_preview_title') and self.lbl_font_preview_title:
            self.lbl_font_preview_title.setFont(QFont(fam, 13, QFont.Weight.Bold))
        if hasattr(self, 'lbl_font_preview_body') and self.lbl_font_preview_body:
            self.lbl_font_preview_body.setFont(QFont(fam, 10))

    def _update_mode_tab_styles(self) -> None:
        clean_accent = (getattr(self, 'solid_accent', '#ff1744') or '#ff1744').split(';')[0].strip()
        tabs = [
            ("normal", getattr(self, 'btn_mode_tab_normal', None)),
            ("compact", getattr(self, 'btn_mode_tab_compact', None)),
            ("expanded", getattr(self, 'btn_mode_tab_expanded', None)),
        ]
        for m_name, btn in tabs:
            if btn:
                is_active = (self.mode == m_name)
                if is_active:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {clean_accent};
                            color: #ffffff;
                            border: 1.5px solid #ffffff;
                            border-radius: 10px;
                            font-weight: bold;
                            font-size: 12px;
                            padding: 4px 12px;
                        }}
                    """)
                else:
                    btn.setStyleSheet("""
                        QPushButton {{
                            background-color: rgba(255, 255, 255, 0.08);
                            color: rgba(255, 255, 255, 0.70);
                            border: 1px solid rgba(255, 255, 255, 0.15);
                            border-radius: 10px;
                            font-weight: bold;
                            font-size: 12px;
                            padding: 4px 12px;
                        }}
                        QPushButton:hover {{
                            background-color: rgba(255, 255, 255, 0.18);
                            color: #ffffff;
                            border: 1px solid rgba(255, 255, 255, 0.35);
                        }}
                    """)

    def _collect_current_ui_state(self) -> dict:
        aspect_keys = ["stretch", "fill", "fit"]
        aspect_mode = aspect_keys[self.combo_aspect.currentIndex()] if hasattr(self, 'combo_aspect') else getattr(self, 'aspect_mode', 'stretch')
        inner_art_mode = "custom_always" if (hasattr(self, 'radio_art_custom') and self.radio_art_custom.isChecked()) else "auto"
        slideshow_enabled = self.chk_slideshow.isChecked() if hasattr(self, 'chk_slideshow') else getattr(self, 'slideshow_enabled', True)
        stays_on_top = self.chk_top.isChecked() if hasattr(self, 'chk_top') else getattr(self, 'stays_on_top', False)
        btn_gradient_effect = self.chk_btn_gradient.isChecked() if hasattr(self, 'chk_btn_gradient') else getattr(self, 'btn_gradient_effect', True)

        brand_input = self.input_brand_name.text().strip() if hasattr(self, 'input_brand_name') else ""
        brand_name = brand_input if brand_input else "RED WORLD"

        source = "gradient"
        if hasattr(self, 'radio_src_wallpaper') and self.radio_src_wallpaper.isChecked():
            source = "wallpaper"
        elif hasattr(self, 'radio_src_custom') and self.radio_src_custom.isChecked():
            source = "custom"
        elif hasattr(self, 'radio_src_gradient') and self.radio_src_gradient.isChecked():
            source = "gradient"

        if getattr(self, 'background_type', 'gradient') == "gradient" and source == "wallpaper":
            source = "gradient"

        bg_colors = dict(getattr(self, 'bg_theme_colors', self.cfg.get("bg_theme_colors", {})))
        if getattr(self, 'bg_image_path', ''):
            bg_colors[self.bg_image_path] = getattr(self, 'solid_accent', '#ff1744')

        vis_style = getattr(self, 'expanded_visualizer_style', 'radial_waves')
        if hasattr(self, 'radio_vis_vinyl') and self.radio_vis_vinyl.isChecked():
            vis_style = "vinyl"
        elif hasattr(self, 'radio_vis_card') and self.radio_vis_card.isChecked():
            vis_style = "card_glow"
        elif hasattr(self, 'radio_vis_radial') and self.radio_vis_radial.isChecked():
            vis_style = "radial_waves"

        cover_shape = "rounded"
        if hasattr(self, 'radio_shape_heart') and self.radio_shape_heart.isChecked():
            cover_shape = "heart"
        elif hasattr(self, 'radio_shape_circle') and self.radio_shape_circle.isChecked():
            cover_shape = "circle"

        return {
            "background_type": getattr(self, 'background_type', 'gradient'),
            "theme_mode": getattr(self, 'theme_mode', 'gradient_auto'),
            "button_color_source": source,
            "btn_gradient_effect": btn_gradient_effect,
            "wallpaper_btn_gradient_effect": btn_gradient_effect if source == "wallpaper" else False,
            "auto_extract_wallpaper_color": getattr(self, 'auto_extract_wallpaper_color', True),
            "manual_gradient_colors": list(getattr(self, 'manual_colors', ["#ff1744", "#7b1fa2", "#0c0c10"])),
            "accent_color": getattr(self, 'solid_accent', '#ff1744'),
            "auto_gradient_colors": list(getattr(self, 'auto_colors', ["#2b0b10", "#180718", "#08060c"])),
            "wallpaper_gradient_colors": list(getattr(self, 'wallpaper_gradient_colors', getattr(self, 'auto_colors', ["#ff1744", "#7b1fa2"]))),
            "custom_btn_gradient_colors": list(getattr(self, 'custom_btn_gradient_colors', ["#ff1744", "#00e5ff", "#e040fb"])),
            "custom_button_swatches": list(getattr(self, 'custom_button_swatches', ["#ff1744", "#00e5ff", "#e040fb", "#00e676", "#ff9100", "#ff4081"])),
            "background_image": getattr(self, 'bg_image_path', ""),
            "bg_folder": getattr(self, 'bg_folder_path', ""),
            "bg_slideshow_enabled": slideshow_enabled,
            "bg_aspect_mode": aspect_mode,
            "bg_theme_colors": bg_colors,
            "inner_art_mode": inner_art_mode,
            "custom_inner_image": getattr(self, 'custom_inner_image', ""),
            "cover_shape": cover_shape,
            "expanded_visualizer_style": vis_style,
            "stays_on_top": stays_on_top,
            "brand_name": brand_name,
            "font_family": getattr(self, 'font_family', "Sans Serif"),
            "custom_font_path": getattr(self, 'custom_font_path', ""),
        }

    def _switch_editing_mode(self, target_mode: str) -> None:
        c_target = "normal" if target_mode in ("normal", "small", None) else target_mode
        if c_target == self.mode:
            return
        self.per_mode_configs[self.mode] = self._collect_current_ui_state()
        self.mode = c_target
        self.mode_label = {
            "normal": "Modo Pequeño",
            "compact": "Modo Compacto",
            "expanded": "Modo Expandido"
        }.get(self.mode, "Modo Pequeño")
        self._load_mode_state(self.per_mode_configs[self.mode])
        self._update_mode_tab_styles()

    def _load_mode_state(self, cfg: dict) -> None:
        self.cfg = dict(cfg)
        self.background_type = self.cfg.get("background_type", "gradient")
        self.theme_mode = self.cfg.get("theme_mode", "gradient_auto")
        self.button_color_source = self.cfg.get("button_color_source", "wallpaper" if self.background_type == "image" else "gradient")
        self.btn_gradient_effect = self.cfg.get("btn_gradient_effect", True)
        self.auto_extract_wallpaper_color = self.cfg.get("auto_extract_wallpaper_color", True)

        self.manual_colors = list(self.cfg.get("manual_gradient_colors", ["#ff1744", "#7b1fa2", "#0c0c10"]))
        self.solid_accent = self.cfg.get("accent_color", "#ff1744")
        self.auto_colors = list(self.cfg.get("auto_gradient_colors", ["#2b0b10", "#180718", "#08060c"]))
        self.wallpaper_gradient_colors = list(self.cfg.get("wallpaper_gradient_colors", ["#ff1744", "#7b1fa2"]))
        self.custom_btn_gradient_colors = list(self.cfg.get("custom_btn_gradient_colors", ["#ff1744", "#00e5ff", "#e040fb"]))
        self.custom_button_swatches = list(self.cfg.get("custom_button_swatches", ["#ff1744", "#00e5ff", "#e040fb", "#00e676", "#ff9100", "#ff4081"]))

        self.bg_image_path = self.cfg.get("background_image", "")
        self.bg_folder_path = self.cfg.get("bg_folder", "")
        self.bg_theme_colors = dict(self.cfg.get("bg_theme_colors", {}))
        self.slideshow_enabled = self.cfg.get("bg_slideshow_enabled", True)
        self.aspect_mode = self.cfg.get("bg_aspect_mode", "stretch")

        self.inner_art_mode = self.cfg.get("inner_art_mode", "auto")
        self.custom_inner_image = self.cfg.get("custom_inner_image", "")
        self.cover_shape = self.cfg.get("cover_shape", "rounded")
        self.expanded_visualizer_style = self.cfg.get("expanded_visualizer_style", "radial_waves")
        self.stays_on_top = self.cfg.get("stays_on_top", False)
        self.brand_name = self.cfg.get("brand_name", "RED WORLD")
        self.font_family = self.cfg.get("font_family", "Sans Serif")
        self.custom_font_path = self.cfg.get("custom_font_path", "")

        # Update input_brand_name & chk_top
        if hasattr(self, 'input_brand_name') and self.input_brand_name:
            self.input_brand_name.setText(self.brand_name)
        if hasattr(self, 'chk_top') and self.chk_top:
            self.chk_top.setChecked(self.stays_on_top)

        # Update background type radio
        if hasattr(self, 'radio_bg_type_image') and hasattr(self, 'radio_bg_type_gradient'):
            if self.background_type == "image":
                self.radio_bg_type_image.setChecked(True)
            else:
                self.radio_bg_type_gradient.setChecked(True)

        # Update theme mode radio
        if hasattr(self, 'radio_auto') and hasattr(self, 'radio_manual') and hasattr(self, 'radio_solid'):
            if self.theme_mode == "gradient_auto":
                self.radio_auto.setChecked(True)
            elif self.theme_mode == "gradient_manual":
                self.radio_manual.setChecked(True)
            else:
                self.radio_solid.setChecked(True)

        # Update button source
        if hasattr(self, 'radio_src_gradient') and hasattr(self, 'radio_src_wallpaper') and hasattr(self, 'radio_src_custom'):
            if self.button_color_source == "gradient":
                self.radio_src_gradient.setChecked(True)
            elif self.button_color_source == "custom":
                self.radio_src_custom.setChecked(True)
            else:
                self.radio_src_wallpaper.setChecked(True)

        if hasattr(self, 'chk_btn_gradient') and self.chk_btn_gradient:
            self.chk_btn_gradient.setChecked(self.btn_gradient_effect)

        # Update wallpaper info labels
        if hasattr(self, 'lbl_selected_img_info') and self.lbl_selected_img_info:
            img_name = os.path.basename(self.bg_image_path) if self.bg_image_path else "Ninguna"
            self.lbl_selected_img_info.setText(f"Imagen seleccionada: {img_name}")
        if hasattr(self, 'lbl_selected_folder_info') and self.lbl_selected_folder_info:
            folder_name = os.path.basename(self.bg_folder_path) or self.bg_folder_path if self.bg_folder_path else "Ninguna"
            self.lbl_selected_folder_info.setText(f"Carpeta activa: {folder_name}")
        if hasattr(self, 'chk_slideshow') and self.chk_slideshow:
            self.chk_slideshow.setChecked(self.slideshow_enabled)
        if hasattr(self, 'combo_aspect') and self.combo_aspect:
            aspect_keys = ["stretch", "fill", "fit"]
            if self.aspect_mode in aspect_keys:
                self.combo_aspect.setCurrentIndex(aspect_keys.index(self.aspect_mode))

        # Update inner art & cover shape
        if hasattr(self, 'radio_art_custom') and hasattr(self, 'radio_art_auto'):
            if self.inner_art_mode == "custom_always":
                self.radio_art_custom.setChecked(True)
            else:
                self.radio_art_auto.setChecked(True)
        if hasattr(self, 'btn_choose_inner') and self.btn_choose_inner:
            if self.custom_inner_image:
                self.btn_choose_inner.setText(f"🖼️ Carátula Fija: {os.path.basename(self.custom_inner_image)}")
            else:
                self.btn_choose_inner.setText("🖼️ Cambiar Imagen Personalizada Fija...")

        if hasattr(self, 'radio_shape_circle') and hasattr(self, 'radio_shape_rounded') and hasattr(self, 'radio_shape_heart'):
            if self.cover_shape == "circle":
                self.radio_shape_circle.setChecked(True)
            elif self.cover_shape == "heart":
                self.radio_shape_heart.setChecked(True)
            else:
                self.radio_shape_rounded.setChecked(True)

        # Update visualizer style container
        if hasattr(self, 'sec_expanded_vis_container') and self.sec_expanded_vis_container:
            self.sec_expanded_vis_container.setVisible(self.mode == "expanded")
            if self.mode == "expanded":
                if hasattr(self, 'radio_vis_vinyl') and hasattr(self, 'radio_vis_card') and hasattr(self, 'radio_vis_radial'):
                    if self.expanded_visualizer_style == "vinyl":
                        self.radio_vis_vinyl.setChecked(True)
                    elif self.expanded_visualizer_style == "card_glow":
                        self.radio_vis_card.setChecked(True)
                    else:
                        self.radio_vis_radial.setChecked(True)

        # Update fonts
        if hasattr(self, 'combo_font') and self.combo_font:
            idx = self.combo_font.findText(self.font_family)
            if idx >= 0:
                self.combo_font.setCurrentIndex(idx)
            else:
                self.combo_font.setCurrentText(self.font_family)

        # Update labels & badges
        if hasattr(self, 'lbl_mode_badge') and self.lbl_mode_badge:
            self.lbl_mode_badge.setText(self.mode_label)
        if hasattr(self, 'lbl_font_badge') and self.lbl_font_badge:
            self.lbl_font_badge.setText(self.mode_label)
        if hasattr(self, 'lbl_font_desc') and self.lbl_font_desc:
            self.lbl_font_desc.setText(f"Personaliza la tipografía de todos los textos, títulos y letras para {self.mode_label}:")

        self.setWindowTitle(f"⚙️ Personalización — {self.mode_label}")
        self._refresh_manual_stops_ui()
        self._update_solid_panel_ui()
        self._refresh_button_visual_state()
        self._update_section_highlights()
        self._apply_dialog_font(self.font_family)

    def _on_apply_clicked(self) -> None:
        self.per_mode_configs[self.mode] = self._collect_current_ui_state()

        for m, m_cfg in self.per_mode_configs.items():
            self.config_manager.set_personalization_dict(m, m_cfg)

        self.settings_saved.emit(self.per_mode_configs[self.mode], self.mode)
        self.accept()
