from PyQt6.QtGui import QPixmap, QColor

def extract_pastel_colors(pixmap: QPixmap, default_stop0="#2b0b10", default_stop1="#140709") -> tuple[str, str]:
    if pixmap.isNull():
        return default_stop0, default_stop1

    image = pixmap.toImage().scaled(32, 32)
    r_sum, g_sum, b_sum, count = 0, 0, 0, 0

    for x in range(0, image.width(), 2):
        for y in range(0, image.height(), 2):
            color = QColor(image.pixelColor(x, y))
            r_sum += color.red()
            g_sum += color.green()
            b_sum += color.blue()
            count += 1

    if count == 0:
        return default_stop0, default_stop1

    r_avg = r_sum // count
    g_avg = g_sum // count
    b_avg = b_sum // count

    c = QColor(r_avg, g_avg, b_avg)
    h, s, v, _ = c.getHsv()

    # Tono oscuro saturado para ambiente gótico
    s_dark = min(max(s, 80), 200)
    v_dark = max(min(v, 70), 25)

    stop0 = QColor.fromHsv(h, s_dark, v_dark).name()
    stop1 = QColor.fromHsv((h + 10) % 360, min(s_dark + 20, 255), max(v_dark - 15, 12)).name()

    return stop0, stop1

def extract_vibrant_accent_color(pixmap: QPixmap, fallback_hex: str = "#ff1744") -> str:
    if pixmap.isNull():
        return fallback_hex

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

    return QColor.fromHsv(h if h >= 0 else 0, s_vibrant, v_vibrant).name()

