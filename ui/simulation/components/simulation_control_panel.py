from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)


class SimulationControlPanel(QWidget):
    """Zakładka sterowania biegiem symulacji, skali czasu oraz przełączników wizualizacji 3D."""

    play_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    reset_requested = pyqtSignal()
    speed_changed = pyqtSignal(int)
    step_size_changed = pyqtSignal(float)  
    overlay_toggled = pyqtSignal(str, bool)

    overlay_toggled = pyqtSignal(str, bool)  # (nazwa_elementu, stan_checkboxa)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_running = False
        self.setup_ui()

    def setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(12)

        info_label = QLabel(
            "This panel provides real-time control over the simulation state. "
            "You can start, pause, or reset orbit propagation, adjust time compression, "
            "inspect live telemetry readouts, and toggle 3D vector overlays."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #b0bec5; font-size: 12px; margin-bottom: 2px;")
        main_layout.addWidget(info_label)

        # 1. SEKCJIA EXECUTION & TIME CONTROL
        main_layout.addWidget(self._create_execution_group())

        # 2. SEKCJA VISUAL OVERLAYS (DRAFT)
        main_layout.addWidget(self._create_overlays_group())

        # 3. SEKCJA LIVE TELEMETRY (PODGLĄD)
        main_layout.addWidget(self._create_telemetry_group())

        main_layout.addStretch()

    def _create_execution_group(self) -> QGroupBox:
        group = QGroupBox("Execution & Time Control")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        # Przyciski Play / Pause / Reset
        btn_layout = QHBoxLayout()
        self.btn_play_pause = QPushButton("Play")
        self.btn_play_pause.setStyleSheet("font-weight: bold; padding: 6px;")
        self.btn_play_pause.clicked.connect(self._on_play_pause_clicked)

        self.btn_reset = QPushButton("Reset Run")
        self.btn_reset.setStyleSheet("padding: 6px;")
        self.btn_reset.clicked.connect(self.reset_requested.emit)

        btn_layout.addWidget(self.btn_play_pause, stretch=2)
        btn_layout.addWidget(self.btn_reset, stretch=1)
        layout.addLayout(btn_layout)

        # Suwak prędkości symulacji (Time Compression)
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

        # Czas oraz Wybór Kroku Czasowego
        time_form = QFormLayout()
        time_form.setHorizontalSpacing(10)

        self.lbl_sim_time = QLabel("0.00 s")
        self.lbl_sim_time.setStyleSheet("color: #ffffff; font-family: monospace;")

        # ComboBox wyboru kroku integracji
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
        self.combo_step_size.setCurrentText("0.010 s (10 ms)")  # Domyślny wybór
        self.combo_step_size.currentTextChanged.connect(self._on_step_size_changed)

        time_form.addRow("Simulation Time (t):", self.lbl_sim_time)
        time_form.addRow("Integration Step (Δt):", self.combo_step_size)

        layout.addLayout(time_form)
        return group

    def _on_step_size_changed(self, text: str) -> None:
        step_val = self.step_options.get(text, 0.010)
        self.step_size_changed.emit(step_val)

    def _create_overlays_group(self) -> QGroupBox:
        group = QGroupBox("3D Overlays & Vectors")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # Draft Checkboxes
        self.chk_body_axes = QCheckBox("Show Satellite Body Axes (X, Y, Z)")
        self.chk_mag_vector = QCheckBox("Show Magnetic Dipole Vector (μ)")
        self.chk_rw_torque = QCheckBox("Show Reaction Wheels Net Torque (τ)")
        self.chk_orbit_trace = QCheckBox("Show Orbit Trajectory Trace")

        # Łączenie z obsługą zdarzeń
        self.chk_body_axes.toggled.connect(lambda chk: self.overlay_toggled.emit("body_axes", chk))
        self.chk_mag_vector.toggled.connect(lambda chk: self.overlay_toggled.emit("magnetic_vector", chk))
        self.chk_rw_torque.toggled.connect(lambda chk: self.overlay_toggled.emit("rw_torque", chk))
        self.chk_orbit_trace.toggled.connect(lambda chk: self.overlay_toggled.emit("orbit_trace", chk))

        layout.addWidget(self.chk_body_axes)
        layout.addWidget(self.chk_mag_vector)
        layout.addWidget(self.chk_rw_torque)
        layout.addWidget(self.chk_orbit_trace)

        return group

    def _create_telemetry_group(self) -> QGroupBox:
        group = QGroupBox("Real-Time Telemetry")
        layout = QFormLayout(group)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(6)

        self.lbl_telemetry_altitude = QLabel("--- km")
        self.lbl_telemetry_omega = QLabel("--- deg/s")
        self.lbl_telemetry_nu = QLabel("--- deg")

        for lbl in (self.lbl_telemetry_altitude, self.lbl_telemetry_omega, self.lbl_telemetry_nu):
            lbl.setStyleSheet("color: #e0e0e0; font-family: monospace;")

        layout.addRow("Altitude:", self.lbl_telemetry_altitude)
        layout.addRow("Ang. Velocity |ω|:", self.lbl_telemetry_omega)
        layout.addRow("True Anomaly (ν):", self.lbl_telemetry_nu)

        return group

    # --- HANDLERY I METODY POMOCNICZE ---

    def _on_play_pause_clicked(self) -> None:
        self.is_running = not self.is_running
        if self.is_running:
            self.btn_play_pause.setText("Pause")
            self.play_requested.emit()
        else:
            self.btn_play_pause.setText("Play")
            self.pause_requested.emit()

    def _on_speed_changed(self, value: int) -> None:
        self.lbl_speed_val.setText(f"{value}x")
        self.speed_changed.emit(value)

    def update_telemetry(self, altitude_km: float, omega_norm_deg: float, nu_deg: float, sim_time: float) -> None:
        """Metoda do bieżącej aktualizacji cyfrowych wskaźników z poziomu pętli symulacji."""
        self.lbl_telemetry_altitude.setText(f"{altitude_km:,.2f} km")
        self.lbl_telemetry_omega.setText(f"{omega_norm_deg:.3f} deg/s")
        self.lbl_telemetry_nu.setText(f"{nu_deg:.2f} deg")
        self.lbl_sim_time.setText(f"{sim_time:.2f} s")