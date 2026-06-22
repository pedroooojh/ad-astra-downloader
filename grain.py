import os
import random

from PySide6.QtCore import Qt, QTimer, QPoint, QEvent
from PySide6.QtGui import QPainter, QPixmap, QImage
from PySide6.QtWidgets import QWidget


def _make_grain_pixmap(size=256):
    noise = bytearray(os.urandom(size * size))
    alpha_raw = bytearray(os.urandom(size * size))
    buf = bytearray(size * size * 4)
    for i in range(size * size):
        b = i * 4
        v = noise[i]
        buf[b] = buf[b + 1] = buf[b + 2] = v
        buf[b + 3] = 3 + (alpha_raw[i] % 18)  # alpha 3–21 (~1–8%)
    img = QImage(bytes(buf), size, size, size * 4, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(img)


class GrainOverlay(QWidget):
    def __init__(self, parent, fps=12, opacity=0.9):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._tex = _make_grain_pixmap()
        self._opacity = opacity
        self._off = QPoint(0, 0)

        parent.installEventFilter(self)
        self.setGeometry(parent.rect())
        self.raise_()

        if fps > 0:
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._tick)
            self._timer.start(max(1, int(1000 / fps)))

    def _tick(self):
        w, h = self._tex.width(), self._tex.height()
        self._off = QPoint(random.randint(0, w - 1), random.randint(0, h - 1))
        self.update()

    def eventFilter(self, obj, ev):
        if obj is self.parent() and ev.type() == QEvent.Type.Resize:
            self.setGeometry(self.parent().rect())
            self.raise_()
        return super().eventFilter(obj, ev)

    def paintEvent(self, _):
        if self._tex.isNull():
            return
        p = QPainter(self)
        p.setOpacity(self._opacity)
        p.drawTiledPixmap(self.rect(), self._tex, self._off)
