
import datetime
import json

from PyQt6.QtWidgets import QHBoxLayout, QMessageBox, QSizePolicy, QWidget, QSplitter
from PyQt6.QtCore import QTimer, Qt

from core.physics.dataclasses.orbital_data import OrbitalElements
from core.physics.dataclasses.satellite_configuration import SatelliteConfiguration
from ui.simulation.components.simulation_controlls import SimulationControls
from ui.simulation.components.simulation_scene import SimulationScene
from utils.rotations import datetime_to_julian_date, get_initial_gmst
from utils.ui.ui_utils import show_dark_message_box




class SimulationView(QWidget):

    def __init__(self, orbital_data : OrbitalElements, satellite_data : SatelliteConfiguration, parent=None):
        super().__init__(parent)        
        self.orbital_data : OrbitalElements= orbital_data
        self.satellite_data : SatelliteConfiguration = satellite_data
        self.plot_update_timer = QTimer(self)
        self.plot_update_timer.setInterval(45) 
        self.plot_update_timer.timeout.connect(self._update_plots_callback)
        self.plot_update_timer.start()
        self.setup_view()

    def load_simulation(self, orbital_data : OrbitalElements, satellite_data : SatelliteConfiguration):

        self.reset()
        now = datetime.datetime.now(datetime.timezone.utc)
        current_jd = datetime_to_julian_date(now)
        
        self.initial_gmst = get_initial_gmst(current_jd)
        self.current_ecef_rotation = self.initial_gmst
        self.orbital_data  = orbital_data
        self.satellite_data = satellite_data
        print("Simulation data successfully loaded into SimulationView.")

        self.controls_panel_container.update_data(
            orbital_data=self.orbital_data,
            satellite_data=self.satellite_data
        )

        self.scene_panel_container._ensure_ECEF_orientation(self.current_ecef_rotation)

    def reset(self):
        self.controls_panel_container.reset()
        self.scene_panel_container._clear_satellite()
        self.current_ecef_rotation = self.initial_gmst
        self.scene_panel_container._ensure_ECEF_orientation(self.current_ecef_rotation)

    def load_simulation_from_file(self, file_path : str) -> None:
        """Load a saved SimulationConfiguration JSON back into the editor."""
        now = datetime.datetime.now(datetime.timezone.utc)
        current_jd = datetime_to_julian_date(now)
        
        self.initial_gmst = get_initial_gmst(current_jd)
        self.current_ecef_rotation = self.initial_gmst
        self.reset()
        try:
            with open(file_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
                orbital_data = payload.get("orbital_data", {})
                mechnical_data = payload.get("satellite_configuration", {})
                if not orbital_data or not mechnical_data:
                    raise ValueError("Missing required simulation data")
                handle.close()
        except (OSError, ValueError, TypeError):
            show_dark_message_box(
                None,
                "Load failed",
                "The selected file could not be read as a simulation configuration.",
                icon=QMessageBox.Icon.Warning,
            )
            raise ValueError("Invalid configuration")
        
        self.controls_panel_container.load_from_file(payload)
        self.scene_panel_container._ensure_ECEF_orientation(self.current_ecef_rotation)

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

        self.controls_panel_container.satellite_state_changed.connect(
            self._on_satellite_state_changed
        )

        self.controls_panel_container.scence_changed.connect(
            self.update_scene
        )
        
        self.scene_panel_container = SimulationScene()

        now = datetime.datetime.now(datetime.timezone.utc)
        current_jd = datetime_to_julian_date(now)
        
        self.initial_gmst = get_initial_gmst(current_jd)
        self.current_ecef_rotation = self.initial_gmst

        self.scene_panel_container._ensure_ECEF_orientation(self.current_ecef_rotation)        

        splitter.addWidget(self.controls_panel_container)
        splitter.addWidget(self.scene_panel_container)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        main_layout.addWidget(splitter)

    def _on_satellite_state_changed(
        self,
        dimensions_m: tuple[float, float, float],
        position_km: tuple[float, float, float],
        euler_deg: tuple[float, float, float],
    ) -> None:
        if not self.scene_panel_container.satellite_items:
            self.scene_panel_container.create_satellite(dimensions_m)

        self.scene_panel_container.update_satellite_state(
            position_km=position_km, euler_deg=euler_deg, track_camera=True
        )

        simulation_engine = self.controls_panel_container.control_panel.engine
        if  simulation_engine is not None:
            # Aktualizacja obrotu Ziemi na podstawie czasu symulacji
            current_t = (
                simulation_engine.sim_state.t
            )

            

            angular_velocity_deg_per_sec = 360.0 / 86164.0905

            initial_offset = getattr(self, "initial_gmst", 0.0)
            self.current_ecef_rotation = (
                initial_offset + angular_velocity_deg_per_sec * current_t
            ) % 360.0

            self.scene_panel_container._ensure_ECEF_orientation(
                self.current_ecef_rotation
            )

            self.update_scene()

    
    def update_scene(self):
        self.scene_panel_container.mark_orbit_trace(
            self.controls_panel_container.show_orbit_trace
            )

        self.scene_panel_container.show_body_frame(
            self.controls_panel_container.show_body_frame
        )

        
        self.scene_panel_container.show_magnetic_vector(
            self.controls_panel_container.show_magnetic_vector
        )

        self.scene_panel_container.show_net_torque(
            self.controls_panel_container.show_rw_net_torque
        )

    def _update_plots_callback(self):
        # Wykresy odświeżają się w stałym interwale 30 FPS, niezależnie od liczby kroków integracji
        if self.controls_panel_container.control_panel.engine is not None:
            history = (
                self.controls_panel_container.control_panel.engine.history
            )
            self.controls_panel_container._plots_tab.update_telemetry(history)

                

                