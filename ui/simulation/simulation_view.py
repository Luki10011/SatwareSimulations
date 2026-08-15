
import json

from PyQt6.QtWidgets import QHBoxLayout, QMessageBox, QSizePolicy, QWidget, QSplitter
from PyQt6.QtCore import Qt

from core.physics.dataclasses.orbital_data import OrbitalElements
from core.physics.dataclasses.satellite_configuration import SatelliteConfiguration
from ui.simulation.components.simulation_controlls import SimulationControls
from ui.simulation.components.simulation_scene import SimulationScene
from utils.ui.ui_utils import show_dark_message_box




class SimulationView(QWidget):

    def __init__(self, orbital_data : OrbitalElements, satellite_data : SatelliteConfiguration, parent=None):
        super().__init__(parent)        
        self.orbital_data : OrbitalElements= orbital_data
        self.satellite_data : SatelliteConfiguration = satellite_data
        self.setup_view()

    def load_simulation(self, orbital_data : OrbitalElements, satellite_data : SatelliteConfiguration):
        self.orbital_data  = orbital_data
        self.satellite_data = satellite_data
        print("Simulation data successfully loaded into SimulationView.")

        self.controls_panel_container.update_data(
            orbital_data=orbital_data,
            satellite_data=satellite_data
        )

    def reset(self):
        self.controls_panel_container.reset()

    def load_simulation_from_file(self, file_path : str) -> None:
        """Load a saved SimulationConfiguration JSON back into the editor."""
        self.reset()
        try:
            with open(file_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, ValueError, TypeError):
            show_dark_message_box(
                self,
                "Load failed",
                "The selected file could not be read as a simulation configuration.",
                icon=QMessageBox.Icon.Warning,
            )
            return

        self.controls_panel_container.load_from_file(payload)

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