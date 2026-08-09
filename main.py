import sys
from PyQt6.QtWidgets import QApplication

if sys.platform == "win32":
    from win_media_client import WindowsMediaClient as MPRISClient
else:
    from mpris_client import MPRISClient

from config_manager import ConfigManager
from ui.player_widget import FloatingMusicPlayer

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Custom Floating Music Player")
    app.setOrganizationName("CustomTools")

    # Configuración y Persistencia
    config = ConfigManager()

    # Cliente DBus MPRIS
    mpris_client = MPRISClient()

    # Ventana flotante
    player_widget = FloatingMusicPlayer(mpris_client=mpris_client, config=config)

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
