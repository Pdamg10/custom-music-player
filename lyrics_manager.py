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



# ─────────────────────────────────────────────────────────────────────────────
# Transliteración fonética a Romaji (Japonés)
# ─────────────────────────────────────────────────────────────────────────────
_kakasi_instance = None

def get_kakasi():
    """Instancia perezosa (lazy singleton) de pykakasi."""
    global _kakasi_instance
    if _kakasi_instance is None:
        try:
            import pykakasi
            _kakasi_instance = pykakasi.kakasi()
        except Exception:
            _kakasi_instance = None
    return _kakasi_instance


def contains_japanese(text: str) -> bool:
    """Detecta si una cadena contiene caracteres japoneses (Hiragana, Katakana o Kanji)."""
    if not text:
        return False
    return bool(re.search(r'[\u3040-\u309F\u30A0-\u30FF\u31F0-\u31FF\u4E00-\u9FFF]', text))


def to_romaji(text: str) -> str:
    """
    Convierte texto en japonés (Kanji, Hiragana, Katakana) a Romaji (Hepburn).
    Si el texto no contiene caracteres japoneses, retorna cadena vacía para no duplicar filas en la UI.
    """
    if not text or not contains_japanese(text):
        return ""

    k = get_kakasi()
    if k is None:
        return ""

    try:
        res = k.convert(text)
        parts = [item.get("hepburn", "").strip() for item in res if item.get("hepburn", "").strip()]
        line = " ".join(parts)
        # Normalizar espacios alrededor de signos de puntuación occidentales y japoneses
        line = re.sub(r'\s+([,.\?!:\)\]」』])', r'\1', line)
        line = re.sub(r'([\(\[「『])\s+', r'\1', line)
        line = re.sub(r'\s{2,}', ' ', line).strip()
        if line:
            line = line[0].upper() + line[1:]
        return line
    except Exception:
        return ""


def get_cached_lyrics(title: str, artist: str) -> Optional[str]:
    """Obtiene la letra almacenada en la caché local si existe (buscando clave cruda y limpia)."""
    if not title:
        return None

    keys = [(artist, title)]
    clean_t, clean_a = clean_song_metadata(title, artist)
    if (clean_a, clean_t) not in keys:
        keys.append((clean_a, clean_t))

    for a_key, t_key in keys:
        fn = f"{sanitize_filename(a_key)}_{sanitize_filename(t_key)}.lrc"
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

    keys = [(artist, title)]
    clean_t, clean_a = clean_song_metadata(title, artist)
    if (clean_a, clean_t) not in keys:
        keys.append((clean_a, clean_t))

    for a_key, t_key in keys:
        fn = f"{sanitize_filename(a_key)}_{sanitize_filename(t_key)}.lrc"
        cache_file = os.path.join(CACHE_DIR, fn)
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(lyrics_text)
        except Exception:
            pass


def clean_song_metadata(title: str, artist: str = "") -> Tuple[str, str]:
    """
    Normaliza títulos y artistas para búsquedas de letras en LRCLIB y bases de datos.
    Elimina etiquetas de anime, corchetes de video, etiquetas de resolución,
    números de pista al inicio y sufijos de canales de YouTube.
    """
    orig_title = (title or "").strip()
    orig_artist = (artist or "").strip()
    clean_t = orig_title
    clean_a = orig_artist

    # 1. Limpiar sufijos típicos de YouTube en artistas: " - Topic", " Official Channel", etc.
    clean_a = re.sub(r'\s*-\s*topic$', '', clean_a, flags=re.IGNORECASE).strip()
    clean_a = re.sub(r'\s*(?:official\s*(?:channel|audio|video)?)$', '', clean_a, flags=re.IGNORECASE).strip()

    # 2. Eliminar corchetes japoneses y decorativos: 【MV】, 【PV】, 〖...〗, 〔...〕, ［...］
    clean_t = re.sub(r'【[^】]*】', ' ', clean_t)
    clean_t = re.sub(r'〖[^〗]*〗', ' ', clean_t)
    clean_t = re.sub(r'〔[^〕]*〕', ' ', clean_t)
    clean_t = re.sub(r'［[^］]*］', ' ', clean_t)

    # 3. Eliminar etiquetas de paréntesis y corchetes estándar (video, audio, resoluciones, anime tags)
    bracket_patterns = [
        r'\((?:official|audio|video|lyric|lyrics|letra|traducida|remix|remaster|hd|4k|1080p|720p|hq|subtitulada|sub\b|sub\s+español|eng\s+sub|music\s+video|visualizer|clip|video\s+oficial|official\s+audio|official\s+video|tv\s*size|tv\s*ver|tv\s*edit|short\s*ver|full\s*ver|op\b|ed\b|ost\b|opening|ending|theme|mad\b|amv\b|cover|off\s*vocal|instrumental|\d{4}\s*remaster)[^\)]*\)',
        r'\[(?:official|audio|video|lyric|lyrics|letra|traducida|remix|remaster|hd|4k|1080p|720p|hq|subtitulada|sub\b|sub\s+español|eng\s+sub|music\s+video|visualizer|clip|video\s+oficial|official\s+audio|official\s+video|tv\s*size|tv\s*ver|tv\s*edit|short\s*ver|full\s*ver|op\b|ed\b|ost\b|opening|ending|theme|mad\b|amv\b|cover|off\s*vocal|instrumental|\d{4}\s*remaster)[^\]]*\]',
    ]
    for pat in bracket_patterns:
        clean_t = re.sub(pat, ' ', clean_t, flags=re.IGNORECASE)

    # 4. Detectar títulos encerrados en comillas japonesas: Artista 「Canción」 o 「Canción」
    quote_match = re.search(r'[「『]([^」』]+)[」』]', clean_t)
    if quote_match:
        prefix = clean_t[:quote_match.start()].strip()
        song_inside = quote_match.group(1).strip()
        if prefix and (not clean_a or clean_a.lower() in ('online', 'desconocido', 'youtube', 'unknown', 'various artists', 'artista desconocido')):
            clean_a = prefix
        clean_t = song_inside

    # 5. Separadores de Artista - Título cuando el artista no está definido o es genérico
    if not clean_a or clean_a.lower() in ('online', 'desconocido', 'youtube', 'unknown', 'various artists', 'artista desconocido'):
        for sep in [' - ', ' – ', ' — ', ' / ', '／', '｜', ' | ']:
            if sep in clean_t:
                parts = clean_t.split(sep, 1)
                clean_a = parts[0].strip()
                clean_t = parts[1].strip()
                break

    # 6. Desenvolver comillas si envolvían el título
    if clean_t.startswith(('「', '『', '"', "'")) and clean_t.endswith(('」', '』', '"', "'")):
        clean_t = clean_t[1:-1].strip()

    # 7. Quitar numeración de pista al inicio: "01. ", "01 - ", "01_ "
    clean_t = re.sub(r'^\s*\d{1,3}[\.\-_:\s]+\s*', '', clean_t).strip()

    # 8. Limpieza de espacios redundantes
    clean_t = re.sub(r'\s{2,}', ' ', clean_t).strip()
    clean_a = re.sub(r'\s{2,}', ' ', clean_a).strip()

    return clean_t or orig_title, clean_a or orig_artist


def fetch_online_lyrics(title: str, artist: str, album: str = "", duration_sec: int = 0) -> Optional[str]:
    """
    Consulta la API de LRCLIB con estrategias múltiples y clasificación de candidatos.
    Prioriza letras sincronizadas (syncedLyrics) cercanas a la duración de la pista.
    """
    if not title or title.strip() in ("Desconocido", "Sin reproducción", ""):
        return None

    clean_t, clean_a = clean_song_metadata(title, artist)
    user_agent = "CustomMusicPlayer/1.1 (https://github.com/Pdamg10/custom-music-player)"
    best_plain: Optional[str] = None

    # Estrategia 1: Endpoint directo /api/get
    # Probar con y sin duración (evita error 404 si la pista difiere por pocos segundos)
    get_attempts = []
    if clean_t:
        a_param = clean_a if clean_a and clean_a.lower() not in ("online", "desconocido", "youtube", "unknown", "various artists") else ""
        alb_param = album if album and album not in ("Desconocido", "Álbum Desconocido", "Online Stream") else ""

        if duration_sec > 0:
            get_attempts.append({"track_name": clean_t, "artist_name": a_param, "album_name": alb_param, "duration": int(duration_sec)})
        get_attempts.append({"track_name": clean_t, "artist_name": a_param, "album_name": alb_param})

    for p in get_attempts:
        filtered_params = {k: v for k, v in p.items() if v}
        url_get = f"https://lrclib.net/api/get?{urllib.parse.urlencode(filtered_params)}"
        try:
            req = urllib.request.Request(url_get, headers={"User-Agent": user_agent})
            with urllib.request.urlopen(req, timeout=4) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    synced = (data.get("syncedLyrics") or "").strip()
                    if synced:
                        save_cached_lyrics(title, artist, synced)
                        return synced
                    plain = (data.get("plainLyrics") or "").strip()
                    if plain and not best_plain:
                        best_plain = plain
        except Exception:
            pass

    # Estrategia 2: Endpoint de búsqueda /api/search con clasificación inteligente
    search_queries = []
    valid_artist = clean_a if clean_a and clean_a.lower() not in ("online", "desconocido", "youtube", "unknown", "various artists") else ""

    if valid_artist and clean_t:
        search_queries.append(f"{valid_artist} {clean_t}".strip())
    if clean_t:
        search_queries.append(clean_t)
    if (title or "").strip() and (title or "").strip() not in search_queries:
        search_queries.append((title or "").strip())

    seen_queries = set()
    for q in search_queries:
        if not q or q in seen_queries:
            continue
        seen_queries.add(q)

        url_search = f"https://lrclib.net/api/search?{urllib.parse.urlencode({'q': q})}"
        try:
            req = urllib.request.Request(url_search, headers={"User-Agent": user_agent})
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    results = json.loads(resp.read().decode("utf-8"))
                    if isinstance(results, list) and results:
                        # Filtrar candidatos con letras sincronizadas
                        synced_candidates = [r for r in results if (r.get("syncedLyrics") or "").strip()]
                        if synced_candidates:
                            if duration_sec > 0:
                                synced_candidates.sort(
                                    key=lambda x: abs(float(x.get("duration") or 0) - duration_sec) if x.get("duration") else 9999
                                )
                            chosen = synced_candidates[0].get("syncedLyrics", "").strip()
                            if chosen:
                                save_cached_lyrics(title, artist, chosen)
                                return chosen

                        # Si no hay sincronizados, guardar el mejor texto plano
                        if not best_plain:
                            plain_candidates = [r for r in results if (r.get("plainLyrics") or "").strip()]
                            if plain_candidates:
                                if duration_sec > 0:
                                    plain_candidates.sort(
                                        key=lambda x: abs(float(x.get("duration") or 0) - duration_sec) if x.get("duration") else 9999
                                    )
                                best_plain = plain_candidates[0].get("plainLyrics", "").strip()
        except Exception:
            pass

    if best_plain:
        save_cached_lyrics(title, artist, best_plain)
        return best_plain

    # Estrategia 3 (Fallback): Consultar letras.com si el motor original (LRCLIB) no encontró la letra
    try:
        from letras_provider import fetch_letras_com_lyrics
        letras_lyrics = fetch_letras_com_lyrics(title, artist)
        if letras_lyrics and letras_lyrics.strip():
            save_cached_lyrics(title, artist, letras_lyrics.strip())
            return letras_lyrics.strip()
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
        duration_sec = self.track_meta.get("length_sec", 0) or self.track_meta.get("duration", 0)

        raw_lyrics = None
        is_synced = False
        parsed_lines = []

        # 1. Intentar offline directo (archivos .lrc o tags embebidos)
        offline_text = get_offline_lyrics(file_path)
        if offline_text:
            parsed_lines, is_synced = parse_lrc_content(offline_text)
            if is_synced and parsed_lines:
                raw_lyrics = offline_text

        # 2. Si no hay offline sincronizada, buscar en caché local
        if not is_synced:
            cached_text = get_cached_lyrics(title, artist)
            if cached_text:
                c_lines, c_synced = parse_lrc_content(cached_text)
                if c_synced and c_lines:
                    raw_lyrics = cached_text
                    parsed_lines = c_lines
                    is_synced = True
                elif not raw_lyrics:
                    raw_lyrics = cached_text
                    parsed_lines = c_lines
                    is_synced = False

        # 3. Si aún no tenemos sincronización, consultar online (LRCLIB)
        # Permite elevar canciones con texto plano a letras sincronizadas si están disponibles
        if not is_synced:
            online_text = fetch_online_lyrics(title, artist, album, duration_sec)
            if online_text:
                o_lines, o_synced = parse_lrc_content(online_text)
                if o_synced and o_lines:
                    raw_lyrics = online_text
                    parsed_lines = o_lines
                    is_synced = True
                elif not raw_lyrics and o_lines:
                    raw_lyrics = online_text
                    parsed_lines = o_lines
                    is_synced = False

        # 4. Fallback a texto plano offline si online no tuvo resultado y no teníamos nada
        if not raw_lyrics and offline_text:
            raw_lyrics = offline_text
            parsed_lines, is_synced = parse_lrc_content(offline_text)

        if self.isInterruptionRequested():
            return

        if raw_lyrics and parsed_lines:
            self.lyrics_loaded.emit(raw_lyrics, parsed_lines, is_synced)
        else:
            self.lyrics_not_found.emit()
