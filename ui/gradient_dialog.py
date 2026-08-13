import os
from typing import List, Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QBrush, QPen, QFont
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QButtonGroup, QFrame, QScrollArea, QWidget,
    QColorDialog, QMessageBox
)

class GradientPreviewWidget(QWidget):
    """Widget de previsualización en vivo del degradado multi-parada."""
    def __init__(self, colors: List[str], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.colors = colors
        self.setFixedHeight(70)

    def set_colors(self, colors: List[str]) -> None:
        self.colors = colors
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        w, h = rect.width(), rect.height()

        grad = QLinearGradient(0, 0, w, h)
        if self.colors:
            count = len(self.colors)
            for i, hex_c in enumerate(self.colors):
                pos = i / max(1, count - 1)
                grad.setColorAt(pos, QColor(hex_c))
        else:
            grad.setColorAt(0.0, QColor("#ff1744"))
            grad.setColorAt(1.0, QColor("#0c0c10"))

        p.setPen(QPen(QColor("#ffffff"), 1.5))
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(1, 1, w - 2, h - 2, 14, 14)
        p.end()

class GradientThemeDialog(QDialog):
    """Diálogo interactivo para personalizar y seleccionar temas degradados (Auto/Manual/Sólido)."""
    theme_changed = pyqtSignal(str, list, str) # (theme_mode, manual_colors_list, solid_accent_hex)

    PRESETS = [
        ("💗 APT. (Rosa & Negro)", ["#ff4081", "#8e24aa", "#14070e"]),
        ("🌌 Aurora Boreal (Cian & Violeta)", ["#00e5ff", "#7c4dff", "#0c051a"]),
        ("🔥 Sunset Neón (Dorado & Carmesí)", ["#ff9100", "#ff1744", "#1a080c"]),
        ("🟢 Esmeralda Ciberpunk", ["#00e676", "#00838f", "#04140d"]),
        ("🟣 Vía Láctea (Lila & Noche)", ["#e040fb", "#311b92", "#080512"])
    ]

    def __init__(self, current_mode: str, manual_colors: List[str], solid_accent: str, auto_colors: List[str], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("🎨 Personalizar Tema & Degradado")
        self.setFixedSize(480, 540)

        self.theme_mode = current_mode
        self.manual_colors = list(manual_colors) if manual_colors else ["#ff1744", "#7b1fa2", "#0c0c10"]
        self.solid_accent = solid_accent or "#ff1744"
        self.auto_colors = auto_colors or ["#2b0b10", "#180718", "#08060c"]

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
            QRadioButton {
                color: #ffffff;
                font-weight: bold;
                font-size: 13px;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
                border-radius: 8px;
                border: 2px solid #ff1744;
            }
            QRadioButton::indicator:checked {
                background-color: #ff1744;
            }
            QPushButton {
                background-color: #1a1c29;
                color: #ffffff;
                border: 1px solid #33364d;
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff1744;
                color: #ffffff;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(18, 18, 18, 18)

        # Header
        header = QLabel("🎨 Selección de Tema & Fondo Degradado", self)
        header.setFont(QFont("Sans Serif", 12, QFont.Weight.Bold))
        header.setStyleSheet("color: #ff1744;")
        layout.addWidget(header)

        # Radio Group
        self.radio_group = QButtonGroup(self)

        self.rb_auto = QRadioButton("✨ Degradado Automático (Extraído de la Carátula / Imagen)", self)
        self.rb_auto.setToolTip("Lee automáticamente los colores de la carátula de la canción activa o imagen de fondo")
        self.radio_group.addButton(self.rb_auto, 1)
        layout.addWidget(self.rb_auto)

        self.rb_manual = QRadioButton("🎨 Degradado Manual Personalizado (Multi-Color)", self)
        self.rb_manual.setToolTip("Elige libremente 2 o más colores para tu propio degradado neón")
        self.radio_group.addButton(self.rb_manual, 2)
        layout.addWidget(self.rb_manual)

        self.rb_solid = QRadioButton("🔴 Tema Neón Sólido Clásico", self)
        self.radio_group.addButton(self.rb_solid, 3)
        layout.addWidget(self.rb_solid)

        # Previsualización
        layout.addWidget(QLabel("👁️ Previsualización del Degradado:", self))
        self.preview_widget = GradientPreviewWidget(self._get_active_preview_colors(), self)
        layout.addWidget(self.preview_widget)

        # Contenedor de controles manuales
        self.manual_box = QFrame(self)
        self.manual_box.setStyleSheet("QFrame { background: #13141f; border-radius: 12px; padding: 10px; }")
        manual_layout = QVBoxLayout(self.manual_box)
        manual_layout.setSpacing(8)

        manual_header_layout = QHBoxLayout()
        manual_header_layout.addWidget(QLabel("🎨 Paradas de Color Manuales:", self.manual_box))
        manual_header_layout.addStretch()

        self.btn_add_color = QPushButton("➕ Añadir Color", self.manual_box)
        self.btn_add_color.clicked.connect(self._add_manual_color)
        manual_header_layout.addWidget(self.btn_add_color)
        manual_layout.addLayout(manual_header_layout)

        # Scroll para lista de colores
        scroll = QScrollArea(self.manual_box)
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(110)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.scroll_content = QWidget()
        self.colors_list_layout = QHBoxLayout(self.scroll_content)
        self.colors_list_layout.setContentsMargins(0, 0, 0, 0)
        self.colors_list_layout.setSpacing(8)
        scroll.setWidget(self.scroll_content)
        manual_layout.addWidget(scroll)

        # Presets Rápidos
        preset_layout = QHBoxLayout()
        preset_layout.setSpacing(6)
        preset_label = QLabel("⚡ Presets:", self.manual_box)
        preset_layout.addWidget(preset_label)

        for name, preset_colors in self.PRESETS:
            p_btn = QPushButton(name.split()[0], self.manual_box)
            p_btn.setToolTip(name)
            p_btn.clicked.connect(lambda checked, c=preset_colors: self._apply_preset(c))
            preset_layout.addWidget(p_btn)
        preset_layout.addStretch()
        manual_layout.addLayout(preset_layout)

        layout.addWidget(self.manual_box)

        # Botones de Acción OK / Cancelar
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        self.btn_cancel = QPushButton("Cancelar", self)
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)

        self.btn_ok = QPushButton("Aplicar Tema", self)
        self.btn_ok.setStyleSheet("QPushButton { background-color: #ff1744; color: #ffffff; padding: 8px 20px; font-size: 13px; }")
        self.btn_ok.clicked.connect(self._on_apply)
        btn_box.addWidget(self.btn_ok)

        layout.addLayout(btn_box)

        # Conectar cambios de radio button
        self.rb_auto.toggled.connect(self._update_state)
        self.rb_manual.toggled.connect(self._update_state)
        self.rb_solid.toggled.connect(self._update_state)

        # Establecer selección inicial
        if self.theme_mode == "gradient_manual":
            self.rb_manual.setChecked(True)
        elif self.theme_mode == "solid":
            self.rb_solid.setChecked(True)
        else:
            self.rb_auto.setChecked(True)

        self._refresh_colors_list_ui()
        self._update_state()

    def _get_active_preview_colors(self) -> List[str]:
        if self.rb_manual.isChecked():
            return self.manual_colors
        elif self.rb_auto.isChecked():
            return self.auto_colors
        else:
            return [self.solid_accent, "#0c0c10"]

    def _update_state(self) -> None:
        if self.rb_manual.isChecked():
            self.theme_mode = "gradient_manual"
            self.manual_box.setEnabled(True)
        elif self.rb_solid.isChecked():
            self.theme_mode = "solid"
            self.manual_box.setEnabled(False)
        else:
            self.theme_mode = "gradient_auto"
            self.manual_box.setEnabled(False)

        self.preview_widget.set_colors(self._get_active_preview_colors())

    def _refresh_colors_list_ui(self) -> None:
        # Limpiar layout
        while self.colors_list_layout.count():
            item = self.colors_list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        for idx, hex_c in enumerate(self.manual_colors):
            card = QFrame(self.scroll_content)
            card.setFixedSize(70, 85)
            card.setStyleSheet(f"QFrame {{ background-color: #1e2030; border-radius: 8px; border: 1px solid #33364d; }}")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(4, 4, 4, 4)
            card_layout.setSpacing(4)

            # Muestra de color
            swatch = QPushButton(card)
            swatch.setFixedHeight(32)
            swatch.setStyleSheet(f"QPushButton {{ background-color: {hex_c}; border-radius: 4px; border: none; }}")
            swatch.setToolTip("Haz clic para cambiar este color")
            swatch.clicked.connect(lambda checked, i=idx: self._edit_manual_color(i))
            card_layout.addWidget(swatch)

            # Botón eliminar
            btn_del = QPushButton("🗑️", card)
            btn_del.setFixedHeight(22)
            btn_del.setStyleSheet("QPushButton { font-size: 11px; padding: 0px; background: transparent; border: none; color: #ff4d6d; } QPushButton:hover { color: #ffffff; }")
            btn_del.setToolTip("Eliminar parada de color")
            btn_del.clicked.connect(lambda checked, i=idx: self._remove_manual_color(i))
            card_layout.addWidget(btn_del)

            self.colors_list_layout.addWidget(card)

        self.colors_list_layout.addStretch()
        self.preview_widget.set_colors(self._get_active_preview_colors())

    def _edit_manual_color(self, index: int) -> None:
        if 0 <= index < len(self.manual_colors):
            c = QColorDialog.getColor(QColor(self.manual_colors[index]), self, f"Seleccionar Color para Parada #{index + 1}")
            if c.isValid():
                self.manual_colors[index] = c.name()
                self._refresh_colors_list_ui()

    def _add_manual_color(self) -> None:
        c = QColorDialog.getColor(QColor("#00e5ff"), self, "Añadir Nuevo Color al Degradado")
        if c.isValid():
            self.manual_colors.append(c.name())
            self._refresh_colors_list_ui()

    def _remove_manual_color(self, index: int) -> None:
        if len(self.manual_colors) <= 2:
            QMessageBox.information(self, "Información", "El degradado requiere al menos 2 colores.")
            return
        if 0 <= index < len(self.manual_colors):
            self.manual_colors.pop(index)
            self._refresh_colors_list_ui()

    def _apply_preset(self, preset_colors: List[str]) -> None:
        self.manual_colors = list(preset_colors)
        self.rb_manual.setChecked(True)
        self._refresh_colors_list_ui()

    def _on_apply(self) -> None:
        self.theme_changed.emit(self.theme_mode, self.manual_colors, self.solid_accent)
        self.accept()
