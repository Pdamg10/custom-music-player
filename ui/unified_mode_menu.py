from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QMenu, QPushButton, QWidget, QLayout


def _clean_text(widget: QPushButton) -> str:
    return " ".join((widget.text() or "").split())


def _is_mode_button(widget: QPushButton) -> bool:
    return _clean_text(widget) in {
        "▣", "▤", "▦",
        "▣ Pequeño", "▤ Compacto", "▦ Expandido",
    }


def _is_settings_button(widget: QPushButton) -> bool:
    return _clean_text(widget) == "⚙"


def _find_in_layout(layout: QLayout, target: QWidget) -> tuple[Optional[QLayout], int]:
    """Devuelve el layout que contiene DIRECTAMENTE al widget.

    No devuelve un layout ancestro. Esto es importante porque los botones de
    navegación viven dentro de layouts anidados, y añadir el nuevo botón al
    layout equivocado puede alterar la geometría completa del reproductor.
    """
    for index in range(layout.count()):
        item = layout.itemAt(index)
        if item.widget() is target:
            return layout, index
        child = item.layout()
        if child is not None:
            owner, child_index = _find_in_layout(child, target)
            if owner is not None:
                return owner, child_index
    return None, -1


def _find_owning_layout(player: QWidget, widget: QWidget) -> tuple[Optional[QLayout], int]:
    root = player.layout()
    if root is None:
        return None, -1
    return _find_in_layout(root, widget)


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
        action.triggered.connect(
            lambda checked=False, selected=mode: _set_mode(player, selected)
        )

    menu.addSeparator()
    personalization = menu.addAction("⚙  Personalización")
    personalization.triggered.connect(lambda: _open_personalization(player))

    menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))


def _make_menu_button(
    player: QWidget,
    layout: QLayout,
    index: int,
    parent: QWidget,
) -> QPushButton:
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
    mode_buttons = [
        button for button in player.findChildren(QPushButton)
        if _is_mode_button(button)
    ]
    settings = [
        button for button in player.findChildren(QPushButton)
        if _is_settings_button(button)
    ]

    if not mode_buttons:
        return False

    groups: dict[int, tuple[QLayout, int, list[QPushButton]]] = {}

    for button in mode_buttons:
        layout, index = _find_owning_layout(player, button)
        if layout is None:
            continue

        key = id(layout)
        if key not in groups:
            groups[key] = (layout, index, [])
        groups[key][2].append(button)

    changed = False

    for layout, index, group in groups.values():
        # Solo ocultamos los botones antiguos. Jamás el contenedor que contiene
        # artwork, controles, información u otros elementos de la interfaz.
        for button in group:
            button.hide()

        if not _has_unified_button(layout):
            parent = group[0].parentWidget() or player
            _make_menu_button(player, layout, index, parent)
            changed = True

    # El engranaje antiguo desaparece porque Personalización vive dentro del menú.
    for button in settings:
        button.hide()

    return changed


def install(player: QWidget) -> None:
    """Instala el selector unificado sin modificar la geometría de las vistas."""
    attempts = {"count": 0}

    def apply() -> None:
        attempts["count"] += 1
        _collapse_legacy_controls(player)

        # Algunas vistas crean/refrescan controles después de init_ui().
        if attempts["count"] < 30:
            QTimer.singleShot(100, apply)

    QTimer.singleShot(0, apply)
