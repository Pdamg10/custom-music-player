import sys
import os
import asyncio
import threading
from typing import Optional, Dict, Any
from PyQt6.QtCore import QMetaObject, Qt, Q_ARG

try:
    from dbus_next.service import ServiceInterface, method, dbus_property, signal, PropertyAccess
    from dbus_next.aio import MessageBus
    from dbus_next.constants import BusType
    from dbus_next import Variant
    HAS_DBUS_NEXT = True
except ImportError:
    HAS_DBUS_NEXT = False


if HAS_DBUS_NEXT:
    class MPRIS2RootInterface(ServiceInterface):
        """Interfaz org.mpris.MediaPlayer2."""
        def __init__(self, window: Optional[Any] = None):
            super().__init__('org.mpris.MediaPlayer2')
            self.window = window

        @method()
        def Raise(self):
            if self.window:
                QMetaObject.invokeMethod(self.window, "show", Qt.ConnectionType.QueuedConnection)
                QMetaObject.invokeMethod(self.window, "raise_", Qt.ConnectionType.QueuedConnection)
                QMetaObject.invokeMethod(self.window, "activateWindow", Qt.ConnectionType.QueuedConnection)

        @method()
        def Quit(self):
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                QMetaObject.invokeMethod(app, "quit", Qt.ConnectionType.QueuedConnection)

        @dbus_property(access=PropertyAccess.READ)
        def CanSetFullscreen(self) -> 'b':
            return False

        @dbus_property(access=PropertyAccess.READWRITE)
        def Fullscreen(self) -> 'b':
            return False

        @Fullscreen.setter
        def Fullscreen(self, val: 'b'):
            pass

        @dbus_property(access=PropertyAccess.READ)
        def CanQuit(self) -> 'b':
            return True

        @dbus_property(access=PropertyAccess.READ)
        def CanRaise(self) -> 'b':
            return True

        @dbus_property(access=PropertyAccess.READ)
        def HasTrackList(self) -> 'b':
            return False

        @dbus_property(access=PropertyAccess.READ)
        def Identity(self) -> 's':
            return 'Custom Music Player'

        @dbus_property(access=PropertyAccess.READ)
        def DesktopEntry(self) -> 's':
            return 'custom-music-player'

        @dbus_property(access=PropertyAccess.READ)
        def SupportedUriSchemes(self) -> 'as':
            return ['file']

        @dbus_property(access=PropertyAccess.READ)
        def SupportedMimeTypes(self) -> 'as':
            return ['audio/mpeg', 'audio/x-flac', 'audio/wav', 'audio/mp4', 'audio/ogg', 'audio/opus', 'audio/aac']


    class MPRIS2PlayerInterface(ServiceInterface):
        """Interfaz org.mpris.MediaPlayer2.Player."""
        def __init__(self, audio_engine: Any, loop: Optional[asyncio.AbstractEventLoop] = None):
            super().__init__('org.mpris.MediaPlayer2.Player')
            self.engine = audio_engine
            self.loop = loop

            # Conectar notificaciones de AudioEngine
            self.engine.playback_status_changed.connect(self._on_status_changed)
            self.engine.metadata_changed.connect(self._on_metadata_changed)
            self.engine.volume_changed.connect(self._on_volume_changed)
            self.engine.loop_status_changed.connect(self._on_loop_changed)
            self.engine.shuffle_status_changed.connect(self._on_shuffle_changed)

        @signal()
        def Seeked(self, position_us: 'x') -> 'x':
            return position_us

        @method()
        def Next(self):
            QMetaObject.invokeMethod(self.engine, "next", Qt.ConnectionType.QueuedConnection)

        @method()
        def Previous(self):
            QMetaObject.invokeMethod(self.engine, "previous", Qt.ConnectionType.QueuedConnection)

        @method()
        def Pause(self):
            QMetaObject.invokeMethod(self.engine, "pause", Qt.ConnectionType.QueuedConnection)

        @method()
        def PlayPause(self):
            QMetaObject.invokeMethod(self.engine, "play_pause", Qt.ConnectionType.QueuedConnection)

        @method()
        def Stop(self):
            QMetaObject.invokeMethod(self.engine, "stop", Qt.ConnectionType.QueuedConnection)

        @method()
        def Play(self):
            QMetaObject.invokeMethod(self.engine, "play", Qt.ConnectionType.QueuedConnection)

        @method()
        def Seek(self, offset_us: 'x'):
            pos_sec = max(0, (self.engine.player.position() + (offset_us // 1000)) // 1000)
            QMetaObject.invokeMethod(self.engine, "set_position", Qt.ConnectionType.QueuedConnection, Q_ARG(int, pos_sec))
            self.Seeked(int(self.engine.player.position() * 1000))

        @method()
        def SetPosition(self, track_id: 'o', position_us: 'x'):
            pos_sec = max(0, position_us // 1000000)
            QMetaObject.invokeMethod(self.engine, "set_position", Qt.ConnectionType.QueuedConnection, Q_ARG(int, pos_sec))
            self.Seeked(int(position_us))

        @method()
        def OpenUri(self, uri: 's'):
            pass

        @dbus_property(access=PropertyAccess.READ)
        def PlaybackStatus(self) -> 's':
            from PyQt6.QtMultimedia import QMediaPlayer
            state = self.engine.player.playbackState()
            if state == QMediaPlayer.PlaybackState.PlayingState:
                return 'Playing'
            elif state == QMediaPlayer.PlaybackState.PausedState:
                return 'Paused'
            return 'Stopped'

        @dbus_property(access=PropertyAccess.READWRITE)
        def LoopStatus(self) -> 's':
            return getattr(self.engine, 'loop_status', 'None')

        @LoopStatus.setter
        def LoopStatus(self, val: 's'):
            if val != getattr(self.engine, 'loop_status', 'None'):
                QMetaObject.invokeMethod(self.engine, "cycle_loop_status", Qt.ConnectionType.QueuedConnection)

        @dbus_property(access=PropertyAccess.READWRITE)
        def Rate(self) -> 'd':
            return 1.0

        @Rate.setter
        def Rate(self, val: 'd'):
            pass

        @dbus_property(access=PropertyAccess.READWRITE)
        def Shuffle(self) -> 'b':
            return getattr(self.engine, 'is_shuffle', False)

        @Shuffle.setter
        def Shuffle(self, val: 'b'):
            if val != getattr(self.engine, 'is_shuffle', False):
                QMetaObject.invokeMethod(self.engine, "toggle_shuffle", Qt.ConnectionType.QueuedConnection)

        @dbus_property(access=PropertyAccess.READ)
        def Metadata(self) -> 'a{sv}':
            m = self.engine.current_metadata or {}
            length_sec = m.get('length_sec', 0)
            track_id = m.get('track_id', '0')
            art_url = m.get('art_url', '')

            res = {
                'mpris:trackid': Variant('o', f'/org/mpris/MediaPlayer2/TrackList/{track_id}'),
                'mpris:length': Variant('x', int(length_sec * 1_000_000)),
                'xesam:title': Variant('s', m.get('title', 'Sin reproducción')),
                'xesam:artist': Variant('as', [m.get('artist', 'Artista desconocido')]),
                'xesam:album': Variant('s', m.get('album', 'Álbum desconocido'))
            }
            if art_url:
                res['mpris:artUrl'] = Variant('s', art_url)
            return res

        @dbus_property(access=PropertyAccess.READWRITE)
        def Volume(self) -> 'd':
            try:
                return float(self.engine.audio_output.volume())
            except Exception:
                return 1.0

        @Volume.setter
        def Volume(self, val: 'd'):
            QMetaObject.invokeMethod(self.engine, "set_volume", Qt.ConnectionType.QueuedConnection, Q_ARG(float, val))

        @dbus_property(access=PropertyAccess.READ)
        def Position(self) -> 'x':
            try:
                return int(self.engine.player.position() * 1000)
            except Exception:
                return 0

        @dbus_property(access=PropertyAccess.READ)
        def MinimumRate(self) -> 'd':
            return 1.0

        @dbus_property(access=PropertyAccess.READ)
        def MaximumRate(self) -> 'd':
            return 1.0

        @dbus_property(access=PropertyAccess.READ)
        def CanGoNext(self) -> 'b':
            return True

        @dbus_property(access=PropertyAccess.READ)
        def CanGoPrevious(self) -> 'b':
            return True

        @dbus_property(access=PropertyAccess.READ)
        def CanPlay(self) -> 'b':
            return True

        @dbus_property(access=PropertyAccess.READ)
        def CanPause(self) -> 'b':
            return True

        @dbus_property(access=PropertyAccess.READ)
        def CanSeek(self) -> 'b':
            return True

        @dbus_property(access=PropertyAccess.READ)
        def CanControl(self) -> 'b':
            return True

        def _safe_emit(self, changed_props: Dict[str, Any]):
            if self.loop and self.loop.is_running():
                try:
                    self.loop.call_soon_threadsafe(self.emit_properties_changed, changed_props)
                except Exception:
                    pass
            else:
                try:
                    self.emit_properties_changed(changed_props)
                except Exception:
                    pass

        def _on_status_changed(self, status: str):
            self._safe_emit({'PlaybackStatus': status})

        def _on_metadata_changed(self, meta: dict):
            self._safe_emit({'Metadata': self.Metadata})

        def _on_volume_changed(self, vol: float):
            self._safe_emit({'Volume': vol})

        def _on_loop_changed(self, loop: str):
            self._safe_emit({'LoopStatus': loop})

        def _on_shuffle_changed(self, shuf: bool):
            self._safe_emit({'Shuffle': shuf})


class MPRISServer:
    """Servidor DBus MPRIS2 multiplataforma para CustomMusicPlayer."""
    def __init__(self, audio_engine: Any, window: Optional[Any] = None) -> None:
        self.engine = audio_engine
        self.window = window
        self.service_registered = False
        self._loop = None
        self._thread = None

        if sys.platform != "win32" and HAS_DBUS_NEXT:
            self._start_dbus_server()

    def _start_dbus_server(self) -> None:
        def _run_server():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

            async def _init_bus():
                try:
                    bus = await MessageBus(bus_type=BusType.SESSION).connect()
                    root_iface = MPRIS2RootInterface(self.window)
                    player_iface = MPRIS2PlayerInterface(self.engine, loop=self._loop)
                    bus.export('/org/mpris/MediaPlayer2', root_iface)
                    bus.export('/org/mpris/MediaPlayer2', player_iface)
                    await bus.request_name('org.mpris.MediaPlayer2.CustomMusicPlayer')
                    self.service_registered = True
                    print("[MPRISServer] Servidor DBus MPRIS2 registrado exitosamente como 'org.mpris.MediaPlayer2.CustomMusicPlayer'")
                except Exception as e:
                    print(f"[MPRISServer] Error registrando servidor DBus: {e}")

            self._loop.run_until_complete(_init_bus())
            self._loop.run_forever()

        self._thread = threading.Thread(target=_run_server, daemon=True)
        self._thread.start()


# Alias para compatibilidad
MPRISClient = MPRISServer
