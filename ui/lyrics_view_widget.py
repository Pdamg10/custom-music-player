from typing import Optional, List, Dict, Any
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint, QPropertyAnimation, QEasingCurve, QThread
from PyQt6.QtGui import QFont, QMouseEvent, QActionGroup, QColor
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QScrollArea,
    QSizePolicy, QPushButton, QMenu, QProgressDialog, QGraphicsDropShadowEffect
)
from PyQt6 import sip
from lyrics_manager import LyricLine, LyricsFetcherThread, to_romaji
from lyrics_translator import get_lyrics_translator, SUPPORTED_LANGUAGES


class LyricLineWidget(QLabel):
    """Línea de letra interactiva con soporte multilingüe (Original / Romaji / Traducción) y sincronización temporal con paleta adaptativa."""
    clicked = pyqtSignal(int)

    def __init__(
        self,
        index: int,
        line: LyricLine,
        translated_text: Optional[str] = None,
        romaji_text: Optional[str] = None,
        is_synced: bool = True,
        accent_color: str = "#ff1744",
        font_family: str = "Sans Serif",
        theme_palette: Optional[Dict[str, Any]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(line.text or "...", parent)
        self.index = index
        self.line = line
        self.translated_text = translated_text
        self.romaji_text = romaji_text
        self.is_synced = is_synced
        self.accent_color = accent_color
        self.font_family = font_family or "Sans Serif"
        self.theme_palette: Dict[str, Any] = dict(theme_palette or {})
        self.is_active = False
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setCursor(Qt.CursorShape.PointingHandCursor if (is_synced and line.time_ms >= 0) else Qt.CursorShape.ArrowCursor)

        self._shadow_effect = QGraphicsDropShadowEffect(self)
        self._shadow_effect.setOffset(0, 1)
        self._shadow_effect.setBlurRadius(5)
        self._apply_shadow_color()
        self.setGraphicsEffect(self._shadow_effect)

        self._update_style()

    def _apply_shadow_color(self) -> None:
        if not hasattr(self, '_shadow_effect') or not self._shadow_effect:
            return
        col = self.theme_palette.get("shadow_color", QColor(0, 0, 0, 220))
        if isinstance(col, str):
            col = QColor(col)
        self._shadow_effect.setColor(col)

    def set_theme_palette(self, palette: Dict[str, Any]) -> None:
        self.theme_palette = dict(palette or {})
        self._apply_shadow_color()
        self._update_style()

    def set_active(self, active: bool, accent_color: str = "") -> None:
        if accent_color:
            self.accent_color = accent_color
        if self.is_active != active:
            self.is_active = active
            self._update_style(self.accent_color)

    def set_romaji_text(self, romaji: Optional[str]) -> None:
        self.romaji_text = romaji
        self._update_style()

    def set_translated_text(self, trans: Optional[str]) -> None:
        self.translated_text = trans
        self._update_style()

    def set_accent_color(self, hex_color: str) -> None:
        if hex_color:
            self.accent_color = hex_color
            self._update_style(hex_color)

    def _update_style(self, accent_color: str = "") -> None:
        clean_accent = (accent_color or self.accent_color or "#ff1744").split(';')[0].strip()
        fam = getattr(self, 'font_family', 'Sans Serif') or 'Sans Serif'
        orig_text = self.line.text or "..."
        pal = getattr(self, 'theme_palette', {}) or {}

        qc = QColor(clean_accent)
        if not qc.isValid():
            qc = QColor("#ff1744")
        r, g, b = qc.red(), qc.green(), qc.blue()

        # Determinar si hay Romaji (Hepburn) y si no es idéntico al texto original
        has_romaji = bool(
            self.romaji_text
            and self.romaji_text.strip()
            and self.romaji_text.strip().lower() != orig_text.strip().lower()
        )
        rom_text = self.romaji_text.strip() if has_romaji else ""

        # Determinar si hay Traducción y si no es idéntica al texto original
        has_translation = bool(
            self.translated_text
            and self.translated_text.strip()
            and self.translated_text.strip().lower() != orig_text.strip().lower()
        )
        trans_text = self.translated_text.strip() if has_translation else ""

        def build_html(orig_style: str, rom_style: str, trans_style: str) -> str:
            # Fila 1: Idioma original (Kanji + Hiragana para japonés)
            rows = [f"<span style='{orig_style}'>{orig_text}</span>"]
            # Fila 2: Romaji fonético (Hepburn, para japonés u otros alfabetos no latinos)
            if has_romaji:
                rows.append(f"<span style='{rom_style}'>{rom_text}</span>")
            # Fila 3: Traducción (al idioma configurado por el usuario, ej. Español)
            if has_translation:
                rows.append(f"<span style='{trans_style}'>{trans_text}</span>")
            return "<br>".join(rows)

        if hasattr(self, '_shadow_effect') and self._shadow_effect:
            self._shadow_effect.setBlurRadius(8 if self.is_active else 5)

        if not self.is_synced:
            # Letra plana (sin timestamps sincronizados)
            self.setFont(QFont(fam, 12))
            unsynced_orig_color = pal.get("unsynced_orig", "rgba(255, 255, 255, 0.90)")
            unsynced_rom_color = pal.get("unsynced_romaji", "rgba(255, 213, 79, 0.85)")
            unsynced_trans_color = pal.get("unsynced_trans", f"rgba({r}, {g}, {b}, 0.88)")

            self.setStyleSheet(f"""
                QLabel {{
                    color: {unsynced_orig_color};
                    background: transparent;
                    border: none;
                    padding: 6px 14px;
                    line-height: 1.45;
                    font-family: '{fam}', 'Sans Serif', sans-serif;
                }}
            """)
            self.setText(build_html(
                orig_style=f"color: {unsynced_orig_color}; font-size: 12pt; font-weight: 500;",
                rom_style=f"color: {unsynced_rom_color}; font-size: 10.5pt; font-weight: 500;",
                trans_style=f"color: {unsynced_trans_color}; font-size: 10pt; font-style: italic;",
            ))

        elif self.is_active:
            # Frase activa resaltada en tiempo real
            self.setFont(QFont(fam, 16, QFont.Weight.Bold))
            active_orig_color = pal.get("active_orig", "#ffffff")
            active_rom_color = pal.get("active_romaji", "#ffe082")
            active_trans_color = pal.get("active_trans", clean_accent)
            active_bg = pal.get("active_bg", "rgba(255, 255, 255, 0.14)")
            active_border = pal.get("active_border", "rgba(255, 255, 255, 0.28)")

            self.setStyleSheet(f"""
                QLabel {{
                    color: {active_orig_color};
                    background-color: {active_bg};
                    border: 1.5px solid {active_border};
                    border-radius: 12px;
                    padding: 10px 18px;
                    line-height: 1.45;
                    font-family: '{fam}', 'Sans Serif', sans-serif;
                }}
            """)
            self.setText(build_html(
                orig_style=f"color: {active_orig_color}; font-size: 16pt; font-weight: bold;",
                rom_style=f"color: {active_rom_color}; font-size: 12.5pt; font-weight: 600;",
                trans_style=f"color: {active_trans_color}; font-size: 12pt; font-style: italic; font-weight: 500;",
            ))

        else:
            # Frases inactivas
            self.setFont(QFont(fam, 12))
            inact_orig_color = pal.get("inactive_orig", "rgba(255, 255, 255, 0.78)")
            inact_rom_color = pal.get("inactive_romaji", "rgba(255, 224, 130, 0.78)")
            inact_trans_color = pal.get("inactive_trans", f"rgba({r}, {g}, {b}, 0.76)")
            inact_hover_col = pal.get("inactive_hover_color", "#ffffff")
            inact_hover_bg = pal.get("inactive_hover_bg", "rgba(255, 255, 255, 0.14)")

            self.setStyleSheet(f"""
                QLabel {{
                    color: {inact_orig_color};
                    background: transparent;
                    border: 1px solid transparent;
                    border-radius: 8px;
                    padding: 5px 12px;
                    line-height: 1.45;
                    font-family: '{fam}', 'Sans Serif', sans-serif;
                }}
                QLabel:hover {{
                    color: {inact_hover_col};
                    background-color: {inact_hover_bg};
                }}
            """)
            self.setText(build_html(
                orig_style=f"color: {inact_orig_color}; font-size: 12pt;",
                rom_style=f"color: {inact_rom_color}; font-size: 10pt;",
                trans_style=f"color: {inact_trans_color}; font-size: 9.5pt; font-style: italic;",
            ))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.is_synced and self.line.time_ms >= 0:
            self.clicked.emit(self.line.time_ms)
        super().mousePressEvent(event)


class LyricsTranslationWorker(QThread):
    """Worker en segundo plano para traducir letras sin bloquear la UI ni el hilo de audio."""
    translation_ready = pyqtSignal(str, str, list)      # track_id, target_lang, List[LyricLine]
    translation_error = pyqtSignal(str, str, str)       # track_id, target_lang, error_message
    translation_progress = pyqtSignal(int, int, str)    # current, total, message

    def __init__(
        self,
        track_id: str,
        lyrics_lines: List[LyricLine],
        target_lang: str,
        mode: str = "auto",
        title: str = "",
        artist: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.track_id = track_id
        self.lyrics_lines = lyrics_lines
        self.target_lang = target_lang
        self.mode = mode
        self.title = title
        self.artist = artist
        self._is_cancelled = False

    def cancel(self) -> None:
        self._is_cancelled = True

    def run(self) -> None:
        if self._is_cancelled or not self.lyrics_lines:
            return

        try:
            translator = get_lyrics_translator()

            # 1. Comprobar caché local en SQLite primero
            cached = translator.get_cached_translation(self.track_id, self.target_lang)
            if cached and not self._is_cancelled:
                self.translation_ready.emit(self.track_id, self.target_lang, cached)
                return

            if self._is_cancelled:
                return

            def on_progress(cur: int, tot: int, msg: str) -> None:
                if not self._is_cancelled:
                    self.translation_progress.emit(cur, tot, msg)

            # 2. Traducir con batching, callbacks de progreso y soporte de Letras.com
            translated_lines = translator.translate_and_cache(
                track_id=self.track_id,
                lines=self.lyrics_lines,
                target_lang=self.target_lang,
                mode=self.mode,
                title=self.title,
                artist=self.artist,
                progress_callback=on_progress,
                is_cancelled=lambda: self._is_cancelled,
            )

            if not self._is_cancelled and translated_lines:
                self.translation_ready.emit(self.track_id, self.target_lang, translated_lines)

        except Exception as exc:
            if not self._is_cancelled:
                err_msg = str(exc) or "Error desconocido durante la traducción"
                self.translation_error.emit(self.track_id, self.target_lang, err_msg)


class LyricsDisplayWidget(QWidget):
    """Contenedor de visualización y sincronización de letras para la vista En Reproducción con animación suave y traducción."""
    seek_requested = pyqtSignal(int)  # Salto de tiempo en milisegundos

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.accent_color: str = "#ff1744"
        self.original_lyrics_lines: List[LyricLine] = []
        self.translated_lyrics_lines: List[LyricLine] = []
        self.romaji_lyrics_lines: List[str] = []
        self.lyrics_lines: List[LyricLine] = []
        self.is_synced: bool = False
        self.active_index: int = -1
        self.line_widgets: List[LyricLineWidget] = []
        self._is_manual_scrolling: bool = False
        self.fetcher_thread: Optional[LyricsFetcherThread] = None
        self.translation_worker: Optional[LyricsTranslationWorker] = None
        self._retiring_workers: set = set()
        self.current_meta: dict = {}
        self._current_loaded_track_id: str = ""

        # Opciones de traducción
        self.is_showing_translation: bool = False
        self.target_lang: str = "es"
        self.translation_mode: str = "auto"
        self.font_family: str = "Sans Serif"
        self.cover_palette: Dict[str, Any] = {}
        self.download_progress_dialog: Optional[QProgressDialog] = None

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
        main_layout.setSpacing(6)

        # Barra superior de controles de letras (Título + Estado + Botón Recargar + Botón Traducir)
        header_bar = QHBoxLayout()
        header_bar.setContentsMargins(12, 4, 12, 2)
        header_bar.setSpacing(8)

        self.lbl_header_title = QLabel("♪ LETRAS", self)
        self.lbl_header_title.setFont(QFont("Sans Serif", 10, QFont.Weight.Bold))
        self.lbl_header_title.setStyleSheet("color: rgba(255, 255, 255, 0.45); background: transparent; border: none;")
        header_bar.addWidget(self.lbl_header_title)

        clean_accent = (getattr(self, 'accent_color', '#ff1744') or '#ff1744').split(';')[0].strip()

        self.lbl_translation_status = QLabel("", self)
        self.lbl_translation_status.setFont(QFont("Sans Serif", 9, QFont.Weight.Medium))
        self.lbl_translation_status.setStyleSheet(f"color: {clean_accent}; background: transparent; border: none;")
        self.lbl_translation_status.setVisible(False)
        header_bar.addWidget(self.lbl_translation_status, stretch=1)

        header_bar.addStretch(1)

        # Botón Recargar Letras (sin afectar componentes externos ni reproducción)
        self.btn_reload_lyrics = QPushButton("🔄", self)
        self.btn_reload_lyrics.setFixedSize(30, 30)
        self.btn_reload_lyrics.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reload_lyrics.setToolTip("Recargar letras de la canción (Buscar versión sincronizada)")
        self.btn_reload_lyrics.clicked.connect(self.reload_lyrics)
        header_bar.addWidget(self.btn_reload_lyrics)

        # Botón Traducir Letras
        self.btn_translate = QPushButton("🌐 Traducir", self)
        self.btn_translate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_translate.setToolTip("Traducir letras a otro idioma")
        self.btn_translate.clicked.connect(self._show_translation_menu)
        header_bar.addWidget(self.btn_translate)

        main_layout.addLayout(header_bar)

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

        # Estado inicial / mensaje con halo de respaldo
        self.lbl_status = QLabel("♪ Esperando reproducción...", self.scroll_content)
        self.lbl_status.setFont(QFont("Sans Serif", 11, QFont.Weight.Medium))
        self.lbl_status.setStyleSheet("color: rgba(255, 255, 255, 0.35); background: transparent; border: none;")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        eff = QGraphicsDropShadowEffect(self.lbl_status)
        eff.setBlurRadius(6)
        eff.setOffset(0, 1)
        eff.setColor(QColor(0, 0, 0, 200))
        self.lbl_status.setGraphicsEffect(eff)
        self.lines_layout.addWidget(self.lbl_status)

        self.scroll_area.setWidget(self.scroll_content)
        self.scroll_area.verticalScrollBar().sliderPressed.connect(self._on_user_scroll_start)
        main_layout.addWidget(self.scroll_area)

        self._update_header_styles()

    def _update_header_styles(self) -> None:
        pal = getattr(self, 'cover_palette', {}) or {}
        clean_accent = (getattr(self, 'accent_color', '#ff1744') or '#ff1744').split(';')[0].strip()

        header_col = pal.get("header_color", "rgba(255, 255, 255, 0.45)")
        lbl_h = getattr(self, 'lbl_header_title', None)
        if lbl_h and not sip.isdeleted(lbl_h):
            try:
                lbl_h.setStyleSheet(f"color: {header_col}; background: transparent; border: none;")
            except (RuntimeError, Exception):
                pass

        trans_col = pal.get("active_trans", clean_accent)
        lbl_t = getattr(self, 'lbl_translation_status', None)
        if lbl_t and not sip.isdeleted(lbl_t):
            try:
                lbl_t.setStyleSheet(f"color: {trans_col}; background: transparent; border: none;")
            except (RuntimeError, Exception):
                pass

        btn_bg = pal.get("btn_bg", "rgba(255, 255, 255, 0.08)")
        btn_col = pal.get("btn_color", "rgba(255, 255, 255, 0.85)")
        btn_border = pal.get("btn_border", "rgba(255, 255, 255, 0.18)")
        btn_hover_bg = pal.get("btn_hover_bg", "rgba(255, 255, 255, 0.18)")
        btn_hover_col = pal.get("btn_hover_color", "#ffffff")

        btn_r = getattr(self, 'btn_reload_lyrics', None)
        if btn_r and not sip.isdeleted(btn_r):
            try:
                btn_r.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {btn_bg};
                        color: {btn_col};
                        font-size: 13px;
                        font-weight: bold;
                        border: 1px solid {btn_border};
                        border-radius: 15px;
                        padding: 0px;
                    }}
                    QPushButton:hover {{
                        background-color: {btn_hover_bg};
                        color: {btn_hover_col};
                        border-color: {clean_accent};
                    }}
                """)
            except (RuntimeError, Exception):
                pass

        btn_tr = getattr(self, 'btn_translate', None)
        if btn_tr and not sip.isdeleted(btn_tr):
            try:
                if getattr(self, 'is_showing_translation', False):
                    act_bg = pal.get("btn_active_bg", "rgba(0, 229, 255, 0.25)")
                    act_col = pal.get("btn_active_color", "#00e5ff")
                    act_border = pal.get("btn_active_border", "#00e5ff")
                    btn_tr.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {act_bg};
                            color: {act_col};
                            font-size: 11px;
                            font-weight: bold;
                            border: 1.5px solid {act_border};
                            border-radius: 8px;
                            padding: 4px 10px;
                        }}
                    """)
                else:
                    btn_tr.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {btn_bg};
                            color: {btn_col};
                            font-size: 11px;
                            font-weight: bold;
                            border: 1px solid {btn_border};
                            border-radius: 8px;
                            padding: 4px 10px;
                        }}
                        QPushButton:hover {{
                            background-color: {btn_hover_bg};
                            color: {btn_hover_col};
                            border-color: {clean_accent};
                        }}
                    """)
            except (RuntimeError, Exception):
                pass

        lbl_s = getattr(self, 'lbl_status', None)
        if lbl_s and not sip.isdeleted(lbl_s):
            try:
                status_col = pal.get("status_color", "rgba(255, 255, 255, 0.35)")
                lbl_s.setStyleSheet(f"color: {status_col}; background: transparent; border: none;")
            except (RuntimeError, Exception):
                self.lbl_status = None
        else:
            self.lbl_status = None

    def set_cover_palette(self, palette: Dict[str, Any]) -> None:
        """Aplica la paleta adaptativa de la carátula al contenedor de letras y a todas las líneas activas/inactivas."""
        self.cover_palette = dict(palette or {})
        c_bg = self.cover_palette.get("container_bg", "rgba(10, 14, 26, 0.58)")
        c_border = self.cover_palette.get("container_border", "rgba(255, 255, 255, 0.12)")
        is_light = self.cover_palette.get("is_light_bg", False)
        sb_handle = "rgba(0, 0, 0, 0.25)" if is_light else "rgba(255, 255, 255, 0.20)"
        sb_handle_hover = "rgba(0, 0, 0, 0.45)" if is_light else "rgba(255, 255, 255, 0.40)"

        if hasattr(self, 'scroll_area') and self.scroll_area and not sip.isdeleted(self.scroll_area):
            try:
                self.scroll_area.setStyleSheet(f"""
                    QScrollArea {{
                        background-color: {c_bg};
                        border: 1px solid {c_border};
                        border-radius: 16px;
                    }}
                    QScrollBar:vertical {{
                        width: 5px;
                        background: transparent;
                        margin: 4px 2px 4px 0px;
                    }}
                    QScrollBar::handle:vertical {{
                        background: {sb_handle};
                        min-height: 20px;
                        border-radius: 2px;
                    }}
                    QScrollBar::handle:vertical:hover {{
                        background: {sb_handle_hover};
                    }}
                    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                        height: 0px;
                    }}
                """)
            except (RuntimeError, Exception):
                pass

        valid_widgets = []
        for w in self.line_widgets:
            if not sip.isdeleted(w):
                try:
                    if hasattr(w, 'set_theme_palette'):
                        w.set_theme_palette(self.cover_palette)
                    valid_widgets.append(w)
                except (RuntimeError, Exception):
                    pass
        self.line_widgets = valid_widgets
        self._update_header_styles()

    def set_accent_color(self, hex_color: str) -> None:
        if hex_color:
            self.accent_color = hex_color
            clean_accent = hex_color.split(';')[0].strip()
            valid_widgets = []
            for w in self.line_widgets:
                if not sip.isdeleted(w):
                    try:
                        if hasattr(w, 'set_accent_color'):
                            w.set_accent_color(clean_accent)
                        valid_widgets.append(w)
                    except (RuntimeError, Exception):
                        pass
            self.line_widgets = valid_widgets
            self._update_header_styles()

    def set_font_family(self, font_family: str) -> None:
        if font_family:
            self.font_family = font_family
            if self.line_widgets:
                self._populate_lyrics_ui()

    def reload_lyrics(self) -> None:
        """Fuerza la recarga limpia de letras para la pista actual sin afectar el audio ni otros componentes."""
        if hasattr(self, 'current_meta') and self.current_meta:
            if hasattr(self, 'lbl_translation_status') and self.lbl_translation_status:
                self.lbl_translation_status.setText("🔄 Recargando letras...")
                self.lbl_translation_status.setVisible(True)
            self.load_lyrics_for_track(self.current_meta, force_reload=True)

    def load_lyrics_for_track(self, track_meta: dict, force_reload: bool = False) -> None:
        """Inicia la búsqueda offline y online de letras para la pista activa en segundo plano."""
        new_track_id = self._get_current_track_id(track_meta)
        if not force_reload and new_track_id and new_track_id == getattr(self, '_current_loaded_track_id', None):
            # Es exactamente la misma pista que ya está en memoria o en proceso: evitar parpadeo y re-fetch
            return

        self._current_loaded_track_id = new_track_id
        self.current_meta = dict(track_meta or {})
        self.original_lyrics_lines = []
        self.translated_lyrics_lines = []
        self.romaji_lyrics_lines = []
        self.lyrics_lines = []
        self.line_widgets = []
        self.active_index = -1
        self.is_synced = False
        self._is_manual_scrolling = False

        if hasattr(self, "scroll_animation") and self.scroll_animation.state() == QPropertyAnimation.State.Running:
            self.scroll_animation.stop()

        # Cancelar hilo previo si sigue activo
        if self.fetcher_thread is not None:
            try:
                if not sip.isdeleted(self.fetcher_thread) and self.fetcher_thread.isRunning():
                    try:
                        self.fetcher_thread.lyrics_loaded.disconnect()
                    except Exception:
                        pass
                    try:
                        self.fetcher_thread.lyrics_not_found.disconnect()
                    except Exception:
                        pass
                    self.fetcher_thread.quit()
                    self.fetcher_thread.wait(200)
            except Exception:
                pass
            self.fetcher_thread = None

        # Cancelar worker de traducción previo
        self._cleanup_translation_worker()

        file_path = self.current_meta.get("path") or self.current_meta.get("file_path", "")
        title = self.current_meta.get("title", "")

        if not file_path and not title:
            self._current_loaded_track_id = ""
            self._show_message("♪ Sin pista activa")
            return

        self._show_message("♪ Buscando letras...")

        self.fetcher_thread = LyricsFetcherThread(
            track_meta=self.current_meta,
            force_reload=force_reload,
            parent=self,
        )
        self.fetcher_thread.lyrics_loaded.connect(self._on_lyrics_loaded)
        self.fetcher_thread.lyrics_not_found.connect(self._on_lyrics_not_found)
        self.fetcher_thread.finished.connect(self._on_fetcher_finished)
        self.fetcher_thread.start()

    def _on_fetcher_finished(self) -> None:
        self.fetcher_thread = None

    def _on_lyrics_loaded(self, raw_text: str, parsed_lines: list, is_synced: bool) -> None:
        self.original_lyrics_lines = list(parsed_lines)
        self.lyrics_lines = list(parsed_lines)
        self.is_synced = is_synced

        # Precalcular Romaji (Hepburn) para todas las líneas originales (rápido y offline)
        self.romaji_lyrics_lines = [to_romaji(l.text) for l in self.original_lyrics_lines]

        # Inmediatamente poblar la interfaz para que la sincronización y lectura funcionen al instante
        self._populate_lyrics_ui()

        # Si el usuario tenía activada la traducción, iniciarla en segundo plano sin bloquear
        if self.is_showing_translation and self.original_lyrics_lines:
            self._start_translation(self.target_lang, self.translation_mode)

    def _on_lyrics_not_found(self) -> None:
        self._clear_layout()
        self._show_message("♪ Sin letras disponibles para esta pista")

    def _clear_layout(self) -> None:
        while self.lines_layout.count() > 0:
            item = self.lines_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.hide()
                widget.deleteLater()
        self.lbl_status = None
        self.line_widgets = []

    def _show_message(self, msg: str) -> None:
        self._clear_layout()
        lbl = QLabel(msg, self.scroll_content)
        self.lbl_status = lbl
        lbl.setFont(QFont("Sans Serif", 10, QFont.Weight.Medium))
        pal = getattr(self, 'cover_palette', {}) or {}
        status_col = pal.get("status_color", "rgba(255, 255, 255, 0.40)")
        lbl.setStyleSheet(f"color: {status_col}; background: transparent; border: none;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        eff = QGraphicsDropShadowEffect(lbl)
        eff.setBlurRadius(6)
        eff.setOffset(0, 1)
        eff.setColor(pal.get("shadow_color", QColor(0, 0, 0, 200)))
        lbl.setGraphicsEffect(eff)
        self.lines_layout.addWidget(lbl)

    def _populate_lyrics_ui(self) -> None:
        self._clear_layout()
        base_lines = self.original_lyrics_lines if self.original_lyrics_lines else self.lyrics_lines
        if not base_lines:
            self._show_message("♪ Sin letras disponibles")
            return

        # Espaciador superior generoso para permitir centrar la primera línea en el visor
        viewport_h = max(200, self.scroll_area.viewport().height())
        top_spacer_h = max(30, int(viewport_h * 0.35))
        self.lines_layout.addSpacing(top_spacer_h)

        has_translation = bool(
            self.is_showing_translation
            and self.translated_lyrics_lines
            and len(self.translated_lyrics_lines) == len(base_lines)
        )
        has_romaji = bool(
            self.romaji_lyrics_lines
            and len(self.romaji_lyrics_lines) == len(base_lines)
        )

        for idx, line in enumerate(base_lines):
            trans_text = self.translated_lyrics_lines[idx].text if has_translation else None
            rom_text = self.romaji_lyrics_lines[idx] if has_romaji else None
            line_w = LyricLineWidget(
                index=idx,
                line=line,
                translated_text=trans_text,
                romaji_text=rom_text,
                is_synced=self.is_synced,
                accent_color=self.accent_color,
                font_family=self.font_family,
                theme_palette=getattr(self, 'cover_palette', None),
                parent=self.scroll_content,
            )
            line_w.clicked.connect(self._on_line_clicked)
            self.lines_layout.addWidget(line_w)
            self.line_widgets.append(line_w)

        # Espaciador inferior generoso para permitir centrar la última línea
        self.lines_layout.addSpacing(top_spacer_h)

        # Reset estado activo y posición de scroll
        self.active_index = -1
        self.scroll_area.verticalScrollBar().setValue(0)
        if getattr(self, '_last_known_pos_ms', 0) > 0:
            QTimer.singleShot(30, lambda: self.update_position(self._last_known_pos_ms))

    def _on_line_clicked(self, time_ms: int) -> None:
        if time_ms >= 0:
            self.seek_requested.emit(time_ms)

    def update_position(self, pos_ms: int) -> None:
        """Actualiza la línea activa y centra la vista en función del tiempo actual de reproducción."""
        self._last_known_pos_ms = max(0, int(pos_ms))
        base_lines = self.original_lyrics_lines if self.original_lyrics_lines else self.lyrics_lines
        if not base_lines or not self.line_widgets:
            return

        if not self.is_synced:
            # Desplazamiento progresivo suave cuando son letras planas no sincronizadas
            duration_sec = self.current_meta.get("length_sec", 0) or self.current_meta.get("duration", 0)
            if duration_sec > 0 and not self._is_manual_scrolling:
                total_ms = duration_sec * 1000
                progress = min(1.0, max(0.0, pos_ms / total_ms))
                est_idx = min(len(self.line_widgets) - 1, int(progress * len(self.line_widgets)))
                if est_idx != self.active_index and est_idx >= 0:
                    if 0 <= self.active_index < len(self.line_widgets):
                        self.line_widgets[self.active_index].set_active(False)
                    self.active_index = est_idx
                    if 0 <= self.active_index < len(self.line_widgets):
                        target_w = self.line_widgets[self.active_index]
                        target_w.set_active(True, self.accent_color)
                        self._center_on_widget(target_w, smooth=True)
            return

        # Buscar la línea activa correspondiente al tiempo actual para letras sincronizadas
        new_active = -1
        for i, line in enumerate(base_lines):
            if 0 <= line.time_ms <= pos_ms:
                new_active = i
            elif line.time_ms > pos_ms:
                break

        if new_active != self.active_index:
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
            elif new_active == -1 and not self._is_manual_scrolling:
                self.scroll_area.verticalScrollBar().setValue(0)

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

    # ══════════════════════════════════════════════════════════════════════════
    # SISTEMA DE TRADUCCIÓN DE LETRAS
    # ══════════════════════════════════════════════════════════════════════════

    def _show_translation_menu(self) -> None:
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(20, 24, 38, 0.96);
                border: 1.5px solid rgba(255, 255, 255, 0.20);
                border-radius: 12px;
                padding: 6px;
                color: #ffffff;
            }
            QMenu::item {
                padding: 7px 16px;
                border-radius: 6px;
                font-size: 12px;
            }
            QMenu::item:selected {
                background-color: rgba(0, 229, 255, 0.25);
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 255, 255, 0.12);
                margin: 4px 8px;
            }
        """)

        # 1. Acción para alternar visualización de traducción
        act_toggle = menu.addAction(f"{'☑' if self.is_showing_translation else '☐'} Mostrar traducción")
        act_toggle.triggered.connect(lambda: self._toggle_translation(not self.is_showing_translation))

        menu.addSeparator()

        # 2. Submenú de Idioma Destino
        lang_menu = menu.addMenu(f"🌐 Idioma: {SUPPORTED_LANGUAGES.get(self.target_lang, self.target_lang.upper())}")
        lang_group = QActionGroup(self)
        for code, name in SUPPORTED_LANGUAGES.items():
            act_lang = lang_menu.addAction(f"{name} ({code})")
            act_lang.setCheckable(True)
            act_lang.setChecked(code == self.target_lang)
            act_lang.triggered.connect(lambda checked, c=code: self._set_target_language(c))
            lang_group.addAction(act_lang)

        # 3. Submenú de Modo de Traducción
        mode_names = {
            "auto": "Automático (Google + Letras.com + Offline)",
            "letras": "Letras.com (Humana / Web)",
            "online_only": "Solo Online (Google / Letras.com)",
            "offline_only": "Solo Offline (Argos)",
        }
        mode_menu = menu.addMenu(f"⚙️ Modo: {mode_names.get(self.translation_mode, 'Auto')}")
        mode_group = QActionGroup(self)
        for m_code, m_name in mode_names.items():
            act_mode = mode_menu.addAction(m_name)
            act_mode.setCheckable(True)
            act_mode.setChecked(m_code == self.translation_mode)
            act_mode.triggered.connect(lambda checked, m=m_code: self._set_translation_mode(m))
            mode_group.addAction(act_mode)

        pos = self.btn_translate.mapToGlobal(QPoint(0, self.btn_translate.height() + 4))
        menu.exec(pos)

    def _toggle_translation(self, enabled: bool) -> None:
        self.is_showing_translation = enabled
        if self.is_showing_translation:
            self.btn_translate.setText(f"🌐 {self.target_lang.upper()}")
            self._update_header_styles()
            if self.translated_lyrics_lines and len(self.translated_lyrics_lines) == len(self.original_lyrics_lines):
                self._populate_lyrics_ui()
            else:
                self._start_translation(self.target_lang, self.translation_mode)
        else:
            self._cleanup_translation_worker()
            self.lbl_translation_status.setVisible(False)
            self.btn_translate.setText("🌐 Traducir")
            self._update_header_styles()
            self._populate_lyrics_ui()

    def _set_target_language(self, lang_code: str) -> None:
        if self.target_lang != lang_code:
            self.target_lang = lang_code
            self.translated_lyrics_lines = []
            if self.is_showing_translation:
                self._start_translation(self.target_lang, self.translation_mode)

    def _set_translation_mode(self, mode: str) -> None:
        if self.translation_mode != mode:
            self.translation_mode = mode
            if self.is_showing_translation:
                self._start_translation(self.target_lang, self.translation_mode)

    def _cleanup_translation_worker(self) -> None:
        if self.download_progress_dialog:
            try:
                self.download_progress_dialog.canceled.disconnect()
            except Exception:
                pass
            try:
                self.download_progress_dialog.close()
            except Exception:
                pass
            self.download_progress_dialog = None

        if self.translation_worker is not None:
            worker = self.translation_worker
            self.translation_worker = None
            try:
                if not sip.isdeleted(worker):
                    if worker.isRunning():
                        worker.cancel()
                        try:
                            worker.translation_ready.disconnect()
                        except Exception:
                            pass
                        try:
                            worker.translation_error.disconnect()
                        except Exception:
                            pass
                        try:
                            worker.translation_progress.disconnect()
                        except Exception:
                            pass
                        self._retiring_workers.add(worker)
                        worker.quit()
                    else:
                        worker.deleteLater()
            except (RuntimeError, Exception):
                pass

    def _on_translation_worker_finished(self, worker: LyricsTranslationWorker) -> None:
        if self.translation_worker is worker:
            self.translation_worker = None
        self._retiring_workers.discard(worker)
        try:
            if not sip.isdeleted(worker):
                worker.deleteLater()
        except (RuntimeError, Exception):
            pass

    def _on_retiring_worker_finished(self, worker: LyricsTranslationWorker) -> None:
        self._on_translation_worker_finished(worker)

    def _get_current_track_id(self, meta: Optional[dict] = None) -> str:
        from database_manager import compute_canonical_track_id
        target = meta if meta is not None else getattr(self, 'current_meta', {})
        title = target.get("title", "")
        artist = target.get("artist", "")
        album = target.get("album", "")
        path = target.get("path") or target.get("file_path", "")
        return compute_canonical_track_id(artist, album, title, path)

    def _start_translation(self, target_lang: str, mode: str = "auto") -> None:
        if not self.original_lyrics_lines:
            return

        track_id = self._get_current_track_id()
        if not track_id:
            return

        self._cleanup_translation_worker()

        self.lbl_translation_status.setText("🌐 Traduciendo... ⏳")
        self.lbl_translation_status.setVisible(True)

        title = self.current_meta.get("title", "")
        artist = self.current_meta.get("artist", "")

        worker = LyricsTranslationWorker(
            track_id=track_id,
            lyrics_lines=self.original_lyrics_lines,
            target_lang=target_lang,
            mode=mode,
            title=title,
            artist=artist,
            parent=None,
        )
        self.translation_worker = worker
        worker.translation_ready.connect(self._on_translation_ready)
        worker.translation_error.connect(self._on_translation_error)
        worker.translation_progress.connect(self._on_translation_progress)
        worker.finished.connect(lambda w=worker: self._on_translation_worker_finished(w))
        worker.start()

    def _on_translation_ready(self, track_id: str, target_lang: str, translated_lines: list) -> None:
        if self.download_progress_dialog:
            self.download_progress_dialog.close()
            self.download_progress_dialog = None

        current_id = self._get_current_track_id()
        if current_id != track_id:
            return

        self.lbl_translation_status.setVisible(False)
        self.translated_lyrics_lines = list(translated_lines)
        if self.is_showing_translation:
            self._populate_lyrics_ui()

    def _on_translation_error(self, track_id: str, target_lang: str, error_msg: str) -> None:
        if self.download_progress_dialog:
            self.download_progress_dialog.close()
            self.download_progress_dialog = None

        current_id = self._get_current_track_id()
        if current_id != track_id:
            return

        self.lbl_translation_status.setText(f"⚠️ {error_msg}")
        self.lbl_translation_status.setVisible(True)
        QTimer.singleShot(5000, lambda: self.lbl_translation_status.setVisible(False))

    def _on_download_canceled(self) -> None:
        """Maneja la cancelación explícita por parte del usuario desde el QProgressDialog."""
        self._cleanup_translation_worker()
        self.lbl_translation_status.setText("⚠️ Descarga de modelo cancelada")
        self.lbl_translation_status.setVisible(True)
        QTimer.singleShot(3500, lambda: self.lbl_translation_status.setVisible(False))

    def _on_translation_progress(self, cur: int, tot: int, msg: str) -> None:
        self.lbl_translation_status.setText(f"📥 {msg} ({cur}%)" if tot > 0 else f"📥 {msg}")
        self.lbl_translation_status.setVisible(True)

        # Flujo de descarga automática (Opción A): Si se detecta descarga/instalación de modelo offline
        is_model_task = any(k in msg.lower() for k in ["descargando", "buscando", "instalando", "modelo", "paquete"])
        if is_model_task and cur < tot:
            if not self.download_progress_dialog:
                self.download_progress_dialog = QProgressDialog(
                    msg,
                    "Cancelar",
                    0,
                    tot if tot > 0 else 100,
                    self.window() if self.window() else self,
                )
                self.download_progress_dialog.setWindowTitle("Descarga de Idioma Offline")
                self.download_progress_dialog.setWindowModality(Qt.WindowModality.NonModal)
                self.download_progress_dialog.setMinimumDuration(0)
                self.download_progress_dialog.setAutoClose(True)
                self.download_progress_dialog.setAutoReset(True)
                self.download_progress_dialog.canceled.connect(self._on_download_canceled)
                self.download_progress_dialog.setStyleSheet("""
                    QProgressDialog {
                        background-color: #141826;
                        color: #ffffff;
                        border: 1.5px solid rgba(0, 229, 255, 0.4);
                        border-radius: 12px;
                        padding: 14px;
                    }
                    QLabel {
                        color: #ffffff;
                        font-size: 12px;
                        font-weight: bold;
                    }
                    QProgressBar {
                        background-color: rgba(255, 255, 255, 0.1);
                        border: 1px solid rgba(255, 255, 255, 0.2);
                        border-radius: 6px;
                        text-align: center;
                        color: #ffffff;
                        height: 20px;
                    }
                    QProgressBar::chunk {
                        background-color: #00e5ff;
                        border-radius: 5px;
                    }
                    QPushButton {
                        background-color: rgba(255, 23, 68, 0.2);
                        color: #ff1744;
                        border: 1px solid #ff1744;
                        border-radius: 6px;
                        padding: 5px 14px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: rgba(255, 23, 68, 0.4);
                        color: #ffffff;
                    }
                """)
                self.download_progress_dialog.show()

            self.download_progress_dialog.setLabelText(msg)
            self.download_progress_dialog.setValue(cur)
        elif cur >= tot and self.download_progress_dialog:
            self.download_progress_dialog.setValue(tot)
            self.download_progress_dialog.close()
            self.download_progress_dialog = None

    def cleanup(self) -> None:
        """Detiene y limpia de forma segura cualquier worker o hilo activo."""
        if hasattr(self, "scroll_animation"):
            try:
                if self.scroll_animation.state() == QPropertyAnimation.State.Running:
                    self.scroll_animation.stop()
            except Exception:
                pass
        if hasattr(self, "user_scroll_timer"):
            try:
                if self.user_scroll_timer.isActive():
                    self.user_scroll_timer.stop()
            except Exception:
                pass

        if self.fetcher_thread is not None:
            try:
                if not sip.isdeleted(self.fetcher_thread) and self.fetcher_thread.isRunning():
                    try:
                        self.fetcher_thread.lyrics_loaded.disconnect()
                    except Exception:
                        pass
                    try:
                        self.fetcher_thread.lyrics_not_found.disconnect()
                    except Exception:
                        pass
                    self.fetcher_thread.quit()
                    self.fetcher_thread.wait(200)
            except Exception:
                pass
            self.fetcher_thread = None

        self._cleanup_translation_worker()

    def closeEvent(self, event) -> None:
        self.cleanup()
        super().closeEvent(event)
