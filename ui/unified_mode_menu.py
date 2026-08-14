from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QMenu, QPushButton, QWidget, QLayout


def _clean_text(widget: QPushButton) -> str:
    return " ".join((widget.text() or "").split())


def _is_mode_button(widget: QPushButton) -> bool:
    return _clean_text(widget) in {"▣", "▤", "▦", "▣ Pequeño", "▤ Compacto", "▦ Expandido"}


def _is_settings_button(widget: QPushButton) -> bool:
    text = _clean_text(widget)
    tooltip = (widget.toolTip() or "").lower()
    return text == "⚙" or "personaliz" in tooltip or "tema" in tooltip


def _layout_contains(layout: QLayout, target: QWidget) -> int:
    for index in range(layout.count()):
        item = layout.itemAt(index)
        if item.widget() is target:
            return index
        child = item.layout()
        if child is not None:
            nested = _layout_contains(child, target)
            if nested >= 0:
                return nested
    return -1


def _find_owning_layout(widget: QWidget) -> tuple[Optional[QLayout], int]:
    current: Optional[QWidget] = widget
    while current is not None:
        layout = current.layout()
        if layout is not None:
            index = _layout_contains(layout, widget)
            if index >= 0:
                return layout, index
        current = current.parentWidget()
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
    opener = getattr(player, "open_personalization_requested", None)
    if callable(opener):
        opener()


def _menu_for(player: QWidget, anchor: QPushButton) -> None:
    menu = QMenu(player)
    current_mode = getattr(player, "view_mode", "normal")

    for label, mode in (
        ("▣  Pequeño", "normal"),
        ("▤  Compacto", "compact"),
        ("▦  Expandido", "expanded"),
    ):
        action = menu.addAction(label)
        action.setCheckable(True)
        action.setChecked(current_mode == mode)
        action.triggered.connect(lambda checked=False, selected=mode: _set_mode(player, selected))

    menu.addSeparator()
    personalization = menu.addAction("⚙  Personalización")
    personalization.triggered.connect(lambda: _open_personalization(player))
    menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))


def _make_menu_button(player: QWidget, layout: QLayout, index: int, parent: QWidget) -> QPushButton:
    button = QPushButton("⋮", parent)
    button.setObjectName("unifiedModeMenuButton")
    button.setFixedSize(30, 30)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setToolTip("Modos y personalización")
    button.clicked.connect(lambda: _menu_for(player, button))
    layout.insertWidget(max(0, index), button)
    return button


def _has_unified_button(layout: QLayout) -> bool:
    for index in range(layout.count()):
        item = layout.itemAt(index)
        widget = item.widget()
        if isinstance(widget, QPushButton) and widget.objectName() == "unifiedModeMenuButton":
            return True
        child = item.layout()
        if child is not None and _has_unified_button(child):
            return True
    return False


def _collapse_legacy_controls(player: QWidget) -> bool:
    mode_buttons = [b for b in player.findChildren(QPushButton) if _is_mode_button(b)]
    settings = [b for b in player.findChildren(QPushButton) if _is_settings_button(b)]
    if not mode_buttons:
        return False

    groups: dict[int, tuple[QLayout, int, list[QPushButton]]] = {}
    for button in mode_buttons:
        layout, index = _find_owning_layout(button)
        if layout is None:
            continue
        key = id(layout)
        if key not in groups:
            groups[key] = (layout, index, [])
        groups[key][2].append(button)

    changed = False
    for layout, index, group in groups.values():
        # Ocultamos únicamente los botones antiguos. Nunca ocultamos su contenedor:
        # puede contener el artwork, controles, barra de título u otros elementos.
        for button in group:
            button.hide()

        if not _has_unified_button(layout):
            _make_menu_button(player, layout, index, group[0].parentWidget() or player)
            changed = True

    # La personalización sigue disponible desde el nuevo menú.
    for button in settings:
        if button.objectName() != "unifiedModeMenuButton":
            button.hide()

    return changed


def install(player: QWidget) -> None:
    """Instala el selector unificado sin ocultar ni alterar contenedores de la interfaz."""
    attempts = {"count": 0}

    def apply() -> None:
        attempts["count"] += 1
        _collapse_legacy_controls(player)
        if attempts["count"] < 30:
            QTimer.singleShot(100, apply)

    QTimer.singleShot(0, apply)
