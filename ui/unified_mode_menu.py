from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QApplication, QMenu, QPushButton, QWidget, QLayout


_MODE_TEXTS = {
    "▣", "▤", "▦",
    "▣ Pequeño", "▤ Compacto", "▦ Expandido",
    "▣  Pequeño", "▤  Compacto", "▦  Expandido",
}

_SETTINGS_TEXTS = {"⚙", "⚙ Personalización", "⚙  Personalización"}


def _clean_text(widget: QPushButton) -> str:
    return " ".join((widget.text() or "").split())


def _is_mode_button(widget: QPushButton) -> bool:
    return _clean_text(widget) in {"▣", "▤", "▦", "▣ Pequeño", "▤ Compacto", "▦ Expandido"}


def _is_settings_button(widget: QPushButton) -> bool:
    text = _clean_text(widget)
    tooltip = (widget.toolTip() or "").lower()
    return text in _SETTINGS_TEXTS or "personaliz" in tooltip or "tema" in tooltip


def _find_layout_index(widget: QWidget) -> tuple[Optional[QLayout], int]:
    current: Optional[QWidget] = widget
    while current is not None:
        layout = current.layout()
        if layout is not None:
            index = layout.indexOf(widget)
            if index >= 0:
                return layout, index
        current = current.parentWidget()
    return None, -1


def _menu_for(player: QWidget, anchor: QPushButton) -> None:
    menu = QMenu(player)
    menu.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

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
    personalization.triggered.connect(
        lambda: getattr(player, "open_personalization_dialog", lambda: None)()
    )

    menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))


def _set_mode(player: QWidget, mode: str) -> None:
    setter = getattr(player, "set_view_mode", None)
    if callable(setter):
        setter(mode)


def _make_menu_button(player: QWidget, layout: QLayout, index: int, parent: QWidget) -> QPushButton:
    button = QPushButton("⋮", parent)
    button.setObjectName("unifiedModeMenuButton")
    button.setFixedSize(30, 30)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setToolTip("Modos y personalización")
    button.clicked.connect(lambda: _menu_for(player, button))
    layout.insertWidget(max(0, index), button)
    return button


def _collapse_legacy_controls(player: QWidget) -> bool:
    buttons = [b for b in player.findChildren(QPushButton) if _is_mode_button(b)]
    settings = [b for b in player.findChildren(QPushButton) if _is_settings_button(b)]
    if not buttons:
        return False

    # Group mode buttons by the layout that actually owns them. This handles normal,
    # compact and expanded layouts without hard-coding their private widget names.
    groups: dict[int, tuple[QLayout, int, list[QPushButton]]] = {}
    for button in buttons:
        layout, index = _find_layout_index(button)
        if layout is None:
            continue
        key = id(layout)
        if key not in groups:
            groups[key] = (layout, index, [])
        groups[key][2].append(button)

    changed = False
    for layout, index, group in groups.values():
        # In expanded view the three buttons may live inside a segmented child widget.
        # Replace that whole segment, preserving the position in its parent layout.
        if len(group) >= 3:
            host = group[0].parentWidget()
            parent_layout, parent_index = _find_layout_index(host) if host is not None else (None, -1)
            if parent_layout is not None and parent_index >= 0:
                if not any(
                    isinstance(parent_layout.itemAt(i).widget(), QPushButton)
                    and parent_layout.itemAt(i).widget().objectName() == "unifiedModeMenuButton"
                    for i in range(parent_layout.count())
                ):
                    for button in group:
                        button.hide()
                    if host is not player:
                        host.hide()
                    _make_menu_button(player, parent_layout, parent_index, host.parentWidget() or player)
                    changed = True
                continue

        for button in group:
            button.hide()
        if not any(
            isinstance(layout.itemAt(i).widget(), QPushButton)
            and layout.itemAt(i).widget().objectName() == "unifiedModeMenuButton"
            for i in range(layout.count())
        ):
            _make_menu_button(player, layout, index, group[0].parentWidget() or player)
            changed = True

    # Hide standalone personalization buttons. The action remains available inside the menu.
    for button in settings:
        if button.objectName() != "unifiedModeMenuButton":
            button.hide()

    return changed


def install(player: QWidget) -> None:
    """Instala el selector unificado sin alterar la lógica interna de los modos."""
    attempts = {"count": 0}

    def apply() -> None:
        attempts["count"] += 1
        _collapse_legacy_controls(player)
        if attempts["count"] < 30:
            QTimer.singleShot(100, apply)

    QTimer.singleShot(0, apply)
