# splitters.py - Custom splitter widgets for UI layout
# This module provides custom splitter classes inheriting from QSplitter and QSplitterHandle.
# These classes are used to create adjustable panels in the user interface, allowing for dynamic
# resizing of widgets within the main window.

# TODO: Add comments to all splitter classes and functions, including any stubs or placeholders.

from PyQt6.QtWidgets import QSplitter, QSplitterHandle
from PyQt6.QtGui import QPainter, QColor


class DoubleLineSplitterHandle(QSplitterHandle):
    """
    Custom handle for the splitter, drawing double lines for visual feedback.
    """

    def __init__(self, orientation, parent):
        """
        Initialize the handle with the given orientation and parent.

        :param orientation: Orientation of the splitter (horizontal or vertical).
        :param parent: Parent widget.
        """
        super().__init__(orientation, parent)

    def paintEvent(self, event):
        """
        Handle the paint event to draw custom lines on the splitter handle.

        :param event: The paint event.
        """
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
    """
    Custom splitter class that uses DoubleLineSplitterHandle for its handles.
    """

    def createHandle(self):
        """
        Create and return a new handle for the splitter.

        :return: A new instance of DoubleLineSplitterHandle.
        """
        return DoubleLineSplitterHandle(self.orientation(), self)
