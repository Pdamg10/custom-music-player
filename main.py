import os
import sys

os.environ["VDPAU_LOG"] = "0"
os.environ["LIBVDPAU_LOG"] = "0"
os.environ["VDPAU_DRIVER"] = "none"
os.environ["LIBVDPAU_DRIVER"] = "none"
os.environ["QT_FFMPEG_DECODING_HW_DEVICE_TYPES"] = ""
os.environ["QT_FFMPEG_ENCODING_HW_DEVICE_TYPES"] = ""
os.environ["QT_LOGGING_RULES"] = "qt.gui.icc*=false;qt.gui.image*=false;qt.multimedia*=false;*.debug=false"
os.environ.setdefault("QT_QPA_PLATFORM", "xcb")

# Silenciar advertencias de bajo nivel de FFmpeg (demuxers de FLAC/MP3 con metadatos de carátula no estándar)
try:
    import ctypes
    import ctypes.util
    _av_lib = ctypes.util.find_library('avutil') or 'libavutil.so'
    if _av_lib:
        _avutil = ctypes.CDLL(_av_lib)
        if hasattr(_avutil, 'av_log_set_level'):
            _avutil.av_log_set_level(16)  # AV_LOG_ERROR
except Exception:
    pass

from PyQt6.QtCore import qInstallMessageHandler

def qt_message_handler(mode, context, message):
    if any(k in message for k in ("fromIccProfile", "VDPAU", "libvdpau", "QFFmpeg", "wildcard call disconnects", "Failed to open VDPAU", "qt.multimedia", "Could not read mimetype", "Could not open media")):
        return
    sys.stderr.write(f"{message}\n")

qInstallMessageHandler(qt_message_handler)

import traceback

def global_exception_handler(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    sys.stderr.write("".join(traceback.format_exception(exc_type, exc_value, exc_traceback)))

sys.excepthook = global_exception_handler

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from config_manager import get_config_manager
from audio_engine import AudioEngine
from ui.player_widget import FloatingMusicPlayer
from ui.unified_mode_menu import install as install_unified_mode_menu
from ui.styles import NORMAL_HEIGHT, COMPACT_HEIGHT

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Custom Floating Music Player")
    app.setOrganizationName("CustomTools")

    # Configurar icono de la aplicación (PC / Desktop)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    icon_png = os.path.join(base_dir, "assets", "icon.png")
    app_icon = None
    if os.path.exists(icon_png):
        app_icon = QIcon(icon_png)
        app.setWindowIcon(app_icon)

    # Configuración y Persistencia
    config = get_config_manager()

    # Motor de Audio Nativo Local
    audio_engine = AudioEngine(config=config)

    # Ventana flotante
    player_widget = FloatingMusicPlayer(audio_engine=audio_engine, config=config)
    if app_icon is not None:
        player_widget.setWindowIcon(app_icon)
    install_unified_mode_menu(player_widget)

    # Servidor de Medios según el Sistema Operativo (Linux MPRIS2 / Windows SMTC)
    if sys.platform == "win32":
        from win_media_client import WindowsMediaServer
        media_server = WindowsMediaServer(audio_engine=audio_engine, window=player_widget)
    else:
        from mpris_server import MPRISServer
        media_server = MPRISServer(audio_engine=audio_engine, window=player_widget)

    # Limpieza al cerrar la aplicación
    def _cleanup():
        if hasattr(media_server, "shutdown"):
            try:
                media_server.shutdown()
            except Exception:
                pass
        audio_engine.shutdown()

    app.aboutToQuit.connect(_cleanup)

    if player_widget.view_mode == "expanded":
        player_widget.showMaximized()
    else:
        # Restaurar posición guardada o colocar en la parte inferior izquierda por defecto
        mode = player_widget.view_mode
        prefix = "compact" if mode == "compact" else "normal"
        user_moved = bool(config.get(f"{prefix}_user_moved", False))
        saved_x = config.get(f"{prefix}_pos_x") if user_moved else None
        saved_y = config.get(f"{prefix}_pos_y") if user_moved else None

        screen_geometry = app.primaryScreen().availableGeometry()
        h = COMPACT_HEIGHT if mode == "compact" else NORMAL_HEIGHT
        default_x = screen_geometry.x() + 40
        default_y = screen_geometry.y() + screen_geometry.height() - h - 40

        if saved_x is not None and saved_y is not None and not (saved_x == 0 and saved_y == 0):
            player_widget.move(saved_x, saved_y)
        else:
            player_widget.move(default_x, default_y)

        player_widget.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
