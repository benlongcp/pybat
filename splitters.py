from PyQt6.QtWidgets import QSplitter, QSplitterHandle
from PyQt6.QtGui import QPainter, QColor


class DoubleLineSplitterHandle(QSplitterHandle):
    def __init__(self, orientation, parent):
        super().__init__(orientation, parent)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        w = self.width()
        h = self.height()
        painter.setPen(QColor(0, 0, 0))
        painter.drawLine(1, 0, 1, h)
        painter.setPen(QColor(68, 68, 68))
        painter.drawLine(3, 0, 3, h)
        painter.end()


class DoubleLineSplitter(QSplitter):
    def createHandle(self):
        return DoubleLineSplitterHandle(self.orientation(), self)
