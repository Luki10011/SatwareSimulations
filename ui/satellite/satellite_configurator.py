
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QSplitter,
    QVBoxLayout,
    QWidget,
    QFormLayout
)
from PyQt6.QtCore import Qt

from ui.satellite.components.satellite_controls import SatelliteControls
from ui.satellite.components.satellite_scene import SatelliteScene

class SatelliteConfigurator(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_view()

    def setup_view(self) -> None:
        """Create the main window layout and initialize the 3D scene."""
        layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.satellite_controls = SatelliteControls()
        self.satellite_view = SatelliteScene()

        # Index 0
        splitter.addWidget(self.satellite_controls)
        # Index 1
        splitter.addWidget(self.satellite_view)

        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

    def reset(self):
        pass

