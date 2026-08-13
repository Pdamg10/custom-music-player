from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QRect
from PyQt6.QtGui import QPainter, QFontMetrics, QFont

class MarqueeLabel(QWidget):
    def __init__(self, text="", font=None, color_str="#ffffff", parent=None):
        super().__init__(parent)
        self._text = text
        self._color_str = color_str
        self._offset = 0
        self._scroll_speed = 1  # píxeles por tick
        self._text_width = 0

        if font:
            self.setFont(font)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.setInterval(40)  # 25 fps para scroll suave

        self.setText(text)

    def setText(self, text: str):
        self._text = text
        self.setToolTip(text)
        self._offset = 0
        self._update_text_width()
        self.update()

    def set_color(self, color_str: str):
        clean = color_str.split(';')[0].strip() if color_str else "#ffffff"
        if "color:" in clean:
            clean = clean.split("color:")[1].strip()
        from PyQt6.QtGui import QColor
        c = QColor(clean)
        if not c.isValid():
            c = QColor("#ffffff")
        self._color_str = c.name()
        self.update()

    def text(self) -> str:
        return self._text

    def _update_text_width(self):
        metrics = QFontMetrics(self.font())
        self._text_width = metrics.horizontalAdvance(self._text)
        if self._text_width > self.width() and self.width() > 0:
            if not self._timer.isActive():
                self._timer.start()
        else:
            if self._timer.isActive():
                self._timer.stop()
            self._offset = 0

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_text_width()

    def _on_tick(self):
        if self._text_width <= self.width():
            self._offset = 0
            self._timer.stop()
            self.update()
            return

        # Scroll continuo con espacio
        spacing = 40
        total_cycle = max(1, self._text_width + spacing)
        self._offset = (self._offset + self._scroll_speed) % total_cycle
        self.update()

    def paintEvent(self, event):
        if self.width() <= 0 or self.height() <= 0 or not self._text:
            return
        painter = QPainter(self)
        painter.setFont(self.font())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        metrics = QFontMetrics(self.font())
        y = (self.height() + metrics.ascent() - metrics.descent()) // 2

        from PyQt6.QtGui import QColor
        clean = self._color_str.split(';')[0].strip() if self._color_str else "#ffffff"
        c = QColor(clean)
        if not c.isValid():
            c = QColor("#ffffff")

        shadow_color = QColor(0, 0, 0, 220)

        if self._text_width <= self.width():
            # Texto centrado estático con sombra proyectada de alto contraste
            x = max(0, (self.width() - self._text_width) // 2)
            painter.setPen(shadow_color)
            painter.drawText(x + 1, y + 1, self._text)
            painter.setPen(c)
            painter.drawText(x, y, self._text)
        else:
            # Texto desplazable en marquesina con sombra de alto contraste
            spacing = 40
            x1 = int(-self._offset)
            x2 = int(x1 + self._text_width + spacing)

            # Sombra
            painter.setPen(shadow_color)
            painter.drawText(x1 + 1, y + 1, self._text)
            painter.drawText(x2 + 1, y + 1, self._text)

            # Texto frontal
            painter.setPen(c)
            painter.drawText(x1, y, self._text)
            painter.drawText(x2, y, self._text)
