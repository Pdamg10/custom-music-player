import os
import random
from typing import Optional, Dict, Any, List
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from library_manager import scan_music_folder_fast, read_track_metadata, LibraryScannerThread
from config_manager import ConfigManager

class AudioEngine(QObject):
    """Motor de reproducción de audio nativo local basado en PyQt6 QMediaPlayer y QAudioOutput."""

    # Señales compatibles con MPRISClient para una integración directa con UI
    metadata_changed = pyqtSignal(dict)
    playback_status_changed = pyqtSignal(str) # "Playing", "Paused", "Stopped"
    position_changed = pyqtSignal(int, int)   # (pos_sec, duration_sec)
    volume_changed = pyqtSignal(float)        # 0.0 a 1.0
    loop_status_changed = pyqtSignal(str)     # "None", "Playlist", "Track"
    shuffle_status_changed = pyqtSignal(bool) # True / False
    player_available = pyqtSignal(bool, str)  # (available, display_name)
    players_list_changed = pyqtSignal(list)
    bus_connection_changed = pyqtSignal(bool)
    playlist_updated = pyqtSignal(list)

    def __init__(self, config: ConfigManager, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.config = config

        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)

        self.playlist: List[Dict[str, Any]] = []
        self.shuffled_indices: List[int] = []
        self.current_index: int = self.config.get("current_index", 0)
        self.loop_status: str = self.config.get("loop_mode", "None") # "None", "Playlist", "Track"
        self.is_shuffle: bool = bool(self.config.get("shuffle", False))
        self.current_metadata: Dict[str, Any] = {}
        self.scanner_thread: Optional[LibraryScannerThread] = None

        # Conectar señales del QMediaPlayer
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)

        # Restaurar volumen inicial
        initial_vol = self.config.get("volume", 1.0)
        self.set_volume(initial_vol)

        # Cargar biblioteca inicial desde music_folder
        music_folder = self.config.get("music_folder", "")
        if music_folder and os.path.exists(music_folder):
            self.load_music_folder(music_folder, auto_play=False)

    def refresh(self) -> None:
        """Sincroniza metadatos y estado actual de reproducción con la UI."""
        if self.playlist and 0 <= self.current_index < len(self.playlist):
            self.metadata_changed.emit(self.current_metadata)
            state = self.player.playbackState()
            if state == QMediaPlayer.PlaybackState.PlayingState:
                status_str = "Playing"
            elif state == QMediaPlayer.PlaybackState.PausedState:
                status_str = "Paused"
            else:
                status_str = "Stopped"
            self.playback_status_changed.emit(status_str)
            self.volume_changed.emit(self.audio_output.volume())
            self.loop_status_changed.emit(self.loop_status)
            self.shuffle_status_changed.emit(self.is_shuffle)
            self.playlist_updated.emit(self.playlist)
        else:
            self.scan_services()

    def scan_services(self) -> None:
        """Alias de compatibilidad con MPRIS. Refresca la biblioteca actual."""
        music_folder = self.config.get("music_folder", "")
        if music_folder and os.path.exists(music_folder):
            self.load_music_folder(music_folder, auto_play=False)
        else:
            self.player_available.emit(True, "Reproductor Nativo (Sin carpeta configurada)")

    def load_music_folder(self, folder_path: str, auto_play: bool = False) -> None:
        """Escanea una carpeta local en milisegundos y enriquece los metadatos en segundo plano."""
        if not folder_path or not os.path.exists(folder_path):
            return

        self.config.set("music_folder", folder_path)
        # 1. Escaneo ultrarrápido sin bloqueo
        fast_tracks = scan_music_folder_fast(folder_path)
        self.playlist = fast_tracks
        self._rebuild_shuffle_indices()

        self.playlist_updated.emit(self.playlist)
        self.player_available.emit(True, f"Nativo ({len(self.playlist)} canciones)")

        if self.playlist:
            if self.current_index >= len(self.playlist):
                self.current_index = 0
            self._load_track(self.current_index, auto_play=auto_play)
        else:
            self.current_metadata = {}
            self.metadata_changed.emit({})
            self.playback_status_changed.emit("Stopped")

        # 2. Iniciar escaneo profundo de metadatos e imágenes en hilo secundario
        if self.scanner_thread and self.scanner_thread.isRunning():
            self.scanner_thread.quit()
            self.scanner_thread.wait()

        self.scanner_thread = LibraryScannerThread(folder_path, self)
        self.scanner_thread.metadata_updated.connect(self._on_metadata_item_updated)
        self.scanner_thread.scan_completed.connect(self._on_scan_completed)
        self.scanner_thread.start()

    def stop_scanner(self) -> None:
        """Detiene de forma limpia el hilo secundario de escaneo de metadatos."""
        if self.scanner_thread and self.scanner_thread.isRunning():
            self.scanner_thread.requestInterruption()
            self.scanner_thread.quit()
            self.scanner_thread.wait()

    def _on_metadata_item_updated(self, idx: int, meta: dict) -> None:
        if 0 <= idx < len(self.playlist):
            self.playlist[idx] = meta
            if idx == self.current_index:
                self.current_metadata = meta
                self.metadata_changed.emit(meta)

    def _on_scan_completed(self, enriched_tracks: list) -> None:
        if enriched_tracks:
            self.playlist = enriched_tracks
            self.playlist_updated.emit(self.playlist)

    def _rebuild_shuffle_indices(self) -> None:
        """Construye la lista de índices aleatorios para el modo Shuffle."""
        count = len(self.playlist)
        self.shuffled_indices = list(range(count))
        if self.is_shuffle and count > 1:
            random.shuffle(self.shuffled_indices)

    def _load_track(self, index: int, auto_play: bool = True) -> None:
        """Carga una pista por su índice en la lista de reproducción."""
        if not self.playlist or index < 0 or index >= len(self.playlist):
            return

        self.current_index = index
        self.config.set("current_index", index)
        track = self.playlist[index]

        file_path = track.get("file_path", "")
        if os.path.exists(file_path):
            # Si el track no tiene metadatos enriquecidos todavía, leerlos de inmediato
            if not track.get("art_url") or track.get("artist") in ("Cargando metadatos...", "Artista desconocido"):
                try:
                    from library_manager import read_track_metadata
                    enriched = read_track_metadata(file_path)
                    if enriched:
                        track.update(enriched)
                        self.playlist[index] = track
                except Exception as e:
                    print(f"[AudioEngine] Error leyendo metadatos síncronos de {file_path}: {e}")

            self.current_metadata = track
            self.player.setSource(QUrl.fromLocalFile(file_path))
            self.metadata_changed.emit(track)
            if auto_play:
                self.player.play()
        else:
            print(f"[AudioEngine] Archivo no encontrado: {file_path}")

    # Acciones de Control
    def play_pause(self) -> None:
        """Alterna entre Reproducción y Pausa."""
        if not self.playlist:
            music_folder = self.config.get("music_folder", "")
            if music_folder:
                self.load_music_folder(music_folder, auto_play=True)
            return

        state = self.player.playbackState()
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            if self.player.mediaStatus() == QMediaPlayer.MediaStatus.NoMedia:
                self._load_track(self.current_index, auto_play=True)
            else:
                self.player.play()

    def play(self) -> None:
        if self.playlist:
            self.player.play()

    def pause(self) -> None:
        self.player.pause()

    def stop(self) -> None:
        self.player.stop()

    def next(self) -> None:
        """Avanza a la siguiente pista de la lista de reproducción."""
        if not self.playlist:
            return

        count = len(self.playlist)
        if self.is_shuffle and count > 1:
            try:
                curr_shuf_pos = self.shuffled_indices.index(self.current_index)
                next_shuf_pos = (curr_shuf_pos + 1) % count
                next_index = self.shuffled_indices[next_shuf_pos]
            except ValueError:
                next_index = (self.current_index + 1) % count
        else:
            next_index = (self.current_index + 1) % count

        self._load_track(next_index, auto_play=True)

    def previous(self) -> None:
        """Retrocede a la pista anterior o reinicia la canción si han pasado más de 3s."""
        if not self.playlist:
            return

        # Si lleva más de 3 segundos reproduciéndose, reiniciar pista actual
        if self.player.position() > 3000:
            self.player.setPosition(0)
            return

        count = len(self.playlist)
        if self.is_shuffle and count > 1:
            try:
                curr_shuf_pos = self.shuffled_indices.index(self.current_index)
                prev_shuf_pos = (curr_shuf_pos - 1 + count) % count
                prev_index = self.shuffled_indices[prev_shuf_pos]
            except ValueError:
                prev_index = (self.current_index - 1 + count) % count
        else:
            prev_index = (self.current_index - 1 + count) % count

        self._load_track(prev_index, auto_play=True)

    def play_index(self, index: int) -> None:
        """Reproduce directamente una pista por índice."""
        if 0 <= index < len(self.playlist):
            self._load_track(index, auto_play=True)

    def set_position(self, target_sec: int) -> None:
        """Establece la posición de reproducción en segundos."""
        ms = max(0, target_sec * 1000)
        self.player.setPosition(ms)

    def set_volume(self, volume: float) -> None:
        """Ajusta el volumen del canal de audio (rango 0.0 - 1.0)."""
        vol = max(0.0, min(1.0, volume))
        self.audio_output.setVolume(vol)
        self.config.set("volume", vol)
        self.volume_changed.emit(vol)

    def cycle_loop_status(self) -> None:
        """Alterna el modo de repetición: None -> Playlist -> Track -> None."""
        if self.loop_status == "None":
            self.loop_status = "Playlist"
        elif self.loop_status == "Playlist":
            self.loop_status = "Track"
        else:
            self.loop_status = "None"

        self.config.set("loop_mode", self.loop_status)
        self.loop_status_changed.emit(self.loop_status)

    def toggle_shuffle(self) -> None:
        """Alterna el modo aleatorio (Shuffle)."""
        self.is_shuffle = not self.is_shuffle
        self._rebuild_shuffle_indices()
        self.config.set("shuffle", self.is_shuffle)
        self.shuffle_status_changed.emit(self.is_shuffle)

    # Manejadores Internos de QtMultimedia
    def _on_position_changed(self, pos_ms: int) -> None:
        pos_sec = max(0, pos_ms // 1000)
        length_sec = self.current_metadata.get("length_sec", max(0, self.player.duration() // 1000))
        self.position_changed.emit(pos_sec, length_sec)

    def _on_duration_changed(self, dur_ms: int) -> None:
        dur_sec = max(0, dur_ms // 1000)
        if self.current_metadata:
            self.current_metadata["length_sec"] = dur_sec
        pos_sec = max(0, self.player.position() // 1000)
        self.position_changed.emit(pos_sec, dur_sec)

    def _on_playback_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        if state == QMediaPlayer.PlaybackState.PlayingState:
            status_str = "Playing"
        elif state == QMediaPlayer.PlaybackState.PausedState:
            status_str = "Paused"
        else:
            status_str = "Stopped"

        self.playback_status_changed.emit(status_str)

    def _on_media_status_changed(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self.loop_status == "Track":
                self.player.setPosition(0)
                self.player.play()
            elif self.loop_status == "Playlist" or (self.current_index + 1 < len(self.playlist)):
                self.next()
            else:
                self.stop()
