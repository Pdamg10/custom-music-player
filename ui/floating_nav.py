"""
ui/floating_nav.py - Widget flotante de navegación para listas de canciones.

Proporciona botones flotantes de acción rápida (FAB) para:
1. Ir a la canción actual / sonando.
2. Volver al inicio de la lista.
Se ancla automáticamente en la esquina inferior derecha del viewport o contenedor,
manteniéndose siempre visible y disponible en cualquier punto del scroll.
"""

from typing import Any, Callable, Optional

from PyQt6.QtCore import QEvent, QSize, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.icon_manager import set_button_icon


class FloatingListNavWidget(QFrame):
    """Widget flotante tipo 'pill' con botones para saltar a la canción actual y al inicio."""

    def __init__(
        self,
        parent: QWidget,
        on_go_to_current: Callable[[], None],
        on_go_to_top: Callable[[], None],
        accent_color: str = "#ff1744",
        offset_x: int = 24,
        offset_y: int = 24,
    ) -> None:
        super().__init__(parent)
        self.on_go_to_current = on_go_to_current
        self.on_go_to_top = on_go_to_top
        self.accent_color = accent_color
        self.offset_x = offset_x
        self.offset_y = offset_y

        self.setObjectName("FloatingListNavWidget")
        self.setFixedSize(46, 92)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._build_ui()
        self._apply_style()

        # Instalar filtro de eventos en el padre para reposicionamiento automático
        if parent:
            parent.installEventFilter(self)
        self.reposition()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 6, 5, 6)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 1. Botón superior: Ir al inicio (flecha hacia arriba)
        self.btn_top = QPushButton(self)
        self.btn_top.setObjectName("btn_floating_top")
        self.btn_top.setFixedSize(36, 36)
        self.btn_top.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_top.setToolTip("Volver al inicio de la lista")
        set_button_icon(self.btn_top, "scroll_top", "#ffffff", 16)
        self.btn_top.clicked.connect(self._on_top_clicked)
        layout.addWidget(self.btn_top)

        # 2. Botón inferior: Ir a la canción actual (diana / locate)
        self.btn_current = QPushButton(self)
        self.btn_current.setObjectName("btn_floating_current")
        self.btn_current.setFixedSize(36, 36)
        self.btn_current.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_current.setToolTip("Ir a la canción actual / sonando")
        set_button_icon(self.btn_current, "current_track", "#ffffff", 16)
        self.btn_current.clicked.connect(self._on_current_clicked)
        layout.addWidget(self.btn_current)

        # Sombra suave de alta definición
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

    def _apply_style(self) -> None:
        clean_accent = self.accent_color.split(";")[0].strip() or "#ff1744"
        self.setStyleSheet(f"""
            QFrame#FloatingListNavWidget {{
                background-color: rgba(14, 18, 30, 0.88);
                border: 1.5px solid rgba(255, 255, 255, 0.18);
                border-radius: 23px;
            }}
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 18px;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.22);
                border-color: {clean_accent};
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 255, 255, 0.35);
            }}
        """)

    def update_accent_color(self, accent_color: str) -> None:
        self.accent_color = accent_color
        self._apply_style()

    def _on_top_clicked(self) -> None:
        if callable(self.on_go_to_top):
            self.on_go_to_top()

    def _on_current_clicked(self) -> None:
        if callable(self.on_go_to_current):
            self.on_go_to_current()

    def reposition(self) -> None:
        """Calcula y fija la posición en la esquina inferior derecha del widget padre."""
        p = self.parentWidget()
        if not p:
            return
        pw = p.width()
        ph = p.height()
        w = self.width()
        h = self.height()
        # Si el padre aún no se ha dibujado, evitar mover fuera
        if pw <= 10 or ph <= 10:
            return
        target_x = max(10, pw - w - self.offset_x)
        target_y = max(10, ph - h - self.offset_y)
        self.move(target_x, target_y)
        self.raise_()

    def eventFilter(self, obj: Any, event: QEvent) -> bool:
        if obj == self.parentWidget() and event.type() in (
            QEvent.Type.Resize,
            QEvent.Type.Show,
            QEvent.Type.Move,
        ):
            self.reposition()
        return super().eventFilter(obj, event)
