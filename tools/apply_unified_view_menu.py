from pathlib import Path
import re


def require_replace(text: str, pattern: str, replacement: str, name: str) -> str:
    new_text, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"No se encontró: {name}")
    return new_text

path = Path("ui/player_widget.py")
text = path.read_text(encoding="utf-8")
text = re.sub(r"\n?        self\.btn_norm_mode_(?:small|compact|expanded|settings)\s*=.*?(?:\n        .*?)*?\n        top_bar_layout\.addWidget\(self\.btn_norm_mode_(?:small|compact|expanded|settings)\)\n", "\n", text, flags=re.S)
text = re.sub(r"        # Botones de Selección de Modo en Modo Pequeño.*?(?=        self\.btn_close\s*=)", "", text, count=1, flags=re.S)
text = require_replace(text, r"        # Botones de Selección de Modo en Barra Compacta.*?(?=        self\.btn_comp_close\s*=)", '''        # Selector unificado de modos y personalización
        compact_nav = QHBoxLayout()
        compact_nav.setSpacing(5)
        self.btn_comp_mode_menu = QPushButton("⋮", self.compact_page)
        self.btn_comp_mode_menu.setFixedSize(30, 30)
        self.btn_comp_mode_menu.setToolTip("Modos y personalización")
        self.btn_comp_mode_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_comp_mode_menu.clicked.connect(lambda: self._show_view_mode_menu(self.btn_comp_mode_menu))
        compact_nav.addWidget(self.btn_comp_mode_menu)

''', "compact selector")
text = require_replace(text, r"(?=        self\.btn_close\s*=)", '''        # Selector unificado de modos y personalización
        self.btn_norm_mode_menu = QPushButton("⋮", self.container)
        self.btn_norm_mode_menu.setFixedSize(30, 30)
        self.btn_norm_mode_menu.setToolTip("Modos y personalización")
        self.btn_norm_mode_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_norm_mode_menu.clicked.connect(lambda: self._show_view_mode_menu(self.btn_norm_mode_menu))
        top_bar_layout.addWidget(self.btn_norm_mode_menu)

''', "normal selector")
text = re.sub(r"        norm_btns = \[.*?(?=        if hasattr\(self, 'btn_close'\))", '''        if hasattr(self, 'btn_norm_mode_menu') and self.btn_norm_mode_menu:
            self.btn_norm_mode_menu.setStyleSheet(build_mode_pill_style(
                is_active=True, accent_hex=clean_hex, btn_gradient_effect=btn_grad,
                gradient_colors=colors, border_radius=15, font_size=16, padding="0 2px"
            ))

''', text, count=1, flags=re.S)
text = re.sub(r"        comp_btns = \[.*?(?=        if hasattr\(self, 'btn_comp_close'\))", '''        if hasattr(self, 'btn_comp_mode_menu') and self.btn_comp_mode_menu:
            self.btn_comp_mode_menu.setStyleSheet(build_mode_pill_style(
                is_active=True, accent_hex=clean_hex, btn_gradient_effect=btn_grad,
                gradient_colors=colors, border_radius=15, font_size=16, padding="0 2px"
            ))

''', text, count=1, flags=re.S)
text = re.sub(r"\s*getattr\(self, 'btn_norm_mode_(?:small|compact|expanded|settings)', None\),", "", text)
text = require_replace(text, r"(?=    def _update_mode_buttons_styles\(self\) -> None:)", '''    def _show_view_mode_menu(self, anchor_button: QPushButton) -> None:
        menu = QMenu(self)
        for label, mode in (("▣  Pequeño", "normal"), ("▤  Compacto", "compact"), ("▦  Expandido", "expanded")):
            action = menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(self.view_mode == mode)
            action.triggered.connect(lambda checked=False, m=mode: self.set_view_mode(m))
        menu.addSeparator()
        menu.addAction("⚙  Personalización", self.open_personalization_dialog)
        menu.exec(anchor_button.mapToGlobal(anchor_button.rect().bottomLeft()))

''', "normal helper")
path.write_text(text, encoding="utf-8")

path = Path("ui/expanded_view.py")
text = path.read_text(encoding="utf-8")
text = require_replace(text, r"        # 2\. Control Segmentado de Modos.*?(?=        top_bar\.addWidget\(self\.btn_settings\))", '''        # 2. Selector unificado de modos y personalización
        self.btn_mode_menu = QPushButton("⋮", self.center_area)
        self.btn_mode_menu.setFixedSize(36, 36)
        self.btn_mode_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mode_menu.setToolTip("Modos y personalización")
        self.btn_mode_menu.clicked.connect(self._show_mode_menu)
        top_bar.addWidget(self.btn_mode_menu)

''', "expanded selector")
text = re.sub(r"\n        # 3\. Botón de Acción Personalizar.*?top_bar\.addWidget\(self\.btn_settings\)\n", "\n", text, count=1, flags=re.S)
text = text.replace("            self.btn_mode_normal,\n            self.btn_mode_compact,\n            self.btn_mode_expanded\n", "            self.btn_mode_menu\n", 1)
text = text.replace("self.btn_settings.setStyleSheet(", "self.btn_mode_menu.setStyleSheet(", 1)
text = require_replace(text, r"(?=    def _highlight_nav_button\(self, active_btn: QPushButton\) -> None:)", '''    def _show_mode_menu(self) -> None:
        menu = QMenu(self)
        current_mode = getattr(self, "current_view_mode", "expanded")
        for label, mode in (("▣  Pequeño", "normal"), ("▤  Compacto", "compact"), ("▦  Expandido", "expanded")):
            action = menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(current_mode == mode)
            action.triggered.connect(lambda checked=False, m=mode: self._on_mode_button_clicked(m))
        menu.addSeparator()
        menu.addAction("⚙  Personalización", self.open_personalization_requested)
        menu.exec(self.btn_mode_menu.mapToGlobal(self.btn_mode_menu.rect().bottomLeft()))

''', "expanded helper")
path.write_text(text, encoding="utf-8")

for filename in ("ui/player_widget.py", "ui/expanded_view.py"):
    content = Path(filename).read_text(encoding="utf-8")
    for legacy in ("btn_norm_mode_small", "btn_norm_mode_compact", "btn_norm_mode_expanded", "btn_norm_settings", "btn_comp_mode_small", "btn_comp_mode_compact", "btn_comp_mode_expanded", "btn_comp_settings", "btn_mode_normal", "btn_mode_compact", "btn_mode_expanded", "btn_settings"):
        if legacy in content:
            raise RuntimeError(f"Referencia legacy encontrada en {filename}: {legacy}")
