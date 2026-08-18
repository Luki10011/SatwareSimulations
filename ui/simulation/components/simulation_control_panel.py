from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from core.physics.solver.simulation_engine import SimulationEngine


class SimulationControlPanel(QWidget):
    """Zakładka sterowania biegiem symulacji, skali czasu oraz przełączników wizualizacji 3D."""

    reset_requested = pyqtSignal()
    speed_changed = pyqtSignal(int)
    overlay_toggled = pyqtSignal(str, bool)  
    state_updated = pyqtSignal(object)  

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_running = False

        self.timer = QTimer(self)
        self.timer.setInterval(20)  
        self.timer.timeout.connect(self._on_sim_tick)

        self.engine: SimulationEngine = None
        self.speed_multiplier = 1  
        self.setup_ui()

    def setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(12)

        info_label = QLabel(
            "This panel provides real-time control over the simulation state. "
            "You can start, pause, or reset orbit propagation."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #b0bec5; font-size: 12px; margin-bottom: 2px;")
        main_layout.addWidget(info_label)

        main_layout.addWidget(self._create_execution_group())
        main_layout.addWidget(self._create_overlays_group())
        main_layout.addStretch()

    def _create_execution_group(self) -> QGroupBox:
        group = QGroupBox("Execution & Time Control")
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
        self.lbl_sim_time.setStyleSheet("color: #ffffff; font-family: monospace;")

        time_form.addRow("Simulation Time (t):", self.lbl_sim_time)

        layout.addLayout(time_form)
        return group

    def _create_overlays_group(self) -> QGroupBox:
        group = QGroupBox("3D Overlays & Vectors")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        self.chk_body_axes = QCheckBox("Show Satellite Body Axes (X, Y, Z)")
        self.chk_mag_vector = QCheckBox("Show Magnetic Dipole Vector (μ)")
        self.chk_rw_torque = QCheckBox("Show Reaction Wheels Net Torque (τ)")
        self.chk_orbit_trace = QCheckBox("Show Orbit Trajectory Trace")

        self.chk_body_axes.toggled.connect(lambda chk: self.overlay_toggled.emit("body_axes", chk))
        self.chk_mag_vector.toggled.connect(lambda chk: self.overlay_toggled.emit("magnetic_vector", chk))
        self.chk_rw_torque.toggled.connect(lambda chk: self.overlay_toggled.emit("rw_torque", chk))
        self.chk_orbit_trace.toggled.connect(lambda chk: self.overlay_toggled.emit("orbit_trace", chk))

        layout.addWidget(self.chk_body_axes)
        layout.addWidget(self.chk_mag_vector)
        layout.addWidget(self.chk_rw_torque)
        layout.addWidget(self.chk_orbit_trace)

        return group

    def _on_play_pause_clicked(self) -> None:
        self.is_running = not self.is_running
        if self.is_running:
            self.btn_play_pause.setText("Pause")
            self.timer.start()  
            # self.play_requested.emit()
        else:
            self.btn_play_pause.setText("Play")
            self.timer.stop()   
            # self.pause_requested.emit()

    def _on_speed_changed(self, value: int) -> None:
        self.speed_multiplier = value
        self.lbl_speed_val.setText(f"{value}x")
        self.speed_changed.emit(value)


    def _on_reset_clicked(self) -> None:
        self.is_running = False
        self.btn_play_pause.setText("Play")
        self.timer.stop()
        if self.engine:
            initial_state = self.engine.reset()
            self.lbl_sim_time.setText(f"{self.engine.sim_state.t:.2f} s")
            self.state_updated.emit(initial_state)
        self.reset_requested.emit()

    def _on_sim_tick(self) -> None:
        if not self.engine:
            return
            
        current_satellite_state = None
        for _ in range(self.speed_multiplier):
            current_satellite_state = self.engine.step()

        if current_satellite_state:
            self.lbl_sim_time.setText(f"{self.engine.sim_state.t:.2f} s")
            self.state_updated.emit(current_satellite_state)

        