import os
import sys

os.environ["VDPAU_LOG"] = "0"
os.environ["LIBVDPAU_LOG"] = "0"
os.environ["QT_LOGGING_RULES"] = "qt.gui.icc*=false;qt.gui.image*=false;qt.multimedia*=false;*.debug=false"
os.environ.setdefault("VDPAU_DRIVER", "none")
os.environ.setdefault("QT_QPA_PLATFORM", "xcb")

from PyQt6.QtCore import qInstallMessageHandler

def qt_message_handler(mode, context, message):
    if "fromIccProfile" in message or "VDPAU" in message or "libvdpau" in message:
        return
    sys.stderr.write(f"{message}\n")

qInstallMessageHandler(qt_message_handler)

from PyQt6.QtWidgets import QApplication

from config_manager import ConfigManager
from audio_engine import AudioEngine
from mpris_server import MPRISServer
from ui.player_widget import FloatingMusicPlayer

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Custom Floating Music Player")
    app.setOrganizationName("CustomTools")

    # Configuración y Persistencia
    config = ConfigManager()

    # Motor de Audio Nativo Local
    audio_engine = AudioEngine(config=config)

    # Ventana flotante
    player_widget = FloatingMusicPlayer(mpris_client=audio_engine, config=config)

    # Servidor de Medios según el Sistema Operativo (Linux MPRIS2 / Windows SMTC)
    if sys.platform == "win32":
        from win_media_client import WindowsMediaServer
        media_server = WindowsMediaServer(audio_engine=audio_engine, window=player_widget)
    else:
        media_server = MPRISServer(audio_engine=audio_engine, window=player_widget)

    # Limpieza al cerrar la aplicación
    app.aboutToQuit.connect(audio_engine.stop_scanner)

    if player_widget.view_mode == "expanded":
        player_widget.showMaximized()
    else:
        # Restaurar posición guardada o colocar en la parte inferior izquierda por defecto
        saved_x = config.get("pos_x")
        saved_y = config.get("pos_y")

        screen_geometry = app.primaryScreen().availableGeometry()
        default_x = screen_geometry.x() + 40
        default_y = screen_geometry.y() + screen_geometry.height() - player_widget.height() - 40

        if saved_x is not None and saved_y is not None and not (saved_x == 0 and saved_y == 0):
            player_widget.move(saved_x, saved_y)
        else:
            player_widget.move(default_x, default_y)

        player_widget.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
