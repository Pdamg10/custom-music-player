import os
from typing import Optional, List
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint, QRectF, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QColor, QPainter, QMouseEvent
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QScrollArea,
    QFrame, QSizePolicy, QPushButton
)
from lyrics_manager import LyricLine, LyricsFetcherThread


class LyricLineWidget(QLabel):
    """Línea de letra interactiva con soporte de sincronización y estado activo destacado."""
    clicked = pyqtSignal(int)

    def __init__(self, index: int, line: LyricLine, is_synced: bool = True, parent: Optional[QWidget] = None) -> None:
        super().__init__(line.text or "...", parent)
        self.index = index
        self.line = line
        self.is_synced = is_synced
        self.is_active = False
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setCursor(Qt.CursorShape.PointingHandCursor if (is_synced and line.time_ms >= 0) else Qt.CursorShape.ArrowCursor)
        self._update_style()

    def set_active(self, active: bool, accent_color: str = "#ff1744") -> None:
        if self.is_active != active:
            self.is_active = active
            self._update_style(accent_color)

    def _update_style(self, accent_color: str = "#ff1744") -> None:
        clean_accent = accent_color.split(';')[0].strip() if accent_color else "#ff1744"
        if not self.is_synced:
            # Letra plana (sin sincronización temporal)
            self.setFont(QFont("Sans Serif", 12))
            self.setStyleSheet("""
                QLabel {
                    color: rgba(255, 255, 255, 0.85);
                    background: transparent;
                    border: none;
                    padding: 6px 12px;
                    line-height: 1.4;
                }
            """)
        elif self.is_active:
            # Frase / oración activa: aumentada de tamaño, color blanco brillante con relieve suave
            self.setFont(QFont("Sans Serif", 16, QFont.Weight.Bold))
            self.setStyleSheet(f"""
                QLabel {{
                    color: #ffffff;
                    background-color: rgba(255, 255, 255, 0.14);
                    border: 1.5px solid rgba(255, 255, 255, 0.28);
                    border-radius: 12px;
                    padding: 10px 18px;
                }}
            """)
        else:
            # Frases inactivas: color gris elegante, tamaño estándar
            self.setFont(QFont("Sans Serif", 12))
            self.setStyleSheet("""
                QLabel {
                    color: rgba(255, 255, 255, 0.38);
                    background: transparent;
                    border: 1px solid transparent;
                    border-radius: 8px;
                    padding: 5px 12px;
                }
                QLabel:hover {
                    color: rgba(255, 255, 255, 0.85);
                    background-color: rgba(255, 255, 255, 0.06);
                }
            """)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.is_synced and self.line.time_ms >= 0:
            self.clicked.emit(self.line.time_ms)
        super().mousePressEvent(event)


class LyricsDisplayWidget(QWidget):
    """Contenedor de visualización y sincronización de letras para la vista En Reproducción con animación suave."""
    seek_requested = pyqtSignal(int)  # Salto de tiempo en milisegundos

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.accent_color: str = "#ff1744"
        self.lyrics_lines: List[LyricLine] = []
        self.is_synced: bool = False
        self.active_index: int = -1
        self.line_widgets: List[LyricLineWidget] = []
        self._is_manual_scrolling: bool = False
        self.fetcher_thread: Optional[LyricsFetcherThread] = None
        self.current_meta: dict = {}

        # Temporizador para reanudar el auto-desplazamiento si el usuario hace scroll manual
        self.user_scroll_timer = QTimer(self)
        self.user_scroll_timer.setSingleShot(True)
        self.user_scroll_timer.setInterval(3000)
        self.user_scroll_timer.timeout.connect(self._resume_auto_scroll)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(120)

        self._setup_ui()

        # Animación de scroll suave con curva cúbica
        self.scroll_animation = QPropertyAnimation(self.scroll_area.verticalScrollBar(), b"value", self)
        self.scroll_animation.setDuration(420)
        self.scroll_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ScrollArea transparente
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.scroll_area.setMinimumHeight(100)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                width: 4px;
                background: transparent;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.20);
                min-height: 20px;
                border-radius: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.40);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent; border: none;")
        self.lines_layout = QVBoxLayout(self.scroll_content)
        self.lines_layout.setContentsMargins(10, 10, 10, 10)
        self.lines_layout.setSpacing(8)
        self.lines_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        # Estado inicial / mensaje
        self.lbl_status = QLabel("♪ Esperando reproducción...", self.scroll_content)
        self.lbl_status.setFont(QFont("Sans Serif", 11, QFont.Weight.Medium))
        self.lbl_status.setStyleSheet("color: rgba(255, 255, 255, 0.35); background: transparent; border: none;")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lines_layout.addWidget(self.lbl_status)

        self.scroll_area.setWidget(self.scroll_content)
        self.scroll_area.verticalScrollBar().sliderPressed.connect(self._on_user_scroll_start)
        main_layout.addWidget(self.scroll_area)

    def set_accent_color(self, hex_color: str) -> None:
        if hex_color:
            self.accent_color = hex_color
            if 0 <= self.active_index < len(self.line_widgets):
                self.line_widgets[self.active_index].set_active(True, self.accent_color)

    def load_lyrics_for_track(self, track_meta: dict) -> None:
        """Inicia la búsqueda offline y online de letras para la pista activa en segundo plano."""
        self.current_meta = dict(track_meta or {})
        self.lyrics_lines = []
        self.line_widgets = []
        self.active_index = -1
        self.is_synced = False
        self._is_manual_scrolling = False

        if hasattr(self, "scroll_animation") and self.scroll_animation.state() == QPropertyAnimation.State.Running:
            self.scroll_animation.stop()

        # Cancelar hilo previo si sigue activo
        if self.fetcher_thread and self.fetcher_thread.isRunning():
            self.fetcher_thread.requestInterruption()
            self.fetcher_thread.quit()
            self.fetcher_thread.wait(200)

        # Limpiar contenedor visual y mostrar indicador de carga
        self._clear_layout()
        title = self.current_meta.get("title", "")
        if not title or title in ("Sin reproducción", "Desconocido"):
            self._show_message("♪ Selecciona una canción para ver su letra")
            return

        self._show_message("♪ Buscando letras...")

        self.fetcher_thread = LyricsFetcherThread(self.current_meta, self)
        self.fetcher_thread.lyrics_loaded.connect(self._on_lyrics_loaded)
        self.fetcher_thread.lyrics_not_found.connect(self._on_lyrics_not_found)
        self.fetcher_thread.start()

    def _on_lyrics_loaded(self, raw_text: str, parsed_lines: list, is_synced: bool) -> None:
        self.lyrics_lines = parsed_lines
        self.is_synced = is_synced
        self._populate_lyrics_ui()

    def _on_lyrics_not_found(self) -> None:
        self._clear_layout()
        self._show_message("♪ Sin letras disponibles para esta pista")

    def _clear_layout(self) -> None:
        while self.lines_layout.count() > 0:
            item = self.lines_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
        self.line_widgets = []

    def _show_message(self, msg: str) -> None:
        self._clear_layout()
        lbl = QLabel(msg, self.scroll_content)
        lbl.setFont(QFont("Sans Serif", 10, QFont.Weight.Medium))
        lbl.setStyleSheet("color: rgba(255, 255, 255, 0.40); background: transparent; border: none;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lines_layout.addWidget(lbl)

    def _populate_lyrics_ui(self) -> None:
        self._clear_layout()
        if not self.lyrics_lines:
            self._show_message("♪ Sin letras disponibles")
            return

        # Espaciador superior generoso para permitir centrar la primera línea en el visor
        viewport_h = max(200, self.scroll_area.viewport().height())
        top_spacer_h = max(30, int(viewport_h * 0.35))
        self.lines_layout.addSpacing(top_spacer_h)

        for idx, line in enumerate(self.lyrics_lines):
            line_w = LyricLineWidget(idx, line, is_synced=self.is_synced, parent=self.scroll_content)
            line_w.clicked.connect(self._on_line_clicked)
            self.lines_layout.addWidget(line_w)
            self.line_widgets.append(line_w)

        # Espaciador inferior generoso para permitir centrar la última línea
        self.lines_layout.addSpacing(top_spacer_h)

        # Reset posición de scroll al inicio
        self.scroll_area.verticalScrollBar().setValue(0)

    def _on_line_clicked(self, time_ms: int) -> None:
        if time_ms >= 0:
            self.seek_requested.emit(time_ms)

    def update_position(self, pos_ms: int) -> None:
        """Actualiza la línea activa y centra la vista en función del tiempo actual de reproducción."""
        if not self.is_synced or not self.lyrics_lines or not self.line_widgets:
            return

        # Buscar la línea activa correspondiente al tiempo actual
        new_active = -1
        for i, line in enumerate(self.lyrics_lines):
            if line.time_ms <= pos_ms:
                new_active = i
            else:
                break

        if new_active != self.active_index and new_active >= 0:
            # Desactivar la línea anterior
            if 0 <= self.active_index < len(self.line_widgets):
                self.line_widgets[self.active_index].set_active(False)

            self.active_index = new_active

            # Activar la nueva línea
            if 0 <= self.active_index < len(self.line_widgets):
                active_w = self.line_widgets[self.active_index]
                active_w.set_active(True, self.accent_color)

                # Si el usuario no está haciendo scroll manual, centrar suavemente la línea activa
                if not self._is_manual_scrolling:
                    self._center_on_widget(active_w, smooth=True)

    def _center_on_widget(self, target_widget: QWidget, smooth: bool = True) -> None:
        if not target_widget or not self.scroll_area:
            return

        def do_scroll():
            try:
                if not target_widget or not self.scroll_area:
                    return
                viewport_h = self.scroll_area.viewport().height()
                pos_in_content = target_widget.mapTo(self.scroll_content, QPoint(0, 0))
                widget_y = pos_in_content.y()
                widget_h = target_widget.height()
                target_scroll = max(0, int(widget_y + widget_h / 2 - viewport_h / 2))

                v_bar = self.scroll_area.verticalScrollBar()
                current_scroll = v_bar.value()

                if not smooth:
                    v_bar.setValue(target_scroll)
                    return

                if abs(target_scroll - current_scroll) > 1:
                    if self.scroll_animation.state() == QPropertyAnimation.State.Running:
                        self.scroll_animation.stop()
                    self.scroll_animation.setStartValue(current_scroll)
                    self.scroll_animation.setEndValue(target_scroll)
                    self.scroll_animation.start()
            except Exception:
                pass

        QTimer.singleShot(20, do_scroll)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if not self._is_manual_scrolling and 0 <= self.active_index < len(self.line_widgets):
            self._center_on_widget(self.line_widgets[self.active_index], smooth=False)

    def wheelEvent(self, event) -> None:
        if hasattr(self, "scroll_animation") and self.scroll_animation.state() == QPropertyAnimation.State.Running:
            self.scroll_animation.stop()
        self._is_manual_scrolling = True
        self.user_scroll_timer.start()
        super().wheelEvent(event)

    def _on_user_scroll_start(self) -> None:
        if hasattr(self, "scroll_animation") and self.scroll_animation.state() == QPropertyAnimation.State.Running:
            self.scroll_animation.stop()
        self._is_manual_scrolling = True
        self.user_scroll_timer.start()

    def _resume_auto_scroll(self) -> None:
        self._is_manual_scrolling = False
        if 0 <= self.active_index < len(self.line_widgets):
            self._center_on_widget(self.line_widgets[self.active_index], smooth=True)
