import sys
import os
import asyncio
from typing import Optional, Dict, Any, List
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer, QMetaObject, Qt, Q_ARG

# Intentar importar bindings de WinRT para Windows System Media Transport Controls (SMTC)
HAS_WINSDK = False
try:
    if sys.platform == "win32":
        import winsdk.windows.media as wmedia
        import winsdk.windows.storage as wstorage
        import winsdk.windows.storage.streams as wstreams
        HAS_WINSDK = True
except ImportError:
    HAS_WINSDK = False


class WindowsMediaServer(QObject):
    """Servidor / Publicador de System Media Transport Controls (SMTC) para Windows 10/11."""
    metadata_changed = pyqtSignal(dict)
    playback_status_changed = pyqtSignal(str)
    position_changed = pyqtSignal(int, int)  # (pos_sec, duration_sec)
    volume_changed = pyqtSignal(float)
    loop_status_changed = pyqtSignal(str)
    shuffle_status_changed = pyqtSignal(bool)

    def __init__(self, audio_engine: Any, window: Optional[QObject] = None, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.engine = audio_engine
        self.window = window
        self.smtc = None

        if HAS_WINSDK:
            self._init_smtc()

        # Suscribir notificaciones desde AudioEngine
        self.engine.playback_status_changed.connect(self._on_status_changed)
        self.engine.metadata_changed.connect(self._on_metadata_changed)
        self.engine.volume_changed.connect(self._on_volume_changed)

    def _init_smtc(self) -> None:
        try:
            import winsdk.windows.media as wmedia
            # Obtener el SMTC del proceso/ventana actual en Windows
            self.smtc = wmedia.SystemMediaTransportControls.get_for_current_view()
            self.smtc.is_play_enabled = True
            self.smtc.is_pause_enabled = True
            self.smtc.is_next_enabled = True
            self.smtc.is_previous_enabled = True
            self.smtc.is_enabled = True

            # Suscribir callback cuando el usuario presiona botones multimedia del SO en Windows
            self.smtc.add_button_pressed(self._on_button_pressed)
            print("[WindowsMediaServer] SMTC inicializado exitosamente.")
        except Exception as e:
            print(f"[WindowsMediaServer] Advertencia: Error inicializando SMTC en Windows: {e}")

    def _on_button_pressed(self, sender: Any, args: Any) -> None:
        """Callback invocado cuando el usuario presiona un botón multimedia en el widget de Windows 10/11."""
        try:
            import winsdk.windows.media as wmedia
            btn = args.button
            if btn == wmedia.SystemMediaTransportControlsButton.PLAY:
                QMetaObject.invokeMethod(self.engine, "play", Qt.ConnectionType.QueuedConnection)
            elif btn == wmedia.SystemMediaTransportControlsButton.PAUSE:
                QMetaObject.invokeMethod(self.engine, "pause", Qt.ConnectionType.QueuedConnection)
            elif btn == wmedia.SystemMediaTransportControlsButton.NEXT:
                QMetaObject.invokeMethod(self.engine, "next", Qt.ConnectionType.QueuedConnection)
            elif btn == wmedia.SystemMediaTransportControlsButton.PREVIOUS:
                QMetaObject.invokeMethod(self.engine, "previous", Qt.ConnectionType.QueuedConnection)
            elif btn == wmedia.SystemMediaTransportControlsButton.STOP:
                QMetaObject.invokeMethod(self.engine, "stop", Qt.ConnectionType.QueuedConnection)
        except Exception as e:
            print(f"[WindowsMediaServer] Error procesando botón presionado: {e}")

    def _on_status_changed(self, status: str) -> None:
        if not self.smtc:
            return
        try:
            import winsdk.windows.media as wmedia
            if status == "Playing":
                self.smtc.playback_status = wmedia.MediaPlaybackStatus.PLAYING
            elif status == "Paused":
                self.smtc.playback_status = wmedia.MediaPlaybackStatus.PAUSED
            else:
                self.smtc.playback_status = wmedia.MediaPlaybackStatus.STOPPED
        except Exception as e:
            print(f"[WindowsMediaServer] Error actualizando playback_status: {e}")

    def _on_metadata_changed(self, meta: dict) -> None:
        if not self.smtc:
            return
        try:
            import winsdk.windows.media as wmedia
            import winsdk.windows.storage as wstorage
            import winsdk.windows.storage.streams as wstreams

            updater = self.smtc.display_updater
            updater.type = wmedia.MediaPlaybackType.MUSIC
            updater.music_properties.title = meta.get("title", "Sin título")
            updater.music_properties.artist = meta.get("artist", "Artista desconocido")
            updater.music_properties.album_title = meta.get("album", "Álbum desconocido")

            art_url = meta.get("art_url", "")
            if art_url and art_url.startswith("file://"):
                local_path = art_url.replace("file://", "")
                if os.path.exists(local_path):

                    async def set_thumbnail():
                        try:
                            file = await wstorage.StorageFile.get_file_from_path_async(local_path)
                            updater.thumbnail = wstreams.RandomAccessStreamReference.create_from_file(file)
                            updater.update()
                        except Exception:
                            updater.update()

                    asyncio.run(set_thumbnail())
                    return

            updater.update()
        except Exception as e:
            print(f"[WindowsMediaServer] Error actualizando metadatos SMTC: {e}")

    def _on_volume_changed(self, volume: float) -> None:
        pass


# Alias para compatibilidad con código existente
WindowsMediaClient = WindowsMediaServer
