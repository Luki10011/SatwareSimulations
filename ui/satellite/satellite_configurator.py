
import json
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QMessageBox, QSizePolicy, QSplitter, QWidget

from core.physics.dataclasses.satellite_configuration import build_satellite_configuration, serialize_satellite_configuration, validate_satellite_configuration_data
from ui.satellite.components.satellite_controls import SatelliteControls
from ui.satellite.components.satellite_scene import SatelliteScene


class SatelliteConfigurator(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_view()

    def setup_view(self) -> None:
        """Create the main window layout and initialize the 3D scene."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.satellite_controls = SatelliteControls()
        self.satellite_controls.setMinimumWidth(360)
        self.satellite_controls.setMaximumWidth(480)
        self.satellite_controls.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Expanding,
        )
        self.satellite_view = SatelliteScene()
        self.satellite_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.satellite_controls.configurationChanged.connect(self._sync_view)
        self.satellite_controls.saveRequested.connect(self._save_configuration)
        self.satellite_controls.loadRequested.connect(self._load_configuration)
        self.satellite_controls.resetRequested.connect(self.reset)

        splitter.addWidget(self.satellite_controls)
        splitter.addWidget(self.satellite_view)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([420, 780])
        layout.addWidget(splitter)

        self._sync_view(self.satellite_controls.get_configuration_data())

    def _sync_view(self, data: dict) -> None:
        self.satellite_view.update_from_data(data)

    def _save_configuration(self) -> None:
        self.satellite_controls.clear_errors()
        data = self.satellite_controls.get_configuration_data()
        errors = validate_satellite_configuration_data(data)
        if errors:
            self.satellite_controls.mark_errors(errors)
            QMessageBox.warning(self, "Invalid configuration", "\n".join(errors))
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save satellite configuration",
            str(Path.home() / "satellite_configuration.json"),
            "JSON files (*.json)",
        )
        if not file_path:
            return

        config = build_satellite_configuration(data)
        with open(file_path, "w", encoding="utf-8") as handle:
            json.dump(serialize_satellite_configuration(config), handle, indent=2)

        QMessageBox.information(self, "Saved", f"Configuration saved to {file_path}")

    def _load_configuration(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load satellite configuration",
            str(Path.home()),
            "JSON files (*.json)",
        )
        if not file_path:
            return

        with open(file_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)

        errors = validate_satellite_configuration_data(data)
        if errors:
            self.satellite_controls.mark_errors(errors)
            QMessageBox.warning(self, "Invalid configuration", "\n".join(errors))
            return

        self.satellite_controls.set_configuration_data(data)
        self._sync_view(data)
        QMessageBox.information(self, "Loaded", f"Configuration loaded from {file_path}")

    def reset(self) -> None:
        self.satellite_controls.set_configuration_data({
            "mechanical": {
                "mass": 12.5,
                "dimensions": [0.3, 0.2, 0.1],
                "inertia_tensor": [[0.02, 0.0, 0.0], [0.0, 0.015, 0.0], [0.0, 0.0, 0.01]],
            },
            "electromagnetic": {
                "coil_turns": 120,
                "coil_area": 0.04,
                "max_current": 2.5,
            },
            "reaction_wheels": {
                "configuration": "principal",
                "wheel_count": 3,
                "wheel_mass": 0.25,
                "wheel_radius": 0.05,
                "wheel_height": 0.02,
                "wheel_max_speed": 6000,
                "com_offset": [0.003, 0.002, 0.001],
            },
        })
        self._sync_view(self.satellite_controls.get_configuration_data())

