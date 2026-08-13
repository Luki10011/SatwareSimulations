import math
from typing import List, Tuple
import numpy as np

from PyQt6.QtWidgets import (
    QFormLayout, QHBoxLayout, QLabel, QLineEdit, QSizePolicy,
    QTabWidget, QWidget, QVBoxLayout, QFrame
)
from PyQt6.QtCore import QLocale, Qt
from PyQt6.QtGui import QDoubleValidator

from core.physics.dataclasses.orbital_data import OrbitalElements
from core.physics.dataclasses.satellite_configuration import SatelliteConfiguration


class SimulationControls(QWidget):
    def __init__(self, orbital_data: OrbitalElements, satellite_data: SatelliteConfiguration, parent=None):
        super().__init__(parent)
        self.orbital_data = orbital_data
        self.satellite_data = satellite_data
        
        self.us_locale = QLocale(QLocale.Language.English, QLocale.Country.UnitedStates)
        self.setup_view()
        
        # Wyliczenie wartości początkowych na podstawie orbity po załadowaniu
        self._update_calculated_state()

    def setup_view(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(10)

        self.tab_widget = QTabWidget(self)
        self.tab_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tab_widget.setObjectName("simulationTabWidget")
        main_layout.addWidget(self.tab_widget)

        self._initial_conditions_tab = QWidget(self)
        self._initial_conditions_tab.setObjectName("initial_conditions") 

        self._plots_tab = QWidget(self)
        self._plots_tab.setObjectName("plots")

        self._build_initial_conditions_tab()
        self._build_plots_tab()

        self.tab_widget.addTab(self._initial_conditions_tab, "Initial Conditions")
        self.tab_widget.addTab(self._plots_tab, "Simulation Plots")

    def _build_initial_conditions_tab(self) -> None:
        
        # Separator Line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #333333; margin-top: 6px; margin-bottom: 6px;")   

        form_layout = QFormLayout(self._initial_conditions_tab)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        form_layout.setHorizontalSpacing(15)
        form_layout.setVerticalSpacing(10)

        info_label = QLabel(
            "Please configure the initial simulation state. The satellite's initial position "
            "and orbital velocity are automatically computed based on the True Anomaly (ν)."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #b0bec5; font-size: 12px; margin-bottom: 4px;")

        

        # --- 1. ORBITAL ENVIRONMENT (Keplerian -> Cartesian) ---
        
        # True Anomaly Validator: Range -360.0 to 360.0
        val_nu = QDoubleValidator(-360.0, 360.0, 3, self)
        val_nu.setLocale(self.us_locale)
        val_nu.setNotation(QDoubleValidator.Notation.StandardNotation)

        # Inicjalizacja z wartością z obiektu orbital_data (w stopniach)
        init_nu_deg = getattr(self.orbital_data, "true_anomaly", 0.0)
        self.input_true_anomaly = self._create_line_edit(val_nu)
        self.input_true_anomaly.setText(f"{init_nu_deg:.3f}")
        self.input_true_anomaly.editingFinished.connect(self._update_calculated_state)

        # Calculated Position & Velocity Fields (Read-Only)
        val_read_only = QDoubleValidator(-1e9, 1e9, 3, self)
        val_read_only.setLocale(self.us_locale)

        self.calculated_position = [self._create_line_edit(val_read_only, read_only=True) for _ in range(3)]
        self.calculated_velocities = [self._create_line_edit(val_read_only, read_only=True) for _ in range(3)]

        pos_container = self._create_horizontal_inputs(self.calculated_position, placeholders=["X", "Y", "Z"])
        vel_container = self._create_horizontal_inputs(self.calculated_velocities, placeholders=["Vx", "Vy", "Vz"])

        form_layout.addRow(self._create_separator())

        form_layout.addRow(info_label)
        form_layout.addRow("True Anomaly (ν) [deg]:", self.input_true_anomaly)

        form_layout.addRow(self._create_separator())

        form_layout.addRow("ECI Position (x, y, z) [km]:", pos_container)
        form_layout.addRow("ECI Velocity (v_x, v_y, v_z) [km/s]:", vel_container)

        form_layout.addRow(self._create_separator())

        # --- 2. SATELLITE ATTITUDE & DYNAMICS ---

        # Euler Angles Validator: Range -360.0 to 360.0
        val_euler = QDoubleValidator(-360.0, 360.0, 3, self)
        val_euler.setLocale(self.us_locale)

        # Angular Velocity Validator: Range -1000.0 to 1000.0
        val_omega = QDoubleValidator(-1000.0, 1000.0, 4, self)
        val_omega.setLocale(self.us_locale)

        self.input_euler_angles = [self._create_line_edit(val_euler) for _ in range(3)]
        for edit in self.input_euler_angles:
            edit.setText("0.000")

        self.input_angular_velocity = [self._create_line_edit(val_omega) for _ in range(3)]
        for edit in self.input_angular_velocity:
            edit.setText("0.000")

        euler_container = self._create_horizontal_inputs(self.input_euler_angles, placeholders=["Roll (ϕ)", "Pitch (θ)", "Yaw (ψ)"])
        omega_container = self._create_horizontal_inputs(self.input_angular_velocity, placeholders=["ωx", "ωy", "ωz"])

        form_layout.addRow("Initial Euler Angles [deg]:", euler_container)
        form_layout.addRow("Initial Angular Velocity [deg/s]:", omega_container)
        

    def _build_plots_tab(self) -> None:
        form_layout = QFormLayout(self._plots_tab)
        # Tab plots logic will go here...

    def _create_separator(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #333333; margin-top: 6px; margin-bottom: 6px;")
        return line


    def _update_calculated_state(self) -> None:
        """Calculates and updates ECI Position and Velocity vectors based on True Anomaly."""
        try:
            nu_deg = float(self.input_true_anomaly.text().replace(',', '.'))
        except ValueError:
            nu_deg = 0.0

        nu_rad = math.radians(nu_deg)
        r_eci_km, v_eci_kms = self._kepler_to_eci(self.orbital_data, nu_rad)

        for idx, val in enumerate(r_eci_km):
            self.calculated_position[idx].setText(f"{val:,.3f}")

        for idx, val in enumerate(v_eci_kms):
            self.calculated_velocities[idx].setText(f"{val:,.3f}")

    @staticmethod
    def _kepler_to_eci(orbit: OrbitalElements, nu_rad: float) -> Tuple[np.ndarray, np.ndarray]:
        """Converts Keplerian elements to ECI Cartesian position (km) and velocity (km/s)."""
        a_m = getattr(orbit, "semi_major_axis", 7000000.0) * 1e3
        e = getattr(orbit, "eccentricity", 0.0)
        inc_rad = getattr(orbit, "inclination", 0.0)
        raan_rad = getattr(orbit, "raan", 0.0)
        arg_p_rad = getattr(orbit, "arg_perigee", 0.0)

        # Standard gravitational parameter of Earth (m^3 / s^2)
        mu = 3.986004418e14

        # Perifocal distance and radius
        p = a_m * (1.0 - e**2)
        r = p / (1.0 + e * math.cos(nu_rad))

        # Position in Perifocal Frame (PQW) [m]
        r_pqw = np.array([r * math.cos(nu_rad), r * math.sin(nu_rad), 0.0])

        # Velocity in Perifocal Frame (PQW) [m/s]
        h = math.sqrt(mu * p) if p > 0 else 1.0
        v_pqw = np.array([
            -(mu / h) * math.sin(nu_rad),
            (mu / h) * (e + math.cos(nu_rad)),
            0.0
        ])

        # Rotation Matrices PQW -> ECI
        cos_O, sin_O = math.cos(raan_rad), math.sin(raan_rad)
        cos_i, sin_i = math.cos(inc_rad), math.sin(inc_rad)
        cos_w, sin_w = math.cos(arg_p_rad), math.sin(arg_p_rad)

        R_z_O = np.array([[cos_O, -sin_O, 0], [sin_O, cos_O, 0], [0, 0, 1]])
        R_x_i = np.array([[1, 0, 0], [0, cos_i, -sin_i], [0, sin_i, cos_i]])
        R_z_w = np.array([[cos_w, -sin_w, 0], [sin_w, cos_w, 0], [0, 0, 1]])

        Q_pqw2eci = R_z_O @ R_x_i @ R_z_w

        r_eci_m = Q_pqw2eci @ r_pqw
        v_eci_ms = Q_pqw2eci @ v_pqw

        # Return values converted to km and km/s
        return r_eci_m / 1000.0, v_eci_ms / 1000.0


    def _create_line_edit(self, validator: QDoubleValidator, read_only: bool = False, parent=None) -> QLineEdit:
        line_edit = QLineEdit(self if parent is None else parent)
        line_edit.setValidator(validator)
        line_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        if read_only:
            line_edit.setReadOnly(True)
            line_edit.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            # Stylizowanie pół niemodyfikowalnych pod ciemny motyw
            line_edit.setStyleSheet("""
                QLineEdit {
                    background-color: #252526;
                    color: #ffffff;
                    border: 1px solid #3c3c3c;
                    border-radius: 3px;
                    padding: 3px;
                }
            """)
        return line_edit

    def _create_horizontal_inputs(self, inputs: List[QLineEdit], placeholders: List[str] = None, parent=None) -> QWidget:
        container = QWidget(self if parent is None else parent)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        for idx, input_field in enumerate(inputs):
            if placeholders and idx < len(placeholders):
                input_field.setPlaceholderText(placeholders[idx])
            layout.addWidget(input_field, stretch=1)

        return container