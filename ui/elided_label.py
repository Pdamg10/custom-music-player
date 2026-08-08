from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QFontMetrics

class ElidedLabel(QLabel):
    def __init__(self, text="", alignment=Qt.AlignmentFlag.AlignCenter, parent=None):
        super().__init__(text, parent)
        self._full_text = text
        self._alignment = alignment

    def setText(self, text: str):
        self._full_text = text
        self.setToolTip(text)
        self.update()

    def text(self) -> str:
        return self._full_text

    def paintEvent(self, event):
        painter = QPainter(self)
        metrics = QFontMetrics(self.font())
        elided_text = metrics.elidedText(self._full_text, Qt.TextElideMode.ElideRight, self.width())
        
        painter.setFont(self.font())
        painter.setPen(self.palette().text().color())
        painter.drawText(self.rect(), self._alignment | Qt.AlignmentFlag.AlignVCenter, elided_text)
