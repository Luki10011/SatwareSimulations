import json
import math
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple
import numpy as np

from PyQt6.QtWidgets import (
    QComboBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox, QSizePolicy,
    QTabWidget, QWidget, QVBoxLayout, QFrame
)
from PyQt6.QtCore import QCoreApplication, QLocale, QSignalBlocker, Qt, pyqtSignal
from PyQt6.QtGui import QDoubleValidator

from core.physics.dataclasses.satellite_state import SatelliteState
from core.physics.dataclasses.simulation_data import (
    TRUE_ANOMALY_MIN,
    TRUE_ANOMALY_MAX,
    EULER_ANGLE_MIN,
    EULER_ANGLE_MAX,
    ANGULAR_VELOCITY_MIN,
    ANGULAR_VELOCITY_MAX,
    SimulationConfiguration,
)
from core.physics.solver.simulation_engine import SimulationEngine

from core.physics.dataclasses.orbital_data import OrbitalElements
from core.physics.dataclasses.satellite_configuration import SatelliteConfiguration, deserialize_satellite_configuration
from ui.simulation.components.simualtion_plots import SimulationPlotsPanel
from ui.simulation.components.simulation_control_panel import SimulationControlPanel
from utils.constants import CONSTANTS
from utils.rotations import rotate_pqw_to_eci
from utils.ui.ui_utils import show_dark_message_box
from utils.transformations import (
    euler_to_quaternion,
    quaternion_to_euler
)

class SimulationControls(QWidget):

    satellite_state_changed = pyqtSignal(list, list, list)

    def __init__(self, orbital_data: OrbitalElements, satellite_data: SatelliteConfiguration, dt :float = 0.1, parent=None):
        super().__init__(parent)

        self.orbital_data : OrbitalElements = orbital_data
        self.satellite_data : SatelliteConfiguration = deserialize_satellite_configuration(satellite_data) if satellite_data is not None else None
        self.current_configuration = None
        self.silent_update = False
        self.step_val = dt
        
        self.us_locale = QLocale(QLocale.Language.English, QLocale.Country.UnitedStates)
        self.setup_view()
        
        self._update_calculated_state()
        self.emit_current_satellite_state()

    def update_data(self, orbital_data: OrbitalElements, satellite_data: SatelliteConfiguration):
        self.reset()
        self.clear_errors()
        self.orbital_data = orbital_data
        self.satellite_data = satellite_data
        
        with QSignalBlocker(self.input_true_anomaly):
            self.input_true_anomaly.setText(str(orbital_data.true_anomaly))
            
        self._update_calculated_state()
        self._sync_error_state(mark_errors=False)
        self.emit_current_satellite_state()

    def setup_view(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(10)

        self.tab_widget = QTabWidget(self)
        self.tab_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tab_widget.setObjectName("simulationTabWidget")
        main_layout.addWidget(self.tab_widget)

        # Index 0: Initial Conditions
        self._initial_conditions_tab = QWidget(self)
        self._initial_conditions_tab.setObjectName("initial_conditions") 

        # Index 1: Control Panel
        self.control_panel = SimulationControlPanel(self)

        self.control_panel.state_updated.connect(self._on_simulation_step)

        # Index 2: Simulation Plots
        self._plots_tab = SimulationPlotsPanel()
        self._plots_tab.setObjectName("plots")

        self._build_initial_conditions_tab()

        self.tab_widget.addTab(self._initial_conditions_tab, "Initial Conditions")
        self.tab_widget.addTab(self.control_panel, "Control Panel")
        self.tab_widget.addTab(self._plots_tab, "Simulation Plots")

    def _build_initial_conditions_tab(self) -> None:
        initial_conditions_layout = QVBoxLayout(self._initial_conditions_tab)
        
        form_layout = QFormLayout()
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

        # --- 1. ORBITAL ENVIRONMENT ---
        val_nu = QDoubleValidator(-360.0, 360.0, 3, self)
        val_nu.setLocale(self.us_locale)
        val_nu.setNotation(QDoubleValidator.Notation.StandardNotation)

        init_nu_deg = getattr(self.orbital_data, "true_anomaly", 0.0)
        self.input_true_anomaly = self._create_line_edit(val_nu)
        self.input_true_anomaly.setText(f"{init_nu_deg:.3f}")
        self.input_true_anomaly.textChanged.connect(self._on_field_finished)

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
        val_euler = QDoubleValidator(-360.0, 360.0, 3, self)
        val_euler.setLocale(self.us_locale)

        val_omega = QDoubleValidator(-1000.0, 1000.0, 4, self)
        val_omega.setLocale(self.us_locale)

        self.input_euler_angles = [self._create_line_edit(val_euler) for _ in range(3)]
        for edit in self.input_euler_angles:
            edit.setText("")
            edit.textChanged.connect(self._on_field_finished)

        self.input_angular_velocity = [self._create_line_edit(val_omega) for _ in range(3)]
        for edit in self.input_angular_velocity:
            edit.setText("")
            edit.textChanged.connect(self._on_field_finished)

        euler_container = self._create_horizontal_inputs(self.input_euler_angles, placeholders=["Roll (ϕ)", "Pitch (θ)", "Yaw (ψ)"])
        omega_container = self._create_horizontal_inputs(self.input_angular_velocity, placeholders=["ωx", "ωy", "ωz"])

        form_layout.addRow("Initial Euler Angles [deg]:", euler_container)
        form_layout.addRow("Initial Angular Velocity [deg/s]:", omega_container)
        form_layout.addRow(self._create_separator())

        self.combo_step_size = QComboBox()
        self.step_options = {
            "0.001 s (1 ms)": 0.001,
            "0.005 s (5 ms)": 0.005,
            "0.010 s (10 ms)": 0.010,
            "0.050 s (50 ms)": 0.050,
            "0.100 s (100 ms)": 0.100,
            "0.500 s (500 ms)": 0.500,
            "1.000 s (1 s)": 1.000,
        }
        self.combo_step_size.addItems(list(self.step_options.keys()))
        initial_text = self._get_step_text_from_value(self.step_val)
        self.combo_step_size.setCurrentText(initial_text)
        self.combo_step_size.currentTextChanged.connect(self._on_step_changed)


        form_layout.addRow("Integration Step (Δt):", self.combo_step_size)

        note_label = QLabel("Note:")
        note_label.setStyleSheet("color: #ffffff; font-size: 15px; margin-top: 5px; font-weight: bold")

        info_label_bot = QLabel(
            "Once the simulation starts, initial conditions cannot be modified. "
            "You can return to edit these settings later, but doing so will discard "
            "the current simulation run."
        )
        info_label_bot.setWordWrap(True)
        info_label_bot.setStyleSheet("color: #b0bec5; font-size: 12px; margin-bottom: 4px;")

        form_layout.addRow(note_label)
        form_layout.addRow(info_label_bot)

        self.btn_start_simulation = QPushButton("Start Simulation")
        self.btn_start_simulation.clicked.connect(self._start_simulation)
        form_layout.addRow(self.btn_start_simulation)

        button_row = QHBoxLayout()
        button_row.setSpacing(6)
        self.btn_save = QPushButton("Save")
        self.btn_reset = QPushButton("Reset")
        self.btn_save.clicked.connect(self.save_to_file)
        self.btn_reset.clicked.connect(self.reset)
        button_row.addWidget(self.btn_save)
        button_row.addWidget(self.btn_reset)

        initial_conditions_layout.addLayout(form_layout)
        initial_conditions_layout.addLayout(button_row)

    def _on_step_changed(self, text: str) -> None:
        self.step_val = self.step_options.get(text, 0.010)

    def _on_simulation_step(self, satellite_state : SatelliteState):
        state = satellite_state.to_vector()
        pos_km = state[0:3] / 1000
        v_kms = state[3:6] / 1000
        quat_orientation = state[6:10]
        angular_vel =  state[10:13]

        self.satellite_state_changed.emit([], pos_km, quaternion_to_euler(quat_orientation))

        # Akutalizacja wykresów
        # if self.control_panel.engine is not None:
        #     history_data = self.control_panel.engine.history
        #     self._plots_tab.update_telemetry(history_data)

    def _start_simulation(self) -> None:
        config = self.save_configuration()
        if config is None:
            return

        self.tab_widget.setTabEnabled(1, True)
        self.tab_widget.setTabEnabled(2, True)
        self.tab_widget.setCurrentIndex(1)
        self.tab_widget.setTabEnabled(0, False)

        QCoreApplication.processEvents()

        # 1. Konwersja dict -> SatelliteConfiguration (jeśli dane pochodzą z pliku JSON)
        sate_config = getattr(config, "satellite_configuration", None)
        if isinstance(sate_config, dict):
            sate_config = deserialize_satellite_configuration(sate_config)

        print(sate_config.mechanical.I)
        # 2. Bezpieczne pobranie macierzy bezwładności
        if sate_config and hasattr(sate_config, "mechanical"):
            I_matrix = np.asarray(sate_config.mechanical.I, dtype=np.float64)
        else:
            I_matrix = np.eye(3, dtype=np.float64)

        # 3. Przeliczenie jednostek na SI dla solvera RK4
        pos_m = config.initial_position * 1000.0
        vel_ms = config.initial_velocities * 1000.0
        omega_rads = np.radians(config.initial_angular_velocities)

        # 4. Pobranie kroku czasowego z konfiguracji lub stanu klasy
        dt_val = getattr(config, "dt", self.step_val)

        self.control_panel.engine = SimulationEngine(
            initial_state=SatelliteState(
                p=pos_m,
                v=vel_ms,
                q=config.initial_quat_orientation,
                omega=omega_rads,
            ),
            I_matrix=I_matrix,
            dt=dt_val,
        )

        # --- Print informacji o uruchomionym eksperymencie ---
        print("\n" + "=" * 65)
        print("               SIMULATION EXPERIMENT INITIALIZED               ")
        print("=" * 65)
        print(f" [Time Settings] Integration Step (dt) : {self.step_val:.4f} s")
        print("-" * 65)
        print(" [User Inputs]")
        print(f"  • Position (r)          : {config.initial_position} [km]")
        print(f"  • Velocity (v)          : {config.initial_velocities} [km/s]")
        print(f"  • Angular Velocity (ω)  : {config.initial_angular_velocities} [deg/s]")
        print(f"  • Quaternion (q)        : {config.initial_quat_orientation}")
        print("-" * 65)
        print(" [Internal Physics State (SI Units)]")
        print(f"  • Position (r_SI)       : {pos_m} [m]")
        print(f"  • Velocity (v_SI)       : {vel_ms} [m/s]")
        print(f"  • Angular Velocity (ω)  : {omega_rads} [rad/s]")
        print("-" * 65)
        print(" [Inertia Tensor Matrix (I)]")
        for row in I_matrix:
            print(f"   | {row[0]:12.6f} {row[1]:12.6f} {row[2]:12.6f} |")
        print("=" * 65 + "\n")

        self.emit_current_satellite_state()

    def _get_step_text_from_value(self, dt: float) -> str:
        """Zwraca etykietę QComboBox odpowiadającą wartości numerycznej dt."""
        for text, val in self.step_options.items():
            if math.isclose(val, dt, abs_tol=1e-6):
                return text
        return "0.010 s (10 ms)"

    def get_satellite_state(
        self, config: SimulationConfiguration | None = None
    ) -> Tuple[List[float], List[float], List[float]]:
        # 1. Pobranie i deserializacja konfiguracji satelity (z config lub fallback do self.satellite_data)
        sate_config = getattr(config, "satellite_configuration", None)
        if sate_config is None and hasattr(self, "satellite_data"):
            sate_config = self.satellite_data

        sat_obj = deserialize_satellite_configuration(sate_config)
        mech = getattr(sat_obj, "mechanical", None)

        if mech is not None:
            dimensions_m = [float(mech.a), float(mech.b), float(mech.h)]
        else:
            dimensions_m = [1.0, 1.0, 1.0]

        # 2. Pozycja początkowa [km] (z config lub z pól interfejsu)
        if config is not None and getattr(config, "initial_position", None) is not None:
            pos_km = [float(x) for x in config.initial_position]
        else:
            pos_km = [
                self._parse_field_number(self.calculated_position[0]) or 0.0,
                self._parse_field_number(self.calculated_position[1]) or 0.0,
                self._parse_field_number(self.calculated_position[2]) or 0.0,
            ]

        # 3. Kąty Eulera [deg] (przeliczone z kwaternionu w config lub z pól GUI)
        if config is not None and getattr(config, "initial_quat_orientation", None) is not None:
            quat = np.asarray(config.initial_quat_orientation, dtype=float)
            if quat.size >= 4:
                roll, pitch, yaw = quaternion_to_euler(quat[:4], degrees=True)
                euler_deg = [float(roll), float(pitch), float(yaw)]
            else:
                euler_deg = [0.0, 0.0, 0.0]
        else:
            euler_deg = [
                self._parse_field_number(self.input_euler_angles[0]) or 0.0,
                self._parse_field_number(self.input_euler_angles[1]) or 0.0,
                self._parse_field_number(self.input_euler_angles[2]) or 0.0,
            ]

        return dimensions_m, pos_km, euler_deg

    def emit_current_satellite_state(self) -> None:
        """Emituje aktualny stan satelity do widoku 3D."""
        base_config = self.save_configuration()
        dimensions_m, pos_km, euler_deg = self.get_satellite_state(base_config)
        self.satellite_state_changed.emit(dimensions_m, pos_km, euler_deg)

    def _create_separator(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #333333; margin-top: 6px; margin-bottom: 6px;")
        return line

    def _get_valid_true_anomaly_degrees(self) -> float | None:
        text = self.input_true_anomaly.text().strip()
        if not text:
            return None
        try:
            value = float(text.replace(',', '.'))
        except ValueError:
            return None

        if not (TRUE_ANOMALY_MIN <= value <= TRUE_ANOMALY_MAX):
            return None

        return value

    def _update_calculated_state(self) -> None:
        nu_deg = self._get_valid_true_anomaly_degrees()
        if nu_deg is None:
            for field in self.calculated_position + self.calculated_velocities:
                field.setText("")
            return

        nu_rad = math.radians(nu_deg)
        r_eci_km, v_eci_kms = self._kepler_to_eci(self.orbital_data, nu_rad)

        for idx, val in enumerate(r_eci_km):
            self.calculated_position[idx].setText(f"{val:,.3f}")

        for idx, val in enumerate(v_eci_kms):
            self.calculated_velocities[idx].setText(f"{val:,.3f}")

    @staticmethod
    def _kepler_to_eci(orbit: OrbitalElements, nu_rad: float) -> Tuple[np.ndarray, np.ndarray]:
        a_m = getattr(orbit, "semi_major_axis", 7000000.0) * 1e3
        e = getattr(orbit, "eccentricity", 0.0)
        inc_rad = np.deg2rad(getattr(orbit, "inclination", 0.0))
        raan_rad = np.deg2rad(getattr(orbit, "raan", 0.0))
        arg_p_rad = np.deg2rad(getattr(orbit, "arg_perigee", 0.0))

        mu = CONSTANTS["mu"]

        p = a_m * (1.0 - e**2)
        r = p / (1.0 + e * math.cos(nu_rad)) if (1.0 + e * math.cos(nu_rad)) != 0 else 1.0

        r_pqw = np.array([r * math.cos(nu_rad), r * math.sin(nu_rad), 0.0])

        h = math.sqrt(mu * p) if p > 0 else 1.0
        v_pqw = np.array([
            -(mu / h) * math.sin(nu_rad),
            (mu / h) * (e + math.cos(nu_rad)),
            0.0
        ])

        r_eci_m = rotate_pqw_to_eci(r_pqw, raan_rad, inc_rad, arg_p_rad)
        v_eci_ms = rotate_pqw_to_eci(v_pqw, raan_rad, inc_rad, arg_p_rad)

        return r_eci_m / 1000.0, v_eci_ms / 1000.0

    def _create_line_edit(self, validator: QDoubleValidator, read_only: bool = False, parent=None) -> QLineEdit:
        line_edit = QLineEdit(self if parent is None else parent)
        line_edit.setValidator(validator)
        line_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        if read_only:
            line_edit.setReadOnly(True)
            line_edit.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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

    def _on_field_finished(self) -> None:
        if self.silent_update:
            return

        sender = self.sender()
        if sender is None or not isinstance(sender, QWidget):
            return

        current_keys = self._get_error_keys_for_widget(sender)
        if not current_keys:
            return

        all_errors = self.validate_inputs() or {}
        current_errors = {
            key: msg for key, msg in all_errors.items() if key in current_keys
        }

        if current_errors:
            self.mark_errors(current_errors, replace_all=False)
        else:
            self._reset_widget_style(sender)

        self.btn_start_simulation.setEnabled(len(all_errors) == 0)
        self.btn_save.setEnabled(len(all_errors) == 0)
        self._update_calculated_state()

        self.emit_current_satellite_state()
        

    def _get_error_keys_for_widget(self, widget: QWidget) -> List[str]:
        if widget == self.input_true_anomaly:
            return ["true_anomaly"]

        if hasattr(self, "input_euler_angles") and widget in self.input_euler_angles:
            index = list(self.input_euler_angles).index(widget)
            keys = ["euler_roll", "euler_pitch", "euler_yaw"]
            return [keys[index]] if index < len(keys) else []

        if hasattr(self, "input_angular_velocity") and widget in self.input_angular_velocity:
            index = list(self.input_angular_velocity).index(widget)
            keys = ["omega_x", "omega_y", "omega_z"]
            return [keys[index]] if index < len(keys) else []

        return []

    def validate_inputs(self) -> dict[str, str]:
        errors: dict[str, str] = {}

        true_anomaly = self.input_true_anomaly.text().strip()
        if not true_anomaly:
            errors["true_anomaly"] = "True anomaly is required."
        else:
            try:
                value = float(true_anomaly.replace(',', '.'))
            except ValueError:
                errors["true_anomaly"] = "True anomaly must be a valid number."
            else:
                if not (TRUE_ANOMALY_MIN <= value <= TRUE_ANOMALY_MAX):
                    errors["true_anomaly"] = (
                        f"True anomaly must be between {TRUE_ANOMALY_MIN} and {TRUE_ANOMALY_MAX} degrees."
                    )

        labels = ["roll", "pitch", "yaw"]
        for index, field in enumerate(self.input_euler_angles):
            text = field.text().strip()
            if not text:
                errors[f"euler_{labels[index]}"] = f"{labels[index].capitalize()} Euler angle is required."
                continue
            try:
                value = float(text.replace(',', '.'))
            except ValueError:
                errors[f"euler_{labels[index]}"] = f"{labels[index].capitalize()} Euler angle must be a valid number."
            else:
                if not (EULER_ANGLE_MIN <= value <= EULER_ANGLE_MAX):
                    errors[f"euler_{labels[index]}"] = (
                        f"{labels[index].capitalize()} Euler angle must be between "
                        f"{EULER_ANGLE_MIN} and {EULER_ANGLE_MAX} degrees."
                    )

        labels = ["x", "y", "z"]
        for index, field in enumerate(self.input_angular_velocity):
            text = field.text().strip()
            if not text:
                errors[f"omega_{labels[index]}"] = f"Angular velocity {labels[index].upper()} is required."
                continue
            try:
                value = float(text.replace(',', '.'))
            except ValueError:
                errors[f"omega_{labels[index]}"] = f"Angular velocity {labels[index].upper()} must be a valid number."
            else:
                if not (ANGULAR_VELOCITY_MIN <= value <= ANGULAR_VELOCITY_MAX):
                    errors[f"omega_{labels[index]}"] = (
                        f"Angular velocity {labels[index].upper()} must be between "
                        f"{ANGULAR_VELOCITY_MIN} and {ANGULAR_VELOCITY_MAX} deg/s."
                    )

        return errors

    def _get_field_map(self) -> dict[str, QLineEdit | list[QLineEdit]]:
        return {
            "true_anomaly": self.input_true_anomaly,
            "euler_roll": self.input_euler_angles[0],
            "euler_pitch": self.input_euler_angles[1],
            "euler_yaw": self.input_euler_angles[2],
            "omega_x": self.input_angular_velocity[0],
            "omega_y": self.input_angular_velocity[1],
            "omega_z": self.input_angular_velocity[2],
        }

    def clear_errors(self) -> None:
        for widget in self._get_field_map().values():
            if isinstance(widget, list):
                for w in widget:
                    self._reset_widget_style(w)
            else:
                self._reset_widget_style(widget)

    def _reset_widget_style(self, widget: QLineEdit | None) -> None:
        if widget is None:
            return
        widget.setProperty("hasError", False)
        widget.setToolTip("")
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def mark_errors(self, errors: dict[str, str], replace_all: bool = True, mark_errors=True) -> None:
        if not mark_errors:
            return

        if replace_all:
            self.clear_errors()

        field_map = self._get_field_map()
        for error_key, error_msg in errors.items():
            target = field_map.get(error_key)
            if target is None:
                continue
            if not isinstance(target, list):
                target = [target]
            for widget in target:
                if widget is None:
                    continue
                widget.setProperty("hasError", True)
                widget.setToolTip(error_msg)
                widget.style().unpolish(widget)
                widget.style().polish(widget)

    def _sync_error_state(self, mark_errors=True, replace_all=True) -> None:
        if self.silent_update:
            return
        errors = self.validate_inputs()
        if errors:
            self.mark_errors(errors, replace_all=replace_all, mark_errors=mark_errors)
            self.btn_start_simulation.setEnabled(False)
            self.btn_save.setEnabled(False)
        else:
            self.clear_errors()
            self.btn_start_simulation.setEnabled(True)
            self.btn_save.setEnabled(True)

    def _jsonify_for_storage(self, value: Any) -> Any:
        if is_dataclass(value):
            return self._jsonify_for_storage(asdict(value))
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, dict):
            return {key: self._jsonify_for_storage(val) for key, val in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._jsonify_for_storage(item) for item in value]
        return value

    def _parse_field_number(self, field: QLineEdit) -> float | None:
        text = field.text().strip()
        if not text:
            return None

        normalized = text.replace(' ', '').replace(',', '.')
        if normalized.count('.') > 1:
            normalized = normalized.replace('.', '', normalized.count('.') - 1)

        try:
            return float(normalized)
        except ValueError:
            return None

    def save_configuration(self) -> SimulationConfiguration | None:
        true_anomaly_deg = self._get_valid_true_anomaly_degrees()
        if true_anomaly_deg is None:
            self._sync_error_state()
            return None

        numeric_position = []
        for field in self.calculated_position:
            value = self._parse_field_number(field)
            if value is None:
                return None
            numeric_position.append(value)

        numeric_velocity = []
        for field in self.calculated_velocities:
            value = self._parse_field_number(field)
            if value is None:
                return None
            numeric_velocity.append(value)

        numeric_euler_angles = []
        for field in self.input_euler_angles:
            value = self._parse_field_number(field)
            if value is None:
                return None
            numeric_euler_angles.append(value)

        numeric_angular_velocity = []
        for field in self.input_angular_velocity:
            value = self._parse_field_number(field)
            if value is None:
                return None
            numeric_angular_velocity.append(value)


        self.current_configuration = SimulationConfiguration(
            orbital_data=self.orbital_data,
            satellite_configuration=self.satellite_data,
            initial_position=np.array(numeric_position, dtype=float),
            initial_velocities=np.array(numeric_velocity, dtype=float),
            initial_quat_orientation=euler_to_quaternion(roll=numeric_euler_angles[0],
                                                         pitch=numeric_euler_angles[1],
                                                         yaw=numeric_euler_angles[2],
                                                         degrees=True),
            initial_angular_velocities=np.array(numeric_angular_velocity, dtype=float),
            dt=self.step_val
        )
        return self.current_configuration

    def save_to_file(self) -> None:
        errors = self.validate_inputs()
        if errors:
            self.mark_errors(errors, replace_all=True)
            show_dark_message_box(
                self,
                "Invalid simulation configuration",
                "Please correct the highlighted fields before saving.",
                icon=QMessageBox.Icon.Warning
            )
            return

        data = self.save_configuration()
        if data is None:
            show_dark_message_box(
                self,
                "Invalid simulation configuration",
                "The true anomaly must be valid before saving.",
                icon=QMessageBox.Icon.Warning
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save simulation configuration",
            str(Path.home() / "simulation_configuration.json"),
            "JSON files (*.json)",
        )
        if not file_path:
            return

        payload = self._jsonify_for_storage(data)

        with open(file_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        show_dark_message_box(
            self,
            "Saved",
            f"Simulation configuration saved to {file_path}",
            icon=QMessageBox.Icon.Information
        )

    def load_from_file(self, payload: dict) -> None:
        self.reset()

        orbital_data = payload.get("orbital_data", {})
        if not isinstance(orbital_data, dict) or not orbital_data:
            show_dark_message_box(
                self,
                "Load failed",
                "The JSON does not contain a valid orbital_data section.",
                icon=QMessageBox.Icon.Warning,
            )
            raise ValueError("Invalid orbital_data section")

        try:
            raw_true_anomaly = float(orbital_data.get("true_anomaly", 0.0))
            if abs(raw_true_anomaly) <= 2.0 * math.pi + 1e-6:
                true_anomaly_deg = math.degrees(raw_true_anomaly)
                true_anomaly_rad = raw_true_anomaly
            else:
                true_anomaly_deg = raw_true_anomaly
                true_anomaly_rad = math.radians(raw_true_anomaly)

            loaded_orbit = OrbitalElements(
                semi_major_axis=float(
                    orbital_data.get("semi_major_axis", 7000000.0)
                ),
                eccentricity=float(orbital_data.get("eccentricity", 0.0)),
                raan=float(orbital_data.get("raan", 0.0)),
                inclination=float(orbital_data.get("inclination", 0.0)),
                arg_perigee=float(orbital_data.get("arg_perigee", 0.0)),
                true_anomaly=true_anomaly_rad,
            )
        except (TypeError, ValueError):
            show_dark_message_box(
                self,
                "Load failed",
                "The orbital_data section contains invalid numeric values.",
                icon=QMessageBox.Icon.Warning,
            )
            return

        self.orbital_data = loaded_orbit

        initial_position = np.asarray(
            payload.get("initial_position", [0.0, 0.0, 0.0]), dtype=float
        )
        initial_velocities = np.asarray(
            payload.get("initial_velocities", [0.0, 0.0, 0.0]), dtype=float
        )
        initial_angular_velocities = np.asarray(
            payload.get("initial_angular_velocities", [0.0, 0.0, 0.0]), dtype=float
        )
        quat = np.asarray(
            payload.get("initial_quat_orientation", [1.0, 0.0, 0.0, 0.0]),
            dtype=float,
        )

        if quat.size >= 4:
            roll, pitch, yaw = quaternion_to_euler(quat[:4], degrees=True)
            euler_values = [roll, pitch, yaw]
        else:
            euler_values = [0.0, 0.0, 0.0]

        # Poprawka 1: Użycie .get() na dict zamiast getattr()
        self.step_val = float(payload.get("dt", 0.010))
        raw_sat_config = payload.get("satellite_configuration", {})
        self.satellite_data = raw_sat_config

        # Poprawka 2: Aktualizacja wyboru w QComboBox
        if hasattr(self, "combo_step_size"):
            step_text = self._get_step_text_from_value(self.step_val)
            self.combo_step_size.setCurrentText(step_text)

        input_widgets = (
            [self.input_true_anomaly]
            + list(self.input_euler_angles)
            + list(self.input_angular_velocity)
        )
        blockers = [QSignalBlocker(widget) for widget in input_widgets]

        self.input_true_anomaly.setText(f"{true_anomaly_deg:.3f}")
        for index, value in enumerate(euler_values[:3]):
            self.input_euler_angles[index].setText(f"{float(value):.3f}")
        for index, value in enumerate(initial_angular_velocities[:3]):
            self.input_angular_velocity[index].setText(f"{float(value):.3f}")

        for index, value in enumerate(initial_position[:3]):
            self.calculated_position[index].setText(f"{float(value):,.3f}")
        for index, value in enumerate(initial_velocities[:3]):
            self.calculated_velocities[index].setText(f"{float(value):,.3f}")

        del blockers

        self._sync_error_state(mark_errors=False)
        self._update_calculated_state()
        self.emit_current_satellite_state()

    def reset(self) -> None:
        """Reset all input fields and simulation tabs to default state without triggering validation errors."""
        self.tab_widget.setTabEnabled(2, False)
        self.tab_widget.setTabEnabled(1, False)
        self.tab_widget.setTabEnabled(0, True)
        self.tab_widget.setCurrentIndex(0)

        all_fields = [
            self.input_true_anomaly,
            *self.input_euler_angles,
            *self.input_angular_velocity
        ]

        # 1. Zablokuj sygnały na czas resetowania, aby setText("") nie uruchamiał _on_field_finished
        blockers = [QSignalBlocker(f) for f in all_fields]

        init_nu_deg = getattr(self.orbital_data, "true_anomaly", 0.0)
        self.input_true_anomaly.setText(f"{init_nu_deg:.3f}")

        for field in self.input_euler_angles + self.input_angular_velocity:
            field.setText("")

        # 2. Usuń blokady sygnałów
        del blockers

        # 3. Wyczyść błędy stylów oraz zaktualizuj stan przycisku i wyliczeń
        self.clear_errors()
        self._update_calculated_state()
        self.btn_start_simulation.setEnabled(False)
        self.btn_save.setEnabled(False)
        self._plots_tab.reset()
        if self.control_panel.engine is not None:
            self.control_panel.engine.reset()