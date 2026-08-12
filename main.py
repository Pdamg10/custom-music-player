import os
import sys

# Silenciar notificaciones informativas de backend multimedia FFmpeg/Qt
os.environ["QT_LOGGING_RULES"] = "qt.multimedia*=false"

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
