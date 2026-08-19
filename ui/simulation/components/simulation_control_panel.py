import numpy as np
from PyQt6.QtCore import QLocale, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QDoubleValidator
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from core.physics.solver.simulation_engine import SimulationEngine


class SimulationControlPanel(QWidget):
    """Zakładka sterowania biegiem symulacji, skali czasu, ADCS oraz wizualizacji 3D."""

    reset_requested = pyqtSignal()
    speed_changed = pyqtSignal(int)
    overlay_toggled = pyqtSignal(str, bool)
    state_updated = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_running = False
        self.is_detumbling = False
        self.detumble_completed = False

        self.timer = QTimer(self)
        self.timer.setInterval(20)
        self.timer.timeout.connect(self._on_sim_tick)
        self.us_locale = QLocale(QLocale.Language.English, QLocale.Country.UnitedStates)

        self.engine: SimulationEngine = None
        self.speed_multiplier = 1
        self.setup_ui()

    def setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(12)

        info_label = QLabel(
            "This panel provides real-time control over simulation execution, "
            "ADCS modes (Detumbling & Pointing), and 3D overlays."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(
            "color: #b0bec5; font-size: 12px; margin-bottom: 2px;"
        )
        main_layout.addWidget(info_label)

        main_layout.addWidget(self._create_execution_group())
        main_layout.addWidget(self._create_adcs_group())
        main_layout.addWidget(self._create_overlays_group())
        main_layout.addStretch()

    def _create_execution_group(self) -> QGroupBox:
        group = QGroupBox("Execution and Time Control")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        btn_layout = QHBoxLayout()
        self.btn_play_pause = QPushButton("Play")
        self.btn_play_pause.setStyleSheet("font-weight: bold; padding: 6px;")
        self.btn_play_pause.clicked.connect(self._on_play_pause_clicked)

        self.btn_reset = QPushButton("Reset Run")
        self.btn_reset.setStyleSheet("padding: 6px;")
        self.btn_reset.clicked.connect(self._on_reset_clicked)

        btn_layout.addWidget(self.btn_play_pause, stretch=2)
        btn_layout.addWidget(self.btn_reset, stretch=1)
        layout.addLayout(btn_layout)

        speed_layout = QVBoxLayout()
        speed_header_layout = QHBoxLayout()
        speed_label = QLabel("Simulation Speed:")
        self.lbl_speed_val = QLabel("1x")
        self.lbl_speed_val.setStyleSheet("color: #4fc3f7; font-weight: bold;")

        speed_header_layout.addWidget(speed_label)
        speed_header_layout.addStretch()
        speed_header_layout.addWidget(self.lbl_speed_val)

        self.slider_speed = QSlider(Qt.Orientation.Horizontal)
        self.slider_speed.setMinimum(1)
        self.slider_speed.setMaximum(100)
        self.slider_speed.setValue(1)
        self.slider_speed.setTickInterval(10)
        self.slider_speed.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider_speed.valueChanged.connect(self._on_speed_changed)

        speed_layout.addLayout(speed_header_layout)
        speed_layout.addWidget(self.slider_speed)
        layout.addLayout(speed_layout)

        time_form = QFormLayout()
        time_form.setHorizontalSpacing(10)

        self.lbl_sim_time = QLabel("0.00 s")
        self.lbl_sim_time.setStyleSheet(
            "color: #ffffff; font-family: monospace;"
        )

        time_form.addRow("Simulation Time (t):", self.lbl_sim_time)
        layout.addLayout(time_form)

        return group

    def _create_adcs_group(self) -> QGroupBox:
        group = QGroupBox("ADCS & Attitude Control")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        # 1. Sekcja Detumblingu
        detumble_layout = QHBoxLayout()
        self.combo_detumble_mode = QComboBox()
        self.combo_detumble_mode.addItems(
            ["Normal B-Dot", "Adaptive B-Dot (Normalized)"]
        )

        gain_validator = QDoubleValidator(0.0, 100000.0, 2, self)
        gain_validator.setLocale(self.us_locale)
        gain_validator.setNotation(QDoubleValidator.Notation.StandardNotation)

        self.txt_k_gain = QLineEdit("7200.0")
        self.txt_k_gain.setValidator(gain_validator)
        self.txt_k_gain.setPlaceholderText("Gain k")

        detumble_layout.addWidget(self.combo_detumble_mode, stretch=2)
        detumble_layout.addWidget(QLabel("k:"))
        detumble_layout.addWidget(self.txt_k_gain, stretch=1)

        self.btn_start_detumble = QPushButton("Start Detumbling")
        self.btn_start_detumble.setStyleSheet("font-weight: bold;")
        self.btn_start_detumble.clicked.connect(self._on_start_detumble_clicked)

        layout.addLayout(detumble_layout)
        layout.addWidget(self.btn_start_detumble)

        # 2. Kontrola Orientacji (Pola Roll, Pitch, Yaw)
        pointing_group_layout = QVBoxLayout()

        grid_rpy = QGridLayout()
        grid_rpy.setHorizontalSpacing(6)

        validator = QDoubleValidator(-180.0, 180.0, 2, self)
        validator.setLocale(self.us_locale)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)

        self.txt_roll = QLineEdit("0.0")
        self.txt_pitch = QLineEdit("0.0")
        self.txt_yaw = QLineEdit("0.0")

        fields = [
            ("Roll (°):", self.txt_roll),
            ("Pitch (°):", self.txt_pitch),
            ("Yaw (°):", self.txt_yaw),
        ]

        for col, (label_text, field) in enumerate(fields):
            field.setValidator(validator)
            field.setEnabled(False)  # Zablokowane do czasu zakończenia detumblingu
            field.textChanged.connect(self._validate_pointing_inputs)

            lbl = QLabel(label_text)
            grid_rpy.addWidget(lbl, 0, col * 2)
            grid_rpy.addWidget(field, 0, col * 2 + 1)

        self.btn_apply_pointing = QPushButton("Set Target Angles")
        self.btn_apply_pointing.setStyleSheet("font-weight: bold;")
        self.btn_apply_pointing.setEnabled(False)
        self.btn_apply_pointing.clicked.connect(self._on_apply_pointing_clicked)

        pointing_group_layout.addLayout(grid_rpy)
        pointing_group_layout.addWidget(self.btn_apply_pointing)
        layout.addLayout(pointing_group_layout)

        # 3. Status ADCS
        status_form = QFormLayout()
        self.txt_adcs_status = QLineEdit("IDLE / Tumbling")
        self.txt_adcs_status.setReadOnly(True)
        self.txt_adcs_status.setStyleSheet(
            "background-color: #1e272c; color: #81c784; font-weight: bold; padding: 4px;"
        )
        status_form.addRow("ADCS Status:", self.txt_adcs_status)
        layout.addLayout(status_form)

        return group

    def _create_overlays_group(self) -> QGroupBox:
        group = QGroupBox("3D Overlays & Vectors")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        self.chk_body_axes = QCheckBox("Show Satellite Body Axes (X, Y, Z)")
        self.chk_mag_vector = QCheckBox("Show Magnetic Dipole Vector (μ)")
        self.chk_rw_torque = QCheckBox("Show Reaction Wheels Net Torque (τ)")
        self.chk_orbit_trace = QCheckBox("Show Orbit Trajectory Trace")

        self.chk_body_axes.toggled.connect(
            lambda chk: self.overlay_toggled.emit("body_axes", chk)
        )
        self.chk_mag_vector.toggled.connect(
            lambda chk: self.overlay_toggled.emit("magnetic_vector", chk)
        )
        self.chk_rw_torque.toggled.connect(
            lambda chk: self.overlay_toggled.emit("rw_torque", chk)
        )
        self.chk_orbit_trace.toggled.connect(
            lambda chk: self.overlay_toggled.emit("orbit_trace", chk)
        )

        layout.addWidget(self.chk_body_axes)
        layout.addWidget(self.chk_mag_vector)
        layout.addWidget(self.chk_rw_torque)
        layout.addWidget(self.chk_orbit_trace)

        return group

    def _validate_pointing_inputs(self) -> bool:
        """Sprawdza poprawność wartości w polach Roll, Pitch, Yaw i steruje dostępnością przycisku."""
        is_valid = True
        for field in [self.txt_roll, self.txt_pitch, self.txt_yaw]:
            text = field.text().replace(",", ".")
            try:
                val = float(text)
                if not (-180.0 <= val <= 180.0):
                    is_valid = False
                    break
            except ValueError:
                is_valid = False
                break

        # Przycisk aktywujemy tylko, gdy detumbling się zakończył ORAZ wpisy są poprawne
        can_enable = self.detumble_completed and is_valid
        self.btn_apply_pointing.setEnabled(can_enable)
        return is_valid

    def _on_start_detumble_clicked(self) -> None:
        try:
            k_gain = float(self.txt_k_gain.text().replace(",", "."))
            if not (0.0 <= k_gain <= 100000.0):
                k_gain = 7200.0
        except ValueError:
            k_gain = 7200.0

        self.is_detumbling = True
        self.combo_detumble_mode.setEnabled(False)
        self.txt_k_gain.setEnabled(False)
        self.btn_start_detumble.setEnabled(False)

        # Blokada wejść orientacji na czas detumblingu
        for field in [self.txt_roll, self.txt_pitch, self.txt_yaw]:
            field.setEnabled(False)
        self.btn_apply_pointing.setEnabled(False)

        self.txt_adcs_status.setText("Satellite is in the detumbling mode")
        self.txt_adcs_status.setStyleSheet(
            "background-color: #1e272c; color: #ffb74d; font-weight: bold; padding: 4px;"
        )

        selected_mode = (
            "adaptive" if self.combo_detumble_mode.currentIndex() == 1 else "normal"
        )
        if self.engine:
            self.engine.set_adcs_mode(
                "DETUMBLE", detumble_algorithm=selected_mode, k_gain=k_gain
            )


    def _on_reset_clicked(self) -> None:
        self.is_running = False
        self.is_detumbling = False
        self.detumble_completed = False

        self.btn_play_pause.setText("Play")
        self.timer.stop()

        self.combo_detumble_mode.setEnabled(True)
        self.txt_k_gain.setEnabled(True)
        self.btn_start_detumble.setEnabled(True)

        for field in [self.txt_roll, self.txt_pitch, self.txt_yaw]:
            field.setText("0.0")
            field.setEnabled(False)
        self.btn_apply_pointing.setEnabled(False)

        self.txt_adcs_status.setText("IDLE / Tumbling")
        self.txt_adcs_status.setStyleSheet(
            "background-color: #1e272c; color: #81c784; font-weight: bold; padding: 4px;"
        )

        if self.engine:
            initial_state = self.engine.reset()
            self.lbl_sim_time.setText(f"{self.engine.sim_state.t:.2f} s")
            self.state_updated.emit(initial_state)
        self.speed_multiplier = 1
        self.reset_requested.emit()

    def _on_apply_pointing_clicked(self) -> None:
        if not self._validate_pointing_inputs():
            return

        roll = float(self.txt_roll.text().replace(",", "."))
        pitch = float(self.txt_pitch.text().replace(",", "."))
        yaw = float(self.txt_yaw.text().replace(",", "."))

        self.txt_adcs_status.setText(
            f"Pointing at Roll: {roll:.1f}°, Pitch: {pitch:.1f}°, Yaw: {yaw:.1f}°"
        )
        self.txt_adcs_status.setStyleSheet(
            "background-color: #1e272c; color: #4fc3f7; font-weight: bold; padding: 4px;"
        )

        if self.engine:
            self.engine.set_adcs_mode(
                "POINTING", target_angles=(roll, pitch, yaw)
            )

    def _check_detumble_condition(self, state) -> None:
        if not self.is_detumbling or self.detumble_completed:
            return

        omega_deg = np.degrees(np.abs(state.omega))
        threshold_deg = 0.4

        if np.all(omega_deg < threshold_deg):
            self.is_detumbling = False
            self.detumble_completed = True

            # Odblokowanie pól edycji orientacji i walidacja
            for field in [self.txt_roll, self.txt_pitch, self.txt_yaw]:
                field.setEnabled(True)
            self._validate_pointing_inputs()

            self.txt_adcs_status.setText(
                "Detumbling finished, entering payload mode"
            )
            self.txt_adcs_status.setStyleSheet(
                "background-color: #1e272c; color: #81c784; font-weight: bold; padding: 4px;"
            )

            if self.engine:
                self.engine.set_adcs_mode("IDLE")

    def _on_play_pause_clicked(self) -> None:
        self.is_running = not self.is_running
        if self.is_running:
            self.btn_play_pause.setText("Pause")
            self.timer.start()
        else:
            self.btn_play_pause.setText("Play")
            self.timer.stop()

    def _on_speed_changed(self, value: int) -> None:
        self.speed_multiplier = value
        self.lbl_speed_val.setText(f"{value}x")
        self.speed_changed.emit(value)

    def _on_sim_tick(self) -> None:
        if not self.engine:
            return

        current_satellite_state = None
        for _ in range(self.speed_multiplier):
            current_satellite_state = self.engine.step()

        if current_satellite_state:
            self.lbl_sim_time.setText(f"{self.engine.sim_state.t:.2f} s")

            if self.is_detumbling:
                self._check_detumble_condition(current_satellite_state)

            self.state_updated.emit(current_satellite_state)