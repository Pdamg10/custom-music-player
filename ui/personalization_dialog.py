import os
from typing import List, Optional, Dict, Any
from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QBrush, QPen, QFont, QPixmap
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QRadioButton, QButtonGroup, QFrame, QScrollArea, QWidget, QSizePolicy,
    QColorDialog, QFileDialog, QCheckBox, QComboBox, QLineEdit, QMessageBox
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

        # Fondo del degradado
        grad = QLinearGradient(0, 0, w, h)
        if self.colors and len(self.colors) >= 2:
            count = len(self.colors)
            for i, hex_c in enumerate(self.colors):
                pos = i / max(1, count - 1)
                grad.setColorAt(pos, QColor(hex_c))
        else:
            grad.setColorAt(0.0, QColor("#ff1744"))
            grad.setColorAt(1.0, QColor("#0c0c10"))

        p.setPen(QPen(QColor("#ffffff"), 1.5))
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), 12.0, 12.0)

        # Muestra de Botón dentro de la previsualización
        btn_w, btn_h = 130.0, 32.0
        btn_x, btn_y = (w - btn_w) / 2.0, (h - btn_h) / 2.0
        btn_rect = QRectF(btn_x, btn_y, btn_w, btn_h)

        if self.btn_gradient and self.colors and len(self.colors) >= 2:
            b_grad = QLinearGradient(btn_x, btn_y, btn_x + btn_w, btn_y + btn_h)
            b_grad.setColorAt(0.0, QColor(self.colors[0]))
            b_grad.setColorAt(1.0, QColor(self.colors[min(1, len(self.colors) - 1)]))
            p.setBrush(QBrush(b_grad))
            text_c = get_contrasting_text_color(self.colors[0])
            p.setPen(QPen(QColor(self.colors[0]), 1.5))
        else:
            accent = self.colors[0] if self.colors else "#ff1744"
            p.setBrush(QBrush(QColor(accent)))
            text_c = get_contrasting_text_color(accent)
            p.setPen(Qt.PenStyle.NoPen)

        p.drawRoundedRect(btn_rect, 16.0, 16.0)
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
        self.setFixedSize(580, 680)

        self.cfg = dict(current_config)

        self.background_type = self.cfg.get("background_type", "gradient")
        self.theme_mode = self.cfg.get("theme_mode", "gradient_auto")
        self.btn_gradient_effect = self.cfg.get("btn_gradient_effect", True)
        self.auto_extract_wallpaper_color = self.cfg.get("auto_extract_wallpaper_color", True)

        self.manual_colors = list(self.cfg.get("manual_gradient_colors", ["#ff1744", "#7b1fa2", "#0c0c10"]))
        self.solid_accent = self.cfg.get("accent_color", "#ff1744")
        self.auto_colors = self.cfg.get("auto_gradient_colors", ["#2b0b10", "#180718", "#08060c"])

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
        title_lbl = QLabel("⚙️ Personalización del Reproductor", self)
        title_lbl.setFont(QFont("Sans Serif", 14, QFont.Weight.Bold))
        layout.addWidget(title_lbl)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_content = QWidget()
        sc_layout = QVBoxLayout(scroll_content)
        sc_layout.setContentsMargins(0, 0, 4, 0)
        sc_layout.setSpacing(14)

        # --------------------------------------------------------
        # SECCIÓN A: 🎨 TEMA DEGRADADO MULTI-COLOR (ACTIVA DEGRADADO)
        # --------------------------------------------------------
        self.sec_gradient_box = QFrame(scroll_content)
        self.sec_gradient_box.setStyleSheet("QFrame { background-color: #131522; border-radius: 12px; border: 1.5px solid #ff1744; }")
        sec_a_layout = QVBoxLayout(self.sec_gradient_box)
        sec_a_layout.setContentsMargins(14, 12, 14, 12)
        sec_a_layout.setSpacing(10)

        lbl_grad_title = QLabel("🎨 Opción 1: Tema Degradado Multi-Color (Sin Imagen)", self.sec_gradient_box)
        lbl_grad_title.setFont(QFont("Sans Serif", 11, QFont.Weight.Bold))
        lbl_grad_title.setStyleSheet("color: #ff1744; border: none;")
        sec_a_layout.addWidget(lbl_grad_title)

        # Grupo de selección principal de modo de fondo (Degradado vs Imagen)
        self.bg_type_group = QButtonGroup(self)
        self.radio_bg_type_gradient = QRadioButton("🎨 ACTIVAR MODO DEGRADADO MULTI-COLOR", self.sec_gradient_box)
        self.radio_bg_type_image = QRadioButton("🖼️ ACTIVAR MODO IMAGEN DE FONDO (WALLPAPER)")
        self.bg_type_group.addButton(self.radio_bg_type_gradient)
        self.bg_type_group.addButton(self.radio_bg_type_image)

        if self.background_type == "image":
            self.radio_bg_type_image.setChecked(True)
        else:
            self.radio_bg_type_gradient.setChecked(True)

        self.radio_bg_type_gradient.toggled.connect(self._on_bg_type_toggled)
        self.radio_bg_type_image.toggled.connect(self._on_bg_type_toggled)

        sec_a_layout.addWidget(self.radio_bg_type_gradient)
        sec_a_layout.addSpacing(4)

        theme_group = QButtonGroup(self)
        self.radio_auto = QRadioButton("✨ Automático (Extraído de la carátula de música)", self.sec_gradient_box)
        self.radio_manual = QRadioButton("🎨 Manual Multi-Color (Selecciona más de 2 colores)", self.sec_gradient_box)
        self.radio_solid = QRadioButton("🔴 Color Sólido Neón", self.sec_gradient_box)

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

        sec_a_layout.addWidget(self.radio_auto)
        sec_a_layout.addWidget(self.radio_manual)

        # Panel de Paradas Manuales
        self.manual_panel = QWidget(self.sec_gradient_box)
        manual_layout = QVBoxLayout(self.manual_panel)
        manual_layout.setContentsMargins(0, 4, 0, 4)
        manual_layout.setSpacing(8)

        lbl_presets = QLabel("Presets rápidos:", self.manual_panel)
        lbl_presets.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        manual_layout.addWidget(lbl_presets)

        presets_layout = QGridLayout()
        presets_layout.setSpacing(6)
        for idx, (name, p_colors) in enumerate(self.PRESETS[:4]):
            btn_p = QPushButton(name, self.manual_panel)
            btn_p.clicked.connect(lambda checked, c=p_colors: self._apply_preset(c))
            row, col = divmod(idx, 2)
            presets_layout.addWidget(btn_p, row, col)
        manual_layout.addLayout(presets_layout)

        # Swatches
        self.swatches_layout = QGridLayout()
        self.swatches_layout.setSpacing(6)
        manual_layout.addLayout(self.swatches_layout)

        btns_colors_row = QHBoxLayout()
        self.btn_add_color = QPushButton("+ Añadir Color", self.manual_panel)
        self.btn_add_color.clicked.connect(self._add_color_stop)
        self.btn_remove_color = QPushButton("- Eliminar Color", self.manual_panel)
        self.btn_remove_color.clicked.connect(self._remove_color_stop)
        btns_colors_row.addWidget(self.btn_add_color)
        btns_colors_row.addWidget(self.btn_remove_color)
        btns_colors_row.addStretch()
        manual_layout.addLayout(btns_colors_row)

        sec_a_layout.addWidget(self.manual_panel)
        sec_a_layout.addWidget(self.radio_solid)

        # Opción 2: Botones con degradado
        self.chk_btn_gradient = QCheckBox("🎨 Aplicar efecto de degradado a los botones", self.sec_gradient_box)
        self.chk_btn_gradient.setChecked(self.btn_gradient_effect)
        self.chk_btn_gradient.toggled.connect(self._on_btn_gradient_toggled)
        sec_a_layout.addWidget(self.chk_btn_gradient)

        # Previsualización
        self.preview_widget = GradientPreviewWidget(self._get_active_colors_for_preview(), self.btn_gradient_effect, self.sec_gradient_box)
        sec_a_layout.addWidget(self.preview_widget)

        sc_layout.addWidget(self.sec_gradient_box)

        # --------------------------------------------------------
        # SECCIÓN B: 🖼️ FONDO DE IMAGEN DE PANTALLA (WALLPAPER)
        # --------------------------------------------------------
        self.sec_image_box = QFrame(scroll_content)
        self.sec_image_box.setStyleSheet("QFrame { background-color: #131522; border-radius: 12px; border: 1px solid #23263a; }")
        sec_b_layout = QVBoxLayout(self.sec_image_box)
        sec_b_layout.setContentsMargins(14, 12, 14, 12)
        sec_b_layout.setSpacing(10)

        lbl_img_title = QLabel("🖼️ Opción 2: Fondo de Imagen de Pantalla (Wallpaper)", self.sec_image_box)
        lbl_img_title.setFont(QFont("Sans Serif", 11, QFont.Weight.Bold))
        lbl_img_title.setStyleSheet("color: #ffffff; border: none;")
        sec_b_layout.addWidget(lbl_img_title)
        sec_b_layout.addWidget(self.radio_bg_type_image)
        sec_b_layout.addSpacing(4)

        btns_img_layout = QHBoxLayout()
        self.btn_choose_img = QPushButton("🖼️ Seleccionar Imagen...", self.sec_image_box)
        self.btn_choose_img.clicked.connect(self._choose_bg_image)
        self.btn_choose_folder = QPushButton("📁 Seleccionar Carpeta...", self.sec_image_box)
        self.btn_choose_folder.clicked.connect(self._choose_bg_folder)
        btns_img_layout.addWidget(self.btn_choose_img)
        btns_img_layout.addWidget(self.btn_choose_folder)
        sec_b_layout.addLayout(btns_img_layout)

        img_name = os.path.basename(self.bg_image_path) if self.bg_image_path else "Ninguna"
        folder_name = os.path.basename(self.bg_folder_path) if self.bg_folder_path else "Ninguna"

        self.lbl_selected_img_info = QLabel(f"Imagen seleccionada: {img_name}", self.sec_image_box)
        self.lbl_selected_img_info.setWordWrap(True)
        self.lbl_selected_img_info.setStyleSheet("color: #a0a4c0; font-size: 10px; border: none;")
        sec_b_layout.addWidget(self.lbl_selected_img_info)

        self.lbl_selected_folder_info = QLabel(f"Carpeta activa: {folder_name}", self.sec_image_box)
        self.lbl_selected_folder_info.setWordWrap(True)
        self.lbl_selected_folder_info.setStyleSheet("color: #a0a4c0; font-size: 10px; border: none;")
        sec_b_layout.addWidget(self.lbl_selected_folder_info)

        self.chk_auto_extract = QCheckBox("✨ Auto-extraer color de acento de la imagen y adaptar texto", self.sec_image_box)
        self.chk_auto_extract.setChecked(self.auto_extract_wallpaper_color)
        self.chk_auto_extract.toggled.connect(self._select_image_mode)
        sec_b_layout.addWidget(self.chk_auto_extract)

        self.chk_slideshow = QCheckBox("🔄 Activar Carrusel Automático de Fondos (Cada 15s)", self.sec_image_box)
        self.chk_slideshow.setChecked(self.slideshow_enabled)
        self.chk_slideshow.toggled.connect(self._select_image_mode)
        sec_b_layout.addWidget(self.chk_slideshow)

        aspect_layout = QHBoxLayout()
        lbl_aspect = QLabel("Modo de Ajuste:", self.sec_image_box)
        self.combo_aspect = QComboBox(self.sec_image_box)
        self.combo_aspect.addItems(["Estirar a la ventana", "Llenar ventana (Recortar)", "Ajustar (Sin recortes)"])
        aspect_map = {"stretch": 0, "fill": 1, "fit": 2}
        self.combo_aspect.setCurrentIndex(aspect_map.get(self.aspect_mode, 0))
        self.combo_aspect.currentIndexChanged.connect(self._select_image_mode)
        aspect_layout.addWidget(lbl_aspect)
        aspect_layout.addWidget(self.combo_aspect)
        sec_b_layout.addLayout(aspect_layout)

        # Sub-sección: 🎨 Colores Extraídos de la Imagen de Fondo para Botones
        self.sec_wallpaper_colors_box = QFrame(self.sec_image_box)
        self.sec_wallpaper_colors_box.setStyleSheet("QFrame { background-color: #10111a; border-radius: 10px; border: 1px solid #1c1e2d; }")
        wp_colors_layout = QVBoxLayout(self.sec_wallpaper_colors_box)
        wp_colors_layout.setContentsMargins(12, 10, 12, 10)
        wp_colors_layout.setSpacing(8)

        lbl_wp_colors_title = QLabel("🎨 Colores Extraídos de la Imagen para Botones", self.sec_wallpaper_colors_box)
        lbl_wp_colors_title.setFont(QFont("Sans Serif", 10, QFont.Weight.Bold))
        lbl_wp_colors_title.setStyleSheet("color: #00e5ff; border: none;")
        wp_colors_layout.addWidget(lbl_wp_colors_title)

        lbl_wp_colors_desc = QLabel("Selecciona un color individual detectado en la imagen o aplica un degradado neón entre sus colores:", self.sec_wallpaper_colors_box)
        lbl_wp_colors_desc.setWordWrap(True)
        lbl_wp_colors_desc.setStyleSheet("color: #a0aec0; font-size: 10px; border: none;")
        wp_colors_layout.addWidget(lbl_wp_colors_desc)

        self.wp_swatches_layout = QGridLayout()
        self.wp_swatches_layout.setSpacing(6)
        wp_colors_layout.addLayout(self.wp_swatches_layout)

        self.chk_wallpaper_btn_gradient = QCheckBox("🎨 Aplicar efecto de degradado de los colores de la imagen a los botones", self.sec_wallpaper_colors_box)
        self.chk_wallpaper_btn_gradient.setWordWrap(True)
        self.chk_wallpaper_btn_gradient.setChecked(self.cfg.get("wallpaper_btn_gradient_effect", False))
        self.chk_wallpaper_btn_gradient.toggled.connect(self._on_wallpaper_btn_gradient_toggled)
        wp_colors_layout.addWidget(self.chk_wallpaper_btn_gradient)

        sec_b_layout.addWidget(self.sec_wallpaper_colors_box)

        sc_layout.addWidget(self.sec_image_box)

        # --------------------------------------------------------
        # SECCIÓN C: RECUADRO CENTRAL & AJUSTES
        # --------------------------------------------------------
        sec_c_box = QFrame(scroll_content)
        sec_c_box.setStyleSheet("QFrame { background-color: #131522; border-radius: 12px; border: 1px solid #23263a; }")
        sec_c_layout = QVBoxLayout(sec_c_box)
        sec_c_layout.setContentsMargins(14, 12, 14, 12)
        sec_c_layout.setSpacing(8)

        lbl_sys_title = QLabel("📌 Recuadro Central & Sistema", sec_c_box)
        lbl_sys_title.setFont(QFont("Sans Serif", 11, QFont.Weight.Bold))
        lbl_sys_title.setStyleSheet("color: #ffffff; border: none;")
        sec_c_layout.addWidget(lbl_sys_title)

        self.radio_art_auto = QRadioButton("🎵 Mostrar Carátula de la Canción (Auto)", sec_c_box)
        self.radio_art_custom = QRadioButton("📌 Mostrar SIEMPRE Imagen Personalizada Fija", sec_c_box)
        art_group = QButtonGroup(self)
        art_group.addButton(self.radio_art_auto)
        art_group.addButton(self.radio_art_custom)

        if self.inner_art_mode == "custom_always":
            self.radio_art_custom.setChecked(True)
        else:
            self.radio_art_auto.setChecked(True)

        sec_c_layout.addWidget(self.radio_art_auto)
        sec_c_layout.addWidget(self.radio_art_custom)

        self.btn_choose_inner = QPushButton("🖼️ Cambiar Imagen Personalizada Fija...", sec_c_box)
        self.btn_choose_inner.clicked.connect(self._choose_inner_image)
        sec_c_layout.addWidget(self.btn_choose_inner)

        self.chk_top = QCheckBox("📌 Ventana Siempre Encima (Stays on Top)", sec_c_box)
        self.chk_top.setChecked(self.stays_on_top)
        sec_c_layout.addWidget(self.chk_top)

        sc_layout.addWidget(sec_c_box)

        # --------------------------------------------------------
        # SECCIÓN D: 🏷️ NOMBRE DE LA MARCA / TÍTULO DEL REPRODUCTOR
        # --------------------------------------------------------
        sec_brand_box = QFrame(scroll_content)
        sec_brand_box.setStyleSheet("QFrame { background-color: #10111a; border-radius: 12px; border: 1px solid #1c1e2d; }")
        sec_brand_layout = QVBoxLayout(sec_brand_box)
        sec_brand_layout.setContentsMargins(14, 12, 14, 12)
        sec_brand_layout.setSpacing(10)

        lbl_brand_title = QLabel("🏷️ Nombre de la Marca / Título del Reproductor", sec_brand_box)
        lbl_brand_title.setFont(QFont("Sans Serif", 11, QFont.Weight.Bold))
        lbl_brand_title.setStyleSheet("color: #ff1744; border: none;")
        sec_brand_layout.addWidget(lbl_brand_title)

        lbl_brand_desc = QLabel("Modifica el nombre de la cabecera (Ej: RED WORLD, WORLD, STRAWBERRY):", sec_brand_box)
        lbl_brand_desc.setStyleSheet("color: #a0aec0; font-size: 11px; border: none;")
        sec_brand_layout.addWidget(lbl_brand_desc)

        self.input_brand_name = QLineEdit(sec_brand_box)
        self.input_brand_name.setText(self.brand_name)
        self.input_brand_name.setPlaceholderText("Nombre de la marca (ej: WORLD)")
        self.input_brand_name.setFixedHeight(34)
        self.input_brand_name.setStyleSheet("""
            QLineEdit {
                background-color: #1a1c29;
                color: #ffffff;
                border: 1px solid #ff1744;
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
        sc_layout.addWidget(sec_brand_box)

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

        self._refresh_swatches_ui()
        self._refresh_wallpaper_swatches_ui()
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

        self._update_section_highlights()
        self._update_preview()

    def _on_bg_type_toggled(self) -> None:
        if hasattr(self, 'radio_bg_type_image') and self.radio_bg_type_image.isChecked():
            self.background_type = "image"
        else:
            self.background_type = "gradient"
        self._update_section_highlights()

    def _select_image_mode(self) -> None:
        self.background_type = "image"
        if hasattr(self, 'radio_bg_type_image') and self.radio_bg_type_image:
            self.radio_bg_type_image.setChecked(True)
        self._update_section_highlights()

    def _update_section_highlights(self) -> None:
        accent = getattr(self, 'solid_accent', '#ff1744')
        if hasattr(self, 'btn_apply') and self.btn_apply:
            self.btn_apply.setStyleSheet(f"QPushButton {{ background-color: {accent}; color: #ffffff; font-weight: bold; padding: 8px 20px; border-radius: 10px; border: none; }} QPushButton:hover {{ opacity: 0.85; }}")

        if self.background_type == "gradient":
            self.sec_gradient_box.setStyleSheet(f"QFrame {{ background-color: #131522; border-radius: 12px; border: 1.5px solid {accent}; }}")
            self.sec_image_box.setStyleSheet("QFrame { background-color: #10111a; border-radius: 12px; border: 1px solid #1c1e2d; }")
        else:
            self.sec_gradient_box.setStyleSheet("QFrame { background-color: #10111a; border-radius: 12px; border: 1px solid #1c1e2d; }")
            self.sec_image_box.setStyleSheet(f"QFrame {{ background-color: #131522; border-radius: 12px; border: 1.5px solid {accent}; }}")

    def _on_btn_gradient_toggled(self, checked: bool) -> None:
        self.btn_gradient_effect = checked
        self._select_gradient_mode()

    def _refresh_swatches_ui(self) -> None:
        while self.swatches_layout.count():
            item = self.swatches_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for idx, hex_c in enumerate(self.manual_colors):
            btn = QPushButton(f"Color {idx + 1}", self.manual_panel)
            btn.setFixedHeight(28)
            btn.setStyleSheet(f"QPushButton {{ background-color: {hex_c}; color: {get_contrasting_text_color(hex_c)}; border: 1px solid #ffffff; border-radius: 6px; font-size: 10px; font-weight: bold; }}")
            btn.clicked.connect(lambda checked, i=idx: self._pick_color_stop(i))
            row, col = divmod(idx, 3)
            self.swatches_layout.addWidget(btn, row, col)

        self._update_preview()

    def _pick_color_stop(self, index: int) -> None:
        if 0 <= index < len(self.manual_colors):
            color = QColorDialog.getColor(QColor(self.manual_colors[index]), self, f"Seleccionar Color {index + 1}")
            if color.isValid():
                self.manual_colors[index] = color.name()
                self._select_gradient_mode()
                self._refresh_swatches_ui()

    def _add_color_stop(self) -> None:
        if len(self.manual_colors) < 6:
            self.manual_colors.append("#ff4081")
            self._select_gradient_mode()
            self._refresh_swatches_ui()

    def _remove_color_stop(self) -> None:
        if len(self.manual_colors) > 2:
            self.manual_colors.pop()
            self._select_gradient_mode()
            self._refresh_swatches_ui()

    def _apply_preset(self, colors: List[str]) -> None:
        self.manual_colors = list(colors)
        self.radio_manual.setChecked(True)
        self._select_gradient_mode()
        self._refresh_swatches_ui()

    def _update_preview(self) -> None:
        self.preview_widget.set_colors(self._get_active_colors_for_preview(), self.btn_gradient_effect)

    def _get_active_colors_for_preview(self) -> List[str]:
        if self.background_type == "image" and hasattr(self, 'chk_wallpaper_btn_gradient') and self.chk_wallpaper_btn_gradient and self.chk_wallpaper_btn_gradient.isChecked():
            return self.auto_colors or ["#ff1744", "#7b1fa2"]
        elif self.theme_mode == "gradient_manual":
            return self.manual_colors
        elif self.theme_mode == "gradient_auto":
            return self.auto_colors
        else:
            return [self.solid_accent, "#0c0c10"]

    def _extract_wallpaper_colors(self) -> List[str]:
        if self.bg_image_path and os.path.exists(self.bg_image_path):
            from ui.expanded_view import get_cached_pixmap
            pix = get_cached_pixmap(self.bg_image_path, 0, 0)
            if pix and not pix.isNull():
                colors = extract_dominant_gradient_colors(pix, max_colors=4)
                if colors and len(colors) >= 2:
                    return colors
                vibrant = extract_vibrant_accent_color(pix)
                return [vibrant, "#1a1c29"]
        return ["#ff1744", "#7b1fa2"]

    def _refresh_wallpaper_swatches_ui(self) -> None:
        if not hasattr(self, 'wp_swatches_layout') or not self.wp_swatches_layout:
            return
        while self.wp_swatches_layout.count():
            item = self.wp_swatches_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        wp_colors = self._extract_wallpaper_colors()
        self.auto_colors = wp_colors

        is_grad = hasattr(self, 'chk_wallpaper_btn_gradient') and self.chk_wallpaper_btn_gradient.isChecked()

        for idx, hex_c in enumerate(wp_colors):
            is_active = (self.solid_accent.lower() == hex_c.lower() and not is_grad)
            border_style = "2px solid #00e5ff" if is_active else "1px solid #ffffff"
            btn = QPushButton(f"Color {idx + 1} ({hex_c})", self.sec_wallpaper_colors_box)
            btn.setFixedHeight(28)
            btn.setStyleSheet(f"QPushButton {{ background-color: {hex_c}; color: {get_contrasting_text_color(hex_c)}; border: {border_style}; border-radius: 6px; font-size: 10px; font-weight: bold; }}")
            btn.clicked.connect(lambda checked, c=hex_c: self._select_wallpaper_color_stop(c))
            row, col = divmod(idx, 2)
            self.wp_swatches_layout.addWidget(btn, row, col)

    def _select_wallpaper_color_stop(self, hex_color: str) -> None:
        self.solid_accent = hex_color
        if hasattr(self, 'chk_wallpaper_btn_gradient') and self.chk_wallpaper_btn_gradient:
            self.chk_wallpaper_btn_gradient.blockSignals(True)
            self.chk_wallpaper_btn_gradient.setChecked(False)
            self.chk_wallpaper_btn_gradient.blockSignals(False)
        self.btn_gradient_effect = False
        self._select_image_mode()
        self._refresh_wallpaper_swatches_ui()
        self._update_preview()

    def _on_wallpaper_btn_gradient_toggled(self, checked: bool) -> None:
        self.btn_gradient_effect = checked
        if checked:
            wp_colors = self._extract_wallpaper_colors()
            if wp_colors:
                self.auto_colors = wp_colors
                self.solid_accent = wp_colors[0]
        self._select_image_mode()
        self._refresh_wallpaper_swatches_ui()
        self._update_preview()

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

            if self.chk_auto_extract.isChecked():
                from ui.expanded_view import get_cached_pixmap
                pix = get_cached_pixmap(path, 0, 0)
                if pix and not pix.isNull():
                    self.solid_accent = extract_vibrant_accent_color(pix, fallback_hex="#ff1744")
            self._refresh_wallpaper_swatches_ui()

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

            from ui.expanded_view import get_cached_pixmap
            for f in sorted(os.listdir(folder)):
                if f.startswith('.'):
                    continue
                fp = os.path.join(folder, f)
                if os.path.isfile(fp):
                    pix = get_cached_pixmap(fp, 0, 0)
                    if pix and not pix.isNull():
                        self.bg_image_path = fp
                        self.lbl_selected_img_info.setText(f"Imagen seleccionada: {os.path.basename(fp)}")
                        if self.chk_auto_extract.isChecked():
                            self.solid_accent = extract_vibrant_accent_color(pix, fallback_hex="#ff1744")
                        break
            self._refresh_wallpaper_swatches_ui()

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

        wallpaper_grad_on = self.chk_wallpaper_btn_gradient.isChecked() if hasattr(self, 'chk_wallpaper_btn_gradient') else False
        if self.background_type == "image":
            self.btn_gradient_effect = wallpaper_grad_on
        else:
            self.btn_gradient_effect = self.chk_btn_gradient.isChecked()

        if self.theme_mode == "gradient_manual" and self.manual_colors:
            self.solid_accent = self.manual_colors[0]

        brand_input = self.input_brand_name.text().strip() if hasattr(self, 'input_brand_name') else ""
        self.brand_name = brand_input if brand_input else "RED WORLD"

        result = {
            "background_type": self.background_type,
            "theme_mode": self.theme_mode,
            "btn_gradient_effect": self.btn_gradient_effect,
            "wallpaper_btn_gradient_effect": wallpaper_grad_on,
            "auto_extract_wallpaper_color": self.auto_extract_wallpaper_color,
            "manual_gradient_colors": self.manual_colors,
            "accent_color": self.solid_accent,
            "auto_gradient_colors": self.auto_colors,
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
