from pathlib import Path
import re


def replace_block(text: str, pattern: str, replacement: str, name: str) -> str:
    new_text, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"No se encontró el bloque esperado: {name}")
    return new_text


# player_widget.py
path = Path("ui/player_widget.py")
text = path.read_text(encoding="utf-8")

# Keep QMenu available for the explicit button menu. It was already imported in the current branch.
if "QMenu" not in text:
    raise RuntimeError("QMenu no está importado en player_widget.py")

text = replace_block(
    text,
    r"        # Botones de Selección de Modo en Modo Pequeño.*?(?=        self\.btn_close\s*=)",
    '''        # Selector unificado de modos y personalización\n        self.btn_norm_mode_menu = QPushButton("⋮", self.container)\n        self.btn_norm_mode_menu.setFixedSize(30, 30)\n        self.btn_norm_mode_menu.setToolTip("Modos y personalización")\n        self.btn_norm_mode_menu.setCursor(Qt.CursorShape.PointingHandCursor)\n        self.btn_norm_mode_menu.clicked.connect(lambda: self._show_view_mode_menu(self.btn_norm_mode_menu))\n        top_bar_layout.addWidget(self.btn_norm_mode_menu)\n\n''',
    "normal-mode buttons",
)

text = replace_block(
    text,
    r"        # Botones de Selección de Modo en Barra Compacta.*?(?=        self\.btn_comp_close\s*=)",
    '''        # Selector unificado de modos y personalización\n        compact_nav = QHBoxLayout()\n        compact_nav.setSpacing(5)\n\n        self.btn_comp_mode_menu = QPushButton("⋮", self.compact_page)\n        self.btn_comp_mode_menu.setFixedSize(30, 30)\n        self.btn_comp_mode_menu.setToolTip("Modos y personalización")\n        self.btn_comp_mode_menu.setCursor(Qt.CursorShape.PointingHandCursor)\n        self.btn_comp_mode_menu.clicked.connect(lambda: self._show_view_mode_menu(self.btn_comp_mode_menu))\n        compact_nav.addWidget(self.btn_comp_mode_menu)\n\n''',
    "compact-mode buttons",
)

# Replace references in the normal-mode visibility/style sections.
text = re.sub(
    r"            getattr\(self, 'btn_norm_mode_small', None\),\n            getattr\(self, 'btn_norm_mode_compact', None\),\n            getattr\(self, 'btn_norm_mode_expanded', None\),\n            getattr\(self, 'btn_norm_settings', None\),",
    "            getattr(self, 'btn_norm_mode_menu', None),",
    text,
    count=1,
)

text = replace_block(
    text,
    r"        norm_btns = \[.*?(?=        if hasattr\(self, 'btn_close'\))",
    '''        if hasattr(self, 'btn_norm_mode_menu') and self.btn_norm_mode_menu:\n            self.btn_norm_mode_menu.setStyleSheet(build_mode_pill_style(\n                is_active=True,\n                accent_hex=clean_hex,\n                btn_gradient_effect=btn_grad,\n                gradient_colors=colors,\n                border_radius=15,\n                font_size=16,\n                padding="0 2px"\n            ))\n\n''',
    "normal-mode style block",
)

# Replace compact mode style block if present.
text = replace_block(
    text,
    r"        comp_btns = \[.*?(?=        if hasattr\(self, 'btn_comp_close'\))",
    '''        if hasattr(self, 'btn_comp_mode_menu') and self.btn_comp_mode_menu:\n            self.btn_comp_mode_menu.setStyleSheet(build_mode_pill_style(\n                is_active=True,\n                accent_hex=clean_hex,\n                btn_gradient_effect=btn_grad,\n                gradient_colors=colors,\n                border_radius=15,\n                font_size=16,\n                padding="0 2px"\n            ))\n\n''',
    "compact-mode style block",
)

helper = '''    def _show_view_mode_menu(self, anchor_button: QPushButton) -> None:\n        """Muestra en un único botón los modos de ventana y Personalización."""\n        menu = QMenu(self)\n        menu.setStyleSheet("""\n            QMenu {\n                background-color: rgba(18, 20, 32, 0.98);\n                color: #ffffff;\n                border: 1px solid rgba(255, 255, 255, 0.18);\n                border-radius: 10px;\n                padding: 5px;\n            }\n            QMenu::item { padding: 8px 18px; border-radius: 7px; }\n            QMenu::item:selected { background-color: rgba(255, 255, 255, 0.14); }\n        """)\n\n        for label, mode in (("▣  Pequeño", "normal"), ("▤  Compacto", "compact"), ("▦  Expandido", "expanded")):\n            action = menu.addAction(label)\n            action.setCheckable(True)\n            action.setChecked(self.view_mode == mode)\n            action.triggered.connect(lambda checked=False, m=mode: self.set_view_mode(m))\n\n        menu.addSeparator()\n        personalize = menu.addAction("⚙  Personalización")\n        personalize.triggered.connect(self.open_personalization_dialog)\n        menu.exec(anchor_button.mapToGlobal(anchor_button.rect().bottomLeft()))\n\n'''
text = replace_block(
    text,
    r"(?=    def _update_mode_buttons_styles\(self\) -> None:)",
    helper,
    "view-mode menu helper",
)

path.write_text(text, encoding="utf-8")


# expanded_view.py
path = Path("ui/expanded_view.py")
text = path.read_text(encoding="utf-8")

text = replace_block(
    text,
    r"        # 2\. Control Segmentado de Modos.*?(?=        top_bar\.addWidget\(self\.btn_settings\))",
    '''        # 2. Selector unificado de modos y personalización\n        self.btn_mode_menu = QPushButton("⋮", self.center_area)\n        self.btn_mode_menu.setFixedSize(36, 36)\n        self.btn_mode_menu.setCursor(Qt.CursorShape.PointingHandCursor)\n        self.btn_mode_menu.setToolTip("Modos y personalización")\n        self.btn_mode_menu.clicked.connect(self._show_mode_menu)\n        top_bar.addWidget(self.btn_mode_menu)\n\n''',
    "expanded-mode controls",
)

# The old Personalización button is part of the block above in some revisions. Remove it if it remains.
text = re.sub(
    r"\n        # 3\. Botón de Acción Personalizar.*?top_bar\.addWidget\(self\.btn_settings\)\n",
    "\n",
    text,
    count=1,
    flags=re.S,
)

# Replace references to the old mode buttons in the style section with the unified button.
text = text.replace("            self.btn_mode_normal,\n            self.btn_mode_compact,\n            self.btn_mode_expanded\n", "            self.btn_mode_menu\n", 1)
text = text.replace("self.btn_settings.setStyleSheet(", "self.btn_mode_menu.setStyleSheet(", 1)

helper = '''    def _show_mode_menu(self) -> None:\n        """Muestra los modos disponibles y Personalización desde un único botón."""\n        menu = QMenu(self)\n        menu.setStyleSheet("""\n            QMenu {\n                background-color: rgba(18, 20, 32, 0.98);\n                color: #ffffff;\n                border: 1px solid rgba(255, 255, 255, 0.18);\n                border-radius: 10px;\n                padding: 5px;\n            }\n            QMenu::item { padding: 8px 18px; border-radius: 7px; }\n            QMenu::item:selected { background-color: rgba(255, 255, 255, 0.14); }\n        """)\n\n        current_mode = getattr(self, "current_view_mode", "expanded")\n        for label, mode in (("▣  Pequeño", "normal"), ("▤  Compacto", "compact"), ("▦  Expandido", "expanded")):\n            action = menu.addAction(label)\n            action.setCheckable(True)\n            action.setChecked(current_mode == mode)\n            action.triggered.connect(lambda checked=False, m=mode: self._on_mode_button_clicked(m))\n\n        menu.addSeparator()\n        personalize = menu.addAction("⚙  Personalización")\n        personalize.triggered.connect(self.open_personalization_requested)\n        menu.exec(self.btn_mode_menu.mapToGlobal(self.btn_mode_menu.rect().bottomLeft()))\n\n'''
text = replace_block(
    text,
    r"(?=    def _highlight_nav_button\(self, active_btn: QPushButton\) -> None:)",
    helper,
    "expanded-mode menu helper",
)

path.write_text(text, encoding="utf-8")

# Verify that no legacy visible mode-control attributes remain.
for filename, legacy in {
    "ui/player_widget.py": ("btn_norm_mode_small", "btn_norm_mode_compact", "btn_norm_mode_expanded", "btn_norm_settings", "btn_comp_mode_small", "btn_comp_mode_compact", "btn_comp_mode_expanded", "btn_comp_settings"),
    "ui/expanded_view.py": ("btn_mode_normal", "btn_mode_compact", "btn_mode_expanded", "btn_settings"),
}.items():
    content = Path(filename).read_text(encoding="utf-8")
    leftovers = [item for item in legacy if item in content]
    if leftovers:
        raise RuntimeError(f"Quedaron referencias antiguas en {filename}: {leftovers}")
