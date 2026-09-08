import time
from typing import Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QMouseEvent, QWheelEvent, QKeyEvent
from PyQt6.QtWidgets import QSlider, QStyle, QStyleOptionSlider, QWidget


class SeekSlider(QSlider):
    """
    Barra de progreso interactiva de alta fidelidad para reproducción de audio.
    Soporta:
    - Salto directo e instantáneo al hacer clic en cualquier punto de la pista/ranura (groove).
    - Arrastre suave y continuo sin importar si se inició en el tirador o en la pista.
    - Soporte para rueda del ratón (desplazamiento +/- 1.5% o ~5 segundos).
    - Teclas de flecha (Izquierda/Derecha) para saltar rápidamente.
    - Emisión precisa del ciclo de señales (sliderPressed -> sliderMoved -> sliderReleased).
    """

    def __init__(self, orientation: Qt.Orientation = Qt.Orientation.Horizontal, parent: Optional[QWidget] = None) -> None:
        super().__init__(orientation, parent)
        self._is_seeking: bool = False
        self.setMouseTracking(True)

    def is_user_seeking(self) -> bool:
        """Devuelve True si el usuario está actualmente arrastrando o presionando el slider."""
        return self._is_seeking

    def _value_from_pos(self, x: float) -> int:
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        handle_rect = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider, opt, QStyle.SubControl.SC_SliderHandle, self
        )
        handle_w = handle_rect.width() if handle_rect.isValid() and handle_rect.width() > 0 else 18

        avail_w = max(1.0, float(self.width() - handle_w))
        pos_x = x - (handle_w / 2.0)
        ratio = max(0.0, min(1.0, pos_x / avail_w))

        val = int(round(self.minimum() + ratio * (self.maximum() - self.minimum())))
        return max(self.minimum(), min(self.maximum(), val))

    def mousePressEvent(self, ev: QMouseEvent) -> None:
        if ev.button() == Qt.MouseButton.LeftButton:
            self._is_seeking = True
            self.setSliderDown(True)
            val = self._value_from_pos(ev.position().x())
            self.setValue(val)
            ev.accept()
        else:
            super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev: QMouseEvent) -> None:
        if self._is_seeking and (ev.buttons() & Qt.MouseButton.LeftButton):
            val = self._value_from_pos(ev.position().x())
            self.setValue(val)
            ev.accept()
        else:
            super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev: QMouseEvent) -> None:
        if ev.button() == Qt.MouseButton.LeftButton and self._is_seeking:
            val = self._value_from_pos(ev.position().x())
            self.setValue(val)
            self._is_seeking = False
            self.setSliderDown(False)
            ev.accept()
        else:
            super().mouseReleaseEvent(ev)

    def wheelEvent(self, ev: QWheelEvent) -> None:
        delta = ev.angleDelta().y()
        if delta != 0:
            # Salto proporcional de ~1.5% del rango por muesca de scroll
            step = max(1, (self.maximum() - self.minimum()) // 66)
            direction = 1 if delta > 0 else -1
            target_val = max(self.minimum(), min(self.maximum(), self.value() + direction * step))
            if target_val != self.value():
                self.setSliderDown(True)
                self.setValue(target_val)
                self.setSliderDown(False)
        ev.accept()

    def keyPressEvent(self, ev: QKeyEvent) -> None:
        key = ev.key()
        if key in (Qt.Key.Key_Left, Qt.Key.Key_Down):
            step = max(1, (self.maximum() - self.minimum()) // 20)
            self.setSliderDown(True)
            self.setValue(max(self.minimum(), self.value() - step))
            self.setSliderDown(False)
            ev.accept()
        elif key in (Qt.Key.Key_Right, Qt.Key.Key_Up):
            step = max(1, (self.maximum() - self.minimum()) // 20)
            self.setSliderDown(True)
            self.setValue(min(self.maximum(), self.value() + step))
            self.setSliderDown(False)
            ev.accept()
        else:
            super().keyPressEvent(ev)
