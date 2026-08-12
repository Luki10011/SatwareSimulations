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
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from core.physics.dataclasses.orbital_data import OrbitalElements
from core.physics.dataclasses.satellite_configuration import SatelliteConfiguration, build_satellite_configuration, validate_satellite_configuration_data
from ui.main_screen.components.predefined_orbit import PredefinedOrbitDialog
from utils.constants import ORBITAL_RANGES, ORBITS_DATA
import numpy as np
from utils.ui.ui_utils import apply_dark_title_bar, show_dark_message_box


class SimulationDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Simulation")
        self.resize(920, 600)
        apply_dark_title_bar(self)

        self.selected_orbit : OrbitalElements = None
        self.selected_satellite : SatelliteConfiguration = None

        self.orbital_ranges = ORBITAL_RANGES

        self.setup_view()

        self.COMMON_STYLE = """
            body {
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
                color: #e0e0e0;
                background-color: #1e1e1e;
                margin: 5px;
            }
            h2 {
                color: #ffffff;
                border-bottom: 1px solid #0288d1;
                padding-bottom: 4px;
                margin-top: 14px;
                margin-bottom: 8px;
                font-size: 14px;
            }
            .summary-table {
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 10px;
            }
            .summary-table td {
                padding: 4px 8px;
                border-bottom: 1px solid #2a2a2a;
            }
            .summary-table td.label {
                font-weight: bold;
                color: #b0bec5;
                width: 45%;
            }
            .summary-table td.value {
                color: #ffffff;
            }
            .tensor-table {
                border-collapse: collapse;
                margin-top: 6px;
                margin-bottom: 10px;
            }
            .tensor-table td {
                border: 1px solid #3f3f3f;
                padding: 5px 10px;
                text-align: right;
                font-family: 'Consolas', 'Courier New', monospace;
                background-color: #252526;
                color: #ffffff;
            }
            .badge {
                background-color: #0288d1;
                color: #ffffff;
                padding: 2px 6px;
                border-radius: 3px;
                font-size: 11px;
                font-weight: bold;
            }
        """

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
        
        self.lbl_sat_summary = QTextBrowser()
        self.lbl_sat_summary.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        layout.addWidget(self.lbl_sat_summary)
        return widget

    def _create_orbit_summary_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.lbl_orbit_summary = QTextBrowser()
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
            "tabs on the right will unlock, enabling the creation of the simulation.\n\n"
            "Note / Disclaimer:\n\n"
            "At this stage, initial conditions (such as starting attitude, angular position, "
            "and angular velocities) cannot be configured yet. You will be able to set these "
            "parameters in the next module once the base simulation is created."
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
            show_dark_message_box(
                self,
                "Invalid configuration",
                "Loaded configuration is invalid:\n" + "\n".join(errors.values() if isinstance(errors, dict) else errors),
                icon=QMessageBox.Icon.Warning
            )
            self.selected_satellite = None
        else:
            self.selected_satellite = build_satellite_configuration(data)
            show_dark_message_box(
                self,
                "Loaded",
                f"Configuration loaded from {file_path}",
                icon=QMessageBox.Icon.Information
            )
        self._update_ui_state()

    def _on_load_predefined_orbit(self) -> None:
        dialog = PredefinedOrbitDialog(ORBITS_DATA, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            orbit_data = dialog.get_selected_orbit_data()
            
            if orbit_data:
                elements = orbit_data["elements"]
                self.selected_orbit = self.build_orbit_configuration(elements)

                show_dark_message_box(
                    self,
                    "Loaded",
                    f"Predefined configuration has been successfully loaded.",
                    icon=QMessageBox.Icon.Information
                )

                self._update_ui_state()
            

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
            show_dark_message_box(
                self,
                "Invalid configuration",
                "Loaded configuration is invalid:\n" + "\n".join(errors),
                icon=QMessageBox.Icon.Warning
            )
            self.selected_orbit = None
        else:
            self.selected_orbit = self.build_orbit_configuration(data)
            show_dark_message_box(
                self,
                "Loaded",
                f"Configuration loaded from {file_path}",
                icon=QMessageBox.Icon.Information
            )
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
            self.lbl_sat_summary.setHtml("No satellite configuration loaded.")
            self.lbl_sat_status.setText("Status: Pending selection")
            self.lbl_sat_status.setStyleSheet("color: #ffa726; font-size: 9pt;")
            return

        self.lbl_sat_status.setText("Status: Valid configuration loaded.")
        self.lbl_sat_status.setStyleSheet("color: #66bb6a; font-size: 9pt;")
        self.lbl_sat_summary.setHtml(self.get_satellite_summary_html(self.selected_satellite))

    def get_satellite_summary_html(self, sat_config: Any) -> str:
        mech = self._get_val(sat_config, "mechanical")
        em = self._get_val(sat_config, "electromagnetic")
        rw = self._get_val(sat_config, "reaction_wheels")

        # Mechanical fields
        m = self._get_val(mech, "m")
        dim_a = self._get_val(mech, "a")
        dim_b = self._get_val(mech, "b")
        dim_h = self._get_val(mech, "h")
        I_tensor = self._get_val(mech, "I", np.zeros((3, 3)))

        # Coils fields
        n_turns = self._get_val(em, "N")
        area = self._get_val(em, "A")
        i_max = self._get_val(em, "I_max")

        # Reaction wheels fields
        rw_config = self._get_val(rw, "configuration", "n/a")
        rw_count = self._get_val(rw, "wheel_count", "n/a")
        rw_mass = self._get_val(rw, "wheel_mass")
        rw_radius = self._get_val(rw, "wheel_radius")
        rw_height = self._get_val(rw, "wheel_height")
        rw_speed = self._get_val(rw, "wheel_max_speed")

        # Format tensor matrix safely
        if not isinstance(I_tensor, np.ndarray) or I_tensor.shape != (3, 3):
            I_tensor = np.zeros((3, 3))

        return f"""<!DOCTYPE html>
            <html>
            <head>
            <style>
            {self.COMMON_STYLE}
            </style>
            </head>
            <body>
                <h2>Satellite Mechanical Properties</h2>
                <table class="summary-table">
                    <tr>
                        <td class="label">Total Mass:</td>
                        <td class="value">{self.fmt(m, "{:.3f}")} kg</td>
                    </tr>
                    <tr>
                        <td class="label">Dimensions (a x b x h):</td>
                        <td class="value">{self.fmt(dim_a, "{:.3f}")} x {self.fmt(dim_b, "{:.3f}")} x {self.fmt(dim_h, "{:.3f}")} m</td>
                    </tr>
                </table>

                <h2>Electromagnetic Coils</h2>
                <table class="summary-table">
                    <tr>
                        <td class="label">Turns Count:</td>
                        <td class="value">{self.fmt(n_turns, "{:d}")}</td>
                    </tr>
                    <tr>
                        <td class="label">Coil Area:</td>
                        <td class="value">{self.fmt(area, "{:.4f}")} m²</td>
                    </tr>
                    <tr>
                        <td class="label">Max Current:</td>
                        <td class="value">{self.fmt(i_max, "{:.3f}")} A</td>
                    </tr>
                </table>

                <h2>Reaction Wheels Subsystem</h2>
                <table class="summary-table">
                    <tr>
                        <td class="label">Configuration:</td>
                        <td class="value">
                            <span>{str(rw_config).upper()}</span> 
                            ({rw_count} wheels)
                        </td>
                    </tr>
                    <tr>
                        <td class="label">Single Wheel Mass:</td>
                        <td class="value">{self.fmt(rw_mass, "{:.3f}")} kg</td>
                    </tr>
                    <tr>
                        <td class="label">Wheel Dimensions (r, h):</td>
                        <td class="value">{self.fmt(rw_radius, "{:.3f}")} m, {self.fmt(rw_height, "{:.3f}")} m</td>
                    </tr>
                    <tr>
                        <td class="label">Max Speed:</td>
                        <td class="value">{self.fmt(rw_speed, "{:,.0f}")} RPM</td>
                    </tr>
                </table>

                <h2>Body Inertia Tensor [kg·m²]</h2>
                <table class="tensor-table">
                    <tr>
                        <td>{self.fmt(I_tensor[0, 0], "{:.6f}")}</td>
                        <td>{self.fmt(I_tensor[0, 1], "{:.6f}")}</td>
                        <td>{self.fmt(I_tensor[0, 2], "{:.6f}")}</td>
                    </tr>
                    <tr>
                        <td>{self.fmt(I_tensor[1, 0], "{:.6f}")}</td>
                        <td>{self.fmt(I_tensor[1, 1], "{:.6f}")}</td>
                        <td>{self.fmt(I_tensor[1, 2], "{:.6f}")}</td>
                    </tr>
                    <tr>
                        <td>{self.fmt(I_tensor[2, 0], "{:.6f}")}</td>
                        <td>{self.fmt(I_tensor[2, 1], "{:.6f}")}</td>
                        <td>{self.fmt(I_tensor[2, 2], "{:.6f}")}</td>
                    </tr>
                </table>
            </body>
            </html>"""

    def _update_orbit_summary(self) -> None:
        """Aktualizuje podsumowanie konfiguracji orbity w zakładce Orbit."""
        if self.selected_orbit is None:
            self.lbl_orbit_summary.setText("No orbit configuration loaded.")
            self.lbl_orbit_status.setText("Status: Pending selection")
            self.lbl_orbit_status.setStyleSheet("color: #ffa726; font-size: 9pt;")
            return

        self.lbl_orbit_status.setText("Status: Valid configuration loaded.")
        self.lbl_orbit_status.setStyleSheet("color: #66bb6a; font-size: 9pt;")
        self.lbl_orbit_summary.setHtml(self.get_orbit_summary_html(self.selected_orbit))

    def fmt(self, value: Any, spec: str = "{:.4f}") -> str:
        """Helper function to format numbers safely, handling None and strings."""
        if value is None:
            return "N/A"
        if isinstance(value, (int, float)):
            try:
                return spec.format(value)
            except (ValueError, TypeError):
                return str(value)
        return str(value)


    def _get_val(self, obj: Any, attr: str, default: Any = None) -> Any:
        """Helper to retrieve attribute from dataclass or dict."""
        if isinstance(obj, dict):
            return obj.get(attr, default)
        return getattr(obj, attr, default)

    def get_orbit_summary_html(self, orbital_elements: Any) -> str:
        """Generates HTML summary for OrbitalElements."""
        a_km = self._get_val(orbital_elements, "semi_major_axis", 0.0)
        e = self._get_val(orbital_elements, "eccentricity", 0.0)
        inc_deg = self._get_val(orbital_elements, "inclination", 0.0)
        raan_deg = self._get_val(orbital_elements, "raan", 0.0)
        arg_p_deg = self._get_val(orbital_elements, "arg_perigee", 0.0)
        nu_deg = self._get_val(orbital_elements, "true_anomaly", 0.0)

        return f"""<!DOCTYPE html>
        <html>
        <head>
        <style>
        {self.COMMON_STYLE}
        </style>
        </head>
        <body>
            <h2>Orbital Elements (Keplerian)</h2>
            <table class="summary-table">
                <tr>
                    <td class="label">Semi-Major Axis (a):</td>
                    <td class="value">{self.fmt(a_km, "{:,.2f}")} km </td>
                </tr>
                <tr>
                    <td class="label">Eccentricity (e):</td>
                    <td class="value">{self.fmt(e, "{:.4f}")}</td>
                </tr>
                <tr>
                    <td class="label">Inclination (i):</td>
                    <td class="value">{self.fmt(inc_deg, "{:.2f}")}° </td>
                </tr>
                <tr>
                    <td class="label">RAAN (Ω):</td>
                    <td class="value">{self.fmt(raan_deg, "{:.2f}")}° </td>
                </tr>
                <tr>
                    <td class="label">Argument of Perigee (ω):</td>
                    <td class="value">{self.fmt(arg_p_deg, "{:.2f}")}° </td>
                </tr>
                <tr>
                    <td class="label">True Anomaly (ν):</td>
                    <td class="value">{self.fmt(nu_deg, "{:.2f}")}° </td>
                </tr>
            </table>
        </body>
        </html>"""