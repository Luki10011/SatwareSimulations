
import pyqtgraph.opengl as gl

from PyQt6.QtWidgets import (
    QWidget
)

class SatelliteScene(QWidget):

    def __init__(self, parent = None):
        super().__init__(parent)
        self.view = None
        self.setup_view()

    def setup_view(self):
        self.view = gl.GLViewWidget()