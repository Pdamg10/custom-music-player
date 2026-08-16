from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QMenu, QPushButton, QWidget, QLayout

from ui.small_playlist import SmallPlaylistPage


NORM_BUTTON_NAMES = (
    "btn_norm_mode_small",
    "btn_norm_mode_compact",
    "btn_norm_mode_expanded",
    "btn_norm_settings",
)

COMP_BUTTON_NAMES = (
    "btn_comp_mode_small",
    "btn_comp_mode_compact",
    "btn_comp_mode_expanded",
    "btn_comp_settings",
)


def _find_direct_layout_of(target: QWidget) -> tuple[Optional[QLayout], int]:
    """Encuentra el QLayout que contiene directamente al widget."""
    parent = target.parentWidget()
    if parent is None or parent.layout() is None:
        return None, -1

    def search(layout: QLayout) -> tuple[Optional[QLayout], int]:
        for index in range(layout.count()):
            item = layout.itemAt(index)
            if item.widget() is target:
                return layout, index
            child_layout = item.layout()
            if child_layout is not None:
                found, child_index = search(child_layout)
                if found is not None:
                    return found, child_index
        return None, -1

    return search(parent.layout())


def _close_small_playlist(player: QWidget) -> None:
    page = getattr(player, "small_playlist_page", None)
    stacked = getattr(player, "stacked", None)
    current_mode = getattr(player, "view_mode", "normal")
    target_page = getattr(player, "compact_page", None) if current_mode == "compact" else getattr(player, "normal_page", None)
    if page is not None and stacked is not None and target_page is not None:
        stacked.setCurrentWidget(target_page)
        page.search.clear()


def _set_mode(player: QWidget, mode: str) -> None:
    _close_small_playlist(player)
    setter = getattr(player, "set_view_mode", None)
    if callable(setter):
        setter(mode)


def _show_small_playlist(player: QWidget) -> None:
    if getattr(player, "view_mode", "normal") not in ("normal", "compact"):
        return

    page = getattr(player, "small_playlist_page", None)
    stacked = getattr(player, "stacked", None)
    if page is not None and stacked is not None:
        stacked.setCurrentWidget(page)
        page.search.setFocus()


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
    for text, mode in (
        ("▣  Pequeño", "normal"),
        ("▤  Compacto", "compact"),
        ("▦  Expandido", "expanded"),
    ):
        action = menu.addAction(text)
        action.setCheckable(True)
        action.setChecked(current == mode)
        action.triggered.connect(lambda checked=False, value=mode: _set_mode(player, value))

    if current in ("normal", "compact"):
        menu.addSeparator()
        playlist_action = menu.addAction("♫  Canciones")
        playlist_action.setToolTip("Ver y buscar canciones")
        playlist_action.triggered.connect(lambda: _show_small_playlist(player))

    menu.addSeparator()
    action = menu.addAction("⚙  Personalización")
    action.triggered.connect(lambda: _open_personalization(player))
    menu.exec(button.mapToGlobal(button.rect().bottomLeft()))


def _create_button(
    player: QWidget,
    layout: QLayout,
    index: int,
    parent: QWidget,
    button_name: str,
) -> QPushButton:
    is_expanded = button_name == "btn_exp_unified_menu"
    size = 36 if is_expanded else 26
    radius = size // 2
    font_size = 18 if is_expanded else 14

    button = QPushButton("⋮", parent)
    button.setObjectName(button_name)
    button.setFixedSize(size, size)
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


def _install_playlist_page(player: QWidget) -> None:
    if getattr(player, "small_playlist_page", None) is not None:
        return

    page = SmallPlaylistPage(player.stacked)
    player.small_playlist_page = page
    player.stacked.addWidget(page)

    page.play_requested.connect(player.mpris.play_index)
    page.close_requested.connect(lambda: _close_small_playlist(player))

    if hasattr(player.mpris, "playlist_updated"):
        player.mpris.playlist_updated.connect(page.set_playlist)
    if hasattr(player.mpris, "metadata_changed"):
        player.mpris.metadata_changed.connect(
            lambda meta: page.set_current_index(getattr(player.mpris, "current_index", -1))
        )

    page.set_playlist(
        getattr(player.mpris, "playlist", []),
        getattr(player.mpris, "current_index", -1),
    )


def _install_for_normal(player: QWidget) -> bool:
    controls = [
        getattr(player, name, None) or player.findChild(QPushButton, name)
        for name in NORM_BUTTON_NAMES
    ]
    controls = [button for button in controls if button is not None]
    if not controls:
        return False

    is_normal = (getattr(player, "view_mode", "normal") == "normal")

    existing_btn = getattr(player, "btn_norm_unified_menu", None) or player.findChild(
        QPushButton, "btn_norm_unified_menu"
    )
    if existing_btn is not None:
        for button in controls:
            button.hide()
        existing_btn.setVisible(is_normal)
        return True

    layout, index = _find_direct_layout_of(controls[0])
    if layout is None:
        return False

    for button in controls:
        button.hide()

    player.btn_norm_unified_menu = _create_button(
        player, layout, index, controls[0].parentWidget() or player, "btn_norm_unified_menu"
    )
    player.btn_norm_unified_menu.setVisible(is_normal)
    return True


def _install_for_compact(player: QWidget) -> bool:
    compact_page = getattr(player, "compact_page", None)
    container = compact_page or player
    controls = [
        getattr(player, name, None) or container.findChild(QPushButton, name)
        for name in COMP_BUTTON_NAMES
    ]
    controls = [button for button in controls if button is not None]
    if not controls:
        return False

    is_compact = (getattr(player, "view_mode", "normal") == "compact")

    existing_btn = getattr(player, "btn_comp_unified_menu", None) or container.findChild(
        QPushButton, "btn_comp_unified_menu"
    )
    if existing_btn is not None:
        for button in controls:
            button.hide()
        existing_btn.setVisible(is_compact)
        return True

    layout, index = _find_direct_layout_of(controls[0])
    if layout is None:
        return False

    for button in controls:
        button.hide()

    player.btn_comp_unified_menu = _create_button(
        player, layout, index, controls[0].parentWidget() or container, "btn_comp_unified_menu"
    )
    player.btn_comp_unified_menu.setVisible(is_compact)
    return True


def _install_for_expanded(player: QWidget) -> bool:
    return False


def install(player: QWidget) -> None:
    """Instala el selector unificado y la lista exclusiva del modo Pequeño."""
    _install_playlist_page(player)
    attempts = {"count": 0}

    def apply() -> None:
        attempts["count"] += 1
        _install_for_normal(player)
        _install_for_compact(player)
        if attempts["count"] < 30:
            QTimer.singleShot(100, apply)

    apply()
