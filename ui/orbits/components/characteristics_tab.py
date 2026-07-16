from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget, QVBoxLayout, QGridLayout, QGroupBox, QLabel, QLineEdit
import numpy as np
from core.physics.dataclasses.orbital_data import OrbitalElements
from ui.orbits.components.ground_track import GroundTrackWindow
from utils.constants import CONSTANTS

class OrbitCharacteristicsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Physical constants for Earth
        self.MU = CONSTANTS["mu"] * 1e-9    # km^3 / s^2
        self.R_E = CONSTANTS["R"] * 1e-3    # km

        self.last_eci_positions = None 
        self.last_times = None
        self.last_orbital_elements = None
        
        self.ground_track_window = None
        self.evolution_plots_window = None
        
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)

        # 1. GROUP: GEOMETRY
        geo_group = QGroupBox("Trajectory Geometry")
        geo_layout = QGridLayout(geo_group)
        
        self.lbl_perigee_alt = self._create_row(geo_layout, 0, "Perigee Altitude (hp):", "km")
        self.lbl_apogee_alt = self._create_row(geo_layout, 1, "Apogee Altitude (ha):", "km")
        self.lbl_semi_latus = self._create_row(geo_layout, 2, "Semi-latus Rectum (p):", "km")
        main_layout.addWidget(geo_group)

        # 2. GROUP: DYNAMICS & ENERGETICS
        dyn_group = QGroupBox("Dynamics and Energetics")
        dyn_layout = QGridLayout(dyn_group)
        
        self.lbl_period = self._create_row(dyn_layout, 0, "Orbital Period (T):", "")
        self.lbl_v_perigee = self._create_row(dyn_layout, 1, "Velocity at Perigee (vp):", "km/s")
        self.lbl_v_apogee = self._create_row(dyn_layout, 2, "Velocity at Apogeum (va):", "km/s")
        self.lbl_energy = self._create_row(dyn_layout, 3, "Specific Mechanical Energy (ε):", "MJ/kg")
        main_layout.addWidget(dyn_group)

        # 3. GROUP: MISSION CLASSIFICATION
        class_group = QGroupBox("Classification & Properties")
        class_layout = QGridLayout(class_group)
        
        self.lbl_orbit_type = self._create_row(class_layout, 0, "Orbit Type (Altitude-based):", "")
        self.lbl_special_features = self._create_row(class_layout, 1, "J2 Perturbation Features:", "")
        main_layout.addWidget(class_group)

        # 4. GROUP: ANALYSIS TOOLS
     
        self.btn_ground_track = QPushButton("Open Ground Track")
        self.btn_ground_track.setEnabled(False) 
        self.btn_ground_track.clicked.connect(self._open_ground_track)
        
        main_layout.addWidget(self.btn_ground_track)

        main_layout.addStretch()

    def _create_row(self, layout, row, label_text, unit_text):
        """Helper method to create a clean key-value-unit layout row."""
        lbl_name = QLabel(f"<b>{label_text}</b>")
        
        val_field = QLineEdit("-")
        val_field.setReadOnly(True)
        val_field.setAlignment(type(val_field).alignment(val_field) | type(val_field).alignment(val_field).AlignRight)
        val_field.setStyleSheet("background-color: #2b2b2b; color: #a9b7c6; border: 1px solid #3c3f41;")
        
        layout.addWidget(lbl_name, row, 0)
        layout.addWidget(val_field, row, 1)
        
        if unit_text:
            lbl_unit = QLabel(unit_text)
            layout.addWidget(lbl_unit, row, 2)
            
        return val_field

    def update_characteristics(self, orbital_elements : OrbitalElements, eci_positions = None, times = None):
        """
        Updates fields based on Keplerian elements.
        Expects orbital_elements to have: semi_major_axis (in m or km), eccentricity, inclination (in rad).
        """
        if orbital_elements is None:
            return
        
        self.last_orbital_elements = orbital_elements
        self.last_times = times
        self.last_eci_positions = eci_positions
        if self.last_eci_positions is not None and len(self.last_eci_positions) > 0:
            self.btn_ground_track.setEnabled(True)

        a = orbital_elements.semi_major_axis * 1e-3 if orbital_elements.semi_major_axis > 100000 else orbital_elements.semi_major_axis
        e = orbital_elements.eccentricity
        inc_rad = orbital_elements.inclination
        inc_deg = np.degrees(inc_rad)

        r_p = a * (1.0 - e)
        r_a = a * (1.0 + e)
        h_p = r_p - self.R_E
        h_a = r_a - self.R_E
        p = a * (1.0 - e**2)

        self.lbl_perigee_alt.setText(f"{h_p:,.2f}")
        self.lbl_apogee_alt.setText(f"{h_a:,.2f}")
        self.lbl_semi_latus.setText(f"{p:,.2f}")

        period_seconds = 2.0 * np.pi * np.sqrt((a**3) / self.MU)
        if period_seconds < 3600:
            self.lbl_period.setText(f"{period_seconds / 60.0:.2f} min")
        else:
            hours = int(period_seconds // 3600)
            minutes = int((period_seconds % 3600) // 60)
            self.lbl_period.setText(f"{hours}h {minutes}m ({period_seconds:,.1f} s)")

        v_p = np.sqrt((2.0 * self.MU / r_p) - (self.MU / a)) if r_p > 0 else 0
        v_a = np.sqrt((2.0 * self.MU / r_a) - (self.MU / a)) if r_a > 0 else 0
        energy = -self.MU / (2.0 * a)

        self.lbl_v_perigee.setText(f"{v_p:.4f}")
        self.lbl_v_apogee.setText(f"{v_a:.4f}")
        self.lbl_energy.setText(f"{energy:.3f}")

        if h_p < 0:
            orbit_type = "Suborbital / Destructive (Re-entry)"
        elif h_a < 2000:
            orbit_type = "LEO (Low Earth Orbit)"
        elif h_p >= 35500 and h_a <= 36000 and e < 0.01:
            orbit_type = "GEO (Geostationary Earth Orbit)"
        elif h_p > 2000 and h_a < 35000:
            orbit_type = "MEO (Medium Earth Orbit)"
        elif e > 0.4:
            orbit_type = "HEO (Highly Elliptical Orbit)"
        else:
            orbit_type = "Other / Non-standard"
        self.lbl_orbit_type.setText(orbit_type)

        features = []
        if np.isclose(inc_deg, 63.435, atol=0.1) or np.isclose(inc_deg, 116.565, atol=0.1):
            features.append("Critical Inclination (Δω = 0)")
        
        if h_a > 0:
            n = np.sqrt(self.MU / (a**3))
            J2 = 1.08263e-3
            raan_drift = -1.5 * n * J2 * (self.R_E / p)**2 * np.cos(inc_rad)
            raan_drift_deg_day = np.degrees(raan_drift) * 86400.0
            if np.isclose(raan_drift_deg_day, 0.9856, atol=0.05):
                features.append("Sun-Synchronous (SSO)")

        if not features:
            features.append("No distinct J2 features")
            
        self.lbl_special_features.setText(", ".join(features))

    def _open_ground_track(self):
        if self.last_eci_positions is None:
            return
        
        if self.last_eci_positions is None:
            return
            
        self.ground_track_window = GroundTrackWindow(self.last_eci_positions, self.last_times)
        self.ground_track_window.show()
        

    def _open_orbital_plots(self):
        if self.last_orbital_elements is None:
            return