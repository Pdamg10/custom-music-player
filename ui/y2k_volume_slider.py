import os
from typing import List, Optional
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QPen, QBrush, QLinearGradient
from PyQt6.QtWidgets import QSlider

class Y2KVolumeSlider(QSlider):
    """
    Barra de volumen con diseño Y2K 'Canva Gradient Loading Tab'.
    Incluye la estrella Y2K de 4 puntas en el extremo izquierdo,
    cápsula contorneada con bordes redondeados y barra de progreso degradada
    con tapa curva brillante (crescent cap) adaptada al tema activo.
    """
    def __init__(self, parent: Optional[QSlider] = None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.accent_color: str = "#ff1744"
        self.gradient_colors: List[str] = ["#ff1744", "#7b1fa2", "#0c0c10"]
        
        self.setFixedHeight(28)
        self.setMinimumWidth(100)
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
        rect = self.rect()
        star_diameter = 24.0
        padding_left = star_diameter + 4.0
        padding_right = 8.0
        
        track_x = padding_left
        track_w = max(1.0, rect.width() - padding_left - padding_right)
        
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

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w = float(self.width())
        h = float(self.height())

        # ----------------------------------------------------
        # 1. PARÁMETROS DE GEOMETRÍA
        # ----------------------------------------------------
        star_diameter = 24.0
        star_cx = 13.0
        star_cy = h / 2.0

        track_h = 16.0
        track_x = star_cx + 4.0
        track_y = (h - track_h) / 2.0
        track_w = max(10.0, w - track_x - 6.0)
        track_rect = QRectF(track_x, track_y, track_w, track_h)
        radius = track_h / 2.0

        val_range = self.maximum() - self.minimum()
        pct = (self.value() - self.minimum()) / val_range if val_range > 0 else 0.0
        pct = max(0.0, min(1.0, pct))
        fill_w = track_w * pct

        # ----------------------------------------------------
        # 2. CONTENEDOR BASE DE CÁPSULA (PILL TRACK)
        # ----------------------------------------------------
        # Fondo oscuro transparente con borde limpio
        track_path = QPainterPath()
        track_path.addRoundedRect(track_rect, radius, radius)

        p.fillPath(track_path, QBrush(QColor(10, 12, 22, 210)))
        p.setPen(QPen(QColor(255, 255, 255, 70), 1.5))
        p.drawPath(track_path)

        # ----------------------------------------------------
        # 3. BARRA DE RELLENO DE PROGRESO (DEGRADADO Y CAPSULA)
        # ----------------------------------------------------
        if fill_w > 1.0:
            fill_rect = QRectF(track_x, track_y, fill_w, track_h)
            fill_path = QPainterPath()
            fill_path.addRoundedRect(fill_rect, radius, radius)

            # Crear degradado según el tema activo
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
            p.setPen(QPen(QColor(255, 255, 255, 120), 1.0))
            p.drawPath(fill_path)

            # ----------------------------------------------------
            # 4. CAPA CURVA BRILLANTE ("CRESCENT CAP & SMILE ARCS")
            # ----------------------------------------------------
            # Dibuja la curva redondeada en la punta del progreso estilo Canva
            cap_cx = track_x + fill_w - (radius * 0.6)
            if cap_cx > track_x + 6:
                arc_pen = QPen(QColor(0, 0, 0, 180), 2.0)
                p.setPen(arc_pen)
                arc_rect = QRectF(cap_cx - 4, track_y + 3, radius * 1.2, track_h - 6)
                p.drawArc(arc_rect, -70 * 16, 140 * 16)

                # Pequeños puntos de brillo nítido (glossy highlights)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(QColor(255, 255, 255, 230)))
                p.drawEllipse(QPointF(cap_cx + 2, track_y + 4), 1.2, 1.2)
                p.drawEllipse(QPointF(cap_cx + 2, track_y + track_h - 4), 1.2, 1.2)

        # ----------------------------------------------------
        # 5. ESTRELLA Y2K DE 4 PUNTAS (SPARKLE STAR BADGE)
        # ----------------------------------------------------
        star_path = QPainterPath()
        r_outer = star_diameter / 2.0
        
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

        # Sombra suave exterior de la estrella
        shadow_path = QPainterPath()
        top_s = QPointF(star_cx, star_cy - r_outer - 1)
        right_s = QPointF(star_cx + r_outer + 1, star_cy)
        bottom_s = QPointF(star_cx, star_cy + r_outer + 1)
        left_s = QPointF(star_cx - r_outer - 1, star_cy)

        shadow_path.moveTo(top_s)
        shadow_path.quadTo(center, right_s)
        shadow_path.quadTo(center, bottom_s)
        shadow_path.quadTo(center, left_s)
        shadow_path.quadTo(center, top_s)

        p.fillPath(shadow_path, QBrush(QColor(0, 0, 0, 160)))

        # Relleno del cuerpo de la estrella Y2K
        star_grad = QLinearGradient(star_cx - r_outer, star_cy - r_outer, star_cx + r_outer, star_cy + r_outer)
        qc_acc = QColor(self.accent_color)
        star_grad.setColorAt(0.0, QColor("#121420"))
        star_grad.setColorAt(0.6, qc_acc.darker(150))
        star_grad.setColorAt(1.0, qc_acc)

        p.fillPath(star_path, QBrush(star_grad))
        p.setPen(QPen(QColor(255, 255, 255, 220), 1.5))
        p.drawPath(star_path)

        # Brillo especular brillante en la esquina superior izquierda de la estrella
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(255, 255, 255, 240)))
        p.drawEllipse(QPointF(star_cx - 3.5, star_cy - 3.5), 1.8, 1.8)

        p.end()
