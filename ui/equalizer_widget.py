import random
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor

class EqualizerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(30, 18)
        self.is_playing = False
        self.bar_heights = [3, 3, 3, 3]

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate_bars)
        self.timer.setInterval(90)

    def set_playing(self, playing: bool):
        self.is_playing = playing
        if playing:
            if not self.timer.isActive():
                self.timer.start()
        else:
            self.timer.stop()
            self.bar_heights = [3, 3, 3, 3]
            self.update()

    def _animate_bars(self):
        if not self.is_playing:
            return
        self.bar_heights = [random.randint(4, 16) for _ in range(4)]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#ff4d5a"))

        w = 4
        spacing = 3
        total_w = 4 * w + 3 * spacing
        start_x = (self.width() - total_w) // 2

        for i in range(4):
            h = self.bar_heights[i]
            x = start_x + i * (w + spacing)
            y = self.height() - h
            painter.drawRoundedRect(x, y, w, h, 2, 2)
