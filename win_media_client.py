import sys
import os
import asyncio
from typing import Optional, Dict, Any, List
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer

class WindowsMediaClient(QObject):
    """Cliente de medios para Windows 10/11 utilizando Windows System Media Transport Controls (SMTC / WinRT)."""
    metadata_changed = pyqtSignal(dict)
    playback_status_changed = pyqtSignal(str)
    position_changed = pyqtSignal(int, int)  # (pos_sec, duration_sec)
    volume_changed = pyqtSignal(float)
    loop_status_changed = pyqtSignal(str)
    shuffle_status_changed = pyqtSignal(bool)
    player_available = pyqtSignal(bool, str)
    players_list_changed = pyqtSignal(list)
    bus_connection_changed = pyqtSignal(bool)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.active_service: Optional[str] = "Windows Media Controls"
        self.current_metadata: Dict[str, Any] = {}
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)

        self.refresh()

    def get_available_services(self) -> List[str]:
        return ["Windows Media Transport Controls"]

    def scan_services(self) -> None:
        self.refresh()

    def set_active_service(self, service_name: Optional[str]) -> None:
        self.active_service = service_name
        self.refresh()

    def refresh(self) -> None:
        try:
            import winsdk.windows.media.control as wmc

            async def get_media_info():
                manager = await wmc.GlobalSystemMediaTransportControlsSessionManager.request_async()
                session = manager.get_current_session()
                if session:
                    info = await session.try_get_media_properties_async()
                    status_info = session.get_playback_info()
                    timeline = session.get_timeline_properties()

                    status_str = "Playing" if status_info and status_info.playback_status == 4 else "Paused"
                    app_id = session.source_app_user_model_id or "Windows Media"
                    clean_app = app_id.split("!")[-1].split(".")[0].capitalize()

                    title = info.title if info else "Sin título"
                    artist = info.artist if info else "Artista desconocido"
                    album = info.album_title if info else ""

                    length_sec = 0
                    pos_sec = 0
                    if timeline:
                        length_sec = int(timeline.end_time.total_seconds()) if timeline.end_time else 0
                        pos_sec = int(timeline.position.total_seconds()) if timeline.position else 0

                    meta = {
                        "title": title,
                        "artist": artist,
                        "album": album,
                        "art_url": "",
                        "length_sec": length_sec,
                        "track_id": ""
                    }

                    self.current_metadata = meta
                    self.player_available.emit(True, clean_app)
                    self.metadata_changed.emit(meta)
                    self.playback_status_changed.emit(status_str)
                    self.position_changed.emit(pos_sec, length_sec)
                else:
                    self.player_available.emit(True, "Windows Media")
                    self.playback_status_changed.emit("Stopped")

            asyncio.run(get_media_info())
        except Exception:
            # Fallback elegante si winsdk no está disponible en la máquina de Windows
            self.player_available.emit(True, "Windows Media")

    def play_pause(self) -> None:
        try:
            import winsdk.windows.media.control as wmc

            async def do_toggle():
                manager = await wmc.GlobalSystemMediaTransportControlsSessionManager.request_async()
                session = manager.get_current_session()
                if session:
                    await session.try_toggle_play_pause_async()

            asyncio.run(do_toggle())
        except Exception as e:
            print(f"[WindowsMediaClient] Error enviando PlayPause: {e}")

    def previous(self) -> None:
        try:
            import winsdk.windows.media.control as wmc

            async def do_prev():
                manager = await wmc.GlobalSystemMediaTransportControlsSessionManager.request_async()
                session = manager.get_current_session()
                if session:
                    await session.try_skip_previous_async()

            asyncio.run(do_prev())
        except Exception as e:
            print(f"[WindowsMediaClient] Error enviando Previous: {e}")

    def next(self) -> None:
        try:
            import winsdk.windows.media.control as wmc

            async def do_next():
                manager = await wmc.GlobalSystemMediaTransportControlsSessionManager.request_async()
                session = manager.get_current_session()
                if session:
                    await session.try_skip_next_async()

            asyncio.run(do_next())
        except Exception as e:
            print(f"[WindowsMediaClient] Error enviando Next: {e}")

    def set_position(self, target_sec: int) -> None:
        pass

    def set_volume(self, volume: float) -> None:
        pass

    def cycle_loop_status(self) -> None:
        pass

    def toggle_shuffle(self) -> None:
        pass
