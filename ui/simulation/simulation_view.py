
from PyQt6.QtWidgets import QHBoxLayout, QSizePolicy, QWidget, QSplitter
from PyQt6.QtCore import Qt

from core.physics.dataclasses.orbital_data import OrbitalElements
from core.physics.dataclasses.satellite_configuration import SatelliteConfiguration
from ui.simulation.components.simulation_controlls import SimulationControls
from ui.simulation.components.simulation_scene import SimulationScene




class SimulationView(QWidget):

    def __init__(self, orbital_data : OrbitalElements, satellite_data : SatelliteConfiguration, parent=None):
        super().__init__(parent)        
        self.orbital_data : OrbitalElements= orbital_data
        self.satellite_data : SatelliteConfiguration = satellite_data

    def load_simulation(self, orbital_data : OrbitalElements, satellite_data : SatelliteConfiguration):
        self.orbital_data  = orbital_data
        self.satellite_data = satellite_data
        print("Simulation data successfully loaded into SimulationView.")
        self.setup_view()


    def setup_view(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.controls_panel_container = SimulationControls(
            orbital_data=self.orbital_data,
            satellite_data=self.satellite_data
        )
        self.controls_panel_container.setMinimumWidth(360)
        self.controls_panel_container.setMaximumWidth(480)
        self.controls_panel_container.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Expanding,
        )
        
        self.scene_panel_container = SimulationScene()

        splitter.addWidget(self.controls_panel_container)
        splitter.addWidget(self.scene_panel_container)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        main_layout.addWidget(splitter)