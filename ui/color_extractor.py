from typing import Optional, List, Dict, Tuple
from PyQt6.QtGui import QPixmap, QColor

_GRADIENT_CACHE: Dict[Tuple[int, int], List[str]] = {}
_ACCENT_CACHE: Dict[int, str] = {}


def _prune_cache_if_needed(cache: dict, max_size: int = 150, prune_count: int = 30) -> None:
    if len(cache) > max_size:
        for k in list(cache.keys())[:prune_count]:
            cache.pop(k, None)


def extract_vibrant_accent_color(pixmap: QPixmap, fallback_hex: str = "#ff1744") -> str:
    if pixmap is None or pixmap.isNull():
        return fallback_hex

    cache_key = pixmap.cacheKey()
    if cache_key in _ACCENT_CACHE:
        return _ACCENT_CACHE[cache_key]

    image = pixmap.toImage().scaled(64, 64)
    r_sum, g_sum, b_sum, count = 0, 0, 0, 0

    for x in range(0, image.width(), 3):
        for y in range(0, image.height(), 3):
            color = QColor(image.pixelColor(x, y))
            r_sum += color.red()
            g_sum += color.green()
            b_sum += color.blue()
            count += 1

    if count == 0:
        return fallback_hex

    r_avg = r_sum // count
    g_avg = g_sum // count
    b_avg = b_sum // count

    c = QColor(r_avg, g_avg, b_avg)
    h, s, v, _ = c.getHsv()

    s_vibrant = max(s, 200)
    v_vibrant = max(v, 230)

    res = QColor.fromHsv(h if h >= 0 else 0, s_vibrant, v_vibrant).name()
    _prune_cache_if_needed(_ACCENT_CACHE)
    _ACCENT_CACHE[cache_key] = res
    return res


def extract_dominant_gradient_colors(pixmap: Optional[QPixmap], max_colors: int = 4, fallback_colors: Optional[List[str]] = None) -> List[str]:
    """Extrae de 2 a 4 colores dominantes y contrastantes de una carátula para generar un degradado armónico con caché instantánea."""
    default_stops = fallback_colors or ["#2b0b10", "#180718", "#08060c"]
    if pixmap is None or pixmap.isNull():
        return default_stops

    cache_key = (pixmap.cacheKey(), max_colors)
    if cache_key in _GRADIENT_CACHE:
        return list(_GRADIENT_CACHE[cache_key])

    img = pixmap.toImage().scaled(48, 48)
    w, h = img.width(), img.height()
    if w <= 0 or h <= 0:
        return default_stops

    # Muestreo de píxeles y agrupación de colores por histograma HSV
    color_samples: List[QColor] = []
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            c = QColor(img.pixelColor(x, y))
            if c.alpha() > 100:
                color_samples.append(c)

    if not color_samples:
        return default_stops

    # Agrupación en cubos HSV
    buckets: Dict[tuple, List[QColor]] = {}
    for c in color_samples:
        h_val, s_val, v_val, _ = c.getHsv()
        if h_val < 0:
            h_val = 0
        h_bin = (h_val // 30) * 30    # 12 tonos de hue
        s_bin = (s_val // 64) * 64    # 4 niveles de saturación
        v_bin = (v_val // 64) * 64    # 4 niveles de brillo
        key = (h_bin, s_bin, v_bin)
        buckets.setdefault(key, []).append(c)

    # Ordenar cubos por cantidad de píxeles y riqueza cromática
    sorted_buckets = []
    for key, samples in buckets.items():
        count = len(samples)
        avg_r = sum(sc.red() for sc in samples) // count
        avg_g = sum(sc.green() for sc in samples) // count
        avg_b = sum(sc.blue() for sc in samples) // count
        avg_col = QColor(avg_r, avg_g, avg_b)
        h_v, s_v, v_v, _ = avg_col.getHsv()
        # Puntuación basada en frecuencia y saturación/brillo
        score = count * (1.0 + (s_v / 255.0) * 0.8)
        sorted_buckets.append((score, avg_col))

    sorted_buckets.sort(key=lambda item: item[0], reverse=True)

    extracted_colors: List[QColor] = []
    for _, col in sorted_buckets:
        if len(extracted_colors) >= max_colors:
            break
        # Evitar colores excesivamente idénticos
        if not any(abs(col.red() - ec.red()) + abs(col.green() - ec.green()) + abs(col.blue() - ec.blue()) < 70 for ec in extracted_colors):
            extracted_colors.append(col)

    if not extracted_colors:
        return default_stops

    # Ajuste estilístico para asegurar que el degradado tenga contraste y fondo elegante
    hex_list = []
    for idx, col in enumerate(extracted_colors):
        h_v, s_v, v_v, _ = col.getHsv()
        if h_v < 0:
            h_v = 0
        # Primer parada: mantén saturación rica y brillo moderado para impacto visual
        if idx == 0:
            s_adj = max(s_v, 110)
            v_adj = max(min(v_v, 180), 45)
            hex_list.append(QColor.fromHsv(h_v, s_adj, v_adj).name())
        elif idx == 1:
            # Segunda parada: tono intermedio armónico
            s_adj = max(min(s_v, 180), 70)
            v_adj = max(min(v_v, 130), 30)
            hex_list.append(QColor.fromHsv(h_v, s_adj, v_adj).name())
        else:
            # Tercera/cuarta parada: tono oscuro gótico elegante para la base del reproductor
            s_adj = max(min(s_v, 150), 50)
            v_adj = max(min(v_v, 70), 15)
            hex_list.append(QColor.fromHsv(h_v, s_adj, v_adj).name())

    # Garantizar al menos 2 paradas de color
    if len(hex_list) == 1:
        c1 = QColor(hex_list[0])
        h_v, s_v, v_v, _ = c1.getHsv()
        dark_stop = QColor.fromHsv((h_v + 15) % 360, max(s_v - 20, 40), max(v_v - 40, 12)).name()
        hex_list.append(dark_stop)

    _prune_cache_if_needed(_GRADIENT_CACHE)
    _GRADIENT_CACHE[cache_key] = hex_list
    return hex_list

def get_contrasting_text_color(hex_color: str) -> str:
    """Retorna '#000000' (Negro) o '#ffffff' (Blanco) según la luminancia percibida del color de fondo."""
    if not hex_color:
        return "#ffffff"
    c = QColor(hex_color)
    if not c.isValid():
        return "#ffffff"
    luminance = (0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()) / 255.0
    return "#000000" if luminance > 0.6 else "#ffffff"



