import os
from typing import Optional, Dict, Any

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush, QPen, QGuiApplication
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QProgressBar, QFrame, QWidget, QGraphicsDropShadowEffect,
    QFileDialog
)

from online_stream_manager import (
    is_supported_media_url, detect_url_provider, LinkResolverWorker
)


class AddLinkDialog(QDialog):
    """Diálogo modal para agregar y reproducir música desde enlaces de YouTube y Spotify (Online / Offline)."""

    track_resolved = pyqtSignal(dict, bool)  # (track_meta, play_now)

    def __init__(
        self,
        download_dir: str = "",
        accent_color: str = "#ff1744",
        font_family: str = "Sans Serif",
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.download_dir = download_dir or os.path.expanduser("~/Música")
        self.accent_color = accent_color if accent_color else "#ff1744"
        self.font_family = font_family or "Sans Serif"
        self.worker: Optional[LinkResolverWorker] = None

        self.setWindowTitle("🔗 Agregar Música desde YouTube o Spotify")
        self.setFixedSize(560, 340)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._drag_pos = None
        self._init_ui()
        self._check_clipboard_for_url()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        # Contenedor Principal Glassmorphism
        self.container = QFrame(self)
        self.container.setObjectName("LinkDialogContainer")
        self.container.setStyleSheet(f"""
            QFrame#LinkDialogContainer {{
                background-color: #0f111a;
                border-radius: 20px;
                border: 1.5px solid rgba(255, 255, 255, 0.14);
            }}
        """)

        # Sombra exterior
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 8)
        self.container.setGraphicsEffect(shadow)

        c_layout = QVBoxLayout(self.container)
        c_layout.setContentsMargins(24, 20, 24, 20)
        c_layout.setSpacing(14)

        # 1. Cabecera con Título y Botón de Cierre
        header_layout = QHBoxLayout()
        lbl_title = QLabel("🔗 AGREGAR MÚSICA DESDE LINK", self.container)
        lbl_title.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {self.accent_color}; border: none;")

        btn_close = QPushButton("✕", self.container)
        btn_close.setFixedSize(28, 28)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #8a8fa8;
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-radius: 14px;
            }
            QPushButton:hover {
                background-color: rgba(255, 23, 68, 0.25);
                color: #ff1744;
            }
        """)
        btn_close.clicked.connect(self.reject)

        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(btn_close)
        c_layout.addLayout(header_layout)

        # 2. Subtítulo explicativo
        lbl_subtitle = QLabel(
            "Pega un enlace de YouTube (video/canción) o Spotify (track/canción) para transmitir online o descargar:",
            self.container
        )
        lbl_subtitle.setFont(QFont(self.font_family, 9))
        lbl_subtitle.setWordWrap(True)
        lbl_subtitle.setStyleSheet("color: #a2a8c2; border: none;")
        c_layout.addWidget(lbl_subtitle)

        # 3. Campo de Entrada URL
        input_box = QHBoxLayout()
        self.edit_url = QLineEdit(self.container)
        self.edit_url.setPlaceholderText("https://www.youtube.com/watch?v=... o https://open.spotify.com/track/...")
        self.edit_url.setFont(QFont(self.font_family, 10))
        self.edit_url.setStyleSheet("""
            QLineEdit {
                background-color: #171a29;
                color: #ffffff;
                border: 1.5px solid rgba(255, 255, 255, 0.15);
                border-radius: 12px;
                padding: 10px 14px;
                selection-background-color: rgba(255, 255, 255, 0.25);
            }
            QLineEdit:focus {
                border: 1.5px solid #00e5ff;
                background-color: #1b1f32;
            }
        """)
        self.edit_url.textChanged.connect(self._on_url_text_changed)

        btn_paste = QPushButton("📋 Pegar", self.container)
        btn_paste.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_paste.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_paste.setFixedHeight(38)
        btn_paste.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 10px;
                padding: 0 14px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.18);
            }
        """)
        btn_paste.clicked.connect(self._paste_from_clipboard)

        input_box.addWidget(self.edit_url, stretch=1)
        input_box.addWidget(btn_paste)
        c_layout.addLayout(input_box)

        # 4. Estado y Barra de Progreso
        self.lbl_status = QLabel("", self.container)
        self.lbl_status.setFont(QFont(self.font_family, 9))
        self.lbl_status.setStyleSheet("color: #00e5ff; border: none;")
        c_layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar(self.container)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #1b1f32;
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {self.accent_color};
                border-radius: 3px;
            }}
        """)
        self.progress_bar.hide()
        c_layout.addWidget(self.progress_bar)

        # 5. Carpeta de Destino para Descargas
        folder_row = QHBoxLayout()
        folder_row.setContentsMargins(4, 0, 4, 0)
        folder_row.setSpacing(8)

        lbl_folder_icon = QLabel("📁", self.container)
        lbl_folder_icon.setStyleSheet("border: none; background: transparent;")
        
        display_dir = self.download_dir
        if len(display_dir) > 42:
            display_dir = "..." + display_dir[-39:]
        self.lbl_folder_path = QLabel(f"Guardar en: {display_dir}", self.container)
        self.lbl_folder_path.setFont(QFont(self.font_family, 8))
        self.lbl_folder_path.setStyleSheet("color: rgba(255, 255, 255, 0.60); border: none;")
        self.lbl_folder_path.setToolTip(self.download_dir)

        btn_change_folder = QPushButton("Cambiar", self.container)
        btn_change_folder.setFont(QFont(self.font_family, 8))
        btn_change_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_change_folder.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: rgba(255, 255, 255, 0.85);
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 6px;
                padding: 3px 8px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.18);
                color: #ffffff;
            }
        """)
        btn_change_folder.clicked.connect(self._choose_custom_download_dir)

        folder_row.addWidget(lbl_folder_icon)
        folder_row.addWidget(self.lbl_folder_path, stretch=1)
        folder_row.addWidget(btn_change_folder)
        c_layout.addLayout(folder_row)

        # 6. Botones de Acción (Online Streaming vs Descarga Offline)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self.btn_stream = QPushButton("⚡ Reproducir Online Ahora", self.container)
        self.btn_stream.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.btn_stream.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stream.setFixedHeight(42)
        self.btn_stream.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.accent_color};
                color: #ffffff;
                border: none;
                border-radius: 12px;
                padding: 0 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #ffffff;
                color: #000000;
            }}
            QPushButton:disabled {{
                background-color: rgba(255, 255, 255, 0.08);
                color: #555870;
            }}
        """)
        self.btn_stream.clicked.connect(lambda: self._start_processing(mode="stream"))

        self.btn_download = QPushButton("📥 Descargar Offline", self.container)
        self.btn_download.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.btn_download.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_download.setFixedHeight(42)
        self.btn_download.setStyleSheet("""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.08);
                color: #ffffff;
                border: 1.5px solid rgba(255, 255, 255, 0.20);
                border-radius: 12px;
                padding: 0 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 229, 255, 0.20);
                border-color: #00e5ff;
                color: #00e5ff;
            }}
            QPushButton:disabled {{
                background-color: rgba(255, 255, 255, 0.04);
                border-color: rgba(255, 255, 255, 0.08);
                color: #555870;
            }}
        """)
        self.btn_download.clicked.connect(lambda: self._start_processing(mode="download"))

        btn_row.addWidget(self.btn_stream, stretch=1)
        btn_row.addWidget(self.btn_download, stretch=1)
        c_layout.addLayout(btn_row)

        layout.addWidget(self.container)

    def _choose_custom_download_dir(self) -> None:
        """Permite al usuario cambiar o confirmar la carpeta destino de descargas."""
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta para Descargas", self.download_dir)
        if folder:
            self.download_dir = folder
            display_dir = self.download_dir
            if len(display_dir) > 42:
                display_dir = "..." + display_dir[-39:]
            self.lbl_folder_path.setText(f"Guardar en: {display_dir}")
            self.lbl_folder_path.setToolTip(self.download_dir)

    def _check_clipboard_for_url(self) -> None:
        """Autodetecta si el portapapeles contiene un enlace compatible al abrir el diálogo."""
        clipboard = QGuiApplication.clipboard()
        if clipboard:
            text = clipboard.text().strip()
            if is_supported_media_url(text):
                self.edit_url.setText(text)
                self.lbl_status.setText(f"✓ Enlace detectado: {detect_url_provider(text).upper()}")

    def _paste_from_clipboard(self) -> None:
        clipboard = QGuiApplication.clipboard()
        if clipboard:
            text = clipboard.text().strip()
            self.edit_url.setText(text)

    def _on_url_text_changed(self, text: str) -> None:
        text = text.strip()
        if not text:
            self.lbl_status.setText("")
            return
        if is_supported_media_url(text):
            prov = detect_url_provider(text).upper()
            self.lbl_status.setStyleSheet("color: #00e676; border: none;")
            self.lbl_status.setText(f"✓ Enlace válido de {prov}")
        else:
            self.lbl_status.setStyleSheet("color: #ff9100; border: none;")
            self.lbl_status.setText("ℹ️ Ingrese un enlace válido de YouTube o Spotify")

    def _start_processing(self, mode: str = "stream") -> None:
        url = self.edit_url.text().strip()
        if not url:
            self.lbl_status.setStyleSheet("color: #ff1744; border: none;")
            self.lbl_status.setText("⚠️ Debe ingresar un enlace.")
            return

        self.btn_stream.setEnabled(False)
        self.btn_download.setEnabled(False)
        self.edit_url.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.show()

        self.worker = LinkResolverWorker(url, mode=mode, download_dir=self.download_dir, parent=self)
        self.worker.status_updated.connect(self._on_worker_status)
        self.worker.progress_updated.connect(self._on_worker_progress)
        self.worker.stream_ready.connect(self._on_stream_ready)
        self.worker.download_finished.connect(self._on_download_finished)
        self.worker.failed.connect(self._on_worker_failed)
        self.worker.start()

    def _on_worker_status(self, message: str) -> None:
        self.lbl_status.setStyleSheet("color: #00e5ff; border: none;")
        self.lbl_status.setText(message)

    def _on_worker_progress(self, frac: float) -> None:
        self.progress_bar.setValue(int(max(0.0, min(1.0, frac)) * 100))

    def _on_stream_ready(self, track_meta: dict) -> None:
        self.lbl_status.setStyleSheet("color: #00e676; border: none;")
        self.lbl_status.setText(f"✓ Reproduciendo: {track_meta.get('title', 'Audio')}")
        self.track_resolved.emit(track_meta, True)
        if self.worker and self.worker.isRunning():
            self.worker.wait(300)
        QTimer.singleShot(300, self.accept)

    def _on_download_finished(self, track_meta: dict) -> None:
        self.lbl_status.setStyleSheet("color: #00e676; border: none;")
        self.lbl_status.setText(f"✓ Guardado: {track_meta.get('title', 'Descarga')}")
        self.track_resolved.emit(track_meta, False)
        if self.worker and self.worker.isRunning():
            self.worker.wait(300)
        QTimer.singleShot(500, self.accept)

    def _on_worker_failed(self, err_msg: str) -> None:
        self.progress_bar.hide()
        self.btn_stream.setEnabled(True)
        self.btn_download.setEnabled(True)
        self.edit_url.setEnabled(True)
        self.lbl_status.setStyleSheet("color: #ff1744; border: none;")
        self.lbl_status.setText(f"✕ Error: {err_msg[:65]}...")

    def closeEvent(self, event) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption()
            self.worker.quit()
            self.worker.wait(300)
        super().closeEvent(event)

    def reject(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption()
            self.worker.quit()
            self.worker.wait(300)
        super().reject()

    # Permitir arrastrar la ventana sin marco
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
