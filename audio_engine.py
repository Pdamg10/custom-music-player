import os
import random
from typing import Optional, Dict, Any, List

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from library_manager import scan_music_folder_fast, LibraryScannerThread, sort_tracks
from config_manager import ConfigManager
from database_manager import get_database_manager


def _silence_ffmpeg_warnings() -> None:
    """Silencia advertencias de bajo nivel de FFmpeg (ej. demuxer de FLAC/MP3 con mimetypes de imagen no estándar)."""
    try:
        import ctypes
        import ctypes.util
        lib = ctypes.util.find_library('avutil') or 'libavutil.so'
        if lib:
            avutil = ctypes.CDLL(lib)
            if hasattr(avutil, 'av_log_set_level'):
                avutil.av_log_set_level(16)  # AV_LOG_ERROR
    except Exception:
        pass


_silence_ffmpeg_warnings()


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
        raw_shuf = self.config.get("shuffle", False)
        if isinstance(raw_shuf, str):
            self.is_shuffle: bool = raw_shuf.strip().lower() in ("true", "1", "yes")
        else:
            self.is_shuffle: bool = bool(raw_shuf)
        self.current_metadata: Dict[str, Any] = {}
        self.scanner_thread: Optional[LibraryScannerThread] = None
        self._last_pos_sec: int = -1
        self._playback_logged: bool = False

        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)
        self.player.errorOccurred.connect(self._on_player_error)

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
        raw_tracks = scan_music_folder_fast(folder_path)
        sort_key = self.config.get("library_sort_order", "recent")
        self.playlist = sort_tracks(raw_tracks, sort_key)
        self._rebuild_shuffle_indices()
        self.playlist_updated.emit(self.playlist)
        self.player_available.emit(True, f"Nativo ({len(self.playlist)} canciones)")
        self.shuffle_status_changed.emit(self.is_shuffle)
        self.loop_status_changed.emit(self.loop_status)

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
        if not meta:
            return
        target_path = meta.get("file_path") or meta.get("path")
        if target_path:
            for i, track in enumerate(self.playlist):
                if (track.get("file_path") or track.get("path")) == target_path:
                    track.update(meta)
                    if i == self.current_index:
                        self.current_metadata = track
                        self.metadata_changed.emit(track)
                    break
        elif 0 <= idx < len(self.playlist):
            self.playlist[idx].update(meta)
            if idx == self.current_index:
                self.current_metadata = self.playlist[idx]
                self.metadata_changed.emit(self.playlist[idx])

    @pyqtSlot(list)
    def _on_scan_completed(self, enriched_tracks: list) -> None:
        """Actualiza la lista de reproducción con los metadatos completos leídos en segundo plano."""
        if enriched_tracks:
            curr_track = self.playlist[self.current_index] if (self.playlist and 0 <= self.current_index < len(self.playlist)) else None
            sort_key = self.config.get("library_sort_order", "recent")
            self.playlist = sort_tracks(enriched_tracks, sort_key)
            if curr_track:
                target_path = curr_track.get("file_path") or curr_track.get("path")
                target_id = curr_track.get("track_id")
                for i, t in enumerate(self.playlist):
                    if (target_path and (t.get("file_path") or t.get("path")) == target_path) or \
                       (target_id and t.get("track_id") == target_id):
                        self.current_index = i
                        self.config.set("current_index", i)
                        break
            self._rebuild_shuffle_indices()
            self.playlist_updated.emit(self.playlist)

    def _rebuild_shuffle_indices(self) -> None:
        count = len(self.playlist)
        if count <= 0:
            self.shuffled_indices = []
            return
        if self.is_shuffle and count > 1:
            indices = list(range(count))
            if 0 <= self.current_index < count:
                remaining = [i for i in indices if i != self.current_index]
                random.shuffle(remaining)
                self.shuffled_indices = [self.current_index] + remaining
            else:
                random.shuffle(indices)
                self.shuffled_indices = indices
        else:
            self.shuffled_indices = list(range(count))

    def _ensure_shuffle_indices(self) -> None:
        count = len(self.playlist)
        if len(self.shuffled_indices) != count or (count > 0 and set(self.shuffled_indices) != set(range(count))):
            self._rebuild_shuffle_indices()

    def _load_track(self, index: int, auto_play: bool = True) -> None:
        if not self.playlist or index < 0 or index >= len(self.playlist):
            return

        self.current_index = index
        self.config.set("current_index", index)
        self._last_pos_sec = -1
        self._playback_logged = False
        track = self.playlist[index]
        file_path = track.get("file_path", "")

        is_url = file_path.startswith("http://") or file_path.startswith("https://")
        if is_url:
            self.current_metadata = track
            self.player.setSource(QUrl(file_path))
            self.metadata_changed.emit(track)
            if auto_play:
                self.player.play()
        elif os.path.exists(file_path):
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
            print(f"[AudioEngine] Archivo o recurso no encontrado: {file_path}")

    def add_track(self, track_meta: Dict[str, Any], play_now: bool = True) -> int:
        """Añade una pista a la lista de reproducción y opcionalmente la reproduce de inmediato."""
        if not isinstance(self.playlist, list):
            self.playlist = []
        if isinstance(track_meta, dict):
            if "added_at" not in track_meta:
                track_meta["added_at"] = time.time()
            fp = track_meta.get("file_path") or ""
            if fp and os.path.exists(fp) and "file_mtime" not in track_meta:
                try:
                    st = os.stat(fp)
                    track_meta["file_mtime"] = max(st.st_mtime, st.st_ctime)
                except Exception:
                    pass
        self.playlist.append(track_meta)
        new_index = len(self.playlist) - 1
        self._rebuild_shuffle_indices()

        # Registrar en base de datos para sincronizar búsquedas e historial inmediatamente
        if hasattr(self, "db") and self.db and track_meta:
            try:
                self.db.upsert_or_migrate_track(track_meta)
            except Exception as e:
                print(f"[AudioEngine] Error registrando pista en DB: {e}")

        self.playlist_updated.emit(self.playlist)
        if play_now:
            self.play_index(new_index)
        return new_index

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
            self._ensure_shuffle_indices()
            try:
                curr_shuf_pos = self.shuffled_indices.index(self.current_index)
                next_index = self.shuffled_indices[(curr_shuf_pos + 1) % count]
            except ValueError:
                remaining = [i for i in range(count) if i != self.current_index]
                next_index = random.choice(remaining) if remaining else 0
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
            self._ensure_shuffle_indices()
            try:
                curr_shuf_pos = self.shuffled_indices.index(self.current_index)
                prev_index = self.shuffled_indices[(curr_shuf_pos - 1 + count) % count]
            except ValueError:
                remaining = [i for i in range(count) if i != self.current_index]
                prev_index = random.choice(remaining) if remaining else 0
        else:
            prev_index = (self.current_index - 1 + count) % count
        self._load_track(prev_index, auto_play=True)

    @pyqtSlot(int)
    def play_index(self, index: int) -> None:
        if 0 <= index < len(self.playlist):
            self.current_index = index
            if self.is_shuffle and len(self.playlist) > 1:
                remaining = [i for i in range(len(self.playlist)) if i != index]
                random.shuffle(remaining)
                self.shuffled_indices = [index] + remaining
            self._load_track(index, auto_play=True)

    @pyqtSlot(str)
    def apply_sort(self, sort_key: str) -> None:
        """Aplica un criterio de ordenación a la lista de reproducción activa sin cortar la música."""
        if not self.playlist or not sort_key:
            return
        curr_track = self.playlist[self.current_index] if (0 <= self.current_index < len(self.playlist)) else None
        self.playlist = sort_tracks(self.playlist, sort_key)
        if curr_track:
            target_path = curr_track.get("file_path") or curr_track.get("path")
            target_id = curr_track.get("track_id")
            for idx, t in enumerate(self.playlist):
                if (target_path and (t.get("file_path") or t.get("path")) == target_path) or \
                   (target_id and t.get("track_id") == target_id):
                    self.current_index = idx
                    self.config.set("current_index", idx)
                    break
        self.config.set("library_sort_order", sort_key)
        self._rebuild_shuffle_indices()
        self.playlist_updated.emit(self.playlist)

    @pyqtSlot(list, int, bool)
    def set_playlist(self, tracks: List[Dict[str, Any]], start_index: int = 0, auto_play: bool = True) -> None:
        """Establece una lista de reproducción explícita (ej. lista personalizada, filtrada u ordenada)."""
        if not tracks:
            return
        self.playlist = list(tracks)
        self.current_index = max(0, min(start_index, len(self.playlist) - 1))
        self.config.set("current_index", self.current_index)
        self._rebuild_shuffle_indices()
        self.playlist_updated.emit(self.playlist)
        if auto_play:
            self._load_track(self.current_index, auto_play=True)

    def insert_next(self, track_meta: Dict[str, Any]) -> None:
        """Inserta una pista en la cola de reproducción justo después de la actual."""
        if not isinstance(self.playlist, list):
            self.playlist = []
        insert_pos = (
            self.current_index + 1
            if (0 <= self.current_index < len(self.playlist))
            else len(self.playlist)
        )
        self.playlist.insert(insert_pos, track_meta)
        self._rebuild_shuffle_indices()
        self.playlist_updated.emit(self.playlist)

    def remove_track_at(self, index: int) -> None:
        """Remueve una canción de la cola activa en memoria."""
        if not isinstance(self.playlist, list) or index < 0 or index >= len(self.playlist):
            return
        self.playlist.pop(index)
        if index < self.current_index:
            self.current_index -= 1
        elif index == self.current_index:
            if self.playlist:
                self.current_index = min(self.current_index, len(self.playlist) - 1)
                self._load_track(self.current_index, auto_play=True)
            else:
                self.current_index = -1
                self.stop()
        self._rebuild_shuffle_indices()
        self.playlist_updated.emit(self.playlist)

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

    @pyqtSlot(bool)
    def set_shuffle(self, enable: bool) -> None:
        if self.is_shuffle != enable:
            self.is_shuffle = enable
            self._rebuild_shuffle_indices()
            self.config.set("shuffle", self.is_shuffle)
            self.shuffle_status_changed.emit(self.is_shuffle)

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

    @pyqtSlot(QMediaPlayer.Error, str)
    def _on_player_error(self, error: QMediaPlayer.Error, error_string: str) -> None:
        if error == QMediaPlayer.Error.NoError:
            return
        print(f"[AudioEngine] QMediaPlayer Error ({error}): {error_string}")
        if self.current_metadata and (self.current_metadata.get("is_online_stream") or str(self.current_metadata.get("file_path", "")).startswith("http")):
            curr_pos = max(0, self.player.position())
            retry_count = getattr(self, '_stream_retry_count', 0)
            if retry_count < 3:
                self._stream_retry_count = retry_count + 1
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(1200, lambda: self._resume_stream_at(curr_pos))

    def _resume_stream_at(self, pos_ms: int) -> None:
        """Reanuda la reproducción de un stream online tras desconexión de red o término abrupto de conexión."""
        if not self.current_metadata:
            return
        source_url = self.current_metadata.get("source_url") or self.current_metadata.get("file_path")
        if not source_url:
            return

        def _worker():
            try:
                from online_stream_manager import extract_online_stream_info
                fresh_meta = extract_online_stream_info(source_url)
                fresh_stream_url = fresh_meta.get("file_path")
                if fresh_stream_url:
                    from PyQt6.QtCore import QTimer
                    def _apply():
                        self.current_metadata["file_path"] = fresh_stream_url
                        self.player.setSource(QUrl(fresh_stream_url))
                        self.player.setPosition(pos_ms)
                        self.player.play()
                    QTimer.singleShot(0, _apply)
            except Exception as e:
                print(f"[AudioEngine] Error reanudando stream: {e}")
                from PyQt6.QtCore import QTimer
                def _fallback():
                    self.player.setPosition(pos_ms)
                    self.player.play()
                QTimer.singleShot(500, _fallback)

        import threading
        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    @pyqtSlot(QMediaPlayer.MediaStatus)
    def _on_media_status_changed(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            curr_pos_ms = self.player.position()
            track_dur_ms = self.player.duration()
            if track_dur_ms <= 0 and self.current_metadata:
                track_dur_ms = int(self.current_metadata.get("length_sec", 0)) * 1000

            is_online = bool(
                self.current_metadata and (
                    self.current_metadata.get("is_online_stream") or
                    str(self.current_metadata.get("file_path", "")).startswith("http")
                )
            )

            # Comprobar si realmente terminó la pista o si fue un corte prematuro
            # (si duraba más de 15 segundos y terminó con más de 4 segundos de antelación)
            if track_dur_ms > 15000 and curr_pos_ms < (track_dur_ms - 4000):
                if is_online:
                    retry_count = getattr(self, '_stream_retry_count', 0)
                    if retry_count < 4:
                        self._stream_retry_count = retry_count + 1
                        print(f"[AudioEngine] Stream interrumpido en {curr_pos_ms // 1000}s de {track_dur_ms // 1000}s. Reanudando...")
                        self._resume_stream_at(curr_pos_ms)
                        return
                    else:
                        print("[AudioEngine] Se superaron los reintentos de stream.")
                        self._stream_retry_count = 0
                else:
                    if curr_pos_ms < (track_dur_ms * 0.90):
                        print(f"[AudioEngine] Archivo cortado prematuramente en {curr_pos_ms // 1000}s de {track_dur_ms // 1000}s. Reintentando...")
                        self.player.setPosition(curr_pos_ms)
                        self.player.play()
                        return

            self._stream_retry_count = 0

            if self.loop_status == "Track":
                self.player.setPosition(0)
                self.player.play()
            elif self.loop_status == "Playlist":
                self.next()
            elif self.is_shuffle:
                count = len(self.playlist)
                self._ensure_shuffle_indices()
                try:
                    curr_shuf_pos = self.shuffled_indices.index(self.current_index)
                    if curr_shuf_pos + 1 < count:
                        self.next()
                    else:
                        self.stop()
                except ValueError:
                    self.next()
            elif (self.current_index + 1 < len(self.playlist)):
                self.next()
            else:
                self.stop()
