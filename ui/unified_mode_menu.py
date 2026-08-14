from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QMenu, QPushButton, QWidget, QLayout


NORM_BUTTON_NAMES = {
    "btn_norm_mode_small",
    "btn_norm_mode_compact",
    "btn_norm_mode_expanded",
    "btn_norm_settings",
}

COMP_BUTTON_NAMES = {
    "btn_comp_mode_small",
    "btn_comp_mode_compact",
    "btn_comp_mode_expanded",
    "btn_comp_settings",
}


def _find_direct_layout_of(target: QWidget) -> tuple[Optional[QLayout], int]:
    """Encuentra el QLayout que contiene directamente al target."""
    parent = target.parentWidget()
    if parent is None:
        return None, -1

    def search(layout: QLayout) -> tuple[Optional[QLayout], int]:
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item.widget() is target:
                return layout, i
            child_layout = item.layout()
            if child_layout is not None:
                found, idx = search(child_layout)
                if found is not None:
                    return found, idx
        return None, -1

    curr_layout = parent.layout()
    if curr_layout is not None:
        return search(curr_layout)
    return None, -1


def _set_mode(player: QWidget, mode: str) -> None:
    setter = getattr(player, "set_view_mode", None)
    if callable(setter):
        setter(mode)


def _open_personalization(player: QWidget) -> None:
    opener = getattr(player, "open_personalization_dialog", None)
    if callable(opener):
        opener()
        return

    signal = getattr(player, "open_personalization_requested", None)
    if callable(signal):
        signal()


def _show_menu(player: QWidget, button: QPushButton) -> None:
    menu = QMenu(player)
    menu.setObjectName("UnifiedModeMenu")

    current = getattr(player, "view_mode", "normal")
    options = (
        ("▣  Pequeño", "normal"),
        ("▤  Compacto", "compact"),
        ("▦  Expandido", "expanded"),
    )

    for text, mode in options:
        action = menu.addAction(text)
        action.setCheckable(True)
        action.setChecked(current == mode)
        action.triggered.connect(lambda checked=False, value=mode: _set_mode(player, value))

    menu.addSeparator()
    action = menu.addAction("⚙  Personalización")
    action.triggered.connect(lambda: _open_personalization(player))

    menu.exec(button.mapToGlobal(button.rect().bottomLeft()))


def _create_button(player: QWidget, layout: QLayout, index: int, parent: QWidget, button_name: str = "unifiedModeMenuButton") -> QPushButton:
    button = QPushButton("⋮", parent)
    button.setObjectName(button_name)
    size = 36 if "exp" in button_name else 26
    radius = size // 2
    font_size = 18 if "exp" in button_name else 14
    button.setFixedSize(size, size)
    button.setMinimumSize(size, size)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setToolTip("Modos y personalización")
    button.setStyleSheet(
        f"QPushButton#{button_name} {{"
        "background: rgba(25, 28, 44, 0.85);"
        "color: #ffffff;"
        "border: 1px solid rgba(255, 255, 255, 0.25);"
        f"border-radius: {radius}px;"
        f"font-size: {font_size}px;"
        "font-weight: bold;"
        "padding: 0px;"
        "}"
        f"QPushButton#{button_name}:hover {{"
        "background: rgba(255, 255, 255, 0.20);"
        "border: 1px solid rgba(255, 255, 255, 0.60);"
        "}"
        f"QPushButton#{button_name}:pressed {{"
        "background: rgba(255, 255, 255, 0.30);"
        "}"
    )
    button.clicked.connect(lambda: _show_menu(player, button))
    layout.insertWidget(max(0, index), button)
    return button


def _install_for_normal(player: QWidget) -> bool:
    """Reemplaza los botones de modo y configuración en modo Normal."""
    controls = [getattr(player, name, None) or player.findChild(QPushButton, name) for name in NORM_BUTTON_NAMES]
    controls = [b for b in controls if b is not None]
    if not controls:
        return False

    existing_btn = getattr(player, "btn_norm_unified_menu", None) or player.findChild(QPushButton, "btn_norm_unified_menu")
    if existing_btn is not None:
        for b in controls:
            b.hide()
        return True

    layout, index = _find_direct_layout_of(controls[0])
    if layout is None:
        return False

    for b in controls:
        b.hide()

    btn = _create_button(player, layout, index, controls[0].parentWidget() or player, "btn_norm_unified_menu")
    player.btn_norm_unified_menu = btn
    return True


def _install_for_compact(player: QWidget) -> bool:
    """Reemplaza los botones de modo y configuración en modo Compacto."""
    compact_page = getattr(player, "compact_page", None)
    container = compact_page or player
    controls = [getattr(player, name, None) or container.findChild(QPushButton, name) for name in COMP_BUTTON_NAMES]
    controls = [b for b in controls if b is not None]
    if not controls:
        return False

    existing_btn = getattr(player, "btn_comp_unified_menu", None) or container.findChild(QPushButton, "btn_comp_unified_menu")
    if existing_btn is not None:
        for b in controls:
            b.hide()
        return True

    layout, index = _find_direct_layout_of(controls[0])
    if layout is None:
        return False

    for b in controls:
        b.hide()

    btn = _create_button(player, layout, index, controls[0].parentWidget() or container, "btn_comp_unified_menu")
    player.btn_comp_unified_menu = btn
    return True


def _install_for_expanded(player: QWidget) -> bool:
    """Reemplaza el selector de modo segmentado y configuración en modo Expandido."""
    expanded = getattr(player, "expanded_page", None)
    if expanded is None:
        return False

    existing_btn = getattr(player, "btn_exp_unified_menu", None) or expanded.findChild(QPushButton, "btn_exp_unified_menu")
    if existing_btn is not None:
        mode_seg = getattr(expanded, "mode_segment_widget", None)
        if mode_seg:
            mode_seg.hide()
        settings = getattr(expanded, "btn_settings", None)
        if settings:
            settings.hide()
        return True

    mode_seg = getattr(expanded, "mode_segment_widget", None)
    settings = getattr(expanded, "btn_settings", None)

    target = mode_seg or settings
    if target is None:
        return False

    layout, index = _find_direct_layout_of(target)
    if layout is None:
        return False

    if mode_seg:
        mode_seg.hide()
    if settings:
        settings.hide()

    btn = _create_button(player, layout, index, target.parentWidget() or expanded, "btn_exp_unified_menu")
    player.btn_exp_unified_menu = btn
    return True


def install(player: QWidget) -> None:
    """Instala el selector unificado en todas las vistas (Normal, Compacta y Expandida)."""
    attempts = {"count": 0}

    def apply() -> None:
        attempts["count"] += 1
        _install_for_normal(player)
        _install_for_compact(player)
        _install_for_expanded(player)
        if attempts["count"] < 30:
            QTimer.singleShot(100, apply)

    apply()
