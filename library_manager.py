import hashlib
import os
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import QThread, pyqtSignal, QObject

try:
    import mutagen
    from mutagen.flac import FLAC
    from mutagen.id3 import ID3, APIC
    from mutagen.mp4 import MP4
    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False

try:
    from tinytag import TinyTag
    HAS_TINYTAG = True
except ImportError:
    HAS_TINYTAG = False

from config_manager import get_platform_base_dir

CACHE_DIR = get_platform_base_dir("config", "covers")
AUDIO_EXTENSIONS = {".mp3", ".flac", ".wav", ".m4a", ".ogg", ".opus", ".aac", ".wma"}
VIDEO_EXTENSIONS = {
    ".mp4", ".webm", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".m4v",
    ".ts", ".mts", ".m2ts", ".ogv", ".3gp", ".mpg", ".mpeg", ".vob"
}
SUPPORTED_EXTENSIONS = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS

UNKNOWN_ARTIST = "Artista desconocido"
UNKNOWN_ALBUM = "Álbum desconocido"
LOADING_METADATA = "Cargando metadatos..."


def ensure_cache_dir() -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)


def get_track_id(file_path: str) -> str:
    return hashlib.md5(file_path.encode("utf-8")).hexdigest()


def extract_cover_art(file_path: str, track_id: str) -> str:
    """Extrae la carátula incrustada y la guarda en la caché local de forma ultra-rápida."""
    ensure_cache_dir()
    cache_path = os.path.join(CACHE_DIR, f"{track_id}.jpg")
    if os.path.exists(cache_path):
        return f"file://{cache_path}"

    ext = os.path.splitext(file_path)[1].lower()
    if ext in VIDEO_EXTENSIONS:
        try:
            from ui.image_cache import extract_video_thumbnail
            thumb = extract_video_thumbnail(file_path)
            if thumb and os.path.exists(thumb):
                return f"file://{thumb}"
        except Exception:
            pass
        return ""

    if not HAS_MUTAGEN:
        return ""

    try:
        ext = os.path.splitext(file_path)[1].lower()
        image_data = None

        if ext == ".mp3":
            try:
                tags = ID3(file_path)
                image_data = next((tag.data for tag in tags.values() if isinstance(tag, APIC)), None)
            except Exception:
                pass
        elif ext == ".flac":
            try:
                audio = FLAC(file_path)
                if audio.pictures:
                    image_data = audio.pictures[0].data
            except Exception:
                pass
        elif ext == ".m4a":
            try:
                audio = MP4(file_path)
                covers = audio.tags.get("covr") if audio.tags else None
                if covers:
                    image_data = bytes(covers[0])
            except Exception:
                pass
        else:
            try:
                audio = mutagen.File(file_path)
                if audio and getattr(audio, "tags", None):
                    for key in audio.tags:
                        if "APIC" in key:
                            image_data = audio.tags[key].data
                            break
            except Exception:
                pass

        if image_data:
            # Escritura directa en binario sin pasar por re-codificación lenta en PIL (300x más rápido)
            try:
                with open(cache_path, "wb") as f:
                    f.write(image_data)
                return f"file://{cache_path}"
            except Exception:
                pass
    except Exception as e:
        print(f"[LibraryManager] Error extrayendo carátula de {file_path}: {e}")

    return ""


def read_track_metadata(file_path: str) -> Dict[str, Any]:
    """Lee metadatos con fallbacks ultra-rápidos entre TinyTag, Mutagen y caché de carátula."""
    base_name = os.path.splitext(os.path.basename(file_path))[0] if file_path else "Desconocido"
    track_id = get_track_id(file_path) if file_path else ""
    title = base_name
    artist = UNKNOWN_ARTIST
    album = UNKNOWN_ALBUM
    length_sec = 0
    art_url = ""

    if not file_path or not os.path.exists(file_path):
        return {
            "file_path": file_path or "",
            "title": title,
            "artist": artist,
            "album": album,
            "length_sec": length_sec,
            "art_url": art_url,
            "track_id": track_id,
        }

    # 1. Comprobación instantánea de carátula pre-cachead en disco (0ms I/O extra)
    cache_path = os.path.join(CACHE_DIR, f"{track_id}.jpg")
    if os.path.exists(cache_path):
        art_url = f"file://{cache_path}"

    try:
        if HAS_TINYTAG:
            try:
                tag = TinyTag.get(file_path)
                if tag:
                    if tag.title and tag.title.strip():
                        title = tag.title.strip()
                    if tag.artist and tag.artist.strip():
                        artist = tag.artist.strip()
                    if tag.album and tag.album.strip():
                        album = tag.album.strip()
                    if tag.duration:
                        length_sec = int(tag.duration)
            except Exception:
                pass

        if HAS_MUTAGEN and (length_sec == 0 or artist in (UNKNOWN_ARTIST, LOADING_METADATA) or title == base_name):
            try:
                audio = mutagen.File(file_path)
                if audio is not None:
                    if length_sec == 0 and getattr(audio.info, "length", 0):
                        length_sec = int(audio.info.length)
                    tags = getattr(audio, "tags", None)
                    if tags is None and hasattr(audio, "get"):
                        tags = audio

                    if tags is not None:
                        if title == base_name or not title:
                            for key in ("title", "TITLE", "Title", "TIT2", "tracktitle"):
                                value = tags.get(key)
                                if value:
                                    title = str(value[0]).strip() if isinstance(value, list) else str(value).strip()
                                    break
                        if artist in (UNKNOWN_ARTIST, LOADING_METADATA):
                            for key in ("artist", "ARTIST", "Artist", "TPE1", "performer", "PERFORMER", "composer", "author"):
                                value = tags.get(key)
                                if value:
                                    artist = str(value[0]).strip() if isinstance(value, list) else str(value).strip()
                                    break
                        if album in (UNKNOWN_ALBUM, ""):
                            for key in ("album", "ALBUM", "Album", "TALB"):
                                value = tags.get(key)
                                if value:
                                    album = str(value[0]).strip() if isinstance(value, list) else str(value).strip()
                                    break
            except Exception:
                pass

        if not artist or artist in (UNKNOWN_ARTIST, LOADING_METADATA):
            if " - " in base_name:
                artist, guessed_title = base_name.split(" - ", 1)
                artist = artist.strip()
                if title == base_name:
                    title = guessed_title.strip()
            else:
                artist = UNKNOWN_ARTIST

        if not art_url:
            try:
                art_url = extract_cover_art(file_path, track_id)
            except Exception:
                art_url = ""

        ext = os.path.splitext(file_path)[1].lower()
        if length_sec == 0 and ext in VIDEO_EXTENSIONS:
            try:
                import subprocess
                res = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path],
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=2
                )
                val = float(res.stdout.strip())
                if val > 0:
                    length_sec = int(val)
            except Exception:
                pass
    except Exception as e:
        print(f"[LibraryManager] Error general leyendo metadatos de {file_path}: {e}")

    file_mtime = 0.0
    if file_path and os.path.exists(file_path):
        try:
            st = os.stat(file_path)
            file_mtime = max(st.st_mtime, st.st_ctime)
        except Exception:
            pass

    return {
        "file_path": file_path,
        "title": title,
        "artist": artist,
        "album": album,
        "length_sec": length_sec,
        "art_url": art_url,
        "track_id": track_id,
        "file_mtime": file_mtime,
        "added_at": file_mtime,
    }


def scan_music_folder_fast(folder_path: str) -> List[Dict[str, Any]]:
    """Escanea rápidamente rutas de archivos de audio sin leer metadatos pesados."""
    tracks = []
    if not folder_path or not os.path.exists(folder_path):
        return tracks

    for root, _, files in os.walk(folder_path):
        for filename in sorted(files):
            ext = os.path.splitext(filename)[1].lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue

            full_path = os.path.join(root, filename)
            track_id = get_track_id(full_path)
            base_title = os.path.splitext(filename)[0]
            guessed_artist = UNKNOWN_ARTIST
            guessed_title = base_title
            if " - " in base_title:
                guessed_artist, guessed_title = base_title.split(" - ", 1)
                guessed_artist = guessed_artist.strip()
                guessed_title = guessed_title.strip()

            # Asignar carátula ya existente de inmediato para renderizado instantáneo
            cached_cover = os.path.join(CACHE_DIR, f"{track_id}.jpg")
            art_url = f"file://{cached_cover}" if os.path.exists(cached_cover) else ""

            file_mtime = 0.0
            try:
                st = os.stat(full_path)
                file_mtime = max(st.st_mtime, st.st_ctime)
            except Exception:
                pass

            tracks.append({
                "file_path": full_path,
                "title": guessed_title,
                "artist": guessed_artist,
                "album": UNKNOWN_ALBUM,
                "length_sec": 0,
                "art_url": art_url,
                "track_id": track_id,
                "file_mtime": file_mtime,
                "added_at": file_mtime,
            })

    return tracks


class LibraryScannerThread(QThread):
    """Enriquece metadatos e imágenes de la biblioteca en segundo plano de forma paralela y de alto rendimiento."""

    metadata_updated = pyqtSignal(int, dict)
    scan_completed = pyqtSignal(list)

    def __init__(self, folder_path: str, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.folder_path = folder_path

    def run(self) -> None:
        if not self.folder_path or not os.path.exists(self.folder_path):
            self.scan_completed.emit([])
            return

        file_paths = []
        for root, _, files in os.walk(self.folder_path):
            if self.isInterruptionRequested():
                return
            for filename in sorted(files):
                if os.path.splitext(filename)[1].lower() in SUPPORTED_EXTENSIONS:
                    file_paths.append(os.path.join(root, filename))

        total = len(file_paths)
        if total == 0:
            self.scan_completed.emit([])
            return

        enriched_tracks: List[Optional[Dict[str, Any]]] = [None] * total
        max_workers = min(8, max(2, (os.cpu_count() or 4)))

        from concurrent.futures import ThreadPoolExecutor

        def _worker(idx: int, path: str):
            if self.isInterruptionRequested():
                return idx, None
            meta = read_track_metadata(path)
            return idx, meta

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(_worker, i, p) for i, p in enumerate(file_paths)]
            for future in futures:
                if self.isInterruptionRequested():
                    executor.shutdown(wait=False, cancel_futures=True)
                    return
                try:
                    idx, meta = future.result()
                    if meta is not None:
                        enriched_tracks[idx] = meta
                        try:
                            self.metadata_updated.emit(idx, meta)
                        except RuntimeError:
                            break
                except Exception:
                    pass

        final_tracks = [t for t in enriched_tracks if t is not None]
        try:
            self.scan_completed.emit(final_tracks)
        except RuntimeError:
            pass
