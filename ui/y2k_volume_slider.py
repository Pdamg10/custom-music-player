import os
from typing import List, Optional
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QPen, QBrush, QLinearGradient
from PyQt6.QtWidgets import QSlider

class Y2KVolumeSlider(QSlider):
    """
    Barra de volumen con diseño Y2K 'Canva Gradient Loading Tab'.
    Incluye cápsula contorneada con bordes redondeados, relleno en degradado
    y un handle en forma de estrella/diamante de 4 puntas móvil en el extremo del relleno.
    """
    def __init__(self, parent: Optional[QSlider] = None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.accent_color: str = "#ff1744"
        self.gradient_colors: List[str] = ["#ff1744", "#7b1fa2", "#0c0c10"]
        
        self.setFixedHeight(24)
        self.setMinimumWidth(60)
        self.setRange(0, 100)
        self.setValue(100)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
        self.setToolTip("Volumen: 100%")
        self.valueChanged.connect(self._update_tooltip)

    def set_accent_color(self, accent_hex: str, gradient_colors: Optional[List[str]] = None) -> None:
        if accent_hex:
            self.accent_color = accent_hex
        if gradient_colors and isinstance(gradient_colors, list) and len(gradient_colors) >= 2:
            self.gradient_colors = list(gradient_colors)
        else:
            self.gradient_colors = [self.accent_color, "#7b1fa2", "#0c0c10"]
        self.update()

    def _update_tooltip(self, val: int) -> None:
        self.setToolTip(f"Volumen: {val}%")

    def _update_val_from_pos(self, x: float) -> None:
        w = float(self.width())
        h = float(self.height())
        star_diameter = min(h - 2.0, 18.0)
        pad_x = (star_diameter / 2.0) + 1.0
        track_x = pad_x
        track_w = max(10.0, w - 2.0 * pad_x)

        rel_x = max(0.0, min(track_w, x - track_x))
        pct = rel_x / track_w
        val = int(round(self.minimum() + pct * (self.maximum() - self.minimum())))
        if val != self.value():
            self.setValue(val)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._update_val_from_pos(event.position().x())
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._update_val_from_pos(event.position().x())
            event.accept()
        super().mouseMoveEvent(event)

    def wheelEvent(self, event) -> None:
        delta = event.angleDelta().y()
        step = 5 if delta > 0 else -5
        new_val = max(0, min(100, self.value() + step))
        if new_val != self.value():
            self.setValue(new_val)
        event.accept()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w = float(self.width())
        h = float(self.height())

        # ----------------------------------------------------
        # 1. PARÁMETROS DE GEOMETRÍA DINÁMICA
        # ----------------------------------------------------
        star_diameter = min(h - 2.0, 18.0)
        r_outer = star_diameter / 2.0
        pad_x = r_outer + 1.0

        track_h = max(6.0, min(11.0, h * 0.46))
        track_x = pad_x
        track_w = max(10.0, w - 2.0 * pad_x)
        track_y = (h - track_h) / 2.0
        track_rect = QRectF(track_x, track_y, track_w, track_h)
        radius = track_h / 2.0

        val_range = self.maximum() - self.minimum()
        pct = (self.value() - self.minimum()) / val_range if val_range > 0 else 0.0
        pct = max(0.0, min(1.0, pct))
        fill_w = track_w * pct

        # Posición dinámica de la estrella (Handle móvil en el extremo del relleno)
        star_cx = track_x + fill_w
        star_cy = h / 2.0

        # ----------------------------------------------------
        # 2. CONTENEDOR BASE DE CÁPSULA (PILL TRACK NO RELLENO)
        # ----------------------------------------------------
        track_path = QPainterPath()
        track_path.addRoundedRect(track_rect, radius, radius)

        # Fondo translúcido neutro con borde sutil para alto contraste en tema oscuro
        p.fillPath(track_path, QBrush(QColor(255, 255, 255, 28)))
        p.setPen(QPen(QColor(255, 255, 255, 55), 1.0))
        p.drawPath(track_path)

        # ----------------------------------------------------
        # 3. BARRA DE RELLENO DE PROGRESO (DEGRADADO ACTIVO DEL MODO)
        # ----------------------------------------------------
        if fill_w > 0.5:
            fill_rect = QRectF(track_x, track_y, fill_w, track_h)
            fill_path = QPainterPath()
            fill_path.addRoundedRect(fill_rect, radius, radius)

            # Degradado horizontal del tema
            grad = QLinearGradient(track_x, 0, track_x + track_w, 0)
            if self.gradient_colors and len(self.gradient_colors) >= 2:
                for idx, c_hex in enumerate(self.gradient_colors):
                    pos = idx / max(1, len(self.gradient_colors) - 1)
                    qc = QColor(c_hex)
                    if qc.isValid():
                        grad.setColorAt(pos, qc)
            else:
                qc_acc = QColor(self.accent_color)
                grad.setColorAt(0.0, qc_acc)
                grad.setColorAt(1.0, qc_acc.darker(130))

            p.fillPath(fill_path, QBrush(grad))
            p.setPen(QPen(QColor(255, 255, 255, 110), 0.8))
            p.drawPath(fill_path)

        # ----------------------------------------------------
        # 4. HANDLE EN FORMA DE ESTRELLA/DIAMANTE DE 4 PUNTAS (MÓVIL)
        # ----------------------------------------------------
        star_path = QPainterPath()
        
        top = QPointF(star_cx, star_cy - r_outer)
        right = QPointF(star_cx + r_outer, star_cy)
        bottom = QPointF(star_cx, star_cy + r_outer)
        left = QPointF(star_cx - r_outer, star_cy)
        center = QPointF(star_cx, star_cy)

        star_path.moveTo(top)
        star_path.quadTo(center, right)
        star_path.quadTo(center, bottom)
        star_path.quadTo(center, left)
        star_path.quadTo(center, top)

        # Sombra suave exterior del handle
        shadow_path = QPainterPath()
        top_s = QPointF(star_cx + 0.5, star_cy - r_outer + 0.5)
        right_s = QPointF(star_cx + r_outer + 1.2, star_cy + 0.5)
        bottom_s = QPointF(star_cx + 0.5, star_cy + r_outer + 1.2)
        left_s = QPointF(star_cx - r_outer - 0.5, star_cy + 0.5)
        center_s = QPointF(star_cx + 0.5, star_cy + 0.5)

        shadow_path.moveTo(top_s)
        shadow_path.quadTo(center_s, right_s)
        shadow_path.quadTo(center_s, bottom_s)
        shadow_path.quadTo(center_s, left_s)
        shadow_path.quadTo(center_s, top_s)

        p.fillPath(shadow_path, QBrush(QColor(0, 0, 0, 150)))

        # Relleno del cuerpo de la estrella con degradado del acento
        star_grad = QLinearGradient(star_cx - r_outer, star_cy - r_outer, star_cx + r_outer, star_cy + r_outer)
        qc_acc = QColor(self.accent_color)
        star_grad.setColorAt(0.0, QColor("#ffffff"))
        star_grad.setColorAt(0.35, qc_acc.lighter(130))
        star_grad.setColorAt(0.8, qc_acc)
        star_grad.setColorAt(1.0, qc_acc.darker(140))

        p.fillPath(star_path, QBrush(star_grad))
        p.setPen(QPen(QColor(255, 255, 255, 230), 1.2))
        p.drawPath(star_path)

        # Brillo especular brillante en la esquina superior izquierda
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(255, 255, 255, 250)))
        spec_size = max(1.2, r_outer * 0.25)
        p.drawEllipse(QPointF(star_cx - r_outer * 0.28, star_cy - r_outer * 0.28), spec_size, spec_size)

        p.end()
