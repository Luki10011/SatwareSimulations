
from PyQt6.QtWidgets import QVBoxLayout, QWidget

import numpy as np
import pyqtgraph.opengl as gl

from PyQt6.QtGui import QColor, QImage
from ui.orbits.components.orbit_scene import OrbitSceneHelper

class SimulationScene(QWidget):

    def __init__(self, parent = None):
        super().__init__(parent)

        self.view = None

        self.setup_view()


    def setup_view(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.view = gl.GLViewWidget()
        self.earth = OrbitSceneHelper.create_earth(rows=300, cols=600)
        
        self.view.addItem(self.earth)
        self.view.setCameraPosition(distance=15000, elevation=30, azimuth=30)
        self.view.setCameraParams()
        self.view.opts["glOptions"] = "opaque"

        layout.addWidget(self.view)