import os
import re
import json
import urllib.request
import urllib.parse
from typing import Optional, List, Dict, Any, Tuple
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from config_manager import get_platform_base_dir

# Directorio de caché local para letras descargadas
CACHE_DIR = get_platform_base_dir("cache", "lyrics")
os.makedirs(CACHE_DIR, exist_ok=True)

class LyricLine:
    """Representa una línea individual de letra sincronizada o plana."""
    __slots__ = ("time_ms", "text")

    def __init__(self, time_ms: int, text: str) -> None:
        self.time_ms = time_ms  # -1 si no está sincronizada
        self.text = text

    def __repr__(self) -> str:
        return f"LyricLine({self.time_ms}ms, '{self.text}')"


def sanitize_filename(name: str) -> str:
    """Limpia cadenas para usarlas de forma segura como nombre de archivo."""
    return re.sub(r'[\\/*?:"<>|]', "", name).strip().replace(" ", "_").lower()


def parse_lrc_content(lrc_text: str) -> Tuple[List[LyricLine], bool]:
    """
    Parsea texto en formato LRC estándar ([mm:ss.xx] Letra) o texto plano.
    Retorna (lista_de_lineas, es_sincronizada).
    """
    if not lrc_text or not lrc_text.strip():
        return [], False

    # Normalizar retornos de carro y secuencias escapadas
    clean_text = lrc_text.replace('\\r\\n', '\n').replace('\\n', '\n').replace('\r\n', '\n').replace('\r', '\n')
    lines = clean_text.strip().splitlines()
    time_regex = re.compile(r'\[(\d{1,2}):(\d{1,2})(?:[\.:](\d{1,3}))?\]')

    parsed: List[LyricLine] = []
    has_timestamps = False

    for line in lines:
        raw = line.strip()
        if not raw:
            continue

        # Ignorar metadatos de cabecera como [ti:Title], [ar:Artist], etc.
        if re.match(r'^\[(ti|ar|al|au|by|length|offset|re|ve):', raw, re.IGNORECASE):
            continue

        matches = list(time_regex.finditer(raw))
        if matches:
            has_timestamps = True
            # Limpiar los timestamps para extraer solo el texto de la línea
            text = time_regex.sub('', raw).strip()
            for m in matches:
                minutes = int(m.group(1))
                seconds = int(m.group(2))
                ms_part = m.group(3) or "0"
                if len(ms_part) == 1:
                    ms = int(ms_part) * 100
                elif len(ms_part) == 2:
                    ms = int(ms_part) * 10
                else:
                    ms = int(ms_part[:3])

                total_ms = (minutes * 60 + seconds) * 1000 + ms
                parsed.append(LyricLine(total_ms, text))
        else:
            # Línea sin timestamp
            parsed.append(LyricLine(-1, raw))

    if has_timestamps:
        # Ordenar cronológicamente por tiempo
        parsed.sort(key=lambda x: x.time_ms)
        # Filtrar líneas vacías consecutivas iniciales
        return parsed, True
    else:
        return parsed, False


def _clean_raw_text(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    if (text.startswith("['") and text.endswith("']")) or (text.startswith('["') and text.endswith('"]')):
        text = text[2:-2]
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        text = text[1:-1]
    return text.strip()


def get_offline_lyrics(file_path: str) -> Optional[str]:
    """
    Busca letras sin conexión:
    1. Archivos sidecar (.lrc, .txt) en el mismo directorio.
    2. Etiquetas de metadatos embebidas (ID3 USLT/SYLT, FLAC/OGG LYRICS, MP4 covr/lyr).
    """
    if not file_path or not os.path.exists(file_path):
        return None

    dir_name = os.path.dirname(file_path)
    base_name = os.path.splitext(os.path.basename(file_path))[0]

    # 1. Buscar archivo sidecar .lrc o .txt con el mismo nombre en la carpeta
    for ext in (".lrc", ".LRC", ".txt", ".TXT", ".lyrics"):
        sidecar = os.path.join(dir_name, base_name + ext)
        if os.path.exists(sidecar):
            try:
                for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
                    try:
                        with open(sidecar, "r", encoding=enc) as f:
                            content = f.read().strip()
                            if content:
                                return _clean_raw_text(content)
                    except UnicodeDecodeError:
                        continue
            except Exception:
                pass

    # 2. Buscar en etiquetas embebidas con Mutagen
    try:
        import mutagen
        audio = mutagen.File(file_path)
        if audio is not None and getattr(audio, "tags", None):
            tags = audio.tags
            # ID3 (MP3)
            for key in tags.keys():
                if key.startswith("USLT") or key.startswith("SYLT") or "LYRICS" in key.upper():
                    val = tags[key]
                    text = getattr(val, "text", str(val))
                    if isinstance(text, list):
                        text = "\n".join(str(t) for t in text)
                    if text and text.strip():
                        return _clean_raw_text(text)

            # FLAC / Vorbis / Ogg / MP4
            for l_key in ("lyrics", "LYRICS", "unsyncedlyrics", "UNSYNCEDLYRICS", "\xa9lyr"):
                if l_key in tags:
                    val = tags[l_key]
                    if isinstance(val, list):
                        text = "\n".join(str(v) for v in val)
                    else:
                        text = str(val)
                    if text and text.strip():
                        return _clean_raw_text(text)
    except Exception:
        pass

    return None


def get_cached_lyrics(title: str, artist: str) -> Optional[str]:
    """Obtiene la letra almacenada en la caché local si existe."""
    if not title:
        return None
    fn = f"{sanitize_filename(artist)}_{sanitize_filename(title)}.lrc"
    cache_file = os.path.join(CACHE_DIR, fn)
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    return content
        except Exception:
            pass
    return None


def save_cached_lyrics(title: str, artist: str, lyrics_text: str) -> None:
    """Guarda la letra obtenida en la caché local para acceso offline futuro."""
    if not title or not lyrics_text:
        return
    fn = f"{sanitize_filename(artist)}_{sanitize_filename(title)}.lrc"
    cache_file = os.path.join(CACHE_DIR, fn)
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(lyrics_text)
    except Exception:
        pass


def fetch_online_lyrics(title: str, artist: str, album: str = "", duration_sec: int = 0) -> Optional[str]:
    """
    Consulta la API abierta y gratuita de LRCLIB (utilizada en clientes modernos open-source).
    Retorna la letra sincronizada (syncedLyrics) o texto plano (plainLyrics).
    """
    if not title or title.strip() in ("Desconocido", "Sin reproducción", ""):
        return None

    clean_artist = artist if artist not in ("Desconocido", "Artista Desconocido", "Selecciona una canción") else ""

    # 1. Búsqueda directa por get
    params: Dict[str, Any] = {"track_name": title}
    if clean_artist:
        params["artist_name"] = clean_artist
    if album and album not in ("Desconocido", "Álbum Desconocido"):
        params["album_name"] = album
    if duration_sec > 0:
        params["duration"] = int(duration_sec)

    url_get = f"https://lrclib.net/api/get?{urllib.parse.urlencode(params)}"
    try:
        req = urllib.request.Request(url_get, headers={"User-Agent": "CustomMusicPlayer/1.0 (Linux)"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                synced = data.get("syncedLyrics")
                plain = data.get("plainLyrics")
                chosen = synced or plain
                if chosen and chosen.strip():
                    save_cached_lyrics(title, clean_artist, chosen.strip())
                    return chosen.strip()
    except Exception:
        pass

    # 2. Búsqueda de reserva (Search) si get exacto falló
    query = f"{clean_artist} {title}".strip()
    url_search = f"https://lrclib.net/api/search?{urllib.parse.urlencode({'q': query})}"
    try:
        req = urllib.request.Request(url_search, headers={"User-Agent": "CustomMusicPlayer/1.0 (Linux)"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            if resp.status == 200:
                results = json.loads(resp.read().decode("utf-8"))
                if isinstance(results, list) and results:
                    best_match = None
                    for r in results:
                        if r.get("syncedLyrics"):
                            best_match = r.get("syncedLyrics")
                            break
                        elif not best_match and r.get("plainLyrics"):
                            best_match = r.get("plainLyrics")

                    if best_match and best_match.strip():
                        save_cached_lyrics(title, clean_artist, best_match.strip())
                        return best_match.strip()
    except Exception:
        pass

    return None


class LyricsFetcherThread(QThread):
    """Hilo secundario para buscar y cargar letras sin congelar la interfaz de usuario."""
    lyrics_loaded = pyqtSignal(str, list, bool)  # raw_text, parsed_lines, is_synced
    lyrics_not_found = pyqtSignal()

    def __init__(self, track_meta: dict, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.track_meta = dict(track_meta or {})

    def run(self) -> None:
        file_path = self.track_meta.get("file_path") or self.track_meta.get("path") or ""
        title = self.track_meta.get("title", "")
        artist = self.track_meta.get("artist", "")
        album = self.track_meta.get("album", "")
        duration_sec = self.track_meta.get("length_sec", 0)

        raw_lyrics = None
        is_synced = False
        parsed_lines = []

        # 1. Intentar offline directo
        offline_text = get_offline_lyrics(file_path)
        if offline_text:
            parsed_lines, is_synced = parse_lrc_content(offline_text)
            if is_synced and parsed_lines:
                raw_lyrics = offline_text

        # 2. Si no hay offline sincronizada, buscar en caché local
        if not raw_lyrics:
            cached_text = get_cached_lyrics(title, artist)
            if cached_text:
                c_lines, c_synced = parse_lrc_content(cached_text)
                if c_synced or not offline_text:
                    raw_lyrics = cached_text
                    parsed_lines = c_lines
                    is_synced = c_synced

        # 3. Si aún no tenemos sincronización, consultar online (LRCLIB)
        if not is_synced:
            online_text = fetch_online_lyrics(title, artist, album, duration_sec)
            if online_text:
                o_lines, o_synced = parse_lrc_content(online_text)
                if o_synced or not raw_lyrics:
                    raw_lyrics = online_text
                    parsed_lines = o_lines
                    is_synced = o_synced

        # 4. Fallback a texto plano offline si online no tuvo resultado
        if not raw_lyrics and offline_text:
            raw_lyrics = offline_text
            parsed_lines, is_synced = parse_lrc_content(offline_text)

        if self.isInterruptionRequested():
            return

        if raw_lyrics and parsed_lines:
            self.lyrics_loaded.emit(raw_lyrics, parsed_lines, is_synced)
        else:
            self.lyrics_not_found.emit()
