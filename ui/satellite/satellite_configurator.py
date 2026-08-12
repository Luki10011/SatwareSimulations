import json
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QMessageBox, QSizePolicy, QSplitter, QWidget

from core.physics.dataclasses.satellite_configuration import build_satellite_configuration, serialize_satellite_configuration, validate_satellite_configuration_data
from ui.satellite.components.satellite_controls import SatelliteControls
from ui.satellite.components.satellite_scene import SatelliteScene
from utils.ui.ui_utils import show_dark_message_box

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
        self.satellite_controls.loadRequested.connect(self.load_configuration)
        self.satellite_controls.resetRequested.connect(self.reset)

        splitter.addWidget(self.satellite_controls)
        splitter.addWidget(self.satellite_view)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([420, 780])
        layout.addWidget(splitter)

        self._sync_view(self.satellite_controls.get_configuration_data(), mark_errors=False)

    def _sync_view(self, data: dict, mark_errors: bool = False) -> None:
        if getattr(self.satellite_controls, "_pristine", True):
            self.satellite_controls.clear_errors()
            try:
                self.satellite_view._clear_scene()
            except Exception:
                pass
            return

        errors = validate_satellite_configuration_data(data)

        if mark_errors:
            if errors:
                self.satellite_controls.mark_errors(errors)
                try:
                    self.satellite_view._clear_scene()
                except Exception:
                    pass
                return
            else:
                self.satellite_controls.clear_errors()

        if errors:
            self.satellite_controls.tab_widget.setTabEnabled(2, False)
        else:
            self.satellite_controls.tab_widget.setTabEnabled(2, True)

        has_mass_error = "mass" in errors
        has_dim_error = any(k in errors for k in ("dimensions", "dim_a", "dim_b", "dim_h"))

        if not has_mass_error and not has_dim_error:
            self.satellite_view.update_from_data(data)

    def _save_configuration(self) -> None:
        self.satellite_controls.clear_errors()
        data = self.satellite_controls.get_configuration_data()
        errors = validate_satellite_configuration_data(data)
        if errors:
            self.satellite_controls.mark_errors(errors)
            show_dark_message_box(
                self,
                "Invalid configuration",
                "\n".join(errors.values() if isinstance(errors, dict) else errors),
                icon=QMessageBox.Icon.Warning
            )
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

        show_dark_message_box(
            self,
            "Saved",
            f"Configuration saved to {file_path}",
            icon=QMessageBox.Icon.Information
        )

    def load_configuration(self, file_path: str) -> None:
        
        if not file_path:
            return

        with open(file_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)

        errors = validate_satellite_configuration_data(data)
        if errors:
            self.satellite_controls.mark_errors(errors)
            show_dark_message_box(
                self,
                "Invalid configuration",
                "\n".join(errors.values() if isinstance(errors, dict) else errors),
                icon=QMessageBox.Icon.Warning
            )
            return

        self.satellite_controls.set_configuration_data(data)
        self._sync_view(data, mark_errors=False)
        show_dark_message_box(
            self,
            "Loaded",
            f"Configuration loaded from {file_path}",
            icon=QMessageBox.Icon.Information
        )

    def reset_satellite_configurator(self):
        self.satellite_controls.tab_widget.setCurrentIndex(0)
        self.reset()
        self.satellite_view.view.setCameraPosition(distance=6, elevation=20, azimuth=35)

    def reset(self) -> None:
        self.satellite_controls.set_configuration_data({
            "mechanical": {
                "mass": "",
                "dimensions": [],
                "inertia_tensor": [],
            },
            "electromagnetic": {
                "coil_turns": "",
                "coil_area": "",
                "max_current": "",
            },
            "reaction_wheels": {
                "configuration": "principal",
                "wheel_count": 3,
                "wheel_mass": "",
                "wheel_radius": "",
                "wheel_height": "",
                "wheel_max_speed": "",
                "inertia_tensor": [],
            },
        })
        self.satellite_controls._pristine = True
        self.satellite_controls.clear_errors()
        self._sync_view(self.satellite_controls.get_configuration_data(), mark_errors=False)