import sys
from typing import Dict, Optional

import numpy as np
import pyqtgraph.opengl as gl
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (QFileDialog, 
                             QHBoxLayout, 
                             QSplitter, 
                             QStackedWidget, 
                             QWidget, 
                             QMessageBox, 
                             QPushButton, 
                             QButtonGroup,
                             QVBoxLayout)

from core.physics.dataclasses.orbital_data import OrbitalElements
from core.physics.orbits import Orbit
from ui.orbits.components.orbit_controls import OrbitControlsWidget
from ui.orbits.components.orbit_scene import OrbitSceneHelper
from ui.orbits.components.J2_analyzer_controls import J2AnalyzerControlsWidget
from ui.orbits.components.characteristics_tab import OrbitCharacteristicsTab
from utils.constants import CONSTANTS
import json
from utils.configuration import dt

from utils.rotations import get_pqw_to_eci_matrix


class OrbitDesigner(QWidget):
    """Main window for building and visualizing orbital trajectories."""

    def __init__(self) -> None:
        super().__init__()
        self.ranges = {
            "a": (CONSTANTS["R"] * 1e-3 + 100, 50000),
            "e": (0, 0.99),
            "i": (0, 180),
            "RAAN": (0, 359.9),
            "arg_perigee": (0, 359.9),
            "true_anomaly": (-360.0, 360.0),
        }

        self.orbit = None
        self.orbital_parameters = None
        self.plane_item = None
        self.earth = None
        self.grid = None
        self.view = None
        self.prev_controls = None
        self.eci_vectors: list[gl.GLLinePlotItem] = []
        self.orbit_artists: list[object] = []
        self.orbit_annotation_items: list[object] = []
        self.controls: Optional[OrbitControlsWidget] = None
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._advance_animation)
        self.animation_points: Optional[np.ndarray] = None
        self.animation_speeds: Optional[np.ndarray] = None
        self.animation_marker: Optional[gl.GLScatterPlotItem] = None
        self.animation_index = 0
        self.animation_step_count = 1000
        self.animation_period = None
        self.perturbed_annotations_items = []
        self.dt = dt

        self.setup_view()

    def setup_view(self) -> None:
        """Create the main window layout and initialize the 3D scene with top tab navigation."""
        layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_panel_container = QWidget()
        left_panel_layout = QVBoxLayout(left_panel_container)
        left_panel_layout.setContentsMargins(0, 0, 0, 0)
        left_panel_layout.setSpacing(10)  # Odstęp między zakładkami a zawartością

        tab_layout = QHBoxLayout()
        tab_layout.setSpacing(2)  # Ciasno spasowane przyciski-zakładki
        tab_layout.setContentsMargins(0, 0, 0, 5)

        self.btn_design = QPushButton("Design Orbit")
        self.btn_chars = QPushButton("Characteristics")
        self.btn_j2 = QPushButton("J₂ Perturbation")

        self.tab_group = QButtonGroup(self)
        self.tab_group.setExclusive(True)

        tabs = [self.btn_design, self.btn_chars, self.btn_j2]
        for idx, btn in enumerate(tabs):
            btn.setCheckable(True)
            btn.setFixedHeight(32)  # Stała, wygodna wysokość zakładki
            self.tab_group.addButton(btn, idx)
            tab_layout.addWidget(btn)

        self.btn_design.setChecked(True)
        left_panel_layout.addLayout(tab_layout)

        self.left_stacked_widget = QStackedWidget()

        self.btn_chars.setEnabled(False)
        self.btn_j2.setEnabled(False)

        self.controls = OrbitControlsWidget(self)
        self.chars_controls = OrbitCharacteristicsTab()  
        self.j2_controls = J2AnalyzerControlsWidget(self)

        self._connect_controls()
        
        self.left_stacked_widget.addWidget(self.controls)        # Index 0
        self.left_stacked_widget.addWidget(self.chars_controls)  # Index 1
        self.left_stacked_widget.addWidget(self.j2_controls)     # Index 2

        self.left_stacked_widget.setCurrentIndex(0)
        left_panel_layout.addWidget(self.left_stacked_widget)

        self.tab_group.idClicked.connect(self._on_tab_changed)

        self.view = gl.GLViewWidget()
        self._set_camera_limits(min_dist=12000.0, max_dist=150000.0)

        self.grid = gl.GLGridItem()
        self.grid.setSize(x=150_000, y=150_000)
        self.grid.setSpacing(x=10_000, y=10_000)    
        self.grid.setColor((255, 255, 255, 100.0))
        self.grid.setVisible(False)
        self.view.addItem(self.grid)

        self.earth = OrbitSceneHelper.create_earth()
        self.view.addItem(self.earth)

        self.eci_vectors = OrbitSceneHelper.create_eci_vectors()
        for axis in self.eci_vectors:
            self.view.addItem(axis)
            axis.setVisible(False)

        self.view.setCameraPosition(distance=20000, elevation=30, azimuth=30)
        self.view.setCameraParams()
        self.view.opts["glOptions"] = "opaque"

        splitter.addWidget(left_panel_container)
        splitter.addWidget(self.view)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)

    def _on_tab_changed(self, index: int) -> None:
        self.left_stacked_widget.setCurrentIndex(index)
        
        if index == 2:  
            if self.orbit is not None:
                self.j2_controls.update_perturbator(self.orbit)
                
        elif index == 1:  
            if self.orbit is not None:
                
                eci_positions = np.array([state.p * 1e-3 for state in self.orbit.orbitalState], dtype=np.float32)
                times = np.linspace(0, self.orbit.orbital_period, len(eci_positions))
                
                self.chars_controls.update_characteristics(
                    orbital_elements=self.orbit.orbitalElements, 
                    eci_positions=eci_positions,
                    times=times)

    def _set_camera_limits(self, min_dist: float, max_dist: float):
        """Set the minimum and maximum camera distance for zooming in/out."""
        original_wheel_event = self.view.wheelEvent

        def custom_wheel_event(event):
            delta = event.angleDelta().y()
            current_dist = self.view.opts['distance']

            if delta < 0 and current_dist >= max_dist:
                event.accept()  
                return

            if delta > 0 and current_dist <= min_dist:
                event.accept()  
                return

            original_wheel_event(event)

        self.view.wheelEvent = custom_wheel_event

    def _connect_controls(self) -> None:
        """Bind UI controls to the corresponding behavior methods."""
        self.controls.generate_button.clicked.connect(self.update_plot)
        self.controls.chk_grid.stateChanged.connect(lambda state: self.toggle_visibility(self.grid, state))
        self.controls.chk_eci.stateChanged.connect(self.toggle_eci_visibility)
        self.controls.chk_earth.stateChanged.connect(lambda state: self.toggle_visibility(self.earth, state))
        self.controls.chk_orbit_plane.stateChanged.connect(
            lambda state: self.toggle_visibility(self.plane_item, state) if self.plane_item is not None else None
        )
        self.controls.chk_orbital_elements.stateChanged.connect(self.toggle_orbital_elements_visibility)
        self.controls.animate_button.clicked.connect(self.toggle_animation)
        self.controls.clear_button.clicked.connect(self.clear_animation)
        self.controls.speed_slider.valueChanged.connect(self._update_animation_speed)
        self.controls.save_button.clicked.connect(self._save_orbit_to_file)
        self.j2_controls.btn_propagate.clicked.connect(self._on_propagate_clicked)
        self.j2_controls.btn_clear.clicked.connect(self._clear_perturbed_orbit)

    def _on_propagate_clicked(self):
        if self.orbit is None or self.j2_controls.J2_perturbator is None:
            return
        
        mode = self.j2_controls.time_mode_combo.currentText()
        value = self.j2_controls.time_value_spin.value()
        
        nodal_regression = self.j2_controls.J2_perturbator.mean_nodal_regression
        apsidal_precession = self.j2_controls.J2_perturbator.mean_apsidal_precession

        time_interval = value * 24 * 3600 if mode == "Days" else value * self.orbit.orbital_period

        raw_delta_Omega = time_interval * nodal_regression
        raw_delta_omega = time_interval * apsidal_precession

        delta_Omega_deg = np.degrees(raw_delta_Omega)
        delta_omega_deg = np.degrees(raw_delta_omega)

        self.j2_controls.update_drift_display(delta_Omega_deg, delta_omega_deg)

        new_Omega = np.mod(self.orbit.orbitalElements.raan + raw_delta_Omega, 2 * np.pi)
        new_omega = np.mod(self.orbit.orbitalElements.arg_perigee + raw_delta_omega, 2 * np.pi)
        inclination = self.orbit.orbitalElements.inclination

        R = get_pqw_to_eci_matrix(new_Omega, inclination, new_omega)
        pqw_positions = np.array([state.p * 1e-3 for state in self.orbit.orbitalState_PQW])
        eci_positions = (R @ pqw_positions.T).T

        self._draw_perturbed_orbit(eci_positions)
        self._draw_perturbed_orbit_annotations(new_Omega, new_omega)
        self.j2_controls.btn_clear.setEnabled(True)


    def _draw_perturbed_orbit(self, points: np.ndarray) -> None:
        """Rysuje linię orbity po ewolucji czasowej J2 do wizualnego porównania."""
        self._clear_perturbed_orbit()

        self.perturbed_orbit_line = gl.GLLinePlotItem(
            pos=points, 
            color=(0.96, 0.95, 0.26, 1.0),  
            width=2,
            glOptions="translucent"
        )
        self._add_item(self.perturbed_orbit_line)

        center = np.array([[0, 0, 0]], dtype=np.float32)
        mesh_vertices = np.vstack([center, points])
        
        faces = []
        num_points = len(points)
        for i in range(1, num_points):
            faces.append([0, i, i + 1])
        faces.append([0, num_points, 1])
        faces = np.array(faces, dtype=np.uint32)
        
        perturbed_plane_mesh = gl.MeshData(vertexes=mesh_vertices, faces=faces)
        self.perturbed_plane_item = gl.GLMeshItem(
            meshdata=perturbed_plane_mesh,
            smooth=False,
            color=(0.96, 0.95, 0.26, 0.15),  # Delikatny błękitny półprzezroczysty
            glOptions="translucent",
        )
        self._add_item(self.perturbed_plane_item)


    def _clear_perturbed_orbit(self):
        """Delete safe pertrubed orbit elements"""
        if hasattr(self, 'perturbed_orbit_line') and self.perturbed_orbit_line is not None:
            if self.perturbed_orbit_line in self.view.items:
                self.view.removeItem(self.perturbed_orbit_line)
            self.perturbed_orbit_line = None

        if hasattr(self, "perturbed_plane_item") and self.perturbed_plane_item is not None:
            if self.perturbed_plane_item in self.view.items:
                self.view.removeItem(self.perturbed_plane_item)
            self.perturbed_plane_item = None

        if hasattr(self, 'perturbed_annotations_items') and self.perturbed_annotations_items:
            for item in self.perturbed_annotations_items:
                if item in self.view.items:
                    self.view.removeItem(item)
                
                if hasattr(item, "_deleteGL"):
                    try:
                        item._deleteGL()
                    except Exception:
                        pass 
                        
            self.perturbed_annotations_items.clear()

        if hasattr(self.j2_controls, 'btn_clear'):
            self.j2_controls.btn_clear.setEnabled(False)

    def reset_designer(self) -> None:
        self.controls.reset_inputs()
        self._clear_previous_orbit_elements()
        self.controls.chk_orbit_plane.setEnabled(False)
        self.controls.chk_orbital_elements.setEnabled(False)
        self.controls.save_button.setEnabled(False)
        self.controls.chk_orbit_plane.setChecked(False)
        self.controls.chk_orbital_elements.setChecked(False)
        self.left_stacked_widget.setCurrentIndex(0)
        self.btn_j2.setEnabled(False)
        self.j2_controls.btn_clear.setEnabled(False)
        self.j2_controls.reset()
        self.btn_chars.setEnabled(False)
        self.view.setCameraPosition(distance=20000, elevation=30, azimuth=30)
        self.view.update()

    def load_predefined_orbit(self, orbit_data: Dict[str, float]) -> None:
        """Load a predefined orbit into the designer."""
        self.reset_designer()
        self.controls.input_a.setText(str(orbit_data["semi_major_axis"]))
        self.controls.input_arg_perigee.setText(str(orbit_data["arg_perigee"]))
        self.controls.input_e.setText(str(orbit_data["eccentricity"]))
        self.controls.input_i.setText(str(orbit_data["inclination"]))
        self.controls.input_RAAN.setText(str(orbit_data["raan"]))
        self.controls.input_true_anomaly.setText(str(orbit_data["true_anomaly"]))

        self.update_plot()


    def load_orbit_from_file(self, file_path : str) -> None:
        """ Loads orbit data from a JSON file and populates the input fields."""
        self.reset_designer()
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)

                self.controls.input_a.setText(str(data["semi_major_axis"]))
                self.controls.input_arg_perigee.setText(str(data["arg_perigee"]))
                self.controls.input_e.setText(str(data["eccentricity"]))
                self.controls.input_i.setText(str(data["inclination"]))
                self.controls.input_RAAN.setText(str(data["raan"]))
                self.controls.input_true_anomaly.setText(str(data["true_anomaly"]))

                file.close()
                QMessageBox.information(self, "Orbit Loaded", f"The orbit has been successfully loaded from:\n{file_path}")
            self.update_plot()
            return
        except Exception as e:
            QMessageBox.critical(self, "Loading Error", f"An error occurred while loading the orbit: {str(e)}")

    def _save_orbit_to_file(self) -> None:
        """ Saving the current orbit to a JSON file. """
        if self.orbit is None:
            QMessageBox.warning(self, "No Orbit", "There is no orbit to save. Please generate an orbit first.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Orbit Data",               # Tytuł okna
            "",                              # Domyślna ścieżka startowa (pusta oznacza katalog bieżący)
            "JSON Files (*.json);;All Files (*)" # Filtry rozszerzeń
        )

        if not file_path:
            return

        try:
            data = {
                "semi_major_axis": self.orbit.orbitalElements.semi_major_axis*1e-3,
                "eccentricity": self.orbit.orbitalElements.eccentricity,
                "inclination": np.rad2deg(self.orbit.orbitalElements.inclination),
                "raan": np.rad2deg(self.orbit.orbitalElements.raan),
                "arg_perigee": np.rad2deg(self.orbit.orbitalElements.arg_perigee),
                "true_anomaly": np.rad2deg(self.orbit.orbitalElements.true_anomaly),
            }

            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=4, ensure_ascii=False)

            QMessageBox.information(self, "Orbit Saved", f"The orbit has been successfully saved to:\n{file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"An error occurred while saving the orbit: {str(e)}")


    def toggle_eci_visibility(self) -> None:
        """Show or hide the ECI coordinate axes."""
        is_visible = self.controls.chk_eci.isChecked()
        for vector in self.eci_vectors:
            vector.setVisible(is_visible)
        self.view.update()

    def toggle_visibility(self, gl_item, state: int) -> None:
        """Toggle visibility for any PyQtGraph OpenGL item."""
        if gl_item is None:
            return
        gl_item.setVisible(state == 2)
        self.view.update()

    def toggle_orbital_elements_visibility(self) -> None:
        """Show or hide orbital-element annotation items."""
        self._set_orbit_annotation_visibility(self.controls.chk_orbital_elements.isChecked())
        self.view.update()

    def _update_animation_speed(self) -> None:
        """Restart the timer with the selected animation speed."""
        if self.animation_timer.isActive():
            self.animation_timer.start(self._animation_interval())

    def _set_animation_controls_enabled(self, enabled: bool) -> None:
        """Enable or disable the animation controls depending on whether an orbit is available."""
        if self.controls is None:
            return
        self.controls.animation_section.setEnabled(enabled)
        self.controls.animate_button.setEnabled(enabled)
        self.controls.clear_button.setEnabled(enabled)
        self.controls.speed_slider.setEnabled(enabled)

    def toggle_animation(self) -> None:
        """Start, pause, or resume the orbital animation."""
        if self.animation_points is None or len(self.animation_points) == 0:
            return

        if self.animation_timer.isActive():
            self.stop_animation()
            return

        self._ensure_animation_marker()
        self.animation_marker.setVisible(True)
        self.animation_timer.start(self._animation_interval())
        self.controls.animate_button.setText("Pause Animation")
        self.view.update()

    def stop_animation(self) -> None:
        """Pause the orbital animation without resetting the marker position."""
        self.animation_timer.stop()
        if self.animation_marker is not None:
            self.animation_marker.setVisible(True)
        if self.controls is not None:
            self.controls.animate_button.setText("Start Animation")
        self.view.update()

    def clear_animation(self) -> None:
        """Stop the animation and reset the marker to the initial orbit position."""
        self.animation_timer.stop()
        self.animation_index = 0
        if self.animation_points is not None and len(self.animation_points) > 0:
            self._set_marker_position(self.animation_points[0])
        if self.animation_marker is not None:
            self.animation_marker.setVisible(False)
        if self.controls is not None:
            self.controls.animate_button.setText("Start Animation")
        self.view.update()

    def _animation_interval(self) -> int:   
        """Convert the slider value into a timer interval in milliseconds."""
        speed_value = max(1, self.controls.speed_slider.value() * 20)
        if self.animation_speeds is None or len(self.animation_speeds) == 0:
            return max(1, int(20 / speed_value))

        if self.animation_points is None or len(self.animation_points) == 0:
            return max(1, int(20 / speed_value))

        if self.animation_points is None or len(self.animation_points) < 2:
            return max(1, int(20 / speed_value))

        current_speed = float(np.max(self.animation_speeds))
        if len(self.animation_speeds) > 0:
            current_speed = float(self.animation_speeds[self.animation_index % len(self.animation_speeds)])

        speed_ratio = current_speed / max(1.0, float(np.max(self.animation_speeds)))
        base_interval = max(20, int(300 * (1.0 - speed_ratio) + 20))
        if self.animation_period is not None and self.animation_period > 0:
            base_interval = max(10, int((self.animation_period / max(1, len(self.animation_speeds))) * 1000 / speed_value))
        return max(1, int(base_interval / speed_value))

    def _ensure_animation_marker(self) -> None:
        """Create the animated satellite marker if it does not exist yet."""
        if self.animation_marker is None:
            self.animation_marker = gl.GLScatterPlotItem(
                pos=np.empty((1, 3), dtype=np.float32),
                size=12,
                color=(1.0, 0.0, 0.0, 1.0),
                glOptions="translucent",
            )
            self._add_item(self.animation_marker)

    def _set_marker_position(self, position: np.ndarray) -> None:
        """Update the marker to a specific orbit position."""
        self._ensure_animation_marker()
        self.animation_marker.setData(
            pos=np.array([position], dtype=np.float32),
            size=12,
            color=(1.0, 1.0, 1.0, 1.0),
        )

    def _advance_animation(self) -> None:
        """Move the animated satellite marker one step along the orbit path."""
        if self.animation_points is None or len(self.animation_points) == 0:
            self.stop_animation()
            return

        self._ensure_animation_marker()
        self.animation_index = (self.animation_index + 1) % self.animation_step_count
        if self.animation_step_count <= 1:
            position = self.animation_points[0]
        else:
            progress = self.animation_index / max(1, self.animation_step_count)
            orbit_index = int(np.round(progress * (len(self.animation_points) - 1)))
            position = self.animation_points[orbit_index]
        self.animation_marker.setData(
            pos=np.array([position], dtype=np.float32),
            size=12,
            color=(1.0, 1.0, 1.0, 1.0),
        )
        self.animation_fraction = 0.0
        self.animation_timer.start(self._animation_interval())
        self.view.update()

    def _set_orbit_annotation_visibility(self, visible: bool) -> None:
        """Apply the current checkbox state to all orbital annotation items."""
        for item in self.orbit_annotation_items:
            item.setVisible(visible)

        if visible:
            self.controls.chk_earth.setChecked(False)
            self.controls.chk_eci.setChecked(True)

    def update_plot(self) -> None:
        """Validate inputs, build the orbit, and draw the resulting scene."""
        self.controls.chk_orbit_plane.setEnabled(False)
        self.controls.chk_orbital_elements.setEnabled(False)
        self.btn_chars.setEnabled(False)
        self.btn_j2.setEnabled(False)
        self.j2_controls.raan_drift_label.setText("0.00°")
        self.j2_controls.omega_drift_label.setText("0.00°")
        self._clear_previous_orbit_elements()

        orbital_values = self._validate_inputs()
        if orbital_values is None:
            return

        self.orbital_parameters = OrbitalElements(
            semi_major_axis=orbital_values["a"] * 1e3,
            eccentricity=orbital_values["e"],
            inclination=np.radians(orbital_values["i"]),
            raan=np.radians(orbital_values["RAAN"]),
            arg_perigee=np.radians(orbital_values["arg_perigee"]),
            true_anomaly=np.radians(orbital_values["true_anomaly"]),
        )

        self.orbit = Orbit(self.orbital_parameters)
        self.orbit.create_simple_orbit()

        points = np.array([state.p * 1e-3 for state in self.orbit.orbitalState], dtype=np.float32)
        self._draw_orbit(points)
        self._draw_orbit_annotations(points)
        self._setup_animation(points)
        self._set_orbit_annotation_visibility(self.controls.chk_orbital_elements.isChecked())
        self._set_animation_controls_enabled(self.orbit is not None and self.orbit.orbitalState is not None)
        self.view.update()
        self.controls.save_button.setEnabled(True)
        self.btn_chars.setEnabled(True)
        self.btn_j2.setEnabled(True)

    def _clear_previous_orbit_elements(self) -> None:
        """Remove earlier orbit visuals while preserving Earth, grid, and ECI axes."""
        self.stop_animation()
        for item in list(self.view.items):
            if item in (self.earth, self.grid, *self.eci_vectors):
                continue
            self.view.removeItem(item)
            if hasattr(item, "_deleteGL"):
                item._deleteGL()

        self.plane_item = None
        self.orbit_artists.clear()
        self.orbit_annotation_items.clear()
        self.animation_marker = None
        self.animation_points = None
        self.animation_speeds = None
        self.animation_index = 0
        self._set_animation_controls_enabled(False)

    def _setup_animation(self, points: np.ndarray) -> None:
        """Prepare the animated satellite marker for the current orbit."""
        self.animation_points = points
        self.animation_speeds = self.orbit.get_speed_profile()
        self.animation_period = self.orbit.orbital_period
        self.animation_index = 0
        self.animation_step_count = max(200, min(2000, len(points)))
        self._ensure_animation_marker()
        if len(points) > 0:
            self.animation_marker.setData(
                pos=np.array([points[0]], dtype=np.float32),
                size=12,
                color=(1.0, 1.0, 1.0, 1.0),
            )
            self.animation_marker.setVisible(False)
        self.view.update()

    def _validate_inputs(self) -> Optional[dict[str, float]]:
        """Collect and verify all orbital parameters from the UI."""
        self.controls.save_button.setEnabled(False)
        values = {}
        widgets = {
            "a": (self.controls.input_a, "Semi-major axis (a)"),
            "e": (self.controls.input_e, "Eccentricity (e)"),
            "i": (self.controls.input_i, "Inclination (i)"),
            "RAAN": (self.controls.input_RAAN, "RAAN (Ω)"),
            "arg_perigee": (self.controls.input_arg_perigee, "Argument of Perigee (ω)"),
            "true_anomaly": (self.controls.input_true_anomaly, "True Anomaly (ν)"),
        }

        for name, (widget, label) in widgets.items():
            numeric_value = self._check_numeric_inputs(widget, label)
            if numeric_value == -1:
                return None
            
            if name == "a":
                if numeric_value < CONSTANTS["R"] * 1e-3 + 100:
                    self.controls.chk_orbit_plane.setChecked(False)
                    self.controls.chk_orbital_elements.setChecked(False)
                    QMessageBox.warning(
                        self,
                        "Input Error",
                        f"Semi-major axis (a) must be greater than minimal value ({self.ranges['a'][0]:.2f} km)",
                    )
                    return None
                e_widget = self.controls.input_e
                try:
                    e_value = float(e_widget.text())
                    if e_value < 0 or e_value >= 1:
                        self.controls.chk_orbit_plane.setChecked(False)
                        self.controls.chk_orbital_elements.setChecked(False)
                        QMessageBox.warning(self, "Input Error", "Eccentricity (e) must be in the range [0, 1).")
                        return None
                    perigee_distance = numeric_value * (1 - e_value)
                    if perigee_distance < CONSTANTS["R"] * 1e-3:
                        self.controls.chk_orbit_plane.setChecked(False)
                        self.controls.chk_orbital_elements.setChecked(False)
                        QMessageBox.warning(
                            self,
                            "Input Error",
                            f"Perigee distance ({perigee_distance:.2f} km) is below Earth's radius ({self.ranges['a'][0]:.2f} km).",
                        )
                        return None
                except ValueError:
                    QMessageBox.warning(self, "Input Error", "Please enter a valid numeric value for Eccentricity (e).")
                    self.controls.chk_orbit_plane.setChecked(False)
                    self.controls.chk_orbital_elements.setChecked(False)
                    return None

            if not self._validate_field(widget, self.ranges[name][0], self.ranges[name][1]):
                return None

            values[name] = numeric_value

        return values

    def _check_numeric_inputs(self, line_edit, parameter: str) -> float:
        """Ensure that a field contains a valid floating point value."""
        try:
            value = float(line_edit.text())
            return value
        except ValueError:
            QMessageBox.warning(self, "Input Error", f"Please enter a valid numeric value for {parameter}.")
            self.controls.chk_orbit_plane.setChecked(False)
            self.controls.chk_orbital_elements.setChecked(False)
            return -1.0

    def _validate_field(self, line_edit, min_val: float, max_val: float) -> bool:
        """Ensure the numeric value stays within the allowed range."""
        try:
            value = float(line_edit.text())
            if not (min_val <= value <= max_val):
                raise ValueError
            return True
        except ValueError:
            self.controls.chk_orbit_plane.setChecked(False)
            self.controls.chk_orbital_elements.setChecked(False)
            return False

    def _draw_orbit(self, points: np.ndarray) -> None:
        """Draw the orbit line and the orbit plane overlay."""
        orbit_line = gl.GLLinePlotItem(pos=points, color=(1, 0.5, 0, 1), width=3)
        orbit_line.setGLOptions("translucent")
        self._add_item(orbit_line)

        center = np.array([[0, 0, 0]], dtype=np.float32)
        mesh_vertices = np.vstack([center, points])

        faces = []
        num_points = len(points)
        for i in range(1, num_points):
            faces.append([0, i, i + 1])
        faces.append([0, num_points, 1])
        faces = np.array(faces, dtype=np.uint32)

        orbit_plane_mesh = gl.MeshData(vertexes=mesh_vertices, faces=faces)
        self.plane_item = gl.GLMeshItem(
            meshdata=orbit_plane_mesh,
            smooth=False,
            color=(1, 0.5, 0, 0.2),
            glOptions="translucent",
        )
        self.plane_item.setVisible(self.controls.chk_orbit_plane.isChecked())
        self._add_item(self.plane_item)

        self.controls.chk_orbit_plane.setEnabled(True)
        self.controls.chk_orbital_elements.setEnabled(True)

    def _draw_orbit_annotations(self, points: np.ndarray) -> None:
        """Display the ascending node, perigee, and inclination annotations."""
        ascending_node_vector = self.orbit.get_ascending_node_line()
        orbit_plane_normal = None
        if self.orbit.orbitalState is not None:
            initial_position = self.orbit.orbitalState[0].p
            initial_velocity = self.orbit.orbitalState[0].v
            orbit_plane_normal = np.cross(initial_position, initial_velocity)
            orbit_plane_norm = np.linalg.norm(orbit_plane_normal)
            if orbit_plane_norm > 1e-8:
                orbit_plane_normal = orbit_plane_normal / orbit_plane_norm
            else:
                orbit_plane_normal = None

        exact_orbit_point = None
        corresponding_ascending_node_line = None

        ascending_node_vector_color = (0.0, 0.8, 0.8, 1.0)
        perigee_line_color = (0.7, 0.2, 0.8, 1.0)
        inclination_vector_color = (1.0, 0.4, 0.7, 1.0)
        true_anomaly_vector_color = (1.0, 0.0, 0.5, 1.0)

        if ascending_node_vector is not None and self.orbit.orbitalElements.inclination != 0.0:
            unit_node = ascending_node_vector / np.linalg.norm(ascending_node_vector)
            a_km = self.orbit.orbitalElements.semi_major_axis * 1e-3
            e = self.orbit.orbitalElements.eccentricity
            omega = self.orbit.orbitalElements.arg_perigee
            r_node_km = (a_km * (1 - e**2)) / (1 + e * np.cos(omega))
            exact_orbit_point = unit_node * r_node_km

            node_line_points = np.array([[0, 0, 0], exact_orbit_point], dtype=np.float32)
            node_item = gl.GLLinePlotItem(pos=node_line_points, color=ascending_node_vector_color, width=6, glOptions='opaque')
            self._add_item(node_item, track_annotation=True)

            ascending_node_point = gl.GLScatterPlotItem(
                pos=np.array([exact_orbit_point], dtype=np.float32),
                size=14,
                color=ascending_node_vector_color,
                glOptions='translucent',
            )
            self._add_item(ascending_node_point, track_annotation=True)

            text_position = exact_orbit_point * 1.05
            text_item = gl.GLTextItem(pos=text_position, text="Ascending Node", color=(255, 255, 255, 255))
            self._add_item(text_item, track_annotation=True)

            if self.orbit.orbitalElements.raan != 0:
                radius_val = 5000.0
                half_x_axis = np.array([radius_val, 0, 0], dtype=np.float32)
                corresponding_ascending_node_line = np.array([
                    radius_val * np.cos(self.orbit.orbitalElements.raan),
                    radius_val * np.sin(self.orbit.orbitalElements.raan),
                    0.0,
                ], dtype=np.float32)

                angle_item, label_item = OrbitSceneHelper.create_angle_arc(
                    half_x_axis,
                    corresponding_ascending_node_line,
                    radius=radius_val,
                    annotation="Ω",
                    normal=np.array([0.0, 0.0, 1.0], dtype=np.float32),
                    color=ascending_node_vector_color
                )
                if angle_item is not None:
                    self._add_item(angle_item, track_annotation=True)
                if label_item is not None:
                    self._add_item(label_item, track_annotation=True)

        perigee_line = self.orbit.get_perigee_line() * 1e-3
        if perigee_line is not None and self.orbit.orbitalElements.eccentricity != 0.0:
            perigee_line_points = np.array([[0, 0, 0], perigee_line], dtype=np.float32)
            perigee_item = gl.GLLinePlotItem(pos=perigee_line_points, color=perigee_line_color, width=6, glOptions='opaque')
            self._add_item(perigee_item, track_annotation=True)

            if self.orbit.orbitalElements.arg_perigee != 0.0:
                if corresponding_ascending_node_line is None:
                    corresponding_ascending_node_line = np.array([1.0, 0.0, 0.0], dtype=np.float32) * 5000.0
                angle_item, label_item = OrbitSceneHelper.create_angle_arc(
                    corresponding_ascending_node_line,
                    perigee_line,
                    radius=5000.0,
                    annotation="ω",
                    normal=orbit_plane_normal,
                    color=perigee_line_color
                )
                if angle_item is not None:
                    self._add_item(angle_item, track_annotation=True)
                if label_item is not None:
                    self._add_item(label_item, track_annotation=True)

        true_anomaly_vector = self.orbit.get_true_anomaly_vector() * 1e-3   
        if true_anomaly_vector is not None and self.orbit.orbitalElements.true_anomaly != 0.0 and self.orbit.orbitalElements.eccentricity != 0.0:
            true_anomaly_line = gl.GLLinePlotItem(
                pos=np.array([[0, 0, 0], true_anomaly_vector], dtype=np.float32),
                color=true_anomaly_vector_color,
                width=6,
                glOptions='opaque',
            )
            self._add_item(true_anomaly_line, track_annotation=True)

            true_anomaly_label = gl.GLTextItem(
                pos=true_anomaly_vector * 1.05,
                text="ν",
                color=(255, 255, 255, 255),
            )
            self._add_item(true_anomaly_label, track_annotation=True)

            true_anomaly_angle, true_anomaly_angle_label = OrbitSceneHelper.create_angle_arc(
                perigee_line,
                true_anomaly_vector,
                radius=5000.0,
                annotation="ν",
                normal=orbit_plane_normal,
                color=true_anomaly_vector_color
            )
            if true_anomaly_angle is not None:
                self._add_item(true_anomaly_angle, track_annotation=True)
            if true_anomaly_angle_label is not None:
                self._add_item(true_anomaly_angle_label, track_annotation=True)

        if self.orbit.orbitalElements.inclination != 0.0 and exact_orbit_point is not None:
            u_node = ascending_node_vector / np.linalg.norm(ascending_node_vector)
            z_axis = np.array([0, 0, 1], dtype=np.float32)
            u_equator_dir = np.cross(z_axis, u_node)
            u_equator_dir = u_equator_dir / np.linalg.norm(u_equator_dir)

            h_vector = np.cross(self.orbit.orbitalState[0].p, self.orbit.orbitalState[0].v)
            u_orbit_dir = np.cross(u_node, h_vector)
            u_orbit_dir = u_orbit_dir / np.linalg.norm(u_orbit_dir)
            if u_orbit_dir[2] < 0:
                u_orbit_dir = -u_orbit_dir

            radius_val = 500.0
            v_equator = u_equator_dir * radius_val
            v_orbit = u_orbit_dir * radius_val

            help_vector_item = gl.GLLinePlotItem(
                pos=np.array([exact_orbit_point, exact_orbit_point + v_equator], dtype=np.float32),
                color=inclination_vector_color,
                width=6,
                glOptions='opaque',
            )
            self._add_item(help_vector_item, track_annotation=True)

            inclination_angle, inclination_label = OrbitSceneHelper.create_angle_arc(
                v_equator,
                v_orbit,
                radius=radius_val,
                annotation="i",
                normal=u_node,
                color=inclination_vector_color
            )
            if inclination_angle is not None:
                shifted_pos = inclination_angle.pos + exact_orbit_point
                inclination_angle.setData(pos=shifted_pos)
                self._add_item(inclination_angle, track_annotation=True)
            if inclination_label is not None:
                current_text_pos = np.array(inclination_label.pos)
                inclination_label.setData(pos=current_text_pos + exact_orbit_point)
                self._add_item(inclination_label, track_annotation=True)

    def _draw_perturbed_orbit_annotations(self, new_Omega: float, new_omega: float) -> None:
        """Draw lines and angles for angular shifts (Delta Omega and Delta omega) for J2."""
        
        if hasattr(self, 'perturbed_annotations_items'):
            for item in self.perturbed_annotations_items:
                if item in self.view.items:
                    self.view.removeItem(item)
        self.perturbed_annotations_items = []

        if self.orbit is None:
            return

        drift_raan_color = (1.0, 0.85, 0.0, 1.0)      # Złoty dla ΔΩ
        drift_omega_color = (1.0, 0.3, 0.3, 1.0)      # Jasnoczerwony dla Δω
        radius_val = 5000.0
        
        inclination = self.orbit.orbitalElements.inclination
        eccentricity = self.orbit.orbitalElements.eccentricity
        orig_raan = self.orbit.orbitalElements.raan
        orig_omega = self.orbit.orbitalElements.arg_perigee
        
        EPSILON = 1e-6
        VISUAL_THRESHOLD = 1e-6  
        
        is_equatorial = (inclination < EPSILON) or np.isclose(inclination, np.pi, atol=EPSILON)

        delta_Omega = np.arctan2(np.sin(new_Omega - orig_raan), np.cos(new_Omega - orig_raan))
        delta_omega = np.arctan2(np.sin(new_omega - orig_omega), np.cos(new_omega - orig_omega))

        if not is_equatorial and abs(delta_Omega) >= VISUAL_THRESHOLD:
            orig_node_vec = np.array([
                radius_val * np.cos(orig_raan),
                radius_val * np.sin(orig_raan),
                0.0
            ], dtype=np.float32)

            perturbed_node_vec = np.array([
                radius_val * np.cos(new_Omega),
                radius_val * np.sin(new_Omega),
                0.0
            ], dtype=np.float32)

            p_node_line_pts = np.array([[0, 0, 0], perturbed_node_vec], dtype=np.float32)
            p_node_item = gl.GLLinePlotItem(pos=p_node_line_pts, color=drift_raan_color, width=6, glOptions='opaque')
            self.view.addItem(p_node_item)
            self.perturbed_annotations_items.append(p_node_item)

            angle_item_raan, label_item_raan = OrbitSceneHelper.create_angle_arc(
                orig_node_vec,
                perturbed_node_vec,
                radius=radius_val,
                annotation="ΔΩ",
                normal=np.array([0.0, 0.0, 1.0], dtype=np.float32),
                color=drift_raan_color,
                shortest_path=True  
            )
            if angle_item_raan is not None:
                self.view.addItem(angle_item_raan)
                self.perturbed_annotations_items.append(angle_item_raan)
            if label_item_raan is not None:
                self.view.addItem(label_item_raan)
                self.perturbed_annotations_items.append(label_item_raan)

        if eccentricity > EPSILON and abs(delta_omega) >= VISUAL_THRESHOLD:
            orig_perigee_raw = self.orbit.get_perigee_line()
            orig_perigee_norm = np.linalg.norm(orig_perigee_raw)
            if orig_perigee_norm > 1e-5:
                orig_perigee_vec = (orig_perigee_raw / orig_perigee_norm) * radius_val
            else:
                orig_perigee_vec = np.array([radius_val, 0, 0], dtype=np.float32)

            R_perturbed = get_pqw_to_eci_matrix(new_Omega, inclination, new_omega)
            perturbed_perigee_dir = R_perturbed @ np.array([1.0, 0.0, 0.0], dtype=np.float32)
            perturbed_perigee_vec = perturbed_perigee_dir * radius_val

            p_perigee_line_pts = np.array([[0, 0, 0], perturbed_perigee_vec], dtype=np.float32)
            p_perigee_item = gl.GLLinePlotItem(pos=p_perigee_line_pts, color=drift_omega_color, width=6, glOptions='opaque')
            self.view.addItem(p_perigee_item)
            self.perturbed_annotations_items.append(p_perigee_item)

            perturbed_plane_normal = np.cross(orig_perigee_vec, perturbed_perigee_vec)
            perturbed_plane_normal = perturbed_plane_normal / np.linalg.norm(perturbed_plane_normal)

            angle_item_omega, label_item_omega = OrbitSceneHelper.create_angle_arc(
                orig_perigee_vec,
                perturbed_perigee_vec,
                radius=radius_val,
                annotation="Δω",
                normal=perturbed_plane_normal,
                color=drift_omega_color,
                shortest_path=True  
            )

            if angle_item_omega is not None:
                self.view.addItem(angle_item_omega)
                self.perturbed_annotations_items.append(angle_item_omega)
            if label_item_omega is not None:
                self.view.addItem(label_item_omega)
                self.perturbed_annotations_items.append(label_item_omega)

    def _add_item(self, item, track_annotation: bool = False) -> None:
        """Add an item to the scene and keep track of it for cleanup."""
        self.view.addItem(item)
        self.orbit_artists.append(item)
        if track_annotation:
            self.orbit_annotation_items.append(item)


# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     window = OrbitDesigner()
#     window.show()
#     sys.exit(app.exec())