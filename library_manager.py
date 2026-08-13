import os
import hashlib
import tempfile
from typing import List, Dict, Any, Optional
from PyQt6.QtCore import QThread, pyqtSignal, QObject

try:
    import mutagen
    from mutagen.id3 import ID3, APIC
    from mutagen.flac import FLAC, Picture
    from mutagen.mp4 import MP4, MP4Cover
    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False

try:
    from tinytag import TinyTag
    HAS_TINYTAG = True
except ImportError:
    HAS_TINYTAG = False

CACHE_DIR = os.path.expanduser("~/.config/custom-music-player/covers")
AUDIO_EXTENSIONS = {".mp3", ".flac", ".wav", ".m4a", ".ogg", ".opus", ".aac", ".wma"}

def ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)

def get_track_id(file_path: str) -> str:
    return hashlib.md5(file_path.encode("utf-8")).hexdigest()

def extract_cover_art(file_path: str, track_id: str) -> str:
    """Extrae la carátula incrustada del archivo de audio y la guarda en el directorio de cache."""
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
                for tag in tags.values():
                    if isinstance(tag, APIC):
                        image_data = tag.data
                        break
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
                covers = audio.tags.get("covr")
                if covers:
                    image_data = bytes(covers[0])
            except Exception:
                pass
        else:
            try:
                audio = mutagen.File(file_path)
                if audio and hasattr(audio, "tags") and audio.tags:
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
                if img.mode != "RGB":
                    img = img.convert("RGB")
                img.save(cache_path, format="JPEG", quality=85)
            except Exception:
                with open(cache_path, "wb") as f:
                    f.write(image_data)
            return f"file://{cache_path}"
    except Exception as e:
        print(f"[LibraryManager] Error extrayendo carátula de {file_path}: {e}")

    return ""

def read_track_metadata(file_path: str) -> Dict[str, Any]:
    """Lee metadatos de un archivo de audio de forma robusta con manejo de errores."""
    track_id = get_track_id(file_path)
    title = os.path.splitext(os.path.basename(file_path))[0]
    artist = "Artista desconocido"
    album = "Álbum desconocido"
    length_sec = 0
    art_url = ""

    # 1. Intentar con tinytag
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

    # 2. Intentar con mutagen si duracion/metadatos faltan
    if HAS_MUTAGEN and (length_sec == 0 or artist == "Artista desconocido"):
        try:
            audio = mutagen.File(file_path)
            if audio is not None:
                if length_sec == 0 and hasattr(audio.info, "length") and audio.info.length:
                    length_sec = int(audio.info.length)
                tags = getattr(audio, "tags", {}) or {}
                if isinstance(tags, dict) or hasattr(tags, "get"):
                    if title == os.path.splitext(os.path.basename(file_path))[0]:
                        t = tags.get("title") or tags.get("TIT2")
                        if t:
                            title = str(t[0]) if isinstance(t, list) else str(t)
                    if artist == "Artista desconocido":
                        a = tags.get("artist") or tags.get("TPE1")
                        if a:
                            artist = str(a[0]) if isinstance(a, list) else str(a)
                    if album == "Álbum desconocido":
                        al = tags.get("album") or tags.get("TALB")
                        if al:
                            album = str(al[0]) if isinstance(al, list) else str(al)
        except Exception:
            pass

    # Extraer carátula si mutagen está disponible
    art_url = extract_cover_art(file_path, track_id)

    return {
        "file_path": file_path,
        "title": title,
        "artist": artist,
        "album": album,
        "length_sec": length_sec,
        "art_url": art_url,
        "track_id": track_id
    }

def scan_music_folder_fast(folder_path: str) -> List[Dict[str, Any]]:
    """Escaneo ultrarrápido de rutas de archivos de audio (retorna en milisegundos)."""
    tracks = []
    if not folder_path or not os.path.exists(folder_path):
        return tracks

    for root, _, files in os.walk(folder_path):
        for f in sorted(files):
            ext = os.path.splitext(f)[1].lower()
            if ext in AUDIO_EXTENSIONS:
                full_path = os.path.join(root, f)
                track_id = get_track_id(full_path)
                base_title = os.path.splitext(f)[0]
                tracks.append({
                    "file_path": full_path,
                    "title": base_title,
                    "artist": "Cargando metadatos...",
                    "album": "Álbum desconocido",
                    "length_sec": 0,
                    "art_url": "",
                    "track_id": track_id
                })

    return tracks

class LibraryScannerThread(QThread):
    """Hilo secundario para escanear y enriquecer metadatos e imágenes en segundo plano."""
    metadata_updated = pyqtSignal(int, dict) # (idx, track_dict)
    scan_completed = pyqtSignal(list)       # Lista completa enriquecida

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
            for f in sorted(files):
                ext = os.path.splitext(f)[1].lower()
                if ext in AUDIO_EXTENSIONS:
                    file_paths.append(os.path.join(root, f))

        enriched_tracks = []
        for idx, path in enumerate(file_paths):
            if self.isInterruptionRequested():
                return
            meta = read_track_metadata(path)
            enriched_tracks.append(meta)
            self.metadata_updated.emit(idx, meta)

        self.scan_completed.emit(enriched_tracks)
