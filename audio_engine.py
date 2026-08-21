import os
import random
import threading
from typing import Optional, Dict, Any, List

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from library_manager import scan_music_folder_fast, LibraryScannerThread
from config_manager import ConfigManager
from database_manager import get_database_manager


class AudioEngine(QObject):
    """Motor de reproducción de audio nativo local basado en PyQt6."""

    metadata_changed = pyqtSignal(dict)
    playback_status_changed = pyqtSignal(str)
    position_changed = pyqtSignal(int, int)
    position_ms_changed = pyqtSignal(int)
    volume_changed = pyqtSignal(float)
    loop_status_changed = pyqtSignal(str)
    shuffle_status_changed = pyqtSignal(bool)
    player_available = pyqtSignal(bool, str)
    players_list_changed = pyqtSignal(list)
    bus_connection_changed = pyqtSignal(bool)
    playlist_updated = pyqtSignal(list)
    playback_recorded = pyqtSignal(dict)

    def __init__(self, config: ConfigManager, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.config = config
        self.db = get_database_manager()

        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)

        self.playlist: List[Dict[str, Any]] = []
        self.shuffled_indices: List[int] = []
        self.current_index: int = self.config.get("current_index", 0)
        self.loop_status: str = self.config.get("loop_mode", "None")
        self.is_shuffle: bool = bool(self.config.get("shuffle", False))
        self.current_metadata: Dict[str, Any] = {}
        self.scanner_thread: Optional[LibraryScannerThread] = None
        self._last_pos_sec: int = -1
        self._playback_logged: bool = False

        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)

        self.set_volume(self.config.get("volume", 1.0))

        music_folder = self.config.get("music_folder", "")
        if music_folder and os.path.exists(music_folder):
            self.load_music_folder(music_folder, auto_play=False)

    @pyqtSlot()
    def refresh(self) -> None:
        """Sincroniza metadatos y estado actual de reproducción con la UI."""
        if self.playlist and 0 <= self.current_index < len(self.playlist):
            self.metadata_changed.emit(self.current_metadata)
            state = self.player.playbackState()
            status_str = {
                QMediaPlayer.PlaybackState.PlayingState: "Playing",
                QMediaPlayer.PlaybackState.PausedState: "Paused",
            }.get(state, "Stopped")
            self.playback_status_changed.emit(status_str)
            self.volume_changed.emit(self.audio_output.volume())
            self.loop_status_changed.emit(self.loop_status)
            self.shuffle_status_changed.emit(self.is_shuffle)
            self.playlist_updated.emit(self.playlist)
        else:
            self.scan_services()

    @pyqtSlot()
    def scan_services(self) -> None:
        """Alias de compatibilidad con MPRIS que refresca la biblioteca actual."""
        music_folder = self.config.get("music_folder", "")
        if music_folder and os.path.exists(music_folder):
            self.load_music_folder(music_folder, auto_play=False)
        else:
            self.player_available.emit(True, "Reproductor Nativo (Sin carpeta configurada)")

    @pyqtSlot(str)
    def load_music_folder(self, folder_path: str, auto_play: bool = False) -> None:
        """Escanea una carpeta local y enriquece los metadatos en segundo plano."""
        if not folder_path or not os.path.exists(folder_path):
            return

        self.config.set("music_folder", folder_path)
        self.playlist = scan_music_folder_fast(folder_path)
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

        if self.scanner_thread and self.scanner_thread.isRunning():
            self.scanner_thread.requestInterruption()
            self.scanner_thread.quit()
            self.scanner_thread.wait()

        self.scanner_thread = LibraryScannerThread(folder_path, self)
        self.scanner_thread.metadata_updated.connect(self._on_metadata_item_updated)
        self.scanner_thread.scan_completed.connect(self._on_scan_completed)
        self.scanner_thread.start()

    @pyqtSlot()
    def stop_scanner(self) -> None:
        """Detiene de forma limpia el hilo secundario de escaneo."""
        if self.scanner_thread and self.scanner_thread.isRunning():
            self.scanner_thread.requestInterruption()
            self.scanner_thread.quit()
            self.scanner_thread.wait()

    @pyqtSlot()
    def shutdown(self) -> None:
        """Cierre ordenado de los recursos del motor de audio y persistencia."""
        self.stop_scanner()
        try:
            self.db.shutdown(timeout=3.0)
        except Exception as e:
            print(f"[AudioEngine] Error cerrando base de datos: {e}")

    @pyqtSlot(int, dict)
    def _on_metadata_item_updated(self, idx: int, meta: dict) -> None:
        if 0 <= idx < len(self.playlist):
            self.playlist[idx] = meta
            if idx == self.current_index:
                self.current_metadata = meta
                self.metadata_changed.emit(meta)

    @pyqtSlot(list)
    def _on_scan_completed(self, enriched_tracks: list) -> None:
        if enriched_tracks:
            self.playlist = enriched_tracks
            self.playlist_updated.emit(self.playlist)

    def _rebuild_shuffle_indices(self) -> None:
        count = len(self.playlist)
        self.shuffled_indices = list(range(count))
        if self.is_shuffle and count > 1:
            random.shuffle(self.shuffled_indices)

    def _load_track(self, index: int, auto_play: bool = True) -> None:
        if not self.playlist or index < 0 or index >= len(self.playlist):
            return

        self.current_index = index
        self.config.set("current_index", index)
        self._last_pos_sec = -1
        self._playback_logged = False
        track = self.playlist[index]
        file_path = track.get("file_path", "")

        if os.path.exists(file_path):
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

    @pyqtSlot()
    def play_pause(self) -> None:
        if not self.playlist:
            music_folder = self.config.get("music_folder", "")
            if music_folder:
                self.load_music_folder(music_folder, auto_play=True)
            return

        state = self.player.playbackState()
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        elif self.player.mediaStatus() == QMediaPlayer.MediaStatus.NoMedia:
            self._load_track(self.current_index, auto_play=True)
        else:
            self.player.play()

    @pyqtSlot()
    def play(self) -> None:
        self.play_pause()

    @pyqtSlot()
    def pause(self) -> None:
        self.player.pause()

    @pyqtSlot()
    def stop(self) -> None:
        self.player.stop()

    @pyqtSlot()
    def next(self) -> None:
        if not self.playlist:
            return

        count = len(self.playlist)
        if self.is_shuffle and count > 1:
            try:
                curr_shuf_pos = self.shuffled_indices.index(self.current_index)
                next_index = self.shuffled_indices[(curr_shuf_pos + 1) % count]
            except ValueError:
                next_index = (self.current_index + 1) % count
        else:
            next_index = (self.current_index + 1) % count
        self._load_track(next_index, auto_play=True)

    @pyqtSlot()
    def previous(self) -> None:
        if not self.playlist:
            return

        if self.player.position() > 3000:
            self.player.setPosition(0)
            return

        count = len(self.playlist)
        if self.is_shuffle and count > 1:
            try:
                curr_shuf_pos = self.shuffled_indices.index(self.current_index)
                prev_index = self.shuffled_indices[(curr_shuf_pos - 1 + count) % count]
            except ValueError:
                prev_index = (self.current_index - 1 + count) % count
        else:
            prev_index = (self.current_index - 1 + count) % count
        self._load_track(prev_index, auto_play=True)

    @pyqtSlot(int)
    def play_index(self, index: int) -> None:
        if 0 <= index < len(self.playlist):
            self._load_track(index, auto_play=True)

    @pyqtSlot(int)
    def set_position(self, target_sec: int) -> None:
        self._last_pos_sec = -1
        self.player.setPosition(max(0, target_sec * 1000))

    @pyqtSlot(int)
    def seek_relative(self, offset_sec: int) -> None:
        """Avanza o retrocede de forma relativa en la pista actual (segundos)."""
        current_ms = self.player.position()
        target_ms = max(0, min(self.player.duration(), current_ms + offset_sec * 1000))
        self._last_pos_sec = -1
        self.player.setPosition(target_ms)

    @pyqtSlot(float)
    def set_volume(self, volume: float) -> None:
        vol = max(0.0, min(1.0, volume))
        self.audio_output.setVolume(vol)
        self.config.set("volume", vol)
        self.volume_changed.emit(vol)

    @pyqtSlot()
    def cycle_loop_status(self) -> None:
        self.loop_status = {
            "None": "Playlist",
            "Playlist": "Track",
            "Track": "None",
        }.get(self.loop_status, "None")
        self.config.set("loop_mode", self.loop_status)
        self.loop_status_changed.emit(self.loop_status)

    @pyqtSlot()
    def toggle_shuffle(self) -> None:
        self.is_shuffle = not self.is_shuffle
        self._rebuild_shuffle_indices()
        self.config.set("shuffle", self.is_shuffle)
        self.shuffle_status_changed.emit(self.is_shuffle)

    @pyqtSlot('qint64')
    def _on_position_changed(self, pos_ms: int) -> None:
        self.position_ms_changed.emit(max(0, int(pos_ms)))
        pos_sec = max(0, pos_ms // 1000)
        if pos_sec == self._last_pos_sec:
            return
        self._last_pos_sec = pos_sec
        length_sec = self.current_metadata.get("length_sec", max(0, self.player.duration() // 1000))
        self.position_changed.emit(pos_sec, length_sec)

        # Hook de persistencia con umbral anti-skip (>10s o >50% en pistas muy cortas)
        if (
            not self._playback_logged
            and self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
            and self.current_metadata
        ):
            threshold_met = pos_sec >= 10 or (length_sec > 0 and pos_sec >= max(3, length_sec // 2))
            if threshold_met:
                self._playback_logged = True
                self._record_playback_async(dict(self.current_metadata))
                self.playback_recorded.emit(dict(self.current_metadata))

    def _record_playback_async(self, track_meta: dict) -> None:
        """Despacha el guardado en la cola persistente del DatabaseManager."""
        if not track_meta:
            return
        self.db.record_playback_async(track_meta)

    @pyqtSlot('qint64')
    def _on_duration_changed(self, dur_ms: int) -> None:
        dur_sec = max(0, dur_ms // 1000)
        if self.current_metadata:
            self.current_metadata["length_sec"] = dur_sec
        self.position_changed.emit(max(0, self.player.position() // 1000), dur_sec)

    @pyqtSlot(QMediaPlayer.PlaybackState)
    def _on_playback_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        status_str = {
            QMediaPlayer.PlaybackState.PlayingState: "Playing",
            QMediaPlayer.PlaybackState.PausedState: "Paused",
        }.get(state, "Stopped")
        self.playback_status_changed.emit(status_str)

    @pyqtSlot(QMediaPlayer.MediaStatus)
    def _on_media_status_changed(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self.loop_status == "Track":
                self.player.setPosition(0)
                self.player.play()
            elif self.loop_status == "Playlist" or (self.current_index + 1 < len(self.playlist)):
                self.next()
            else:
                self.stop()
