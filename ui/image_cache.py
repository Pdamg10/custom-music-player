"""Módulo centralizado de caché y renderizado acelerado de carátulas e imágenes para Custom Music Player."""

import hashlib
import os
import subprocess
import threading
import urllib.parse
import uuid
from typing import Any, Callable, Dict, Optional, Tuple

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QImageReader,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPixmap,
)
from library_manager import VIDEO_EXTENSIONS

GIF_EXTENSIONS = {".gif"}

_PIXMAP_CACHE: Dict[tuple, Optional[QPixmap]] = {}
_ROUNDED_PIXMAP_CACHE: Dict[tuple, QPixmap] = {}
_PLACEHOLDER_CACHE: Dict[tuple, QPixmap] = {}
_PROXY_LOCK = threading.Lock()
_ACTIVE_PROXIES: set = set()


def _trim_cache_if_needed(cache: dict, max_size: int = 250, prune_count: int = 50) -> None:
    if len(cache) > max_size:
        for k in list(cache.keys())[:prune_count]:
            cache.pop(k, None)


def clean_art_path(path_or_url: Any) -> str:
    """Normaliza y limpia rutas locales, file:// URLs y quita comillas."""
    if not path_or_url:
        return ""
    clean = str(path_or_url).strip()
    if clean.startswith("file://"):
        clean = urllib.parse.unquote(clean[7:])
    elif clean.startswith("file:"):
        clean = urllib.parse.unquote(clean[5:])
    else:
        clean = urllib.parse.unquote(clean)
    return os.path.expanduser(clean.strip("'\""))


def is_video_file(path_or_url: Any) -> bool:
    """Verifica si la ruta apunta a un archivo de video soportado."""
    clean = clean_art_path(path_or_url)
    if not clean:
        return False
    ext = os.path.splitext(clean)[1].lower()
    return ext in VIDEO_EXTENSIONS


def is_gif_file(path_or_url: Any) -> bool:
    """Verifica si la ruta apunta a una animación GIF."""
    clean = clean_art_path(path_or_url)
    if not clean:
        return False
    ext = os.path.splitext(clean)[1].lower()
    return ext in GIF_EXTENSIONS


def get_media_type(path_or_url: Any) -> str:
    """Determina si el medio es 'video', 'gif', 'image' o 'none'."""
    if not path_or_url:
        return "none"
    if is_video_file(path_or_url):
        return "video"
    if is_gif_file(path_or_url):
        return "gif"
    clean = clean_art_path(path_or_url)
    if clean.startswith("http://") or clean.startswith("https://") or os.path.exists(clean):
        return "image"
    return "none"


def extract_video_thumbnail(video_path: str) -> str:
    """Extrae de forma ultra-rápida un fotograma de un video y lo cachea en disco."""
    clean_p = clean_art_path(video_path)
    if not clean_p or not os.path.exists(clean_p) or not os.path.isfile(clean_p):
        return ""

    try:
        from config_manager import get_platform_base_dir
        cache_dir = get_platform_base_dir("config", os.path.join("covers", "video_thumbs"))
        os.makedirs(cache_dir, exist_ok=True)
        v_hash = hashlib.md5(clean_p.encode("utf-8")).hexdigest()
        thumb_path = os.path.join(cache_dir, f"{v_hash}.jpg")

        if os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 0:
            return thumb_path

        import subprocess
        # Intento 1: A los 0.5s para evitar fotogramas iniciales en negro
        cmd = [
            "ffmpeg", "-y",
            "-ss", "00:00:00.500",
            "-i", clean_p,
            "-vframes", "1",
            "-q:v", "2",
            thumb_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=4)
        if os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 0:
            return thumb_path

        # Intento 2 (Fallback): Al inicio exacto (00:00:00) para clips cortos o timestamps singulares
        cmd_fallback = [
            "ffmpeg", "-y",
            "-i", clean_p,
            "-vframes", "1",
            "-q:v", "2",
            thumb_path
        ]
        subprocess.run(cmd_fallback, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=4)
        if os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 0:
            return thumb_path
    except Exception as e:
        print(f"[ImageCache] Error extrayendo fotograma de video {clean_p}: {e}")

    return ""


_VIDEO_PROBE_CACHE: Dict[str, Tuple[float, int, int, float]] = {}
_VALID_MP4_CACHE: Dict[str, Tuple[float, bool]] = {}


def get_video_playback_source(video_path: str, on_ready_callback: Optional[Callable[[str], None]] = None) -> str:
    """
    Retorna la ruta optimizada para reproducir el video en tiempo real sin lag ni consumo excesivo de CPU.
    Si el video original ya es ligero (<= 854px en su dimensión mayor y <= 30 FPS), se reproduce directamente.
    Si es de alta resolución (720p, 1080p, 4K) o alta tasa de refresco (> 30 FPS como 50/60 FPS),
    genera en segundo plano un proxy ultrarrápido a 30 FPS y max 854px en caché para garantizar 60 FPS fluidos
    en la interfaz de usuario con 0% de sobrecarga en el bucle de eventos.
    """
    clean_p = clean_art_path(video_path)
    if not clean_p or not os.path.exists(clean_p) or not os.path.isfile(clean_p):
        return video_path

    try:
        mtime = os.path.getmtime(clean_p)
        cached_probe = _VIDEO_PROBE_CACHE.get(clean_p)
        if cached_probe and cached_probe[0] == mtime:
            w_val, h_val, fps_val = cached_probe[1], cached_probe[2], cached_probe[3]
        else:
            cmd = [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,r_frame_rate",
                "-of", "csv=s=x:p=0",
                clean_p
            ]
            out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=1.5).decode().strip()
            w_val, h_val, fps_val = 0, 0, 30.0
            if "x" in out:
                parts = out.split("x")
                if len(parts) >= 2:
                    w_val = int(parts[0])
                    h_val = int(parts[1])
                if len(parts) >= 3:
                    fps_str = parts[2].strip()
                    if "/" in fps_str:
                        num, den = fps_str.split("/", 1)
                        if float(den) > 0:
                            fps_val = float(num) / float(den)
                    elif fps_str:
                        fps_val = float(fps_str)
            _VIDEO_PROBE_CACHE[clean_p] = (mtime, w_val, h_val, fps_val)

        # Si el video ya es ligero (<= 854px y <= 30.5 fps), reproducir directamente
        if 0 < max(w_val, h_val) <= 854 and fps_val <= 30.5:
            return clean_p
    except Exception:
        pass

    try:
        from config_manager import get_platform_base_dir
        cache_dir = get_platform_base_dir("config", os.path.join("covers", "video_proxies"))
        os.makedirs(cache_dir, exist_ok=True)
        v_hash = hashlib.md5(f"{clean_p}_{mtime}".encode("utf-8")).hexdigest()
        proxy_path = os.path.join(cache_dir, f"{v_hash}_opt30.mp4")

        def _is_valid_mp4(p: str) -> bool:
            if not os.path.exists(p) or os.path.getsize(p) < 10000:
                return False
            pmtime = os.path.getmtime(p)
            cached_valid = _VALID_MP4_CACHE.get(p)
            if cached_valid and cached_valid[0] == pmtime:
                return cached_valid[1]
            try:
                check_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", p]
                dur_str = subprocess.check_output(check_cmd, stderr=subprocess.DEVNULL, timeout=1.5).decode().strip()
                res = float(dur_str) > 0.1
                _VALID_MP4_CACHE[p] = (pmtime, res)
                return res
            except Exception:
                return False

        if _is_valid_mp4(proxy_path):
            return proxy_path

        with _PROXY_LOCK:
            if proxy_path in _ACTIVE_PROXIES:
                return clean_p
            _ACTIVE_PROXIES.add(proxy_path)

        def _generate():
            temp_proxy = f"{proxy_path}.tmp_{os.getpid()}_{uuid.uuid4().hex[:8]}.mp4"
            try:
                # Transcodificación acelerada a 30 FPS y max 854px con ultrafast para reproducción instantánea y fluida
                scale_filter = "scale=w='if(gt(iw,ih),min(854,iw),trunc(iw*854/ih/2)*2)':h='if(gt(iw,ih),trunc(ih*854/iw/2)*2,min(854,ih))',fps=30,format=yuv420p"
                cpu_cmd = [
                    "ffmpeg", "-y", "-i", clean_p,
                    "-vf", scale_filter,
                    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24",
                    "-threads", "4",
                    "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart",
                    "-an", temp_proxy
                ]
                res = subprocess.run(cpu_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90.0)
                if _is_valid_mp4(temp_proxy):
                    os.replace(temp_proxy, proxy_path)
                    if on_ready_callback:
                        on_ready_callback(proxy_path)
                    return
            except Exception:
                pass
            finally:
                with _PROXY_LOCK:
                    _ACTIVE_PROXIES.discard(proxy_path)
                if os.path.exists(temp_proxy):
                    try:
                        os.remove(temp_proxy)
                    except Exception:
                        pass

        threading.Thread(target=_generate, daemon=True).start()
        return clean_p
    except Exception:
        return clean_p


def resolve_library_art(track_meta: Optional[Dict[str, Any]], global_custom_art: str = "") -> str:
    """
    Jerarquía Inteligente de Carátulas para la BIBLIOTECA (listas y cuadrículas):
    1. Si la canción tiene carátula individual asignada, se usa su carátula individual.
    2. Las canciones que ya tienen su carátula original la conservan intacta en listas y cuadrículas.
    3. La carátula personalizada global entra en acción únicamente en las canciones que carecen de portada definida.
    4. Si ninguna existe, retorna cadena vacía (lo que activa el placeholder estándar).
    """
    if not track_meta or not isinstance(track_meta, dict):
        clean_glob = clean_art_path(global_custom_art)
        return clean_glob if (clean_glob and os.path.exists(clean_glob)) else ""

    # 1. Carátula personalizada individual asignada a la canción
    custom_ind = clean_art_path(track_meta.get("custom_art_url") or "")
    if custom_ind and os.path.exists(custom_ind):
        return custom_ind

    # 2. Carátula original del archivo de audio (conservada intacta)
    orig_art = clean_art_path(track_meta.get("art_url") or "")
    if orig_art and (orig_art.startswith("http://") or orig_art.startswith("https://") or os.path.exists(orig_art)):
        return orig_art

    # 3. Carátula personalizada global (entra en acción únicamente en canciones que carecen de portada definida)
    clean_glob = clean_art_path(global_custom_art)
    if clean_glob and os.path.exists(clean_glob):
        return clean_glob

    return ""


def resolve_now_playing_art(
    track_meta: Optional[Dict[str, Any]],
    global_custom_art: str = "",
    inner_art_mode: str = "auto"
) -> Tuple[str, str]:
    """
    Jerarquía Inteligente de Carátulas para la SECCIÓN EN REPRODUCCIÓN:
    1. Si asignas una carátula individual (video/GIF/foto), se mostrará como carátula principal.
    2. Si inner_art_mode == 'custom_always' y hay carátula personalizada global, se muestra esa.
    3. Si inner_art_mode == 'auto', prioriza la carátula original de la canción. Si no tiene, usa la carátula personalizada global como fallback.
    4. Si no hay ninguna carátula, retorna ('', 'none') para usar el placeholder visual.

    Retorna: (path_del_medio, 'video' | 'gif' | 'image' | 'none')
    """
    if track_meta and isinstance(track_meta, dict):
        # 1. Carátula personalizada individual asignada a esta canción
        indiv_art = clean_art_path(track_meta.get("custom_art_url") or "")
        if indiv_art and os.path.exists(indiv_art):
            return indiv_art, get_media_type(indiv_art)

    clean_glob = clean_art_path(global_custom_art)
    has_glob = bool(clean_glob and os.path.exists(clean_glob))

    # En modo custom_always, la carátula personalizada global tiene prioridad sobre la del archivo
    if inner_art_mode == "custom_always" and has_glob:
        return clean_glob, get_media_type(clean_glob)

    # 3. Carátula original del archivo (en modo auto o si custom_always no tiene global)
    if track_meta and isinstance(track_meta, dict):
        orig_art = clean_art_path(track_meta.get("art_url") or "")
        if orig_art and (orig_art.startswith("http://") or orig_art.startswith("https://") or os.path.exists(orig_art)):
            return orig_art, get_media_type(orig_art)

    # Si no hay carátula original, usar la carátula global como fallback si existe
    if has_glob:
        return clean_glob, get_media_type(clean_glob)

    return "", "none"


def get_cached_pixmap(path_or_url: str, width: int = 129, height: int = 110) -> Optional[QPixmap]:
    """Carga y escala una imagen/video desde disco o memoria utilizando el motor C++ de Qt con caché LRU."""
    if not path_or_url:
        return None

    clean_path = clean_art_path(path_or_url)

    if is_video_file(clean_path):
        thumb = extract_video_thumbnail(clean_path)
        if thumb and os.path.exists(thumb):
            clean_path = thumb
        else:
            _PIXMAP_CACHE[(clean_path, width, height)] = None
            return None

    cache_key = (clean_path, width, height)
    if cache_key in _PIXMAP_CACHE:
        return _PIXMAP_CACHE[cache_key]

    base_key = (clean_path, 0, 0)
    if base_key in _PIXMAP_CACHE and _PIXMAP_CACHE[base_key] is not None:
        base_pix = _PIXMAP_CACHE[base_key]
        if width > 0 and height > 0:
            scaled = base_pix.scaled(
                width,
                height,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            _PIXMAP_CACHE[cache_key] = scaled
            return scaled
        return base_pix

    if not os.path.exists(clean_path) or not os.path.isfile(clean_path):
        _PIXMAP_CACHE[cache_key] = None
        return None

    pixmap: Optional[QPixmap] = None

    # Método 1: QPixmap Directo Nativo en C++ (Ultrarrápido, ~0.5ms por imagen)
    try:
        pix = QPixmap(clean_path)
        if pix and not pix.isNull() and pix.width() > 0:
            pixmap = pix
            _PIXMAP_CACHE[base_key] = pixmap
    except Exception:
        pixmap = None

    # Método 2: QImageReader (Con auto-transformación EXIF)
    if pixmap is None or pixmap.isNull():
        try:
            reader = QImageReader(clean_path)
            reader.setAutoTransform(True)
            qimg = reader.read()
            if not qimg.isNull():
                pixmap = QPixmap.fromImage(qimg)
                _PIXMAP_CACHE[base_key] = pixmap
        except Exception:
            pixmap = None

    # Método 3: PIL / Pillow Fallback
    if pixmap is None or pixmap.isNull():
        try:
            from PIL import Image, ImageOps
            import io

            with Image.open(clean_path) as pil_img:
                pil_img = ImageOps.exif_transpose(pil_img)
                if width > 0 and height > 0:
                    pil_img.thumbnail((max(width * 2, 400), max(height * 2, 400)))
                buf = io.BytesIO()
                pil_img.save(buf, format="PNG")
                pix = QPixmap()
                if pix.loadFromData(buf.getvalue()):
                    pixmap = pix
                    _PIXMAP_CACHE[base_key] = pixmap
        except Exception:
            pixmap = None

    if pixmap and not pixmap.isNull():
        _trim_cache_if_needed(_PIXMAP_CACHE)
        if width > 0 and height > 0:
            scaled = pixmap.scaled(
                width,
                height,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            _PIXMAP_CACHE[cache_key] = scaled
            return scaled
        else:
            _PIXMAP_CACHE[cache_key] = pixmap
            return pixmap

    _PIXMAP_CACHE[cache_key] = None
    return None


def get_cached_rounded_pixmap(
    path_or_url: str,
    width: int = 140,
    height: int = 140,
    radius: float = 12.0,
    is_circular: bool = False,
    placeholder_text: str = "♫",
    accent_color: str = "#ff1744",
) -> QPixmap:
    """Genera y cachea en memoria pixmaps pre-escalados y con esquinas redondeadas o circulares (0ms I/O)."""
    clean_path = clean_art_path(path_or_url)
    clean_accent = (accent_color or "#ff1744").split(";")[0].strip() or "#ff1744"
    cache_key = (clean_path, width, height, radius, is_circular, clean_accent, placeholder_text)
    if cache_key in _ROUNDED_PIXMAP_CACHE:
        return _ROUNDED_PIXMAP_CACHE[cache_key]

    base_pix = get_cached_pixmap(clean_path, width, height) if clean_path else None

    final_pm = QPixmap(max(1, width), max(1, height))
    final_pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(final_pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    path = QPainterPath()
    if is_circular:
        path.addEllipse(0, 0, width, height)
    else:
        path.addRoundedRect(QRectF(0, 0, width, height), radius, radius)
    p.setClipPath(path)

    if base_pix and not base_pix.isNull():
        sx = int((width - base_pix.width()) / 2)
        sy = int((height - base_pix.height()) / 2)
        p.drawPixmap(sx, sy, base_pix)
    else:
        qc = QColor(clean_accent)
        if not qc.isValid():
            qc = QColor("#ff1744")
        grad = QLinearGradient(0, 0, width, height)
        grad.setColorAt(0.0, QColor(qc.red() // 3, qc.green() // 3, qc.blue() // 3, 220))
        grad.setColorAt(1.0, QColor(16, 20, 36, 240))
        p.fillPath(path, QBrush(grad))
        p.setPen(QColor(255, 255, 255, 180))
        font_size = max(9, int(min(width, height) * 0.28))
        p.setFont(QFont("Sans Serif", font_size, QFont.Weight.Bold))
        p.drawText(QRectF(0, 0, width, height), Qt.AlignmentFlag.AlignCenter, placeholder_text)

    p.end()
    _trim_cache_if_needed(_ROUNDED_PIXMAP_CACHE)
    _ROUNDED_PIXMAP_CACHE[cache_key] = final_pm
    return final_pm
