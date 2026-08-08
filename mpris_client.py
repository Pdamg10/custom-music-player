import urllib.parse
from typing import Optional, Dict, Any, List, Tuple
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer, QVariant
from PyQt6.QtDBus import QDBusConnection, QDBusInterface, QDBusMessage, QDBusObjectPath

class MPRISClient(QObject):
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
        self.bus: QDBusConnection = QDBusConnection.sessionBus()
        self.active_service: Optional[str] = None
        self.player_iface: Optional[QDBusInterface] = None
        self.props_iface: Optional[QDBusInterface] = None
        self.current_metadata: Dict[str, Any] = {}

        self._setup_dbus_listeners()

        # Timer para consultar la posición actual cada 500 ms si está reproduciendo
        self.position_timer: QTimer = QTimer(self)
        self.position_timer.timeout.connect(self._poll_position)
        self.position_timer.start(500)

        # Heartbeat timer de respaldo y verificación de salud de la conexión DBus
        self.heartbeat_timer: QTimer = QTimer(self)
        self.heartbeat_timer.timeout.connect(self._health_check_and_refresh)
        self.heartbeat_timer.start(3000)

        self.scan_services()

    def _setup_dbus_listeners(self) -> bool:
        """Configura el listener de NameOwnerChanged en el bus de DBus."""
        if not self._ensure_bus_connected():
            return False
        try:
            self.bus.connect(
                "org.freedesktop.DBus",
                "/org/freedesktop/DBus",
                "org.freedesktop.DBus",
                "NameOwnerChanged",
                self._on_name_owner_changed
            )
            return True
        except Exception as e:
            print(f"[MPRISClient] Error registrando NameOwnerChanged: {e}")
            return False

    def _ensure_bus_connected(self) -> bool:
        """Verifica la salud del bus DBus y reconecta automáticamente si la conexión se perdió."""
        if self.bus.isConnected():
            return True
        print("[MPRISClient] Alerta: Conexión DBus interrumpida. Intentando reconectar...")
        self.bus = QDBusConnection.sessionBus()
        is_connected = self.bus.isConnected()
        self.bus_connection_changed.emit(is_connected)
        if is_connected:
            print("[MPRISClient] Reconexión exitosa a DBus Session Bus.")
            self._setup_dbus_listeners()
            self.scan_services()
        return is_connected

    def _health_check_and_refresh(self) -> None:
        """Supervisa el estado de la conexión DBus y actualiza los metadatos."""
        if not self._ensure_bus_connected():
            return
        self.refresh()

    def get_available_services(self) -> List[str]:
        """Devuelve la lista de servicios MPRIS2 activos en el bus DBus."""
        if not self._ensure_bus_connected():
            return []
        try:
            iface = self.bus.interface()
            if iface and iface.isValid():
                services = iface.registeredServiceNames().value()
                return [s for s in services if s.startswith("org.mpris.MediaPlayer2.")]
        except Exception as e:
            print(f"[MPRISClient] Error listando servicios DBus: {e}")
        return []

    def scan_services(self) -> None:
        """Escanea reproductores MPRIS disponibles y selecciona el prioritario."""
        mpris_services = self.get_available_services()
        self.players_list_changed.emit(mpris_services)

        if not mpris_services:
            self.set_active_service(None)
            return

        target = self.active_service
        if target not in mpris_services:
            if "org.mpris.MediaPlayer2.strawberry" in mpris_services:
                target = "org.mpris.MediaPlayer2.strawberry"
            elif "org.mpris.MediaPlayer2.spotify" in mpris_services:
                target = "org.mpris.MediaPlayer2.spotify"
            else:
                target = mpris_services[0]

        self.set_active_service(target)

    def set_active_service(self, service_name: Optional[str]) -> None:
        """Establece el reproductor activo e inicializa las interfaces DBus."""
        if self.active_service and self.active_service != service_name:
            try:
                if self.bus.isConnected():
                    self.bus.disconnect(
                        self.active_service,
                        "/org/mpris/MediaPlayer2",
                        "org.freedesktop.DBus.Properties",
                        "PropertiesChanged",
                        self._on_properties_changed
                    )
            except Exception:
                pass

        self.active_service = service_name

        if not service_name or not self._ensure_bus_connected():
            self.player_iface = None
            self.props_iface = None
            self.player_available.emit(False, "")
            self.metadata_changed.emit({})
            self.playback_status_changed.emit("Stopped")
            self.position_changed.emit(0, 0)
            return

        self.player_iface = QDBusInterface(
            service_name,
            "/org/mpris/MediaPlayer2",
            "org.mpris.MediaPlayer2.Player",
            self.bus
        )
        self.props_iface = QDBusInterface(
            service_name,
            "/org/mpris/MediaPlayer2",
            "org.freedesktop.DBus.Properties",
            self.bus
        )

        try:
            self.bus.connect(
                service_name,
                "/org/mpris/MediaPlayer2",
                "org.freedesktop.DBus.Properties",
                "PropertiesChanged",
                self._on_properties_changed
            )
        except Exception as e:
            print(f"[MPRISClient] Error suscribiendo a PropertiesChanged para {service_name}: {e}")

        display_name = service_name.replace("org.mpris.MediaPlayer2.", "").capitalize()
        self.player_available.emit(True, display_name)
        self.refresh()

    @pyqtSlot(QDBusMessage)
    def _on_name_owner_changed(self, msg: QDBusMessage) -> None:
        """Maneja el evento de aparición o cierre de reproductores en DBus."""
        args = msg.arguments()
        if len(args) >= 3:
            name, old_owner, new_owner = str(args[0]), str(args[1]), str(args[2])
            if name.startswith("org.mpris.MediaPlayer2."):
                mpris_services = self.get_available_services()
                self.players_list_changed.emit(mpris_services)
                if not new_owner and name == self.active_service:
                    self.scan_services()
                elif new_owner and not self.active_service:
                    self.set_active_service(name)

    @pyqtSlot(QDBusMessage)
    def _on_properties_changed(self, msg: QDBusMessage) -> None:
        """Procesa las notificaciones de cambio de propiedad de MPRIS (Event-driven)."""
        args = msg.arguments()
        if len(args) >= 2 and args[0] == "org.mpris.MediaPlayer2.Player":
            changed_props = args[1]
            if isinstance(changed_props, dict):
                if "Metadata" in changed_props:
                    self.current_metadata = self._parse_metadata(changed_props["Metadata"])
                    self.metadata_changed.emit(self.current_metadata)
                if "PlaybackStatus" in changed_props:
                    self.playback_status_changed.emit(str(changed_props["PlaybackStatus"]))
                if "Volume" in changed_props:
                    self.volume_changed.emit(float(changed_props["Volume"]))
                if "LoopStatus" in changed_props:
                    self.loop_status_changed.emit(str(changed_props["LoopStatus"]))
                if "Shuffle" in changed_props:
                    self.shuffle_status_changed.emit(bool(changed_props["Shuffle"]))

    def _poll_position(self) -> None:
        """Consulta la posición actual de reproducción en milisegundos de forma segura."""
        if not self.props_iface or not self.props_iface.isValid():
            return
        try:
            pos_reply = self.props_iface.call("Get", "org.mpris.MediaPlayer2.Player", "Position")
            if pos_reply and pos_reply.arguments():
                pos_us = int(pos_reply.arguments()[0])
                pos_sec = max(0, pos_us // 1000000)
                length_sec = self.current_metadata.get("length_sec", 0)
                self.position_changed.emit(pos_sec, length_sec)
        except Exception:
            pass

    def refresh(self) -> None:
        """Fuerza la sincronización completa de estado y metadatos del reproductor activo."""
        if not self.props_iface or not self.props_iface.isValid():
            self.scan_services()
            return

        try:
            # Metadata
            meta_reply = self.props_iface.call("Get", "org.mpris.MediaPlayer2.Player", "Metadata")
            if meta_reply and meta_reply.arguments():
                self.current_metadata = self._parse_metadata(meta_reply.arguments()[0])
                self.metadata_changed.emit(self.current_metadata)

            # Estado de reproducción
            status_reply = self.props_iface.call("Get", "org.mpris.MediaPlayer2.Player", "PlaybackStatus")
            if status_reply and status_reply.arguments():
                self.playback_status_changed.emit(str(status_reply.arguments()[0]))

            # Volumen
            vol_reply = self.props_iface.call("Get", "org.mpris.MediaPlayer2.Player", "Volume")
            if vol_reply and vol_reply.arguments():
                self.volume_changed.emit(float(vol_reply.arguments()[0]))

            # LoopStatus
            loop_reply = self.props_iface.call("Get", "org.mpris.MediaPlayer2.Player", "LoopStatus")
            if loop_reply and loop_reply.arguments():
                self.loop_status_changed.emit(str(loop_reply.arguments()[0]))

            # Shuffle
            shuf_reply = self.props_iface.call("Get", "org.mpris.MediaPlayer2.Player", "Shuffle")
            if shuf_reply and shuf_reply.arguments():
                self.shuffle_status_changed.emit(bool(shuf_reply.arguments()[0]))

            self._poll_position()
        except Exception as e:
            print(f"[MPRISClient] Error durante refresh DBus: {e}")
            self.scan_services()

    def _parse_metadata(self, metadata_raw: Any) -> Dict[str, Any]:
        """Parsea de forma segura el diccionario de metadatos de DBus."""
        if not isinstance(metadata_raw, dict):
            return {}

        title = str(metadata_raw.get("xesam:title", "Sin título"))
        artist_raw = metadata_raw.get("xesam:artist", ["Artista desconocido"])
        if isinstance(artist_raw, list) and artist_raw:
            artist = ", ".join([str(a) for a in artist_raw])
        elif isinstance(artist_raw, str):
            artist = artist_raw
        else:
            artist = "Artista desconocido"

        album = str(metadata_raw.get("xesam:album", ""))
        art_url = str(metadata_raw.get("mpris:artUrl", ""))
        length_us = int(metadata_raw.get("mpris:length", 0))
        length_sec = max(0, length_us // 1000000)
        track_id = str(metadata_raw.get("mpris:trackid", "/org/mpris/MediaPlayer2/TrackList/NoTrack"))

        return {
            "title": title,
            "artist": artist,
            "album": album,
            "art_url": art_url,
            "length_sec": length_sec,
            "track_id": track_id,
            "raw": metadata_raw
        }

    # Acciones de Control de Medios
    def play_pause(self) -> None:
        """Alterna entre reproducción y pausa."""
        if self.player_iface and self.player_iface.isValid():
            try:
                self.player_iface.call("PlayPause")
            except Exception as e:
                print(f"[MPRISClient] Error llamando a PlayPause: {e}")

    def previous(self) -> None:
        """Retrocede a la pista anterior."""
        if self.player_iface and self.player_iface.isValid():
            try:
                self.player_iface.call("Previous")
            except Exception as e:
                print(f"[MPRISClient] Error llamando a Previous: {e}")

    def next(self) -> None:
        """Avanza a la siguiente pista."""
        if self.player_iface and self.player_iface.isValid():
            try:
                self.player_iface.call("Next")
            except Exception as e:
                print(f"[MPRISClient] Error llamando a Next: {e}")

    def set_position(self, target_sec: int) -> None:
        """Establece la posición de reproducción en segundos."""
        if not self.player_iface or not self.player_iface.isValid():
            return
        track_id = self.current_metadata.get("track_id", "/org/mpris/MediaPlayer2/TrackList/NoTrack")
        position_us = target_sec * 1000000
        try:
            self.player_iface.call("SetPosition", QDBusObjectPath(track_id), position_us)
        except Exception as e:
            print(f"[MPRISClient] Error enviando SetPosition: {e}")

    def set_volume(self, volume: float) -> None:
        """Ajusta el volumen del reproductor activo (rango 0.0 - 1.0)."""
        volume = max(0.0, min(1.0, volume))
        if self.props_iface and self.props_iface.isValid():
            try:
                self.props_iface.call("Set", "org.mpris.MediaPlayer2.Player", "Volume", QVariant(volume))
            except Exception as e:
                print(f"[MPRISClient] Error cambiando volumen: {e}")

    def cycle_loop_status(self) -> None:
        """Alterna el modo de repetición: None -> Playlist -> Track -> None."""
        if not self.props_iface or not self.props_iface.isValid():
            return
        try:
            current_reply = self.props_iface.call("Get", "org.mpris.MediaPlayer2.Player", "LoopStatus")
            current = str(current_reply.arguments()[0]) if current_reply and current_reply.arguments() else "None"
            next_status = "Playlist" if current == "None" else ("Track" if current == "Playlist" else "None")
            self.props_iface.call("Set", "org.mpris.MediaPlayer2.Player", "LoopStatus", QVariant(next_status))
            self.loop_status_changed.emit(next_status)
        except Exception as e:
            print(f"[MPRISClient] Error cambiando LoopStatus: {e}")

    def toggle_shuffle(self) -> None:
        """Alterna el modo de reproducción aleatoria (Shuffle)."""
        if not self.props_iface or not self.props_iface.isValid():
            return
        try:
            current_reply = self.props_iface.call("Get", "org.mpris.MediaPlayer2.Player", "Shuffle")
            current = bool(current_reply.arguments()[0]) if current_reply and current_reply.arguments() else False
            next_shuffle = not current
            self.props_iface.call("Set", "org.mpris.MediaPlayer2.Player", "Shuffle", QVariant(next_shuffle))
            self.shuffle_status_changed.emit(next_shuffle)
        except Exception as e:
            print(f"[MPRISClient] Error cambiando Shuffle: {e}")

