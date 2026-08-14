import os
from typing import List, Optional, Dict, Any
from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QBrush, QPen, QFont, QPixmap
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QRadioButton, QButtonGroup, QFrame, QScrollArea, QWidget, QSizePolicy,
    QColorDialog, QFileDialog, QCheckBox, QComboBox, QLineEdit, QMessageBox, QApplication
)

from ui.color_extractor import extract_vibrant_accent_color, get_contrasting_text_color, extract_dominant_gradient_colors

class GradientPreviewWidget(QWidget):
    """Widget de previsualización en vivo del degradado multi-parada."""
    def __init__(self, colors: List[str], btn_gradient: bool = False, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.colors = colors
        self.btn_gradient = btn_gradient
        self.setFixedHeight(75)

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
        btn_w, btn_h = 150.0, 34.0
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
    """Ventana emergente de personalización unificada directa (Degradado vs Imagen, Efecto Botones y Extracción de Color)."""
    settings_saved = pyqtSignal(dict)

    PRESETS = [
        ("💗 APT. (Rosa & Negro)", ["#ff4081", "#8e24aa", "#14070e"]),
        ("🌌 Aurora Boreal", ["#00e5ff", "#7c4dff", "#0c051a"]),
        ("🔥 Sunset Neón", ["#ff9100", "#ff1744", "#1a080c"]),
        ("🟢 Esmeralda Ciberpunk", ["#00e676", "#00838f", "#04140d"]),
        ("🟣 Vía Láctea", ["#e040fb", "#311b92", "#080512"])
    ]

    def __init__(self, current_config: dict, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("⚙️ Personalización Completa del Reproductor")
        self.setMinimumSize(560, 480)

        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            w = min(620, int(avail.width() * 0.9))
            h = min(740, int(avail.height() * 0.85))
            self.resize(w, h)
        else:
            self.resize(580, 650)

        self.cfg = dict(current_config)

        self.background_type = self.cfg.get("background_type", "gradient")
        self.theme_mode = self.cfg.get("theme_mode", "gradient_auto")
        self.button_color_source = self.cfg.get("button_color_source", "wallpaper" if self.background_type == "image" else "gradient")
        self.btn_gradient_effect = self.cfg.get("btn_gradient_effect", True)
        self.auto_extract_wallpaper_color = self.cfg.get("auto_extract_wallpaper_color", True)

        self.manual_colors = list(self.cfg.get("manual_gradient_colors", ["#ff1744", "#7b1fa2", "#0c0c10"]))
        self.solid_accent = self.cfg.get("accent_color", "#ff1744")
        self.auto_colors = list(self.cfg.get("auto_gradient_colors", ["#2b0b10", "#180718", "#08060c"]))
        self.custom_btn_gradient_colors = list(self.cfg.get("custom_btn_gradient_colors", ["#ff1744", "#00e5ff", "#e040fb"]))
        self.custom_button_swatches = list(self.cfg.get("custom_button_swatches", ["#ff1744", "#00e5ff", "#e040fb", "#00e676", "#ff9100", "#ff4081"]))
        self.active_gradient_stop_index: int = 0

        self.bg_image_path = self.cfg.get("background_image", "")
        self.bg_folder_path = self.cfg.get("bg_folder", "")
        self.slideshow_enabled = self.cfg.get("bg_slideshow_enabled", True)
        self.aspect_mode = self.cfg.get("bg_aspect_mode", "stretch")

        self.inner_art_mode = self.cfg.get("inner_art_mode", "auto")
        self.custom_inner_image = self.cfg.get("custom_inner_image", "")
        self.stays_on_top = self.cfg.get("stays_on_top", False)
        self.brand_name = self.cfg.get("brand_name", "RED WORLD")

        self.init_ui()

    def init_ui(self) -> None:
        self.setStyleSheet("""
            QDialog {
                background-color: #0d0e15;
                color: #ffffff;
                font-family: 'Sans Serif', sans-serif;
            }
            QLabel {
                color: #ffffff;
            }
            QRadioButton, QCheckBox {
                color: #ffffff;
                font-weight: bold;
                font-size: 12px;
                spacing: 8px;
            }
            QRadioButton::indicator, QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 2px solid #ff1744;
            }
            QRadioButton::indicator {
                border-radius: 8px;
            }
            QRadioButton::indicator:checked, QCheckBox::indicator:checked {
                background-color: #ff1744;
            }
            QPushButton {
                background-color: #1a1c29;
                color: #ffffff;
                border: 1px solid #33364d;
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #2a2d42;
                border-color: #ff1744;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)
        title_lbl = QLabel("⚙️ PERSONALIZACIÓN & TEMAS", self)
        title_lbl.setFont(QFont("Sans Serif", 14, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {self.solid_accent}; letter-spacing: 1px;")
        header_layout.addWidget(title_lbl)

        subtitle_lbl = QLabel("Ajusta la apariencia visual, carátulas y comportamiento del reproductor", self)
        subtitle_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        header_layout.addWidget(subtitle_lbl)
        layout.addLayout(header_layout)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_content = QWidget()
        sc_layout = QVBoxLayout(scroll_content)
        sc_layout.setContentsMargins(0, 4, 4, 4)
        sc_layout.setSpacing(16)

        # --------------------------------------------------------
        # CATEGORÍA 1: 🎨 APARIENCIA & TEMA
        # --------------------------------------------------------
        self.sec_bg_box = QFrame(scroll_content)
        self.sec_bg_box.setStyleSheet(f"QFrame {{ background-color: #121420; border-radius: 14px; border: 1.5px solid {self.solid_accent}; }}")
        sec_bg_layout = QVBoxLayout(self.sec_bg_box)
        sec_bg_layout.setContentsMargins(16, 14, 16, 14)
        sec_bg_layout.setSpacing(12)

        lbl_bg_title = QLabel("🎨 1. APARIENCIA & TEMA", self.sec_bg_box)
        lbl_bg_title.setFont(QFont("Sans Serif", 11, QFont.Weight.Bold))
        lbl_bg_title.setStyleSheet("color: #ffffff; border: none;")
        sec_bg_layout.addWidget(lbl_bg_title)

        # Selector principal de tipo de fondo
        self.bg_type_group = QButtonGroup(self)
        self.radio_bg_type_gradient = QRadioButton("🎨 Fondo en Degradado Multi-Color", self.sec_bg_box)
        self.radio_bg_type_image = QRadioButton("🖼️ Fondo de Imagen de Pantalla (Wallpaper)", self.sec_bg_box)
        self.bg_type_group.addButton(self.radio_bg_type_gradient)
        self.bg_type_group.addButton(self.radio_bg_type_image)

        if self.background_type == "image":
            self.radio_bg_type_image.setChecked(True)
        else:
            self.radio_bg_type_gradient.setChecked(True)

        self.radio_bg_type_gradient.toggled.connect(self._on_bg_type_toggled)
        self.radio_bg_type_image.toggled.connect(self._on_bg_type_toggled)

        bg_mode_row = QHBoxLayout()
        bg_mode_row.addWidget(self.radio_bg_type_gradient)
        bg_mode_row.addWidget(self.radio_bg_type_image)
        sec_bg_layout.addLayout(bg_mode_row)

        # Panel de Opciones de Fondo en Degradado
        self.panel_bg_gradient = QWidget(self.sec_bg_box)
        panel_grad_layout = QVBoxLayout(self.panel_bg_gradient)
        panel_grad_layout.setContentsMargins(0, 4, 0, 0)
        panel_grad_layout.setSpacing(8)

        theme_group = QButtonGroup(self)
        self.radio_auto = QRadioButton("✨ Automático (Extraído de carátula de música)", self.panel_bg_gradient)
        self.radio_manual = QRadioButton("🎨 Manual Multi-Color (Presets rápidos)", self.panel_bg_gradient)
        self.radio_solid = QRadioButton("🔴 Color Sólido Neón", self.panel_bg_gradient)
        theme_group.addButton(self.radio_auto)
        theme_group.addButton(self.radio_manual)
        theme_group.addButton(self.radio_solid)

        if self.theme_mode == "gradient_auto":
            self.radio_auto.setChecked(True)
        elif self.theme_mode == "gradient_manual":
            self.radio_manual.setChecked(True)
        else:
            self.radio_solid.setChecked(True)

        self.radio_auto.toggled.connect(self._select_gradient_mode)
        self.radio_manual.toggled.connect(self._select_gradient_mode)
        self.radio_solid.toggled.connect(self._select_gradient_mode)

        panel_grad_layout.addWidget(self.radio_auto)
        panel_grad_layout.addWidget(self.radio_manual)

        self.manual_panel = QWidget(self.panel_bg_gradient)
        manual_layout = QVBoxLayout(self.manual_panel)
        manual_layout.setContentsMargins(0, 4, 0, 4)
        manual_layout.setSpacing(6)

        presets_layout = QGridLayout()
        presets_layout.setSpacing(6)
        for idx, (name, p_colors) in enumerate(self.PRESETS[:4]):
            btn_p = QPushButton(name, self.manual_panel)
            btn_p.clicked.connect(lambda checked, c=p_colors: self._apply_preset(c))
            row, col = divmod(idx, 2)
            presets_layout.addWidget(btn_p, row, col)
        manual_layout.addLayout(presets_layout)

        panel_grad_layout.addWidget(self.manual_panel)
        panel_grad_layout.addWidget(self.radio_solid)
        sec_bg_layout.addWidget(self.panel_bg_gradient)

        # Panel de Opciones de Wallpaper
        self.panel_bg_image = QWidget(self.sec_bg_box)
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

        sec_bg_layout.addWidget(self.panel_bg_image)

        # Sub-sección Estilo y Colores de Botones
        sep_btn = QFrame(self.sec_bg_box)
        sep_btn.setFrameShape(QFrame.Shape.HLine)
        sep_btn.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); border: none;")
        sec_bg_layout.addWidget(sep_btn)

        lbl_btn_title = QLabel("🎛️ Estilo y Color de los Botones", self.sec_bg_box)
        lbl_btn_title.setFont(QFont("Sans Serif", 10, QFont.Weight.Bold))
        lbl_btn_title.setStyleSheet("color: #00e5ff; border: none;")
        sec_bg_layout.addWidget(lbl_btn_title)

        # Previsualización en Vivo Única del Botón ("Botón Ejemplo")
        self.btn_preview_widget = GradientPreviewWidget(self._get_active_colors_for_preview(), self.btn_gradient_effect, self.sec_bg_box)
        sec_bg_layout.addWidget(self.btn_preview_widget)

        # Grupo de Fuente de Color para Botones (3 Opciones)
        lbl_src_title = QLabel("Origen del color de los botones:", self.sec_bg_box)
        lbl_src_title.setStyleSheet("color: #a0aec0; font-size: 11px; font-weight: bold; border: none;")
        sec_bg_layout.addWidget(lbl_src_title)

        self.btn_src_group = QButtonGroup(self)
        self.radio_src_gradient = QRadioButton("🎨 Usar Colores del Tema en Degradado", self.sec_bg_box)
        self.radio_src_wallpaper = QRadioButton("🖼️ Usar Colores Extraídos del Wallpaper", self.sec_bg_box)
        self.radio_src_custom = QRadioButton("🔮 Usar Color / Degradado Libre e Independiente", self.sec_bg_box)
        self.btn_src_group.addButton(self.radio_src_gradient)
        self.btn_src_group.addButton(self.radio_src_wallpaper)
        self.btn_src_group.addButton(self.radio_src_custom)

        if self.button_color_source == "gradient":
            self.radio_src_gradient.setChecked(True)
        elif self.button_color_source == "custom":
            self.radio_src_custom.setChecked(True)
        else:
            self.radio_src_wallpaper.setChecked(True)

        self.radio_src_gradient.toggled.connect(self._on_btn_source_changed)
        self.radio_src_wallpaper.toggled.connect(self._on_btn_source_changed)
        self.radio_src_custom.toggled.connect(self._on_btn_source_changed)

        sec_bg_layout.addWidget(self.radio_src_gradient)
        sec_bg_layout.addWidget(self.radio_src_wallpaper)
        sec_bg_layout.addWidget(self.radio_src_custom)

        # Swatches interactivos para botones
        self.btn_swatches_layout = QGridLayout()
        self.btn_swatches_layout.setSpacing(6)
        sec_bg_layout.addLayout(self.btn_swatches_layout)

        # Botón para Color Personalizado
        self.btn_custom_picker = QPushButton("🎨 Seleccionar Color Personalizado para Botones...", self.sec_bg_box)
        self.btn_custom_picker.setStyleSheet("QPushButton { background-color: #1a1c29; color: #00e5ff; border: 1px solid #2a2d42; border-radius: 8px; font-weight: bold; padding: 6px 12px; } QPushButton:hover { background-color: #24273b; }")
        self.btn_custom_picker.clicked.connect(self._pick_custom_button_color)
        sec_bg_layout.addWidget(self.btn_custom_picker)

        # Checkbox para Degradado en Botones
        self.chk_btn_gradient = QCheckBox("🎨 Aplicar efecto de degradado a los botones", self.sec_bg_box)
        self.chk_btn_gradient.setChecked(self.btn_gradient_effect)
        self.chk_btn_gradient.toggled.connect(self._on_btn_gradient_toggled)
        sec_bg_layout.addWidget(self.chk_btn_gradient)

        sc_layout.addWidget(self.sec_bg_box)

        # --------------------------------------------------------
        # CATEGORÍA 2: 🖼️ CARÁTULA & RECUADRO CENTRAL
        # --------------------------------------------------------
        self.sec_c_box = QFrame(scroll_content)
        self.sec_c_box.setStyleSheet("QFrame { background-color: #121420; border-radius: 14px; border: 1px solid rgba(255, 255, 255, 0.12); }")
        sec_c_layout = QVBoxLayout(self.sec_c_box)
        sec_c_layout.setContentsMargins(16, 14, 16, 14)
        sec_c_layout.setSpacing(10)

        lbl_art_title = QLabel("🖼️ 2. CARÁTULA & RECUADRO CENTRAL", self.sec_c_box)
        lbl_art_title.setFont(QFont("Sans Serif", 11, QFont.Weight.Bold))
        lbl_art_title.setStyleSheet("color: #ffffff; border: none;")
        sec_c_layout.addWidget(lbl_art_title)

        self.radio_art_auto = QRadioButton("🎵 Mostrar Carátula de la Canción (Automático)", self.sec_c_box)
        self.radio_art_custom = QRadioButton("📌 Mostrar SIEMPRE Imagen Personalizada Fija", self.sec_c_box)
        art_group = QButtonGroup(self)
        art_group.addButton(self.radio_art_auto)
        art_group.addButton(self.radio_art_custom)

        if self.inner_art_mode == "custom_always":
            self.radio_art_custom.setChecked(True)
        else:
            self.radio_art_auto.setChecked(True)

        sec_c_layout.addWidget(self.radio_art_auto)
        sec_c_layout.addWidget(self.radio_art_custom)

        self.btn_choose_inner = QPushButton("🖼️ Cambiar Imagen Personalizada Fija...", self.sec_c_box)
        self.btn_choose_inner.clicked.connect(self._choose_inner_image)
        sec_c_layout.addWidget(self.btn_choose_inner)

        sc_layout.addWidget(self.sec_c_box)

        # --------------------------------------------------------
        # CATEGORÍA 3: 🎧 SISTEMA & REPRODUCTOR
        # --------------------------------------------------------
        self.sec_brand_box = QFrame(scroll_content)
        self.sec_brand_box.setStyleSheet("QFrame { background-color: #121420; border-radius: 14px; border: 1px solid rgba(255, 255, 255, 0.12); }")
        sec_brand_layout = QVBoxLayout(self.sec_brand_box)
        sec_brand_layout.setContentsMargins(16, 14, 16, 14)
        sec_brand_layout.setSpacing(10)

        lbl_sys_title = QLabel("🎧 3. SISTEMA & COMPORTAMIENTO", self.sec_brand_box)
        lbl_sys_title.setFont(QFont("Sans Serif", 11, QFont.Weight.Bold))
        lbl_sys_title.setStyleSheet("color: #ffffff; border: none;")
        sec_brand_layout.addWidget(lbl_sys_title)

        lbl_brand_desc = QLabel("Título / Marca mostrado en cabecera:", self.sec_brand_box)
        lbl_brand_desc.setStyleSheet("color: #a0aec0; font-size: 11px; border: none;")
        sec_brand_layout.addWidget(lbl_brand_desc)

        self.input_brand_name = QLineEdit(self.sec_brand_box)
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
        sec_brand_layout.addWidget(self.input_brand_name)

        self.chk_top = QCheckBox("📌 Ventana Siempre Encima (Stays on Top)", self.sec_brand_box)
        self.chk_top.setChecked(self.stays_on_top)
        sec_brand_layout.addWidget(self.chk_top)

        sc_layout.addWidget(self.sec_brand_box)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, stretch=1)

        # Botones de Acción final
        actions_layout = QHBoxLayout()
        actions_layout.addStretch()

        btn_cancel = QPushButton("Cancelar", self)
        btn_cancel.clicked.connect(self.reject)
        actions_layout.addWidget(btn_cancel)

        self.btn_apply = QPushButton("💾 Guardar y Aplicar", self)
        self.btn_apply.setStyleSheet(f"QPushButton {{ background-color: {self.solid_accent}; color: #ffffff; font-weight: bold; padding: 8px 20px; border-radius: 10px; border: none; }} QPushButton:hover {{ opacity: 0.85; }}")
        self.btn_apply.clicked.connect(self._on_apply_clicked)
        actions_layout.addWidget(self.btn_apply)

        layout.addLayout(actions_layout)

        self._on_bg_type_toggled()
        self._refresh_button_swatches_ui()
        self._update_section_highlights()

    def _is_button_gradient_enabled(self) -> bool:
        if hasattr(self, 'chk_btn_gradient') and self.chk_btn_gradient is not None:
            return bool(self.chk_btn_gradient.isChecked())
        return bool(getattr(self, 'btn_gradient_effect', True))

    def _get_active_button_colors(self) -> List[str]:
        if not self._is_button_gradient_enabled():
            accent = getattr(self, 'solid_accent', '#ff1744') or '#ff1744'
            return [accent, accent]

        source = getattr(self, 'button_color_source', 'wallpaper' if getattr(self, 'background_type', 'gradient') == 'image' else 'gradient')
        raw_colors = None

        if source == "gradient":
            if self.theme_mode == "gradient_manual":
                raw_colors = getattr(self, 'manual_colors', None)
            elif self.theme_mode == "gradient_auto":
                raw_colors = getattr(self, 'auto_colors', None)
            else:
                raw_colors = [getattr(self, 'solid_accent', '#ff1744')]
        elif source == "wallpaper":
            raw_colors = getattr(self, 'auto_colors', None)
            if not raw_colors:
                raw_colors = self._extract_wallpaper_colors()
                self.auto_colors = raw_colors
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
        if self.radio_auto.isChecked():
            self.theme_mode = "gradient_auto"
            self.manual_panel.setVisible(False)
        elif self.radio_manual.isChecked():
            self.theme_mode = "gradient_manual"
            self.manual_panel.setVisible(True)
            if self.manual_colors:
                self.solid_accent = self.manual_colors[0]
        else:
            self.theme_mode = "solid"
            self.manual_panel.setVisible(False)

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

        if hasattr(self, 'radio_src_gradient'): self.radio_src_gradient.setVisible(True)
        if hasattr(self, 'radio_src_wallpaper'): self.radio_src_wallpaper.setVisible(True)

        self._refresh_button_visual_state()

    def _select_image_mode(self) -> None:
        self.background_type = "image"
        if hasattr(self, 'radio_bg_type_image') and self.radio_bg_type_image:
            self.radio_bg_type_image.setChecked(True)
        self._refresh_button_visual_state()

    def _update_section_highlights(self) -> None:
        accent = getattr(self, 'solid_accent', '#ff1744')
        if hasattr(self, 'btn_apply') and self.btn_apply:
            self.btn_apply.setStyleSheet(f"QPushButton {{ background-color: {accent}; color: #ffffff; font-weight: bold; padding: 8px 20px; border-radius: 10px; border: none; }} QPushButton:hover {{ opacity: 0.85; }}")

        if hasattr(self, 'sec_bg_box'):
            self.sec_bg_box.setStyleSheet(f"QFrame {{ background-color: #131522; border-radius: 12px; border: 1.5px solid {accent}; }}")

    def _on_btn_source_changed(self) -> None:
        if hasattr(self, 'radio_src_gradient') and self.radio_src_gradient.isChecked():
            self.button_color_source = "gradient"
        elif hasattr(self, 'radio_src_custom') and self.radio_src_custom.isChecked():
            self.button_color_source = "custom"
        elif hasattr(self, 'radio_src_wallpaper') and self.radio_src_wallpaper.isChecked():
            self.button_color_source = "wallpaper"
        self._refresh_button_visual_state()

    def _on_btn_gradient_toggled(self, checked: bool) -> None:
        self.btn_gradient_effect = checked
        self._refresh_button_visual_state()

    def _set_active_stop_index(self, index: int) -> None:
        self.active_gradient_stop_index = index
        self._refresh_button_swatches_ui()

    def _refresh_button_swatches_ui(self) -> None:
        if not hasattr(self, 'btn_swatches_layout') or not self.btn_swatches_layout:
            return
        while self.btn_swatches_layout.count():
            item = self.btn_swatches_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        active_colors = self._get_active_button_colors()
        source = getattr(self, 'button_color_source', 'wallpaper' if getattr(self, 'background_type', 'gradient') == 'image' else 'gradient')

        row_offset = 0
        if self._is_button_gradient_enabled() and source in ("custom", "gradient"):
            stops_list = self.custom_btn_gradient_colors if source == "custom" else self.manual_colors
            if not stops_list:
                stops_list = ["#ff1744", "#00e5ff", "#e040fb"]

            idx_active = max(0, min(getattr(self, 'active_gradient_stop_index', 0), len(stops_list) - 1))
            self.active_gradient_stop_index = idx_active

            lbl_stop_title = QLabel("📍 Seleccionar Stop a Editar:", self.sec_buttons_box)
            lbl_stop_title.setStyleSheet("color: #00e5ff; font-weight: bold; font-size: 11px; border: none;")
            self.btn_swatches_layout.addWidget(lbl_stop_title, 0, 0, 1, 3)

            for s_idx, s_hex in enumerate(stops_list):
                stop_letter = chr(65 + s_idx)
                is_selected_stop = (s_idx == idx_active)
                b_border = "2px solid #00e5ff" if is_selected_stop else "1px solid rgba(255, 255, 255, 0.3)"
                b_prefix = "▶ " if is_selected_stop else ""
                
                btn_stop = QPushButton(f"{b_prefix}Stop {stop_letter}: {s_hex}", self.sec_buttons_box)
                btn_stop.setFixedHeight(26)
                btn_stop.setStyleSheet(
                    f"QPushButton {{ background-color: {s_hex}; color: {get_contrasting_text_color(s_hex)}; "
                    f"border: {b_border}; border-radius: 6px; font-size: 10px; font-weight: bold; }} "
                    f"QPushButton:hover {{ border: 2px solid #ffffff; }}"
                )
                btn_stop.clicked.connect(lambda checked, idx=s_idx: self._set_active_stop_index(idx))
                self.btn_swatches_layout.addWidget(btn_stop, 1, s_idx)

            lbl_palette_title = QLabel(f"🎨 Paleta para Editar Stop {chr(65 + idx_active)}:", self.sec_buttons_box)
            lbl_palette_title.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 11px; border: none;")
            self.btn_swatches_layout.addWidget(lbl_palette_title, 2, 0, 1, 3)
            row_offset = 3

        if source == "gradient":
            if self.theme_mode == "gradient_manual":
                colors_to_show = self.manual_colors or ["#ff1744", "#7b1fa2", "#0c0c10"]
            elif self.theme_mode == "gradient_auto":
                colors_to_show = self.auto_colors or ["#ff1744", "#7b1fa2", "#0c0c10"]
            else:
                colors_to_show = [self.solid_accent]
        elif source == "wallpaper":
            colors_to_show = self._extract_wallpaper_colors()
            self.auto_colors = colors_to_show
        else:
            colors_to_show = getattr(self, 'custom_button_swatches', ["#ff1744", "#00e5ff", "#e040fb", "#00e676", "#ff9100", "#ff4081"])

        for idx, hex_c in enumerate(colors_to_show):
            is_active = (hex_c.lower() in [c.lower() for c in active_colors])
            border_style = "2px solid #00e5ff" if is_active else "1px solid #ffffff"
            btn = QPushButton(f"{hex_c}", self.sec_buttons_box)
            btn.setFixedHeight(26)
            btn.setStyleSheet(f"QPushButton {{ background-color: {hex_c}; color: {get_contrasting_text_color(hex_c)}; border: {border_style}; border-radius: 6px; font-size: 10px; font-weight: bold; }}")
            btn.clicked.connect(lambda checked, c=hex_c: self._select_button_color(c))
            row, col = divmod(idx, 3)
            self.btn_swatches_layout.addWidget(btn, row_offset + row, col)

    def _select_button_color(self, hex_color: str) -> None:
        self.solid_accent = hex_color
        if self._is_button_gradient_enabled():
            if self.button_color_source == "custom":
                if not hasattr(self, 'custom_btn_gradient_colors') or not self.custom_btn_gradient_colors:
                    self.custom_btn_gradient_colors = [hex_color, "#00e5ff", "#e040fb"]
                else:
                    idx = max(0, min(getattr(self, 'active_gradient_stop_index', 0), len(self.custom_btn_gradient_colors) - 1))
                    self.custom_btn_gradient_colors[idx] = hex_color
            elif self.button_color_source == "gradient" and self.theme_mode == "gradient_manual":
                if self.manual_colors:
                    idx = max(0, min(getattr(self, 'active_gradient_stop_index', 0), len(self.manual_colors) - 1))
                    self.manual_colors[idx] = hex_color
        else:
            if hasattr(self, 'chk_btn_gradient') and self.chk_btn_gradient:
                self.chk_btn_gradient.blockSignals(True)
                self.chk_btn_gradient.setChecked(False)
                self.chk_btn_gradient.blockSignals(False)
            self.btn_gradient_effect = False

        self._refresh_button_visual_state()

    def _pick_custom_button_color(self) -> None:
        idx = max(0, min(getattr(self, 'active_gradient_stop_index', 0), len(self.custom_btn_gradient_colors) - 1))
        curr_c = self.custom_btn_gradient_colors[idx] if self.custom_btn_gradient_colors else self.solid_accent
        color = QColorDialog.getColor(QColor(curr_c), self, f"Seleccionar Color para Stop {chr(65 + idx)}")
        if color.isValid():
            hex_c = color.name()
            if not hasattr(self, 'custom_button_swatches'):
                self.custom_button_swatches = ["#ff1744", "#00e5ff", "#e040fb", "#00e676", "#ff9100", "#ff4081"]
            if hex_c not in self.custom_button_swatches:
                self.custom_button_swatches.insert(0, hex_c)

            if not hasattr(self, 'custom_btn_gradient_colors') or not self.custom_btn_gradient_colors:
                self.custom_btn_gradient_colors = ["#ff1744", "#00e5ff", "#e040fb"]
            idx = max(0, min(self.active_gradient_stop_index, len(self.custom_btn_gradient_colors) - 1))
            self.custom_btn_gradient_colors[idx] = hex_c
            self.solid_accent = hex_c
            if hasattr(self, 'radio_src_custom') and self.radio_src_custom:
                self.radio_src_custom.setChecked(True)
            self.button_color_source = "custom"
            self._refresh_button_visual_state()

    def _apply_preset(self, colors: List[str]) -> None:
        self.manual_colors = list(colors)
        if hasattr(self, 'radio_manual') and self.radio_manual:
            self.radio_manual.setChecked(True)
        self._select_gradient_mode()

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
                from ui.expanded_view import get_cached_pixmap
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
            from ui.expanded_view import get_cached_pixmap
            pix = get_cached_pixmap(target_path, 0, 0)
            if pix and not pix.isNull():
                colors = extract_dominant_gradient_colors(pix, max_colors=4)
                if colors and len(colors) >= 2:
                    return colors
                vibrant = extract_vibrant_accent_color(pix)
                return [vibrant, "#1a1c29"]
        return ["#ff1744", "#7b1fa2"]

    def _choose_bg_image(self) -> None:
        initial_dir = self.bg_folder_path if (self.bg_folder_path and os.path.exists(self.bg_folder_path)) else os.path.expanduser("~/Imágenes")
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Imagen de Fondo",
            initial_dir,
            "Imágenes (*.png *.jpg *.jpeg *.webp *.jfif *.bmp);;Todos los archivos (*)"
        )
        if path:
            self.bg_image_path = path
            self._select_image_mode()
            self.lbl_selected_img_info.setText(f"Imagen seleccionada: {os.path.basename(path)}")
            wp_colors = self._extract_wallpaper_colors()
            if wp_colors:
                self.auto_colors = wp_colors
                self.solid_accent = wp_colors[0]
            self._refresh_button_swatches_ui()

    def _choose_bg_folder(self) -> None:
        initial_dir = self.bg_folder_path if (self.bg_folder_path and os.path.exists(self.bg_folder_path)) else os.path.expanduser("~/Imágenes")
        folder = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar Carpeta de Fondos",
            initial_dir
        )
        if folder:
            self.bg_folder_path = folder
            self._select_image_mode()
            self.lbl_selected_folder_info.setText(f"Carpeta activa: {os.path.basename(folder) or folder}")
            wp_colors = self._extract_wallpaper_colors()
            if wp_colors:
                self.auto_colors = wp_colors
                self.solid_accent = wp_colors[0]
            self._refresh_button_swatches_ui()

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

    def _on_apply_clicked(self) -> None:
        aspect_keys = ["stretch", "fill", "fit"]
        self.aspect_mode = aspect_keys[self.combo_aspect.currentIndex()]
        self.inner_art_mode = "custom_always" if self.radio_art_custom.isChecked() else "auto"
        self.slideshow_enabled = self.chk_slideshow.isChecked()
        self.stays_on_top = self.chk_top.isChecked()

        self.btn_gradient_effect = self.chk_btn_gradient.isChecked()
        brand_input = self.input_brand_name.text().strip() if hasattr(self, 'input_brand_name') else ""
        self.brand_name = brand_input if brand_input else "RED WORLD"

        source = "wallpaper"
        if hasattr(self, 'radio_src_gradient') and self.radio_src_gradient.isChecked():
            source = "gradient"
        elif hasattr(self, 'radio_src_custom') and self.radio_src_custom.isChecked():
            source = "custom"

        result = {
            "background_type": self.background_type,
            "theme_mode": self.theme_mode,
            "button_color_source": source,
            "btn_gradient_effect": self.btn_gradient_effect,
            "wallpaper_btn_gradient_effect": self.btn_gradient_effect if source == "wallpaper" else False,
            "auto_extract_wallpaper_color": self.auto_extract_wallpaper_color,
            "manual_gradient_colors": self.manual_colors,
            "accent_color": self.solid_accent,
            "auto_gradient_colors": self.auto_colors,
            "custom_btn_gradient_colors": getattr(self, 'custom_btn_gradient_colors', ["#ff1744", "#00e5ff", "#e040fb"]),
            "custom_button_swatches": getattr(self, 'custom_button_swatches', ["#ff1744", "#00e5ff", "#e040fb", "#00e676", "#ff9100", "#ff4081"]),
            "background_image": self.bg_image_path,
            "bg_folder": self.bg_folder_path,
            "bg_slideshow_enabled": self.slideshow_enabled,
            "bg_aspect_mode": self.aspect_mode,
            "inner_art_mode": self.inner_art_mode,
            "custom_inner_image": self.custom_inner_image,
            "stays_on_top": self.stays_on_top,
            "brand_name": self.brand_name
        }
        self.settings_saved.emit(result)
        self.accept()
