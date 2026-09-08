import os
import re
import json
import urllib.request
from typing import Optional, Dict, Any, Callable

from PyQt6.QtCore import QThread, pyqtSignal

try:
    import yt_dlp
    HAS_YTDL = True
except ImportError:
    yt_dlp = None
    HAS_YTDL = False


def is_supported_media_url(url: str) -> bool:
    """Verifica si la cadena de texto corresponde a un enlace compatible o consulta de búsqueda."""
    if not url or not isinstance(url, str):
        return False
    u = url.strip()
    if len(u) < 2:
        return False

    # Enlaces de Spotify (soporta intl-es, intl-xx, track, album, playlist, URI spotify:track:...)
    if "spotify.com/" in u.lower() or u.lower().startswith("spotify:"):
        return True

    # Enlaces de YouTube (soporta www., m., music., youtu.be, shorts, etc.)
    if any(d in u.lower() for d in ("youtube.com/", "youtu.be/", "music.youtube.com/")):
        return True

    # Enlaces de SoundCloud
    if "soundcloud.com/" in u.lower():
        return True

    # Enlaces directos a archivos multimedia
    if any(u.lower().split("?")[0].endswith(ext) for ext in (".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wav", ".mp4", ".webm", ".mkv")):
        return True

    # Cualquier URL web http/https
    if u.lower().startswith("http://") or u.lower().startswith("https://"):
        return True

    # Si es texto (búsqueda directa de canción o artista), se admite para buscar en YouTube
    return len(u) >= 3


def detect_url_provider(url: str) -> str:
    """Identifica el proveedor del enlace proporcionado."""
    if not url:
        return "unknown"
    u = url.lower().strip()
    if "spotify.com" in u or u.startswith("spotify:"):
        return "spotify"
    elif any(d in u for d in ("youtube.com", "youtu.be")):
        return "youtube"
    elif "soundcloud.com" in u:
        return "soundcloud"
    elif any(u.split("?")[0].endswith(ext) for ext in (".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wav")):
        return "direct"
    elif u.startswith("http://") or u.startswith("https://"):
        return "web"
    return "search"


def fetch_spotify_metadata(url: str) -> Optional[Dict[str, Any]]:
    """Extrae metadatos precisos (Título, Artista, Carátula HD, Duración) de Spotify mediante scraping crawler y fallback oEmbed."""
    try:
        clean_url = url.split("?")[0].strip()
        m = re.search(r'spotify\.com/(?:intl-[a-z]{2}/)?(track|album|playlist)/([a-zA-Z0-9]+)', clean_url)
        if not m:
            m2 = re.search(r'spotify:(track|album|playlist):([a-zA-Z0-9]+)', clean_url)
            if m2:
                clean_url = f"https://open.spotify.com/{m2.group(1)}/{m2.group(2)}"
        else:
            clean_url = f"https://open.spotify.com/{m.group(1)}/{m.group(2)}"

        title = ""
        artist = ""
        art_url = ""
        duration = 0

        # 1. Intentar scraping de etiquetas OpenGraph con User-Agent de crawler
        try:
            req = urllib.request.Request(
                clean_url,
                headers={"User-Agent": "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)"}
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                title_m = re.search(r'<meta property="og:title" content="([^"]+)"', html)
                artist_m = re.search(r'<meta property="music:musician_description" content="([^"]+)"', html)
                desc_m = re.search(r'<meta property="og:description" content="([^"]+)"', html)
                art_m = re.search(r'<meta property="og:image" content="([^"]+)"', html)
                dur_m = re.search(r'<meta property="music:duration" content="([^"]+)"', html)

                if title_m:
                    title = title_m.group(1).strip()
                if artist_m:
                    artist = artist_m.group(1).strip()
                elif desc_m:
                    parts = [p.strip() for p in desc_m.group(1).split("·")]
                    if parts:
                        artist = parts[0]
                if art_m:
                    art_url = art_m.group(1).strip()
                if dur_m and dur_m.group(1).isdigit():
                    duration = int(dur_m.group(1))
        except Exception:
            pass

        # 2. Fallback a oEmbed si faltó título o carátula
        if not title or not art_url:
            try:
                oembed_endpoint = f"https://open.spotify.com/oembed?url={urllib.request.quote(clean_url)}"
                req_oe = urllib.request.Request(
                    oembed_endpoint,
                    headers={"User-Agent": "Mozilla/5.0"}
                )
                with urllib.request.urlopen(req_oe, timeout=5.0) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    if not title:
                        raw_t = data.get("title", "")
                        if "by " in raw_t:
                            parts = raw_t.split("by ")
                            title = parts[0].strip()
                            if not artist:
                                artist = parts[1].strip()
                        else:
                            title = raw_t.strip()
                    if not art_url:
                        art_url = data.get("thumbnail_url", "")
            except Exception:
                pass

        if title:
            return {
                "title": title,
                "artist": artist or "Spotify",
                "art_url": art_url,
                "length_sec": duration,
                "duration": duration,
                "source_url": url,
            }
    except Exception as e:
        print(f"[OnlineStreamManager] Error extrayendo metadatos de Spotify: {e}")
    return None


def extract_online_stream_info(url: str, progress_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
    """
    Extrae la URL de streaming directo y los metadatos para reproducción online instantánea.
    Soporta enlaces de YouTube, Spotify, SoundCloud y búsquedas directas.
    """
    if not HAS_YTDL:
        raise RuntimeError("La librería 'yt-dlp' no está instalada. Ejecute: pip install yt-dlp")

    url = url.strip()
    provider = detect_url_provider(url)

    target_query = url
    spotify_meta: Optional[Dict[str, Any]] = None

    if provider == "spotify":
        if progress_callback:
            progress_callback("Obteniendo metadatos de Spotify...")
        spotify_meta = fetch_spotify_metadata(url)
        if spotify_meta and spotify_meta.get("title"):
            target_query = f"ytsearch1:{spotify_meta['title']} {spotify_meta.get('artist', '')} audio"
        else:
            target_query = f"ytsearch1:{url}"
    elif provider == "search":
        target_query = f"ytsearch1:{url} audio"

    if progress_callback:
        progress_callback("Conectando con el servidor de audio...")

    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio/best",
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
        "noplaylist": True,
        "socket_timeout": 15,
        "retries": 10,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"],
            }
        },
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(target_query, download=False)
        if "entries" in info and info["entries"]:
            entry = info["entries"][0]
        else:
            entry = info

        stream_url = entry.get("url", "")
        if not stream_url:
            raise RuntimeError("No se pudo obtener la URL de streaming de audio.")

        raw_title = (spotify_meta.get("title") if spotify_meta else None) or entry.get("title") or "Pista Online"
        raw_artist = (spotify_meta.get("artist") if spotify_meta else None) or entry.get("artist") or entry.get("uploader") or "Online"
        
        from lyrics_manager import clean_song_metadata
        title, artist = clean_song_metadata(raw_title, raw_artist)

        art_url = (spotify_meta.get("art_url") if spotify_meta else None) or entry.get("thumbnail") or ""
        duration = int(entry.get("duration") or (spotify_meta.get("duration") if spotify_meta else 0) or 0)
        video_id = entry.get("id") or "stream"

        return {
            "track_id": f"stream_{video_id}",
            "file_path": stream_url,
            "title": title,
            "artist": artist,
            "album": entry.get("album") or "Online Stream",
            "length_sec": duration,
            "duration": duration,
            "art_url": art_url,
            "is_online_stream": True,
            "source_url": url,
            "provider": provider,
        }


def download_media_offline(
    url: str,
    output_dir: str,
    format_type: str = "audio",
    progress_callback: Optional[Callable[[str, float], None]] = None
) -> Dict[str, Any]:
    """
    Descarga el audio o video de un enlace de YouTube o Spotify y lo guarda en disco local
    con etiquetas incrustadas y carátula del álbum.
    """
    if not HAS_YTDL:
        raise RuntimeError("La librería 'yt-dlp' no está instalada. Ejecute: pip install yt-dlp")

    os.makedirs(output_dir, exist_ok=True)
    provider = detect_url_provider(url)

    target_query = url
    spotify_meta: Optional[Dict[str, Any]] = None

    if provider == "spotify":
        if progress_callback:
            progress_callback("Obteniendo metadatos de Spotify...", 0.10)
        spotify_meta = fetch_spotify_metadata(url)
        if spotify_meta and spotify_meta.get("title"):
            target_query = f"ytsearch1:{spotify_meta['title']} {spotify_meta.get('artist', '')} audio"
        else:
            target_query = f"ytsearch1:{url}"
    elif provider == "search":
        target_query = f"ytsearch1:{url} audio"

    downloaded_files = []

    def _ytdl_hook(d):
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 1
            downloaded = d.get("downloaded_bytes", 0)
            percent = downloaded / float(total) if total > 0 else 0.5
            if progress_callback:
                lbl = "video" if format_type == "video" else "audio"
                progress_callback(f"Descargando {lbl}... {int(percent * 100)}%", 0.15 + percent * 0.70)
        elif d.get("status") == "finished":
            fn = d.get("filename")
            if fn:
                downloaded_files.append(fn)
            if progress_callback:
                progress_callback("Procesando medio y carátula...", 0.90)

    outtmpl = os.path.join(output_dir, "%(title)s.%(ext)s")
    common_extractor_args = {
        "youtube": {
            "player_client": ["android", "web"],
        }
    }

    if format_type == "video":
        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": outtmpl,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "socket_timeout": 20,
            "retries": 10,
            "extractor_args": common_extractor_args,
            "progress_hooks": [_ytdl_hook],
            "merge_output_format": "mp4",
            "postprocessors": [
                {
                    "key": "FFmpegMetadata",
                    "add_metadata": True,
                },
                {
                    "key": "EmbedThumbnail",
                },
            ],
            "writethumbnail": True,
        }
    else:
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "socket_timeout": 20,
            "retries": 10,
            "extractor_args": common_extractor_args,
            "progress_hooks": [_ytdl_hook],
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "320",
                },
                {
                    "key": "FFmpegMetadata",
                    "add_metadata": True,
                },
                {
                    "key": "EmbedThumbnail",
                },
            ],
            "writethumbnail": True,
        }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(target_query, download=True)
        if "entries" in info and info["entries"]:
            entry = info["entries"][0]
        else:
            entry = info

        title = entry.get("title", "Descarga")
        target_ext = ".mp4" if format_type == "video" else ".mp3"
        expected_path = os.path.join(output_dir, f"{title}{target_ext}")
        
        final_path = ""
        if os.path.exists(expected_path):
            final_path = expected_path
        else:
            candidates = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith(target_ext)]
            if candidates:
                final_path = max(candidates, key=os.path.getmtime)
            elif downloaded_files:
                final_path = downloaded_files[0]

        if not final_path or not os.path.exists(final_path):
            raise RuntimeError("No se pudo localizar el archivo descargado.")

        if progress_callback:
            progress_callback("¡Descarga completada!", 1.0)

        from library_manager import read_track_metadata
        track_meta = read_track_metadata(final_path)
        if spotify_meta:
            if spotify_meta.get("title"):
                track_meta["title"] = spotify_meta["title"]
            if spotify_meta.get("artist"):
                track_meta["artist"] = spotify_meta["artist"]

        from lyrics_manager import clean_song_metadata
        t_clean, a_clean = clean_song_metadata(track_meta.get("title", ""), track_meta.get("artist", ""))
        track_meta["title"] = t_clean
        track_meta["artist"] = a_clean

        return track_meta


class LinkResolverWorker(QThread):
    """Hilo de trabajo asíncrono para resolver streams o descargar pistas desde enlaces de YouTube/Spotify."""
    
    status_updated = pyqtSignal(str)
    progress_updated = pyqtSignal(float)
    stream_ready = pyqtSignal(dict)
    download_finished = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, url: str, mode: str = "stream", format_type: str = "audio", download_dir: str = "", parent: Optional[Any] = None) -> None:
        super().__init__(parent)
        self.url = url
        self.mode = mode  # 'stream' o 'download'
        self.format_type = format_type  # 'audio' o 'video'
        self.download_dir = download_dir

    def run(self) -> None:
        try:
            if self.mode == "stream":
                self.status_updated.emit("Extrayendo enlace de audio...")
                self.progress_updated.emit(0.25)
                meta = extract_online_stream_info(self.url, progress_callback=lambda msg: self.status_updated.emit(msg))
                self.progress_updated.emit(1.0)
                self.stream_ready.emit(meta)
            else:
                lbl = "video" if self.format_type == "video" else "audio"
                self.status_updated.emit(f"Iniciando descarga de {lbl}...")
                self.progress_updated.emit(0.05)
                
                def _prog(msg: str, frac: float):
                    self.status_updated.emit(msg)
                    self.progress_updated.emit(frac)

                meta = download_media_offline(self.url, self.download_dir, format_type=self.format_type, progress_callback=_prog)
                self.download_finished.emit(meta)
        except Exception as e:
            self.failed.emit(str(e))
