import json
from typing import Any, Tuple, Dict, List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.physics.dataclasses.orbital_data import OrbitalElements
from core.physics.dataclasses.satellite_configuration import SatelliteConfiguration, build_satellite_configuration, validate_satellite_configuration_data
from utils.constants import ORBITAL_RANGES

class SimulationDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Simulation")
        self.resize(920, 600)

        self.selected_orbit : OrbitalElements = None
        self.selected_satellite : SatelliteConfiguration = None

        self.orbital_ranges = ORBITAL_RANGES

        self.setup_view()

    def setup_view(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        left_panel = self._create_left_panel()
        content_layout.addWidget(left_panel, stretch=1)

        right_panel = self._create_right_panel()
        content_layout.addWidget(right_panel, stretch=1)

        main_layout.addLayout(content_layout)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.btn_ok = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        self.btn_ok.setEnabled(False)  

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        main_layout.addWidget(self.button_box)

    def _create_right_panel(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        header = QLabel("Configuration Overview")
        header.setStyleSheet("font-weight: bold; font-size: 11pt; color: #ffffff;")
        layout.addWidget(header)

        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("summaryTabWidget")

        self.tab_satellite = self._create_satellite_summary_tab()
        self.tab_widget.addTab(self.tab_satellite, "Satellite")

        self.tab_orbit = self._create_orbit_summary_tab()
        self.tab_widget.addTab(self.tab_orbit, "Orbit")

        self.tab_widget.setTabEnabled(0, False)
        self.tab_widget.setTabEnabled(1, False)

        layout.addWidget(self.tab_widget)
        return container

    def _create_satellite_summary_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.lbl_sat_summary = QLabel("No satellite configuration loaded.")
        self.lbl_sat_summary.setWordWrap(True)
        self.lbl_sat_summary.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        layout.addWidget(self.lbl_sat_summary)
        return widget

    def _create_orbit_summary_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.lbl_orbit_summary = QLabel("No orbit configuration loaded.")
        self.lbl_orbit_summary.setWordWrap(True)
        self.lbl_orbit_summary.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        layout.addWidget(self.lbl_orbit_summary)
        return widget

    def _create_left_panel(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        instructions_label = QLabel("Setup Instructions")
        instructions_label.setStyleSheet("font-weight: bold; font-size: 11pt; color: #ffffff; margin-bottom: 0px;")

        instructions_group = QGroupBox()
        instructions_layout = QVBoxLayout(instructions_group)
        
        info_text = (
            "To configure a new experiment, please follow these steps:\n\n"
            "1. Select a satellite configuration (custom file).\n"
            "2. Select orbital elements for the simulation environment.\n\n"
            "Once both valid configurations are loaded, the corresponding summary "
            "tabs on the right will unlock, enabling the creation of the simulation."
        )
        lbl_info = QLabel(info_text)
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet("color: rgba(255, 255, 255, 0.75); font-size: 9.5pt;")
        instructions_layout.addWidget(lbl_info)

        layout.addWidget(instructions_label)
        layout.addWidget(instructions_group)

        sat_group = QGroupBox("Satellite Configuration")
        sat_layout = QVBoxLayout(sat_group)
        
        self.lbl_sat_status = QLabel("Status: Pending selection")
        self.lbl_sat_status.setStyleSheet("color: #ffa726; font-size: 9pt;")

        btn_sat_custom = QPushButton("Load Custom Satellite File...")
        
        btn_sat_custom.clicked.connect(self._on_load_custom_satellite)

        sat_layout.addWidget(self.lbl_sat_status)
        sat_layout.addWidget(btn_sat_custom)
        layout.addWidget(sat_group)

        # Sekcja 2: Wybór Orbity
        orbit_group = QGroupBox("Orbit Configuration")
        orbit_layout = QVBoxLayout(orbit_group)

        self.lbl_orbit_status = QLabel("Status: Pending selection")
        self.lbl_orbit_status.setStyleSheet("color: #ffa726; font-size: 9pt;")

        btn_orbit_predefined = QPushButton("Load Predefined Orbit")
        btn_orbit_custom = QPushButton("Load Custom Orbit File...")

        btn_orbit_predefined.clicked.connect(self._on_load_predefined_orbit)
        btn_orbit_custom.clicked.connect(self._on_load_custom_orbit)

        orbit_layout.addWidget(self.lbl_orbit_status)
        orbit_layout.addWidget(btn_orbit_predefined)
        orbit_layout.addWidget(btn_orbit_custom)
        layout.addWidget(orbit_group)

        layout.addStretch()
        return container

    def _on_load_custom_satellite(self) -> None:
        """Slot for loading a custom satellite configuration file."""

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Satellite Configuration",
            "",
            "JSON Files (*.json);;All Files (*)"
        )

        if not file_path:
            return

        with open(file_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)

        errors = validate_satellite_configuration_data(data)
        if errors:
            QMessageBox.warning(self, "Invalid configuration", "Loaded configuration is invalid:\n" + "\n".join(errors.values() if isinstance(errors, dict) else errors))
            self.selected_satellite = None
        else:
            self.selected_satellite = build_satellite_configuration(data)
            QMessageBox.information(self, "Loaded", f"Configuration loaded from {file_path}")
        self._update_ui_state()

    def _on_load_predefined_orbit(self) -> None:
        """Slot for loading a predefined orbit."""
        pass

    def _on_load_custom_orbit(self) -> None:
        """Slot for loading a custom orbit file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Orbit Configuration",
            "",
            "JSON Files (*.json);;All Files (*)"
        )

        if not file_path:
            return

        with open(file_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)   

        errors = self.validate_orbit_configuration_data(data)
        if errors:
            QMessageBox.warning(self, "Invalid configuration", "Loaded configuration is invalid:\n" + "\n".join(errors))
            self.selected_orbit = None 
        else:
            self.selected_orbit = self.build_orbit_configuration(data)
            QMessageBox.information(self, "Loaded", f"Configuration loaded from {file_path}")
        self._update_ui_state()

    def build_orbit_configuration(self, data : Dict[str, Any]) -> OrbitalElements:
        return OrbitalElements(
            semi_major_axis=data["semi_major_axis"],
            eccentricity=data["eccentricity"],
            inclination=data["inclination"],
            raan=data["raan"],
            arg_perigee=data["arg_perigee"],
            true_anomaly=data["true_anomaly"]
        )

    def validate_orbit_configuration_data(self,
        data: Any,
        earth_radius_km: float = 6371.0
    ) -> List[str]:
        """
        Validates a dictionary containing orbital elements loaded from JSON 
        against user-defined ranges and physical constraints.
        """
        errors: List[str] = []

        if not isinstance(data, dict):
            return ["Invalid JSON structure: Root element must be an object/dictionary."]

        # Mapowanie kluczy z pliku JSON na
        param_mapping = {
            "semi_major_axis": ("a", "Semi-major axis (a)"),
            "eccentricity": ("e", "Eccentricity (e)"),
            "inclination": ("i", "Inclination (i)"),
            "raan": ("RAAN", "RAAN (Ω)"),
            "arg_perigee": ("arg_perigee", "Argument of Perigee (ω)"),
            "true_anomaly": ("true_anomaly", "True Anomaly (ν)"),
        }

        parsed_values: Dict[str, float] = {}

        for json_key, (range_key, label) in param_mapping.items():
            if json_key not in data:
                errors.append(f"Missing required field: '{json_key}' ({label}).")
                continue

            val = data[json_key]
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                errors.append(f"Field '{json_key}' ({label}) must be a valid numeric value.")
                continue

            float_val = float(val)
            parsed_values[json_key] = float_val

            if range_key in self.orbital_ranges:
                min_val, max_val = self.orbital_ranges[range_key]
                if not (min_val <= float_val <= max_val):
                    errors.append(
                        f"Field '{json_key}' ({label}) value {float_val:.2f} is out of allowed range [{min_val:.2f}, {max_val:.2f}]."
                    )

        if errors:
            return errors

        a = parsed_values["semi_major_axis"]
        e = parsed_values["eccentricity"]

        perigee_distance = a * (1.0 - e)
        if perigee_distance < earth_radius_km:
            errors.append(
                f"Perigee distance ({perigee_distance:.2f} km) is below Earth's radius ({earth_radius_km:.2f} km). "
                "The orbit would intersect with Earth."
            )

        return errors

    def _update_ui_state(self) -> None:
        """Pomocnicza metoda do aktualizacji stanu zakładek oraz przycisku OK."""
        sat_valid = self.selected_satellite is not None
        orbit_valid = self.selected_orbit is not None

        self.tab_widget.setTabEnabled(0, sat_valid)
        self._update_satellite_summary()

        self.tab_widget.setTabEnabled(1, orbit_valid)
        self._update_orbit_summary()

        self.btn_ok.setEnabled(sat_valid and orbit_valid)

    def _update_satellite_summary(self) -> None:
        """Aktualizuje podsumowanie konfiguracji satelity w zakładce Satellite."""
        if self.selected_satellite is None:
            self.lbl_sat_summary.setText("No satellite configuration loaded.")
            self.lbl_sat_status.setText("Status: Pending selection")
            self.lbl_sat_status.setStyleSheet("color: #ffa726; font-size: 9pt;")
            return

        self.lbl_sat_status.setText("Status: Valid configuration loaded.")
        self.lbl_sat_status.setStyleSheet("color: #66bb6a; font-size: 9pt;")
        self.lbl_sat_summary.setText(f"Satellite configuration loaded successfully.")

    def _update_orbit_summary(self) -> None:
        """Aktualizuje podsumowanie konfiguracji orbity w zakładce Orbit."""
        if self.selected_orbit is None:
            self.lbl_orbit_summary.setText("No orbit configuration loaded.")
            self.lbl_orbit_status.setText("Status: Pending selection")
            self.lbl_orbit_status.setStyleSheet("color: #ffa726; font-size: 9pt;")
            return

        self.lbl_orbit_status.setText("Status: Valid configuration loaded.")
        self.lbl_orbit_status.setStyleSheet("color: #66bb6a; font-size: 9pt;")
        self.lbl_orbit_summary.setText(f"Orbit configuration loaded successfully.")