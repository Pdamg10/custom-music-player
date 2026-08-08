import sys
from PyQt6.QtWidgets import QApplication

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

    # Restaurar posición guardada o por defecto
    saved_x = config.get("pos_x")
    saved_y = config.get("pos_y")

    if saved_x is not None and saved_y is not None:
        player_widget.move(saved_x, saved_y)
    else:
        screen_geometry = app.primaryScreen().availableGeometry()
        x = screen_geometry.width() - player_widget.width() - 40
        y = 60
        player_widget.move(x, y)

    player_widget.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
