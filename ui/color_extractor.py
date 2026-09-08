from typing import Optional, List, Dict, Tuple, Any
from PyQt6.QtGui import QPixmap, QColor

_GRADIENT_CACHE: Dict[Tuple[int, int], List[str]] = {}
_ACCENT_CACHE: Dict[int, str] = {}
_LYRICS_PALETTE_CACHE: Dict[Tuple[int, str], Dict[str, Any]] = {}


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


def extract_lyrics_theme_colors(pixmap: Optional[QPixmap], accent_hex: str = "#ff1744") -> Dict[str, Any]:
    """
    Analiza la carátula / fondo detrás de las letras y calcula una paleta dinámica de alto contraste
    armonizada con los colores de la carátula para garantizar legibilidad al 100% sobre fondos
    oscuros, claros, pastel o con textura compleja.
    """
    clean_accent = accent_hex.split(';')[0].strip() if accent_hex else "#ff1744"
    qc_accent = QColor(clean_accent)
    if not qc_accent.isValid():
        qc_accent = QColor("#ff1744")

    cache_key = (pixmap.cacheKey() if (pixmap and not pixmap.isNull()) else 0, clean_accent)
    if cache_key in _LYRICS_PALETTE_CACHE:
        return dict(_LYRICS_PALETTE_CACHE[cache_key])

    is_light_bg = False
    avg_lum = 0.0
    center_lum = 0.0
    cover_accent_hex = clean_accent

    if pixmap and not pixmap.isNull():
        # Extraer el acento vibrante dominante de la carátula
        cover_accent_hex = extract_vibrant_accent_color(pixmap, fallback_hex=clean_accent)
        img = pixmap.toImage().scaled(64, 64)
        w, h = img.width(), img.height()
        if w > 0 and h > 0:
            total_lum = 0.0
            count = 0
            c_total_lum = 0.0
            c_count = 0

            # Límites de la zona central donde se proyectan las letras
            cx_min, cx_max = int(w * 0.15), int(w * 0.85)
            cy_min, cy_max = int(h * 0.15), int(h * 0.85)

            for x in range(0, w, 2):
                for y in range(0, h, 2):
                    col = img.pixelColor(x, y)
                    if col.alpha() > 40:
                        lum = (0.2126 * col.red() + 0.7152 * col.green() + 0.0722 * col.blue()) / 255.0
                        total_lum += lum
                        count += 1
                        if cx_min <= x <= cx_max and cy_min <= y <= cy_max:
                            c_total_lum += lum
                            c_count += 1

            if count > 0:
                avg_lum = total_lum / count
            if c_count > 0:
                center_lum = c_total_lum / c_count
            else:
                center_lum = avg_lum

            # Ponderación: 65% zona central + 35% global
            effective_lum = (center_lum * 0.65) + (avg_lum * 0.35)
            if effective_lum >= 0.44:
                is_light_bg = True

    qc_cover = QColor(cover_accent_hex)
    if not qc_cover.isValid():
        qc_cover = qc_accent
    cr, cg, cb = qc_cover.red(), qc_cover.green(), qc_cover.blue()

    if is_light_bg:
        # Paleta para FONDOS CLAROS (blanco, crema, pasteles claros, etc.)
        # Oscurecer acento si es muy claro para garantizar contraste sobre fondo blanco/claro
        cov_lum = (0.2126 * cr + 0.7152 * cg + 0.0722 * cb) / 255.0
        if cov_lum > 0.38:
            dark_cov = qc_cover.darker(170)
            t_accent = dark_cov.name()
            tcr, tcg, tcb = dark_cov.red(), dark_cov.green(), dark_cov.blue()
        else:
            t_accent = cover_accent_hex
            tcr, tcg, tcb = cr, cg, cb

        palette: Dict[str, Any] = {
            "is_light_bg": True,
            "avg_lum": avg_lum,
            "cover_accent": t_accent,
            # Contenedor de letras (Velo de cristal traslúcido para aislar ruido de carátula)
            "container_bg": "rgba(255, 255, 255, 0.68)",
            "container_border": "rgba(15, 23, 42, 0.12)",
            # Letra activa (resaltada)
            "active_orig": "#080c16",
            "active_romaji": "#b45309",   # Ámbar profundo de alto contraste
            "active_trans": t_accent,
            "active_bg": f"rgba({tcr}, {tcg}, {tcb}, 0.14)",
            "active_border": f"rgba({tcr}, {tcg}, {tcb}, 0.45)",
            # Letras inactivas (contraste elevado al 80% para legibilidad perfecta)
            "inactive_orig": "rgba(10, 15, 28, 0.78)",
            "inactive_romaji": "rgba(180, 83, 9, 0.82)",
            "inactive_trans": f"rgba({tcr}, {tcg}, {tcb}, 0.80)",
            "inactive_hover_bg": f"rgba({tcr}, {tcg}, {tcb}, 0.10)",
            "inactive_hover_color": "#080c16",
            # Letra plana / no sincronizada
            "unsynced_orig": "rgba(8, 12, 24, 0.92)",
            "unsynced_romaji": "rgba(180, 83, 9, 0.90)",
            "unsynced_trans": f"rgba({tcr}, {tcg}, {tcb}, 0.92)",
            # Encabezado, estados y botones
            "header_color": "rgba(10, 15, 28, 0.65)",
            "status_color": "rgba(10, 15, 28, 0.55)",
            "btn_bg": "rgba(15, 23, 42, 0.08)",
            "btn_color": "rgba(10, 15, 28, 0.88)",
            "btn_border": "rgba(15, 23, 42, 0.20)",
            "btn_hover_bg": f"rgba({tcr}, {tcg}, {tcb}, 0.18)",
            "btn_hover_color": "#080c16",
            "btn_active_bg": f"rgba({tcr}, {tcg}, {tcb}, 0.20)",
            "btn_active_color": t_accent,
            "btn_active_border": t_accent,
            # Halo blanco traslúcido para legibilidad sobre cualquier textura
            "shadow_color": QColor(255, 255, 255, 230),
            # Título y Artista en Now Playing
            "title_color": "#070a14",
            "artist_color": "#334155",
        }
    else:
        # Paleta para FONDOS OSCUROS (carátulas oscuras, degradados oscuros)
        # Asegurar que el acento de la carátula sea lo suficientemente brillante
        cov_lum = (0.2126 * cr + 0.7152 * cg + 0.0722 * cb) / 255.0
        if cov_lum < 0.40:
            bright_cov = qc_cover.lighter(160)
            t_accent = bright_cov.name()
            tcr, tcg, tcb = bright_cov.red(), bright_cov.green(), bright_cov.blue()
        else:
            t_accent = cover_accent_hex
            tcr, tcg, tcb = cr, cg, cb

        palette = {
            "is_light_bg": False,
            "avg_lum": avg_lum,
            "cover_accent": t_accent,
            # Contenedor de letras (Velo de cristal oscuro traslúcido)
            "container_bg": "rgba(10, 14, 26, 0.60)",
            "container_border": "rgba(255, 255, 255, 0.12)",
            # Letra activa (resaltada con el acento de la carátula)
            "active_orig": "#ffffff",
            "active_romaji": "#ffe082",   # Oro brillante cálido
            "active_trans": t_accent,
            "active_bg": f"rgba({tcr}, {tcg}, {tcb}, 0.28)",
            "active_border": f"rgba({tcr}, {tcg}, {tcb}, 0.65)",
            # Letras inactivas (contraste reforzado al 78% para evitar texto invisible)
            "inactive_orig": "rgba(255, 255, 255, 0.78)",
            "inactive_romaji": "rgba(255, 224, 130, 0.78)",
            "inactive_trans": f"rgba({tcr}, {tcg}, {tcb}, 0.76)",
            "inactive_hover_bg": f"rgba({tcr}, {tcg}, {tcb}, 0.18)",
            "inactive_hover_color": "#ffffff",
            # Letra plana / no sincronizada
            "unsynced_orig": "rgba(255, 255, 255, 0.94)",
            "unsynced_romaji": "rgba(255, 224, 130, 0.90)",
            "unsynced_trans": f"rgba({tcr}, {tcg}, {tcb}, 0.92)",
            # Encabezado, estados y botones
            "header_color": "rgba(255, 255, 255, 0.60)",
            "status_color": "rgba(255, 255, 255, 0.45)",
            "btn_bg": "rgba(255, 255, 255, 0.08)",
            "btn_color": "rgba(255, 255, 255, 0.88)",
            "btn_border": "rgba(255, 255, 255, 0.18)",
            "btn_hover_bg": f"rgba({tcr}, {tcg}, {tcb}, 0.25)",
            "btn_hover_color": "#ffffff",
            "btn_active_bg": f"rgba({tcr}, {tcg}, {tcb}, 0.30)",
            "btn_active_color": t_accent,
            "btn_active_border": t_accent,
            # Sombra oscura profunda para despegar el texto blanco
            "shadow_color": QColor(0, 0, 0, 245),
            # Título y Artista en Now Playing
            "title_color": "#ffffff",
            "artist_color": "#cbd5e1",
        }

    _prune_cache_if_needed(_LYRICS_PALETTE_CACHE)
    _LYRICS_PALETTE_CACHE[cache_key] = palette
    return dict(palette)



