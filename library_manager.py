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

UNKNOWN_ARTIST = "Artista desconocido"
UNKNOWN_ALBUM = "Álbum desconocido"
LOADING_METADATA = "Cargando metadatos..."


def ensure_cache_dir() -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)


def get_track_id(file_path: str) -> str:
    return hashlib.md5(file_path.encode("utf-8")).hexdigest()


def extract_cover_art(file_path: str, track_id: str) -> str:
    """Extrae la carátula incrustada y la guarda en la caché local."""
    ensure_cache_dir()
    cache_path = os.path.join(CACHE_DIR, f"{track_id}.jpg")
    if os.path.exists(cache_path):
        return f"file://{cache_path}"

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
            try:
                from PIL import Image
                import io
                img = Image.open(io.BytesIO(image_data))
                if img.width > 600 or img.height > 600:
                    img.thumbnail((600, 600))
                fmt = "PNG" if img.mode in ("RGBA", "LA", "P") else "JPEG"
                if fmt == "JPEG" and img.mode != "RGB":
                    img = img.convert("RGB")
                img.save(cache_path, format=fmt)
            except Exception:
                with open(cache_path, "wb") as f:
                    f.write(image_data)
            return f"file://{cache_path}"
    except Exception as e:
        print(f"[LibraryManager] Error extrayendo carátula de {file_path}: {e}")

    return ""


def read_track_metadata(file_path: str) -> Dict[str, Any]:
    """Lee metadatos con fallbacks entre TinyTag, Mutagen y el nombre del archivo."""
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

        try:
            art_url = extract_cover_art(file_path, track_id)
        except Exception:
            art_url = ""
    except Exception as e:
        print(f"[LibraryManager] Error general leyendo metadatos de {file_path}: {e}")

    return {
        "file_path": file_path,
        "title": title,
        "artist": artist,
        "album": album,
        "length_sec": length_sec,
        "art_url": art_url,
        "track_id": track_id,
    }


def scan_music_folder_fast(folder_path: str) -> List[Dict[str, Any]]:
    """Escanea rápidamente rutas de archivos de audio sin leer metadatos pesados."""
    tracks = []
    if not folder_path or not os.path.exists(folder_path):
        return tracks

    for root, _, files in os.walk(folder_path):
        for filename in sorted(files):
            ext = os.path.splitext(filename)[1].lower()
            if ext not in AUDIO_EXTENSIONS:
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

            tracks.append({
                "file_path": full_path,
                "title": guessed_title,
                "artist": guessed_artist,
                "album": UNKNOWN_ALBUM,
                "length_sec": 0,
                "art_url": "",
                "track_id": track_id,
            })

    return tracks


class LibraryScannerThread(QThread):
    """Enriquece metadatos e imágenes de la biblioteca en segundo plano."""

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
                if os.path.splitext(filename)[1].lower() in AUDIO_EXTENSIONS:
                    file_paths.append(os.path.join(root, filename))

        enriched_tracks = []
        for idx, path in enumerate(file_paths):
            if self.isInterruptionRequested():
                return
            meta = read_track_metadata(path)
            enriched_tracks.append(meta)
            try:
                self.metadata_updated.emit(idx, meta)
            except RuntimeError:
                break

        try:
            self.scan_completed.emit(enriched_tracks)
        except RuntimeError:
            pass
