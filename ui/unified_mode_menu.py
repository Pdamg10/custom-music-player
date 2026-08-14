from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QMenu, QPushButton, QWidget, QLayout


MODE_BUTTON_NAMES = {
    "btn_norm_mode_small",
    "btn_norm_mode_compact",
    "btn_norm_mode_expanded",
}
SETTINGS_BUTTON_NAMES = {"btn_norm_settings"}


def _find_direct_layout(layout: QLayout, target: QWidget) -> tuple[Optional[QLayout], int]:
    for index in range(layout.count()):
        item = layout.itemAt(index)
        if item.widget() is target:
            return layout, index
        child = item.layout()
        if child is not None:
            owner, child_index = _find_direct_layout(child, target)
            if owner is not None:
                return owner, child_index
    return None, -1


def _owning_layout(player: QWidget, widget: QWidget) -> tuple[Optional[QLayout], int]:
    root = player.layout()
    return _find_direct_layout(root, widget) if root is not None else (None, -1)


def _set_mode(player: QWidget, mode: str) -> None:
    setter = getattr(player, "set_view_mode", None)
    if callable(setter):
        setter(mode)


def _open_personalization(player: QWidget) -> None:
    opener = getattr(player, "open_personalization_dialog", None)
    if callable(opener):
        opener()


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


def _create_button(player: QWidget, layout: QLayout, index: int, parent: QWidget) -> QPushButton:
    button = QPushButton("⋮", parent)
    button.setObjectName("unifiedModeMenuButton")
    button.setFixedSize(30, 30)
    button.setMinimumSize(30, 30)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setToolTip("Modos y personalización")
    button.setStyleSheet(
        "QPushButton#unifiedModeMenuButton {"
        "background: rgba(25, 28, 44, 0.85);"
        "color: white;"
        "border: 1px solid rgba(255,255,255,0.25);"
        "border-radius: 15px;"
        "font-size: 18px;"
        "font-weight: bold;"
        "padding: 0px;"
        "}"
        "QPushButton#unifiedModeMenuButton:hover {"
        "background: rgba(255,255,255,0.18);"
        "border: 1px solid rgba(255,255,255,0.55);"
        "}"
        "QPushButton#unifiedModeMenuButton:pressed {"
        "background: rgba(255,255,255,0.28);"
        "}"
    )
    button.clicked.connect(lambda: _show_menu(player, button))
    layout.insertWidget(max(0, index), button)
    return button


def _is_installed(player: QWidget) -> bool:
    return bool(player.findChildren(QPushButton, "unifiedModeMenuButton"))


def _install_for_top_bar(player: QWidget) -> bool:
    """Replace the four controls in the shared normal/compact top bar with one button."""
    controls = [player.findChild(QPushButton, name) for name in MODE_BUTTON_NAMES | SETTINGS_BUTTON_NAMES]
    controls = [button for button in controls if button is not None]
    if len(controls) < 4:
        return False

    # All four controls are intentionally in the same top_bar_layout.
    layout, first_index = _owning_layout(player, controls[0])
    if layout is None:
        return False

    # If already replaced, simply keep the legacy controls hidden.
    if _is_installed(player):
        for button in controls:
            button.hide()
        return True

    for button in controls:
        button.hide()

    _create_button(player, layout, first_index, controls[0].parentWidget() or player)
    return True


def _install_for_expanded(player: QWidget) -> bool:
    """Handle the expanded view's own mode controls if it has a separate segment."""
    expanded = getattr(player, "expanded_page", None)
    if expanded is None:
        return False

    candidates = []
    for button in expanded.findChildren(QPushButton):
        text = " ".join((button.text() or "").split()).lower()
        tooltip = (button.toolTip() or "").lower()
        if any(key in text for key in ("peque", "compact", "expand")) or any(key in tooltip for key in ("peque", "compact", "expand")):
            candidates.append(button)

    if len(candidates) < 3:
        return False

    layout, index = _owning_layout(expanded, candidates[0])
    if layout is None:
        return False

    for button in candidates:
        button.hide()

    if not any(
        isinstance(layout.itemAt(i).widget(), QPushButton)
        and layout.itemAt(i).widget().objectName() == "unifiedModeMenuButton"
        for i in range(layout.count())
    ):
        _create_button(player, layout, index, candidates[0].parentWidget() or expanded)
    return True


def install(player: QWidget) -> None:
    """Replace the four existing mode/customization controls with one real menu button."""
    attempts = {"count": 0}

    def apply() -> None:
        attempts["count"] += 1
        _install_for_top_bar(player)
        _install_for_expanded(player)
        if attempts["count"] < 30:
            QTimer.singleShot(100, apply)

    QTimer.singleShot(0, apply)
